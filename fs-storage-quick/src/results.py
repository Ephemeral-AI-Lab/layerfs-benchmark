"""Row summaries (export) and baseline-vs-candidate comparison. Pure: no LayerFS.

``export(state, ...)`` turns a campaign's state into the row-summary JSON that
is pinned as a baseline (``baseline/<full-sha>.json``) and that ``compare``
reads. ``compare(baseline, candidate)`` gives, per case × backend, Δ bytes,
Δ% and a noise verdict per metric.

Noise rule (owner rule "±1 page per table; new_metadata ±16 B per Commit"):

* Store bytes (SQLite file, WAL, file + WAL, closed/late bytes; PostgreSQL
  schema bytes): ±1 page per Store table, i.e. ±``SQLITE_TABLES`` × 4,096 B
  (SQLite page) or ±``PG_TABLES`` × 8,192 B (PostgreSQL page). The table counts
  are the ``CREATE TABLE`` statements of the base Store schema
  (``layerfs_v2_0_0`` @ b4fa173e40: SQLite 25, PostgreSQL 22); override with
  ``tables=`` when a schema change adds tables.
* ``new_metadata`` and ``new_stored``: ±16 B per Commit of the row
  (``new_stored`` includes ``new_metadata``).
* ``payload`` (stored − metadata), ``new_canonical``, raw (Σ logical) and the
  Commit count: exact; any difference is outside noise. A raw or Commit-count
  difference means the workload differs and the row is not comparable.

A baseline may also carry, per row, ``repeat_abs_delta``: the |Δ| a second
campaign of the same build measured for each metric (``add_repeat``). The band
of a metric is then max(rule band, that repeat |Δ|): the base repeat showed
Q1's single Commit of 2,000 files drifting +28 B in ``new_metadata``, beyond
16 B per Commit. Workload metrics stay exact.

A Δ inside its band is ``same``; below it ``lower`` (smaller is better for
every metric here), above it ``HIGHER`` (a regression).
"""

import statistics

SQLITE_PAGE = 4096
PG_PAGE = 8192
SQLITE_TABLES = 25
PG_TABLES = 22
METADATA_PER_COMMIT = 16
WAL_HEADER = 32
WAL_FRAME_HEADER = 24
BACKENDS = ("sqlite", "postgresql")


def wal_frames(wal_bytes, page_size=SQLITE_PAGE):
    """WAL frames in a WAL file of ``wal_bytes`` (32 B header + 24 B + page per frame)."""
    if not isinstance(wal_bytes, int) or wal_bytes <= 0:
        return 0 if wal_bytes == 0 else None
    frames, rest = divmod(wal_bytes - WAL_HEADER, WAL_FRAME_HEADER + page_size)
    return frames if rest == 0 else None


def _probe_total(probes, label):
    found = probes.get(label) or {}
    if not found:
        return None
    out = {}
    for field in ("total_bytes", "file_bytes", "wal_bytes", "schema_bytes", "allocated_bytes"):
        values = [p.get(field) for p in found.values()]
        out[field] = None if any(v is None for v in values) else sum(values)
    out["wal_frames"] = wal_frames(out["wal_bytes"]) if out.get("wal_bytes") is not None else None
    lsns = [p.get("server_wal_lsn") for p in found.values() if p.get("server_wal_lsn")]
    if lsns:
        out["server_wal_lsn"] = lsns[0]
    return out


def _commit_timings(row):
    """Per-Commit wall and local CLI CPU from the row's commands, in Commit order."""
    timings = [
        {"wall_ms": round(c["elapsed_ns"] / 1e6, 1) if c.get("elapsed_ns") else None,
         "cli_cpu_ms": round(c["child_cpu_ns"] / 1e6, 1) if c.get("child_cpu_ns") else None}
        for c in row.get("commands", []) if c.get("phase", "").endswith("_commit")
    ]
    results = row.get("commit_results", [])
    return {r.get("id"): {"label": r.get("label"), **t} for r, t in zip(results, timings)}


def _phase_ms(row, suffix):
    return [round(c["elapsed_ns"] / 1e6, 1) for c in row.get("commands", [])
            if c.get("phase", "").endswith(suffix) and c.get("elapsed_ns")]


def row_summary(row, init_logical=0):
    """Compact, comparable summary of one finished campaign row."""
    probes = row.get("probes", {})
    floor, final, late = (_probe_total(probes, x) for x in ("floor", "final", "late"))
    seen, curve = set(), []
    timings = _commit_timings(row)
    for history in row.get("histories", []):
        for commit in history["commits"]:
            if commit["id"] in seen:
                continue
            seen.add(commit["id"])
            timing = timings.get(commit["id"], {})
            curve.append({
                "branch": f"{history['project'].split('/', 1)[-1]}@{history['branch']}",
                "label": timing.get("label"),
                **{k: commit[k] for k in ("logical", "new_canonical", "new_stored", "new_metadata")},
                "wall_ms_ineligible": timing.get("wall_ms"),
                "cli_cpu_ms_ineligible": timing.get("cli_cpu_ms"),
            })

    def net(field, end=final):
        a, b = (end or {}).get(field), (floor or {}).get(field)
        return a - b if isinstance(a, int) and isinstance(b, int) else None

    stored = sum(c["new_stored"] for c in curve)
    metadata = sum(c["new_metadata"] for c in curve)
    commit_walls = [c["wall_ms_ineligible"] for c in curve if c["wall_ms_ineligible"] is not None]
    out = {
        "id": row["id"], "case": row.get("case"), "backend": row.get("backend"),
        "execution": row.get("execution"), "verification": row.get("verification"),
        "cleanup": row.get("cleanup"), "reason": row.get("reason"),
        "commits": len(curve),
        "raw": sum(c["logical"] for c in curve) + init_logical,
        "sum_logical_commits": sum(c["logical"] for c in curve),
        "init_logical": init_logical,
        "sum_new_canonical": sum(c["new_canonical"] for c in curve),
        "sum_new_stored": stored,
        "sum_new_metadata": metadata,
        "sum_new_payload": stored - metadata,
        "floor": floor, "final": final, "late": late,
        "inits": {label: _probe_total(probes, label) for label in sorted(probes) if label.startswith("init_")},
        "net_bytes": net("total_bytes"),
        "net_file_bytes": net("file_bytes"),
        "net_wal_bytes": net("wal_bytes"),
        "net_schema_bytes": net("schema_bytes"),
        "late_net_bytes": net("total_bytes", late) if late else None,
        "late_net_file_bytes": net("file_bytes", late) if late else None,
        "late_net_wal_bytes": net("wal_bytes", late) if late else None,
        "late_idle_s": (row.get("late_probe") or {}).get("idle_s"),
        "late_status": (row.get("late_probe") or {}).get("status", "NOT_RUN"),
        "curve": curve,
        "diagnostics": {
            "label": "INELIGIBLE wall / local CLI process CPU; Commit statistics beyond bytes UNAVAILABLE",
            "row_wall_s": round(row["wall_ns_ineligible"] / 1e9, 1) if row.get("wall_ns_ineligible") else None,
            "commit_wall_ms_sum": round(sum(commit_walls), 1) if commit_walls else None,
            "commit_wall_ms_median": statistics.median(commit_walls) if commit_walls else None,
            "commit_wall_ms_max": max(commit_walls) if commit_walls else None,
            "init_wall_ms": _phase_ms(row, "_project_init")[1:],
            "verify_wall_ms": _phase_ms(row, "_verify"),
            "commit_cpu_worker": "UNAVAILABLE (public CLI reports none)",
            "read_amplification": "UNAVAILABLE (value_lookups/value_rows, decode and delta-depth counters are not in Commit output)",
        },
    }
    if row.get("attribution"):
        out["attribution"] = row["attribution"]
    return out


def export(state, config, cases_module, init_logical=None):
    rows = {}
    for row in state.get("rows", {}).values():
        if row.get("execution") in (None, "NOT_RUN") and not row.get("probes"):
            continue
        key = f"{row['case']}/{row['backend']}" + (f"/r{row['repeat']}" if row.get("repeat", 1) > 1 else "")
        logical = (init_logical or {}).get(row["case"], 0)
        rows[key] = row_summary(row, logical)
    walls = {}
    for backend in BACKENDS:
        mine = [r for r in state.get("rows", {}).values() if r.get("backend") == backend
                and r.get("started_unix_ns") and r.get("finished_unix_ns")]
        if mine:
            walls[backend] = {
                "matrix_wall_s": round((max(r["finished_unix_ns"] for r in mine)
                                        - min(r["started_unix_ns"] for r in mine)) / 1e9, 1),
                "sum_row_wall_s": round(sum(r.get("wall_ns_ineligible", 0) for r in mine) / 1e9, 1),
                "rows": len(mine),
            }
    artifacts = config.get("artifacts", {})
    return {
        "suite": "fs-storage-quick",
        "format": 1,
        "workload_version": cases_module.WORKLOAD_VERSION,
        "gen_sha256": cases_module.GEN_SHA256,
        "model_sha256": cases_module.MODEL_SHA256,
        "pins_sha256": cases_module.PINS_SHA256,
        "campaign_id": state.get("campaign_id"),
        "source_sha": state.get("source_sha"),
        "artifacts": {k: artifacts.get(k) for k in (
            "cli_sha256", "daemon_sha256", "linux_bundle_sha256", "profile", "base_image", "sandbox_image")},
        "late_probe": state.get("late_probe"),
        "wall_ineligible": walls,
        "rows": dict(sorted(rows.items(), key=lambda kv: (kv[0].split("/")[0], BACKENDS.index(kv[0].split("/")[1]), kv[0]))),
    }


# ------------------------------------------------------------------ compare

def store_tolerance(backend, tables=None):
    tables = tables or {}
    if backend == "sqlite":
        return tables.get("sqlite", SQLITE_TABLES) * SQLITE_PAGE
    return tables.get("postgresql", PG_TABLES) * PG_PAGE


def metrics(backend):
    """(name, row key, kind) per backend; kind picks the noise band."""
    common = [
        ("Σ new_stored", "sum_new_stored", "per_commit"),
        ("Σ payload", "sum_new_payload", "exact"),
        ("Σ new_metadata", "sum_new_metadata", "per_commit"),
        ("Σ new_canonical", "sum_new_canonical", "exact"),
        ("raw (Σ logical)", "raw", "workload"),
        ("Commits", "commits", "workload"),
    ]
    if backend == "sqlite":
        store = [
            ("Store file+WAL net", "net_bytes", "store"),
            ("Store file net", "net_file_bytes", "store"),
            ("Store WAL net", "net_wal_bytes", "store"),
            ("Late file+WAL net", "late_net_bytes", "store"),
            ("Late file net", "late_net_file_bytes", "store"),
            ("Late WAL net", "late_net_wal_bytes", "store"),
        ]
    else:
        store = [
            ("Store schema net", "net_bytes", "store"),
            ("Late schema net", "late_net_bytes", "store"),
        ]
    return store + common


def verdict(delta, band):
    if delta is None:
        return "n/a"
    if abs(delta) <= band:
        return "same"
    return "lower" if delta < 0 else "HIGHER"


def compare(baseline, candidate, tables=None):
    """Per case × backend metric deltas with noise verdicts."""
    out = {"rows": [], "regressions": [], "improvements": [], "not_comparable": [], "missing": []}
    if baseline.get("workload_version") != candidate.get("workload_version"):
        out["not_comparable"].append(
            f"workload_version {baseline.get('workload_version')} != {candidate.get('workload_version')}")
    for key, base in baseline["rows"].items():
        cand = candidate["rows"].get(key)
        if cand is None:
            out["missing"].append(key)
            continue
        backend = base["backend"]
        commits = base.get("commits") or 0
        bands = {
            "store": store_tolerance(backend, tables),
            "per_commit": METADATA_PER_COMMIT * commits,
            "exact": 0,
            "workload": 0,
        }
        repeat = base.get("repeat_abs_delta") or {}
        row = {"key": key, "case": base["case"], "backend": backend,
               "baseline_outcome": f"{base.get('execution')}/{base.get('verification')}",
               "candidate_outcome": f"{cand.get('execution')}/{cand.get('verification')}", "metrics": []}
        for name, field, kind in metrics(backend):
            a, b = base.get(field), cand.get(field)
            delta = b - a if isinstance(a, int) and isinstance(b, int) else None
            pct = (delta / a * 100.0) if delta is not None and a else None
            band = bands[kind] if kind == "workload" else max(bands[kind], repeat.get(field) or 0)
            mark = verdict(delta, band)
            row["metrics"].append({"metric": name, "field": field, "baseline": a, "candidate": b,
                                   "delta": delta, "delta_pct": pct, "band": band, "verdict": mark})
            if kind == "workload" and mark not in ("same", "n/a"):
                out["not_comparable"].append(f"{key}: {name} differs ({a} → {b})")
            elif mark == "HIGHER":
                out["regressions"].append(f"{key}: {name} {delta:+,} B ({pct:+.2f}%), band ±{band:,}")
            elif mark == "lower":
                out["improvements"].append(f"{key}: {name} {delta:+,} B ({pct:+.2f}%)")
        if cand.get("verification") != "PASS":
            out["not_comparable"].append(f"{key}: candidate verification {cand.get('verification')}")
        out["rows"].append(row)
    return out


def add_repeat(baseline, repeat):
    """Record, per row and metric, |Δ| between the baseline and a same-build repeat."""
    for key, base in baseline["rows"].items():
        other = repeat["rows"].get(key)
        if other is None:
            continue
        deltas = {}
        for _, field, kind in metrics(base["backend"]):
            a, b = base.get(field), other.get(field)
            if kind != "workload" and isinstance(a, int) and isinstance(b, int):
                deltas[field] = abs(b - a)
        base["repeat_abs_delta"] = deltas
    baseline["repeat"] = {"campaign_id": repeat.get("campaign_id"), "source_sha": repeat.get("source_sha"),
                          "harness": repeat.get("harness"), "wall_ineligible": repeat.get("wall_ineligible")}
    return baseline


def _n(value):
    return f"{value:,}" if isinstance(value, int) else "—"


def compare_markdown(result, baseline, candidate):
    lines = [
        "# fs-storage-quick compare",
        "",
        f"Baseline: `{baseline.get('source_sha')}` ({baseline.get('campaign_id')}); "
        f"candidate: `{candidate.get('source_sha')}` ({candidate.get('campaign_id')}). "
        f"Workload `{candidate.get('workload_version')}`.",
        "",
        "Noise: Store bytes ±1 page per Store table (SQLite "
        f"{SQLITE_TABLES} × 4,096 B = {SQLITE_TABLES * SQLITE_PAGE:,} B; PostgreSQL {PG_TABLES} × 8,192 B = "
        f"{PG_TABLES * PG_PAGE:,} B); new_stored/new_metadata ±16 B per Commit; payload, canonical, raw exact; "
        "each band widened to the baseline's same-build repeat |Δ| where pinned. "
        "`lower` = smaller beyond noise, `HIGHER` = larger beyond noise (regression). Bytes are exact integers.",
        "",
    ]
    for title, items in (("Regressions", result["regressions"]), ("Not comparable", result["not_comparable"]),
                         ("Missing rows", result["missing"])):
        lines.append(f"**{title}:** " + ("none" if not items else ""))
        lines += [f"- {item}" for item in items]
        lines.append("")
    lines += ["| Row | Metric | Baseline (B) | Candidate (B) | Δ (B) | Δ% | Band (±B) | Verdict |",
              "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |"]
    for row in result["rows"]:
        for m in row["metrics"]:
            if m["baseline"] is None and m["candidate"] is None:
                continue
            pct = f"{m['delta_pct']:+.2f}%" if m["delta_pct"] is not None else "—"
            delta = f"{m['delta']:+,}" if m["delta"] is not None else "—"
            lines.append(f"| {row['key']} | {m['metric']} | {_n(m['baseline'])} | {_n(m['candidate'])} | "
                         f"{delta} | {pct} | {m['band']:,} | {m['verdict']} |")
    walls = []
    for backend in BACKENDS:
        a = (baseline.get("wall_ineligible") or {}).get(backend, {}).get("matrix_wall_s")
        b = (candidate.get("wall_ineligible") or {}).get(backend, {}).get("matrix_wall_s")
        if a or b:
            walls.append(f"{backend} {a} s → {b} s")
    if walls:
        lines += ["", "Matrix wall (INELIGIBLE diagnostic, not a speed claim): " + "; ".join(walls) + "."]
    return "\n".join(lines) + "\n"
