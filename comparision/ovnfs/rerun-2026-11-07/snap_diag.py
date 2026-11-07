"""Diagnostic: time ovnfs snap/apply inside its container (see report.md).

Run inside a container with ovnfs started and checkout b01 created, with
/tmp/steps.json holding encoded model steps:  python3 /tmp/snap_diag.py
"""
import json, subprocess, time, os
env = dict(os.environ, OVNFS_STATE="/data/state")
def run(argv, cwd=None):
    t = time.monotonic_ns(); p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True)
    assert p.returncode == 0, (argv, p.stderr[-300:]); return (time.monotonic_ns() - t) / 1e6, p.stdout
steps = json.load(open("/tmp/steps.json"))
out = {"true": [], "ovnfs_version": [], "snap": [], "snap_nowait": [], "apply": []}
for _ in range(5):
    out["true"].append(run(["true"])[0]); out["ovnfs_version"].append(run(["ovnfs", "version"])[0])
co = "/root/checkouts/b01"
for k, enc in enumerate(steps):
    out["apply"].append(run(["python3", "/opt/fs-storage-history/model.py", "apply", enc], cwd=co)[0])
    if k < 10:
        out["snap"].append(run(["ovnfs", "--json", "snap", "b01", "--wait"])[0])
    else:
        out["snap_nowait"].append(run(["ovnfs", "--json", "snap", "b01"])[0])
print(json.dumps({k: [round(x, 1) for x in v] for k, v in out.items()}))
