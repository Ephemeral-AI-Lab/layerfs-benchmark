#!/usr/bin/env python3
"""Markdown tables from export receipts, one table per case, native first.

    report.py RUN_ID...      (receipts under results/<run-id>/receipt.json)

Prints the tables only; the report's outcome, configuration, observations,
limits and cleanup are written by the agent who ran the campaign.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cases  # noqa: E402

RESULTS = HERE.parent / "results"
COLUMNS = (
    "Machine", "Execution", "Verification", "Performance", "Cold pages",
    "Export ms", "MB/s", "Files/s", "First event ms", "Cold control s", "Verify s", "Load 1m",
)


def load(run_ids: list) -> list:
    return [json.loads((RESULTS / run_id / "receipt.json").read_text()) for run_id in run_ids]


def cell(value) -> str:
    return "—" if value is None else str(value)


def row(r: dict) -> list:
    files = r["cold"].get("files", [])
    resident = f"{sum(f['resident_pages'] for f in files)}/{sum(f['pages'] for f in files)}" if files else "unknown"
    m = r["metrics"]
    return [
        r["machine"], r["execution"], r["verification"]["status"], r["performance"], resident,
        cell(m["wall_ms"]), cell(m["mb_per_s"]), cell(m["files_per_s"]), cell(m["prepare_ms"]),
        cell(r["cold"].get("control_s")), cell(r["verification"]["wall_s"]), f"{r['load_1m_before']:.1f}",
    ]


def tables(receipts: list) -> str:
    out = []
    for case_id, case in cases.CASES.items():
        rows = sorted(
            (r for r in receipts if r["case"] == case_id), key=lambda r: cases.MACHINES.index(r["machine"])
        )
        if not rows:
            continue
        out.append(f"## {case_id} — {case['work']}\n")
        out.append("| " + " | ".join(COLUMNS) + " |")
        out.append("| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        out.extend("| " + " | ".join(row(r)) + " |" for r in rows)
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    print(tables(load(sys.argv[1:])))
