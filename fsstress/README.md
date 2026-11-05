# fsstress

S01 exercises metadata and bounded file mutations using the unchanged upstream
[`fsstress` at `31f7192f90a89a6f808a37c3a3cd30491bd50eba`](https://kernel.googlesource.com/pub/scm/fs/xfs/xfstests-dev/+/31f7192f90a89a6f808a37c3a3cd30491bd50eba/ltp/fsstress.c).
Its exact two-worker, 512-operations-per-worker, seed-1 profile and error policy
are frozen in [cases.py](src/cases.py) and [AGENTS.md](AGENTS.md).

All LayerFS calls use the shared public-CLI lifecycle. Install the Linux binary
at `$BENCH_TOOL_ROOT/bin/fsstress` and provide Python 3. Set the machine-specific
tool root in [the environment example](environments.example.json), supply pinned
product artifacts and exact owned PostgreSQL/infrastructure records, then run:

```bash
python3 fsstress/src/run.py prepare --environment fsstress/environments.local.json --matrix --cache /owned/fsstress-cache
python3 fsstress/src/run.py run --environment fsstress/environments.local.json --matrix --cache /owned/fsstress-cache --output /owned/fsstress-results
```

Native macOS rows are NOT_RUN because this upstream requires Linux headers and
interfaces. The three Linux routes use the same binary/profile. Build it with
the unchanged upstream commands and packages documented in [fsx](../fsx/README.md).
The observed Debian 12/aarch64 build links only glibc, with no additional runtime
library package to distribute.

The compact result reports actual successful operations, requested slots,
no-object/zero-size skips and expected errno outcomes. Each worker must report
every operation index, so the upstream parent returning zero cannot conceal a
dead child. Unexpected errors and zero effective work fail. Logging and summary
costs stay in Exec wall time; diagnostic files live in owned Sandbox `/tmp`,
and `stress.data` is the Workspace mutation captured by LayerFS Commit.

Extra independent proof is off by default; `--verify` is explicitly unsupported.
Upstream operation checks/reporting remain enabled. Cache validity and cleanup
have separate verdicts. Finish the shared campaign's owned machines, server/data,
temporary homes and inputs once after all suites; do not delete uncertain state.
