# fsstress — random concurrent filesystem operations
> group: filesystem · measures: correctness

## Basic info

| | |
| --- | --- |
| Tool | Unchanged [`secfs.test` fsstress at `edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed`](https://github.com/billziss-gh/secfs.test/tree/edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed/fsstress) (portable); workload `fsstress-S01-v2`. Build, binary hashes and image: [TOOL.md](TOOL.md) |
| Runs on | Native macOS, Docker, Lima and Apple Container; SQLite and PostgreSQL Stores (eight rows per case) |
| Status | Active: portable S01 v2. Latest checkpoint is the corrected product `b9ad9edd`. Timings are INELIGIBLE diagnostics. |
| Frozen rules | [AGENTS.md](AGENTS.md): platform semantics, error policy, the narrow Darwin dangling-symlink link exception, execution and cleanup |

## Overview

fsstress runs random file, directory and link operations from two concurrent
processes inside a Workspace, then Commits the result. Native macOS and Linux
execute the same two-process, 512-slots-per-process, seed-1 profile.
[cases.py](src/cases.py) freezes argv, symbolic error policy, per-child
accounting and provenance. A PASS means every slot was accounted for with
nonzero effective work and no unexpected errors; it is not independent
committed-content proof, a cold-cache result or an identical-byte comparison
across platforms.

| Case | Workload | Expected result |
| --- | --- | --- |
| S01 | Two processes × 512 operation slots, seed 1, one loop. Frozen weights: creat 4, mkdir 2, stat 4, rename 2, unlink 2, rmdir 1, link 1, symlink 1, readlink 1, read 2, write 2, truncate 1. `-c` keeps the mutations for Commit. | Each child completes all 512 slots with nonzero successful operations. Listed errno values count as expected errors; any other error, or zero effective work, fails. |

The result distinguishes requested slots, successful operations, no-object or
zero-size skips and expected errors. The parent's exit zero alone does not
prove child completion. Requested read/write lengths are what upstream logs;
the tool does not report transferred bytes. Native uses 16 KiB pages and Linux uses 4 KiB pages, so
the page-derived request ranges differ; these are descriptive diagnostics
rather than identical-byte performance comparisons.

Extra committed-result proof is off by default and explicitly unsupported.
Upstream checks remain active; unknown cache state means INELIGIBLE.

## Setup

Prerequisites: the matching fsstress binary at `$BENCH_TOOL_ROOT/bin/fsstress`
on each ready machine (see [TOOL.md](TOOL.md)), and Python 3.

Configure [environments.example.json](environments.example.json) with the
selected current LayerFS SHA, matched release artifacts, independent PostgreSQL
databases, ready tool roots and exact owned infrastructure. Every LayerFS
operation uses [the shared public-CLI runner](../shared/src/runner.py):

```bash
python3 fsstress/src/run.py prepare --environment /private/fsstress.json \
  --cache /owned/fsstress-cache --case S01 --machine native --backend sqlite
python3 fsstress/src/run.py run --environment /private/fsstress.json \
  --cache /owned/fsstress-cache --case S01 --machine native --backend sqlite \
  --output /retained/fsstress/S01/native/sqlite
```

Complete all eight rows in native/Docker/Lima/Apple Container order, SQLite then
PostgreSQL. Release each known-safe case through the CLI, then finish shared
campaign infrastructure once all selected suites release their users.

Time limits: the default 15-second case budget; the example config also sets
25 s for preparation and 10 s for cleanup. Every test command has an explicit
timeout of at most 120 seconds.

## Past runs

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-06 | `76a32a9a10` (pgr2-six) | Diagnostic terminal: INCOMPLETE. 9 registered rows; execution {'PASS': 2, 'FAIL': 7}. Final infrastructure cleanup: INCOMPLETE | [report](../result/2026-11-06/fsstress/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md) |
| 2026-11-06 | `ddd1bc83cd` (pg71-six) | Diagnostic terminal: INCOMPLETE. 9 registered rows; execution {'PASS': 2, 'FAIL': 7}. Final infrastructure cleanup: INCOMPLETE | [report](../result/2026-11-06/fsstress/ddd1bc83cda03d223c9dde6be86b08024db0c5e5/pg71-six/report.md) |
| 2026-11-06 | `b9ad9edd7e` | Diagnostic terminal: PASS. 8 registered rows; execution {'PASS': 8}. Final infrastructure cleanup: COMPLETE | [report](../result/2026-11-06/fsstress/b9ad9edd7ea3a9314625dee53466aa59a7ea69c7/report.md) |
| 2026-11-06 | `b919f50eaf` | Superseded by the corrected-product checkpoint | [report](../result/2026-11-06/fsstress/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) |
<!-- runs:end -->

fsstress v1 (retired): 6 PASS, 0 FAIL, 2 NOT_RUN; replaced by v2. It was the
Linux-only xfstests profile. The v2 run on the original product `b919f50e`
(2 PASS, 1 FAIL, 5 withdrawn before attempt) was superseded by the corrected
product `b9ad9edd`, which permits Workspace hardlinks to symlink inodes; the
workload and error policy did not change. The failed initial native standalone
error-policy check is also retained. None of these is converted into a current
successful row.
