#!/usr/bin/env python3
"""Publish the fs-storage-dsh report from retained campaign state.

    report.py --cache C [--cache C2 ...] [--repeat-cache R] [--superseded C:ROW ...]
              --references <dir> --environment E --cleanup final-cleanup.json --output report.md

Rows are taken from every `--cache` campaign (the newest attempt of each row
wins; earlier attempts listed with `--superseded` are reported as superseded).
`--repeat-cache` holds the determinism repeat of D10 SQLite.
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path[:0] = [str(SRC), str(SRC.parents[1] / "shared" / "src")]

import cases  # noqa: E402
import storage  # noqa: E402
import storage_report as sr  # noqa: E402

NAMES = sr.BACKEND_NAMES
REF_NAMES = ("whole_file_unique", "tar_zstd", "git_pack", "cdc_oracle")


def load_rows(caches):
    rows, campaigns = {}, []
    for cache in caches:
        state = json.loads((Path(cache) / "campaign.json").read_text())
        campaigns.append(state)
        for key, row in state["rows"].items():
            rows[(state["campaign_id"], key)] = row
    return rows, campaigns


def references(directory):
    out, pins = {}, {}
    for case_id in cases.CASE_IDS:
        path = Path(directory) / f"references-{case_id}.json"
        text = path.read_text()
        out[case_id] = json.loads(text)
        pins[case_id] = __import__("hashlib").sha256(text.encode()).hexdigest()
    return out, pins


def outcome(row):
    if row.get("execution") != "PASS":
        return "FAIL"
    if row.get("verification") not in ("PASS",):
        return "FAIL (verify)"
    return "PASS"


def summary(row, refs):
    return storage.row_summary(row, storage_refs(refs), refs["whole_file_unique"]["bytes"])


def storage_refs(refs):
    return {name: refs[name]["bytes"] for name in REF_NAMES if isinstance(refs.get(name, {}).get("bytes"), int)}


def history(row):
    return (row.get("histories") or [{}])[0].get("commits", [])


def curve_stats(commits):
    stored = [c["new_stored"] for c in commits]
    if not stored:
        return {}
    top = sorted(range(len(stored)), key=lambda i: -stored[i])[:3]
    return {
        "first": stored[0],
        "rest_sum": sum(stored[1:]),
        "rest_median": int(statistics.median(stored[1:])) if len(stored) > 1 else None,
        "rest_max": max(stored[1:]) if len(stored) > 1 else None,
        "top": top,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", action="append", required=True)
    parser.add_argument("--repeat-cache")
    parser.add_argument("--superseded", action="append", default=[])
    parser.add_argument("--references", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--cleanup", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    config = json.loads(Path(args.environment).read_text())
    cleanup = json.loads(Path(args.cleanup).read_text())
    refs, pins = references(args.references)
    all_rows, campaigns = load_rows(args.cache)
    superseded = {tuple(item.split(":", 1)) for item in args.superseded}
    current = {}
    for (campaign_id, key), row in all_rows.items():
        if (campaign_id, key) not in superseded:
            current[key] = (campaign_id, row)
    table_rows = []
    for case_id in cases.CASE_IDS:
        for backend in ("sqlite", "postgresql"):
            key = f"{case_id}/docker/{backend}"
            campaign_id, row = current.get(key, (None, {}))
            table_rows.append({
                "case": case_id,
                "backend": backend,
                "campaign": campaign_id,
                "row": row,
                "outcome": outcome(row) if row else "NOT_RUN",
                "summary": summary(row, refs[case_id]) if row.get("probes") else None,
            })
    passed = sum(1 for r in table_rows if r["outcome"] == "PASS")
    repeat = None
    if args.repeat_cache:
        state = json.loads((Path(args.repeat_cache) / "campaign.json").read_text())
        row = state["rows"].get("D10/docker/sqlite")
        if row:
            repeat = {"campaign": state["campaign_id"], "row": row, "summary": summary(row, refs["D10"]) if row.get("probes") else None}

    lines = []
    d10 = {r["backend"]: r for r in table_rows if r["case"] == "D10"}
    d03 = {r["backend"]: r for r in table_rows if r["case"] == "D03"}

    def net(r):
        return (r.get("summary") or {}).get("net_bytes")

    git = {c: refs[c]["git_pack"]["bytes"] for c in cases.CASE_IDS}
    headline = (
        f"**{passed} of 4 rows PASS (applied, committed, measured and verified at state 157); "
        f"net Store bytes D10 {sr.b(net(d10['sqlite']))} B SQLite / {sr.b(net(d10['postgresql']))} B PostgreSQL, "
        f"D03 {sr.b(net(d03['sqlite']))} B / {sr.b(net(d03['postgresql']))} B, "
        f"against a Git pack + idx of {sr.b(git['D10'])} / {sr.b(git['D03'])} B; final cleanup "
        f"{cleanup.get('cleanup', 'UNKNOWN')}.**"
    )
    lines += [headline, ""]
    lines += [
        "Storage only: every number is an exact byte count from the public CLI "
        "(`store status`, `commit list`) or the Docker worker volume; wall times are "
        "INELIGIBLE diagnostics. " + sr.UNITS_NOTE,
        "",
        "## Raw vs stored",
        "",
        sr.REDUCTION_NOTE,
        "",
        sr.reduction_table([
            {
                "case": r["case"], "backend": r["backend"],
                "raw": r["summary"].get("sum_logical"),
                "stored": r["summary"].get("net_bytes"),
                "canonical": r["summary"].get("sum_new_canonical"),
                "packs": r["summary"].get("sum_new_stored"),
            }
            for r in table_rows if r.get("summary")
        ], order=cases.CASE_IDS),
        "",
        "## Configuration",
        "",
    ]
    art = config["artifacts"]
    cfg = [
        ("LayerFS source", f"`{config['source_sha']}` (`layerfs_v2_0_0`)"),
        ("CLI / daemon SHA-256", f"`{art['cli_sha256']}` / `{art['daemon_sha256']}`"),
        ("Linux bundle seal", f"`{art['linux_bundle_sha256']}` (release, reused unchanged)"),
        ("Sandbox image", f"`{art['sandbox_image_tag']}` = `{art['sandbox_image']}`, FROM `{art['base_image']}` (Debian 12, Python 3.11.2, git 2.39.5)"),
        ("Seed", "`git-snapshots-157-v1/snapshots.git` (157 trees, linear Commits), local pinned copy, not published; "
                 f"pack SHA-256 `{art['seed_pack_sha256']}`; seed file-set identity `{art['seed_manifest_sha256']}` "
                 "(pack, idx, rev, bitmap, refs, `mapping.json`, corpus `checkpoint-manifest.json` "
                 "`03f21acf…334271`, state-157 oracle `10e705a3…295e3c`)"),
        ("Workload", f"`{cases.WORKLOAD_VERSION}`: empty project → per state one Exec `apply.py <prev> <k>` + one Commit → final `verify.py 157`"),
        ("Write method", cases.WRITE_METHOD),
        ("Storage policy", cases.STORAGE_POLICY + " (fixed in 2.0; recorded, not varied)"),
        ("Machine", "Docker only (private home, `LAYERFS_CONSTRUCTION_WORKERS=1`); " + config.get("environment_description", "")),
        ("PostgreSQL", f"{config['postgresql']['server_image']}, container `{config['postgresql']['server_container']}`, one fresh empty database per row, `--synchronous-commit off`"),
        ("Command bound", f"each CLI call {config.get('command_timeout_s')} s; no retries"),
        ("Campaigns", ", ".join(f"`{c['campaign_id']}`" for c in campaigns) + (f"; repeat `{repeat['campaign']}`" if repeat else "")),
    ]
    lines += sr.table(["Item", "Value"], [[a, b] for a, b in cfg]).splitlines()
    lines += ["", "## Rows", ""]
    body = []
    for r in table_rows:
        row = r["row"]
        body.append([
            r["case"], NAMES[r["backend"]], r["campaign"] or "—", r["outcome"],
            str(len(history(row))), row.get("verification", "—"), row.get("cleanup", "—"),
            f"{row.get('wall_ns_ineligible', 0) / 1e9:.1f}" if row else "—",
        ])
    lines += sr.table(["Case", "Database", "Campaign", "Outcome", "Commits", "Verify", "Row cleanup", "Wall s (INELIGIBLE)"], body).splitlines()
    for item in sorted(superseded):
        row = all_rows.get(item, {})
        lines += ["", f"Superseded attempt `{item[0]}` `{item[1]}`: {row.get('execution')} — {row.get('reason')}. "
                  f"{config.get('supersedes', {}).get('reason', '')}"]

    for case_id in cases.CASE_IDS:
        rows = [r for r in table_rows if r["case"] == case_id]
        lines += ["", f"## {case_id}: {len(cases.SELECTIONS[case_id])} states", ""]
        lines += [f"Selection `{cases.SELECTIONS[case_id]}`. Logical bytes (Σ states, files + symlink targets) "
                  f"{sr.b(cases.EXPECTED_LOGICAL_BYTES[case_id])} B; LayerFS Σ Commit `logical` counts regular files only.", ""]
        lines += ["### Store bytes", ""]
        lines += sr.store_bytes_table(rows).splitlines()
        lines += ["", "### Attribution", ""]
        lines += sr.attribution_table(rows).splitlines()
        lines += ["", "### References and ratios", ""]
        ref_bytes = {case_id: storage_refs(refs[case_id])}
        lines += sr.references_bytes_table(ref_bytes, [case_id]).splitlines()
        lines += [""]
        lines += sr.reference_table(rows, ref_bytes).splitlines()
        lines += ["", "Net ÷ whole-file unique is the space amplification against ideal unique (uncompressed) bytes."]
        lines += ["", "### new_stored curve", ""]
        stats_rows = []
        for r in rows:
            st = curve_stats(history(r["row"]))
            if not st:
                continue
            states = cases.SELECTIONS[case_id]
            stats_rows.append([
                NAMES[r["backend"]], sr.b(st["first"]), sr.b(st["rest_sum"]), sr.b(st["rest_median"]),
                sr.b(st["rest_max"]), ", ".join(f"state {states[i]}" for i in st["top"]),
            ])
        lines += sr.table(["Database", "Commit 1 new_stored (B)", "Σ Commits 2… (B)", "Median Commit 2… (B)", "Max Commit 2… (B)", "Largest three"], stats_rows).splitlines()
        curves = {r["backend"]: history(r["row"]) for r in rows if history(r["row"])}
        if curves:
            lines += ["", "<details><summary>Per-Commit bytes</summary>", ""]
            table = sr.commit_curve_table(curves, label="Commit").splitlines()
            states = cases.SELECTIONS[case_id]
            table[0] = table[0].replace("| Commit |", "| Commit | State |", 1)
            table[1] = "| ---: " + table[1]
            for i in range(2, len(table)):
                table[i] = table[i].replace("| ", f"| {i - 1} | ", 1).replace(f"| {i - 1} | {i - 1} |", f"| {i - 1} | {states[i - 2]} |", 1)
            lines += table
            lines += ["", "</details>"]

    lines += ["", "## Determinism", ""]
    if repeat and repeat["summary"]:
        a, b2 = d10["sqlite"]["summary"], repeat["summary"]
        ha, hb = history(d10["sqlite"]["row"]), history(repeat["row"])
        same_stored = [x["new_stored"] for x in ha] == [x["new_stored"] for x in hb]
        same_meta = [x["new_metadata"] for x in ha] == [x["new_metadata"] for x in hb]
        def drow(label, key):
            x, y = a.get(key), b2.get(key)
            return [label, sr.b(x), sr.b(y), sr.signed(y - x) if isinstance(x, int) and isinstance(y, int) else "—"]

        drows = [
            drow("Net file bytes, no WAL (B)", "net_file_bytes"),
            drow("Net WAL bytes (B)", "net_wal_bytes"),
            drow("Net file + WAL (B)", "net_bytes"),
            drow("Net allocated (B)", "net_allocated_bytes"),
            drow("Σ new_stored (B)", "sum_new_stored"),
            drow("Σ new_metadata (B)", "sum_new_metadata"),
        ]
        drift = [abs(x["new_stored"] - y["new_stored"]) for x, y in zip(ha, hb)]
        lines += [f"D10 SQLite repeated once in campaign `{repeat['campaign']}` (outcome {outcome(repeat['row'])}), same product, image and seed. "
                  f"Per-Commit new_stored identical: **{same_stored}** (largest per-Commit difference {sr.b(max(drift) if drift else None)} B); "
                  f"per-Commit new_metadata identical: **{same_meta}**. The Store is not byte-identical on repeat; see the table.", ""]
        lines += sr.table(["Metric", "First run", "Repeat", "Δ"], drows).splitlines()
    else:
        lines += ["Not run."]

    lines += ["", "## Reference pins", ""]
    prow = []
    for case_id in cases.CASE_IDS:
        r = refs[case_id]
        prow.append([case_id, f"`{pins[case_id]}`", f"`{r['input_sha256'][:16]}…`", sr.b(r["git_pack"]["bytes"]),
                     sr.b(r["git_pack"]["pinned_dsh_dedup_v1_bytes"]),
                     sr.signed(r["git_pack"]["bytes"] - r["git_pack"]["pinned_dsh_dedup_v1_bytes"])])
    lines += sr.table(["Case", "references JSON SHA-256", "State manifests", "Git pack+idx recomputed (B)", "dsh-dedup v1.0.0 pin (B)", "Δ (B)"], prow).splitlines()
    lines += [
        "",
        f"Git: {refs['D10']['git_pack']['version']}, {refs['D10']['git_pack']['recipe']}. With `--threads=2` the pack varies by a few kB "
        "between runs (a second D10 run gave 41,801,497 B); the pins (git 2.47.1) are confirmed within 0.02%. "
        "Whole-file unique, Σ tar|zstd-3 (deterministic PAX tar, zstd 1.5.7 `-3 -T1`) and the CDC oracle "
        "(**approximate**: gear 8/16/32 KiB, cutoff 128 KiB, own gear table; Σ min(raw, zstd-3) of unique objects, "
        "no deltas) come from `shared/src/references.py` over the states materialized in the suite image with the "
        "workload's own `apply.py`; state 157 matched its corpus oracle.",
    ]
    lines += ["", "## Observations", ""]
    lines += observations(table_rows, refs)
    lines += ["", "## Limits", ""]
    lines += [
        "- One sample per row on Docker Desktop (arm64 Mac). Byte counts, not speed; no other machine is run.",
        "- SQLite Store bytes are `file.bytes + file.wal_bytes`; the product leaves a WAL after quiesce (capped at 4 MiB here), "
        "which can hold already-checkpointed frames. The parts and the allocated bytes are listed separately.",
        "- PostgreSQL Store bytes are the `layerfs` schema's relation sizes (tables, TOAST, indexes); server WAL is not part of the Store "
        "and is recorded only as a WAL position (diagnostic).",
        "- Bytes outside Commit packs (net − Σ new_stored) are measured once per row, not per Commit: "
        "the CLI exposes no Store-wide total between Commits without closing the Workspace.",
        "- The CDC oracle is approximate and has no delta encoding, so it is a dedup-only reference, not a lower bound.",
        "- dsh-dedup v1.0.0 numbers came through the SDK route (Init of state 1, older policy history) and are context, not a baseline.",
    ]
    lines += ["", "## Cleanup", ""]
    lines += cleanup_lines(cleanup)
    # shared storage_report leaves "|" unescaped in headers ("Σ tar|zstd-3").
    lines = [line.replace("tar|zstd", "tar\\|zstd") if line.startswith("| ") else line for line in lines]
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text("\n".join(lines) + "\n")
    print(args.output)
    return 0


def observations(table_rows, refs):
    out = [
        "- `new_stored` is all new pack bytes of a Commit and `new_metadata` its metadata subset (LayerFS 2.0 "
        "CommitStatistics), so payload = stored − metadata and the Store bytes no Commit accounts for are "
        "net − Σ new_stored. The spec formula net − (Σ new_stored + Σ new_metadata) counts metadata twice; it is "
        "listed as \"Spec unattributed\" only for comparability."
    ]
    for r in table_rows:
        s = r.get("summary")
        if not s:
            continue
        c = r["case"]
        ref = refs[c]["git_pack"]["bytes"]
        text = (
            f"- {c} {NAMES[r['backend']]}: net {sr.b(s['net_bytes'])} B = {s['net_bytes'] / ref:.3f}× Git pack+idx, "
            f"{s['net_bytes'] / refs[c]['tar_zstd']['bytes']:.3f}× Σ tar|zstd-3, {s['net_bytes'] / refs[c]['cdc_oracle']['bytes']:.3f}× the CDC oracle. "
            f"Σ new_stored {sr.b(s['sum_new_stored'])} B = {s['sum_new_stored'] / ref:.3f}× Git (payload {sr.b(s['sum_new_payload'])} B, "
            f"metadata {sr.b(s['sum_new_metadata'])} B); net − Σ new_stored {sr.signed(s['unattributed_after_packs_bytes'])} B "
            f"({s['unattributed_after_packs_bytes'] / s['net_bytes']:.1%} of net)"
        )
        if r["backend"] == "sqlite" and isinstance(s.get("net_file_bytes"), int):
            text += (f"; file-only net (no WAL) {sr.b(s['net_file_bytes'])} B = {s['net_file_bytes'] / ref:.3f}× Git, "
                     f"WAL {sr.b(s['net_wal_bytes'])} B")
        wal = storage.server_wal_bytes(r["row"]) if r["backend"] == "postgresql" else None
        if isinstance(wal, int):
            text += f"; server WAL generated floor→final {sr.b(wal)} B (diagnostic, not Store bytes)"
        out.append(text + ".")
    ctx = cases.DSH_DEDUP_V1_ALLOCATED_BYTES
    out.append(
        f"- Context only: dsh-dedup v1.0.0 (SDK route, Init of state 1, older policy history) recorded {sr.b(ctx['D10'])} B (D10) and "
        f"{sr.b(ctx['D03'])} B (D03) of Store allocation, with offline payload 41,472,751 B / 51,897,185 B and metadata "
        "1,325,047 B / 2,457,063 B. Not comparable as a baseline."
    )
    return out


def cleanup_lines(cleanup):
    lines = [f"Final cleanup: **{cleanup.get('cleanup')}**."]
    for item in cleanup.get("released", []):
        lines.append(f"- {item}")
    for item in cleanup.get("retained", []):
        lines.append(f"- Retained: {item}")
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
