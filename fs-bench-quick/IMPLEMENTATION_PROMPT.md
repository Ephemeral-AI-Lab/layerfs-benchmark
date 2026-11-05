# fs-bench-quick implementation prompt

> Status: Current planning checklist; no release candidate exists.

Use the following prompt to implement the suite. The prompt authorizes delegated
implementation when invoked; writing this document does not start the campaign.

---

Implement `fs-bench-quick` in `/Users/yifanxu/Ephemeral-AI-Lab/layerfs-benchmark`.
Follow `fs-bench-quick/SPEC.md` and the owner requirements below. Carry the work
through implementation, bounded execution, evidence/reporting and final cleanup.
Use subagents iteratively, with explicit file/resource ownership. Optimize for
fast preparation, fast cleanup and a small shared implementation.

Owner clarification, 2026-11-06: finish all 96 CLI execution/cleanup checks and
report timings as INELIGIBLE diagnostics. Terminal PASS for this campaign means
96 execution PASS plus COMPLETE final cleanup, with optional verification SKIPPED
by default. Implementing a public cache-control capability is outside this run.
Do not present this diagnostic terminal outcome as qualified speed or release
correctness evidence.

## Non-negotiable execution order

The outer loop is the cell, the middle loop is the machine, and the inner loop
is the database. Use this exact sequence:

```python
for cell in C01_through_C12:
    for machine in ["native", "docker", "lima", "apple-container"]:
        for database in ["sqlite", "postgresql"]:
            implement_current_configuration(cell, machine, database)
            execute_selected_bounded_attempt(cell, machine, database)
            record_outcome_and_release_case_resources()
    checkpoint_cell_with_all_eight_outcomes()
finish_campaign_and_report()
```

For C01: native/SQLite, native/PostgreSQL, Docker/SQLite, Docker/PostgreSQL,
Lima/SQLite, Lima/PostgreSQL, Apple Container/SQLite, Apple Container/PostgreSQL.
Only then start C02, repeating through C12. There are eight configurations and
96 registered rows. Do not finish all cells on one machine or one database first.
Do not build twelve separate runners.

Each checkpoint must account for all eight configurations with actual outcomes.
A missing prerequisite is NOT_RUN; a failed attempt retains its failure. Neither
is PASS. Resolve actionable defects before advancing; when an external blocker
cannot be resolved safely, retain the exact blocker and continue independent work
in order without claiming that the cell or campaign is fully qualified.

## Resolve current product authority

Use the latest remote 2.0 implementation branch as the product reference. The
owner called it `layerfs-v_2_0_0`; the observed actual remote name is
`layerfs_v2_0_0`. Resolve the remote instead of guessing from punctuation or using
main. At prompt creation its head was
`b919f50eaf9cce79671f8501a580279d23cc5f3c`; this is an observation, not a permanent
pin. Resolve again when starting, record the selected full SHA, and use a clean
snapshot of that commit for source, release builds and bundles.

Read the applicable current AGENTS.md files, measurement rules, report template,
worktree rules and current source/contracts from that selected snapshot. Use the
parallel-worktree launcher for LayerFS build resources. Preserve unrelated work.
Do not reset or switch somebody else's active checkout. Do not traverse archived
benchmark content, revive old runners, or edit/run/repair fs-bench-pro.

Product changes require a clean derived source identity, matched artifacts and
an explicit change record. An upstream branch moving during the campaign does
not silently change its treatment. Assess a necessary update explicitly and rerun
only affected checkpoints; never mix artifact identities in a paired claim.

## Subagent workflow

The primary agent owns sequencing, the campaign manifest, integration decisions,
measurement admission, the report and final cleanup. Delegate implementation and
focused diagnosis, not overall responsibility.

Use at most three concurrent child agents and reuse them for follow-up tasks:

| Agent | File/responsibility ownership |
| --- | --- |
| Lifecycle worker | `run.py`: CLI subprocesses, preparation, lifecycle, receipts and cleanup; related focused tests |
| Workload worker | `cases.py`: current cell body/setup, provenance and optional verification; related focused tests |
| Measurement worker | `measure.py`: timing, cache validity, resource accounting and budget handling; related focused tests |
| Primary | `report.py`, configuration example, docs, integration, ordered execution and campaign ownership |

Workers are not alone in the codebase: they must preserve and accommodate other
agents' changes. Give every task an explicit owned file/test subset and scope it
to the current cell or a specific shared prerequisite. Avoid multiple owners of
one file. A worker needing another owner's edit sends a concrete request.

For each cell, delegate its workload mapping and any necessary lifecycle or
measurement extension. Integrate those changes before execution. Keep scope
limited to the current cell; do not ask workers to implement future cells or run
future configurations. Shared helpers may naturally serve later cells.

The primary may delegate the current row's execution to one worker, temporarily
assigning it exact campaign resources and output paths. Only that row may run.
The primary must wait for its receipt and cleanup disposition before admitting
the next row. Subagent parallelism must never overlap measured workloads, cache
resets, server restarts, provisioning or builds with this campaign's measurement.
Record external interference; do not interrupt other owners or add a global gate.

At each cell checkpoint review exact CLI commands, source/artifact identities,
setup reuse, all eight row outcomes, cache eligibility, timings and resource
disposition. Update the append-only ledger and give the user a concise progress
update. Reassign workers only after reconciling their changes and resource custody.

## Keep the implementation small

Use the Python standard library and the four files specified above. One shared
lifecycle handles all configurations. Environment records supply machine names,
artifacts, PostgreSQL endpoint, credential references, resources and cache controls.
Add a file only for a demonstrated independent responsibility. Do not build a
framework, plugin registry, service, scheduler or generalized database adapter.

Every LayerFS call invokes the pinned public `layerfs` executable. All workload
and proof commands go through `layerfs workspace exec`. No LayerFS SDK imports,
private worker calls, direct Store SQL or test-only product stand-ins. Ordinary
OS timing/cache/monitoring facilities and explicit infrastructure administration
are permitted; account for them separately from LayerFS operations.

Preserve exact C01-C12 bodies/setup semantics with provenance and hashes. C04/C05
contain 110 directories; C11 overwrites the defined committed content. Accept
UpToDate where appropriate. Check CLI success and embedded workload exit status
separately. Preserve failures, missing timing and uncertainty exactly.

## Efficient preparation

Provision ready machines and one dedicated PostgreSQL server once. Reuse pinned
binaries, bundles, images and closed prepared inputs. Prepare only selected rows,
preferably just ahead of the current cell, and record cost separately. Preserve
independent Store/history state per row. Full-matrix maxima are 48 SQLite Stores
and 48 PostgreSQL databases; release consumed rows instead of retaining 96 live
allocations until the end.

SQLite: create on native, initialize the empty project and fork the working
Branch. For guest cases push that small Store once through `layerfs store push`
before creating its Sandbox. For C09-C11 build and Commit the defined base on the
destination, then release the preparation mount/Sandbox. Native needs no push.
The full matrix requires 36 initial guest pushes, zero in ready-input performance
invocations and no pull-back solely for deletion.

PostgreSQL: provision isolated empty databases on the same pinned server, attach
them through `layerfs store connect` with a credential reference and explicit
`synchronous_commit=off`, then use CLI project/Branch/workspace setup. LayerFS
initializes its schema but does not create the server/database. Ensure both host
CLI and guest daemons can reach the endpoint; pin actual routing/TLS/settings.
Do not push/pull PostgreSQL or silently add schema-selection support.

Mark prepared mutable inputs consumed before mutation. Never recycle them after
an attempt or unknown outcome. Use supported independent copies where available;
do not invent a Store clone API or copy live database files. Repeated setup may
be avoided only outside the measured operation. Record preparation and final
infrastructure costs rather than hiding them in an unreported earlier command.

## Honest performance; verification off by default

Cache setup artifacts, but do not use setup/own-write warmth to qualify measured
LayerFS phases. Enforce the declared host/guest/daemon/worker/PostgreSQL cache
conditions at their specified boundaries. A new database, mount, filename or CLI
process alone does not establish coldness. Remove the inherited workload warm-up.
Unknown or mismatched state is INELIGIBLE; missing timing is never zero.

Preserve C07/C08's write-then-copy/read bodies and explicitly assess their
own-write cache effects. Keep policy-violating timings diagnostic; do not silently
change the body or label them eligible. Cache enforcement cost remains visible
in complete invocation wall time.

Default content verification is SKIPPED and correctness is UNVERIFIED. Perform
only cheap execution/result/timing checks. Add independent proof only with
`--verify`: one fresh mount, one compact oracle command, one unmount, all after
measurement. Target <=1 second and enforce a total proof budget strictly <10
seconds. Do not weaken assertions or run proof after each tool call.

Default delivery is a performance diagnostic campaign. Report qualification gaps
without turning verification on to satisfy the old issue text. If qualification
is explicitly selected, plan `--verify` before the corresponding one-time samples.

Use complete performance invocation budgets <=15 seconds by default, with
prospectively declared exceptions <=25 seconds. Set explicit subprocess deadlines.
Every test invocation has an explicit timeout <=120 seconds, with builds first.
Target prepared-input claim <=1 second and healthy case cleanup <=2 seconds;
these are engineering targets, not existing measurements. Measure Sandbox creation
and cache-control costs, too. Build artifacts before measured work.

One performance sample per case/arm. No unchanged resampling, best-of, automatic
retry/replay or full-matrix rerun at the end. Diagnose retained failures with
count-driven/source evidence. After a documented change rerun only necessary
affected checkpoints. Reuse unaffected evidence with exact scope justification;
record harness changes even when they do not affect a measured mechanism.

Use SQLite Disposable/WAL/OFF, PostgreSQL synchronous_commit=off and
`LAYERFS_CONSTRUCTION_WORKERS=1` except supported namespace Init parallelism.
Durable is NOT_RUN, disabled by owner. Record time and storage together; include
PostgreSQL server resources, actual route costs and unavailable counters. Do not
use lifetime memory peaks as measured phase peaks.

## Cleanup is part of implementation

Allocate every resource under one campaign ID. Record exact identities and
created/borrowed ownership before and after allocation. Close/release completed
case resources promptly; keep shared campaign infrastructure between cells.

On the last selected row, failure that terminates the campaign, or handled
interruption, finalize receipts and clean known-safe resources in dependency
order: Workspaces, Sandboxes, SQLite Stores on their current machines,
PostgreSQL registrations/data, workers/machines/containers/volumes, temporary
homes and prepared fixture allocations. Include unused prepared inputs.

Where the campaign owns a wholly disposable PostgreSQL instance, remove its
owned server/data allocation once. On a borrowed server, release only exact
owned databases after their users finish. Disconnect is not database deletion.
Leave pre-existing shared caches and evidence; restore borrowed infrastructure
only according to its recorded prior state and current ownership.

Preserve uncertain state and its containing VM/server/volume. Never force-delete,
replay or infer release from a CLI timeout. Produce a cleanup receipt with
released identities, actual free-space changes where observable, and every
retained allocation/reason. Known cleanup failure is FAIL; uncertain release is
INCOMPLETE. Neither permits an overall successful completion claim.

Provide bounded `finish` handling for campaigns split across invocations or
interrupted by an unhandled kill. Inspection does not replay an uncertain action.
Check disk at assignment start, required intervals, before/after large work and
at handoff, following standing cleanup authority and protection rules.

## Completion and handoff

Persist progress in the campaign ledger so a context reset resumes at the exact
next cell/machine/database without rerunning completed samples. Summarize each
cell's eight dispositions, code changes, remaining blockers and resource custody.

At final handoff give the implementation paths, pinned product/harness/artifact
identities, 96-row accounting, per-configuration comparisons, exact reproduction
commands, measured setup/cleanup cost, verification disposition and cleanup
receipt. Include defects and explicit infrastructure gaps. Do not claim speed
PASS without a predeclared gate or release correctness from unverified rows.

Follow repository commit/production-LOC rules if commits are created. Do not
publish, push, or post issue updates solely because this prompt names an issue.
