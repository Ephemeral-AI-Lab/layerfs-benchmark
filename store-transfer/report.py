import os
#!/usr/bin/env python3
"""Summarise the LP08-S1 receipts: one row per case, and the #12 roll-up."""
import json
from pathlib import Path

REC = Path(os.environ.get("LP08_RECEIPTS", "./receipts/lp08-s1"))

r12 = []
rows = []
for path in sorted(REC.glob("*.json")):
    if path.name == "matrix.json":
        continue
    entry = json.loads(path.read_text())
    if entry["case"] == "R12-PROGRESS":
        continue
    checks = entry["checks"]
    ok = sum(1 for c in checks if c["ok"])
    failed = [c["name"] for c in checks if not c["ok"]]
    rows.append(
        {
            "case": entry["case"],
            "verdict": entry["verdict"],
            "checks": len(checks),
            "passed": ok,
            "failed": failed,
        }
    )
    r12.extend(c for c in checks if c["name"].startswith("R12-"))

order = {"PASS": 0, "FAIL": 1, "NOT_RUN": 2}
rows.sort(key=lambda r: (order.get(r["verdict"], 3), r["case"]))
summary = {
    "cases": rows,
    "totals": {
        "cases": len(rows),
        "pass": sum(1 for r in rows if r["verdict"] == "PASS"),
        "fail": sum(1 for r in rows if r["verdict"] == "FAIL"),
        "not_run": sum(1 for r in rows if r["verdict"] == "NOT_RUN"),
        "checks": sum(r["checks"] for r in rows),
        "checks_passed": sum(r["passed"] for r in rows),
    },
    "progress": {
        "checks": len(r12),
        "passed": sum(1 for c in r12 if c["ok"]),
        "failed": [c["name"] for c in r12 if not c["ok"]],
    },
}
(REC / "matrix.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))

print("| case | verdict | checks | passed | failing |")
print("| --- | --- | --- | --- | --- |")
for row in rows:
    failing = ", ".join(row["failed"][:4]) + ("…" if len(row["failed"]) > 4 else "")
    print(f"| {row['case']} | {row['verdict']} | {row['checks']} | {row['passed']} | {failing} |")
print()
print(json.dumps(summary["totals"], indent=1))
print(json.dumps(summary["progress"], indent=1))
