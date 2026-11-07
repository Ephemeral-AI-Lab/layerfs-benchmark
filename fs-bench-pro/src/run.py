#!/usr/bin/env python3
"""fs-bench-pro export family: setup, one sample per invocation, receipts.

    run.py setup   --env environments.local.json
    run.py run     --env environments.local.json --case E01 --machine lima
    run.py cleanup --env environments.local.json

Every LayerFS step is the public CLI (absolute path from the env file). One
`run` is one sample of one case on one machine: cold control (outside the
timer), the timed `project export --progress`, independent verification
(outside the timer), output removal, and an append-only receipt under
results/<run-id>/. Nothing is retried; a failure keeps its receipt.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cases  # noqa: E402
import cold  # noqa: E402
import fixture  # noqa: E402

ROOT = HERE.parent
# 2: the budget judges the timed export alone; cold control and verification
# are reported beside it (receipt 20261107T231724Z-4dd18c ran under 1).
# 3: stderr lines that are not progress events are kept verbatim (under 2 a
# final refusal line was parsed and dropped: 20261107T231818Z-c7a8fa).
HARNESS = 3


def load_env(path: str) -> dict:
    env = json.loads(Path(path).read_text())
    for key in ("cli", "home", "xdg_cache", "fixtures", "out", "machines", "native"):
        if key not in env:
            sys.exit(f"{path}: missing `{key}`")
    return env


def process_env(env: dict) -> dict:
    e = dict(os.environ)
    e.update(
        LAYERFS_HOME=env["home"],
        XDG_CACHE_HOME=env["xdg_cache"],
        LAYERFS_CONSTRUCTION_WORKERS="1",
    )
    return e


def cli(env: dict, *args: str, timeout: float = 120) -> dict:
    out = subprocess.run(
        [env["cli"], *args], capture_output=True, text=True, timeout=timeout, env=process_env(env)
    )
    if out.returncode != 0:
        raise RuntimeError(f"layerfs {' '.join(args)}: rc={out.returncode} {out.stderr.strip()[:400]}")
    return json.loads(out.stdout) if out.stdout.strip() else {}


def store_of(env: dict, machine: str) -> str:
    return env["machines"][machine]["store"] if machine != "native" else env["native"]["store"]


def setup(env: dict) -> None:
    """Untimed: one Store per machine holding both fixtures, inited on native, then pushed."""
    for machine in cases.MACHINES:
        store = store_of(env, machine)
        cli(env, "store", "create", store)
        for kind in cases.FIXTURES:
            cli(env, "project", "init", f"{store}/{kind}", str(Path(env["fixtures"]) / kind))
        if machine != "native":
            cli(env, "store", "push", store, env["machines"][machine]["machine"], timeout=300)
            cold.install_tool(env, machine, Path(env["guest_tool"]))
    print(json.dumps(cli(env, "store", "list"), indent=1))


def timed_export(env: dict, project: str, dest: Path) -> dict:
    """The timed phase: one CLI process; progress lines stamped as they arrive."""
    events, stamps = [], []
    started = time.monotonic_ns()
    proc = subprocess.Popen(
        [env["cli"], "project", "export", project, str(dest), "--progress"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=process_env(env),
    )

    def read_progress() -> None:
        for line in proc.stderr:
            stamps.append(time.monotonic_ns() - started)
            events.append(line.rstrip("\n"))

    reader = threading.Thread(target=read_progress, daemon=True)
    reader.start()
    try:
        stdout, _ = proc.communicate(timeout=cases.BUDGET_S * 4)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, _ = proc.communicate()
    wall_ns = time.monotonic_ns() - started
    reader.join(timeout=5)
    progress = []
    for stamp, line in zip(stamps, events):
        try:
            value = json.loads(line)["progress"]
            progress.append({"t_ms": round(stamp / 1e6, 2), "phase": value["phase"], "bytes": value["bytes"]})
        except (ValueError, KeyError, TypeError):
            progress.append({"t_ms": round(stamp / 1e6, 2), "line": line[:2000]})
    result = None
    try:
        result = json.loads(stdout) if stdout.strip() else None
    except ValueError:
        pass
    return {
        "rc": proc.returncode, "wall_ms": round(wall_ns / 1e6, 2), "result": result,
        "stdout": None if result is not None else stdout[:2000], "progress": progress,
    }


def phase_ms(progress: list, phase: str, last: bool = False):
    hits = [p["t_ms"] for p in progress if p.get("phase") == phase]
    return (hits[-1] if last else hits[0]) if hits else None


def run(env: dict, case_id: str, machine: str) -> dict:
    case = cases.CASES[case_id]
    kind = case["fixture"]
    expect = cases.FIXTURES[kind]
    store = store_of(env, machine)
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:6]
    out_dir = Path(env["out"]) / run_id
    receipts = ROOT / "results" / run_id
    receipts.mkdir(parents=True)
    out_dir.mkdir(parents=True)
    dest = out_dir / "exported"
    started = time.monotonic()
    receipt = {
        "family": cases.FAMILY, "harness": HARNESS, "workload": cases.WORKLOAD_VERSION, "case": case_id, "machine": machine,
        "store": store, "project": f"{store}/{kind}", "fixture": kind, "run_id": run_id,
        "identity": env.get("identity", {}), "load_1m_before": os.getloadavg()[0],
    }
    try:
        receipt["cold"] = cold.evict(env, machine, store)
    except Exception as error:  # the control failed: the row cannot be cold
        receipt["cold"] = {"cold": False, "error": str(error)[:400]}
    receipt["export"] = timed_export(env, f"{store}/{kind}", dest)
    receipt["load_1m_after"] = os.getloadavg()[0]
    res = receipt["export"]["result"] or {}
    counts_ok = all(res.get(k) == expect[k] for k in ("files", "directories", "symlinks", "bytes"))
    receipt["execution"] = "PASS" if receipt["export"]["rc"] == 0 and counts_ok else "FAIL"
    v0 = time.monotonic()
    if dest.is_dir():
        got = fixture.manifest(dest)
        receipt["verification"] = {"status": "PASS" if got == expect["manifest"] else "FAIL", "manifest": got}
    else:
        receipt["verification"] = {"status": "FAIL", "reason": "no exported folder"}
    receipt["verification"]["wall_s"] = round(time.monotonic() - v0, 3)
    left = [p.name for p in out_dir.iterdir() if p.name.startswith(".layerfs-export-")]
    receipt["staging_left"] = left
    shutil.rmtree(out_dir, ignore_errors=True)
    receipt["complete_s"] = round(time.monotonic() - started, 3)
    receipt["performance"] = verdict(receipt)
    wall_s = receipt["export"]["wall_ms"] / 1000
    receipt["metrics"] = {
        "wall_ms": receipt["export"]["wall_ms"],
        "prepare_ms": phase_ms(receipt["export"]["progress"], "prepare"),
        "finalize_ms": phase_ms(receipt["export"]["progress"], "finalize", last=True),
        "mb_per_s": round(expect["bytes"] / 1e6 / wall_s, 1) if receipt["execution"] == "PASS" else None,
        "files_per_s": round(expect["files"] / wall_s, 1) if receipt["execution"] == "PASS" else None,
    }
    (receipts / "receipt.json").write_text(json.dumps(receipt, indent=1))
    return receipt


def verdict(receipt: dict) -> str:
    """QUALIFIED only with execution and verification PASS, a shown cold Store and the budget met.

    The budget judges the timed export command; the cold control's cost is
    enforcement overhead, reported as `cold.control_s`, never case time.
    """
    if receipt["execution"] != "PASS" or receipt["verification"]["status"] != "PASS":
        return "FAIL"
    if not receipt["cold"].get("cold"):
        return "INELIGIBLE"
    budget = cases.DECLARED_EXCEPTIONS.get(f"{receipt['case']}/{receipt['machine']}", cases.BUDGET_S)
    if receipt["export"]["wall_ms"] / 1000 > budget or receipt["verification"]["wall_s"] > cases.VERIFY_BUDGET_S:
        return "OVER_BUDGET"
    return "QUALIFIED"


def cleanup(env: dict) -> None:
    """Removes the Stores this family made; machines, images and fixtures are the caller's."""
    for machine in cases.MACHINES:
        try:
            cli(env, "store", "remove", store_of(env, machine), timeout=300)
            print("removed", store_of(env, machine))
        except RuntimeError as error:
            print("KEPT", store_of(env, machine), error)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("setup", "run", "cleanup"))
    parser.add_argument("--env", required=True)
    parser.add_argument("--case", choices=sorted(cases.CASES))
    parser.add_argument("--machine", choices=cases.MACHINES)
    args = parser.parse_args()
    env = load_env(args.env)
    if args.command == "setup":
        setup(env)
    elif args.command == "cleanup":
        cleanup(env)
    else:
        if not (args.case and args.machine):
            parser.error("run needs --case and --machine")
        receipt = run(env, args.case, args.machine)
        m = receipt["metrics"]
        print(f"{receipt['run_id']} {args.case} {args.machine}: execution {receipt['execution']}, "
              f"verification {receipt['verification']['status']}, performance {receipt['performance']}, "
              f"wall {m['wall_ms']} ms, {m['mb_per_s']} MB/s, {m['files_per_s']} files/s, "
              f"cold={receipt['cold'].get('cold')}, complete {receipt['complete_s']} s")


if __name__ == "__main__":
    main()
