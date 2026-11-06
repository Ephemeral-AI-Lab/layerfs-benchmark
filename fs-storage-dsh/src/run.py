#!/usr/bin/env python3
"""fs-storage-dsh rows on the shared storage driver (Docker only).

    run.py run    --environment E --cache C --case D10 --backend sqlite --output O
    run.py finish --environment E --cache C

One fresh Store per row: create/connect, `project init` of an empty folder,
`store push` to Docker for SQLite, empty-Store floor probe, fork `lane`; one
Sandbox and Workspace; for each selected state one Exec `apply.py p k` and one
Workspace Commit; unmount and close; final Store probe at the quiesced
boundary and the paged `commit list`; then `verify.py <last>` once in a fresh
Sandbox on the branch head. Every command has its own deadline of at most
120 s; nothing is retried. Custody is `shared/src/runner.py`'s Campaign; the
driver is `shared/src/storage.py`.
"""

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

SRC = Path(__file__).resolve().parent
SHARED = SRC.parents[1] / "shared" / "src"
sys.path[:0] = [str(SRC), str(SHARED)]

import cases  # noqa: E402
import measure  # noqa: E402
import storage  # noqa: E402

RUNNER = {"__file__": str(SRC / "run.py"), "__name__": "fs_storage_dsh_runner"}
exec(compile((SHARED / "runner.py").read_bytes(), str(SHARED / "runner.py"), "exec"), RUNNER)  # noqa: S102
Campaign, Failure, campaign_lock = RUNNER["Campaign"], RUNNER["Failure"], RUNNER["campaign_lock"]

MACHINE = "docker"
BACKENDS = ("sqlite", "postgresql")
SUITE = SRC.parent
HARNESS = {
    "run.py": SRC / "run.py",
    "cases.py": SRC / "cases.py",
    "apply.py": SUITE / "image" / "apply.py",
    "verify.py": SUITE / "image" / "verify.py",
    "runner.py": SHARED / "runner.py",
    "measure.py": SHARED / "measure.py",
    "storage.py": SHARED / "storage.py",
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def harness_hashes():
    return {name: digest(path) for name, path in HARNESS.items()}


def matrix():
    return [f"{case}/{MACHINE}/{backend}" for case in cases.CASE_IDS for backend in BACKENDS]


def check_config(config):
    if not re.fullmatch(r"[a-z0-9-]{1,24}", config["campaign_id"]):
        raise Failure("campaign_id must contain 1–24 lowercase letters, digits or hyphens")
    if not re.fullmatch(r"[a-f0-9]{40}", config["source_sha"]):
        raise Failure("source_sha must be a full commit identity")
    if not Path(config["home"]).is_absolute():
        raise Failure("LayerFS home must be absolute")
    timeout = config.get("command_timeout_s", 110)
    if not 0 < timeout <= storage.MAX_COMMAND_S:
        raise Failure("command_timeout_s must be in (0, 120]")


def spec_for(campaign, row, case):
    config = campaign.config
    store, project = row["store"], row["store"] + "/p"
    timeout = config.get("command_timeout_s", 110)
    entry = {"name": store, "backend": row["backend"], "projects": [{"project": project, "source": config["empty_source"]}]}
    if row["backend"] == "postgresql":
        entry["url"] = config["postgresql"]["databases"][f"{row['cell']}/{MACHINE}"]
    steps = [
        {"op": "sandbox", "project": project, "sandbox": row["sandbox"], "timeout_s": timeout},
        {"op": "mount", "sandbox": row["sandbox"], "branch": "lane", "name": "dsh", "as": "w", "timeout_s": timeout},
    ]
    for (before, after), command in zip(case["steps"], case["commands"]):
        steps.append({"op": "exec", "ws": "w", "command": command, "timeout_s": timeout})
        steps.append({"op": "commit", "ws": "w", "label": f"state {after}", "timeout_s": timeout})
    steps += [
        {"op": "unmount", "ws": "w", "timeout_s": timeout},
        {"op": "close", "sandbox": row["sandbox"], "timeout_s": timeout},
    ]
    final = case["final_state"]

    def check(result):
        row["verify_result"] = cases.parse_verify(result.get("stdout", ""), final)

    allocated = None
    if row["backend"] == "sqlite":
        allocated = {
            "volume": config["storage"].get("docker_volume") or storage.docker_volume_for(config["home"], MACHINE),
            "image": config["storage"]["probe_image"],
        }
    return {
        "prefix": row["sandbox"],
        "machine": config["machines"][MACHINE].get("name", MACHINE),
        "timeout_s": timeout,
        "stores": [entry],
        "branches": [{"project": project, "name": "lane", "from": "main"}],
        "steps": steps,
        "collect": [{"project": project, "branch": "lane"}],
        "verify": [{"project": project, "branch": "lane", "command": case["verify_command"], "check": check, "timeout_s": timeout}],
        "allocated": allocated,
        "password_env": config.get("postgresql", {}).get("password_env"),
    }


def apply_results(row, case):
    """apply.py's JSON lines from the retained Exec results, in order."""
    outputs = []
    for command in row.get("commands", []):
        if command.get("phase", "").endswith("_exec") and command.get("process_exit") == 0:
            value = json.loads(command["stdout"])
            outputs.append(value.get("stdout", ""))
    return [cases.parse_apply(text, a, b) for text, (a, b) in zip(outputs, case["steps"])]


def execute(campaign, case_id, backend, output, verify=True):
    selection = {"cell": case_id, "machine": MACHINE, "backend": backend, "id": f"{case_id}/{MACHINE}/{backend}"}
    row = campaign.row(selection)
    if row["execution"] != "NOT_RUN":
        raise Failure(f"{row['id']}: attempt already registered; no resampling")
    order = matrix()
    index = order.index(row["id"])
    prior = campaign.state.get("attempt_sequence", [])
    if prior and index < prior[-1]["matrix_index"]:
        raise Failure("row is earlier than the campaign cursor; keep D10 → D03, SQLite → PostgreSQL")
    output = Path(output)
    if output.exists():
        raise Failure("output directory already exists; retained evidence cannot be overwritten")
    output.mkdir(parents=True)
    case = cases.get_case(case_id)
    row.update(
        output=str(output.resolve()),
        harness_sha256=harness_hashes(),
        matrix_index=index,
        workload=case["provenance"],
        storage_policy=storage.POLICY,
    )
    campaign.state.setdefault("attempt_sequence", []).append(
        {"row": row["id"], "matrix_index": index, "harness_sha256": row["harness_sha256"], "registered_ns": time.time_ns()}
    )
    reason = campaign.prerequisite(row)
    if reason:
        row["reason"] = reason
        row["execution"] = "NOT_RUN"
        campaign.persist()
        campaign.receipt(row)
        return row
    row["preparation"] = "CONSUMED"
    campaign.persist()
    campaign.event("attempt", row=row["id"])
    storage.run_row(campaign, row, spec_for(campaign, row, case), verify=verify)
    try:
        row["apply_results"] = apply_results(row, case)
        if row["execution"] == "PASS" and len(row["apply_results"]) != len(case["steps"]):
            raise ValueError("apply.py results are incomplete")
    except (ValueError, KeyError) as error:
        row["execution"] = "FAIL"
        row["reason"] = f"apply result: {error}"
    commits = row.get("histories", [{}])[0].get("commits", []) if row.get("histories") else []
    if row["execution"] == "PASS" and len(commits) != len(case["steps"]):
        row["execution"] = "FAIL"
        row["reason"] = f"commit list has {len(commits)} Commits, expected {len(case['steps'])}"
    if commits:
        row["final_logical"] = commits[-1]["logical"]
        row["sum_logical"] = sum(c["logical"] for c in commits)
    row["summary"] = storage.row_summary(row)
    campaign.persist()
    campaign.receipt(row)
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "finish"))
    parser.add_argument("--environment", required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--case", choices=cases.CASE_IDS)
    parser.add_argument("--backend", choices=BACKENDS)
    parser.add_argument("--output")
    parser.add_argument("--no-verify", action="store_true")
    args = parser.parse_args(argv)
    campaign = None
    try:
        config = json.loads(Path(args.environment).read_text())
        check_config(config)
        with campaign_lock(args.cache):
            campaign = Campaign(config, args.cache)
            if args.action == "finish":
                result = campaign.finish()
                print(json.dumps(result))
                return 0 if result["cleanup"] == "COMPLETE" else 1
            if not (args.case and args.backend and args.output):
                raise Failure("run needs --case, --backend and a fresh --output")
            row = execute(campaign, args.case, args.backend, args.output, verify=not args.no_verify)
            summary = row.get("summary") or {}
            print(
                json.dumps(
                    {
                        "id": row["id"],
                        "execution": row["execution"],
                        "verification": row["verification"],
                        "cleanup": row["cleanup"],
                        "net_bytes": summary.get("net_bytes"),
                        "sum_new_stored": summary.get("sum_new_stored"),
                        "reason": row.get("reason"),
                    }
                )
            )
            ok = row["execution"] == "PASS" and row["verification"] in ("PASS", "SKIPPED") and row["cleanup"] == "COMPLETE"
            return 0 if ok else 1
    except (Failure, OSError, ValueError, KeyError) as error:
        if campaign is not None:
            campaign.event("terminal_failure", reason=str(error))
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
