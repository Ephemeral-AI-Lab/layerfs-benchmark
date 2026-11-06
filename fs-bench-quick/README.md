# fs-bench-quick — CLI case times for eighteen small file workloads
> group: filesystem · measures: speed

## Basic info

| | |
| --- | --- |
| Tool | In-house: Python standard library over the shared runner in [../shared/src/](../shared/src/); every LayerFS step uses the public CLI |
| Product | LayerFS 2.0 (`layerfs_v2_0_0`), pinned per campaign |
| Machines | macOS host: native, Docker, Lima, Apple Container |
| Store backends | SQLite, then PostgreSQL, on each machine |
| Status | Current general guide. Eighteen cells are implemented (C13–C18 added for layerfs-project#62); the matrix has 144 rows plus any declared co-located PostgreSQL arm. |
| Frozen rules | [AGENTS.md](AGENTS.md) (workloads, measurement, cleanup); root [CLI and cache rules](../AGENTS.md) |

Agents must read the root [CLI and cache rules](../AGENTS.md) and the
[suite instructions](AGENTS.md) before preparing or running selections.

The suite root holds documentation and the configuration example. Python
implementation lives in `src/`, and focused checks live in `tests/`.
[cases.py](src/cases.py) pins the exact bodies and provenance.

## Overview

A small CLI-only filesystem diagnostic suite for LayerFS 2.0. Each case creates
a Sandbox, mounts a Workspace, runs one Bash workload through Exec, makes a
LayerFS Commit, unmounts and cleans up, timing each call. A PASS row means the
CLI calls succeeded and the workload's own exit code was 0. It does not prove
content correctness (UNVERIFIED unless `run --verify` is selected) or qualified
performance: unknown cache state makes timings INELIGIBLE diagnostics.

Implementation advanced one cell at a time through native, Docker, Lima and
Apple Container, with SQLite then PostgreSQL on each machine. The
[completed diagnostic report](../result/2026-11-06/fs-bench-quick/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md)
reached 96 execution PASS outcomes and final runtime cleanup COMPLETE. All
timings are INELIGIBLE diagnostics and independent verification was SKIPPED, as
requested. This terminal outcome establishes execution and cleanup coverage;
content correctness and performance qualification remain unproven.

| Case | Workload | Starting view | Expected result |
| --- | --- | --- | --- |
| C01 | Create 1,000 numbered files `f1`–`f1000` | Empty | Exit 0; with `--verify`, exactly those files, each holding its number |
| C02 | C01, then `stat` each file | Empty | As C01 |
| C03 | C01, then `rm f*` | Empty | Exit 0; with `--verify`, an empty root |
| C04 | Create 110 directories (10×10) holding 1,000 empty files | Empty | Exit 0; with `--verify`, exactly that tree of empty regular files |
| C05 | C04, then `find . -type f \| wc -l` | Empty | As C04 |
| C06 | Write 64 MiB of zeros to `big` with `dd` | Empty | Exit 0; with `--verify`, `big` only, 67,108,864 zero bytes |
| C07 | C06, then `cp big big2` | Empty | Exit 0; with `--verify`, `big` and `big2`, both 64 MiB of zeros |
| C08 | C06, then `cat big > /dev/null` | Empty | As C06 |
| C09 | Read the committed 64 MiB `big` | Committed base | As C06 |
| C10 | Copy the committed `big` to `big2` | Committed base | As C07 |
| C11 | Overwrite `big` with 64 MiB of zeros (`dd conv=notrunc`) | Committed base | As C06 |
| C12 | `git init`, create 100 numbered files, `git add -A`, `git commit` | Empty | Exit 0; with `--verify`, the 100 files, one Git commit `init` tracking them, clean status |
| C13 | `echo 1 > a`, Commit; then `echo 2 > b`, second Commit on the same Workspace | Empty | Exit 0; with `--verify`, `a` and `b` only |
| C14 | File-count sweep, 0 files (`true`) | Empty | Exit 0; with `--verify`, an empty root |
| C15 | File-count sweep, 100 numbered files | Empty | As C01 for 100 files |
| C16 | File-count sweep, 10,000 numbered files; declared 25 s budget | Empty | As C01 for 10,000 files |
| C17 | `cat rand > /dev/null` of a committed 64 MiB non-repeating file | Committed base | Exit 0; with `--verify`, `rand` only, with the pinned SHA-256 |
| C18 | `stat f{1..1000}` over 1,000 committed numbered files | Committed base | As C01 |

C12's Git commit belongs to the workload; the LayerFS Commit is a separate call.
C01 is the sweep's 1,000-file point. C17's base is AES-128-CTR keystream with a
pinned key, identical on every machine and not deduplicable, unlike C09's zeros.
The PostgreSQL route arms, per-phase server counts and round-trip calibration
are described in [AGENTS.md](AGENTS.md#postgresql-route-arms-observation-and-calibration).

Reports name the full run metric **End-to-end case time**, including Sandbox
creation, mount, Exec, LayerFS Commit, unmount and case cleanup. Preparation and
initial Python startup/configuration checks are excluded. CSV reports expose it
as `end_to_end_case_ns`; raw receipts retain their original field names.

## Setup

### Prerequisites

Use a clean, pinned `layerfs_v2_0_0` source snapshot and matching release CLI,
daemon and Linux bundle. Build with PostgreSQL support. Install the bundle under
the campaign's `XDG_CACHE_HOME` using the product's `tools/linux_bundle.py` and
registered worktree resources. Prepare the native daemon setting, Docker worker
and guest machines through the public CLI before registering them ready.

PostgreSQL needs a dedicated pinned server, an empty database per selected row,
and a password environment reference. The CLI attaches the database and creates
the LayerFS schema. The harness performs no direct SQL on LayerFS tables. Declare
the actual data-disposal resource; disconnecting does not delete database data.

### Config file

Copy [the configuration example](environments.example.json) to a private local
path and replace every artifact placeholder. Give the campaign a unique lowercase
ID, private LayerFS home, empty source directory and owned cache directory. Machine
names refer to actual LayerFS records in that home. Declare exact infrastructure
release commands in dependency order; never select resources by a guessed prefix.

### One selection

These commands operate a single prepared input and a fresh output directory:

```bash
python3 fs-bench-quick/src/run.py prepare \
  --environment /private/environment.json --cache /private/prepared \
  --case C01 --machine native --backend sqlite

python3 fs-bench-quick/src/run.py run \
  --environment /private/environment.json --cache /private/prepared \
  --case C01 --machine native --backend sqlite \
  --output /retained/results/C01/native/sqlite

python3 fs-bench-quick/src/report.py --input /retained/results
```

Verification is off by default. Select `run --verify` prospectively to add one
independent committed-result proof, after measurement, with a separate budget
strictly under 10 seconds. Otherwise correctness remains UNVERIFIED. CLI success
and the workload's own exit code are always checked.

Each prepared input is consumed once. Attempted operations and failed releases
are never automatically replayed. Missing infrastructure produces NOT_RUN.
Unknown cache conditions produce INELIGIBLE, not speed PASS. The current cache
assessment deliberately cannot certify coldness from a configuration flag.

### Time limits

[AGENTS.md](AGENTS.md) sets the default case invocation budget at 15 seconds;
prospectively declared exceptions may reach 25 seconds. The configuration
example declares `prepare_budget_s` 25, `performance_budget_s` 15 and
`cleanup_budget_s` 10. The optional verification proof has its own budget
strictly under 10 seconds.

### Ordered matrix and finish

The matrix order is C01-C18 (or alternating arms per cell, when configured), then native/Docker/Lima/Apple Container within each
cell, then SQLite/PostgreSQL within each machine. `--matrix` selects that order.
Each cell has eight outcomes before the next cell begins. Missing prerequisites
remain registered NOT_RUN and unsuccessful attempts retain their dispositions.

Close case resources promptly while retaining reusable campaign infrastructure.
After separate single-case invocations, finish explicitly:

```bash
python3 fs-bench-quick/src/run.py finish \
  --environment /private/environment.json --cache /private/prepared
```

A matrix execution finalizes its infrastructure automatically. Failures preserve
uncertain state and its containing resources. Inspect `cleanup.json` and the
ownership ledger: cleanup FAIL/INCOMPLETE prevents overall success. Retain the
ledger, campaign manifest and raw receipts before removing temporary caches.

New attempts retain the exact runtime harness source bytes and hashes with their
receipts. The completed campaign predates source-byte retention and preserves
its per-row harness hashes, exact CLI commands and workload provenance; the
report describes that limitation. Reports suppress comparisons for ineligible
or mismatched pairs.

### Docker subset regression gate

[gate.py](src/gate.py) (layerfs-project#98) compares a control and a treatment
build on Docker only: C01, C04, C09, C13, C14, C16, C17 and C18 on SQLite,
PostgreSQL over the published port and co-located PostgreSQL, in two paired
rounds (96 rows) under the regression-screen exception. Each identity gets a
fresh home, XDG cache and Docker worker per gate. `setup` creates them and the
row databases, `next` prepares and runs exactly one row through `run.py`,
`verdict` writes the paired-delta summary (median paired delta, pairs slower,
flag; 5 ms floor) and `finish` releases the gate's workers and databases. Its
docstring has the exact commands.

### Publishing

Publish only the report using the [result directory convention](../result/README.md).
Raw receipts, logs and machine-readable working output stay local under this
suite's ignored `results/` directory.

### Focused checks

The checks exercise oracles, timing bounds, result parsing and resource custody;
they do not substitute for real machine execution. Invoke them with an explicit
wall timeout no greater than 120 seconds. The product build is separate.

```bash
python3 -c 'import subprocess,sys; sys.exit(subprocess.run([sys.executable,"-m","unittest","discover","-s","fs-bench-quick/tests"],timeout=30).returncode)'
```

## Past runs

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-06 | `b919f50eaf` | 96/96 CLI execution checks passed. Case and final runtime cleanup: COMPLETE | [report](../result/2026-11-06/fs-bench-quick/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) |
<!-- runs:end -->
