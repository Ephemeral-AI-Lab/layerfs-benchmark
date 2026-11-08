#!/usr/bin/env python3
"""Run one already-built crate fixture process with private connection settings."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

p = argparse.ArgumentParser()
p.add_argument("--state", type=Path, required=True)
p.add_argument("--timeout", type=int, default=100)
p.add_argument("command", nargs=argparse.REMAINDER)
a = p.parse_args()
command = a.command[1:] if a.command[:1] == ["--"] else a.command
if not command or not 1 <= a.timeout <= 100:
    p.error("a command and a timeout between 1 and 100 seconds are required")
env = dict(os.environ)
env.update(json.loads((a.state / "environment.json").read_text()))
started = time.time()
result = subprocess.run(command, env=env, timeout=a.timeout)
receipt = {"command": command, "started_unix": started, "elapsed_seconds": time.time()-started, "exit_code": result.returncode, "fixture": str(a.state), "source": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "profile": "Disposable", "timing_claim": "none; correctness qualification only"}
if Path(command[0]).is_file():
    receipt["binary_sha256"] = hashlib.sha256(Path(command[0]).read_bytes()).hexdigest()
path = a.state / f"run-{int(started*1000000)}.json"
path.write_text(json.dumps(receipt, indent=2)+"\n")
print(path)
raise SystemExit(result.returncode)
