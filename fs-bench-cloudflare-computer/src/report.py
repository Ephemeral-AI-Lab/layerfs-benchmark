#!/usr/bin/env python3
"""Publish one report: the frozen script's scenario times on eight LayerFS rows."""

import argparse
import json
from collections import Counter
from pathlib import Path

import cases

DISPLAY = ("docker", "native", "lima", "apple-container")
TITLES = {"docker": "Docker", "native": "native", "lima": "Lima", "apple-container": "Apple Container"}
BACKENDS = ("sqlite", "postgresql")
DATABASES = {"sqlite": "SQLite", "postgresql": "PostgreSQL"}


def ms(value):
    return f"{value / 1_000_000:,.1f}" if isinstance(value, (int, float)) else "—"


def safe(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def ratio(a, b):
    return f"{a / b:.2f}" if isinstance(a, int) and isinstance(b, int) and b > 0 else "—"


def scenario_ns(row):
    metrics = row.get("tool_metrics") if row.get("execution") == "PASS" else None
    if not metrics:
        return {}
    times = {item["scenario"]: item["ns"] for item in metrics["scenarios"]}
    times[None] = metrics["sum_ns"]
    return times


def render(state, cleanup, config):
    missing = {"execution": "NOT_RUN", "cleanup": "NOT_RUN", "reason": "not attempted"}
    rows = {
        (machine, backend): state.get("rows", {}).get(f"B01/{machine}/{backend}", missing)
        for machine in DISPLAY
        for backend in BACKENDS
    }
    counts = Counter(row.get("execution", "NOT_RUN") for row in rows.values())
    passed = counts.get("PASS", 0)
    cleanup_state = cleanup.get("cleanup", "NOT_RUN")
    lines = [
        "# fs-bench-cloudflare-computer — Cloudflare's fs-bench.sh on LayerFS",
        "",
        "> Status: Diagnostic observations; every timing and ratio is performance-ineligible.",
        "",
        f"**{passed} of 8 rows ran all twelve scenarios (execution {dict(counts)}); "
        f"final cleanup {cleanup_state}.** One sample per row; every time and ratio is an "
        "INELIGIBLE diagnostic.",
        "",
        f"LayerFS `{state['source_sha']}` (remote `layerfs_v2_0_0`, resolved at campaign start). "
        f"Harness `{config.get('harness_commit', 'working tree')}`. Each row runs Cloudflare "
        f"Computer's byte-identical `script/fs-bench.sh` (Computer `{cases.SOURCE_COMMIT}`, "
        f"SHA-256 `{cases.SCRIPT_SHA256}`) once, with REPS=1, WARMUP=0, RANDOMIZE_TARGETS=0, no "
        "BASE, and the twelve offline scenarios. The script times each scenario itself with "
        "`date +%s%N`, inside the Workspace, in a fresh directory it removes afterwards. Computer "
        "itself is not measured.",
        "",
        "All LayerFS work uses the public CLI: Sandbox create, Workspace mount, one Exec running "
        "the script on the Workspace root, LayerFS Commit, unmount, Sandbox close and Store "
        "remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one "
        "construction worker; kernel writeback off.",
        "",
        "Ratios divide a machine's time by Docker's time for the same scenario and database; "
        "Docker = 1.00, below 1 means less time. `pure read`, `pure copy` and `overwrite` read "
        "or rewrite a file the script wrote just before its clock started, so they are own-write "
        "warm. The 64 MiB rows write zeros. The sum is a convenience total, not an agent turn.",
        "",
        f"Environment: {config.get('environment_description', 'UNAVAILABLE')}",
        "",
    ]
    artifacts = config.get("artifacts", {})
    if artifacts:
        lines += ["| Build input | Identity |", "| --- | --- |"]
        for label, key in (
            ("CLI (macOS, release, PostgreSQL)", "cli_sha256"),
            ("Native daemon", "daemon_sha256"),
            ("Linux bundle seal", "linux_bundle_sha256"),
            ("Sandbox tool image", "sandbox_image"),
            ("Namespace archive config", "sandbox_archive_config"),
        ):
            lines.append(f"| {label} | `{artifacts.get(key, 'UNAVAILABLE')}` |")
        lines.append("")
    lines += [
        "## Rows",
        "",
        "CLI call times in milliseconds, including launch and routing. Create is Sandbox "
        "creation; Exec is the whole script run; Commit is the LayerFS Commit; Cleanup is Sandbox "
        "close and Store remove/disconnect; End-to-end also includes mount and unmount and "
        "excludes preparation.",
        "",
        "| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Commit result |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for machine in DISPLAY:
        for backend in BACKENDS:
            row = rows[(machine, backend)]
            timings = row.get("timings_ns", {})
            values = [
                TITLES[machine],
                DATABASES[backend],
                row.get("execution", "NOT_RUN"),
                row.get("cleanup", "NOT_RUN"),
                ms(timings.get("sandbox_create")),
                ms(timings.get("exec")),
                ms(timings.get("commit")),
                ms(row.get("cleanup_elapsed_ns")),
                ms(row.get("performance_invocation_elapsed_ns")),
                safe((row.get("commit") or {}).get("kind", "—")),
            ]
            lines.append("| " + " | ".join(values) + " |")
    lines.append("")
    reasons = {}
    for (machine, backend), row in rows.items():
        if row.get("execution") != "PASS" and row.get("reason"):
            reasons.setdefault(row["reason"], []).append(f"{TITLES[machine]} {DATABASES[backend]}")
    for reason, names in reasons.items():
        lines.append(f"- {', '.join(names)}: {safe(reason)}")
    if reasons:
        lines.append("")
    for backend in BACKENDS:
        times = {machine: scenario_ns(rows[(machine, backend)]) for machine in DISPLAY}
        lines += [f"## Scenario times, {DATABASES[backend]}", ""]
        if not any(times.values()):
            lines += ["No row produced scenario times.", ""]
            continue
        others = [m for m in DISPLAY if m != "docker"]
        lines += [
            "| Scenario | Cache state | "
            + " | ".join(f"{TITLES[m]} ms" for m in DISPLAY)
            + " | "
            + " | ".join(f"{TITLES[m]} / Docker" for m in others)
            + " |",
            "| --- | --- | " + " | ".join("---:" for _ in DISPLAY + tuple(others)) + " |",
        ]
        for name in (*cases.SCENARIOS, None):
            label = name or "Sum of scenarios"
            cache = "—" if name is None else (
                "own-write warm" if name in cases.OWN_WRITE_WARM else "self-contained"
            )
            values = [times[m].get(name) for m in DISPLAY]
            ratios = [ratio(times[m].get(name), times["docker"].get(name)) for m in others]
            lines.append(
                "| " + " | ".join([label, cache, *(ms(v) for v in values), *ratios]) + " |"
            )
        lines.append("")
    lines += [
        "## Limits and cleanup",
        "",
        "Each row is one unrepeated sample on a shared macOS host. Other owners' containers and "
        "VMs ran during the campaign and were left alone. No cache was cleared or proven cold. "
        "Execution PASS means the CLI lifecycle succeeded and the script reported one sample "
        "for each of the twelve scenarios; it is not independent content verification (every "
        "scenario deletes its own directory).",
        "",
        f"Final cleanup: **{cleanup_state}**. {safe(cleanup.get('summary', ''))}",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="the campaign cache")
    parser.add_argument("--cleanup", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("report already exists; do not overwrite released results")
    text = render(
        json.loads((args.input / "campaign.json").read_text()),
        json.loads(args.cleanup.read_text()),
        json.loads(args.environment.read_text()),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
