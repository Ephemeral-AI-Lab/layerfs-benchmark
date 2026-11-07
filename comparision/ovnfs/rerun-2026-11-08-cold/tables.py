"""Print the cold report's numbers as JSON.

Cold samples: results/<arm>-<case>.run{1,2,3} (this folder). Warm references, for the cold/warm
ratio only: LayerFS b9c4adcb from ../rerun-2026-11-08-commit-speed/results, ovnfs 5d54cb0 from
../rerun-2026-11-07/results (S1-S4) and ../rerun-2026-11-07-v2-speed/results (500 MiB cases).
The small-edit cases (L100, L10, I10, A5) have no published warm run on this LayerFS build.
"""
import hashlib
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "harness"))
sys.path.insert(0, "/Users/yifanxu/Ephemeral-AI-Lab/layerfs-benchmark/fs-storage-history/src")
import largefile  # noqa: E402
BASE_DIR = "/Users/yifanxu/.cache/fs-storage-history/base-157"
HISTORY = {  # same shapes and seeds as harness/compare.py
    "S1": [("b01", "main", 40, "H01/p01/b01")],
    "S2": [(f"b{i:02d}", "main", 3, f"H02/p01/b{i:02d}") for i in range(1, 6)],
    "S3": [(f"l{i:02d}", "main" if i == 1 else f"l{i - 1:02d}", 3, f"H04/p01/l{i:02d}") for i in range(1, 5)],
    "S4": [(f"b{i:02d}", "main", 1, "H03/shared") for i in range(1, 6)],
}
SMALL = ("S1", "S2", "S3", "S4")
LARGE = ("NEW500", "ADD500", "RM500", "DEL500", "L500")
EDITS = ("L100", "L10", "I10", "A5")
WARM = {
    "layerfs": lambda c: sorted((HERE.parent / "rerun-2026-11-08-commit-speed" / "results").glob(f"layerfs-{c}*")),
    "ovnfs": lambda c: [HERE.parent / ("rerun-2026-11-07" if c in SMALL else "rerun-2026-11-07-v2-speed")
                        / "results" / f"ovnfs-{c}"],
}


def ms(ns):
    return ns / 1e6


def med(xs):
    return round(st.median(xs), 1)


def logical(case):
    """Raw = Σ file bytes over every state (the imported base plus every commit's state);
    distinct = Σ bytes of distinct file contents over those states."""
    states = []
    if case in SMALL:
        import base, model  # fs-storage-history oracle
        heads = {"main": base.load_tree(BASE_DIR)}
        states.append({p: e.data for p, e in heads["main"].entries.items() if e.kind == "file"})
        for name, source, commits, seed in HISTORY[case]:
            s = heads[source].copy()
            for k in range(1, commits + 1):
                model.plan_step(s, seed, k)
                states.append({p: e.data for p, e in s.entries.items() if e.kind == "file"})
            heads[name] = s
        raw = sum(len(d) for st_ in states for d in st_.values())
        distinct = {}
        for st_ in states:
            for d in st_.values():
                distinct.setdefault(hashlib.sha256(d).digest(), len(d))
        return {"states": len(states), "raw": raw, "distinct": sum(distinct.values())}
    exp = largefile.expect(case)
    if largefile.CASES[case].get("tree"):
        raw = sum(f["size"] for e in exp for f in e["files"].values())
        distinct = {f["sha256"]: f["size"] for e in exp for f in e["files"].values()}
    else:
        raw = sum(e["size"] for e in exp)
        distinct = {e["sha256"]: e["size"] for e in exp}
    return {"states": len(exp), "raw": raw, "distinct": sum(distinct.values())}


def one(path, case):
    """Per-sample summary: commit (median over the sample's commits), read and open (median over
    branches), import, final bytes, verification, and the cold evidence."""
    s = json.loads((path / "state.json").read_text())
    probes = {p["label"]: p.get("total_bytes", p.get("allocated_bytes")) for p in s["probes"]}
    if case in SMALL:
        branches = list(s["branches"].values())
        steps = [x for b in branches for x in b["steps"]]
        reads = [ms(b["verify_read_ns"]) for b in branches]
        opens = [ms(b["verify_open_ns"]) for b in branches]
        evicts = [x.get("evict") for x in steps] + [b.get("read_evict") for b in branches]
        ok = all(b.get("verification") == "PASS" for b in branches)
    else:
        steps = s["steps"]
        reads, opens = [ms(s["verify_read_ns"])], [ms(s["verify_open_ns"])]
        evicts = [x.get("evict") for x in steps] + [s.get("read_evict")]
        ok = s["verification"]["result"] == "PASS"
    commits = [ms(x.get("commit_ns", x.get("snap_ns", 0))) for x in steps]
    applies = [ms(x["apply_ns"]) for x in steps]
    evicts = [e for e in evicts if e]
    return {
        "status": s["status"], "verified": ok,
        "apply_ms": med(applies), "commit_ms": med(commits), "commit_all_ms": [round(c) for c in commits],
        "read_ms": med(reads), "open_ms": med(opens),
        "import_ms": round(ms(s["import_ns"])),
        "copy_base_ms": round(ms(s["copy_base_ns"])) if "copy_base_ns" in s else None,
        "stored_by_commits": probes["final"] - probes["import"], "stored_at_end": probes["final"],
        "stored_after_import": probes["import"], "commits": len(steps),
        "sum_new_stored": sum(x.get("new_stored") or 0 for x in steps) if "new_stored" in steps[0] else None,
        "sum_new_canonical": sum(x.get("new_canonical") or 0 for x in steps) if "new_canonical" in steps[0] else None,
        "sum_new_metadata": sum(x.get("new_metadata") or 0 for x in steps) if "new_metadata" in steps[0] else None,
        "evictions": len(evicts), "resident_after_max": max((e["resident_after"] for e in evicts), default=None),
        "evicted_mb": round(sum(e["resident_before"] for e in evicts) / 1e6, 1),
        "load": [x["load"] for x in s["load_1m"]],
    }


def arm(case, name):
    runs = sorted(HERE.glob(f"results/{name}-{case}.run*"))
    samples = [one(r, case) for r in runs]
    warm = [] if case in EDITS else [one(p, case) for p in WARM[name](case)]
    cold = {k: med([x[k] for x in samples]) for k in ("apply_ms", "commit_ms", "read_ms", "open_ms", "import_ms")}
    cold.update({f"{k}_range": [min(x[k] for x in samples), max(x[k] for x in samples)]
                 for k in ("apply_ms", "commit_ms", "read_ms")})
    w = {k: med([x[k] for x in warm]) if warm else None for k in ("apply_ms", "commit_ms", "read_ms")}
    return {
        "samples": len(samples), "verified": all(x["verified"] for x in samples),
        "cold_demonstrated": all(x["resident_after_max"] == 0 for x in samples),
        "evictions": sum(x["evictions"] for x in samples), **cold,
        "stored_by_commits": [x["stored_by_commits"] for x in samples],
        "stored_after_import": [x["stored_after_import"] for x in samples],
        "commits": samples[0]["commits"],
        "sum_new_stored": [x["sum_new_stored"] for x in samples],
        "sum_new_canonical": [x["sum_new_canonical"] for x in samples],
        "sum_new_metadata": [x["sum_new_metadata"] for x in samples],
        "stored_at_end": [x["stored_at_end"] for x in samples],
        "copy_base_ms": [x["copy_base_ms"] for x in samples],
        "warm_apply_ms": w["apply_ms"], "warm_commit_ms": w["commit_ms"], "warm_read_ms": w["read_ms"],
        "cold_over_warm": {"commit": round(cold["commit_ms"] / w["commit_ms"], 2),
                           "read": round(cold["read_ms"] / w["read_ms"], 2)} if warm else None,
        "load": [min(min(x["load"]) for x in samples), max(max(x["load"]) for x in samples)],
        "per_sample": samples,
    }


READS = ("RT0", "RT40", "RF0", "RF5")


def reads(case, name):
    """Explicit cold read case: every read's time (ms), median, MB/s, verification and cold evidence."""
    s = json.loads((HERE / "results" / f"{name}-{case}.cold" / "state.json").read_text())
    rs = s["reads"]
    times = [ms(r["read_ns"]) for r in rs]
    return {"status": s["status"], "reads": len(rs), "read_ms": med(times), "read_ms_all": [round(x) for x in times],
            "bytes": rs[0]["got"]["bytes"], "files": rs[0]["got"]["files"],
            "mb_per_s": round(rs[0]["got"]["bytes"] / 1e6 / (med(times) / 1e3), 1),
            "verified": all(r["verification"] == "PASS" for r in rs),
            "cold_demonstrated": all(r["evict"]["resident_after"] == 0 for r in rs),
            "load": [x["load"] for x in s["load_1m"]]}


def main():
    out = {c: {a: arm(c, a) for a in ("ovnfs", "layerfs")} for c in SMALL + LARGE + EDITS}
    for c in out:
        out[c]["logical"] = logical(c)
    out["read"] = {c: {a: reads(c, a) for a in ("ovnfs", "layerfs")} for c in READS}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
