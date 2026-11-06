#!/usr/bin/env python3
"""fs-storage-quick: the ≤120 s per backend storage subset (Docker only).

  run.py run        --environment E --cache C [--case Qn ...] [--backend B ...]
                    [--late-probe-wait-s 75 [--attribution DIR]] [--defer-release] [--repeat N]
  run.py late-probe --environment E --cache C [--wait-s 75] [--attribution DIR] [--keep]
  run.py release    --environment E --cache C
  run.py finish     --environment E --cache C
  run.py createdb   --environment E --cache C
  run.py export     --cache C --output rows.json
  run.py compare    --baseline B.json --candidate (C | rows.json) [--output md|json] [--out FILE]

Rows run serially, all SQLite rows then all PostgreSQL rows (so each backend's
matrix wall is one interval), one fresh Store per row, one attempt per row:
a registered row is never rerun. ``--late-probe-wait-s`` keeps every row's
Store after the row, waits once after the matrix (outside the 120 s budget),
re-probes each Store as ``late`` (SQLite after the worker's idle close,
PostgreSQL after autovacuum had a chance), optionally collects DIAGNOSTIC
per-table attribution, then releases the Stores.
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "shared" / "src"))
sys.path.insert(0, str(HERE))
import cases  # noqa: E402
import measure  # noqa: E402
import results  # noqa: E402
import rows  # noqa: E402
import storage  # noqa: E402

BACKENDS = ("sqlite", "postgresql")
runner = storage.load_runner(cases)


def row_id(case, backend, repeat=1):
    return f"{case}/docker/{backend}" + (f"/r{repeat}" if repeat > 1 else "")


def db_key(case, backend, repeat=1):
    return f"{case}/{backend}" + (f"/r{repeat}" if repeat > 1 else "")


def store_name(config, case, backend, repeat=1):
    tag = {"sqlite": "s", "postgresql": "p"}[backend]
    return f"{config['campaign_id']}-{case.lower()}{tag}" + (f"r{repeat}" if repeat > 1 else "")


def preflight(config, selected):
    """Identity and capacity checks before the first row (outside the timed matrix)."""
    problems = []
    cli = Path(config["cli"])
    if not cli.is_absolute() or not cli.is_file():
        problems.append("CLI missing or not absolute")
    elif runner.digest(cli) != config.get("artifacts", {}).get("cli_sha256"):
        problems.append("CLI hash differs from artifacts.cli_sha256")
    empty = Path(config["empty_source"])
    if not empty.is_dir() or any(empty.iterdir()):
        problems.append("empty source fixture missing or not empty")
    home = Path(config["home"])
    if not home.is_dir() or (home.stat().st_mode & 0o777) != 0o700:
        problems.append("LAYERFS_HOME missing or not mode 0700")
    if not cases.PINS_SHA256:
        problems.append("no pins.json matching gen.py/model.py (run src/pin.py)")
    if any(backend == "postgresql" for _, backend, _ in selected):
        if not os.environ.get(config.get("postgresql", {}).get("password_env", "")):
            problems.append("PostgreSQL password environment variable unset")
        for case, backend, repeat in selected:
            url = config.get("postgresql", {}).get("databases", {}).get(db_key(case, backend, repeat))
            if backend == "postgresql" and (not url or not storage.safe_database_url(url)):
                problems.append(f"no password-free database URL for {db_key(case, backend, repeat)}")
    env = dict(os.environ, **config.get("environment", {}), LAYERFS_HOME=config["home"],
               LAYERFS_CONSTRUCTION_WORKERS="1")
    got = measure.run_command([config["cli"], "machine", "get", config["machines"]["docker"]["name"]],
                              measure.Deadline.after(30), env=env)
    try:
        machine = json.loads(got["stdout"])
        image = config["artifacts"].get("sandbox_image", "").split()[0]
        if machine.get("image") != image:
            problems.append(f"docker machine image {machine.get('image')} != artifacts.sandbox_image {image}")
        if machine.get("state") != "running":
            problems.append(f"docker machine is {machine.get('state')}")
    except ValueError:
        problems.append("machine get gave no JSON")
    free = rows.docker_free_bytes(config["artifacts"]["base_image"])
    minimum = config.get("docker_min_free_bytes", 20 * 2**30)
    if free is None or free < minimum:
        problems.append(f"Docker guest free space {free} B < {minimum} B (capacity, not a product result)")
    return problems


def q6_context(config):
    state = cases.load_base(config["base_dir"])
    plan = cases.q6_plan(state)
    pinned = cases.PINS.get("q6", {})
    for key in ("lane_head", "shared_head", "lane_check", "shared_check"):
        if pinned.get(key) != plan[key]:
            raise SystemExit(f"Q6 {key} differs from pins.json")
    return plan


def run_one(campaign, case, backend, repeat, verify, defer, q6):
    config = campaign.config
    key = row_id(case, backend, repeat)
    if key in campaign.state["rows"]:
        raise runner.Failure(f"{key}: attempt already registered; no replay")
    name = store_name(config, case, backend, repeat)
    row = {
        "id": key, "cell": case, "case": case, "machine": "docker", "backend": backend, "repeat": repeat,
        "store": name, "pending": None, "uncertain": False, "execution": "NOT_RUN",
        "verification": "NOT_RUN", "cleanup": "NOT_RUN", "correctness": "UNVERIFIED",
        "performance": "INELIGIBLE", "workload": cases.provenance(case, q6), "policy": storage.POLICY,
        "registered_ns": time.time_ns(),
    }
    campaign.state["rows"][key] = row
    campaign.state.setdefault("attempt_sequence", []).append({"row": key, "registered_ns": row["registered_ns"]})
    campaign.persist()
    url = config.get("postgresql", {}).get("databases", {}).get(db_key(case, backend, repeat))
    spec = cases.spec(case, backend, name, config, url, q6)
    spec["defer_release"] = defer
    row["init_logical"] = spec.get("init_logical", 0)
    rows.run_row(campaign, row, spec, verify=verify)
    campaign.persist()
    return row


def load_rows_json(path_or_cache):
    path = Path(path_or_cache)
    if path.is_dir():
        state = json.loads((path / "campaign.json").read_text())
        config = json.loads((path / "environment.json").read_text())
        return export_state(state, config)
    return json.loads(path.read_text())


def export_state(state, config):
    logical = {r["case"]: r.get("init_logical", 0) for r in state.get("rows", {}).values()}
    out = results.export(state, config, cases, logical)
    out["harness"] = state.get("harness")
    return out


def harness_identity():
    import hashlib
    import subprocess

    files = sorted(p for p in (HERE.parent).rglob("*") if p.is_file() and p.suffix in (".py", ".json", "")
                   and "__pycache__" not in p.parts and p.parent.name != "baseline")
    shared = [HERE.parents[1] / "shared" / "src" / n for n in ("storage.py", "runner.py", "measure.py")]
    digest = hashlib.sha256()
    for p in files + shared:
        digest.update(p.name.encode() + hashlib.sha256(p.read_bytes()).digest())
    try:
        head = subprocess.run(["git", "-C", str(HERE), "rev-parse", "HEAD"], capture_output=True, text=True,
                              timeout=10).stdout.strip()
        dirty = bool(subprocess.run(["git", "-C", str(HERE.parent), "status", "--porcelain", "."],
                                    capture_output=True, text=True, timeout=10).stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        head, dirty = None, None
    return {"git_head": head, "suite_dirty": dirty, "sources_sha256": digest.hexdigest()}


def createdb(config, cache):
    """Pre-create each row's empty database in the owned server (one attempt each)."""
    pg = config["postgresql"]
    ledger = Path(cache) / "infrastructure.jsonl"
    failed = False
    for key, url in sorted(pg.get("databases", {}).items()):
        name = url.rsplit("/", 1)[1]
        user = url.split("://", 1)[1].split("@", 1)[0]
        argv = ["docker", "exec", pg["server_container"], "createdb", "-U", user, name]
        with ledger.open("a") as stream:
            stream.write(json.dumps({"event": "intent", "argv": argv, "time_ns": time.time_ns()}) + "\n")
        got = measure.run_command(argv, measure.Deadline.after(30))
        with ledger.open("a") as stream:
            stream.write(json.dumps({"event": "result", "argv": argv, **{k: got.get(k) for k in (
                "process_exit", "stdout", "stderr", "elapsed_ns")}}) + "\n")
        print(json.dumps({"database": key, "name": name, "exit": got.get("process_exit"),
                          "stderr": (got.get("stderr") or "").strip()[:200]}))
        failed |= got.get("process_exit") != 0
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("run", "late-probe", "release", "finish", "createdb", "export", "compare"))
    parser.add_argument("--environment")
    parser.add_argument("--cache")
    parser.add_argument("--case", choices=cases.CASE_IDS, action="append")
    parser.add_argument("--backend", choices=BACKENDS, action="append")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--no-verify", action="store_true")
    parser.add_argument("--defer-release", action="store_true")
    parser.add_argument("--late-probe-wait-s", type=float)
    parser.add_argument("--wait-s", type=float, default=75.0)
    parser.add_argument("--attribution", metavar="DIR",
                        help="DIAGNOSTIC per-table attribution into private DIR (owner decision pending)")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--out")
    parser.add_argument("--baseline")
    parser.add_argument("--candidate")
    args = parser.parse_args(argv)

    if args.action == "compare":
        baseline = json.loads(Path(args.baseline).read_text())
        candidate = load_rows_json(args.candidate)
        result = results.compare(baseline, candidate)
        text = (json.dumps(result, indent=1) if args.output == "json"
                else results.compare_markdown(result, baseline, candidate))
        if args.out:
            Path(args.out).write_text(text)
        print(text)
        return 1 if result["regressions"] or result["not_comparable"] or result["missing"] else 0
    if args.action == "export":
        data = load_rows_json(args.cache)
        text = json.dumps(data, indent=1, sort_keys=False) + "\n"
        if args.output:
            Path(args.output).write_text(text)
        else:
            print(text)
        return 0

    config = json.loads(Path(args.environment).read_text())
    if not re.fullmatch(r"[a-z0-9-]{1,16}", config["campaign_id"]):
        print("campaign_id must be 1–16 lowercase letters, digits or hyphens", file=sys.stderr)
        return 2
    if args.action == "createdb":
        Path(args.cache).mkdir(parents=True, exist_ok=True)
        return createdb(config, args.cache)
    with runner.campaign_lock(args.cache):
        campaign = runner.Campaign(config, args.cache)
        (Path(args.cache) / "environment.json").write_text(json.dumps(config, indent=1, sort_keys=True) + "\n")
        if args.action == "late-probe":
            done = rows.late_probe(campaign, args.wait_s, args.attribution, keep=args.keep)
            print(json.dumps([{"id": r["id"], "late": r.get("late_probe"), "cleanup": r["cleanup"]} for r in done]))
            return 0
        if args.action in ("release", "finish"):
            for row in rows.deferred_rows(campaign):
                rows.release(campaign, row)
            if args.action == "release":
                return 0
            receipt = campaign.finish()
            print(json.dumps({k: receipt[k] for k in ("cleanup", "retained_rows")}))
            return 0 if receipt["cleanup"] == "COMPLETE" else 1
        # run
        selected = [
            (case, backend, args.repeat)
            for backend in BACKENDS if backend in (args.backend or BACKENDS)
            for case in cases.CASE_IDS if case in (args.case or cases.CASE_IDS)
        ]
        problems = preflight(config, selected)
        if problems:
            print(json.dumps({"execution": "NOT_RUN", "reasons": problems}))
            return 1
        q6 = q6_context(config) if any(case == "Q6" for case, _, _ in selected) else None
        campaign.state.setdefault("harness", harness_identity())
        campaign.persist()
        defer = bool(args.defer_release or args.late_probe_wait_s is not None)
        failed = False
        for case, backend, repeat in selected:
            if row_id(case, backend, repeat) in campaign.state["rows"]:
                continue  # already attempted: never rerun, resume with the next row
            row = run_one(campaign, case, backend, repeat, not args.no_verify, defer, q6)
            summary = results.row_summary(row, row.get("init_logical", 0))
            print(json.dumps({
                "id": row["id"], "execution": row["execution"], "verification": row["verification"],
                "cleanup": row["cleanup"], "net_bytes": summary.get("net_bytes"),
                "wall_s": summary["diagnostics"]["row_wall_s"], "reason": row.get("reason"),
            }), flush=True)
            failed |= row["execution"] != "PASS" or row["verification"] == "FAIL"
            if row.get("uncertain"):
                break
        walls = export_state(campaign.state, config)["wall_ineligible"]
        print(json.dumps({"matrix_wall_s_ineligible": {k: v["matrix_wall_s"] for k, v in walls.items()}}))
        if args.late_probe_wait_s is not None:
            done = rows.late_probe(campaign, args.late_probe_wait_s, args.attribution, keep=args.keep)
            for r in done:
                print(json.dumps({"id": r["id"], "late": r.get("late_probe"), "cleanup": r["cleanup"]}), flush=True)
        return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
