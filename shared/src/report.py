#!/usr/bin/env python3
"""Publish one small Markdown report from a suite's retained campaign state."""

import argparse
from collections import Counter
import json
from pathlib import Path

DISPLAY = ("docker", "native", "lima", "apple-container")
DATABASES = ("sqlite", "postgresql")


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


def elapsed(row, phase):
    if phase == "end_to_end":
        return row.get("performance_invocation_elapsed_ns")
    return row.get("timings_ns", {}).get(phase)


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
            headers += ["Read / write / truncate counts"]
            values += [
                " / ".join(
                    str(metrics.get("operation_counts", {}).get(key, 0))
                    for key in ("READ", "WRITE", "TRUNCATE")
                )
            ]
        else:
            headers += ["Expected errno", "Unexpected errors"]
            values += [
                str(metrics.get("operations_expected_errors")),
                str(metrics.get("operations_unexpected_errors")),
            ]
        return headers, values
    if suite == "mdtest":
        return ["Entries", "Create ops/s", "Stat ops/s", "Remove ops/s"], [
            str(metrics.get("entries")),
            *[
                number(metrics.get("phase_rates", {}).get(phase, {}).get("mean"))
                for phase in ("create", "stat", "remove")
            ],
        ]
    if suite == "smallfile":
        return ["Files", "Files/s", "Worker 00 records", "Worker 01 records"], [
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
    keys = (
        "workload_version",
        "profile",
        "entry_kind",
        "ranks",
        "entries",
        "iterations",
        "operation",
        "workers",
        "files_per_worker",
        "bytes_per_file",
        "script",
        "assertion_count",
        "selection",
        "bounds",
        "operation_weights",
    )
    fields = {key: workload[key] for key in keys if key in workload}
    return (
        "; ".join(
            f"{key}: {json.dumps(value) if isinstance(value, dict) else value}"
            for key, value in fields.items()
        )
        or "Frozen workload and prerequisite in the linked suite definition."
    )


def render(suite, state, cleanup, config):
    expected = state["matrix"]
    rows = {
        item["id"]: {**item, **state.get("rows", {}).get(item["id"], {})}
        for item in expected
    }
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
        f"**Diagnostic terminal: {terminal}.** {len(expected)} registered rows; execution {dict(counts)}. "
        f"Final infrastructure cleanup: **{cleanup.get('cleanup', 'NOT_RUN')}**.",
        "",
        f"LayerFS `{state['source_sha']}` (remote `layerfs_v2_0_0`, resolved at campaign start). "
        f"Harness: {config.get('harness_commit', 'working source hashes retained locally')}. "
        "Matched release CLI/daemon/Linux bundle reused after hash checks; no product changes.",
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
        "Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates "
        "cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.",
        "",
        "Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. "
        "Cleanup includes Sandbox close and Store remove/disconnect; End-to-end also includes mount/unmount "
        "and intervening harness work, excludes preparation, Python startup and optional proof. "
        "Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, "
        "below 1 means less elapsed time. One sample per row, no median or repeatability claim.",
        "",
        f"Environment: {config.get('environment_description', 'native macOS; Docker; Lima; Apple Container; dedicated PostgreSQL17 server')}. "
        "Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage "
        "are UNAVAILABLE; no storage-efficiency claim.",
        "",
    ]
    for cell in dict.fromkeys(item["cell"] for item in expected):
        selected = [r for r in rows.values() if r["cell"] == cell]
        workload = next(
            (r.get("workload", {}) for r in selected if r.get("workload")),
            config.get("tool_identity", {}).get("workload_profiles", {}).get(cell, {}),
        )
        lines += [
            f"## {cell}",
            "",
            safe(workload_summary(workload)),
            "",
            "| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for machine in DISPLAY:
            for backend in DATABASES:
                row = rows[f"{cell}/{machine}/{backend}"]
                base = rows[f"{cell}/docker/{backend}"]
                values = [
                    machine,
                    backend,
                    row.get("execution", "NOT_RUN"),
                    row.get("cleanup", "NOT_RUN"),
                    ms(elapsed(row, "sandbox_create")),
                    ms(elapsed(row, "exec")),
                    ms(elapsed(row, "commit")),
                    ms(row.get("cleanup_elapsed_ns")),
                    ms(elapsed(row, "end_to_end")),
                    ratio(row, base, "exec"),
                    ratio(row, base, "commit"),
                    ratio(row, base, "end_to_end"),
                ]
                lines.append("| " + " | ".join(values) + " |")
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
            lines += ["", *[f"- {name}: {safe(reason)}" for name, reason in reasons]]
        lines.append("")
    setup_ns = sum(r.get("prepare_elapsed_ns", 0) for r in rows.values())
    lines += [
        "## Preparation, limits and cleanup",
        "",
        f"Row preparation total: {setup_ns / 1e9:.3f} s (separate from timings). "
        f"Final shared infrastructure teardown: {str(round(cleanup['elapsed_ns'] / 1e9, 3)) + ' s' if isinstance(cleanup.get('elapsed_ns'), int) else 'UNAVAILABLE'}. "
        "Tools and image prepared once; one owned PostgreSQL server and three ready guest machines reused across suites. "
        "Each row has independent Store/history and is consumed once. PostgreSQL databases are released with the owned server data volume.",
        "",
        safe(cleanup.get("summary", "Final disposition recorded by campaign owner.")),
        "",
        "Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. "
        "All failed and unsupported rows remain visible. Measured rows ran serially; implementation/tool builds completed before measurement.",
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
    args = parser.parse_args()
    state = json.loads((args.input / "campaign.json").read_text())
    text = render(
        args.suite,
        state,
        json.loads(args.cleanup.read_text()),
        json.loads(args.environment.read_text()),
    )
    if args.output.exists():
        parser.error(
            "report already exists; select a new report rather than overwriting released results"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
