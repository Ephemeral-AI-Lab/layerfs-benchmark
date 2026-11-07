#!/usr/bin/env python3
"""Publish one report: the frozen script's scenario times on eight LayerFS rows."""

import argparse
import json
from collections import Counter
from pathlib import Path

import cases
import host

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


def host_ns(host_baseline):
    """The one host sample's scenario times, or {} when it is unavailable."""
    if not host_baseline or not host_baseline.get("available"):
        return {}
    return dict(host_baseline.get("scenarios") or {})


def attributable(native, plain):
    """native − host: what LayerFS adds on top of plain APFS, both sampled."""
    if isinstance(native, int) and isinstance(plain, int):
        return native - plain
    return None


def scenario_ns(row):
    metrics = row.get("tool_metrics") if row.get("execution") == "PASS" else None
    if not metrics:
        return {}
    times = {item["scenario"]: item["ns"] for item in metrics["scenarios"]}
    times[None] = metrics["sum_ns"]
    return times


def render(state, cleanup, config, host_baseline=None):
    host_baseline = host_baseline or {"available": False, "reason": "no --host-baseline given"}
    host_times = host_ns(host_baseline)
    host_cell = "UNAVAILABLE" if not host_times else None
    missing = {"execution": "NOT_RUN", "cleanup": "NOT_RUN", "reason": "not attempted"}
    rows = {
        (machine, backend): state.get("rows", {}).get(f"B01/{machine}/{backend}", missing)
        for machine in DISPLAY
        for backend in BACKENDS
    }
    counts = Counter(row.get("execution", "NOT_RUN") for row in rows.values())
    passed = counts.get("PASS", 0)
    # Only claim a shared Linux bundle and image when a Linux row actually ran.
    linux_rows = any(
        rows[(machine, backend)].get("execution") == "PASS"
        for machine in DISPLAY
        if machine != "native"
        for backend in BACKENDS
    )
    shared_identity = "All campaigns use the same CLI and daemon" + (
        ", Linux bundle and image" if linux_rows else ""
    )
    cleanup_state = cleanup.get("cleanup", "NOT_RUN")
    lines = [
        "# fs-bench-cloudflare-computer — Cloudflare's fs-bench.sh on LayerFS",
        "",
        "> Status: Diagnostic observations; every timing and ratio is performance-ineligible.",
        "",
        f"**{passed} of 8 rows ran all twelve scenarios "
        f"({', '.join(f'{n} {k}' for k, n in sorted(counts.items()))}); "
        f"final cleanup {cleanup_state}.** One sample per row; every time and ratio is an "
        "INELIGIBLE diagnostic.",
        "",
        f"LayerFS `{state['source_sha']}` (remote `layerfs_v2_0_0`, resolved at campaign start). "
        + (
            "Campaigns: " + "; ".join(
                f"`{c['campaign_id']}` (harness `{c['harness_commit'][:10]}`): "
                + (", ".join(c["rows"]) or "no executed rows")
                for c in state["campaigns"]
            ) + f". {shared_identity}. "
            if state.get("campaigns")
            else f"Harness `{config.get('harness_commit', 'working tree')}`. "
        )
        + "Each row runs Cloudflare "
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
    native = config.get("native_tools")
    if native:
        lines += [
            f"Native macOS ships bash 3.2, which the script cannot run, so native rows put a pinned "
            f"GNU bash {native['bash']['version']} (source SHA-256 `{native['bash']['source_sha256'][:16]}…`, "
            f"binary `{native['bash']['binary_sha256'][:16]}…`) first on the Exec PATH, plus a small "
            "`sha256sum` wrapper that gives macOS's checker GNU's `-c --quiet` form. The workload "
            "command is byte-identical on every row. Native Workspaces are NFS mounts, and every "
            "`stat`, `mkdir` and `echo >` loop step launches a macOS process.",
            "",
        ]
    if host_times:
        tools = host_baseline.get("tool_environment") or {}
        lines += [
            f"Host baseline: one sample recorded by campaign `{host_baseline.get('campaign_id')}` at "
            f"{host_baseline.get('measured_at')} from "
            f"`{host_baseline.get('platform') or 'unrecorded platform'}`, on a directory the recorder "
            f"proved to be {host_baseline.get('filesystem') or 'apfs, not NFS'}, with the same frozen "
            "script body, the same pinned bash "
            f"(`{(tools.get('bash_sha256') or 'unrecorded')[:16]}…`) and PATH as the native "
            "rows, one sample per campaign. It is host cost, not a LayerFS row: it has no "
            "create/mount/Exec/Commit/unmount/close lifecycle and is never counted as a ninth row. "
            "`native − host` is the LayerFS-attributable time per scenario, and it is only "
            "attributable when the sample's platform is the machine the native rows ran on.",
            "",
        ]
    else:
        lines += [
            "Host baseline: UNAVAILABLE — "
            + safe(host_baseline.get("reason") or "no host sample")
            + ". The host columns below are UNAVAILABLE; nothing is inferred from the Docker or "
            "native columns in their place, so the native cost is not split into host and LayerFS "
            "in this report.",
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
                {"COMPLETE_AFTER_INSPECTION": "COMPLETE (after inspection)"}.get(
                    row.get("cleanup", "NOT_RUN"), row.get("cleanup", "NOT_RUN")
                ),
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
            reason = row["reason"]
            if reason == "not attempted":
                machine_reason = (
                    (config.get("machines") or {}).get(machine) or {}
                ).get("unavailable_reason")
                reason = machine_reason or reason
            if row.get("reason") == "exec: CLI/process exit -9":
                reason = (
                    "the Exec was stopped at the row's 25 s budget (CLI killed, exit -9), so the "
                    "script's reply and scenario times were lost"
                )
            if row.get("custody_resolution"):
                reason += (
                    "; afterwards inspection found no script process, an idle Workspace and an "
                    "empty root, and the row was released through the CLI"
                )
            reasons.setdefault(reason, []).append(f"{TITLES[machine]} {DATABASES[backend]}")
    for reason, names in reasons.items():
        lines.append(f"- {', '.join(names)}: {safe(reason)}")
    for (machine, backend), row in rows.items():
        if row.get("budget_exception"):
            exception = row["budget_exception"]
            lines.append(
                f"- {TITLES[machine]} {DATABASES[backend]} ran under a {exception['max_s']} s budget "
                f"({safe(exception['approved_by'])}: {safe(exception['reason'])}); other rows use 25 s. "
                f"This row took {ms(row.get('performance_invocation_elapsed_ns'))} ms end to end."
            )
    for old in state.get("superseded", []):
        machine, backend = old["id"].split("/")[1:]
        lines.append(
            f"- Superseded attempt: {TITLES[machine]} {DATABASES[backend]} in `{old.get('campaign_id')}` "
            f"was {old.get('execution')} (Exec {ms(old.get('timings_ns', {}).get('exec'))} ms, "
            f"budget {old.get('performance_budget_s', 25)} s); it is retained, not relabeled."
        )
    if reasons or state.get("superseded") or any(r.get("budget_exception") for r in rows.values()):
        lines.append("")
    for backend in BACKENDS:
        times = {machine: scenario_ns(rows[(machine, backend)]) for machine in DISPLAY}
        lines += [f"## Scenario times, {DATABASES[backend]}", ""]
        if not any(times.values()):
            lines += ["No row produced scenario times.", ""]
            continue
        others = [m for m in DISPLAY if m != "docker"]
        header = (
            ["Scenario", "Cache state", "host ms"]
            + [f"{TITLES[m]} ms" for m in DISPLAY]
            + ["host / Docker", "native − host ms"]
            + [f"{TITLES[m]} / Docker" for m in others]
        )
        lines += [
            "| " + " | ".join(header) + " |",
            "| --- | --- | " + " | ".join("---:" for _ in header[2:]) + " |",
        ]
        sum_ns = None
        for name in (*cases.SCENARIOS, None):
            label = name or "Sum of scenarios"
            cache = "—" if name is None else (
                "own-write warm" if name in cases.OWN_WRITE_WARM else "self-contained"
            )
            plain = host_baseline.get("sum_ns") if name is None and host_times else (
                host_times.get(name) if host_times else None
            )
            values = [times[m].get(name) for m in DISPLAY]
            add = attributable(times["native"].get(name), plain)
            lines.append(
                "| "
                + " | ".join(
                    [label, cache, host_cell or ms(plain)]
                    + [ms(v) for v in values]
                    + [host_cell or ratio(plain, times["docker"].get(name))]
                    + [host_cell or ms(add)]
                    + [ratio(times[m].get(name), times["docker"].get(name)) for m in others]
                )
                + " |"
            )
        lines.append("")
    passing = [
        (m, b, r) for (m, b), r in rows.items()
        if r.get("execution") == "PASS" and r.get("tool_metrics")
    ]
    if passing:
        sums = sorted((r["tool_metrics"]["sum_ns"], m, b) for m, b, r in passing)
        e2e = max(r.get("performance_invocation_elapsed_ns") or 0 for _, _, r in passing)
        kinds = Counter((r.get("commit") or {}).get("kind", "—") for _, _, r in passing)
        lines += [
            "## Main observations",
            "",
        ] + (
            [
                f"- The one complete row summed to {ms(sums[0][0])} ms "
                f"({TITLES[sums[0][1]]} {DATABASES[sums[0][2]]})."
            ]
            if len(sums) == 1
            else [
                f"- Sum of scenario times ranged from {ms(sums[0][0])} ms ({TITLES[sums[0][1]]} "
                f"{DATABASES[sums[0][2]]}) to {ms(sums[-1][0])} ms ({TITLES[sums[-1][1]]} "
                f"{DATABASES[sums[-1][2]]})."
            ]
        ) + [
            f"- Longest complete row: {ms(e2e)} ms.",
            "- LayerFS Commit results: "
            + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items()))
            + "; the script removes every directory it creates, so nothing new is committed.",
        ]
        native = [(b, r) for m, b, r in passing if m == "native"]
        docker = {b: r for m, b, r in passing if m == "docker"}
        if native and any(b in docker for b, _ in native):
            b, r = next((b, r) for b, r in native if b in docker)
            stat = scenario_ns(r).get("stat 1000 files")
            base = scenario_ns(docker[b]).get("stat 1000 files")
            lines.append(
                f"- Native macOS is the slowest machine: "
                f"`stat 1000 files` took {ms(stat)} ms against Docker's {ms(base)} ms on "
                f"{DATABASES[b]}. The 1,000-step loops launch one macOS process per file on an NFS "
                "mount; the 64 MiB rows are close to Docker."
            )
        if host_times:
            lines.append(
                "- The host baseline is the same frozen script on a plain APFS folder outside LayerFS, "
                "one sample per campaign and unrelated to the database, so both tables share it. It is "
                "host cost, not a LayerFS row; `native − host` is the LayerFS-attributable part and the "
                "`native / Docker` and `host / Docker` ratios stay the only cross-machine comparisons."
            )
        lines += [
            "- Single unrepeated samples under shared host load: differences of a few tens of "
            "percent between rows are within what one sample can show and are not a ranking.",
            "",
        ]
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


def merge(states, configs):
    """Rows from several campaigns at one product commit; an executed row wins over NOT_RUN."""
    if len({s["source_sha"] for s in states}) != 1:
        raise SystemExit("campaigns measured different product commits")
    merged = {"source_sha": states[0]["source_sha"], "rows": {}, "campaigns": [], "superseded": []}
    for state, config in zip(states, configs):
        executed = []
        for key, row in state.get("rows", {}).items():
            previous = merged["rows"].get(key)
            if previous and previous.get("execution") not in (None, "NOT_RUN") and row.get("execution") != "NOT_RUN":
                merged["superseded"].append({**previous, "id": key})
            if row.get("execution") != "NOT_RUN" or key not in merged["rows"]:
                merged["rows"][key] = {**row, "campaign_id": config["campaign_id"]}
            if row.get("execution") != "NOT_RUN":
                machine, backend = key.split("/")[1:]
                executed.append(f"{TITLES[machine]} {DATABASES[backend]}")
        merged["campaigns"].append({
            "campaign_id": config["campaign_id"],
            "harness_commit": config.get("harness_commit", "working tree"),
            "rows": executed,
        })
    config = dict(configs[0])
    for other in configs[1:]:
        config.setdefault("native_tools", other.get("native_tools"))
    return merged, config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, nargs="+", required=True, help="campaign caches")
    parser.add_argument("--cleanup", type=Path, required=True)
    parser.add_argument("--environment", type=Path, nargs="+", required=True, help="one per --input, same order")
    parser.add_argument(
        "--host-baseline", type=Path,
        help="host-baseline.json from src/host.py; its columns are UNAVAILABLE without it",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(args.input) != len(args.environment):
        parser.error("give one --environment per --input")
    if args.output.exists():
        parser.error("report already exists; do not overwrite released results")
    state, config = merge(
        [json.loads((path / "campaign.json").read_text()) for path in args.input],
        [json.loads(path.read_text()) for path in args.environment],
    )
    host_baseline = host.load(args.host_baseline, state["source_sha"]) if args.host_baseline else None
    text = render(state, json.loads(args.cleanup.read_text()), config, host_baseline)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
