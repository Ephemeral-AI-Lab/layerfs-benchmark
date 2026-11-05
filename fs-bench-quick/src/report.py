#!/usr/bin/env python3
"""Report retained fs-bench-quick evidence without executing product operations."""

import argparse
import csv
import json
import os
from collections import Counter
from pathlib import Path

MACHINES = ("native", "docker", "lima", "apple-container")
BACKENDS = ("sqlite", "postgresql")
FIELDS = (
    "id",
    "execution",
    "performance",
    "verification",
    "correctness",
    "cleanup",
    "exec_ns",
    "commit_ns",
    "mount_ns",
    "unmount_ns",
    "prepare_ns",
    "cleanup_ns",
    "end_to_end_case_ns",
    "reason",
    "receipt",
)


def matrix():
    return [f"C{cell:02}/{machine}/{backend}" for cell in range(1, 13) for machine in MACHINES for backend in BACKENDS]


def load_rows(root):
    """Retain all 96 selections; duplicate attempts must be disambiguated by owner."""
    found = {}
    for path in sorted(root.rglob("receipt.json")):
        item = json.loads(path.read_text())
        identity = item.get("id")
        if identity not in matrix():
            continue
        if identity in found:
            raise ValueError(f"duplicate retained attempts for {identity}; select one campaign")
        phases = item.get("timings_ns", {})
        found[identity] = {
            "id": identity,
            "execution": item.get("execution", "NOT_RUN"),
            "performance": item.get("performance", "INELIGIBLE"),
            "verification": item.get("verification", "SKIPPED"),
            "correctness": item.get("correctness", "UNVERIFIED"),
            "cleanup": item.get("cleanup", "NOT_RUN"),
            "exec_ns": phases.get("exec"),
            "commit_ns": phases.get("commit"),
            "mount_ns": phases.get("measured_mount"),
            "unmount_ns": phases.get("unmount"),
            "prepare_ns": item.get("prepare_elapsed_ns"),
            "cleanup_ns": item.get("cleanup_elapsed_ns"),
            "end_to_end_case_ns": item.get("harness_elapsed_ns"),
            "reason": item.get("reason", ""),
            "receipt": str(path.relative_to(root)),
            "source_sha": item.get("source_sha"),
            "artifacts": item.get("artifacts", {}),
            "cache": item.get("cache", {}),
            "workload": item.get("workload", {}),
            "harness_sha256": item.get("harness_sha256", {}),
            "comparison_protocol_sha256": item.get("comparison_protocol_sha256"),
        }
    return [
        found.get(
            identity,
            {
                "id": identity,
                "execution": "NOT_RUN",
                "performance": "INELIGIBLE",
                "verification": "SKIPPED",
                "correctness": "UNVERIFIED",
                "cleanup": "NOT_RUN",
                "reason": "No retained attempt in this campaign",
                "receipt": "",
            },
        )
        for identity in matrix()
    ]


def comparable(left, right):
    required_artifacts = ("cli_sha256", "daemon_sha256", "linux_bundle_sha256", "profile")
    identities = ("workload", "harness_sha256", "comparison_protocol_sha256")
    return (
        left["execution"] == right["execution"] == "PASS"
        and left["performance"] == right["performance"] == "ELIGIBLE"
        and left.get("source_sha") == right.get("source_sha")
        and bool(left.get("source_sha"))
        and left.get("artifacts") == right.get("artifacts")
        and all(left.get("artifacts", {}).get(key) for key in required_artifacts)
        and all(left.get(key) and left.get(key) == right.get(key) for key in identities)
        and all(
            set(row.get("cache", {})) == {"mount", "exec", "commit"}
            and all(value.get("eligibility") == "ELIGIBLE" for value in row["cache"].values())
            for row in (left, right)
        )
        and all(isinstance(row.get("exec_ns"), int) and row["exec_ns"] > 0 for row in (left, right))
    )


def safe(value):
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def diagnostic_outcome(rows, cleanup):
    passed = sum(row["execution"] == "PASS" and row["cleanup"] == "COMPLETE" for row in rows)
    complete = len(rows) == passed == 96 and cleanup.get("cleanup") == "COMPLETE"
    return {
        "diagnostic_terminal": "PASS" if complete else "INCOMPLETE",
        "execution_and_case_cleanup_pass_rows": passed,
        "registered_rows": 96,
        "final_cleanup": cleanup.get("cleanup", "NOT_RUN"),
        "scope": "CLI execution and cleanup only; timings are ineligible diagnostics",
        "verification": dict(Counter(row["verification"] for row in rows)),
        "performance": dict(Counter(row["performance"] for row in rows)),
    }


def render(rows, cleanup=None):
    execution = Counter(row["execution"] for row in rows)
    eligible = sum(row["performance"] == "ELIGIBLE" for row in rows)
    verified = sum(row["verification"] == "PASS" for row in rows)
    outcome = diagnostic_outcome(rows, cleanup or {})
    lines = [
        "# fs-bench-quick campaign report",
        "",
        "> Status: Research; informative and not a product contract.",
        "",
        (
            f"**Diagnostic execution/cleanup outcome: {outcome['diagnostic_terminal']}.** "
            f"Final infrastructure cleanup: {outcome['final_cleanup']}."
        ),
        "",
        (
            f"Registered rows: 96. Execution outcomes: {dict(execution)}. "
            f"Performance-eligible rows: {eligible}. Independently verified rows: {verified}."
        ),
        "",
        (
            "Raw CLI observations include launch, routing and Store open/close costs. "
            "Unverified rows are diagnostics. Ineligible observations establish no speed comparison. "
            "Cleanup completion is reported separately in the campaign cleanup receipt."
        ),
        "",
        (
            "End-to-end case time includes Sandbox creation, mount, Exec, LayerFS Commit, "
            "unmount and case cleanup. It excludes preparation and initial Python startup/configuration checks."
        ),
        "",
        "| Case / machine / database | Execution | Performance | Verification | Cleanup | Exec ns | End-to-end case ns | Reason |",
        "| --- | --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for row in rows:
        name = f"[{row['id']}]({row['receipt']})" if row["receipt"] else row["id"]
        values = [
            name,
            row["execution"],
            row["performance"],
            row["verification"],
            row["cleanup"],
            row.get("exec_ns", ""),
            row.get("end_to_end_case_ns", ""),
            safe(row["reason"]),
        ]
        lines.append("| " + " | ".join(map(str, values)) + " |")
    lines += [
        "",
        "## Database comparisons",
        "",
        (
            "Ratio = PostgreSQL CLI exec ns / SQLite CLI exec ns. "
            "Delta = PostgreSQL ns - SQLite ns. Only eligible matched rows receive a ratio."
        ),
        "",
        "| Cell / machine | Delta ns | Ratio | Disposition |",
        "| --- | ---: | ---: | --- |",
    ]
    by_id = {row["id"]: row for row in rows}
    for cell in range(1, 13):
        for machine in MACHINES:
            key = f"C{cell:02}/{machine}"
            left, right = (by_id[f"{key}/{backend}"] for backend in BACKENDS)
            if comparable(left, right):
                delta = right["exec_ns"] - left["exec_ns"]
                ratio = f"{right['exec_ns'] / left['exec_ns']:.6f}"
                disposition = "Descriptive; no speed gate declared"
            else:
                delta, ratio, disposition = "", "", "INELIGIBLE or incomplete pair"
            lines.append(f"| {key} | {delta} | {ratio} | {disposition} |")
    lines += [
        "",
        "## Machine comparisons",
        "",
        (
            "Ratio = guest CLI exec ns / native CLI exec ns, within the same cell and database. "
            "Only eligible matched rows receive a ratio."
        ),
        "",
        "| Cell / database / guest | Delta ns vs native | Ratio | Disposition |",
        "| --- | ---: | ---: | --- |",
    ]
    for cell in range(1, 13):
        for backend in BACKENDS:
            native = by_id[f"C{cell:02}/native/{backend}"]
            for machine in MACHINES[1:]:
                guest = by_id[f"C{cell:02}/{machine}/{backend}"]
                if comparable(native, guest):
                    delta = guest["exec_ns"] - native["exec_ns"]
                    ratio = f"{guest['exec_ns'] / native['exec_ns']:.6f}"
                    disposition = "Descriptive; actual deployment routes"
                else:
                    delta, ratio, disposition = "", "", "INELIGIBLE or incomplete pair"
                lines.append(f"| C{cell:02}/{backend}/{machine} | {delta} | {ratio} | {disposition} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="fresh report directory (default: input/report)")
    args = parser.parse_args(argv)
    output = args.output or args.input / "report"
    try:
        rows = load_rows(args.input)
        cleanup_path = args.input / "cleanup.json"
        cleanup = json.loads(cleanup_path.read_text()) if cleanup_path.exists() else {}
        output.mkdir(parents=True, exist_ok=False)
        with (output / "summary.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        (output / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
        # Report links are relative to its own output directory.
        for row in rows:
            if row["receipt"]:
                row["receipt"] = os.path.relpath(args.input / row["receipt"], output)
        (output / "report.md").write_text(render(rows, cleanup))
        (output / "outcome.json").write_text(json.dumps(diagnostic_outcome(rows, cleanup), indent=2) + "\n")
        print(output / "report.md")
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"report: {error}\n")


if __name__ == "__main__":
    main()
