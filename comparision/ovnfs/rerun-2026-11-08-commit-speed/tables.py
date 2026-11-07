"""Print the report's numbers: LayerFS b9c4adcb (results/) against ovnfs 5d54cb0 (earlier folders)."""
import json
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
OVNFS_SMALL = HERE.parent / "rerun-2026-11-07" / "results"
OVNFS_LARGE = HERE.parent / "rerun-2026-11-07-v2-speed" / "results"


def ms(ns):
    return round(ns / 1e6)


def small(path):
    s = json.loads((path / "state.json").read_text())
    probes = {p["label"]: p for p in s["probes"]}
    branches = list(s["branches"].values())
    steps = [x for b in branches for x in b["steps"]]
    return {
        "verified": f'{sum(b.get("verification") == "PASS" for b in branches)}/{len(branches)}',
        "import_ms": ms(s.get("import_ns", 0)),
        "apply_med_ms": round(st.median(x["apply_ns"] / 1e6 for x in steps)),
        "commit_med_ms": round(st.median(x["commit_ns"] / 1e6 for x in steps)),
        "open_med_ms": round(st.median((b["fork_ns"] + b["mount_ns"]) / 1e6 for b in branches)),
        "noop_ms": ms(s.get("control_ns", 0)),
        "read_ms": [ms(b["verify_read_ns"]) for b in branches],
        "import_bytes": probes["import"]["total_bytes"],
        "final_bytes": probes["final"]["total_bytes"],
    }


def large(path):
    s = json.loads((path / "state.json").read_text())
    commit = "commit_ns" if "commit_ns" in s["steps"][0] else "snap_ns"
    probes = {p["label"]: p.get("total_bytes", p.get("allocated_bytes")) for p in s["probes"]}
    return {
        "verification": s["verification"]["result"],
        "import_ms": ms(s["import_ns"]),
        "copy_base_ms": ms(s["copy_base_ns"]) if "copy_base_ns" in s else None,
        "apply_ms": [ms(x["apply_ns"]) for x in s["steps"]],
        "commit_ms": [ms(x[commit]) for x in s["steps"]],
        "stored_by_commits": probes["final"] - probes["import"],
        "stored_at_end": probes["final"],
        "read_ms": ms(s["verify_read_ns"]),
        "load": [x["load"] for x in s["load_1m"]],
    }


def main():
    out = {}
    for c in ("S1", "S2", "S3", "S4"):
        out[c] = {"layerfs": small(HERE / "results" / f"layerfs-{c}"), "ovnfs": small(OVNFS_SMALL / f"ovnfs-{c}")}
    for c in ("NEW500", "ADD500", "RM500", "DEL500", "L500"):
        runs = sorted((HERE / "results").glob(f"layerfs-{c}.run*")) or [HERE / "results" / f"layerfs-{c}"]
        out[c] = {"layerfs": [large(r) for r in runs], "ovnfs": large(OVNFS_LARGE / f"ovnfs-{c}")}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
