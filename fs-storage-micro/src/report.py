#!/usr/bin/env python3
"""Publish the fs-storage-micro report from retained campaign state.

  report.py --cache C --environment E --output result/.../report.md
            [--notes observations.md] [--cleanup cleanup.json]
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "shared" / "src"))
sys.path.insert(0, str(HERE))
import cases  # noqa: E402
import storage  # noqa: E402
import storage_report as sr  # noqa: E402

BACKENDS = ("sqlite", "postgresql")
KiB = 1024


def history(row):
    histories = row.get("histories") or []
    return histories[0]["commits"] if histories else []


def stored(commits, index):
    return commits[index]["new_stored"] if index < len(commits) else None


def actual(case, commits, summary, refs):
    """Short case-specific numbers to set against the expected result."""
    if not commits or not summary:
        return "—"
    net = summary.get("net_bytes")
    s = [c["new_stored"] for c in commits]
    m = [c["new_metadata"] for c in commits]
    if case == "M01":
        return (
            f"net ÷ 10,000 = {net / 10000:,.1f} B per file; new_stored {s[0]:,} B for "
            f"{commits[0]['logical']:,} B logical; (net − new_stored) ÷ 10,000 = {(net - s[0]) / 10000:,.1f} B per file"
        )
    if case == "M02":
        return (
            f"Commit 1 new_stored {s[0]:,} B; Commit 2 (500,000,000 B of copies) new_stored "
            f"{s[1]:,} B, new_metadata {m[1]:,} B"
        )
    if case in ("M03", "M04", "M05"):
        edits = s[1:]
        peak = max(range(len(edits)), key=lambda i: edits[i]) + 2
        return (
            f"Commit 1 new_stored {s[0]:,} B; 20 edit Commits Σ {sum(edits):,} B "
            f"(mean {sum(edits) / len(edits):,.0f} B, largest {max(edits):,} B at Commit {peak}); "
            f"Σ new_metadata {sum(m):,} B"
        )
    if case == "M06":
        names = ["base", "insert start", "insert middle", "overwrite 4 KiB", "append 1 MiB", "delete first"]
        return "; ".join(f"{n} {v:,} B ({v / KiB:,.1f} KiB)" for n, v in zip(names, s))
    if case == "M07":
        text = refs.get("zstd3_text.txt")
        return (
            f"random {s[0]:,} B ({s[0] / 67108864:.4f} of 64 MiB); zeros {s[1]:,} B; text {s[2]:,} B"
            + (f" vs zstd -3 of the file {text:,} B ({s[2] / text:.3f}×)" if text else "")
        )
    if case == "M08":
        churn = s[1:11]
        return (
            f"create {s[0]:,} B; 10 update Commits Σ {sum(churn):,} B (mean {sum(churn) / 10:,.0f} B); "
            f"VACUUM {s[11]:,} B" if len(s) >= 12 else "incomplete history"
        )
    return "—"


def outcome(rows, primary, cleanup):
    passed = [r for r in primary if r.get("execution") == "PASS" and r.get("verification") == "PASS"]
    text = f"**{len(passed)} of {len(primary)} fs-storage-micro rows PASS with verified final state"
    failed = [r["id"] for r in primary if r not in passed]
    if failed:
        text += f" ({len(failed)} not passing: {', '.join(failed)})"
    repeats = [r for r in rows if r.get("repeat", 1) > 1]
    for repeat in repeats:
        base = next((r for r in primary if r["case"] == repeat["case"] and r["backend"] == repeat["backend"]), None)
        same = deterministic(base, repeat)
        text += f"; determinism repeat {repeat['id']}: {'identical Store bytes' if same else 'DIFFERENT Store bytes'}"
    text += f"; final cleanup {cleanup}.**"
    return text


def deterministic(a, b):
    if not a or not b or not a.get("summary") or not b.get("summary"):
        return False
    keys = ("final_bytes", "net_bytes", "sum_new_stored", "sum_new_metadata")
    return all(a["summary"].get(k) == b["summary"].get(k) for k in keys) and [
        (c["new_stored"], c["new_metadata"]) for c in history(a)
    ] == [(c["new_stored"], c["new_metadata"]) for c in history(b)]


def render(state, config, notes="", cleanup="UNKNOWN"):
    rows = list(state["rows"].values())
    for row in rows:
        row.setdefault("case", row.get("cell"))
        refs = cases.REFERENCES.get(row["case"], {})
        if row.get("probes", {}).get("final"):
            row["summary"] = storage.row_summary(row, {k: refs[k] for k in ("whole_file_unique", "tar_zstd", "git_pack", "cdc_oracle") if k in refs}, refs.get("whole_file_unique"))
        row["outcome"] = (
            "PASS" if row.get("execution") == "PASS" and row.get("verification") == "PASS"
            else row.get("execution", "NOT_RUN")
        )
    primary = [r for r in rows if r.get("repeat", 1) == 1]
    artifacts = config.get("artifacts", {})
    lines = [
        f"# fs-storage-micro — {state['source_sha'][:10]}",
        "",
        outcome(rows, primary, cleanup),
        "",
        "Store bytes for eight single-mechanism workloads on LayerFS 2.0 (Docker machine, SQLite and "
        "PostgreSQL Stores), measured at a quiesced boundary through the public CLI. Bytes are reported "
        "against each case's expected result, not gated by it. "
        + sr.UNITS_NOTE,
        "",
        "## Configuration",
        "",
        "| Item | Value |",
        "| --- | --- |",
        f"| LayerFS source | `{state['source_sha']}` (`layerfs_v2_0_0`) |",
        f"| CLI / daemon (macOS, release) | `{artifacts.get('cli_sha256')}` / `{artifacts.get('daemon_sha256')}` |",
        f"| Linux bundle seal | `{artifacts.get('linux_bundle_sha256')}` |",
        f"| Sandbox image | `{artifacts.get('sandbox_image')}` (FROM runtime `{artifacts.get('base_image')}`) |",
        f"| Machine | Docker (`{config['machines']['docker']['name']}`), private `LAYERFS_HOME`, `LAYERFS_CONSTRUCTION_WORKERS=1` |",
        f"| PostgreSQL | {config.get('postgresql', {}).get('server_image', '—')}; one pre-created empty database per row; `--synchronous-commit off` |",
        f"| Workload | `{cases.WORKLOAD_VERSION}`, generator `image/gen.py` SHA-256 `{cases.GEN_SHA256}` |",
        f"| Pins | `src/pins.json` SHA-256 `{cases.REFERENCES_PIN}` (oracles and references) |",
        f"| Storage policy (fixed in 2.0) | {storage.POLICY['cdc']}; delta depth caps 16/8/8 (whole file/chunk/metadata); {storage.POLICY['compression']} |",
        "| Store bytes | SQLite: `store status` `file.bytes` + `file.wal_bytes`; allocated = st_blocks×512 of `store.sqlite` + `-wal` in the worker volume. PostgreSQL: `server.schemas.layerfs` |",
        "| Floor | the row's own Store after create/connect + `project init` of an empty folder (+ `store push` for SQLite), before any fork |",
        "",
        "## Rows",
        "",
    ]
    lifecycle = []
    for row in sorted(rows, key=lambda r: (r["case"], BACKENDS.index(r["backend"]), r.get("repeat", 1))):
        wall = row.get("wall_ns_ineligible")
        lifecycle.append([
            row["id"], row.get("execution", "NOT_RUN"), row.get("verification", "NOT_RUN"),
            row.get("cleanup", "NOT_RUN"), (row.get("summary") or {}).get("commits", "—"),
            f"{wall / 1e9:.1f}" if isinstance(wall, int) else "—", row.get("reason", ""),
        ])
    lines += [sr.table(["Row", "Execution", "Final-state verification", "Cleanup", "Commits", "Wall s (INELIGIBLE)", "Reason"], lifecycle), ""]
    lines += ["## Store bytes", "", sr.store_bytes_table(primary), ""]
    lines += [
        "## Per-Commit attribution",
        "",
        "`logical` is each Commit's whole-tree size, so Σ logical sums the states. Unattributed = net − "
        "(Σ new_stored + Σ new_metadata): bytes in the Store that no Commit counter names (database pages, "
        "indexes, free space, WAL).",
        "",
        sr.attribution_table(primary),
        "",
    ]
    ref_bytes = {case: cases.REFERENCES.get(case, {}) for case in cases.CASE_IDS if cases.REFERENCES.get(case)}
    lines += [
        "## References",
        "",
        "Computed offline once per workload version from the same generator's states (pinned in "
        "`src/pins.json`). The CDC oracle is approximate: its gear table and masks differ from LayerFS's.",
        "",
        sr.references_bytes_table(ref_bytes, [c for c in cases.CASE_IDS if c in ref_bytes]),
        "",
        sr.reference_table(primary, ref_bytes),
        "",
        "## Cases",
        "",
    ]
    for case in cases.CASE_IDS:
        lines += [f"### {case} {cases.TITLES[case]}", ""]
        lines += [
            f"- **Workload:** {cases.WORKLOADS[case]}.",
            f"- **Write method:** {cases.gen.WRITE_METHOD[case]}; {len(cases.gen.PLAN[case])} Commits.",
            f"- **Expected:** {cases.EXPECTED[case]}.",
        ]
        by_backend = {}
        for row in primary:
            if row["case"] == case:
                by_backend[row["backend"]] = history(row)
                lines.append(
                    f"- **Actual, {sr.BACKEND_NAMES[row['backend']]}:** "
                    + actual(case, history(row), row.get("summary"), cases.REFERENCES.get(case, {}))
                    + "."
                )
        lines.append("")
        if any(by_backend.values()):
            lines += [sr.commit_curve_table(by_backend), ""]
    repeats = [r for r in rows if r.get("repeat", 1) > 1]
    if repeats:
        lines += ["## Determinism", ""]
        body = []
        for repeat in repeats:
            base = next((r for r in primary if r["case"] == repeat["case"] and r["backend"] == repeat["backend"]), {})
            a, b = base.get("summary") or {}, repeat.get("summary") or {}
            body.append([
                repeat["id"], sr.b(a.get("final_bytes")), sr.b(b.get("final_bytes")),
                sr.b(a.get("net_bytes")), sr.b(b.get("net_bytes")),
                sr.b(a.get("net_allocated_bytes")), sr.b(b.get("net_allocated_bytes")),
                "identical" if deterministic(base, repeat) else "DIFFERENT",
            ])
        lines += [sr.table(["Repeat", "Final first (B)", "Final repeat (B)", "Net first (B)", "Net repeat (B)",
                            "Net allocated first (B)", "Net allocated repeat (B)", "Store bytes and per-Commit counters"], body), ""]
    if notes:
        lines += [notes.strip(), ""]
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--notes")
    parser.add_argument("--cleanup")
    args = parser.parse_args(argv)
    state = json.loads((Path(args.cache) / "campaign.json").read_text())
    config = json.loads(Path(args.environment).read_text())
    notes = Path(args.notes).read_text() if args.notes else ""
    cleanup = json.loads(Path(args.cleanup).read_text()).get("cleanup") if args.cleanup else state.get("cleanup", "UNKNOWN")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(state, config, notes, cleanup))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
