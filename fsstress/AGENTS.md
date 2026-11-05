# fsstress agent instructions

Follow the repository [AGENTS.md](../AGENTS.md) and [SPEC.md](../SPEC.md).
Use the shared public-CLI lifecycle and the exact [cases.py](src/cases.py) profile.

S01 pins unmodified xfstests `31f7192f90a89a6f808a37c3a3cd30491bd50eba`.
Use two processes, seed 1 (upstream adds the process index), 512 requested
operations per process and one loop. Zero all operation weights first, then use:
creat=4, mkdir=2, stat=4, rename=2, unlink=2, rmdir=1, link=1, symlink=1,
readlink=1, read=2, write=2 and truncate=1. No sync, direct I/O, asynchronous,
allocation or filesystem-specific operation is selected. Keep upstream checks
and error reporting; do not alter source or remove an operation after a failure.

Upstream bounds individual writes at 131,072 bytes and write/truncate extension
at 1 MiB beyond current size. For this finite profile the conservative bounds
are 128 MiB requested write payload, 576 MiB maximum logical file size and
1,028 simultaneously created entries including the parent/worker/probe entries.
These derive from the fixed operation count, not admission limits in LayerFS.

Run native, Docker, Lima, Apple Container; SQLite then PostgreSQL. Linux is the
only supported platform at this pin. Native macOS is NOT_RUN, with its actual
`linux/fs.h` compiler failure retained. Install the unmodified tool at
`$BENCH_TOOL_ROOT/bin/fsstress` and provide Python 3 for summarization.

`-v -V` and per-child `/tmp` logs retain actual operation outcomes without
interleaved records. Require all indices 0–511 from each worker, nonzero effective
work and complete accounting; the upstream parent's exit zero does not establish
child completion. Report no-object/zero-size skips, successful operations and
errno histograms separately. The frozen expected errors are EEXIST for creation/
link operations; EEXIST/EINVAL/ENOTEMPTY for rename; EEXIST/ENOTEMPTY for rmdir;
and EINVAL for readlink. Other errors fail, with compact retained details.

Logs belong to owned Sandbox `/tmp`, data to `stress.data` in the Workspace.
Summarizer execution is included in Exec time. Extra independent committed-result
proof is unimplemented and explicitly rejected; default proof is SKIPPED.
Unknown caches remain INELIGIBLE. Do not warm up, retry or resample unchanged
treatments. Use the 15-second case budget and explicit <=120-second test limits.
Release resources through their recorded owners and publish only the report.
