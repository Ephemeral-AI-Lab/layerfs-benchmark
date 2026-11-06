# fio — buffered sequential and random file I/O
> group: filesystem · measures: speed

## Basic info

| Item | Value |
| --- | --- |
| Tool | Unchanged upstream fio 3.40, commit `ff930c4653ae3952d6b09ab3ec89671aeabf2cbe`; build and binary hashes in [TOOL.md](TOOL.md) |
| Runs on | Four LayerFS machines (native, Docker, Lima, Apple Container) and two Store backends (SQLite, PostgreSQL): 4 cases, 32 rows |
| Status | Implemented diagnostic workload; no cold-cache qualification; timings are INELIGIBLE diagnostics |
| Frozen rules | [AGENTS.md](AGENTS.md): workload and cache limits; exact flags in [src/cases.py](src/cases.py) |
| Lifecycle | [shared/src/runner.py](../shared/src/runner.py): preparation, CLI execution, deadlines and cleanup; this suite has no separate lifecycle |

## Overview

Four small, finite buffered-I/O cases run fio in a LayerFS Workspace through
the public CLI. Each case is one fixed byte-count pass: one job, the `sync`
engine, depth 1, seed 1. A PASS means the CLI lifecycle succeeded and fio's
result was accepted. It is not independent committed-content proof or cold
performance qualification.

| Case | Workload | Expected result |
| --- | --- | --- |
| F01 | Sequential write, 64 MiB in 1 MiB blocks, empty starting view | One job, tool error 0, exactly 67,108,864 bytes in 64 writes, no short/drop I/O, no read bytes |
| F02 | Sequential read, 64 MiB in 1 MiB blocks, of committed fio data | One job, tool error 0, exactly 67,108,864 bytes in 64 reads, no short/drop I/O, no write bytes |
| F03 | Random write, 8 MiB in 4 KiB blocks, empty starting view | One job, tool error 0, exactly 8,388,608 bytes in 2,048 writes, no short/drop I/O, no read bytes |
| F04 | Random read, 8 MiB in 4 KiB blocks, of committed fio data | One job, tool error 0, exactly 8,388,608 bytes in 2,048 reads, no short/drop I/O, no write bytes |

`create_fsync=0` is deliberate: upstream normally syncs a newly created data file.
`fallocate=none`, `create_on_open=1`, `end_fsync=0` and `fsync_on_close=0` avoid
unrequested preparation/sync work. Buffered I/O and `invalidate=0` make no cold
claim. The repeated `0x5a` data are nonzero and highly compressible.

## Setup

Prerequisites:

- The pinned fio binary for each machine ([TOOL.md](TOOL.md)). Place each
  matching binary in a ready machine's tool directory once, outside any LayerFS
  Store. Set `machines.<machine>.tool_environment.BENCH_TOOL_ROOT` to that
  directory; the exact workload references `$BENCH_TOOL_ROOT/fio` and does not
  embed machine-specific paths in its provenance.
- Resolve the current product source and build matched release artifacts first.
- PostgreSQL databases are independent, pre-provisioned inputs; the shared
  runner initializes their LayerFS schema using public CLI calls.

Config: use [environments.example.json](environments.example.json) as a schema,
replacing placeholders and recording exact owned infrastructure.

Prepare and run one row:

```bash
python3 fio/src/run.py prepare --environment /private/fio.json \
  --cache /private/fio-prepared --case F01 --machine native --backend sqlite
python3 fio/src/run.py run --environment /private/fio.json \
  --cache /private/fio-prepared --case F01 --machine native --backend sqlite \
  --output /retained/fio/F01/native/sqlite
```

Prepare and execute the next row in case → machine → database order, completing
all eight rows before advancing. Verification is skipped unless `--verify` is
selected before that one-time sample. At shared campaign finish, release the
server/data and other exact owned resources once. Do not tear down common
machines between suites.

```bash
python3 fio/src/run.py finish --environment /private/fio.json --cache /private/fio-prepared
python3 shared/src/report.py --suite fio --input /private/fio-prepared \
  --cleanup /retained/final-cleanup.json \
  --output result/YYYY-MM-DD/fio/FULL_LAYERFS_SHA/report.md
```

Time limits: 15 seconds per performance case and 25 seconds for setup
([AGENTS.md](AGENTS.md)). With `--verify`, the proof targets at most one second,
with a separate total budget below ten seconds.

Run focused harness checks with an explicit wall bound:

```bash
python3 -c 'import subprocess; subprocess.run(["python3", "-m", "unittest", "discover", "-s", "fio/tests", "-v"], check=True, timeout=30)'
```

## Past runs

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-06 | `76a32a9a10` (pgr2-six) | Diagnostic terminal: INCOMPLETE. 36 registered rows; execution {'PASS': 36}. Final infrastructure cleanup: INCOMPLETE | [report](../result/2026-11-06/fio/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md) |
| 2026-11-06 | `ddd1bc83cd` (pg71-six) | Diagnostic terminal: INCOMPLETE. 36 registered rows; execution {'PASS': 36}. Final infrastructure cleanup: INCOMPLETE | [report](../result/2026-11-06/fio/ddd1bc83cda03d223c9dde6be86b08024db0c5e5/pg71-six/report.md) |
| 2026-11-06 | `b919f50eaf` | Diagnostic terminal: PASS. 32 registered rows; execution {'PASS': 32}. Final infrastructure cleanup: COMPLETE | [report](../result/2026-11-06/fio/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) |
<!-- runs:end -->
