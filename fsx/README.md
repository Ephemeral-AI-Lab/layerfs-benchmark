# fsx — random file reads, writes and truncates checked by fsx itself
> group: filesystem · measures: correctness

## Basic info

| | |
| --- | --- |
| Tool | Portable secfs.test `fsx`, unchanged, commit `edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed`; built separately for macOS and Linux ([tool build](TOOL.md)) |
| Workload version | `fsx-X01-v2-secfs-portable` (X01 v2) |
| Runs on | Four machine routes (native, Docker, Lima, Apple Container) × SQLite and PostgreSQL Stores: eight configurations, one shared public-CLI lifecycle |
| Status | Current. Timings are INELIGIBLE diagnostics; independent proof is SKIPPED |
| Frozen rules | [AGENTS.md](AGENTS.md); exact flags and source/summarizer hashes in [cases.py](src/cases.py) |

## Overview

X01 v2 runs the unchanged portable secfs.test `fsx`, with built-in size and
read-consistency checks, through the public LayerFS CLI. Only ordinary
read/write/truncate work executes; zero-size/past-EOF operation slots remain
skipped and are separately counted. A PASS means the CLI lifecycle succeeded and
fsx completed all 1,000 slots with its intrinsic checks, complete operation
records and at least one effective operation. It is not independent proof of
the committed content and not a cold performance result; cache state remains
diagnostic unless separately demonstrated.

| Case | Workload | Expected result |
| --- | --- | --- |
| X01 | One process, seed 1, 1,000 requested slots, maximum 8 MiB file, maximum 64 KiB operation. Flags `-S 1 -N 1000 -F 8388608 -o 65536 -R -W -v -P <owned-logdir> fsx.data` | fsx exits 0 and reports all 1,000 operations completed; 1,000 records; nonzero effective read/write/truncate count |

No sync option or verification-disabling option is selected. A success banner
without complete operation records or without effective work fails result
parsing.

## Setup

Prerequisites, all in place before measurement (provisioning and tool builds
happen first):

- The pinned `fsx` for each platform, installed as `bin/fsx` beneath that
  machine's `tool_environment.BENCH_TOOL_ROOT` (build steps in [TOOL.md](TOOL.md)).
- Python 3 on each machine's PATH.
- Matching product artifacts and owned database/infrastructure records.

Copy [environments.example.json](environments.example.json) to a local ignored
file (for example `fsx/environments.local.json`), supply the product artifacts
and owned database/infrastructure records, and set each machine's
`tool_environment.BENCH_TOOL_ROOT`.

```bash
python3 fsx/src/run.py prepare --environment fsx/environments.local.json --matrix --cache /owned/fsx-cache
python3 fsx/src/run.py run --environment fsx/environments.local.json --matrix --cache /owned/fsx-cache --output /owned/fsx-results
python3 fsx/src/run.py finish --environment fsx/environments.local.json --cache /owned/fsx-cache
```

`finish` releases campaign-owned infrastructure.

Time limits in the example config: 15 s per case (`performance_budget_s`),
25 s for preparation (`prepare_budget_s`) and 10 s for cleanup
(`cleanup_budget_s`).

Default independent proof is skipped. `--verify` is rejected explicitly because
a separate committed-result oracle has not been implemented. Tool-internal
checks still run. The CLI receives a compact summary; temporary upstream
diagnostic logs are outside the Workspace and are removed after successful
summary generation, or released with the owning Sandbox.

## Past runs

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-06 | `76a32a9a10` (pgr2-six) | Diagnostic terminal: INCOMPLETE. 9 registered rows; execution {'PASS': 9}. Final infrastructure cleanup: INCOMPLETE | [report](../result/2026-11-06/fsx/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md) |
| 2026-11-06 | `ddd1bc83cd` (pg71-six) | Diagnostic terminal: INCOMPLETE. 9 registered rows; execution {'PASS': 9}. Final infrastructure cleanup: INCOMPLETE | [report](../result/2026-11-06/fsx/ddd1bc83cda03d223c9dde6be86b08024db0c5e5/pg71-six/report.md) |
| 2026-11-06 | `b919f50eaf` | Diagnostic terminal: PASS. 8 registered rows; execution {'PASS': 8}. Final infrastructure cleanup: COMPLETE | [report](../result/2026-11-06/fsx/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) |
<!-- runs:end -->

fsx v1 (retired): 6 PASS, 0 FAIL, 2 NOT_RUN; replaced by portable v2 above.
