# fsx agent instructions

Follow the repository [AGENTS.md](../AGENTS.md) and [SPEC.md](../SPEC.md).
Use the shared public-CLI lifecycle; the workload is pinned in [cases.py](src/cases.py).

Current X01 v2 uses unmodified secfs.test commit `edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed`,
one process, seed 1, 1,000 requested operation slots, 8 MiB maximum file size,
and 64 KiB maximum operation size. Preserve all fsx size/read consistency checks.
Use exactly `-S 1 -N 1000 -F 8388608 -o 65536 -R -W -v -P <owned-logdir> fsx.data`.
This upstream uses `-F` for file size; `-l` is a log path. Do not use `-n` or `-m`:
the latter falls through to disabling size checks in the pinned source. No sync,
cache-switch, mapped I/O, interactive or duration option is selected. Its default
four-byte data elements remain enabled. Ordinary read/write/truncate operations
run; zero-length/past-EOF skips are real skipped slots, not effective I/O.

Freeze `TOOL_ARGV`, summarizer and body hashes before execution. Run native,
Docker, Lima and Apple Container in that order, SQLite then PostgreSQL. This
pinned upstream builds unchanged on macOS and Linux. All eight configurations
use the same source and flags. Keep native and Linux binary hashes distinct.
Never patch the upstream source to fit a platform.

Install the pinned binary at `$BENCH_TOOL_ROOT/bin/fsx`; Python 3 is required
for the compact log summarizer. Tool diagnostic files belong to a fresh owned
Sandbox `/tmp` directory; `fsx.data` is the intended Workspace mutation. Summary
generation is declared Exec work, and its cost stays in Exec wall time. Original
fsx checks run regardless of extra verification selection. Independent committed
result proof is unavailable and `--verify` fails explicitly; default is SKIPPED.

The v1 xfstests profile at `31f7192f90a89a6f808a37c3a3cd30491bd50eba` was Linux-only.
Its original receipts, six Linux passes and two native NOT_RUN rows remain
unchanged. The owner's portable-upstream follow-up prospectively selects v2;
do not relabel or overwrite v1 evidence or compare its operation counts as the
same treatment. Re-execution is authorized only for the affected revised profile.

No workload warm-up, automatic retry or unchanged resampling. Unknown cache
conditions remain INELIGIBLE. Preserve finite limits and the default 15-second
case deadline. Every test command has an explicit timeout no greater than 120
seconds. Release case resources and campaign-owned infrastructure through their
recorded owners; preserve uncertain state. Publish only the suite report.
