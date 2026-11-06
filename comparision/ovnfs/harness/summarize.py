#!/usr/bin/env python3
"""Tabulate compare.py results (results/<arm>-<case>/state.json)."""

import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "results"
CASES = {"S1": "1 branch x 40 commits", "S2": "5 branches x 3 commits",
         "S3": "4 nested forks x 3 commits", "S4": "5 identical branches x 1 commit"}


def ms(ns):
    return ns / 1e6


def med(xs):
    return round(st.median(xs)) if xs else None


def p90(xs):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(0.9 * len(xs)))]) if xs else None


rows = {}
for case in CASES:
    for arm in ("layerfs", "ovnfs"):
        s = json.loads((ROOT / f"{arm}-{case}" / "state.json").read_text())
        probes = {p["label"]: p for p in s["probes"]}
        br = s["branches"].values()
        steps = [x for b in br for x in b["steps"]]
        r = {
            "status": s["status"], "verified": sum(b["verification"] == "PASS" for b in br),
            "branches": len(s["branches"]), "commits": len(steps),
            "floor": probes["floor"]["total_bytes"], "import": probes["import"]["total_bytes"],
            "final": probes["final"]["total_bytes"],
            "import_ms": round(ms(s["import_ns"])),
            "control_ms": round(ms(s["control_ns"])),
            "branch_open_ms": med([ms(b["fork_ns"] + b["mount_ns"]) for b in br]),
            "apply_med": med([ms(x["apply_ns"]) for x in steps]),
            "apply_p90": p90([ms(x["apply_ns"]) for x in steps]),
            "commit_med": med([ms(x["commit_ns"]) for x in steps]),
            "commit_p90": p90([ms(x["commit_ns"]) for x in steps]),
            "verify_read_ms": [round(ms(b["verify_read_ns"])) for b in br],
            "load": [x["load"] for x in s.get("load_1m", [])],
        }
        if arm == "layerfs":
            r["sum_new_stored"] = sum(x["new_stored"] or 0 for x in steps)
            r["sum_new_metadata"] = sum(x["new_metadata"] or 0 for x in steps)
            r["final_file"] = probes["final"]["file_bytes"]
            r["final_wal"] = probes["final"]["wal_bytes"]
            r["import_file"] = probes["import"]["file_bytes"]
            r["final_alloc"] = probes["final"]["allocated_bytes"]
        else:
            r["final_apparent"] = probes["final"]["apparent_bytes"]
            r["import_apparent"] = probes["import"]["apparent_bytes"]
            r["parts_import"] = probes["import"]["parts"]
            r["parts_final"] = probes["final"]["parts"]
        r["import_cost"] = r["import"] - r["floor"]
        r["growth"] = r["final"] - r["import"]
        rows[(case, arm)] = r

print(json.dumps({f"{c}/{a}": v for (c, a), v in rows.items()}, indent=1))
