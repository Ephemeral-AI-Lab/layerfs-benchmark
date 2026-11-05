# Six filesystem benchmark suites

> Status: Current planning checklist; no release candidate exists.

Implement [#55](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/55)
fio, [#56](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/56) fsx,
[#57](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/57) fsstress,
[#58](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/58) mdtest,
[#59](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/59) pjdfstest and
[#60](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/60) smallfile,
under [parent #54](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/54).
Creating this specification does not start implementation or benchmark runs.
Follow the root [AGENTS.md](AGENTS.md).

## Layout and shared code

Follow the layout established by `ca157f36bd62431ab7ffab8dc3abfdc4cf53ab0f`:
each suite is a root-level directory, with implementation in `src/` and tests
in `tests/`. Keep its concise `AGENTS.md`, usage `README.md`, environment example
and `.gitignore` at the suite root. Create each suite only when implementing it.
Do not introduce a `benchmarks/` wrapper or restore archived runners.

The working reference is [fs-bench-quick/src/run.py](fs-bench-quick/src/run.py),
with [cases.py](fs-bench-quick/src/cases.py),
[measure.py](fs-bench-quick/src/measure.py) and
[report.py](fs-bench-quick/src/report.py). The old root-level script paths are
obsolete. Existing fs-bench-quick results remain unchanged.

Reuse its CLI lifecycle, deadlines, resource custody and result parsing. Extract
only helpers actually shared by fio and fs-bench-quick into `shared/src/`, with
focused checks in `shared/tests/`; keep suite entrypoints small and workloads in
each suite's `src/cases.py`. Use the Python standard library. No plugin system,
background service or six copied lifecycle implementations. Shared selection and
reporting must accept each suite's case list, not assume C01–C12 or 96 rows.
Keep fs-bench-quick's twelve cases and public command behavior intact.

## Product, tools and matrix

At campaign start resolve the remote 2.0 branch, observed as `layerfs_v2_0_0`,
and record the full SHA. Build matched release CLI, native daemon and Linux
bundle from that clean snapshot, with PostgreSQL support. Read its current
instructions, measurement rules and worktree/disk rules. Do not reuse the old
campaign's SHA as a claim of latest source or silently change product identity.

Pin upstream tool revisions and their builds once per host/guest architecture.
Build/install outside measured calls and reuse cached tools/images. Do not patch
third-party source. Record unsupported platforms/dependencies as NOT_RUN with
the exact prerequisite; product or workload failures remain FAIL.

Every case registers eight configurations: native macOS, Docker, Lima and Apple
Container, each with SQLite and PostgreSQL. Use SQLite Disposable/WAL/OFF,
PostgreSQL synchronous commit off, and `LAYERFS_CONSTRUCTION_WORKERS=1`.
Durable and additional machines are outside this assignment.

## Initial case set

These are proposed small v1 workloads, not measured promises. Before the first
product attempt, resolve exact flags against the pinned upstream tool, freeze
the case IDs, setup, argv, seed, counts, sizes and expected tool result in
`src/cases.py`, and document them in the suite's `AGENTS.md`. Do not invent flags
or silently use different workloads on different machines. A necessary later
change gets a new workload version and retains the previous outcome.

| Issue / suite | Cases | Initial workload |
| --- | --- | --- |
| #55 fio | F01–F04 | Sequential write/read: 64 MiB, 1 MiB blocks. Random write/read: 8 MiB, 4 KiB blocks. One job, synchronous engine, depth 1, one fixed byte-count pass, fixed seed. Buffered I/O; no warm-up, ramp time, repeated loops or implicit data preparation in a read case. |
| #56 fsx | X01 | One process, seed 1, 1,000 operations, maximum file size 8 MiB and operation size 64 KiB. Freeze a supported read/write/truncate operation selection; retain fsx's built-in consistency checks. |
| #57 fsstress | S01 | Two processes, seed 1, 512 requested operations per process. Freeze operation names/weights and allocation bounds prospectively; report actual completed work and unexpected errors. |
| #58 mdtest | M01–M02 | Separate file and directory cases: one MPI rank, 512 entries, one iteration, create/stat/remove phases. File case uses empty files. This is a small diagnostic, not an MPI scaling study. |
| #59 pjdfstest | P01–P04 | Small fixed upstream script selections for open, rename, chmod and symlink. Pin the exact script list before execution; retain all assertions and report TAP pass/fail/skip counts. |
| #60 smallfile | L01–L05 | Separate create/read/stat/rename/delete cases. Two threads, 256 files per thread, 4 KiB files, fixed directory distribution and no distributed host launcher. |

This proposed set has **17 cases / 136 registered rows**. Any prospective case
selection change updates that count before execution. No suite inherits twelve
cells merely because fs-bench-quick has twelve.

Use upstream documentation and the selected revision's help:
[fio](https://github.com/axboe/fio),
[fsx](https://kernel.googlesource.com/pub/scm/fs/xfs/xfstests-dev/+/31f7192f90a89a6f808a37c3a3cd30491bd50eba/ltp/fsx.c),
[fsstress](https://kernel.googlesource.com/pub/scm/fs/xfs/xfstests-dev/+/31f7192f90a89a6f808a37c3a3cd30491bd50eba/ltp/fsstress.c),
[mdtest / IOR](https://github.com/hpc/ior),
[pjdfstest](https://github.com/pjd/pjdfstest), and
[smallfile](https://github.com/distributed-system-analysis/smallfile).
These are references, not selected build pins.

Treat tool semantics explicitly:

- fio reads consume prepared data; disable unrequested preallocation and sync
  additions in the declared profile. Direct I/O is not a portable cold-cache proof.
- fsstress's expected operation errors are not automatically test failures;
  preserve upstream interpretation and expose effective work. A zero-work run
  is not PASS. Do not silently remove unsupported operations after a failed run.
- mdtest needs its pinned MPI runtime on every selected route; use a single-rank
  invocation and record each reported phase. Do not replace it with shell loops.
- pjdfstest requires the privileges and TAP tooling its upstream specifies;
  macOS support must be established, not assumed. Missing privileges/support are
  NOT_RUN. Failed assertions stay FAIL; an all-skipped selection is not PASS.
- smallfile reads use files created by the same pinned tool/configuration.
  Its upstream cautions about single-thread timing; use the declared two threads
  and report the small workload's limits. Keep any declared tool data checks.

## Preparation and execution

Owner execution update: implement suites in parallel with at most three child
agents and explicit suite ownership. Integrate shared changes centrally. Execute
measured suites in issue order: fio, fsx, fsstress, mdtest, pjdfstest, smallfile.
Within a suite use **case → machine → database**: native, Docker, Lima, Apple
Container; SQLite then PostgreSQL. Complete and account for all eight outcomes
of a case before advancing. Never run benchmark workloads, builds, provisioning
or cache resets concurrently with a measured row. Record external interference.

Prepare only the next independent input. Reuse one campaign-owned set of ready
machines and one dedicated PostgreSQL server across the six suites while their
product identities match. Do not boot/rebuild between cases or copy tool trees
into every Store. Maintain one private campaign home and an exact resource list
with intent recorded before allocation. Keep compact local receipts and one
retained source snapshot per harness identity rather than a source-tree copy per row. Never publish them.

SQLite preparation uses public `store create`, empty `project init` and
`branch fork`. Guest SQLite pushes only the small initialized Store before any
Sandbox. Build necessary read/stat/rename/delete fixtures on the destination
through setup Workspace Exec and Commit, then unmount/close setup. Each measured
row consumes independent ready state once; no fixture rewrite or transfer in its
timed path. State whether upstream fixture creation writes zero or nonzero data.

Reuse one dedicated PostgreSQL server with pinned settings/resources. Provision
an isolated empty database for each selected row outside measurement, then use
CLI `store connect --password env:... --synchronous-commit off` and public project
setup. PostgreSQL data is never pushed/pulled. Record server placement and each
guest's actual route. Keep its data allocation owned until final disposal.

Every row uses the pinned public CLI in this order:

```text
sandbox create → workspace mount → workspace exec → workspace commit
→ workspace unmount → sandbox close
```

Pass the returned `ws` identifier, check both CLI and workload exits, and parse
the upstream tool's results. Accept valid Committed/UpToDate outcomes. Never
substitute SDK calls, private worker messages or direct Store SQL. Provider and
PostgreSQL administration may use their owning infrastructure tools.

Default complete case budget is 15 seconds; a declared exception may reach 25.
All phase calls consume one remaining case deadline. Tool sizes are finite;
do not replace a timeout with a smaller unrecorded workload, extra workers or
automatic reruns. A timeout retains its failure and remote uncertainty.

## Cache state and verification

Warm setup reuse is encouraged. Measured phases receive no credit for setup,
earlier-phase or own-write warmth. Document relevant host/guest/daemon/database
caches separately. Unknown or unenforceable state means INELIGIBLE diagnostics;
do not delay these tasks to build a new cache-control product feature.

Extra independent committed-result verification is optional and off by default.
When selected, run it once after measurement with a separate budget below
10 seconds, targeting at most 1 second. Tool-internal assertions, consistency
checks and error reporting remain part of the declared workload. Tool checks
are not independent proof of the LayerFS committed result.

## Cleanup and one report

After each known successful case, unmount and close through the CLI; remove
SQLite on its current machine or disconnect PostgreSQL. A disconnect does not
delete its database. At finish, release the dedicated server and owned data,
owned machines/containers/volumes, temporary inputs, homes and credentials.
Restore borrowed infrastructure to its prior state. Preserve uncertain state,
containing resources and other owners' resources; never blindly force-delete or
replay an uncertain operation. Cleanup FAIL/INCOMPLETE prevents overall success.

Publish only `result/YYYY-MM-DD/<suite>/<full-layerfs-sha>/report.md`, following
the [report convention](result/README.md). Keep it short: outcome, configuration,
case tables, critical observations, limits and cleanup. No published logs,
receipt directories, manifests, CSV/JSON bundles, binaries or source snapshots.

Each case has one table of eight rows, displayed **Docker, native, Lima, Apple
Container**, with SQLite then PostgreSQL for each. Display order does not change
execution order. Separate Create, Exec, LayerFS Commit, Cleanup and End-to-end
times, with units. Define End-to-end to include mount/unmount and intervening
harness work, while excluding input preparation and initial Python startup.
Report setup and final teardown separately. Docker ratios are machine elapsed
time divided by Docker elapsed time for the same case/backend/metric.

Add only useful upstream metrics: fio I/O rates/latencies, fsx/fsstress operation
counts, mdtest phase rates, pjdfstest pass/fail/skip counts, and smallfile file
rates. Preserve reported units and denominators. CLI wall time is not pure tool
time; unavailable resource/storage measurements remain unavailable. Do not call
INELIGIBLE ratios qualified comparisons or execution PASS independent correctness.

## Delivery checkpoints

1. For fio, implement the minimum shared lifecycle adaptation and the first
   frozen case. Run focused harness checks before any product attempt. Preserve
   fs-bench-quick's surviving tests; no full historical campaign rerun.
2. Complete each case's eight configurations in order. Fix actionable defects
   with a change record; retain failures and rerun only affected work at its new
   identity. External blockers remain explicit rather than fabricated PASS.
3. Checkpoint each suite locally and release its case resources before advancing.
   Keep the shared machines/server owned for the next suite. At overall campaign
   finish (or terminal failure), release known-safe infrastructure once, then
   publish the six reports with the actual final cleanup disposition.
4. For each of #55–#60, link the implementation/report and record execution,
   verification, eligibility and cleanup separately. Close only on an achieved
   scope or explicit owner-accepted exclusion. In Project 2 set **Track: Main**,
   **Lane: Benchmark** and the actual Status; leave the shared project open.

Use focused tests for argument/result parsing, deadline/custody failures and
complete row accounting. Every test invocation has an explicit timeout at most
120 seconds; keep cheap proof separate. No new test or benchmark run is needed
merely to create or edit this document.

## Campaign prerequisite findings (2026-11-06)

The selected unmodified xfstests fsx/fsstress sources require Linux headers, so
native macOS has four NOT_RUN rows across X01/S01. Pinned LayerFS executes all
four routes as a nonroot identity and refuses root, with no-new-privileges on
guest routes. Upstream pjdfstest requires root; its 32 rows are NOT_RUN. No public
CLI root option or safe image workaround exists. Implement and account for those
rows, retain the exact blockers, and run the other 100 supported rows. This does
not qualify the unsupported rows or change the product security contract.
