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
            (r.get("workload", {}) for r in selected if r.get("workload")), {}
        )
        lines += [
            f"## {cell}",
            "",
            safe(
                workload.get(
                    "description",
                    workload.get(
                        "name",
                        "Exact frozen workload in suite src/cases.py; upstream identity below.",
                    ),
                )
            ),
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
            lines += [
                "",
                "Tool results (upstream units; intrinsic checks only):",
                "",
                "| Machine / database | Metrics |",
                "| --- | --- |",
            ]
            for machine in DISPLAY:
                for row in metrics:
                    if row["machine"] == machine:
                        lines.append(
                            f"| {row['machine']} / {row['backend']} | {safe(json.dumps(row['tool_metrics'], sort_keys=True, separators=(',', ':')))} |"
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
        lines += ["Tool identity: " + safe(json.dumps(pins, sort_keys=True)) + ".", ""]
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
