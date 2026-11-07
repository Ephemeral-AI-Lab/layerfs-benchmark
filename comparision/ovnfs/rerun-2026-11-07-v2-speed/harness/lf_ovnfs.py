#!/usr/bin/env python3
"""Drive `fsh-ovnfs-largefile-v0` (largefile.py) on ovnfs, one unit per command.

    lf_ovnfs.py CASE open            container, starting file, import, branch b01
    lf_ovnfs.py CASE steps FIRST LAST  edit + snap --wait + storage probe per step
    lf_ovnfs.py CASE verify          fresh checkout of the last snapshot, sha256 vs oracle
    lf_ovnfs.py CASE close           stop the daemon, final probe, remove container + volume

Each unit stays under two minutes; each call is bounded at 110 s; nothing is
retried and a failed case is never continued. Results go to
results/ovnfs-<CASE>/ (events.jsonl append-only, state.json) next to this file,
or under $LF_RESULTS.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import largefile  # noqa: E402

RESULTS = Path(os.environ.get("LF_RESULTS", HERE / "results"))
IMAGE = os.environ.get("LF_OVNFS_IMAGE", "fsh-cmp-ovnfs:5d54cb0")
SCRIPT = "/opt/lf/largefile.py"
CHECKOUT = "/root/checkouts/b01"
CALL_TIMEOUT_S = 110
UNIT_BUDGET_S = 100
PROBE = ("cd /data/state && du -s -B1 . && du -s -b --apparent-size . && "
         "for d in store store/packs store/objects layers uppers bases nodes.log; do "
         "[ -e $d ] && du -s -B1 $d; done; "
         "echo objects_files $(find store/objects -type f 2>/dev/null | wc -l); "
         "echo objects_apparent $(du -s -b --apparent-size store/objects 2>/dev/null | cut -f1); "
         "echo packs_apparent $(du -s -b --apparent-size store/packs 2>/dev/null | cut -f1); true")


class Fail(Exception):
    pass


class Unit:
    def __init__(self, case, unit):
        self.case, self.unit = case, unit
        self.dir = RESULTS / f"ovnfs-{case}"
        self.ctr = f"fsh-lf-ov-{case.lower()}"
        if unit == "open":
            if self.dir.exists():
                raise Fail("results exist; never overwritten")
            self.dir.mkdir(parents=True)
            self.state = {"arm": "ovnfs", "case": case, "workload": largefile.VERSION,
                          "spec": largefile.CASES[case], "image": IMAGE, "steps": [],
                          "probes": [], "calls": [], "status": "open"}
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

    def call(self, label, argv, check=True):
        if time.monotonic() - self.started > UNIT_BUDGET_S:
            raise Fail(f"unit budget spent before {label}")
        seq = len(self.state["calls"]) + 1
        t0 = time.monotonic_ns()
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=CALL_TIMEOUT_S)
            code, out, err = p.returncode, p.stdout, p.stderr
        except subprocess.TimeoutExpired as e:
            code = "timeout"
            out = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            err = e.stderr.decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        wall = time.monotonic_ns() - t0
        with open(self.dir / "events.jsonl", "a") as f:
            f.write(json.dumps({"seq": seq, "label": label, "argv": argv[:8], "exit": code,
                                "wall_ns": wall, "stdout": out[-4000:], "stderr": err[-2000:],
                                "unit": self.unit}) + "\n")
        self.state["calls"].append({"seq": seq, "label": label, "wall_ns": wall, "exit": code})
        if check and code != 0:
            raise Fail(f"{label}: exit {code}: {err.strip()[-300:]}")
        return out, wall

    def ov(self, label, *args, cwd=None):
        argv = ["docker", "exec", "-e", "OVNFS_STATE=/data/state"]
        if cwd:
            argv += ["-w", cwd]
        return self.call(label, argv + [self.ctr, *args])

    def probe(self, label):
        out, _ = self.ov(f"probe_{label}", "sh", "-c", PROBE)
        lines = [ln.split() for ln in out.strip().split("\n") if ln.strip()]
        rec = {"label": label, "allocated_bytes": int(lines[0][0]), "apparent_bytes": int(lines[1][0]),
               "parts": {}}
        for p in lines[2:]:
            if p[0] in ("objects_files", "objects_apparent", "packs_apparent"):
                rec[p[0]] = int(p[1]) if len(p) > 1 and p[1].isdigit() else 0
            else:
                rec["parts"][p[1]] = int(p[0])
        self.state["probes"].append(rec)
        return rec

    def open(self):
        self.call("docker_run", ["docker", "run", "-d", "--name", self.ctr, "--device", "/dev/fuse",
                                 "--cap-add", "SYS_ADMIN", "--security-opt", "apparmor=unconfined",
                                 "-v", f"{self.ctr}:/data", "--entrypoint", "sleep", IMAGE, "infinity"])
        self.state["owned"] = {"container": self.ctr, "volume": self.ctr}
        self.save()
        self.ov("mkdir", "mkdir", "-p", "/data/src", "/opt/lf")
        self.call("copy_script", ["docker", "cp", str(HERE / "largefile.py"), f"{self.ctr}:{SCRIPT}"])
        # the container's Python 3.11 cannot generate 500 MiB in one randbytes call; the host made
        # the same seeded bytes (largefile.py gen), so they are copied in instead (not timed as gen)
        src = Path(os.environ["LF_BASE"]) / self.case / f"{self.case}.bin"
        _, self.state["copy_base_ns"] = self.call("copy_base", ["docker", "cp", str(src), f"{self.ctr}:/data/src/{self.case}.bin"])
        self.ov("daemon_start", "ovnfs", "start")
        self.probe("floor")
        out, self.state["import_ns"] = self.ov("import", "ovnfs", "--json", "new", "--name", "main",
                                               "--rule", "source *", cwd="/data/src")
        self.state["import_reply"] = json.loads(out)
        self.probe("import")
        _, self.state["branch_open_ns"] = self.ov("new_b01", "ovnfs", "--json", "new", "--name", "b01",
                                                  "--rule", "source *", cwd="/data/src")
        self.probe("branch")

    def steps(self, first, last):
        done = len(self.state["steps"])
        if first != done + 1:
            raise Fail(f"next step is {done + 1}, not {first}")
        if last > largefile.CASES[self.case]["commits"]:
            raise Fail("past the last commit")
        for k in range(first, last + 1):
            out, we = self.ov(f"apply_{k}", "python3", SCRIPT, "apply", self.case, str(k), ".",
                              cwd=CHECKOUT)
            sout, wc = self.ov(f"snap_{k}", "ovnfs", "--json", "snap", "b01", "--wait")
            snap = json.loads(sout)["snapshot"]
            rec = {"step": k, "apply_ns": we, "snap_ns": wc, "snapshot": snap["id"],
                   "edit": json.loads(out)}
            rec["probe"] = self.probe(f"after_{k}")
            self.state["steps"].append(rec)
            self.save()

    def verify(self):
        expected = largefile.expect(self.case)[-1]
        if len(self.state["steps"]) != largefile.CASES[self.case]["commits"]:
            raise Fail("not every step has run")
        snap = self.state["steps"][-1]["snapshot"]
        _, self.state["verify_open_ns"] = self.ov("vnew", "ovnfs", "--json", "new", "--name", "v",
                                                  "--from", snap)
        out, self.state["verify_read_ns"] = self.ov("vsha", "python3", SCRIPT, "sha", ".",
                                                    cwd="/root/checkouts/v")
        got = json.loads(out).get(f"{self.case}.bin", {})
        self.ov("vrm", "ovnfs", "rm", "v")
        self.state["verification"] = {"expected": expected, "got": got,
                                      "result": "PASS" if got.get("sha256") == expected["sha256"] else "FAIL"}

    def close(self):
        self.ov("daemon_stop", "ovnfs", "stop")
        self.probe("final")
        self.call("docker_rm", ["docker", "rm", "-f", self.ctr])
        self.call("volume_rm", ["docker", "volume", "rm", self.ctr])
        self.state["owned_released"] = True

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
        last = self.state["probes"][-1] if self.state["probes"] else {}
        print(json.dumps({"unit": self.unit, "elapsed_s": round(time.monotonic() - self.started, 1),
                          "steps": len(self.state["steps"]),
                          "verification": self.state.get("verification", {}).get("result"),
                          "last_probe": {k: last.get(k) for k in ("label", "allocated_bytes",
                                                                    "objects_files", "packs_apparent",
                                                                    "objects_apparent")}}))
        return 0


def main(argv):
    if len(argv) < 2 or argv[0] not in largefile.CASES or argv[1] not in ("open", "steps", "verify", "close"):
        print(__doc__)
        return 2
    return Unit(argv[0], argv[1]).run(argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
