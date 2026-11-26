#!/usr/bin/env python3
"""Assert the local results.json is complete and honest:
- every case the run registered (`results["expected"]`) is present in its arm with a status;
- no arm failed (`failed_arms` is empty) and every entry of `results["proof"]` is True;
- every row carries identity.host; every OK read row carries a matching proof.manifest;
- no row is labelled cold unless it is an INELIGIBLE cold row.

usage: python3 check_results.py <results.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

STATUSES = {"OK", "REFUSED", "FAIL", "NOT_RUN", "INELIGIBLE"}


def proof_problems(proof: dict) -> list[str]:
    bad: list[str] = []
    for key, value in proof.items():
        if isinstance(value, dict):
            bad += [f"{key}.{label}" for label, item in value.items() if (item or {}).get("match") is not True]
        elif value is not True:
            bad.append(key)
    return bad


def check(results: dict) -> list[str]:
    errors: list[str] = []
    rows_seen = 0
    for arm, data in results.get("arms", {}).items():
        for row in [*data.get("rows", []), *data.get("concurrency", [])]:
            rows_seen += 1
            name = f"{arm}: {row.get('case') or row.get('workload')}"
            if not (row.get("identity") or {}).get("host"):
                errors.append(f"{name}: missing identity.host")
            if row.get("kind") == "cold" and row.get("status") != "INELIGIBLE":
                errors.append(f"{name}: cold row is {row.get('status')}, must be INELIGIBLE")
            if row.get("kind") != "cold" and "cold" in str(row.get("cache_state", "")).lower().replace("no cold claim", ""):
                errors.append(f"{name}: a non-cold row is labelled cold")
            if row.get("kind") == "read" and row.get("status") == "OK":
                manifest = (row.get("proof") or {}).get("manifest")
                if not manifest:
                    errors.append(f"{name}: read row without proof.manifest")
                elif manifest.get("match") is not True:
                    errors.append(f"{name}: proof.manifest does not match ({manifest.get('matched')}/{manifest.get('checked')})")
    if not rows_seen:
        errors.append("no rows in results")
    expected = results.get("expected")
    if not expected:
        errors.append("results carries no `expected` registry")
    for arm, cases in (expected or {}).items():
        if arm not in results.get("arms", {}):
            errors.append(f"{arm}: registered arm is absent")
        have = {r["case"]: r for r in results.get("arms", {}).get(arm, {}).get("rows", [])}
        for case in cases:
            if case not in have:
                errors.append(f"{arm}: registered case missing: {case}")
            elif have[case].get("status") not in STATUSES:
                errors.append(f"{arm}: {case}: no valid status ({have[case].get('status')})")
    for arm, reason in results.get("failed_arms", {}).items():
        errors.append(f"failed arm {arm}: {reason}")
    errors += [f"proof not True: {p}" for p in proof_problems(results.get("proof", {}))]
    return errors


def main() -> int:
    errors = check(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    for e in errors:
        print("FAIL", e)
    print(f"check_results: {'FAIL' if errors else 'PASS'} ({len(errors)} problems)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
