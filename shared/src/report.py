#!/usr/bin/env python3
"""Publish one small Markdown report from a suite's retained campaign state."""

import argparse
import json
from collections import Counter
from pathlib import Path

DISPLAY = ("docker", "native", "lima", "apple-container")
DATABASES = ("sqlite", "postgresql", "pg-colocated")
PHASE_KEYS = {"create": "sandbox_create", "mount": "measured_mount", "close": "sandbox_close"}
# Server-side observation phases, in lifecycle order, with report labels.
OBSERVED = (
    ("sandbox_create", "Create"),
    ("measured_mount", "Mount"),
    ("exec", "Exec"),
    ("commit", "Commit"),
    ("followup_exec", "Exec 2"),
    ("commit_2", "Commit 2"),
    ("unmount", "Unmount"),
    ("cleanup", "Cleanup"),
)
DELTA_PHASES = ("create", "mount", "exec", "commit", "unmount", "close", "release", "end_to_end")


def ms(value):
    return f"{value / 1_000_000:.2f}" if isinstance(value, (int, float)) else "—"


def safe(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def ratio(row, baseline, phase):
    if row.get("execution") != "PASS" or baseline.get("execution") != "PASS":
        return "—"
    a, b = elapsed(row, phase), elapsed(baseline, phase)
    return (
        f"{a / b:.2f}" if isinstance(a, int) and isinstance(b, int) and b > 0 else "—"
    )


MEASURED_CALLS = (
    "sandbox_create",
    "measured_mount",
    "exec",
    "commit",
    "followup_exec",
    "commit_2",
    "unmount",
    "sandbox_close",
    "store_remove",
    "store_disconnect",
)


def phase_sum(row):
    """Sum of the measured lifecycle CLI calls of a passing row (no harness gaps)."""
    timings = row.get("timings_ns", {})
    if row.get("execution") != "PASS" or "sandbox_create" not in timings:
        return None
    return sum(timings[key] for key in MEASURED_CALLS if isinstance(timings.get(key), int))


def elapsed(row, phase):
    """Phase wall ns; End-to-end excludes declared observer control overhead."""
    if phase == "end_to_end":
        if "end_to_end_ns" in row:
            return row["end_to_end_ns"]
        total = row.get("performance_invocation_elapsed_ns")
        if isinstance(total, int):
            return total - row.get("control_overhead_ns", 0)
        return total
    timings = row.get("timings_ns", {})
    if phase == "release":
        return timings.get("store_remove", timings.get("store_disconnect"))
    return timings.get(PHASE_KEYS.get(phase, phase))


def median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    return (
        ordered[middle]
        if len(ordered) % 2
        else (ordered[middle - 1] + ordered[middle]) / 2
    )


def backend_deltas(rows):
    """Median PostgreSQL arm minus SQLite per machine/phase over PASS cell pairs."""
    lines = []
    for machine in DISPLAY:
        for arm in DATABASES[1:]:
            values, cells = {}, set()
            for row in rows.values():
                if row["machine"] != machine or row["backend"] != arm:
                    continue
                base = rows.get(f"{row['cell']}/{machine}/sqlite", {})
                if row.get("execution") != "PASS" or base.get("execution") != "PASS":
                    continue
                cells.add(row["cell"])
                for phase in DELTA_PHASES:
                    a, b = elapsed(row, phase), elapsed(base, phase)
                    if isinstance(a, int) and isinstance(b, int):
                        values.setdefault(phase, []).append(a - b)
            if cells:
                lines.append(
                    f"| {machine} | {arm} | {len(cells)} | "
                    + " | ".join(
                        f"{median(values[p]) / 1e6:+.1f}" if values.get(p) else "—"
                        for p in DELTA_PHASES
                    )
                    + " |"
                )
    if not lines:
        return []
    return [
        "## PostgreSQL minus SQLite",
        "",
        "Median over cells of (PostgreSQL arm − SQLite) per machine, milliseconds, using only cells where both rows passed. "
        "Close is Sandbox close; Store release is `store disconnect` (PostgreSQL) versus `store remove` (SQLite), which the product does not unify.",
        "",
        "| Machine | Arm | Cells | Create | Mount | Exec | Commit | Unmount | Close | Store release | End-to-end |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *lines,
        "",
    ]


def observed_counts(selected):
    """Per-phase pg_stat_statements calls and logged connections for one cell."""
    observed = [r for r in selected if r.get("pg_phases")]
    if not observed:
        return []
    phases = [
        (key, label)
        for key, label in OBSERVED
        if any(key in r["pg_phases"] for r in observed)
    ]
    lines = [
        "",
        "Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database "
        "(reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).",
        "",
        "| Machine | Database | " + " | ".join(label for _, label in phases) + " | Statements | Connections | Statement exec ms |",
        "| --- | --- | " + " | ".join("---:" for _ in phases) + " | ---: | ---: | ---: |",
    ]
    for machine in DISPLAY:
        for backend in DATABASES:
            for row in observed:
                if row["machine"] != machine or row["backend"] != backend:
                    continue
                cells, statements, connections, exec_ms = [], 0, 0, 0.0
                for key, _ in phases:
                    value = row["pg_phases"].get(key, {})
                    count = value.get("statements")
                    opened = value.get("connections")
                    statements += count or 0
                    connections += opened or 0
                    exec_ms += value.get("statement_exec_ms") or 0.0
                    cells.append(
                        f"{'—' if count is None else count} / {'—' if opened is None else opened}"
                    )
                lines.append(
                    f"| {machine} | {backend} | "
                    + " | ".join(cells)
                    + f" | {statements} | {connections} | {exec_ms:.1f} |"
                )
    return lines


def calibration_lines(calibration):
    if not calibration:
        return []
    lines = [
        "## Round-trip calibration",
        "",
        "`pgrtt.py` from each client location: address resolution, then 20 fresh connections (TCP connect; one SSLRequest "
        "probe, which a plaintext server answers `N` and which an unset `sslmode` (`prefer`) adds to every connection; as the first "
        "server reply it also includes the server starting a backend; startup to ReadyForQuery), then 200 simple-protocol "
        "`SELECT 1` on one connection. Milliseconds, medians unless marked p90. Resolve is one `getaddrinfo` call and "
        "includes the client's first-call library loading. "
        "Guests and the trust rows use a trust-authenticated calibration role; the SCRAM rows add the Store user's SCRAM-SHA-256 exchange.",
        "",
        "| Client | Route | Target | Peer | Auth | Resolve | TCP connect | SSL probe | Startup | SELECT 1 | SELECT 1 p90 |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    def cell(value, key="median_ns"):
        return f"{value[key] / 1e6:.3f}" if isinstance(value, dict) else "—"

    for item in calibration:
        if item.get("location") == "host":
            entries = [(f"host ({item['route']})", item["route"], item["target"], label, result)
                       for label, result in item.get("results", {}).items()]
        else:
            entries = [(item["machine"], arm, value["target"], "trust", value["measurement"])
                       for arm, value in item.get("results", {}).items()]
            if item.get("execution") != "PASS":
                lines.append(f"| {item.get('machine')} | — | — | — | — | {safe(item.get('reason'))} | | | | | |")
        for client, route, target, auth, result in entries:
            if "error" in result:
                lines.append(f"| {client} | {route} | {target['host']}:{target['port']} | — | {auth} | {safe(result['error'][-200:])} | | | | | |")
                continue
            lines.append(
                f"| {client} | {route} | {target['host']}:{target['port']} | {result.get('peer')} | {auth} | "
                f"{result['resolve_ns'] / 1e6:.3f} | {cell(result.get('tcp_connect'))} | {cell(result.get('ssl_probe'))} | "
                f"{cell(result.get('startup_to_ready'))} | {cell(result.get('select1'))} | {cell(result.get('select1'), 'p90_ns')} |"
            )
    return lines + [""]


def number(value, scale=1):
    return f"{value / scale:.2f}" if isinstance(value, (int, float)) else "UNAVAILABLE"


def metric_cells(suite, metrics):
    if suite == "fio":
        return ["I/O MiB", "I/O count", "MiB/s", "IOPS", "Mean completion μs"], [
            number(metrics.get("io_bytes"), 1048576),
            str(metrics.get("total_ios")),
            number(metrics.get("bandwidth_bytes_per_second"), 1048576),
            number(metrics.get("iops")),
            number(metrics.get("completion_latency_ns", {}).get("mean"), 1000),
        ]
    if suite in ("fsx", "fsstress"):
        headers = [
            "Requested slots",
            "Completed slots",
            "Effective operations",
            "Skipped slots",
        ]
        values = [
            str(metrics.get(key))
            for key in (
                "operations_requested",
                "operations_completed",
                "operations_effective",
                "operations_skipped",
            )
        ]
        if suite == "fsx":
            headers += ["Reads", "Writes", "Truncates"]
            values += [
                str(metrics.get("operation_counts", {}).get(key, 0))
                for key in ("READ", "WRITE", "TRUNCATE")
            ]
        else:
            headers += [
                "Expected errno",
                "Unexpected errors",
                "Page bytes",
                "Requested write bytes",
            ]
            values += [
                str(metrics.get("operations_expected_errors")),
                str(metrics.get("operations_unexpected_errors")),
                str(metrics.get("page_size_bytes", "UNAVAILABLE")),
                str(
                    metrics.get("io_requests", {})
                    .get("write", {})
                    .get("requested_bytes", "UNAVAILABLE")
                ),
            ]
        return headers, values
    if suite == "pjdfstest":
        return ["Assertions", "Passed", "Failed", "Skipped", "TODO"], [
            str(metrics.get(key))
            for key in ("assertions", "pass", "fail", "skip", "todo")
        ]
    if suite == "mdtest":
        return ["Entries", "Create ops/s", "Stat ops/s", "Remove ops/s"], [
            str(metrics.get("entries")),
            *[
                number(metrics.get("phase_rates", {}).get(phase, {}).get("mean"))
                for phase in ("create", "stat", "remove")
            ],
        ]
    if suite == "smallfile":
        return [
            "Files",
            "Σ worker files/s",
            "Worker 00 records",
            "Worker 01 records",
        ], [
            str(metrics.get("files")),
            number(metrics.get("files_per_second")),
            *[
                str(worker.get("records"))
                for worker in sorted(
                    metrics.get("worker_results", []), key=lambda x: x["thread"]
                )
            ],
        ]
    return ["Metrics"], [safe(json.dumps(metrics, separators=(",", ":")))]


def workload_summary(workload):
    version = workload.get("workload_version", "frozen workload")
    profile = workload.get("profile")
    if profile:
        label = {
            "write": "Sequential write",
            "read": "Sequential read",
            "randwrite": "Random write",
            "randread": "Random read",
        }.get(profile.get("rw"), profile.get("rw"))
        return f"{label}: {profile['size_bytes'] / 1048576:g} MiB, {profile['block_bytes'] / 1024:g} KiB blocks; buffered synchronous engine, one job/depth 1, seed 1, nonzero 0x5a pattern. {version}."
    if workload.get("entry_kind"):
        noun = "empty files" if workload["entry_kind"] == "file" else "directories"
        return f"512 {noun}; one MPI rank; one create/stat/remove iteration. {version}."
    if workload.get("operation"):
        return f"{workload['operation'].capitalize()} 512 files: two workers × 256 files, 4 KiB/file, 64 files/directory. {version}."
    if workload.get("scripts"):
        privilege = (
            "selected scripts run unprivileged"
            if workload.get("privilege_profile")
            else "upstream root prerequisite"
        )
        return f"{', '.join(workload['scripts'])}: {workload.get('expected_assertions_darwin_linux')} planned TAP assertions; {privilege}. {version}."
    if workload.get("bounds"):
        return f"Two processes × 512 requested operation slots, seed 1; frozen operation weights and per-operation allocation bounds. Effective work, skipped slots and expected errno are separate below. {version}."
    if workload.get("selection"):
        return f"1,000 operation slots, seed 1, file ≤8 MiB, operation ≤64 KiB; read/write/truncate and upstream consistency checks. Skipped slots remain explicit. {version}."
    return version


def render(suite, state, cleanup, config):
    expected = state["matrix"]
    rows = {
        item["id"]: {**item, **state.get("rows", {}).get(item["id"], {})}
        for item in expected
    }
    if config.get("end_to_end") == "phase_sum":
        for row in rows.values():
            row["end_to_end_ns"] = phase_sum(row)
    counts = Counter(row.get("execution", "NOT_RUN") for row in rows.values())
    complete = all(
        row.get("execution") == "PASS"
        and row.get("cleanup") == "COMPLETE"
        and row.get("verification", "SKIPPED") in ("PASS", "SKIPPED")
        for row in rows.values()
    )
    terminal = (
        "PASS" if complete and cleanup.get("cleanup") == "COMPLETE" else "INCOMPLETE"
    )
    lines = [
        f"# {suite} — CLI execution and cleanup",
        "",
        "> Status: Diagnostic observations; timings are performance-ineligible.",
        "",
        (
            f"**Diagnostic terminal: {terminal}.** {len(expected)} registered rows; execution {dict(counts)}. "
            f"Final infrastructure cleanup: **{cleanup.get('cleanup', 'NOT_RUN')}**."
        ),
        "",
        (
            f"LayerFS `{state['source_sha']}` ({config.get('source_reference', 'remote `layerfs_v2_0_0`, resolved at campaign start')}). "
            f"Harness: {config.get('harness_commit', 'working source hashes retained locally')}. "
            + config.get(
                "artifact_preparation",
                "Matched release CLI/daemon/Linux bundle reused after hash checks; no product changes.",
            )
        ),
        "",
        "All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, "
        "unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; "
        "PostgreSQL synchronous commit off; one construction worker. Independent committed-result "
        "verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: "
        + str(
            dict(Counter(row.get("verification", "SKIPPED") for row in rows.values()))
        )
        + ".",
        "",
        (
            "Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates "
            "cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**."
        ),
        "",
        (
            "Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. "
            "Close is Sandbox close; Store release is Store remove (SQLite) or disconnect (PostgreSQL). "
            + (
                "End-to-end is the sum of the measured calls from create through Store release, without harness gaps; it "
                if config.get("end_to_end") == "phase_sum"
                else "End-to-end covers create through Store release and intervening harness work, minus any declared "
                "observer control calls; it "
            )
            + "excludes preparation, Python startup and optional proof. "
            "Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, "
            "below 1 means less elapsed time. One sample per row, no median or repeatability claim."
        ),
        "",
        (
            f"Environment: {config.get('environment_description', 'native macOS; Docker; Lima; Apple Container; dedicated PostgreSQL17 server')}. "
            "Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage "
            "are UNAVAILABLE; no storage-efficiency claim."
        ),
        "",
    ]
    for section in config.get("report_sections", []):
        lines += [f"## {section['title']}", "", *section["lines"], ""]
    lines += backend_deltas(rows)
    lines += calibration_lines(config.get("calibration_results", []))
    artifacts = config.get("artifacts", {})
    if artifacts:
        lines += ["| Build input | SHA-256 / identity |", "| --- | --- |"]
        for label, key in (
            ("CLI", "cli_sha256"),
            ("Native daemon", "daemon_sha256"),
            ("Linux bundle seal", "linux_bundle_sha256"),
            ("Docker tool image", "sandbox_image"),
            ("Namespace archive config", "sandbox_archive_config"),
        ):
            lines.append(f"| {label} | `{artifacts.get(key, 'UNAVAILABLE')}` |")
        lines.append("")
    for cell in dict.fromkeys(item["cell"] for item in expected):
        selected = [r for r in rows.values() if r["cell"] == cell]
        workload = next(
            (r.get("workload", {}) for r in selected if r.get("workload")),
            config.get("tool_identity", {}).get("workload_profiles", {}).get(cell, {}),
        )
        second = any(elapsed(r, "commit_2") is not None for r in selected)
        load = any("load_1m" in r for r in selected)
        headers = ["Create ms", "Mount ms", "Exec ms", "Commit ms"]
        headers += ["Commit 2 ms"] if second else []
        headers += ["Unmount ms", "Close ms", "Store release ms", "End-to-end ms"]
        lines += [
            f"## {cell}",
            "",
            safe(config.get("case_summaries", {}).get(cell) or workload_summary(workload)),
            "",
            "| Machine | Database | Execution | Cleanup | "
            + ("Load 1m | " if load else "")
            + " | ".join(headers)
            + " | Exec / Docker | Commit / Docker | End-to-end / Docker |",
            "| --- | --- | --- | --- | "
            + ("---: | " if load else "")
            + " | ".join("---:" for _ in headers)
            + " | ---: | ---: | ---: |",
        ]
        for machine in DISPLAY:
            for backend in DATABASES:
                row = rows.get(f"{cell}/{machine}/{backend}")
                if row is None:
                    continue
                base = rows.get(f"{cell}/docker/{backend}", {})
                phases = ["create", "mount", "exec", "commit"]
                phases += ["commit_2"] if second else []
                phases += ["unmount", "close", "release", "end_to_end"]
                values = [
                    machine,
                    backend,
                    row.get("execution", "NOT_RUN"),
                    row.get("cleanup", "NOT_RUN"),
                    *([number(row.get("load_1m"))] if load else []),
                    *[ms(elapsed(row, phase)) for phase in phases],
                    ratio(row, base, "exec"),
                    ratio(row, base, "commit"),
                    ratio(row, base, "end_to_end"),
                ]
                lines.append("| " + " | ".join(values) + " |")
        lines += observed_counts(selected)
        metrics = [r for r in selected if r.get("tool_metrics")]
        if metrics:
            headers, _ = metric_cells(suite, metrics[0]["tool_metrics"])
            lines += [
                "",
                "Tool observations (intrinsic checks only; rates retain their upstream denominator):",
                "",
                "| Machine / database | " + " | ".join(headers) + " |",
                "| --- | " + " | ".join("---:" for _ in headers) + " |",
            ]
            for machine in DISPLAY:
                for row in metrics:
                    if row["machine"] == machine:
                        _, values = metric_cells(suite, row["tool_metrics"])
                        lines.append(
                            f"| {row['machine']} / {row['backend']} | "
                            + " | ".join(values)
                            + " |"
                        )
        reasons = [
            (r["machine"] + "/" + r["backend"], r.get("reason"))
            for r in selected
            if r.get("reason")
        ]
        if reasons:
            grouped = {}
            for name, reason in reasons:
                grouped.setdefault(reason, []).append(name)
            lines += [""]
            for reason, names in grouped.items():
                scope = (
                    "All eight configurations" if len(names) == 8 else ", ".join(names)
                )
                lines.append(f"- {scope}: {safe(reason)}")
        lines.append("")
    preparations = [
        r["prepare_elapsed_ns"]
        for r in rows.values()
        if isinstance(r.get("prepare_elapsed_ns"), int)
    ]
    setup = (
        f"Attempted row preparation: {sum(preparations) / 1e9:.3f} s total; maximum {max(preparations) / 1e9:.3f} s (25 s bound)."
        if preparations
        else (
            "No case inputs were allocated: prerequisites failed before preparation."
            if all(
                r.get("preparation") == "NOT_RUN" and r.get("execution") == "NOT_RUN"
                for r in rows.values()
            )
            else "Row preparation wall: UNAVAILABLE."
        )
    )
    lines += [
        "## Preparation, limits and cleanup",
        "",
        setup
        + " Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.",
        "",
        f"Final infrastructure cleanup: **{cleanup.get('cleanup', 'NOT_RUN')}**. Overall uninterrupted teardown wall: {str(round(cleanup['elapsed_ns'] / 1e9, 3)) + ' s' if isinstance(cleanup.get('elapsed_ns'), int) else 'UNAVAILABLE'}. "
        + (
            f"Serial resource-release commands total {cleanup['release_commands_ns'] / 1e9:.3f} s, local-file cleanup is excluded from that sum."
            if isinstance(cleanup.get("release_commands_ns"), int)
            else ""
        ),
        "",
        safe(cleanup.get("summary", "Final disposition recorded by campaign owner.")),
        "",
        safe(cleanup.get("cleanup_observation", "")),
        "",
        "Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.",
        "",
    ]
    if suite == "smallfile":
        lines += [
            "Smallfile upstream rate = 256/T00 + 256/T01 files/s. Each worker timer starts after directory, seed/buffer preparation and gate waiting; it uses upstream time.time(). It excludes launcher/startup work, so it is not 512 divided by CLI Exec time. Its control-file fsyncs are intrinsic upstream behavior; payload fsync is disabled. The declared 4KiB payload pattern is nonzero and compressible.",
            "",
        ]
    if suite == "fio":
        lines += [
            "fio writes the declared compressible nonzero 0x5a pattern. Bandwidth and completion latency come from fio's own single job interval; CLI Exec and End-to-end above include additional lifecycle/routing costs.",
            "",
        ]
    lines += [
        "External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.",
        "",
    ]
    pins = config.get("tool_identity")
    if pins:
        lines += [
            "Upstream source commit: `"
            + str(pins.get("source_commit"))
            + "`. Exact flags and setup: [frozen suite definition](https://github.com/Ephemeral-AI-Lab/layerfs-benchmark/blob/"
            + config.get("harness_commit", "main")
            + "/"
            + suite
            + "/src/cases.py).",
            "",
        ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--cleanup", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--calibration", type=Path, help="directory of calibration receipts"
    )
    args = parser.parse_args()
    state = json.loads((args.input / "campaign.json").read_text())
    config = json.loads(args.environment.read_text())
    if args.calibration:
        config["calibration_results"] = [
            json.loads(path.read_text())
            for path in sorted(args.calibration.glob("*.json"))
        ]
    text = render(args.suite, state, json.loads(args.cleanup.read_text()), config)
    if args.output.exists():
        parser.error(
            "report already exists; select a new report rather than overwriting released results"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
