#!/usr/bin/env python3
"""Assert the local results.json is complete: every row carries identity.host,
every OK read row carries proof.manifest with a match, and no row is labelled cold
unless it is an INELIGIBLE cold row.

usage: python3 check_results.py <results.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


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
    return errors


def main() -> int:
    errors = check(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    for e in errors:
        print("FAIL", e)
    print(f"check_results: {'FAIL' if errors else 'PASS'} ({len(errors)} problems)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
