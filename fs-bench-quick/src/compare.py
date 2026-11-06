#!/usr/bin/env python3
"""Before -> after tables from two retained fs-bench-quick receipt trees (no product calls).

  compare.py --before ROWS_DIR --after ROWS_DIR [--before-label L] [--after-label L]

ROWS_DIR holds <cell>/<machine>/<backend>/receipt.json. Prints Markdown: row outcomes,
per machine x backend phase medians, PostgreSQL - SQLite gaps per machine (and the Docker
co-located arm), per-phase pg_stat_statements counts and Commit storage. Medians are over the
cells that PASS in both trees for that machine/arm. One sample per row; timings are diagnostic.
"""

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

MACHINES = ("native", "docker", "lima", "apple-container")
ARMS = {"native": ("sqlite", "postgresql"), "docker": ("sqlite", "postgresql", "pg-colocated"),
        "lima": ("sqlite", "postgresql"), "apple-container": ("sqlite", "postgresql")}
PHASES = (("create", "sandbox_create"), ("mount", "measured_mount"), ("Exec", "exec"),
          ("Commit", "commit"), ("unmount", "unmount"))
COUNT_PHASES = ("sandbox_create", "measured_mount", "exec", "commit", "commit_2", "unmount")


def load(root):
    rows = {}
    for path in sorted(Path(root).glob("*/*/*/receipt.json")):
        cell, machine, backend = path.parts[-4:-1]
        rows[(cell, machine, backend)] = json.loads(path.read_text())
    return rows


def ok(r):
    return r is not None and r.get("execution") == "PASS"


def ms(r, key):
    v = (r or {}).get("timings_ns", {}).get(key)
    return None if v is None else v / 1e6


def med(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def f0(v, sign=False):
    if v is None:
        return "—"
    return f"{v:+.0f}" if sign else f"{v:.0f}"


def counts(r, phase):
    p = (r or {}).get("pg_phases", {}).get(phase)
    if not p:
        return None
    return f"{p.get('statements', '?')}/{p.get('connections', '?')}"


def stored(r, key):
    return (((r or {}).get("commit") or {}).get("commit") or {}).get(key)


def outcomes(label, rows):
    c = Counter(r.get("execution", "NO_RECEIPT") for r in rows.values())
    out = [f"- {label}: {dict(c)} of {len(rows)}"]
    for key, r in sorted(rows.items()):
        if not ok(r):
            out.append(f"  - {'/'.join(key)}: {r.get('execution')} — {str(r.get('reason', ''))[:200]}")
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--before", required=True)
    p.add_argument("--after", required=True)
    p.add_argument("--before-label", default="before")
    p.add_argument("--after-label", default="after")
    a = p.parse_args(argv)
    B, A = load(a.before), load(a.after)
    cells = sorted({k[0] for k in A} | {k[0] for k in B})
    lines = ["### Row outcomes", ""] + outcomes(a.before_label, B) + outcomes(a.after_label, A) + [""]

    lines += [f"### Per machine × backend medians, {a.before_label} → {a.after_label}, ms", "",
              "Median over the cells that PASS in both campaigns for that machine/arm (`n`). One sample per row.", "",
              "| machine | backend | n | " + " | ".join(n for n, _ in PHASES) + " |",
              "|---|---|---:|" + "---|" * len(PHASES)]
    for m in MACHINES:
        for arm in ARMS[m]:
            both = [c for c in cells if ok(B.get((c, m, arm))) and ok(A.get((c, m, arm)))]
            parts = [f"{f0(med(ms(B[(c, m, arm)], k) for c in both))} → {f0(med(ms(A[(c, m, arm)], k) for c in both))}"
                     for _, k in PHASES]
            lines.append(f"| {m} | {arm} | {len(both)} | " + " | ".join(parts) + " |")

    lines += ["", f"### PostgreSQL − SQLite median gap per machine, {a.before_label} → {a.after_label}, ms", "",
              "Median over cells of (PostgreSQL row − SQLite row), cells where both arms PASS in both campaigns. "
              "`coloc` is the Docker co-located arm minus Docker SQLite.", "",
              "| machine | arm | n | " + " | ".join(n for n, _ in PHASES) + " |",
              "|---|---|---:|" + "---|" * len(PHASES)]
    for m in MACHINES:
        for arm in [x for x in ARMS[m] if x != "sqlite"]:
            both = [c for c in cells if all(ok(T.get((c, m, x))) for T in (A, B) for x in ("sqlite", arm))]
            parts = []
            for _, k in PHASES:
                gb = med(ms(B[(c, m, arm)], k) - ms(B[(c, m, "sqlite")], k) for c in both
                         if ms(B[(c, m, arm)], k) is not None and ms(B[(c, m, "sqlite")], k) is not None)
                ga = med(ms(A[(c, m, arm)], k) - ms(A[(c, m, "sqlite")], k) for c in both
                         if ms(A[(c, m, arm)], k) is not None and ms(A[(c, m, "sqlite")], k) is not None)
                parts.append(f"{f0(gb, True)} → {f0(ga, True)}")
            lines.append(f"| {m} | {'coloc' if arm == 'pg-colocated' else 'pg'} | {len(both)} | " + " | ".join(parts) + " |")

    lines += ["", f"### pg_stat_statements per phase, Docker PostgreSQL (published port), statements/connections "
              f"{a.before_label} → {a.after_label}", "",
              "| cell | create | mount | Exec | Commit | Commit 2 | unmount |", "|---|---|---|---|---|---|---|"]
    for c in cells:
        b, r = B.get((c, "docker", "postgresql")), A.get((c, "docker", "postgresql"))
        parts = []
        for ph in COUNT_PHASES:
            x, y = counts(b, ph), counts(r, ph)
            parts.append("" if x is None and y is None else f"{x or '—'} → {y or '—'}")
        lines.append(f"| {c} | " + " | ".join(parts) + " |")

    lines += ["", f"### pg_stat_statements per phase and route, {a.after_label} (statements/connections)", "",
              "| cell | phase | native | docker | lima | apple | docker coloc |", "|---|---|---|---|---|---|---|"]
    routes = (("native", "postgresql"), ("docker", "postgresql"), ("lima", "postgresql"),
              ("apple-container", "postgresql"), ("docker", "pg-colocated"))
    for c in cells:
        for ph in COUNT_PHASES:
            vals = [counts(A.get((c, m, arm)), ph) for m, arm in routes]
            if any(vals) and any(v not in ("0/0", None) for v in vals):
                lines.append(f"| {c} | {ph} | " + " | ".join(v or "—" for v in vals) + " |")

    lines += ["", f"### Storage recorded by Commit (bytes), Docker rows, {a.before_label} → {a.after_label}", "",
              "`new_stored` / `new_metadata` from the Commit result. No database file size is recorded.", "",
              "| cell | SQLite new_stored | PostgreSQL new_stored | co-located new_stored | SQLite new_metadata | PostgreSQL new_metadata |",
              "|---|---|---|---|---|---|"]
    for c in cells:
        row = []
        for key, arm in (("new_stored", "sqlite"), ("new_stored", "postgresql"), ("new_stored", "pg-colocated"),
                         ("new_metadata", "sqlite"), ("new_metadata", "postgresql")):
            x, y = stored(B.get((c, "docker", arm)), key), stored(A.get((c, "docker", arm)), key)
            row.append("—" if x is None and y is None else f"{x if x is not None else '—'} → {y if y is not None else '—'}")
        lines.append(f"| {c} | " + " | ".join(row) + " |")

    loads = [r.get("load_1m") for r in A.values() if r.get("load_1m") is not None]
    if loads:
        lines += ["", f"{a.after_label} 1-minute load at row start: min {min(loads):.1f}, median "
                      f"{statistics.median(loads):.1f}, max {max(loads):.1f}."]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
