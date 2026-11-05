# fs-bench-quick agent instructions

> Status: Current general guide.

These instructions apply to `fs-bench-quick/` and extend the repository-root
[CLI and cache rules](../AGENTS.md). This file is the suite's current contract;
[cases.py](src/cases.py) pins the exact workload bodies, setup and provenance.
Reading these instructions does not start a campaign or authorize repeating
completed samples.

Use the existing runner with the exact bodies, environment and provenance in
[cases.py](src/cases.py). Preserve Bash/pipefail semantics. C12's Git commit belongs
to the workload; the explicit LayerFS Commit remains a separate operation.

## Workloads and implementation

The macOS suite covers twelve cases on native, Docker, Lima and Apple Container,
with SQLite and PostgreSQL on each machine: 96 rows. Other platforms are outside
this campaign. The suite originated from
[layerfs-project#15](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/15),
with public CLI calls and optional independent verification.

| Case | Work | Starting view |
| --- | --- | --- |
| C01 | Create 1,000 numbered files | Empty |
| C02 | Create them, then stat each | Empty |
| C03 | Create them, then remove them | Empty |
| C04 | Create 110 directories and 1,000 empty files | Empty |
| C05 | Create that tree, then find/count its files | Empty |
| C06 | Write 64 MiB | Empty |
| C07 | Write 64 MiB, then copy it | Empty |
| C08 | Write 64 MiB, then read it | Empty |
| C09 | Read the committed 64 MiB file | Committed base |
| C10 | Copy the committed 64 MiB file | Committed base |
| C11 | Overwrite it with the defined zero-over-zero body | Committed base |
| C12 | Git init, create 100 files, add and commit | Empty |

Use the Python standard library and one shared lifecycle in `src/run.py`, workload
and proof definitions in `src/cases.py`, timing/eligibility in `src/measure.py`, and
report generation in `src/report.py`. Configuration supplies machine and backend
variations. Add modules only for a demonstrated independent responsibility.
Pin original body, setup and verifier provenance/hashes before measurement;
deliberate changes require a new workload version. Accept valid UpToDate Commits.

Preparation reuse, enforcement overhead and final infrastructure teardown are
reported separately from case timing. Ready C09–C11 execution consumes its
prepared base. No warm-up, duplicate workload, hidden base reconstruction or
pre-measurement content proof belongs in the case path. Gather machine facts
once per configuration and keep per-case observations bounded. Missing phase
CPU/memory, logical/physical Store growth, WAL/overlay/temp or server metrics
remain unavailable; post-command WAL absence proves no peak, and a process
lifetime peak is not a phase peak.

## Select the product before running

- Resolve the selected remote 2.0 implementation branch at campaign start and
  record its full commit SHA. The observed branch name is `layerfs_v2_0_0`;
  resolve the remote rather than guessing punctuation or substituting `main`.
- Build the CLI, native daemon and Linux bundle from one clean source snapshot,
  with PostgreSQL support where selected. Record binary, bundle and image
  identities. Use the selected source's worktree launcher for build resources.
- Read that snapshot's applicable `AGENTS.md`, measurement rules, report template
  and worktree rules. Preserve its product contracts and machine-specific disk
  rules. Do not switch another owner's checkout or mix artifacts from commits.
- Use an absolute pinned CLI path. An installed `layerfs` on `PATH` may belong to
  another version. Check grammar with the selected executable's
  `help <family> [<call>]` before using commands on a new product identity.

The completed diagnostic campaign used commit
`b919f50eaf9cce79671f8501a580279d23cc5f3c`. That is historical evidence, not a
permanent latest-source pin. The command forms below were checked against it.

## Prepare the database through the CLI

Keep one independent writable Store/history per selected row. Inputs are issued
once and never returned to a pool after mutation or uncertainty. Reuse builds,
images, ready machines and closed prepared inputs; never reuse a measured sample.

For SQLite, the preparation sequence is:

```text
layerfs store create <store>
layerfs project init <store>/p <owned-empty-source-directory>
layerfs branch fork <store>/p lane main
layerfs store push <store> <machine>    # guest SQLite only, before any Sandbox
```

At the documented pin, `store create` creates SQLite on native with the
Disposable profile. Confirm the returned `profile` is `disposable` and the
selected source's WAL/OFF contract. Durable execution is disabled by the owner;
do not enable it or invent a profile flag unsupported by the selected CLI.

`store push` relocates the authoritative Store and retires its native source;
it is not a clone. Record destination custody and transfer bytes. For C09–C11,
build and Commit the registered 64 MiB base on the destination through the same
Sandbox/Workspace CLI lifecycle, then unmount and close that setup Sandbox.
Ready case execution performs no Store transfer or base reconstruction.

For PostgreSQL, provision the server and a distinct empty database per selected
row before attachment. Use a password environment reference, never a password in
the URL, logged argv, receipt or source:

```text
layerfs store connect <store> postgresql://<user>@<host>:<port>/<database> --password env:BENCH_PG_PASSWORD --synchronous-commit off
layerfs project init <store>/p <owned-empty-source-directory>
layerfs branch fork <store>/p lane main
```

The CLI creates LayerFS's schema in an existing database; it does not create the
PostgreSQL server or database. PostgreSQL inputs are not pushed or pulled.
Pin server version, settings, resources and actual guest reachability. A host
loopback URL may be rewritten for a guest; record the actual route and listening
interface. Separate databases do not prove cold shared buffers or server cache.

## Use the existing runner and exact matrix order

Use [run.py](src/run.py) rather than adding another lifecycle runner.
Start from [the environment example](environments.example.json),
replace artifact placeholders and register exact infrastructure release commands.
An example `ready: false` or unowned disposal resource is not runnable setup.

For incremental implementation/execution, prepare and run each current row before
advancing: C01 through C12; within each cell native, Docker, Lima, Apple Container;
within each machine SQLite, PostgreSQL. Checkpoint all eight outcomes per cell.
Do not run all cells of one machine or database first. Keep benchmark attempts
serial; builds, provisioning and cache resets must not overlap an attempt.

From the repository root, one selection uses:

```bash
python3 fs-bench-quick/src/run.py prepare \
  --environment /private/environment.json --cache /private/prepared \
  --case C01 --machine native --backend sqlite

python3 fs-bench-quick/src/run.py run \
  --environment /private/environment.json --cache /private/prepared \
  --case C01 --machine native --backend sqlite \
  --output /retained/results/C01/native/sqlite
```

Use fresh campaign identities and output paths. A new output path does not
authorize repeating an unchanged treatment. Missing prerequisites are NOT_RUN;
failed attempts retain their failures. Do not automatically retry, reconnect,
reprepare or replay a failed or uncertain operation.

## Parse results and keep timing boundaries clear

Check both the CLI process result and its complete JSON object. In particular,
`workspace exec` must return workload `exit_code: 0`; CLI transport success alone
does not establish workload success. Missing, malformed or truncated results
are failures/uncertainty, not zero-duration samples. At the documented pin,
process exit 2 denotes invalid arguments and 125 denotes refusal; retain the
structured error and exact custody rather than guessing whether an effect ran.
List results are objects with an `items` array, not bare arrays.

## Report format

Follow the root's single-report publication rule. Use **C01 through C12** as
section headings, with one table of eight configurations under each heading.
Display machines as **Docker, native, Lima, Apple Container**, with **SQLite then
PostgreSQL** for each machine. Docker is the baseline. Display order is separate
from execution order, which still starts with native.

Use separate columns: **Machine**, **Database**, **Create ms**, **Exec ms**,
**Commit ms**, **Cleanup ms**, **End-to-end ms**, **Exec / Docker**,
**Commit / Docker**, **End-to-end / Docker**. Define Create as Sandbox creation
and Commit as LayerFS Commit. Do not combine metrics into an unlabeled triplet.

End-to-end case time includes Sandbox creation, mount, Exec, Commit, unmount and
normal case cleanup. It excludes preparation and initial Python startup/configuration
validation; full process wall time, when collected, is separate. Keep execution,
verification, performance eligibility and cleanup outcomes explicit in the summary.

CLI call times include launch/routing and applicable Store open/close work.
Command-only time is unavailable unless independently instrumented and validated.
Keep unavailable CPU, memory and storage metrics explicitly unavailable.

The current cache assessment fails closed for all eight routes. Mount can warm
immutable metadata even for an empty starting view; Exec's writes can remain in
the live overlay SQLite pager and OS cache before Commit. A fresh process or
mount does not demonstrate coldness. Unmount deletes the overlay, so remounting
cannot reset caches while preserving a dirty frontier. There is no demonstrated
public CLI control that releases and observes these caches while preserving the
same live Workspace and mutations.

Cold qualification requires phase-specific dependency accounting and effective,
owned controls for canonical/pager caches, host and guest OS caches, virtual-disk
backing and PostgreSQL shared buffers/server OS cache where applicable. A server
restart alone does not clear OS pages, and separate databases do not establish
cold buffers. Never purge a shared host. Retain control method, boundary, cost
and residency or equivalent validated evidence without warming the inputs during
validation. Preserve authoritative identity, open/reference state and pending
mutations; add no private protocol or direct Store SQL escape hatch.

C07/C08 read their own writes within the exact body. Preserve those bodies and
assess that warmth explicitly; an initially cold state cannot qualify later
reads automatically. The completed campaign did not demonstrate cold
live-Workspace state before Commit. Its timings remain INELIGIBLE diagnostics,
including requested ratios. Do not relabel retained receipts after the fact.

For an explicitly requested Docker baseline, ratio means **machine elapsed time
divided by Docker elapsed time**, separately per cell, database and metric.
Docker is 1.00; below 1 means less elapsed time. Label diagnostic ratios clearly;
the standard report admits qualified comparisons only for matching eligible rows.

Verification is **off by default**. `run --verify` adds a separate independent
proof after measurement, with a target of at most 1 second and hard budget below
10 seconds including proof mount/exec/unmount. A default run is UNVERIFIED even
when execution passes. Do not add proof by repeating an unchanged timing sample.
Default case invocation budget is 15 seconds; prospectively declared exceptions
may reach 25 seconds. Give every test command an explicit timeout at most 120
seconds. No benchmark execution is needed for documentation-only edits.

## Close cases and finish the campaign

After known successful unmount and Sandbox close, use:

- SQLite: `layerfs store remove <store>` on its current machine. Do not pull it
  home for deletion.
- PostgreSQL: `layerfs store disconnect <store>`. This removes the registration,
  not the server database data; keep that allocation recorded until disposal.

For a known failed case, use `workspace unmount <ws> --discard` only when custody
is known and discarding is the declared cleanup action. Do not force-close,
delete or replay after an uncertain reply. Preserve the Workspace, Store and
containing infrastructure for inspection. Local timeout does not prove remote
execution stopped. Record intent before allocation and exact identity afterwards.

Separate single-row invocations require explicit finalization:

```bash
python3 fs-bench-quick/src/run.py finish \
  --environment /private/environment.json --cache /private/prepared
```

A matrix run finalizes infrastructure automatically. Finish releases known-safe
case resources, then exact campaign-owned infrastructure in dependency order.
Dispose of PostgreSQL data by releasing the dedicated owned server/data volume
or only exact owned databases on a borrowed server. Restore infrastructure the
campaign started to its recorded prior state. Preserve other owners' resources,
uncertain state and protected build caches; no global prune or guessed prefix
deletion. A failed/uncertain release blocks deletion of containing resources.

Retain receipts, the append-only ledger, final state, redacted configuration,
artifact/source identities and cleanup dispositions before deleting temporary
homes, credentials, staging and prepared inputs. Export exact completed build
cache releases through the selected worktree's cleanup tools. Record protected
exceptions and observed absence/space recovery; do not claim allocation estimates
as physical recovered bytes.

Use the completion date and full LayerFS product SHA in the report path. Identify
the harness commit separately inside the report. Follow the
[result directory convention](../result/README.md); keep raw working data local.

Execution, content verification, performance eligibility, case cleanup and final
infrastructure cleanup are distinct outcomes. Cleanup FAIL/INCOMPLETE prevents
overall success. The completed owner-selected diagnostic campaign required 96
execution PASS rows and final cleanup COMPLETE, with timings INELIGIBLE; that
scope does not establish performance or release qualification for future work.
