# fs-bench-quick implementation specification

> Status: Proposal; target LayerFS 2.0; not a released contract.

## Purpose and decisions

Build a small benchmark that gets to the measured operation quickly. Prepare
expensive inputs once, reuse provisioned machines, measure one case once, and
release its disposable state promptly. All LayerFS operations use the public
`layerfs` executable. Verification is optional and off by default.

This proposal implements [layerfs-project#15](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/15)
with two requested changes: replace internal Node SDK calls with CLI calls, and
run independent correctness proof only when explicitly selected. The runner and
protocol tasks (#16 and #17 in that repository) need the same amendments. An
unverified performance run does not satisfy the issue's release qualification.

Owner execution scope, confirmed 2026-11-06: finish the 96 CLI execution/cleanup
checks and report timings as ineligible diagnostics. No new cache-control product
capability is required for this campaign. Its terminal PASS means all 96 execution
checks pass and final owned cleanup is COMPLETE; verification remains off by
default. This is distinct from release/performance qualification.

Priority order:

1. Preserve workload meaning and honest measurement.
2. Minimize repeated setup, CLI calls, scans, transfers and teardown.
3. Keep one execution path and a small implementation.
4. Collect useful evidence without making observation the main workload.

## Scope

Host: macOS. Machines: native, Docker, Lima and Apple Container. Store kinds:
SQLite and PostgreSQL. Twelve cases across eight configurations produce 96
registered rows. Other platforms are outside this campaign.

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
| C11 | Overwrite it with the defined body | Committed base |
| C12 | Git init, create 100 files, add and commit | Empty |

Pin original body, setup and verifier provenance and hashes before measuring.
Preserve the exact bodies, including C11's zero-over-zero write. Record deliberate
changes as a new workload version. Accept valid UpToDate Commit outcomes.

## Small implementation

Start with four Python files and one environment example:

- `run.py`: arguments, preparation, case lifecycle, CLI subprocesses, receipts
  and owned cleanup.
- `cases.py`: twelve bodies, two setup definitions, shared verification scripts
  and provenance. Verification definitions are loaded only when needed.
- `measure.py`: monotonic timing, cache enforcement, resource observations and
  eligibility decisions.
- `report.py`: read retained receipts and produce CSV plus a comparison report.
- `environments.example.json`: machine names, artifact paths and identities,
  resources, PostgreSQL endpoint/credential references and cache controls.

Use the Python standard library. Add modules only when an existing file develops
an independent responsibility that needs separation. Use one shared lifecycle;
machine records and Store setup supply its variations. Introduce no general
adapter framework, background service, job queue or plugin system.

Maintain this spec and a short README. Add focused tests for failed CLI calls,
invalid timing/cache evidence, uncertain cleanup and complete row accounting.

## CLI-only boundary

Every LayerFS operation launches the pinned release `layerfs` executable with an
argument array. No LayerFS SDK imports, direct Store SQL, private worker calls or
test-only product routes. Workload and proof scripts run through
`layerfs workspace exec`.

The harness may use ordinary operating-system facilities for timers, fixture
files, cache controls and resource accounting. Machine/provider installation and
PostgreSQL database provisioning are explicit infrastructure prerequisites. They
do not become hidden database administration inside a LayerFS benchmark call.

Capture the CLI process exit code and JSON result separately. A successful CLI
exec can contain a nonzero workload `exit_code`. Parse both. Missing or malformed
output is a failure or ineligible measurement, never a zero duration. Keep output
bounded; verification prints a compact result rather than file contents.

## Prepare once

`prepare` validates and registers reusable assets before any case is measured:

- Matched release CLI, daemons, workers, images and PostgreSQL-enabled features.
- Provisioned, ready machines and pinned tools with their actual versions.
- Closed pristine inputs with the two required starting views.
- A manifest of independently owned prepared Stores/databases for selected rows.
- A demonstrated cache protocol for every selected route and database.

Give preparation and execution one campaign ID. Record every allocated resource
under that ID, including exact Store/database names, machine/container IDs, data
volumes, temporary paths and whether it was created or borrowed. Record creation
intent before allocation and the returned identity afterwards, so interrupted
preparation can be finalized without guessing. A name prefix alone is not
ownership evidence.

Preparation records elapsed time, disk usage, artifact hashes and fixture
identities. Later invocations reuse matching artifacts; changed identities require
new preparation. Do not repeatedly rebuild, download, generate, hash whole trees
or boot machines between cases. Validation that reads measured data happens
before final cache enforcement.

Each case gets independent mutable Store/history state. A prepared Store is
issued once; mark it consumed before the first mutating call, and never return
it to the ready pool after use or an uncertain result. Prepared inputs must have
no live Workspace or Sandbox. Reuse of a machine does not authorize reuse of its
measured-data caches.

Where a supported preparation mechanism supplies independent writable byte
copies of closed masters, record the method and identity. A copy is not evidence
of coldness. Do not invent a public Store clone API or copy live database files.
If the selected CLI route has no supported clone mechanism, construct independent
inputs through public CLI setup in `prepare` and consume them once. Report that
preparation cost honestly; moving it earlier does not make it disappear.

For C09-C11, construct the committed base through the pinned setup semantics.
Do not recreate its write/Commit sequence during every timed invocation.

SQLite lives on its selected machine. PostgreSQL uses a fixed server version,
configuration and resource allocation, with a distinct provisioned database for
each isolated Store. Its schema is `layerfs`; arbitrary schema selection is not
assumed. PostgreSQL databases are never pushed or pulled.

### Concrete database preparation

There are eight configurations, not eight shared writable Stores. Keeping the
issue's per-case isolation means preparing up to 48 SQLite Stores and 48
PostgreSQL databases for a complete 96-row selection. Prepare only selected
rows; consumed inputs are not recycled. Keep the machines and PostgreSQL server
running across their case selections.

For each SQLite row, use `layerfs store create`, `project init` from the empty
source and `branch fork` on native. For a guest row, push this small initialized
Store with `layerfs store push <store> <machine>` before creating its Sandbox.
Construct C09-C11's committed base through the defined workspace setup on the
destination machine, then unmount and close the preparation Sandbox. Thus the
64 MiB base is built where it will be used instead of being shipped from native.
Record this setup placement in the workload mapping. All of this belongs to
preparation, followed by cache enforcement before measurement.

The complete matrix needs 36 initial SQLite pushes: twelve rows on each of
Docker, Lima and Apple Container. Native's twelve rows need none. A ready row
requires no push during its performance invocation. `store push` relocates the
authoritative Store, verifies the transfer and retires the native source; it is
not a clone. Keep the target worker ready, the Store idle and Sandbox-free during
the push, and preserve custody after an uncertain reply. Remove the Store on its
current machine during successful cleanup.

For PostgreSQL, provision one dedicated server once, with pinned version,
storage and resources. Provision a distinct empty database per selected row.
Attach it with the public CLI, passing the password reference and explicit
`--synchronous-commit off`, then perform project/Branch and committed-base setup
through the CLI. LayerFS creates its schema in an existing database; it does not
provision the server or create the database. Preallocated empty databases keep
administration out of the case path without sharing mutation/history state.

Prefer one stable non-loopback server address reachable from the macOS CLI and
all selected guest daemons. Pin authentication and TLS settings. If a host
loopback address is used, record LayerFS's actual route: Docker rewrites it to
`host.docker.internal`, Lima to `192.168.5.2`, and Apple Container to its inspected
gateway. The server must listen on the reachable interface; host-loopback-only
listening is insufficient for Apple Container. Reachability checks are setup
checks and do not read the case's measured content. Database isolation does not
prove cold PostgreSQL shared buffers or server OS cache.

## One case, one simple path

The normal run consumes a ready input and performs:

1. Register the case attempt and claim its prepared input.
2. Create its Sandbox using the public CLI.
3. Establish the measured starting cache state at the specified boundary.
4. Mount, execute the exact case, Commit and unmount, with separate timers.
5. If `--verify` was selected, run the independent proof after measurement.
6. Close the Sandbox, release disposable state and finalize the receipt.

The cache protocol may require boundaries between individual measured phases.
For example, cold Commit needs enforcement after mutations, outside the Commit
timer. Record that cost in harness wall time. Do not insert cache controls inside
an exact workload body without declaring a workload revision.

No untimed workload warm-up, duplicate execution, polling of measured data or
pre-measurement content verification. Gather machine facts once per configuration.
Gather only the per-case state needed to validate the result and its eligibility.

## Cache protocol: reusable setup, honest LayerFS work

Cache immutable setup artifacts on disk. Each measured phase must still pay for
the data/metadata work required by its registered cache contract.

Account for the host and guest page caches, LayerFS daemon/worker caches, and
PostgreSQL shared buffers plus server OS cache. Fresh CLI processes, fresh mounts,
fresh filenames and independent copies alone prove none of these cold.

Cache control must affect only owned infrastructure and must be demonstrably
effective. Keep a dedicated PostgreSQL instance where server cache enforcement
requires restart or reset. Never reset another owner's server or globally purge
a shared host merely to improve this campaign.

Record enforcement method, boundary, elapsed cost and evidence. If enforcement
is unavailable or unproven, retain the timing as diagnostic with performance
eligibility INELIGIBLE. Do not silently fall back to a warm result.

C07/C08 intentionally read data just written in the same body. Preserve them as
specified, and explicitly assess own-write cache effects. A successful cold
starting condition does not establish cold reads later inside that body. Phases
that violate the governing cache policy remain ineligible. Any alternative cold
workload needs its own version and prospective scope decision.

## Verification: explicit, independent and quick

Default: verification is SKIPPED. Perform only cheap execution checks: parse the
CLI result, check command exit status, validate timing, accept the documented
Commit outcome and capture cleanup. These are not a content-correctness proof.

`--verify` adds a fresh verification mount after the measured unmount. Run one
bounded script through the CLI and then unmount. Verify exact names, sizes,
content and relevant metadata; C04/C05 include all 110 directories; C12 checks
tracked files, history and clean status. Reuse common assertions across cases.

Target the complete proof at no more than 1 second; the hard independent-proof
budget remains strictly under 10 seconds, including its mount/exec/unmount. If
the remaining budget is exhausted, stop and record failure. Do not weaken the
oracle or replace content checking with byte counts to meet the target.

Run verification once for the selected final identity. Do not verify after every
CLI call or mix proof time into operation timings. Report proof time separately
and include it in total harness wall time. Unknown outcomes preserve custody.

Default runs are performance diagnostics with correctness UNVERIFIED. A report
may show eligible timings but cannot label the row release-qualified without
matching independent proof. Select `--verify` prospectively for qualification;
do not repeat an unchanged performance sample merely to add verification.

## Fast cleanup

After unmount, close the case Sandbox once and release only its confirmed owned
disposable resources. Remove SQLite on its current machine; do not pull it home
for deletion. PostgreSQL disconnect releases its LayerFS registration but does
not delete server data. Record that remaining allocation explicitly.

Keep machines, image layers, binaries and pristine masters ready between cases
within the campaign. At campaign finish, automatically release all confirmed
campaign-owned mutable resources, including unused prepared inputs. Case cleanup
and final teardown have distinct completion fields; disconnecting is never
reported as deleting a database.

Final teardown is required even with verification disabled. Use the existing
runner and ownership manifest; add no cleanup service. Follow dependency order:

1. Finalize receipts and collect the already-declared resource/storage metrics.
2. Release known inactive Workspaces and close their Sandboxes through the CLI.
3. Remove SQLite Stores on their current machines and disconnect PostgreSQL
   Store registrations. Include consumed and unused prepared inputs.
4. Reclaim PostgreSQL data through the infrastructure owner. If the campaign
   created the whole dedicated disposable server, stop/remove it and its owned
   data allocation once, rather than issue 48 separate database drops. On a
   borrowed server, drop only exact campaign-owned databases after confirming
   their users have released them. A disconnect alone does not complete this step.
5. Release campaign-created workers, machines, runtime containers and data
   volumes through their owning lifecycle tools. Borrowed running machines stay;
   restore borrowed infrastructure that this campaign explicitly started to its
   recorded prior state after releasing its users.
6. Remove campaign-owned temporary homes, transfer/staging files and fixture
   caches. Retain receipts/reports and pre-existing shared binaries/image caches.

Do not tear down a server, VM, volume or parent directory containing retained
uncertain state. Retain that owning resource too and report the reason.

Check exact resource identities after teardown, without reading workload
contents or scanning unrelated resources. Record cleanup duration, actual
available-space changes where observable, and every remaining resource with its
owner and reason. Cleanup is COMPLETE only when all required owned resources are
released; uncertain outcomes are INCOMPLETE and known release failures are FAIL.
The runner must not return an overall success while cleanup is FAIL/INCOMPLETE.
Keep performance results and cleanup verdicts separately visible.

The last selected row of a matrix campaign triggers final teardown automatically.
A terminal preparation/run failure or handled interruption also finalizes all
resources whose release is known safe, preserving uncertain ones. Use bounded
teardown steps and retain output; do not silently retry failed operations. An
explicit `finish` command completes a campaign run in separate single-case
invocations or audits resources left by an unhandled process kill. It inspects
retained operation state first and does not blindly replay uncertain deletions.

A failure is not permission for unconditional force-close, retry, replay or
deletion. Preserve uncertain Stores, Workspaces, database allocations and evidence
under the case ID. Record their resource identities and last known state. A
timeout stops the local attempt; it does not prove a remote command stopped.

## Speed targets and bounds

These are implementation targets to validate with labeled diagnostics, not
measured promises or authority to change the workload:

| Component | Initial target |
| --- | --- |
| Claim prepared input, excluding Sandbox creation/cache enforcement | <=1 s |
| Healthy case cleanup, excluding the measured unmount | <=2 s |
| Explicit independent proof, complete | <=1 s target; <10 s hard budget |
| Performance invocation, without independent proof | <=15 s default |

Record Sandbox creation and cache enforcement separately. Establish their actual
cost before assigning a more specific target. The complete performance invocation
includes input claim, Sandbox creation, cache enforcement, measured operations
and normal case cleanup. Report the whole cost as well as individual operations.
Preparation/provisioning and final infrastructure teardown are explicit separate
commands; report their costs and reuse counts alongside run costs.

Prospectively declared performance exceptions may reach 25 seconds. A selected
case exceeding its budget retains its failure. No workload shrinking, timeout
inflation or extra construction workers. All test invocations have explicit wall
timeouts <=120 seconds, with compilation completed beforehand. Every subprocess
uses a deadline; calls consume the remaining phase/case budget rather than each
receiving a fresh full budget.

Run selected cases sequentially in cell -> machine -> database order: C01-C12;
within each cell native, Docker, Lima, Apple Container; within each machine SQLite
then PostgreSQL. Implement and account for all eight configurations of one cell
before advancing to the next. Subagents may work on disjoint implementation or
analysis tasks, but measured rows never overlap. Reuse ready machine
infrastructure, keep writable inputs isolated, and record external interference.
Do not block other owners with a global build gate. Export
`LAYERFS_CONSTRUCTION_WORKERS=1`; namespace Init retains its supported exception.
Use SQLite Disposable/WAL/OFF and PostgreSQL `synchronous_commit=off`. Durable
execution remains NOT_RUN, disabled by owner.

## Evidence and reporting

Use one fresh output directory per run. Freeze all 96 matrix selections, even
when executing a subset. Each row has separate execution, performance eligibility,
verification, case cleanup and final resource-disposition fields. Preserve
FAIL, INELIGIBLE, INCOMPLETE and NOT_RUN rows. Verification defaults to SKIPPED.

Write a manifest, append-only command/event log and per-case receipt. Include
artifact/fixture/protocol hashes, exact redacted argv, machine/database topology,
phase times, command and CLI exits, Commit outcome, cache evidence and resources.
Never store resolved secrets. Flush attempt/effect records before cleanup so an
interruption leaves useful evidence. Finalization must not overwrite history.

Record logical and physical Store growth, WAL/overlay/temp bytes and available
phase CPU/memory, including PostgreSQL server work. Use bounded observations at
phase boundaries or a validated lightweight sampler; avoid repeated tree scans.
Post-command WAL absence does not establish peak WAL usage. Unavailable metrics
remain unavailable; required missing evidence prevents qualification. A process
lifetime peak is not a measured phase peak.

Produce per-case comparisons within each machine/backend, with absolute deltas
and ratios. CLI wall time includes process startup, Store open/close and route
costs. Optional in-Sandbox monotonic timing is a separate metric, validated on
both macOS and Linux guests. Missing command timing never becomes zero. Apply
only predeclared performance gates; descriptive ratios alone are not speed PASS.

## Proposed commands

These commands describe the new harness interface, not existing product commands:

```bash
python3 fs-bench-quick/run.py prepare \
  --environment /path/to/environment.json --matrix \
  --cache /path/to/prepared

# Default: one performance sample, no independent verification.
python3 fs-bench-quick/run.py run \
  --environment /path/to/environment.json \
  --cache /path/to/prepared --machine lima --backend postgresql \
  --case C09 --output /path/to/results/run-id

# Explicit qualification selection: measure once, then prove separately.
python3 fs-bench-quick/run.py run \
  --environment /path/to/environment.json \
  --cache /path/to/prepared --machine native --backend sqlite \
  --case C01 --verify --output /path/to/results/another-run-id

python3 fs-bench-quick/report.py --input /path/to/results/run-id

# Finish a campaign exercised through separate single-case invocations.
# A matrix run performs this finalization automatically.
python3 fs-bench-quick/run.py finish \
  --environment /path/to/environment.json --cache /path/to/prepared
```

`run --matrix` schedules the 96 registered selections as separately bounded
attempts. `--case` may select a subset. Consumed inputs and attempted case
identities are not silently replayed when a command is invoked again. A fresh
output name does not authorize unchanged treatment resampling.

## Implementation order and completion

1. Freeze the workload manifest and CLI-only invocation/result contract.
2. Build the minimum shared lifecycle, receipt, prepared-input and cleanup path.
   Resolve the latest `layerfs_v2_0_0` branch and pin its exact source identity.
3. Implement C01 across native SQLite/PostgreSQL, then Docker SQLite/PostgreSQL,
   Lima SQLite/PostgreSQL and Apple Container SQLite/PostgreSQL. Demonstrate the
   relevant clocks, cache protocol and overhead using controlled diagnostics
   before collecting eligible samples. Keep verification opt-in.
4. Repeat that exact eight-configuration loop for C02 through C12. Extend shared
   code only as the current cell requires. Record failures and prerequisites
   honestly; never advance silently past a missing configuration.
5. Generate the report from retained receipts, reuse unaffected evidence with
   exact scope justification, and perform final campaign cleanup. A change to an
   earlier measured mechanism requires only its affected checkpoint at the final
   identity; do not automatically rerun the whole matrix.

For the owner-selected diagnostic campaign, complete when all 96 execution rows
PASS, final cleanup is COMPLETE, verification disposition is explicit, and all
timings remain honestly INELIGIBLE. Preserve any failures and documented changed
checkpoints rather than silently resampling. Do not require new product cache
controls or enable proof by default to satisfy this terminal outcome.

Release qualification, if separately requested, is complete when all 96 rows are
accounted for; the CLI route, setup reuse, cache
validity and real overhead costs are checkable; optional proof behaves as
specified; and required qualification rows have eligible measurements plus
independent proof or an explicitly accepted exclusion. A default diagnostic run
does not close the issue's qualification requirement. Campaign completion also
requires a final cleanup receipt accounting for every owned allocation; retained
uncertainty or failed cleanup remains an explicit incomplete outcome.
