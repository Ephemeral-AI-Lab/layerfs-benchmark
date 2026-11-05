# fsx agent instructions

Follow the repository [AGENTS.md](../AGENTS.md) and [SPEC.md](../SPEC.md).
Use the shared public-CLI lifecycle; the workload is pinned in [cases.py](src/cases.py).

X01 uses unmodified xfstests commit `31f7192f90a89a6f808a37c3a3cd30491bd50eba`,
one process, seed 1, 1,000 requested operation slots, 8 MiB maximum file size,
and 64 KiB maximum operation size. Preserve all fsx size/read consistency checks.
Mapped reads/writes become ordinary reads/writes. Explicitly disable atomic,
dontcache, preallocation, hole/range, reflink/dedupe/copy/exchange operations.
Upstream still selects disabled slots and records them as skipped: report both
1,000 completed slots and the actual READ/WRITE/TRUNCATE counts. Never call all
1,000 slots effective I/O.

Freeze `TOOL_ARGV`, summarizer and body hashes before execution. Run native,
Docker, Lima and Apple Container in that order, SQLite then PostgreSQL. This
pinned upstream is Linux-only: native macOS rows are NOT_RUN, with the missing
Linux/XFS development headers recorded. Do not port or patch it, or substitute
another fsx implementation.

Install the pinned binary at `$BENCH_TOOL_ROOT/bin/fsx`; Python 3 is required
for the compact log summarizer. Tool diagnostic files belong to a fresh owned
Sandbox `/tmp` directory; `fsx.data` is the intended Workspace mutation. Summary
generation is declared Exec work, and its cost stays in Exec wall time. Original
fsx checks run regardless of extra verification selection. Independent committed
result proof is unavailable and `--verify` fails explicitly; default is SKIPPED.

No workload warm-up, automatic retry or unchanged resampling. Unknown cache
conditions remain INELIGIBLE. Preserve finite limits and the default 15-second
case deadline. Every test command has an explicit timeout no greater than 120
seconds. Release case resources and campaign-owned infrastructure through their
recorded owners; preserve uncertain state. Publish only the suite report.
