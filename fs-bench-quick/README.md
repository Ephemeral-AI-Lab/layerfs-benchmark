# fs-bench-quick

> Status: Current general guide.

Agents must read the repository-root [CLI and cache rules](../AGENTS.md) and
the [suite instructions](AGENTS.md) before preparing or running selections.

A small CLI-only filesystem diagnostic suite for LayerFS 2.0. Implementation
advances one cell at a time through native, Docker, Lima and Apple Container,
with SQLite then PostgreSQL on each machine. All twelve cells are implemented;
the complete matrix has 96 rows. See [the specification](SPEC.md) for measurement
and cleanup requirements.

The [completed diagnostic campaign](records/quick-20261105T185054Z.md) reached
96 execution PASS outcomes and final runtime cleanup COMPLETE. All timings are
INELIGIBLE diagnostics and independent verification was SKIPPED, as requested.
This terminal outcome establishes execution and cleanup coverage; content
correctness and performance qualification remain unproven.

The [published dataset](../result/2026-11-06/fs-bench-quick/b919f50eaf9cce79671f8501a580279d23cc5f3c/quick-20261105T185054Z/README.md)
contains all96 original receipts, the CLI ledger, reports and CSV/JSON. Follow the
[result directory convention](../result/README.md) for future publications;
working output under this suite's `results/` remains ignored.

## Preparation

Use a clean, pinned `layerfs_v2_0_0` source snapshot and matching release CLI,
daemon and Linux bundle. Build with PostgreSQL support. Install the bundle under
the campaign's `XDG_CACHE_HOME` using the product's `tools/linux_bundle.py` and
registered worktree resources. Prepare the native daemon setting, Docker worker
and guest machines through the public CLI before registering them ready.

Copy [the configuration example](environments.example.json) to a private local
path and replace every artifact placeholder. Give the campaign a unique lowercase
ID, private LayerFS home, empty source directory and owned cache directory. Machine
names refer to actual LayerFS records in that home. Declare exact infrastructure
release commands in dependency order; never select resources by a guessed prefix.

PostgreSQL needs a dedicated pinned server, an empty database per selected row,
and a password environment reference. The CLI attaches the database and creates
the LayerFS schema. The harness performs no direct SQL on LayerFS tables. Declare
the actual data-disposal resource; disconnecting does not delete database data.

## One selection

These commands operate a single prepared input and a fresh output directory:

```bash
python3 fs-bench-quick/run.py prepare \
  --environment /private/environment.json --cache /private/prepared \
  --case C01 --machine native --backend sqlite

python3 fs-bench-quick/run.py run \
  --environment /private/environment.json --cache /private/prepared \
  --case C01 --machine native --backend sqlite \
  --output /retained/results/C01/native/sqlite

python3 fs-bench-quick/report.py --input /retained/results
```

Verification is off by default. Select `run --verify` prospectively to add one
independent committed-result proof, after measurement, with a separate budget
strictly under 10 seconds. Otherwise correctness remains UNVERIFIED. CLI success
and the workload's own exit code are always checked.

Each prepared input is consumed once. Attempted operations and failed releases
are never automatically replayed. Missing infrastructure produces NOT_RUN.
Unknown cache conditions produce INELIGIBLE, not speed PASS. The current cache
assessment deliberately cannot certify coldness from a configuration flag.

## Ordered matrix and finish

The matrix order is C01-C12, then native/Docker/Lima/Apple Container within each
cell, then SQLite/PostgreSQL within each machine. `--matrix` selects that order.
Each cell has eight outcomes before the next cell begins. Missing prerequisites
remain registered NOT_RUN and unsuccessful attempts retain their dispositions.

Close case resources promptly while retaining reusable campaign infrastructure.
After separate single-case invocations, finish explicitly:

```bash
python3 fs-bench-quick/run.py finish \
  --environment /private/environment.json --cache /private/prepared
```

A matrix execution finalizes its infrastructure automatically. Failures preserve
uncertain state and its containing resources. Inspect `cleanup.json` and the
ownership ledger: cleanup FAIL/INCOMPLETE prevents overall success. Retain the
ledger, campaign manifest and raw receipts before removing temporary caches.

New attempts retain the exact runtime harness source bytes and hashes with their
receipts. The completed campaign predates source-byte retention and preserves
its per-row harness hashes, exact CLI commands and workload provenance; its
record describes that limitation. Reports suppress comparisons for ineligible
or mismatched pairs.

Reports name the full run metric **End-to-end case time**, including Sandbox
creation, mount, Exec, LayerFS Commit, unmount and case cleanup. Preparation and
initial Python startup/configuration checks are excluded. CSV reports expose it
as `end_to_end_case_ns`; raw receipts retain their original field names.

## Focused checks

The checks exercise oracles, timing bounds, result parsing and resource custody;
they do not substitute for real machine execution. Invoke them with an explicit
wall timeout no greater than 120 seconds. The product build is separate.

```bash
python3 -c 'import subprocess,sys; sys.exit(subprocess.run([sys.executable,"-m","unittest","discover","-s","fs-bench-quick/tests"],timeout=30).returncode)'
```
