#!/usr/bin/env python3
"""Publish one report from the shared runner's retained campaign receipts."""
import argparse
import json
from pathlib import Path
import cases


def ms(value):
    return "UNAVAILABLE" if value is None else f"{value / 1e6:,.3f}"


def render(state, config, cleanup, completion=None, previous=None, pg=None):
    rows = list(state["rows"].values())
    passed = sum(r.get("execution") == "PASS" for r in rows)
    status = cleanup.get("cleanup", "INCOMPLETE")
    budget = config.get("budget_exceptions", {}).get("docker", {}).get(
        "max_s", config.get("performance_budget_s", 25))
    if pg:
        if pg["tool_sha256"] != config["artifacts"]["juicefs_sha256"] or pg["client_image"] != config["artifacts"]["sandbox_image"]:
            raise ValueError("JuiceFS baseline uses different tool/image identities")
        if any(row.get("workload") != pg["workload"] for row in rows):
            raise ValueError("JuiceFS baseline workload differs")
        combined_cleanup = "COMPLETE" if status == pg.get("cleanup") == "COMPLETE" else "INCOMPLETE"
        outcome = (f"**LayerFS/SQLite execution {'PASS' if passed == len(rows) else 'FAIL'}; "
                   f"JuiceFS/PG16 execution {pg.get('execution', 'NOT_RUN')}; timings INELIGIBLE diagnostics; "
                   f"final cleanup {combined_cleanup}.**")
    else:
        outcome = f"**{passed}/{len(rows)} selected JuiceFS bench rows completed; timings INELIGIBLE diagnostics; final cleanup {status}.**"
    lines = [
        outcome,
        "", "# JuiceFS bench: LayerFS and JuiceFS/PG16" if pg else "# JuiceFS bench on LayerFS", "",
        f"LayerFS `layerfs_v2_0_0` at `{state['source_sha']}`. Campaign `{config['campaign_id']}`. "
        f"Harness base commit `{config.get('harness_commit', 'unrecorded')}` plus the suite source "
        "hashes retained with the receipts. This exploratory family has no committed product "
        "roadmap specification or tracking issue; admission_eligible=false.", "",
        "## Configuration", "",
        "One unrepeated Docker/SQLite sample on a shared macOS ARM64 host, Linux FUSE route. "
        "Four workers, each writing one 1 GiB file with 1 MiB blocks and 100 files of 128 KiB. "
        "Store profile: disposable. LAYERFS_CONSTRUCTION_WORKERS=1. "
        "SKIP_DROP_CACHES=true; no cache purge or pre-touch. Phase timers are upstream's "
        "Go monotonic elapsed wall times, converted by the tool to aggregate throughput. "
        "Launch, checksum validation and lifecycle control are outside these phase timers. "
        f"Complete measured lifecycle budget: {budget} s; preparation: "
        f"{config.get('prepare_budget_s', 25)} s; cleanup: "
        f"{config.get('cleanup_budget_s', 10)} s.", "",
        "| Artifact | Identity |", "| --- | --- |",
    ]
    for key, value in config.get("artifacts", {}).items():
        lines.append(f"| {key} | `{value}` |")
    if config.get("budget_exceptions"):
        exception = config["budget_exceptions"]["docker"]
        lines += ["", f"Budget authorization: {exception['approved_by']}. {exception['reason']}."]
    lines += ["", "Exact inner workload (the runner also checks the pinned tool binary hash):", "",
              "```bash", "SKIP_DROP_CACHES=true /usr/local/bin/juicefs bench . -p 4 "
              "--block-size 1 --big-file-size 1024 --small-file-size 128 --small-file-count 100", "```"]
    lines += ["", "## J01 results", "",
              "| Machine | Backend | Execution | Correctness | Performance | Cleanup |",
              "| --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(k, "UNAVAILABLE")) for k in
                     ("machine", "backend", "execution", "correctness", "performance", "cleanup")) + " |")
    lines += ["", "| Phase | Value | Unit | Reported cost | Cost unit |",
              "| --- | ---: | --- | ---: | --- |"]
    for row in rows:
        for metric in row.get("tool_metrics", {}).get("metrics", []):
            lines.append(f"| {metric['name']} | {metric['value']:,.2f} | {metric['unit']} | {metric['cost']:,.2f} | {metric['cost_unit']} |")
    if not any(r.get("tool_metrics") for r in rows):
        for name, unit, cost_unit in cases.METRICS:
            lines.append(f"| {name} | UNAVAILABLE | {unit} | UNAVAILABLE | {cost_unit} |")
    lines += ["", "CLI lifecycle times include process launch and routing, separately from tool phase throughput.", "",
              "| Machine | Backend | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Cleanup ms | End-to-end ms |",
              "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for row in rows:
        t = row.get("timings_ns", {})
        vals = [row["machine"], row["backend"], *[ms(t.get(k)) for k in
                ("sandbox_create", "measured_mount", "exec", "commit", "unmount")],
                ms(row.get("cleanup_elapsed_ns")), ms(row.get("performance_invocation_elapsed_ns"))]
        lines.append("| " + " | ".join(vals) + " |")
        if row.get("reason"):
            lines += ["", f"Disposition: {row['reason'].replace('|', '/')}"]
        if row.get("performance_budget_exceeded"):
            lines += ["", f"The {row.get('performance_budget_s', budget)} s complete lifecycle deadline expired during Exec. The CLI was "
                      "killed (process exit -9); no complete tool table was returned. This is a "
                      "budget failure with unavailable phase throughputs, not a filesystem "
                      "correctness verdict. The reported End-to-end value ends at that failed "
                      "attempt; subsequent custody inspection and recovery cleanup are separate."]
        if row.get("cleanup_after_inspection"):
            lines += ["", "Cleanup ms in this failed row records later recovery and is excluded "
                      "from the failed-attempt End-to-end value. Initial cleanup was INCOMPLETE "
                      "because the lost Exec reply left custody "
                      "uncertain. Public Workspace status then showed Idle, inspection of the "
                      "exact owned worker found no workload process, and a new read-only "
                      "inspection Exec confirmed an empty root. Public unmount with discard, "
                      "Sandbox close and Store remove succeeded; the exact worker and its data "
                      "volume were released. The original failed receipt and incomplete-cleanup "
                      "receipt remain preserved beside the append-only resolution record."]
    if pg:
        lf = {m["name"]: m for row in rows for m in row.get("tool_metrics", {}).get("metrics", [])}
        baseline = {m["name"]: m for m in pg.get("metrics", {}).get("metrics", [])}
        lines += ["", "## JuiceFS PostgreSQL 16 comparison", "",
            "This is an actual JuiceFS FUSE mount with PostgreSQL metadata, not a LayerFS PostgreSQL "
            "Store. It ran once later on the same shared Docker VM, using the identical JuiceFS "
            "binary, client image and inner workload. LayerFS was not rerun. The baseline uses "
            "a separate PG16 server over a private Docker bridge and local-file object storage "
            "on a dedicated Docker volume. No S3 server or network object store was used.", "",
            f"PostgreSQL image: `{pg['pg_image']}`. JuiceFS client image: `{pg['client_image']}`.", "",
            "Observed PostgreSQL version, fsync, synchronous_commit, full_page_writes and shared_buffers, in order:",
            "", "```text", pg.get("pg_settings", "UNAVAILABLE").strip(), "```", "",
            "JuiceFS: compression none; trash 0 days; writeback disabled; 300 MiB buffer; "
            "100 GiB disk cache limit with a fresh cache directory; all other mount settings "
            "at v1.4.2 defaults. LayerFS used its disposable SQLite profile. These durability "
            "and storage architectures differ; this is not a matched persistence comparison.", "",
            "Baseline first. Ratios are LayerFS throughput divided by JuiceFS throughput, "
            "provided only as INELIGIBLE diagnostic arithmetic; above 1 means higher observed throughput.", "",
            "| Phase | Unit | JuiceFS PG16 | LayerFS SQLite | LayerFS / JuiceFS |",
            "| --- | --- | ---: | ---: | ---: |"]
        for name, unit, _ in cases.METRICS:
            b, candidate = baseline.get(name, {}).get("value"), lf.get(name, {}).get("value")
            values = [f"{v:,.2f}" if v is not None else "UNAVAILABLE" for v in (b, candidate)]
            ratio = f"{candidate / b:.2f}×" if b and candidate else "UNAVAILABLE"
            lines.append(f"| {name} | {unit} | {values[0]} | {values[1]} | {ratio} |")
        lines += ["", f"JuiceFS execution: **{pg.get('execution')}**; content correctness: "
                  f"**UNVERIFIED**; cache eligibility: **INELIGIBLE**; cleanup: **{pg.get('cleanup')}**.", "",
                  f"JuiceFS benchmark Exec wall: {ms(pg.get('bench_elapsed_ns'))} ms, under a "
                  f"{pg['budget_s']} s limit. Format, mount and readiness were untimed setup. "
                  "This wall includes Docker Exec launch, checksum validation, bench and its "
                  "file deletion; it has a different boundary from LayerFS's full lifecycle "
                  "and must not be used for a lifecycle speedup ratio. The phase throughput "
                  "columns use the same upstream internal timers on both filesystems.", "",
                  "The baseline's two containers, PG data volume, object/cache volume and "
                  "private network are tracked by exact IDs and owner labels. Its receipts "
                  "and source snapshot remain local under `.cache/juicefs-pg16/`.", ""]
        if pg.get("reason") or pg.get("cleanup_reason"):
            lines += ["Baseline disposition: " + str(pg.get("reason") or pg.get("cleanup_reason")), ""]
    lines += ["", "## Observations and limits", "",
        "The tool reads and stats its own recent writes. Kernel pages, FUSE metadata, "
        "daemon/overlay SQLite caches, VM backing and Store caches are uncontrolled. "
        "Every metric remains INELIGIBLE; none establishes cold-storage throughput or "
        "a performance advantage over another filesystem. " +
        ("JuiceFS client, PostgreSQL and OS caches were also uncontrolled; settings and "
         "topology differ, and the samples were taken at different times on shared hardware."
         if pg else "No JuiceFS filesystem arm was run."), "",
        "The write loop reuses one random block per file and does not fsync. "
        "These are buffered filesystem API measurements, not durable writes or global-history "
        "publication. The tool removes its test directory before returning; a subsequent "
        "LayerFS Commit in a successful lifecycle would not save the measured dataset. "
        + ("This attempt never reached Commit. " if not any(r.get("commit") for r in rows) else
           "Observed Commit result: " + ", ".join(r["commit"]["kind"] for r in rows if r.get("commit")) + ". ")
        + "Independent content correctness "
        "is UNVERIFIED; successful reads only check that the requested byte counts were returned. "
        "Tool COST is upstream's wall-time-derived statistic, not independently observed "
        "per-operation latency. Phase-local CPU, memory, peak backing bytes and stored dataset "
        "bytes are UNAVAILABLE; the dataset is deleted before the Commit.", "",
        ("Setup reused the earlier sealed release artifacts and tool image, with fresh writable "
         "state for this separately authorized campaign. " if previous else
         "Warm setup reused installed toolchains/images and a closed dependency seed; release "
         "builds used new private targets. ")
        + "No setup input was pre-touched for measured reads. "
        "Concurrent shared-host activity was not interrupted. No automatic retry or uncertain-operation "
        "replay was performed.", "", "## Cleanup", "",
        f"Final runtime cleanup: **{status}**. Case cleanup uses public Workspace unmount, "
        "Sandbox close and SQLite Store remove; infrastructure releases use exact owned IDs. "
        "Raw receipts, ownership ledger, source snapshots, configuration and artifact manifests "
        "stay local under ignored `juicefs-bench/.cache/`.", "",
    ]
    extra = config.get("completion_notes")
    if extra:
        lines += [extra, ""]
    if completion:
        lines += [completion["notes"], ""]
    if previous:
        old_state, old_config = previous
        if old_state["source_sha"] != state["source_sha"] or old_config["artifacts"] != config["artifacts"]:
            raise ValueError("prior campaign source or artifact identities differ")
        if {key: row.get("workload") for key, row in old_state["rows"].items()} != {
                key: row.get("workload") for key, row in state["rows"].items()}:
            raise ValueError("prior campaign workload identities differ")
        lines += ["## Retained earlier attempt", "",
                  f"Campaign `{old_config['campaign_id']}` used the same product, tool and workload "
                  "with a 25 s lifecycle budget. Its failure is preserved; the owner subsequently "
                  "authorized the separate 60 s campaign above. Each campaign used independent "
                  "writable state. No throughput is inferred from the timed-out attempt.", "",
                  "| Campaign | Budget s | Execution | Lifecycle ms | Metric table | Runtime cleanup |",
                  "| --- | ---: | --- | ---: | --- | --- |"]
        for row in old_state["rows"].values():
            lines.append(f"| {old_config['campaign_id']} | {row.get('performance_budget_s', 25)} | "
                         f"{row['execution']} | {ms(row.get('performance_invocation_elapsed_ns'))} | "
                         f"UNAVAILABLE — {row.get('reason', 'no reply')} | {row['cleanup']} after inspection |")
        lines += ["", "The original failed receipt, original INCOMPLETE cleanup receipt, custody "
                  "inspection and later successful resource-release receipts remain local and "
                  "unchanged. The prior report text is retained locally; this is the single "
                  "published report for both campaigns.", ""]
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--environment", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--completion", type=Path, help="post-run environment and cleanup notes")
    p.add_argument("--previous-cache", type=Path)
    p.add_argument("--previous-environment", type=Path)
    p.add_argument("--juicefs-pg", type=Path, help="JuiceFS/PG16 state.json")
    args = p.parse_args()
    config = json.loads(args.environment.read_text())
    state = json.loads((args.cache / "campaign.json").read_text())
    cleanup = json.loads((args.cache / "cleanup.json").read_text())
    if state["source_sha"] != config["source_sha"]:
        p.error("configuration and campaign source identities differ")
    completion = json.loads(args.completion.read_text()) if args.completion else None
    if bool(args.previous_cache) != bool(args.previous_environment):
        p.error("prior campaign requires both --previous-cache and --previous-environment")
    previous = (json.loads((args.previous_cache / "campaign.json").read_text()),
                json.loads(args.previous_environment.read_text())) if args.previous_cache else None
    pg = json.loads(args.juicefs_pg.read_text()) if args.juicefs_pg else None
    text = render(state, config, cleanup, completion, previous, pg)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(text)
    print(args.output)


if __name__ == "__main__":
    main()
