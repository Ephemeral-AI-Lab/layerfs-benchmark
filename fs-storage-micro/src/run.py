#!/usr/bin/env python3
"""fs-storage-micro rows on the shared storage driver (Docker only).

  run.py run    --environment E --cache C (--case M0x --backend B | --matrix) [--repeat N]
  run.py finish --environment E --cache C

One fresh Store per row, serial, one attempt per row (no replay). A row id is
``<case>/docker/<backend>``; ``--repeat 2`` runs the determinism repeat
``<case>/docker/<backend>/r2`` on its own fresh Store.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "shared" / "src"))
sys.path.insert(0, str(HERE))
import cases  # noqa: E402
import storage  # noqa: E402

BACKENDS = ("sqlite", "postgresql")
runner = storage.load_runner(cases)


def row_id(case, backend, repeat=1):
    return f"{case}/docker/{backend}" + (f"/r{repeat}" if repeat > 1 else "")


def store_name(config, case, backend, repeat=1):
    tag = {"sqlite": "s", "postgresql": "p"}[backend]
    return f"{config['campaign_id']}-{case.lower()}{tag}" + (f"r{repeat}" if repeat > 1 else "")


def prerequisite(config, backend, key):
    cli = Path(config["cli"])
    if not cli.is_file() or runner.digest(cli) != config.get("artifacts", {}).get("cli_sha256"):
        return "pinned CLI missing or hash mismatch"
    if not config.get("machines", {}).get("docker", {}).get("ready"):
        return "docker machine not registered ready"
    empty = Path(config["empty_source"])
    if not empty.is_dir() or any(empty.iterdir()):
        return "empty source fixture missing or not empty"
    if not cases.ORACLE:
        return "no pinned oracle for this generator (run references.py and pin)"
    if backend == "postgresql":
        url = config.get("postgresql", {}).get("databases", {}).get(key)
        if not url or not storage.safe_database_url(url):
            return "pre-created PostgreSQL database URL missing or carries a password"
        import os

        if not os.environ.get(config["postgresql"].get("password_env", "")):
            return "PostgreSQL password environment variable unset"
    return None


def run_one(campaign, case, backend, repeat, verify=True):
    config = campaign.config
    key = row_id(case, backend, repeat)
    if key in campaign.state["rows"]:
        raise runner.Failure(f"{key}: attempt already registered; no replay")
    name = store_name(config, case, backend, repeat)
    db_key = f"{case}/{backend}" + (f"/r{repeat}" if repeat > 1 else "")
    row = {
        "id": key, "cell": case, "case": case, "machine": "docker", "backend": backend,
        "repeat": repeat, "store": name, "pending": None, "uncertain": False,
        "execution": "NOT_RUN", "verification": "NOT_RUN", "cleanup": "NOT_RUN",
        "correctness": "UNVERIFIED", "performance": "INELIGIBLE",
        "workload": cases.provenance(case), "policy": storage.POLICY,
        "registered_ns": time.time_ns(),
    }
    campaign.state["rows"][key] = row
    campaign.state.setdefault("attempt_sequence", []).append({"row": key, "registered_ns": row["registered_ns"]})
    campaign.persist()
    reason = prerequisite(config, backend, db_key)
    if reason:
        row["reason"] = reason
        row["cleanup"] = "COMPLETE"
        campaign.persist()
        return row
    url = config.get("postgresql", {}).get("databases", {}).get(db_key)
    storage.run_row(campaign, row, cases.spec(case, backend, name, config, url), verify=verify)
    row["summary"] = storage.row_summary(
        row, cases.REFERENCES.get(case), (cases.REFERENCES.get(case) or {}).get("whole_file_unique")
    )
    campaign.persist()
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("run", "finish"))
    parser.add_argument("--environment", required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--case", choices=cases.CASE_IDS, action="append")
    parser.add_argument("--backend", choices=BACKENDS, action="append")
    parser.add_argument("--matrix", action="store_true")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--no-verify", action="store_true")
    args = parser.parse_args(argv)
    config = json.loads(Path(args.environment).read_text())
    if not re.fullmatch(r"[a-z0-9-]{1,16}", config["campaign_id"]):
        print("campaign_id must be 1–16 lowercase letters, digits or hyphens", file=sys.stderr)
        return 2
    selected = [
        (case, backend)
        for case in cases.CASE_IDS if case in (args.case or cases.CASE_IDS)
        for backend in BACKENDS if backend in (args.backend or BACKENDS)
    ]
    if args.action == "run" and not args.matrix and len(selected) != 1:
        print("select one --case/--backend or use --matrix", file=sys.stderr)
        return 2
    with runner.campaign_lock(args.cache):
        campaign = runner.Campaign(config, args.cache)
        campaign.state.setdefault("storage_matrix", [row_id(c, b) for c in cases.CASE_IDS for b in BACKENDS])
        if args.action == "finish":
            receipt = campaign.finish()
            print(json.dumps({k: receipt[k] for k in ("cleanup", "retained_rows")}))
            return 0 if receipt["cleanup"] == "COMPLETE" else 1
        failed = False
        for case, backend in selected:
            if args.matrix and row_id(case, backend, args.repeat) in campaign.state["rows"]:
                continue  # already attempted: never rerun, resume with the next row
            row = run_one(campaign, case, backend, args.repeat, verify=not args.no_verify)
            summary = row.get("summary") or {}
            print(json.dumps({
                "id": row["id"], "execution": row["execution"], "verification": row["verification"],
                "cleanup": row["cleanup"], "net_bytes": summary.get("net_bytes"),
                "reason": row.get("reason"),
            }), flush=True)
            failed |= row["execution"] != "PASS" or row["verification"] == "FAIL"
            if row.get("uncertain"):
                break
        return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
