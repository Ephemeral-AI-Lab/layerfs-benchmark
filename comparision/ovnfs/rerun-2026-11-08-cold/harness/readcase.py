#!/usr/bin/env python3
"""Explicit cold read cases for LayerFS and ovnfs, one unit per command.

    readcase.py ARM CASE open      set up the committed state to read
    readcase.py ARM CASE read K    cold boundary, then one timed exec that reads every byte
    readcase.py ARM CASE close     release everything

Cases:
    RT0    the 65 MB fs-storage-history base tree (9,404 files), as imported
    RT40   that tree after S1's 40 commits (fs-storage-history edit model, seed H01/p01/b01)
    RF0    the 500 MiB L500 file, as imported
    RF5    that file after L500's 5 commits (100 B overwrites)

Cold boundary before every read: LayerFS closes the Sandbox, restarts the machine, creates a new
Sandbox and mounts the branch; ovnfs stops and starts its daemon and opens a fresh checkout of the
last snapshot. Then cold.py evicts the system's own files from the VM page cache. The timed exec
walks the tree and reads every regular file (symlinks skipped) in 1 MiB blocks; its file and byte
counts must match the oracle. ARM is layerfs or ovnfs; results go to
$CMP_CAMPAIGN/results/<arm>-<case>/. Nothing is retried; a failed case is never continued.
"""

import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cold  # noqa: E402
import largefile  # noqa: E402

sys.path.insert(0, "/Users/yifanxu/Ephemeral-AI-Lab/layerfs-benchmark/fs-storage-history/src")
import base  # noqa: E402
import model  # noqa: E402

CAMPAIGN = Path(os.environ["CMP_CAMPAIGN"])
CLI = str(CAMPAIGN / "artifacts" / "layerfs")
ENV = dict(os.environ, LAYERFS_HOME=str(CAMPAIGN / "home"), XDG_CACHE_HOME=str(CAMPAIGN / "xdg"),
           LAYERFS_CONSTRUCTION_WORKERS="1")
TREE = "/Users/yifanxu/.cache/fs-storage-history/base-157"
FILE_DIR = str(CAMPAIGN / "base" / "L500")
MODEL = "/opt/fs-storage-history/model.py"
OVNFS_IMAGE = "fsh-cmp-ovnfs:5d54cb0"
CALL_TIMEOUT_S = 110
CASES = {"RT0": ("tree", 0), "RT40": ("tree", 40), "RF0": ("file", 0), "RF5": ("file", 5)}
READ = ("import os,json\nn=b=0\nfor d,_,fs in os.walk('.'):\n for f in fs:\n  p=os.path.join(d,f)\n"
        "  if os.path.isfile(p) and not os.path.islink(p):\n   n+=1\n   with open(p,'rb') as h:\n"
        "    while True:\n     x=h.read(1<<20)\n     if not x: break\n     b+=len(x)\n"
        "print(json.dumps({'files':n,'bytes':b}))\n")
LARGEFILE = shlex.quote((HERE / "largefile.py").read_text())


class Fail(Exception):
    pass


def home_id8():
    return json.loads((CAMPAIGN / "home" / "layerfs.json").read_text())["id"][:8]


def history(case):
    """The encoded edit steps and the expected {files, bytes} of the state to read."""
    kind, n = CASES[case]
    if kind == "tree":
        s = base.load_tree(TREE)
        steps = [model.encode_ops(model.plan_step(s, "H01/p01/b01", k)) for k in range(1, n + 1)]
        files = [e for e in s.entries.values() if e.kind == "file"]
        return steps, {"files": len(files), "bytes": sum(len(e.data) for e in files)}
    return list(range(1, n + 1)), {"files": 1, "bytes": largefile.CASES["L500"]["size"]}


class Unit:
    def __init__(self, arm, case, unit):
        self.arm, self.case, self.unit = arm, case, unit
        self.kind, self.commits = CASES[case]
        self.dir = CAMPAIGN / "results" / f"{arm}-{case}"
        self.store, self.sb = f"rd-{case.lower()}", f"rd-{case.lower()}-sb"
        self.ctr = f"fsh-rd-ov-{case.lower()}"
        if unit == "open":
            if self.dir.exists():
                raise Fail("results exist; never overwritten")
            self.dir.mkdir(parents=True)
            self.state = {"arm": arm, "case": case, "reads": [], "calls": [], "status": "open"}
        else:
            self.state = json.loads((self.dir / "state.json").read_text())
            if self.state.get("status") == "FAIL" and unit != "close":
                raise Fail("case already failed; not continued (close still releases it)")
        self.state.setdefault("load_1m", []).append({"unit": " ".join(sys.argv[3:]), "load": round(os.getloadavg()[0], 2)})

    def save(self):
        tmp = self.dir / "state.json.tmp"
        tmp.write_text(json.dumps(self.state, indent=1, sort_keys=True) + "\n")
        tmp.replace(self.dir / "state.json")

    def call(self, label, argv, env=None):
        seq = len(self.state["calls"]) + 1
        t0 = time.monotonic_ns()
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=CALL_TIMEOUT_S, env=env)
            code, out, err = p.returncode, p.stdout, p.stderr
        except subprocess.TimeoutExpired as e:
            code = "timeout"
            out = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            err = e.stderr.decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        wall = time.monotonic_ns() - t0
        shown = [a if len(a) < 200 else a[:40] + "…" + a[-40:] for a in argv[:8]]
        with open(self.dir / "events.jsonl", "a") as f:
            f.write(json.dumps({"seq": seq, "label": label, "argv": shown, "exit": code, "wall_ns": wall,
                                "stdout": out[-4000:], "stderr": err[-2000:], "unit": self.unit}) + "\n")
        self.state["calls"].append({"seq": seq, "label": label, "wall_ns": wall, "exit": code})
        if code != 0:
            raise Fail(f"{label}: exit {code}: {err.strip()[-300:]}")
        return out, wall

    def evict(self, label):
        if self.arm == "layerfs":
            argv = cold.evict_argv(f"lfs-{home_id8()}-docker-data", cold.layerfs_roots(home_id8(), self.store, self.sb))
        else:
            argv = cold.evict_argv(self.ctr, cold.OVNFS_ROOTS)
        out, wall = self.call(label, argv)
        return dict(json.loads(out), wall_ns=wall)

    # -- LayerFS ------------------------------------------------------------------
    def lf(self, label, *args):
        out, wall = self.call(label, [CLI, *args], env=ENV)
        try:
            return json.loads(out), wall
        except ValueError:
            return {"raw": out.strip()}, wall

    def lf_exec(self, label, ws, cmd):
        r, wall = self.lf(label, "workspace", "exec", ws, cmd)
        if r.get("exit_code") != 0:
            raise Fail(f"{label}: exit_code {r.get('exit_code')}: {str(r.get('stderr', ''))[-300:]}")
        return r, wall

    def lf_open(self):
        s = self.store
        self.lf("store_create", "store", "create", s)
        self.lf("init_floor", "project", "init", f"{s}/e", str(CAMPAIGN / "empty"))
        self.lf("store_push", "store", "push", s, "docker")
        self.lf("import", "project", "init", f"{s}/p01", TREE if self.kind == "tree" else FILE_DIR)
        self.lf("sandbox_create", "sandbox", "create", f"{s}/p01", self.sb, "docker")
        # main is the published line and cannot be mounted: read a Branch forked from it (no commits
        # for RT0/RF0, the case's history for RT40/RF5)
        self.lf("fork", "branch", "fork", f"{s}/p01", "b01", "main")
        self.state["branch"] = "b01"
        steps, _ = history(self.case)
        if steps:
            m, _ = self.lf("mount", "workspace", "mount", self.sb, "b01", "--name", "wb01")
            for k, step in enumerate(steps, 1):
                cmd = (f"python3 {MODEL} apply {step}" if self.kind == "tree"
                       else f"python3 -c {LARGEFILE} apply L500 {step} .")
                self.lf_exec(f"apply_{k}", m["ws"], cmd)
                c, _ = self.lf(f"commit_{k}", "workspace", "commit", m["ws"])
                if c.get("kind") != "Committed":
                    raise Fail(f"commit kind {c.get('kind')}")
            self.lf("unmount", "workspace", "unmount", m["ws"])

    def lf_read(self, k):
        self.lf(f"cold_sandbox_close_{k}", "sandbox", "close", self.sb)
        self.lf(f"cold_machine_stop_{k}", "machine", "stop", "docker")
        self.lf(f"cold_machine_start_{k}", "machine", "start", "docker")
        self.lf(f"cold_sandbox_create_{k}", "sandbox", "create", f"{self.store}/p01", self.sb, "docker")
        m, open_ns = self.lf(f"mount_{k}", "workspace", "mount", self.sb, self.state["branch"], "--name", f"r{k}")
        ev = self.evict(f"evict_{k}")
        r, read_ns = self.lf_exec(f"read_{k}", m["ws"], f"python3 -c {shlex.quote(READ)}")
        self.lf(f"unmount_{k}", "workspace", "unmount", m["ws"])
        return json.loads(r["stdout"]), read_ns, open_ns, ev

    def lf_close(self):
        self.lf("sandbox_close", "sandbox", "close", self.sb)
        self.lf("store_remove", "store", "remove", self.store)

    # -- ovnfs --------------------------------------------------------------------
    def ov(self, label, *args, cwd=None):
        argv = ["docker", "exec", "-e", "OVNFS_STATE=/data/state"] + (["-w", cwd] if cwd else [])
        return self.call(label, argv + [self.ctr, *args])

    def ov_open(self):
        self.call("docker_run", ["docker", "run", "-d", "--name", self.ctr, "--device", "/dev/fuse", "--cap-add",
                                 "SYS_ADMIN", "--security-opt", "apparmor=unconfined", "-v", f"{self.ctr}:/data",
                                 "--entrypoint", "sleep", OVNFS_IMAGE, "infinity"])
        self.state["owned"] = {"container": self.ctr, "volume": self.ctr}
        self.save()
        self.ov("mkdir", "mkdir", "-p", "/data/src", "/opt/lf")
        self.call("copy_script", ["docker", "cp", str(HERE / "largefile.py"), f"{self.ctr}:/opt/lf/largefile.py"])
        self.call("copy_base", ["docker", "cp", "-q", f"{TREE if self.kind == 'tree' else FILE_DIR}/.", f"{self.ctr}:/data/src/"])
        self.ov("daemon_start", "ovnfs", "start")
        self.ov("import", "ovnfs", "--json", "new", "--name", "main", "--rule", "source *", cwd="/data/src")
        steps, _ = history(self.case)
        name = "main"
        if steps:
            self.ov("new_b01", "ovnfs", "--json", "new", "--name", "b01", "--rule", "source *", cwd="/data/src")
            name = "b01"
            for k, step in enumerate(steps, 1):
                cmd = (["python3", MODEL, "apply", step] if self.kind == "tree"
                       else ["python3", "/opt/lf/largefile.py", "apply", "L500", str(step), "."])
                self.ov(f"apply_{k}", *cmd, cwd="/root/checkouts/b01")
                out, _ = self.ov(f"snap_{k}", "ovnfs", "--json", "snap", "b01", "--wait")
        else:
            out, _ = self.ov("snap_main", "ovnfs", "--json", "snap", "main", "--wait")
        self.state["snapshot"] = json.loads(out)["snapshot"]["id"]

    def ov_read(self, k):
        self.ov(f"cold_daemon_stop_{k}", "ovnfs", "stop")
        self.ov(f"cold_daemon_start_{k}", "ovnfs", "start")
        _, open_ns = self.ov(f"new_{k}", "ovnfs", "--json", "new", "--name", f"r{k}", "--from", self.state["snapshot"])
        ev = self.evict(f"evict_{k}")
        out, read_ns = self.ov(f"read_{k}", "python3", "-c", READ, cwd=f"/root/checkouts/r{k}")
        self.ov(f"rm_{k}", "ovnfs", "rm", f"r{k}")
        return json.loads(out), read_ns, open_ns, ev

    def ov_close(self):
        self.ov("daemon_stop", "ovnfs", "stop")
        self.call("docker_rm", ["docker", "rm", "-f", self.ctr])
        self.call("volume_rm", ["docker", "volume", "rm", self.ctr])
        self.state["owned_released"] = True

    def run(self, args):
        try:
            if self.unit == "open":
                self.lf_open() if self.arm == "layerfs" else self.ov_open()
            elif self.unit == "read":
                k = int(args[0])
                if k != len(self.state["reads"]) + 1:
                    raise Fail(f"next read is {len(self.state['reads']) + 1}, not {k}")
                got, read_ns, open_ns, ev = self.lf_read(k) if self.arm == "layerfs" else self.ov_read(k)
                _, want = history(self.case)
                self.state["reads"].append({"k": k, "read_ns": read_ns, "open_ns": open_ns, "evict": ev, "got": got,
                                            "verification": "PASS" if got == want else "FAIL"})
            elif self.unit == "close":
                self.lf_close() if self.arm == "layerfs" else self.ov_close()
                self.state["released"] = True
                if self.state["status"] != "FAIL":
                    self.state["status"] = "closed"
        except (Fail, ValueError, KeyError, IndexError) as e:
            self.state["status"] = "FAIL"
            self.state["reason"] = f"{type(e).__name__}: {e}"
            self.save()
            print(json.dumps({"unit": self.unit, "status": "FAIL", "reason": self.state["reason"]}))
            return 1
        self.save()
        last = self.state["reads"][-1] if self.state["reads"] else {}
        print(json.dumps({"unit": self.unit, "read_ms": round(last.get("read_ns", 0) / 1e6),
                          "verification": last.get("verification"), "resident_after": last.get("evict", {}).get("resident_after")}))
        return 0


def main(argv):
    if len(argv) < 3 or argv[0] not in ("layerfs", "ovnfs") or argv[1] not in CASES or argv[2] not in ("open", "read", "close"):
        print(__doc__)
        return 2
    return Unit(argv[0], argv[1], argv[2]).run(argv[3:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
