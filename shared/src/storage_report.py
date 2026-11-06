#!/usr/bin/env python3
"""Markdown pieces for storage reports: exact bytes, labelled units, tables.

Bytes are exact integers (``12,345,678``). MB = 10^6 B and MiB = 2^20 B are
always labelled. Tables are grouped by case with SQLite before PostgreSQL.
Suites compose their own report from these helpers; ``shared/src/report.py``
(speed suites) is untouched.
"""

from __future__ import annotations

BACKENDS = ("sqlite", "postgresql")
BACKEND_NAMES = {"sqlite": "SQLite", "postgresql": "PostgreSQL"}
UNITS_NOTE = (
    "Bytes are exact integers. MB = 10⁶ B; MiB = 2²⁰ B = 1,048,576 B. "
    "Wall times are INELIGIBLE diagnostics, never speed claims."
)


def safe(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def b(value):
    """Exact integer bytes with thousands separators, or a dash."""
    return f"{value:,}" if isinstance(value, int) else "—"


def signed(value):
    return f"{value:+,}" if isinstance(value, int) else "—"


def mb(value):
    return f"{value / 1e6:.3f}" if isinstance(value, (int, float)) else "—"


def mib(value):
    return f"{value / 1048576:.3f}" if isinstance(value, (int, float)) else "—"


def ratio(value, digits=3):
    return f"{value:.{digits}f}" if isinstance(value, (int, float)) else "—"


def table(headers, rows):
    lines = ["| " + " | ".join(safe(h) for h in headers) + " |", "| " + " | ".join(
        "---:" if h.endswith(")") or h.startswith("Σ") or h[:1].isdigit() else "---"
        for h in headers
    ) + " |"]
    lines += ["| " + " | ".join(safe(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def ordered(rows):
    """Rows sorted by case then SQLite before PostgreSQL."""
    return sorted(rows, key=lambda r: (r["case"], BACKENDS.index(r["backend"])))


def store_bytes_table(rows):
    """One row per (case, backend): floor, final, net and the SQLite parts.

    Each input row: ``{case, backend, outcome, summary, probes}`` where
    ``summary`` is ``storage.summarize`` output.
    """
    headers = [
        "Case", "Database", "Outcome", "Floor (B)", "Final (B)", "Net (B)",
        "Net (MB)", "Net (MiB)", "Net file (B)", "Net WAL (B)", "Net allocated (B)",
    ]
    body = []
    for row in ordered(rows):
        s = row.get("summary") or {}
        body.append([
            row["case"], BACKEND_NAMES[row["backend"]], row.get("outcome", "—"),
            b(s.get("floor_bytes")), b(s.get("final_bytes")), b(s.get("net_bytes")),
            mb(s.get("net_bytes")), mib(s.get("net_bytes")),
            b(s.get("net_file_bytes")), b(s.get("net_wal_bytes")), b(s.get("net_allocated_bytes")),
        ])
    return table(headers, body)


def attribution_table(rows):
    headers = [
        "Case", "Database", "Commits", "Σ logical (B)", "Σ new_canonical (B)",
        "Σ new_stored (B)", "Σ new_metadata (B)", "Σ payload = stored − metadata (B)",
        "Net (B)", "Net − Σ new_stored (B)", "Spec unattributed (B)", "Logical ÷ net",
    ]
    body = []
    for row in ordered(rows):
        s = row.get("summary") or {}
        body.append([
            row["case"], BACKEND_NAMES[row["backend"]], s.get("commits", "—"),
            b(s.get("sum_logical")), b(s.get("sum_new_canonical")), b(s.get("sum_new_stored")),
            b(s.get("sum_new_metadata")), b(s.get("sum_new_payload")), b(s.get("net_bytes")),
            signed(s.get("unattributed_after_packs_bytes")), signed(s.get("unattributed_bytes")),
            ratio(s.get("logical_per_net"), 2),
        ])
    return table(headers, body)


def reference_table(rows, references):
    """``references``: case → {name: bytes}. Net ÷ reference per backend."""
    names = ("whole_file_unique", "tar_zstd", "git_pack", "cdc_oracle")
    labels = {
        "whole_file_unique": "whole-file unique",
        "tar_zstd": "Σ tar|zstd-3",
        "git_pack": "Git pack+idx",
        "cdc_oracle": "CDC oracle (approx.)",
    }
    headers = ["Case", "Database", "Net (B)"] + [f"Net ÷ {labels[n]}" for n in names]
    body = []
    for row in ordered(rows):
        s = row.get("summary") or {}
        refs = references.get(row["case"], {})
        net = s.get("net_bytes")
        cells = []
        for name in names:
            value = refs.get(name)
            cells.append(ratio(net / value) if isinstance(net, int) and isinstance(value, int) and value > 0 else "—")
        body.append([row["case"], BACKEND_NAMES[row["backend"]], b(net)] + cells)
    return table(headers, body)


def references_bytes_table(references, order=None):
    names = ("whole_file_unique", "tar_zstd", "git_pack", "cdc_oracle")
    headers = ["Case", "Whole-file unique (B)", "Σ tar|zstd-3 (B)", "Git pack+idx (B)", "CDC oracle, approx. (B)"]
    body = [
        [case] + [b(references.get(case, {}).get(name)) for name in names]
        for case in (order or sorted(references))
    ]
    return table(headers, body)


def commit_curve_table(histories_by_backend, label="Commit"):
    """Per-Commit bytes side by side: backend → list of commit records."""
    present = [x for x in BACKENDS if x in histories_by_backend]
    headers = [label, "Logical (B)"]
    for backend in present:
        name = BACKEND_NAMES[backend]
        headers += [f"{name} new_stored (B)", f"{name} new_metadata (B)"]
    length = max((len(v) for v in histories_by_backend.values()), default=0)
    body = []
    for index in range(length):
        first = next(
            (histories_by_backend[x][index] for x in present if index < len(histories_by_backend[x])),
            {},
        )
        cells = [str(index + 1), b(first.get("logical"))]
        for backend in present:
            commits = histories_by_backend[backend]
            commit = commits[index] if index < len(commits) else {}
            cells += [b(commit.get("new_stored")), b(commit.get("new_metadata"))]
        body.append(cells)
    return table(headers, body)


REDUCTION_NOTE = (
    "**Raw** is Σ logical: the bytes of every committed snapshot, as if each "
    "were stored in full. **Stored** is the net Store bytes (SQLite: file + "
    "WAL; PostgreSQL: schema). **Raw ÷ stored** is the overall reduction, "
    "= exact dedup × delta + zstd ÷ Store overhead: **exact dedup** = raw ÷ "
    "Σ new_canonical (identical files, chunks and trees stored once); "
    "**delta + zstd** = Σ new_canonical ÷ Σ new_stored (delta encoding and "
    "compression of the new objects); **Store overhead** = stored ÷ Σ "
    "new_stored (database pages, indexes and free space around the packs; "
    "1.35 means the Store is 35% larger than its packs)."
)


def _mb(value):
    return f"{value / 1e6:,.1f}" if isinstance(value, (int, float)) else "—"


def _div(a, b):
    ok = isinstance(a, (int, float)) and isinstance(b, (int, float)) and b > 0
    return a / b if ok else None


def reduction_table(rows, order=None):
    """Headline raw-vs-stored table.

    ``rows``: dicts with ``case``, ``backend``, ``raw`` (Σ logical) and
    ``stored`` (net Store bytes), plus optional ``canonical`` (Σ
    new_canonical) and ``packs`` (Σ new_stored) for the three-factor split.
    Leave those out when the Commit list does not cover everything stored,
    e.g. when a base is imported with ``project init``. ``order`` lists case
    IDs in display order (default: sorted).
    """
    if order:
        rows = sorted(rows, key=lambda r: (list(order).index(r["case"]), BACKENDS.index(r["backend"])))
    else:
        rows = ordered(rows)
    headers = [
        "Case", "Database", "Raw (MB)", "Stored (MB)", "Raw ÷ stored (×)",
        "Exact dedup (×)", "Delta + zstd (×)", "Store overhead (×)",
    ]
    body = []
    for row in rows:
        raw, stored = row.get("raw"), row.get("stored")
        canonical, packs = row.get("canonical"), row.get("packs")
        body.append([
            row["case"], BACKEND_NAMES[row["backend"]], _mb(raw), _mb(stored),
            ratio(_div(raw, stored), 2), ratio(_div(raw, canonical), 2),
            ratio(_div(canonical, packs), 2), ratio(_div(stored, packs), 2),
        ])
    return table(headers, body)


__all__ = [
    "UNITS_NOTE", "REDUCTION_NOTE", "b", "signed", "mb", "mib", "ratio", "table",
    "ordered", "store_bytes_table", "attribution_table", "reference_table",
    "references_bytes_table", "commit_curve_table", "reduction_table",
]
