#!/usr/bin/env python3
"""LayerFS v2.0.0 (Docker machine) vs ovnfs: a small speed + storage comparison.

Workload: the fs-storage-history base tree (DSH checkpoint 157) and its frozen
edit model (fsh-edit-model-v1), in four small shapes. This is a diagnostic
side-by-side, label "fsh-ovnfs-compare-v0"; it is not fs-storage-history-v1.

    compare.py ARM CASE open
    compare.py ARM CASE branch NAME
    compare.py ARM CASE close

ARM is layerfs or ovnfs. Each unit is one command bounded below two minutes;
each subprocess is bounded at 110 s; nothing is retried. Results go to
results/<ARM>-<CASE>/ (events.jsonl append-only, state.json).
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUITE = Path("/Users/yifanxu/Ephemeral-AI-Lab/layerfs-benchmark/fs-storage-history/src")
sys.path.insert(0, str(SUITE))
import base  # noqa: E402
import model  # noqa: E402

BASE_DIR = "/Users/yifanxu/.cache/fs-storage-history/base-157"
CLI = str(ROOT / "artifacts" / "layerfs")
ENV = dict(os.environ, LAYERFS_HOME=str(ROOT / "home"), XDG_CACHE_HOME=str(ROOT / "xdg"),
           LAYERFS_CONSTRUCTION_WORKERS="1")
WORKER_VOLUME = "lfs-0bb7b473-docker-data"
LAYERFS_IMAGE = "fsh-cmp-layerfs:b4fa173e"
OVNFS_IMAGE = "fsh-cmp-ovnfs:cdb3fb6"
MODEL = "/opt/fs-storage-history/model.py"
CALL_TIMEOUT_S = 110
UNIT_BUDGET_S = 105  # no new call starts after this; the unit fails instead

# name -> list of (branch, from, commits, seed); seeds reuse fs-storage-history's.
CASES = {
    "S1": [("b01", "main", 40, "H01/p01/b01")],
    "S2": [(f"b{i:02d}", "main", 3, f"H02/p01/b{i:02d}") for i in range(1, 6)],
    "S3": [(f"l{i:02d}", "main" if i == 1 else f"l{i - 1:02d}", 3, f"H04/p01/l{i:02d}")
           for i in range(1, 5)],
    "S4": [(f"b{i:02d}", "main", 1, "H03/shared") for i in range(1, 6)],
}


class Fail(Exception):
    pass


def plan(case):
    state = base.load_tree(BASE_DIR)
    base.check_pins(state.summary())
    heads, out = {"main": state}, {}
    for name, source, commits, seed in CASES[case]:
        s = heads[source].copy()
        steps = [model.encode_ops(model.plan_step(s, seed, k)) for k in range(1, commits + 1)]
        heads[name] = s
        out[name] = {"from": source, "steps": steps, "head": s.summary()["sha256"]}
    return out


class Unit:
    def __init__(self, arm, case, unit):
        self.arm, self.case, self.unit = arm, case, unit
        self.dir = ROOT / "results" / f"{arm}-{case}"
        if unit == "open":
            if self.dir.exists():
                raise Fail("results exist; never overwritten")
            self.dir.mkdir(parents=True)
            self.state = {"arm": arm, "case": case, "branches": {}, "probes": [], "status": "open"}
        else:
            self.state = json.loads((self.dir / "state.json").read_text())
            if self.state.get("status") == "FAIL":
                raise Fail("case already failed; not continued")
        self.started = time.monotonic()
        self.seq = len(self.state.setdefault("calls", []))
        self.state.setdefault("load_1m", []).append(
            {"unit": unit if unit != "branch" else f"branch {sys.argv[4]}",
             "load": round(os.getloadavg()[0], 2)})

    def save(self):
        tmp = self.dir / "state.json.tmp"
        tmp.write_text(json.dumps(self.state, indent=1, sort_keys=True) + "\n")
        tmp.replace(self.dir / "state.json")

    def call(self, label, argv, env=None, check=True):
        if time.monotonic() - self.started > UNIT_BUDGET_S:
            raise Fail(f"unit budget spent before {label}")
        self.seq += 1
        t0 = time.monotonic_ns()
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=CALL_TIMEOUT_S, env=env)
            code, out, err = p.returncode, p.stdout, p.stderr
        except subprocess.TimeoutExpired as e:
            code, out, err = "timeout", e.stdout or "", e.stderr or ""
            if isinstance(out, bytes):
                out, err = out.decode(errors="replace"), (err or b"").decode(errors="replace")
        wall = time.monotonic_ns() - t0
        event = {"seq": self.seq, "label": label, "argv": argv[:6] + (["…"] if len(argv) > 6 else []),
                 "exit": code, "wall_ns": wall, "stdout": out[-4000:], "stderr": err[-2000:],
                 "unit": self.unit}
        with open(self.dir / "events.jsonl", "a") as f:
            f.write(json.dumps(event) + "\n")
        self.state["calls"].append({"seq": self.seq, "label": label, "wall_ns": wall, "exit": code})
        if check and code != 0:
            self.state["status"] = "FAIL"
            self.state["reason"] = f"{label}: exit {code}: {err.strip()[-300:]}"
            self.save()
            raise Fail(self.state["reason"])
        return out, wall

    # -- LayerFS --------------------------------------------------------------
    def lf(self, label, *args):
        out, wall = self.call(label, [CLI, *args], env=ENV)
        try:
            return json.loads(out), wall
        except ValueError:
            return {"raw": out.strip()}, wall

    def lf_probe(self, label):
        store = self.store
        status, _ = self.lf(f"probe_{label}", "store", "status", store)
        f = status.get("file") or {}
        out, _ = self.call(f"probe_{label}_alloc", [
            "docker", "run", "--rm", "--network", "none", "--pull", "never", "-v",
            f"{WORKER_VOLUME}:/d:ro", "--entrypoint", "find", LAYERFS_IMAGE, f"/d/store/{store}",
            "-maxdepth", "1", "-name", "store.sqlite*", "-printf", "%f %s %b\\n"])
        alloc = {}
        for line in out.split("\n"):
            parts = line.split()
            if len(parts) == 3:
                alloc[parts[0]] = int(parts[2]) * 512
        rec = {"label": label, "file_bytes": f.get("bytes"), "wal_bytes": f.get("wal_bytes") or 0,
               "allocated_bytes": sum(v for k, v in alloc.items() if not k.endswith("-shm")),
               "state": status.get("state")}
        rec["total_bytes"] = (rec["file_bytes"] or 0) + rec["wal_bytes"]
        self.state["probes"].append(rec)
        return rec

    @property
    def store(self):
        return f"cmp-{self.case.lower()}"

    def lf_open(self):
        s, empty = self.store, str(ROOT / "empty")
        self.lf("store_create", "store", "create", s)
        self.lf("init_floor", "project", "init", f"{s}/e", empty)
        self.lf("store_push", "store", "push", s, "docker")
        self.lf_probe("floor")
        _, w = self.lf("import", "project", "init", f"{s}/p01", BASE_DIR)
        self.state["import_ns"] = w
        self.lf_probe("import")
        _, w = self.lf("sandbox_create", "sandbox", "create", f"{s}/p01", f"{s}-sb", "docker")
        self.state["sandbox_create_ns"] = w

    def lf_branch(self, name, spec):
        s, rec = self.store, {"steps": []}
        _, rec["fork_ns"] = self.lf(f"fork_{name}", "branch", "fork", f"{s}/p01", name, spec["from"])
        m, rec["mount_ns"] = self.lf(f"mount_{name}", "workspace", "mount", f"{s}-sb", name,
                                     "--name", f"w{name}")
        ws = m.get("ws")
        if not ws:
            raise Fail("mount gave no ws")
        if "control_ns" not in self.state:
            r, w = self.lf("control_exec_true", "workspace", "exec", ws, "true")
            self.state["control_ns"] = w
        for k, enc in enumerate(spec["steps"], 1):
            r, we = self.lf(f"exec_{name}_{k}", "workspace", "exec", ws,
                            f"python3 {MODEL} apply {enc}")
            if r.get("exit_code") != 0:
                raise Fail(f"apply exit {r.get('exit_code')}: {r.get('stderr', '')[-300:]}")
            c, wc = self.lf(f"commit_{name}_{k}", "workspace", "commit", ws)
            if c.get("kind") != "Committed":
                raise Fail(f"commit kind {c.get('kind')}")
            info = c.get("commit") or {}
            rec["steps"].append({"apply_ns": we, "commit_ns": wc, "new_stored": info.get("new_stored"),
                                 "new_metadata": info.get("new_metadata"),
                                 "new_canonical": info.get("new_canonical")})
            self.save()
        _, rec["unmount_ns"] = self.lf(f"unmount_{name}", "workspace", "unmount", ws)
        m, rec["verify_open_ns"] = self.lf(f"vmount_{name}", "workspace", "mount", f"{s}-sb", name,
                                           "--name", f"v{name}")
        r, rec["verify_read_ns"] = self.lf(f"manifest_{name}", "workspace", "exec", m["ws"],
                                           f"python3 {MODEL} manifest")
        self.lf(f"vunmount_{name}", "workspace", "unmount", m["ws"])
        rec["head_sha256"] = json.loads(r["stdout"])["sha256"]
        return rec

    def lf_close(self):
        self.lf("sandbox_close", "sandbox", "close", f"{self.store}-sb")
        self.lf_probe("final")
        self.lf("store_remove", "store", "remove", self.store)

    # -- ovnfs ------------------------------------------------------------------
    @property
    def ctr(self):
        return f"fsh-cmp-ov-{self.case.lower()}"

    def ov(self, label, *args, cwd=None, check=True):
        argv = ["docker", "exec", "-e", "OVNFS_STATE=/data/state"]
        if cwd:
            argv += ["-w", cwd]
        return self.call(label, argv + [self.ctr, *args], check=check)

    def ov_probe(self, label):
        out, _ = self.ov(f"probe_{label}", "sh", "-c",
                         "cd /data/state && du -s -B1 . && du -s -b --apparent-size . && "
                         "for d in store layers uppers bases snapshots git sources; do "
                         "[ -e $d ] && du -s -B1 $d; done; true")
        lines = [ln.split() for ln in out.strip().split("\n") if ln.strip()]
        rec = {"label": label, "allocated_bytes": int(lines[0][0]), "apparent_bytes": int(lines[1][0]),
               "parts": {p[1]: int(p[0]) for p in lines[2:]}}
        rec["total_bytes"] = rec["allocated_bytes"]
        self.state["probes"].append(rec)
        return rec

    def ov_open(self):
        vol = self.ctr
        self.call("docker_run", ["docker", "run", "-d", "--name", self.ctr, "--device", "/dev/fuse",
                                 "--cap-add", "SYS_ADMIN", "--security-opt", "apparmor=unconfined",
                                 "-v", f"{vol}:/data", "--entrypoint", "sleep", OVNFS_IMAGE, "infinity"])
        self.state["owned"] = {"container": self.ctr, "volume": vol}
        self.save()
        self.ov("mkdir_src", "mkdir", "-p", "/data/src")
        self.call("copy_base", ["docker", "cp", "-q", f"{BASE_DIR}/.", f"{self.ctr}:/data/src/"])
        _, self.state["daemon_start_ns"] = self.ov("daemon_start", "ovnfs", "start")
        self.ov_probe("floor")
        out, w = self.ov("import", "ovnfs", "--json", "new", "--name", "main", "--rule", "source *",
                         cwd="/data/src")
        self.state["import_ns"] = w
        self.state["import_reply"] = json.loads(out)
        self.ov_probe("import")

    def ov_branch(self, name, spec):
        rec = {"steps": []}
        if spec["from"] == "main":
            _, rec["fork_ns"] = self.ov(f"new_{name}", "ovnfs", "--json", "new", "--name", name,
                                        "--rule", "source *", cwd="/data/src")
        else:
            _, rec["fork_ns"] = self.ov(f"fork_{name}", "ovnfs", "--json", "fork", spec["from"],
                                        "--name", name)
        rec["mount_ns"] = 0  # the checkout is mounted by new/fork
        if "control_ns" not in self.state:
            _, self.state["control_ns"] = self.ov("control_exec_true", "true")
        path = f"/root/checkouts/{name}"
        snap = None
        for k, enc in enumerate(spec["steps"], 1):
            _, we = self.ov(f"exec_{name}_{k}", "python3", MODEL, "apply", enc, cwd=path)
            out, wc = self.ov(f"commit_{name}_{k}", "ovnfs", "--json", "snap", name, "--wait")
            snap = json.loads(out)["snapshot"]
            rec["steps"].append({"apply_ns": we, "commit_ns": wc, "snapshot": snap["id"]})
            self.save()
        rec["unmount_ns"] = 0
        v = f"v{name}"
        _, rec["verify_open_ns"] = self.ov(f"vnew_{name}", "ovnfs", "--json", "new", "--name", v,
                                           "--from", snap["id"])
        out, rec["verify_read_ns"] = self.ov(f"manifest_{name}", "python3", MODEL, "manifest",
                                             cwd=f"/root/checkouts/{v}")
        self.ov(f"vrm_{name}", "ovnfs", "rm", v)
        rec["head_sha256"] = json.loads(out)["sha256"]
        return rec

    def ov_close(self):
        self.ov("daemon_stop", "ovnfs", "stop")
        self.ov_probe("final")
        self.call("docker_rm", ["docker", "rm", "-f", self.ctr])
        self.call("volume_rm", ["docker", "volume", "rm", self.ctr])
        self.state["owned_released"] = True

    # -- driver -----------------------------------------------------------------
    def run(self, name=None):
        try:
            if self.unit == "open":
                self.lf_open() if self.arm == "layerfs" else self.ov_open()
            elif self.unit == "branch":
                spec = plan(self.case)[name]
                if name in self.state["branches"]:
                    raise Fail("branch already run")
                rec = self.lf_branch(name, spec) if self.arm == "layerfs" else self.ov_branch(name, spec)
                rec["verification"] = "PASS" if rec["head_sha256"] == spec["head"] else "FAIL"
                self.state["branches"][name] = rec
                # LayerFS probes need a quiesced Store (Sandbox closed), so only
                # ovnfs gets a per-branch probe; LayerFS reports new_stored per Commit.
                if self.arm == "ovnfs":
                    self.ov_probe(f"after_{name}")
            elif self.unit == "close":
                self.lf_close() if self.arm == "layerfs" else self.ov_close()
                self.state["status"] = "closed"
        except Fail as e:
            self.state["status"] = "FAIL"
            self.state.setdefault("reason", str(e))
            self.save()
            print(json.dumps({"unit": self.unit, "status": "FAIL", "reason": self.state["reason"]}))
            return 1
        self.save()
        summary = {"unit": self.unit, "name": name, "elapsed_s": round(time.monotonic() - self.started, 1)}
        if name:
            r = self.state["branches"][name]
            summary.update(verification=r["verification"],
                           apply_ms=[round(s["apply_ns"] / 1e6) for s in r["steps"]],
                           commit_ms=[round(s["commit_ns"] / 1e6) for s in r["steps"]])
        if self.state["probes"]:
            summary["last_probe"] = self.state["probes"][-1]
        print(json.dumps(summary))
        return 0


def main(argv):
    arm, case, unit = argv[0], argv[1], argv[2]
    if arm not in ("layerfs", "ovnfs") or case not in CASES or unit not in ("open", "branch", "close"):
        print(__doc__)
        return 2
    return Unit(arm, case, unit).run(argv[3] if unit == "branch" else None)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
