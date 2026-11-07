"""Print the report's tables from results/ (and ovnfs S1-S4 from ../rerun-2026-11-07/results)."""
import json
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = {
    "layerfs before": HERE / "results" / "layerfs-before-{c}",
    "layerfs merged": HERE / "results" / "layerfs-{c}",
    "ovnfs": HERE.parent / "rerun-2026-11-07" / "results" / "ovnfs-{c}",
}


def ms(ns):
    return round(ns / 1e6)


def small(case):
    rows = {}
    for arm, pattern in ARMS.items():
        s = json.loads((Path(str(pattern).format(c=case)) / "state.json").read_text())
        probes = {p["label"]: p for p in s["probes"]}
        branches = list(s["branches"].values())
        steps = [x for b in branches for x in b["steps"]]
        rows[arm] = {
            "verified": f'{sum(b.get("verification") == "PASS" for b in branches)}/{len(branches)}',
            "import_ms": ms(s.get("import_ns", 0)),
            "apply_med": round(st.median(x["apply_ns"] / 1e6 for x in steps)),
            "commit_med": round(st.median(x["commit_ns"] / 1e6 for x in steps)),
            "open_med": round(st.median((b["fork_ns"] + b["mount_ns"]) / 1e6 for b in branches)),
            "control_ms": ms(s.get("control_ns", 0)),
            "read_ms": [ms(b["verify_read_ns"]) for b in branches],
            "import_bytes": probes["import"]["total_bytes"],
            "final_bytes": probes["final"]["total_bytes"],
        }
    return rows


def large():
    rows = {}
    for arm in ("layerfs-before-L500", "layerfs-L500", "ovnfs-L500", "layerfs-ADD500", "ovnfs-ADD500",
                "layerfs-DEL500", "ovnfs-DEL500", "layerfs-NEW500", "ovnfs-NEW500", "layerfs-RM500",
                "ovnfs-RM500"):
        s = json.loads((HERE / "results" / arm / "state.json").read_text())
        probes = {p["label"]: p.get("total_bytes", p.get("allocated_bytes")) for p in s["probes"]}
        commit = "commit_ns" if "commit_ns" in s["steps"][0] else "snap_ns"
        rows[arm] = {
            "verification": s["verification"]["result"],
            "import_ms": ms(s["import_ns"]),
            "copy_base_ms": ms(s["copy_base_ns"]) if "copy_base_ns" in s else None,
            "commit_ms": [ms(x[commit]) for x in s["steps"]],
            "apply_ms": [ms(x["apply_ns"]) for x in s["steps"]],
            "new_stored": [x.get("new_stored") for x in s["steps"]],
            "stored_after_import": probes.get("import"),
            "stored_at_end": probes.get("final"),
            "read_ms": ms(s["verify_read_ns"]),
            "load": [x["load"] for x in s["load_1m"]],
        }
    return rows


if __name__ == "__main__":
    print(json.dumps({**{c: small(c) for c in ("S1", "S2", "S3", "S4")}, "L500": large()}, indent=1))
