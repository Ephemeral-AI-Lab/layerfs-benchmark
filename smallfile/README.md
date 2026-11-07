# smallfile — two-worker small-file create, read, stat, rename and delete
> group: filesystem · measures: speed

## Basic info

| Item | Value |
| --- | --- |
| Tool | [distributed-system-analysis/smallfile](https://github.com/distributed-system-analysis/smallfile/tree/aa2519de5bf0b3b383db2c31eacbf8ac4328e19c), unmodified, pinned at `aa2519de5bf0b3b383db2c31eacbf8ac4328e19c` |
| Runs on | Machines: native, Docker, Lima, Apple Container. Store backends: SQLite (Disposable/WAL/OFF) and PostgreSQL |
| Status | Current. Five cases (L01–L05), 40 registered rows (case × machine × backend); workload `two-worker-256x4k-as-host-v1` |
| Frozen rules | [AGENTS.md](AGENTS.md); exact commands and provenance in [src/cases.py](src/cases.py) |

## Overview

Five two-worker file workloads: create, read, stat, rename and delete. Every
worker processes 256 files of 4 KiB, so each case handles 512 files. A PASS
means the public CLI lifecycle completed and the tool's own result was accepted:
both workers finished all their files with status ok, and read checks matched.
It is not independent committed-content proof and not a cold performance
result: unknown cache state is INELIGIBLE, even if execution and internal checks
pass.

| Case | Workload | Expected result |
| --- | --- | --- |
| L01 | Create 512 files; starts from an empty view | PASS: two workers, 256 files and 256 records each, 100% of files processed |
| L02 | Read 512 files with read verification on | PASS: two workers, 256 files and 256 records each, no read mismatch |
| L03 | Stat 512 files | PASS: two workers, 256 files each, 100% of files processed |
| L04 | Rename 512 files | PASS: two workers, 256 files each, 100% of files processed |
| L05 | Delete 512 files | PASS: two workers, 256 files each, 100% of files processed |

L02–L05 use committed inputs created by the same pinned tool during destination
preparation. Missing workers, partial work or a read mismatch is FAIL.

## Setup

Prerequisites:

- Copy the pinned tool's unmodified Python tree once to
  `BENCH_TOOL_ROOT/smallfile`, and provide Python 3. Extra xattr/fallocate
  libraries are unnecessary for these selected operations.
- The suite uses an explicit POSIX fork context on macOS and Linux, upstream
  `--as-host bench`, fixed sizes/distribution, full completion and enabled read
  verification.
- The hidden hostname flag prevents changes in Sandbox hostname from breaking
  prepared names. A Workspace-local `TMPDIR` retains seed files across the setup
  Commit and bounds cleanup to campaign-owned state. Tool code stays outside the
  Store.
- Payload `--fsync N` does not remove upstream control-file synchronization:
  `sync_files.write_sync_file` and `write_pickle` call fsync for their
  gate/result files. Preserve those intrinsic calls and report them; this
  profile does not claim zero fsync requests. LayerFS remains Disposable/OFF.

Config file: start from [environments.example.json](environments.example.json)
and add the campaign's product artifacts, home and database ownership.

Run command: see `python3 smallfile/src/run.py --help`. Extra committed-result
verification is optional and off by default. Tool-internal read checks are
always enabled.

Time limit: 15 s for the complete performance invocation of a case; the
optional independent proof stays below 10 s. Upstream includes a 2–3 s
synchronization delay; retain it, and report its file rate separately from
complete CLI time.

Every case and the final infrastructure release must complete or retain an
exact reason/custody record. See [AGENTS.md](AGENTS.md) for workload and
reporting rules.

## Past runs

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-06 | `76a32a9a10` (pgr2-six) | Diagnostic terminal: INCOMPLETE. 45 registered rows; execution {'PASS': 45}. Final infrastructure cleanup: INCOMPLETE | [report](../result/2026-11-06/smallfile/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md) |
| 2026-11-06 | `ddd1bc83cd` (pg71-six) | Diagnostic terminal: INCOMPLETE. 45 registered rows; execution {'PASS': 45}. Final infrastructure cleanup: INCOMPLETE | [report](../result/2026-11-06/smallfile/ddd1bc83cda03d223c9dde6be86b08024db0c5e5/pg71-six/report.md) |
| 2026-11-06 | `b919f50eaf` | Diagnostic terminal: PASS. 40 registered rows; execution {'PASS': 40}. Final infrastructure cleanup: COMPLETE | [report](../result/2026-11-06/smallfile/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) |
<!-- runs:end -->
