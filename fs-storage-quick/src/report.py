#!/usr/bin/env python3
"""Render one fs-storage-quick report from an exported row-summary JSON.

  report.py --rows rows.json [--notes notes.md] [--outcome TEXT] --output result/.../report.md

The rows JSON is ``run.py export`` output (the pinned baseline is one). The
report leads with the raw-vs-stored reduction table, then configuration,
lifecycle and matrix wall (INELIGIBLE), Store bytes (SQLite file / WAL / WAL
frames, PostgreSQL schema; late probe), Q6 Init floors, per-Commit
attribution, per-Commit curves, diagnostics and optional DIAGNOSTIC
attribution. Observations, limits and cleanup come from ``--notes``.
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "shared" / "src"))
sys.path.insert(0, str(HERE))
import cases  # noqa: E402
from storage_report import (  # noqa: E402
    BACKEND_NAMES, REDUCTION_NOTE, UNITS_NOTE, b, mb, reduction_table, signed, table,
)

ORDER = cases.CASE_IDS


def ordered(rows):
    return sorted((r for r in rows.values() if r.get("case") in ORDER),
                  key=lambda r: (ORDER.index(r["case"]), ("sqlite", "postgresql").index(r["backend"]), r["id"]))


def outcome(data):
    rows = [r for r in data["rows"].values()]
    passed = sum(1 for r in rows if r["execution"] == "PASS" and r["verification"] == "PASS")
    walls = data.get("wall_ineligible", {})
    wall = "; ".join(f"{BACKEND_NAMES[k]} {v['matrix_wall_s']} s" for k, v in walls.items())
    cleanup = "COMPLETE" if all(r.get("cleanup") == "COMPLETE" for r in rows) else "INCOMPLETE"
    late = sum(1 for r in rows if r.get("late_status") == "MEASURED")
    return (f"{passed} of {len(rows)} fs-storage-quick rows PASS with verified final state; matrix wall "
            f"{wall} (INELIGIBLE, target ≤ 120 s per backend); late probe on {late} rows; row cleanup {cleanup}")


def reduction(data):
    out = []
    for r in ordered(data["rows"]):
        entry = {"case": r["case"], "backend": r["backend"], "raw": r["raw"], "stored": r["net_bytes"]}
        if not r.get("init_logical"):
            entry.update(canonical=r["sum_new_canonical"], packs=r["sum_new_stored"])
        out.append(entry)
    return reduction_table(out, ORDER)


def configuration(data):
    a = data.get("artifacts", {})
    h = data.get("harness") or {}
    return table(["Item", "Value"], [
        ["LayerFS source", f"`{data.get('source_sha')}`"],
        ["CLI / daemon (macOS, release)", f"`{a.get('cli_sha256')}` / `{a.get('daemon_sha256')}`"],
        ["Linux bundle seal", f"`{a.get('linux_bundle_sha256')}`"],
        ["Sandbox image", f"`{a.get('sandbox_image')}` (FROM runtime `{a.get('base_image')}`)"],
        ["Workload", f"`{data.get('workload_version')}`; gen.py `{data.get('gen_sha256')}`; model.py `{data.get('model_sha256')}`"],
        ["Pins", f"`src/pins.json` SHA-256 `{data.get('pins_sha256')}`"],
        ["Harness", f"layerfs-benchmark `{h.get('git_head')}` (suite dirty: {h.get('suite_dirty')}), sources `{h.get('sources_sha256')}`"],
        ["Machine", "Docker (`docker`), private `LAYERFS_HOME`, `LAYERFS_CONSTRUCTION_WORKERS=1`; rows serial, all SQLite then all PostgreSQL"],
        ["Store bytes", "SQLite: `store status` `file.bytes` (file) + `file.wal_bytes` (WAL); WAL frames = (WAL − 32) ÷ 4,120. PostgreSQL: `server.schemas.layerfs`"],
        ["Floor", "the row's own Store after create/connect + `project init` of an empty folder (+ `store push` for SQLite)"],
        ["Late probe", late_text(data.get("late_probe"))],
    ])


def late_text(late):
    if not late:
        return "not run"
    return (f"one wait of {late.get('wait_s')} s after the last row (slept {late.get('slept_s')} s), then "
            f"`store status` of {len(late.get('rows') or [])} retained Stores, then release")


def frames(probe):
    wal = probe.get("wal_bytes")
    if probe.get("wal_frames") is not None:
        return b(probe["wal_frames"])
    return "at 4 MiB limit" if wal == 4 * 1048576 else "—"


def lifecycle(data):
    body = []
    for r in ordered(data["rows"]):
        d = r.get("diagnostics", {})
        body.append([r["case"], BACKEND_NAMES[r["backend"]], r["execution"], r["verification"], r["cleanup"],
                     r["commits"], d.get("row_wall_s"), r.get("reason") or ""])
    walls = data.get("wall_ineligible", {})
    text = table(["Case", "Database", "Execution", "Final-state verification", "Cleanup", "Commits",
                  "Row wall (s, INELIGIBLE)", "Reason"], body)
    text += "\n\n" + table(["Database", "Rows", "Matrix wall, first row start → last row end (s, INELIGIBLE)",
                            "Σ row wall (s, INELIGIBLE)"],
                           [[BACKEND_NAMES[k], v["rows"], v["matrix_wall_s"], v["sum_row_wall_s"]]
                            for k, v in walls.items()])
    return text


def store_bytes(data):
    body = []
    for r in ordered(data["rows"]):
        final, floor, late = r.get("final") or {}, r.get("floor") or {}, r.get("late") or {}
        sqlite = r["backend"] == "sqlite"
        body.append([
            r["case"], BACKEND_NAMES[r["backend"]], b(floor.get("total_bytes")), b(final.get("total_bytes")),
            b(r.get("net_bytes")), mb(r.get("net_bytes")),
            b(r.get("net_file_bytes")) if sqlite else "—", b(final.get("wal_bytes")) if sqlite else "—",
            frames(final) if sqlite else "—",
            b(r.get("late_net_bytes")), b(r.get("late_net_file_bytes")) if sqlite else "—",
            b(late.get("wal_bytes")) if sqlite else "—", r.get("late_idle_s") if late else "—",
        ])
    return table(["Case", "Database", "Floor (B)", "Final (B)", "Net (B)", "Net (MB)", "Net file (B)",
                  "Final WAL (B)", "Final WAL frames", "Late net (B)", "Late net file (B)", "Late WAL (B)",
                  "Late idle (s)"], body)


def inits(data):
    body = []
    for r in ordered(data["rows"]):
        if not r.get("inits"):
            continue
        floor = (r.get("floor") or {}).get("total_bytes")
        previous = floor
        for label, probe in r["inits"].items():
            total = probe.get("total_bytes")
            body.append([r["case"], BACKEND_NAMES[r["backend"]], label, b(total),
                         signed(total - previous if isinstance(total, int) and isinstance(previous, int) else None),
                         b(probe.get("wal_bytes")) if r["backend"] == "sqlite" else "—"])
            previous = total
        final = (r.get("final") or {}).get("total_bytes")
        body.append([r["case"], BACKEND_NAMES[r["backend"]], "final (after Commits)", b(final),
                     signed(final - previous if isinstance(final, int) and isinstance(previous, int) else None),
                     b((r.get("final") or {}).get("wal_bytes")) if r["backend"] == "sqlite" else "—"])
    if not body:
        return ""
    return table(["Case", "Database", "Probe", "Store (B)", "Δ previous probe (B)", "WAL (B)"], body)


def attribution(data):
    body = []
    for r in ordered(data["rows"]):
        net, stored = r.get("net_bytes"), r["sum_new_stored"]
        body.append([r["case"], BACKEND_NAMES[r["backend"]], r["commits"], b(r["raw"]), b(r["sum_new_canonical"]),
                     b(stored), b(r["sum_new_payload"]), b(r["sum_new_metadata"]), b(net),
                     signed(net - stored if isinstance(net, int) else None)])
    return table(["Case", "Database", "Commits", "Raw = Σ logical (+ Init) (B)", "Σ new_canonical (B)",
                  "Σ new_stored (B)", "Σ payload (B)", "Σ new_metadata (B)", "Net (B)",
                  "Net − Σ new_stored (B)"], body)


def curves(data):
    parts = []
    by_case = {}
    for r in ordered(data["rows"]):
        by_case.setdefault(r["case"], {})[r["backend"]] = r
    for case, pair in by_case.items():
        present = [x for x in ("sqlite", "postgresql") if x in pair]
        if case == "Q6":
            body = []
            for backend in present:
                curve = pair[backend]["curve"]
                for group, items in (("p1@lane", [c for c in curve if c["branch"] == "p1@lane"]),
                                     ("b01.. (identical)", [c for c in curve if c["branch"] != "p1@lane"])):
                    if not items:
                        continue
                    stored = [c["new_stored"] for c in items]
                    meta = [c["new_metadata"] for c in items]
                    body.append([BACKEND_NAMES[backend], group, len(items), b(sum(stored)), b(min(stored)),
                                 b(int(statistics.median(stored))), b(max(stored)), b(sum(meta)),
                                 b(int(statistics.median(meta)))])
            parts.append(f"**Q6** (per-Commit values in the exported JSON)\n\n" + table(
                ["Database", "Branch", "Commits", "Σ new_stored (B)", "Min (B)", "Median (B)", "Max (B)",
                 "Σ new_metadata (B)", "Median new_metadata (B)"], body))
            continue
        headers = ["Commit", "Logical (B)"]
        for backend in present:
            headers += [f"{BACKEND_NAMES[backend]} new_stored (B)", f"{BACKEND_NAMES[backend]} new_metadata (B)"]
        length = max(len(pair[x]["curve"]) for x in present)
        body = []
        for i in range(length):
            first = pair[present[0]]["curve"][i] if i < len(pair[present[0]]["curve"]) else {}
            cells = [str(i + 1), b(first.get("logical"))]
            for backend in present:
                curve = pair[backend]["curve"]
                c = curve[i] if i < len(curve) else {}
                cells += [b(c.get("new_stored")), b(c.get("new_metadata"))]
            body.append(cells)
        parts.append(f"**{case} {cases.TITLES[case]}**\n\n" + table(headers, body))
    return "\n\n".join(parts)


def diagnostics(data):
    body = []
    for r in ordered(data["rows"]):
        d = r.get("diagnostics", {})
        cpu = [c.get("cli_cpu_ms_ineligible") for c in r["curve"] if c.get("cli_cpu_ms_ineligible") is not None]
        body.append([r["case"], BACKEND_NAMES[r["backend"]], d.get("commit_wall_ms_sum"),
                     d.get("commit_wall_ms_median"), d.get("commit_wall_ms_max"),
                     round(statistics.median(cpu), 1) if cpu else "—",
                     ", ".join(str(x) for x in d.get("init_wall_ms") or []) or "—",
                     ", ".join(str(x) for x in d.get("verify_wall_ms") or []) or "—"])
    return table(["Case", "Database", "Σ Commit wall (ms)", "Median Commit wall (ms)", "Max Commit wall (ms)",
                  "Median CLI-process CPU per Commit (ms)", "Init wall (ms)", "Verify Exec wall (ms)"], body)


def attribution_section(data):
    out = []
    for r in ordered(data["rows"]):
        for store, record in (r.get("attribution") or {}).items():
            if record.get("status") != "MEASURED":
                out.append(f"- {r['id']} `{store}`: {record.get('status')} {record.get('reason', '')}")
                continue
            body = []
            for t in record["tables"][:12]:
                if r["backend"] == "sqlite":
                    body.append([t["name"], b(t.get("pages")), b(t.get("bytes")), b(t.get("payload")), b(t.get("unused"))])
                else:
                    body.append([t["name"], b(t.get("total_bytes")), b(t.get("heap_bytes")), b(t.get("index_bytes")),
                                 b(t.get("toast_bytes")), b(t.get("live_tuples")), b(t.get("dead_tuples")),
                                 str(t.get("last_autovacuum") or "—")])
            headers = (["Table/index", "Pages", "Bytes (B)", "Payload (B)", "Unused (B)"] if r["backend"] == "sqlite"
                       else ["Table", "Total (B)", "Heap (B)", "Indexes (B)", "TOAST (B)", "Live tuples",
                             "Dead tuples", "Last autovacuum"])
            out.append(f"**{r['id']}** ({record['label']}; {record['method']})\n\n" + table(headers, body))
    return "\n\n".join(out)


DIAGNOSTICS_NOTE = (
    "What the public CLI exposes per Commit is `logical`, `new_canonical`, `new_stored` and `new_metadata` "
    "(bytes). Wall time of each Commit call and the CPU of the local CLI process come from the harness ledger and "
    "are INELIGIBLE diagnostics. **UNAVAILABLE** through the public CLI: worker/daemon Commit CPU, "
    "`value_lookups`/`value_rows`, pooled decode/read-amplification counters (`chain_edges`, "
    "`physical_group_decodes`, `branch_delta_applies`, …), delta depth and PostgreSQL round trips; the product "
    "collects some of them only on the SDK trace route, which benchmarks may not use."
)


def render(data, notes="", outcome_text=None):
    sha = data.get("source_sha") or "unknown"
    sections = [
        f"# fs-storage-quick — {sha[:10]}",
        "",
        f"**{outcome_text or outcome(data)}.**",
        "",
        "Store bytes for six quick storage workloads on LayerFS 2.0 (Docker machine, SQLite and PostgreSQL "
        "Stores), measured at a quiesced boundary through the public CLI. This subset is the before/after gate "
        "of the #84 storage optimizations (`run.py compare` against this baseline); the full fs-storage suites "
        "remain the release check. " + UNITS_NOTE,
        "",
        "## Raw vs stored",
        "",
        REDUCTION_NOTE + " Q6 imports its base with `project init`, which no Commit covers, so only the overall "
        "reduction is shown for it; its raw counts every Commit state plus the Init state.",
        "",
        reduction(data),
        "",
        "## Configuration",
        "",
        configuration(data),
        "",
        "## Cases",
        "",
        table(["Case", "Workload", "Write method", "Commits", "Exercises"],
              [[c, cases.WORKLOADS[c], cases.WRITE_METHOD[c], cases.commits(c), cases.EXERCISES[c]] for c in ORDER]),
        "",
        "## Rows and matrix wall",
        "",
        lifecycle(data),
        "",
        "## Store bytes",
        "",
        "SQLite file and WAL are separate: a quiesced Store keeps up to 4 MiB of WAL (`journal_size_limit`). "
        "The late probe re-reads every Store after one wait (SQLite after the worker's 60 s idle close; "
        "PostgreSQL after autovacuum had a chance).",
        "",
        store_bytes(data),
        "",
    ]
    init_text = inits(data)
    if init_text:
        sections += ["## Q6 Init floors", "", init_text, ""]
    sections += [
        "## Per-Commit attribution",
        "",
        "In LayerFS 2.0 `new_stored` counts all new pack bytes and `new_metadata` is its metadata-domain subset, "
        "so payload = stored − metadata; **net − Σ new_stored** is what no Commit's packs account for (database "
        "pages, indexes, free space, the SQLite WAL, and for Q6 both Inits).",
        "",
        attribution(data),
        "",
        "## Per-Commit curves",
        "",
        curves(data),
        "",
        "## Diagnostics",
        "",
        DIAGNOSTICS_NOTE,
        "",
        diagnostics(data),
        "",
    ]
    attr = attribution_section(data)
    if attr:
        sections += ["## Per-table attribution (DIAGNOSTIC)", "",
                     "Read-only, after the late probe, on closed copies (SQLite `dbstat`) or the row's own "
                     "disposable database (PostgreSQL); the owner has not yet decided whether this belongs in the "
                     "suite (layerfs-project#85 task 1).", "", attr, ""]
    if notes:
        sections += [notes.strip(), ""]
    return "\n".join(sections)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rows", required=True)
    parser.add_argument("--notes")
    parser.add_argument("--outcome")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    data = json.loads(Path(args.rows).read_text())
    notes = Path(args.notes).read_text() if args.notes else ""
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(data, notes, args.outcome))
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
