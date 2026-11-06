#!/usr/bin/env python3
"""Publish the fs-storage-history report from local row results.

    report.py --results DIR --references refs.json --environment E \
        [--determinism probe-result.json] [--cleanup cleanup.json] \
        [--notes notes.md] --output result/<date>/fs-storage-history/<sha>/report.md

DIR holds `<case>-<backend>/result.json` for each row. Raw results, ledgers
and references stay local; only the Markdown report is published.
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
sys.path.insert(1, str(SRC.parents[1] / "shared" / "src"))

import cases  # noqa: E402
import model  # noqa: E402
import storage  # noqa: E402
from storage_report import UNITS_NOTE, b, mb, mib, ratio, signed, table  # noqa: E402

BACKENDS = ("sqlite", "postgresql")
NAMES = {"sqlite": "SQLite", "postgresql": "PostgreSQL"}


SUPERSEDED = []  # (case, backend, attempt dir, row) of attempts replaced by a rerun


def load(results):
    """The latest attempt per row: `<case>-<backend>`, then `-r2`, `-r3`, …"""
    rows = {}
    SUPERSEDED.clear()
    for case_id in cases.CASE_IDS:
        for backend in BACKENDS:
            attempts = []
            for suffix in [""] + [f"-r{i}" for i in range(2, 10)]:
                path = Path(results) / f"{case_id}-{backend}{suffix}" / "result.json"
                if path.exists():
                    attempts.append((path.parent.name, json.loads(path.read_text())))
            if attempts:
                rows[(case_id, backend)] = attempts[-1][1]
                SUPERSEDED.extend((case_id, backend, name, row) for name, row in attempts[:-1])
    return rows


def superseded_table():
    out = [[c, NAMES[k], name, row["execution"], row.get("cleanup"), row.get("reason") or "—"]
           for c, k, name, row in SUPERSEDED]
    return table(["Case", "Backend", "Attempt", "Execution", "Cleanup", "Reason"], out) if out else ""


def outcome(row):
    if row is None:
        return "NOT_RUN"
    return "PASS" if row["execution"] == "PASS" and row["verification"] == "PASS" else "FAIL"


def branches(row):
    for store in row["stores"]:
        for project in store["projects"]:
            for branch in project["branches"]:
                yield store, project, branch


def spread(values):
    if not values:
        return ("—",) * 4
    return (b(min(values)), b(int(statistics.median(values))), b(round(statistics.mean(values))),
            b(max(values)))


def file_part(row, key):
    """Σ over Stores of a probe field at final minus floor (SQLite parts)."""
    total = 0
    for store in row["stores"]:
        a, f = store.get("final", {}).get(key), store["floor"].get(key)
        if not isinstance(a, int) or not isinstance(f, int):
            return None
        total += a - f
    return total


def init_part(row, key):
    total = 0
    for store in row["stores"]:
        a, f = store["init_floor"].get(key), store["floor"].get(key)
        if not isinstance(a, int) or not isinstance(f, int):
            return None
        total += a - f
    return total


def summary_table(rows):
    out = []
    for case_id in cases.CASE_IDS:
        for backend in BACKENDS:
            row = rows.get((case_id, backend))
            if row is None:
                out.append([case_id, NAMES[backend], "NOT_RUN"] + ["—"] * 10)
                continue
            t = row.get("totals", {})
            stored, meta = t.get("sum_new_stored"), t.get("sum_new_metadata")
            payload = stored - meta if isinstance(stored, int) and isinstance(meta, int) else None
            after = t["growth"] - stored if isinstance(stored, int) and "growth" in t else None
            out.append([
                case_id, NAMES[backend], outcome(row), b(t.get("commits")), b(t.get("floor")),
                b(t.get("init")), b(t.get("final")), b(t.get("net")), b(t.get("growth")),
                b(stored), b(payload), b(meta), signed(after),
            ])
    return table(["Case", "Backend", "Outcome", "Commits", "Floor (B)", "Init (B)", "Final (B)",
                  "Net (B)", "Growth after Init (B)", "Σ new_stored (B)", "of which payload (B)",
                  "of which metadata (B)", "Unattributed after Init and packs (B)"], out)


def server_wal(row):
    """PostgreSQL server WAL between each Store's floor and final probes, summed (server-wide)."""
    total = 0
    for store in row["stores"]:
        try:
            a = storage.pg_lsn_bytes(store["floor"]["server_wal_lsn"])
            z = storage.pg_lsn_bytes(store["final"]["server_wal_lsn"])
        except (KeyError, ValueError, TypeError, AttributeError):
            return None
        total += z - a
    return total


def postgresql_table(rows):
    out = []
    for case_id in cases.CASE_IDS:
        row = rows.get((case_id, "postgresql"))
        if row is None or not row.get("totals", {}).get("complete"):
            continue
        out.append([case_id, b(row["totals"]["net"]), b(server_wal(row))])
    return table(["Case", "Net schema bytes (B)", "Server WAL floor→final (B, server-wide)"], out)


def sqlite_parts_table(rows):
    out = []
    for case_id in cases.CASE_IDS:
        row = rows.get((case_id, "sqlite"))
        if row is None or not row.get("totals", {}).get("complete"):
            continue
        growth = file_part(row, "file_bytes") - init_part(row, "file_bytes")
        stored = row["totals"]["sum_new_stored"]
        out.append([case_id, b(init_part(row, "file_bytes")), b(file_part(row, "file_bytes")),
                    b(file_part(row, "wal_bytes")), b(row["totals"]["net"]),
                    b(file_part(row, "allocated_bytes")), b(growth), signed(growth - stored)])
    return table(["Case", "Init, file only (B)", "Net, file only (B)", "Net WAL (B)",
                  "Net, file + WAL (B)", "Net allocated (B)", "Growth after Init, file only (B)",
                  "File-only growth − Σ new_stored (B)"], out)


def commit_rows(row):
    seen, out = set(), []
    for _, _, branch in branches(row):
        for item in branch.get("history") or []:
            if item["id"] not in seen:
                seen.add(item["id"])
                out.append(item)
    return out


def h01_section(rows):
    lines = ["Per-Commit `new_stored` and `new_metadata` (B) from the paged `commit list`, "
             "in blocks of 50 Commits (Commit 1 is the oldest):", ""]
    data = {}
    for backend in BACKENDS:
        row = rows.get(("H01", backend))
        if row and row.get("totals", {}).get("complete"):
            store, project, branch = next(branches(row))
            data[backend] = branch.get("history") or []
    if not data:
        return "No complete H01 row."
    length = max(len(v) for v in data.values())
    out = []
    for start in range(0, length, 50):
        cells = [f"{start + 1}–{min(start + 50, length)}"]
        for backend in BACKENDS:
            block = data.get(backend, [])[start:start + 50]
            stored = [c["new_stored"] for c in block]
            meta = [c["new_metadata"] for c in block]
            cells += [b(sum(stored)) if block else "—",
                      b(round(statistics.mean(stored))) if block else "—",
                      b(max(stored)) if block else "—",
                      b(sum(meta)) if block else "—"]
        out.append(cells)
    headers = ["Commits"]
    for backend in BACKENDS:
        n = NAMES[backend]
        headers += [f"{n} Σ new_stored (B)", f"{n} mean new_stored (B)",
                    f"{n} max new_stored (B)", f"{n} Σ new_metadata (B)"]
    lines.append(table(headers, out))
    lines.append("")
    growth = []
    for backend in BACKENDS:
        row = rows.get(("H01", backend))
        if row and row.get("totals", {}).get("complete"):
            t = row["totals"]
            growth.append([NAMES[backend], b(t["growth"]), b(round(t["growth"] / t["commits"])),
                           b(round(t["sum_new_stored"] / t["commits"])),
                           b(round((t["sum_new_stored"] - t["sum_new_metadata"]) / t["commits"])),
                           b(round(t["sum_new_metadata"] / t["commits"])), b(t["head_logical"])])
    lines.append(table(["Backend", "Growth after Init (B)", "Growth per Commit (B)",
                        "new_stored per Commit (B)", "payload per Commit (B)",
                        "new_metadata per Commit (B)", "Head logical (B)"], growth))
    return "\n".join(lines)


def branch_section(rows, case_id):
    out = []
    for backend in BACKENDS:
        row = rows.get((case_id, backend))
        if not row or not row.get("totals", {}).get("complete"):
            out.append([NAMES[backend]] + ["—"] * 11)
            continue
        own = [x["sum_new_stored"] for _, _, x in branches(row)]
        meta = [x["sum_new_metadata"] for _, _, x in branches(row)]
        delta = [x["marginal_bytes"] for _, _, x in branches(row)]
        count = len(own)
        t = row["totals"]
        out.append([NAMES[backend], b(count), *spread(own), b(round(statistics.mean(meta))),
                    *spread(delta), b(round(t["growth"] / count))])
    return table(["Backend", "Branches", "Own Σ new_stored: min (B)", "median (B)", "mean (B)",
                  "max (B)", "of which metadata, mean (B)", "Store delta per Branch: min (B)",
                  "median (B)", "mean (B)", "max (B)", "Growth after Init ÷ Branches (B)"], out)


def h04_levels(rows):
    out = []
    for backend in BACKENDS:
        row = rows.get(("H04", backend))
        if not row or not row.get("totals", {}).get("complete"):
            continue
        for _, _, x in branches(row):
            out.append([NAMES[backend], x["name"], x["from"], b(x["listed_commits"]),
                        b(x["sum_new_stored"]), b(x["sum_new_metadata"]), b(x["marginal_bytes"])])
    return table(["Backend", "Branch", "Forked from", "Commits listed", "Own Σ new_stored (B)",
                  "Own Σ new_metadata (B)", "Store delta (B)"], out)


def project_section(rows):
    lines = []
    out = []
    for case_id in ("H05", "H06"):
        for backend in BACKENDS:
            row = rows.get((case_id, backend))
            if not row or not row.get("totals", {}).get("complete"):
                out.append([case_id, NAMES[backend]] + ["—"] * 6)
                continue
            if case_id == "H05":
                store = row["stores"][0]
                inits, previous = [], store["floor"]["total_bytes"]
                for project in store["projects"]:
                    inits.append(project["after_init"] - previous)
                    previous = project["after_init"]
            else:
                inits = [s["accounting"]["init"] for s in row["stores"]]
            own = [p["sum_new_stored"]
                   for s in row["stores"] for p in s["projects"]]
            out.append([case_id, NAMES[backend], b(inits[0]), b(min(inits[1:] or inits)),
                        b(round(statistics.mean(inits[1:] or inits))), b(max(inits[1:] or inits)),
                        b(round(statistics.mean(own))),
                        b(round(row["totals"]["net"] / len(own)))])
    lines.append(table(["Case", "Backend", "First project Init (B)", "Later Inits: min (B)",
                        "mean (B)", "max (B)", "Own Σ new_stored per project (B)",
                        "Net ÷ projects (B)"], out))
    lines.append("")
    gain = []
    for backend in BACKENDS:
        h05, h06 = rows.get(("H05", backend)), rows.get(("H06", backend))
        if not (h05 and h06 and h05["totals"].get("complete") and h06["totals"].get("complete")):
            gain.append([NAMES[backend]] + ["—"] * 7)
            continue
        a, s = h05["totals"], h06["totals"]
        gain.append([NAMES[backend], b(a["net"]), b(s["net"]), ratio(s["net"] / a["net"], 2),
                     b(a["init"]), b(s["init"]), ratio(s["init"] / a["init"], 2),
                     ratio(s["final"] / a["final"], 2)])
    lines.append(table(["Backend", "H05 net (B)", "Σ H06 net (B)", "Cross-project gain Σ H06 ÷ H05 (net)",
                        "H05 Init (B)", "Σ H06 Init (B)", "Gain on Init", "Σ H06 final ÷ H05 final"],
                       gain))
    return "\n".join(lines)


def reference_section(rows, refs):
    lines = ["Computed once offline from the oracle states ([src/refs.py](../../../../fs-storage-history/src/refs.py)); "
             f"input digest `{refs.get('input_sha256', '—')}`. H06 references are Σ over its 20 "
             "separate Stores/repositories. The CDC oracle is approximate (different gear table).", ""]
    out = []
    for case_id in cases.CASE_IDS:
        r = refs.get("cases", {}).get(case_id)
        if not r:
            continue
        t = r["total"]
        out.append([case_id, b(t["states"]), b(t["logical_bytes"]), b(t["whole_file_unique"]["bytes"]),
                    b(t["tar_zstd"]["bytes"]), b(t["git_pack"]["bytes"]), b(t["cdc_oracle"]["bytes"])])
    lines.append(table(["Case", "States", "Σ logical (B)", "Whole-file unique (B)",
                        "Σ tar | zstd -3 (B)", "Git pack + idx (B)", "CDC oracle, approx. (B)"], out))
    lines.append("")
    out = []
    for case_id in cases.CASE_IDS:
        r = refs.get("cases", {}).get(case_id)
        for backend in BACKENDS:
            row = rows.get((case_id, backend))
            if not r or not row or not row.get("totals", {}).get("complete"):
                continue
            t, net = r["total"], row["totals"]["net"]
            out.append([case_id, NAMES[backend], b(net), ratio(t["logical_bytes"] / net, 1),
                        ratio(net / t["whole_file_unique"]["bytes"]),
                        ratio(net / t["tar_zstd"]["bytes"], 4), ratio(net / t["git_pack"]["bytes"]),
                        ratio(net / t["cdc_oracle"]["bytes"])])
    lines.append(table(["Case", "Backend", "Net (B)", "Σ logical ÷ net", "Net ÷ whole-file unique",
                        "Net ÷ Σ tar|zstd", "Net ÷ Git pack", "Net ÷ CDC oracle"], out))
    return "\n".join(lines)


def opcost_section(rows):
    import opcost

    out = []
    for backend in BACKENDS:
        fits = {}
        for field in ("new_stored", "new_metadata"):
            points = []
            for case_id in ("H01", "H02", "H04", "H05", "H07"):
                row = rows.get((case_id, backend))
                if row and outcome(row) == "PASS":
                    points += opcost.samples(row, field)
            fits[field] = opcost.fit(points) if points else (None, 0)
        stored, count = fits["new_stored"]
        meta, _ = fits["new_metadata"]
        if not stored or not meta:
            continue
        for kind in opcost.KINDS:
            out.append([NAMES[backend], kind, b(count), b(round(stored[kind])),
                        b(round(stored[kind] - meta[kind])), b(round(meta[kind]))])
    return ("Least-squares fit of per-Commit bytes on the five operation counts over every Commit "
            "of H01, H02, H04, H05 and H07 (no intercept; the counts always sum to 5, so each "
            "coefficient carries a fifth of the fixed per-Commit cost). Differences between kinds "
            "are the useful part; this is a diagnostic estimate, not a measurement.\n\n"
            + table(["Backend", "Operation", "Commits", "new_stored per op (B)",
                     "payload per op (B)", "new_metadata per op (B)"], out))


def lifecycle_table(rows):
    out = []
    for case_id in cases.CASE_IDS:
        for backend in BACKENDS:
            row = rows.get((case_id, backend))
            if row is None:
                out.append([case_id, NAMES[backend], "NOT_RUN", "—", "—", "—", "—", "—"])
                continue
            heads = [x["verification"] for _, _, x in branches(row)]
            out.append([case_id, NAMES[backend], row["execution"],
                        f"{heads.count('PASS')}/{len(heads)}", row["cleanup"], b(len(row["stores"])),
                        b(row.get("calls")), f"{row['wall_ns_ineligible'] / 1e9:.1f}" if row.get("wall_ns_ineligible") else "—"])
    return table(["Case", "Backend", "Execution", "Heads verified", "Cleanup", "Stores", "CLI/Docker calls",
                  "Row wall (s, INELIGIBLE)"], out)


def counts_table():
    out = []
    for case_id in cases.CASE_IDS:
        s = cases.shape(case_id)
        projects = sum(len(x["projects"]) for x in s)
        heads = sum(len(p["branches"]) for x in s for p in x["projects"])
        out.append([case_id, cases.TITLES[case_id], b(len(s)), b(projects), b(heads),
                    b(cases.commit_count(case_id)), cases.SHOWS[case_id]])
    return table(["Case", "Shape", "Stores", "Projects", "Branches", "Commits", "What it shows"], out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True)
    parser.add_argument("--references", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--notes", help="Markdown with outcome, observations, limits and cleanup")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    rows = load(args.results)
    refs = json.loads(Path(args.references).read_text())
    config = json.loads(Path(args.environment).read_text())
    notes = Path(args.notes).read_text() if args.notes else ""
    sections = notes.split("\n## ")
    head, rest = sections[0].strip(), ["## " + s for s in sections[1:]]
    a = config["artifacts"]
    any_row = next(iter(rows.values()), {})
    workloads = {c: r["workload"].get("workload_sha256") for (c, _), r in rows.items()}
    text = [
        "# fs-storage-history report", "",
        head, "",
        "## Configuration", "",
        table(["Item", "Value"], [
            ["LayerFS source", f"`{config['source_sha']}` (`layerfs_v2_0_0`)"],
            ["CLI / daemon SHA-256", f"`{a['cli_sha256']}` / `{a['daemon_sha256']}`"],
            ["Linux bundle seal", f"`{a['linux_bundle_sha256']}` (release)"],
            ["Sandbox image", f"`{a['sandbox_image_tag']}` = `{a['sandbox_image']}`, FROM `{a['base_image']}`"],
            ["Edit model", f"`{model.MODEL_VERSION}`, `src/model.py` SHA-256 `{a['model_sha256']}`"],
            ["Workload", f"`{cases.WORKLOAD_VERSION}`"],
            ["Machine", "Docker only (built-in `docker` machine, private home, `LAYERFS_CONSTRUCTION_WORKERS=1`)"],
            ["PostgreSQL", f"own container `fsh-pg`, {config['postgresql']['server_image']}, 1 CPU, 512 MiB, one pre-created empty database per Store, `synchronous_commit=off`"],
            ["Base tree", f"DSH checkpoint {cases.BASE_CHECKPOINT}: commit `{cases.BASE_COMMIT}`, tree `{cases.BASE_TREE}`, "
                          f"{cases.BASE_FILES:,} files + {cases.BASE_LINKS} symlinks, {cases.BASE_BYTES:,} B; "
                          f"manifest `{cases.BASE_MANIFEST_SHA256}`; seed pack `{cases.SEED_PACK_SHA256}`"],
            ["Storage policy", "; ".join(f"{k}: {v}" for k, v in storage.POLICY.items() if k != "note")],
        ]), "",
        "Each Commit applies five operations drawn from `(seed, step)` with a BLAKE2b counter PRNG: "
        "70% small text edit of 1–5 lines (in place, same inode, `O_WRONLY|O_TRUNC`), 10% new 256–4,096 B "
        "synthetic text file (new path), 5% delete (unlink), 10% rename (`rename(2)`, 80% same directory), "
        "5% append of one 80–240 B line to a `*.jsonl`/`*.log` file (in place, `O_APPEND`). Every project "
        "imports the base with `project init`; Branches are forked with `branch fork` and committed through "
        "one Sandbox each (`workspace exec` + `workspace commit` per step). Each Branch head is verified once, "
        "in a fresh mount, against the oracle digest (path, type, mode, size, SHA-256; no missing, extra or "
        "empty-directory paths).", "",
        counts_table(), "",
        "Workload digests: " + ", ".join(f"{c} `{w[:16]}…`" for c, w in sorted(workloads.items())
                                          if w and _first_backend(rows, c)), "",
        UNITS_NOTE, "",
        "**Floor** = Store bytes after `store create`/`connect` + `project init` of an empty folder "
        "(+ `store push` for SQLite). **Init** = after every base `project init` − floor (the Init floor). "
        "**Net** = final − floor. **Growth after Init** = final − Init floor. SQLite bytes are "
        "`file.bytes + file.wal_bytes`; PostgreSQL bytes are `server.schemas.layerfs`. In LayerFS 2.0 "
        "`new_stored` counts every new pack byte of a Commit and `new_metadata` is a subset of it, so "
        "payload = new_stored − new_metadata and **unattributed after Init and packs** = growth − "
        "Σ new_stored over distinct Commits (database pages, indexes, free space and WAL). The spec's "
        "net − (Σ new_stored + Σ new_metadata) counts metadata twice and is not used.", "",
        "## Lifecycle", "",
        lifecycle_table(rows), "",
        *(["Superseded attempts (kept as local evidence; see Observations):", "",
           superseded_table(), ""] if SUPERSEDED else []),
        "## Store bytes", "",
        summary_table(rows), "",
        "SQLite parts (Σ over Stores). The product keeps a WAL of up to 4 MiB after quiesce, "
        "so file-only figures are shown beside file + WAL:", "",
        sqlite_parts_table(rows), "",
        "PostgreSQL server WAL (the server is owned and serves one row at a time, but the LSN is "
        "server-wide):", "",
        postgresql_table(rows), "",
        "## H01 long history", "",
        h01_section(rows), "",
        "## H02 many branches", "",
        branch_section(rows, "H02"), "",
        "## H03 identical branches", "",
        branch_section(rows, "H03"), "",
        "## H04 nested forks", "",
        branch_section(rows, "H04"), "",
        h04_levels(rows), "",
        "## H05 and H06: projects in one Store vs separate Stores", "",
        project_section(rows), "",
        "## H07 combined", "",
        branch_section(rows, "H07"), "",
        "## Cost per operation kind", "",
        opcost_section(rows), "",
        "## References", "",
        reference_section(rows, refs), "",
        *[s.strip() + "\n" for s in rest],
    ]
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text("\n".join(text).rstrip() + "\n")
    print(args.output)
    del any_row
    return 0


def _first_backend(rows, case_id):
    return any((case_id, backend) in rows for backend in BACKENDS)


if __name__ == "__main__":
    sys.exit(main())
