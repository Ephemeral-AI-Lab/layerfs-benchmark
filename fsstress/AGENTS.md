# fsstress agent instructions

Follow root [AGENTS.md](../AGENTS.md) and [SPEC.md](../SPEC.md). Use the shared
public-CLI lifecycle and exact [cases.py](src/cases.py), version
`fsstress-S01-v2`. Prior v1 xfstests/Linux-only results remain historical.

## Portable S01 v2

Use unchanged [secfs.test](https://github.com/billziss-gh/secfs.test/tree/edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed),
commit `edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed`, `fsstress/fsstress.c`.
Both native macOS and Linux use this source and the same argv: two processes,
seed 1 (upstream adds process index), 512 slots per process, one loop, `-z`,
`-v` and `-c`. `-c` disables upstream final cleanup and retains mutations for
LayerFS Commit. This revision supports neither `-V` nor `-o`.

Freeze weights: creat=4, mkdir=2, stat=4, rename=2, unlink=2, rmdir=1, link=1,
symlink=1, readlink=1, read=2, write=2, truncate=1. No sync, direct, asynchronous,
preallocation or filesystem-specific operation is selected. Preserve upstream
checks and reporting. Never patch third-party source or drop a failed operation.

The source derives read/write lengths from `getpagesize()*32` and extends file
offsets by at most 1 MiB before a write/truncate. Registered arm64 environments
have these conservative bounds, rather than identical byte workloads:

| Platform | Page bytes | Maximum request bytes | Total requested-write bound | Per-file logical-size bound |
| --- | ---: | ---: | ---: | ---: |
| macOS | 16,384 | 524,288 | 536,870,912 | 805,306,368 |
| Linux | 4,096 | 131,072 | 134,217,728 | 603,979,776 |

The entry bound is 1,028, including root/worker/probe entries. These are derived
workload bounds, not LayerFS limits. libc `random()` sequences and filesystem
responses can also differ across platforms. Identical seeds and slots do not
claim identical operations or byte work. Report actual selected operations and
upstream logged request lengths; the tool does not report transferred bytes.

## Strict accounting and expected errors

Upstream line-buffers its verbose stdout. Capture it in one owned Sandbox `/tmp`
log and parse every record strictly. Require indices 0–511 once for each worker,
nonzero successful work from each, complete accounting and no unexpected errors.
The parent's exit zero cannot establish child completion. Reject malformed or
interleaved lines rather than reconstructing them. Summarization remains inside
Exec. Data live at `stress.data`; logs remain outside committed content.

Normalize runtime errno numbers through Python's local `errno.errorcode`:
EEXIST for create/link operations; EEXIST/EINVAL/ENOTEMPTY for rename;
EEXIST/ENOTEMPTY for rmdir; EINVAL for readlink. ENOTEMPTY is 66 on macOS and 39
on Linux, so Linux numbers must not be reused on native.

One prospective v2 exception is narrow: **Darwin `link`, ENOENT, logged source
basename exactly `l[0-9a-f]+`**. Upstream's `l` prefix denotes its symlink list;
its random target may dangle. Apple's [link(2) contract](https://raw.githubusercontent.com/apple-oss-distributions/xnu/main/bsd/man/man2/link.2)
follows a final source symlink and documents ENOENT for a dangling source.
Ordinary file links, Linux links and other operations retain strict ENOENT
failure. The first standalone native result under the pre-exception policy is
retained as FAIL; it is not a LayerFS campaign failure or a relabeled pass.

## Execution and cleanup

Run native, Docker, Lima, Apple Container; SQLite then PostgreSQL. Install the
matching tool at `$BENCH_TOOL_ROOT/bin/fsstress`; provide Python 3. Use the default
15-second case budget and explicit test timeouts at most 120 seconds. Extra
independent proof is unavailable and rejected; default verification is SKIPPED.
Unknown caches remain INELIGIBLE diagnostics. No warm-up, retry or unchanged
resampling. Release known-safe state through recorded owners, preserve uncertain
state and containing resources, and publish only the compact final report.

## Corrected product checkpoint

At reference `b919f50eaf9cce79671f8501a580279d23cc5f3c`, v2 retained two
native PASS rows, one Docker/SQLite FAIL and five selections withdrawn before
attempt. Six symlink hard-link operations returned EPERM because that product
explicitly refused them. Never reclassify those failures or add an EPERM allowance.

The owner-approved capability fix is clean derived commit
`b9ad9edd7ea3a9314625dee53466aa59a7ea69c7`. Use matched CLI/daemon/Linux bundle
from that source for a separate complete eight-row checkpoint, after scoped
product proof. Keep the v2 workload/error policy unchanged and record the new
product identity explicitly. Preserve older profiles separately; Docker ratios
use only rows from the same product checkpoint. Default extra benchmark proof
remains SKIPPED and every timing remains INELIGIBLE.
