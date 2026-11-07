#!/usr/bin/env python3
"""Drive `fsh-ovnfs-largefile-v0` (largefile.py) on LayerFS, one unit per command.

    lf_layerfs.py CASE open              Store, push to docker, import, Sandbox, branch b01, mount
    lf_layerfs.py CASE steps FIRST LAST  per step: Exec the edit, Commit (records new_stored)
    lf_layerfs.py CASE verify            unmount, fresh mount, sha256 vs oracle
    lf_layerfs.py CASE close             close the Sandbox, final probe, remove the Store

Public CLI only. Campaign directory $LF_CAMPAIGN holds artifacts/layerfs, home/
(0700), xdg/ (sealed bundle), empty/ and base/<CASE>/<CASE>.bin (from
`largefile.py gen`); results go to $LF_CAMPAIGN/results/layerfs-<CASE>/. The
Sandbox image does not contain largefile.py, so each Exec passes it inline
(`python3 -c <script>`); the project tree holds only the case's file. Each call
is bounded at 110 s, nothing is retried and a failed case is never continued.
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
import largefile  # noqa: E402

CAMPAIGN = Path(os.environ.get("LF_CAMPAIGN", Path.home() / ".cache" / "fsh-lf-layerfs"))
CLI = str(CAMPAIGN / "artifacts" / "layerfs")
ENV = dict(os.environ, LAYERFS_HOME=str(CAMPAIGN / "home"), XDG_CACHE_HOME=str(CAMPAIGN / "xdg"),
           LAYERFS_CONSTRUCTION_WORKERS="1")
PROBE_IMAGE = "fsh-cmp-layerfs:b4fa173e"  # any local image with GNU find
SCRIPT = shlex.quote((HERE / "largefile.py").read_text())
CALL_TIMEOUT_S = 110
UNIT_BUDGET_S = 100


class Fail(Exception):
    pass


def worker_volume():
    home_id = json.loads((CAMPAIGN / "home" / "layerfs.json").read_text())["id"]
    return f"lfs-{home_id[:8]}-docker-data"


class Unit:
    def __init__(self, case, unit):
        self.case, self.unit = case, unit
        self.dir = CAMPAIGN / "results" / f"layerfs-{case}"
        self.store = f"lf-{case.lower()}"
        if unit == "open":
            if self.dir.exists():
                raise Fail("results exist; never overwritten")
            self.dir.mkdir(parents=True)
            self.state = {"arm": "layerfs", "case": case, "workload": largefile.VERSION,
                          "spec": largefile.CASES[case], "steps": [], "probes": [], "calls": [],
                          "status": "open"}
        else:
            self.state = json.loads((self.dir / "state.json").read_text())
            if self.state.get("status") == "FAIL":
                raise Fail("case already failed; not continued")
        self.started = time.monotonic()
        self.state.setdefault("load_1m", []).append(
            {"unit": " ".join(sys.argv[2:]), "load": round(os.getloadavg()[0], 2)})

    def save(self):
        tmp = self.dir / "state.json.tmp"
        tmp.write_text(json.dumps(self.state, indent=1, sort_keys=True) + "\n")
        tmp.replace(self.dir / "state.json")

    def call(self, label, argv, env=None):
        if time.monotonic() - self.started > UNIT_BUDGET_S:
            raise Fail(f"unit budget spent before {label}")
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
        shown = [a if len(a) < 200 else a[:40] + "…<inline largefile.py>…" + a[-60:] for a in argv[:8]]
        with open(self.dir / "events.jsonl", "a") as f:
            f.write(json.dumps({"seq": seq, "label": label, "argv": shown, "exit": code, "wall_ns": wall,
                                "stdout": out[-4000:], "stderr": err[-2000:], "unit": self.unit}) + "\n")
        self.state["calls"].append({"seq": seq, "label": label, "wall_ns": wall, "exit": code})
        if code != 0:
            raise Fail(f"{label}: exit {code}: {err.strip()[-300:]}")
        return out, wall

    def lf(self, label, *args):
        out, wall = self.call(label, [CLI, *args], env=ENV)
        try:
            return json.loads(out), wall
        except ValueError:
            return {"raw": out.strip()}, wall

    def exec_py(self, label, ws, *args):
        cmd = f"python3 -c {SCRIPT} " + " ".join(shlex.quote(a) for a in args)
        r, wall = self.lf(label, "workspace", "exec", ws, cmd)
        if r.get("exit_code") != 0:
            raise Fail(f"{label}: exit_code {r.get('exit_code')}: {str(r.get('stderr', ''))[-300:]}")
        return json.loads(r["stdout"]), wall

    def probe(self, label):
        status, _ = self.lf(f"probe_{label}", "store", "status", self.store)
        f = status.get("file") or {}
        rec = {"label": label, "file_bytes": f.get("bytes"), "wal_bytes": f.get("wal_bytes") or 0,
               "state": status.get("state")}
        if status.get("machine") == "docker":
            out, _ = self.call(f"probe_{label}_alloc", [
                "docker", "run", "--rm", "--network", "none", "--pull", "never", "-v",
                f"{worker_volume()}:/d:ro", "--entrypoint", "find", PROBE_IMAGE, f"/d/store/{self.store}",
                "-maxdepth", "1", "-name", "store.sqlite*", "-printf", "%f %s %b\\n"])
            alloc = {}
            for line in out.split("\n"):
                parts = line.split()
                if len(parts) == 3:
                    alloc[parts[0]] = int(parts[2]) * 512
            rec["allocated_bytes"] = sum(v for k, v in alloc.items() if not k.endswith("-shm"))
        rec["total_bytes"] = (rec["file_bytes"] or 0) + rec["wal_bytes"]
        self.state["probes"].append(rec)
        return rec

    def open(self):
        s = self.store
        self.lf("store_create", "store", "create", s)
        self.lf("init_floor", "project", "init", f"{s}/e", str(CAMPAIGN / "empty"))
        self.lf("store_push", "store", "push", s, "docker")
        self.probe("floor")
        _, self.state["import_ns"] = self.lf("import", "project", "init", f"{s}/p01",
                                             str(CAMPAIGN / "base" / self.case))
        self.probe("import")
        _, self.state["sandbox_create_ns"] = self.lf("sandbox_create", "sandbox", "create", f"{s}/p01",
                                                     f"{s}-sb", "docker")
        _, self.state["fork_ns"] = self.lf("fork", "branch", "fork", f"{s}/p01", "b01", "main")
        m, self.state["mount_ns"] = self.lf("mount", "workspace", "mount", f"{s}-sb", "b01", "--name", "wb01")
        if not m.get("ws"):
            raise Fail("mount gave no ws")
        self.state["ws"] = m["ws"]

    def steps(self, first, last):
        done = len(self.state["steps"])
        if first != done + 1:
            raise Fail(f"next step is {done + 1}, not {first}")
        if last > largefile.CASES[self.case]["commits"]:
            raise Fail("past the last commit")
        ws = self.state["ws"]
        for k in range(first, last + 1):
            edit, we = self.exec_py(f"apply_{k}", ws, "apply", self.case, str(k), ".")
            c, wc = self.lf(f"commit_{k}", "workspace", "commit", ws)
            if c.get("kind") != "Committed":
                raise Fail(f"commit kind {c.get('kind')}")
            info = c.get("commit") or {}
            self.state["steps"].append({"step": k, "apply_ns": we, "commit_ns": wc, "edit": edit,
                                        "new_stored": info.get("new_stored"),
                                        "new_metadata": info.get("new_metadata"),
                                        "new_canonical": info.get("new_canonical")})
            self.save()

    def verify(self):
        expected = largefile.expect(self.case)[-1]
        if len(self.state["steps"]) != largefile.CASES[self.case]["commits"]:
            raise Fail("not every step has run")
        self.lf("unmount", "workspace", "unmount", self.state["ws"])
        m, self.state["verify_open_ns"] = self.lf("vmount", "workspace", "mount", f"{self.store}-sb", "b01",
                                                  "--name", "vb01")
        got, self.state["verify_read_ns"] = self.exec_py("vsha", m["ws"], "sha", ".")
        self.lf("vunmount", "workspace", "unmount", m["ws"])
        got = got.get(f"{self.case}.bin", {})
        self.state["verification"] = {"expected": expected, "got": got,
                                      "result": "PASS" if got.get("sha256") == expected["sha256"] else "FAIL"}

    def close(self):
        self.lf("sandbox_close", "sandbox", "close", f"{self.store}-sb")
        self.probe("final")
        self.lf("store_remove", "store", "remove", self.store)
        self.state["store_removed"] = True

    def run(self, args):
        try:
            if self.unit == "open":
                self.open()
            elif self.unit == "steps":
                self.steps(int(args[0]), int(args[1]))
            elif self.unit == "verify":
                self.verify()
            elif self.unit == "close":
                self.close()
                self.state["status"] = "closed"
        except (Fail, ValueError, KeyError, IndexError) as e:
            self.state["status"] = "FAIL"
            self.state["reason"] = f"{type(e).__name__}: {e}"
            self.save()
            print(json.dumps({"unit": self.unit, "status": "FAIL", "reason": self.state["reason"]}))
            return 1
        self.save()
        steps = self.state["steps"]
        print(json.dumps({"unit": self.unit, "elapsed_s": round(time.monotonic() - self.started, 1),
                          "steps": len(steps),
                          "new_stored": [s["new_stored"] for s in steps[-10:]],
                          "commit_ms": [round(s["commit_ns"] / 1e6) for s in steps[-10:]],
                          "verification": self.state.get("verification", {}).get("result"),
                          "last_probe": self.state["probes"][-1] if self.state["probes"] else None}))
        return 0


def main(argv):
    if len(argv) < 2 or argv[0] not in largefile.CASES or argv[1] not in ("open", "steps", "verify", "close"):
        print(__doc__)
        return 2
    return Unit(argv[0], argv[1]).run(argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
