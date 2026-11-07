# fs-storage-dsh — Store bytes for a real repository history replayed through Workspace Commits
> group: filesystem · measures: storage

## Basic info

| Item | Value |
| --- | --- |
| Workload | `fs-storage-dsh-v1`: the 157-checkpoint DeepSeek-harness history (every 100th of 15,632 Commits plus the last; BSD-3-Clause or MIT by checkpoint), replayed at stride 10 (D10, 17 states) and stride 3 (D03, 53 states) |
| Runs on | Docker only, SQLite then PostgreSQL: 2 cases, 4 rows, one fresh Store per row |
| Measures | Store bytes (floor, final, net), per-Commit `new_stored` (all new pack bytes) and its `new_metadata` subset, bytes outside Commit packs (net − Σ `new_stored`), and ratios against whole-file unique, Σ `tar \| zstd -3`, Git pack + idx and an approximate CDC oracle. No timing claims |
| Frozen rules | [AGENTS.md](AGENTS.md); selections, pins and commands in [src/cases.py](src/cases.py); image in [TOOL.md](TOOL.md) |
| Driver | [shared/src/storage.py](../shared/src/storage.py) on [shared/src/runner.py](../shared/src/runner.py) custody ([shared/STORAGE.md](../shared/STORAGE.md)) |
| Replaces | the archived SDK harness `.archive/dsh-dedup` (its results are context only) |

## Overview

Each row starts from an empty project. For each selected state `k` (after the
previous selected state `p`, or the empty tree first) one `workspace exec` runs
`apply.py p k` inside the Workspace, then one `workspace commit`:

| Case | States | Selection | Logical bytes (Σ states) | Git pack + idx, dsh-dedup v1.0.0 pin |
| --- | ---: | --- | ---: | ---: |
| D10 | 17 | `sorted(set(range(1,158,10)) \| {157})` | 561,010,345 | 41,797,536 |
| D03 | 53 | `range(1,158,3)` (ends at 157) | 1,676,767,835 | 48,169,384 |

`apply.py` reads both trees from the seed repository baked into the image
(`git ls-tree`, one `git cat-file --batch`). **Write method:** a path that
stays a regular file is rewritten in place (same inode, `O_WRONLY|O_TRUNC`);
removed paths and file↔symlink changes are unlinked; new paths are created;
emptied directories are removed. After the last Commit the Store is measured
at the quiesced boundary, the paged `commit list` is collected, and
`verify.py 157` checks the branch head once in a fresh Sandbox (path, type,
executable bit, size and SHA-256 against the corpus's own state-157 oracle; no
missing or extra paths).

## Setup

See [TOOL.md](TOOL.md) for the seed, image, machine and PostgreSQL setup, and
[environments.example.json](environments.example.json) for the config. The
seed is a local pinned copy (54 MB bare repository) and is never published.

```bash
python3 fs-storage-dsh/src/seed.py stage --data ~/Ephemeral-AI-Lab/deepseek-history-data --out ~/.cache/fs-storage-dsh/context-v1
docker build --pull=false --platform linux/arm64 -t fs-storage-dsh:v1-<sha> ~/.cache/fs-storage-dsh/context-v1
E=/private/fsd.json C=/private/fsd-prepared O=/retained/fsd
export BENCH_PG_PASSWORD=...   # the variable named in the config
python3 fs-storage-dsh/src/run.py run --environment $E --cache $C --case D10 --backend sqlite --output $O/D10/sqlite
python3 fs-storage-dsh/src/run.py run --environment $E --cache $C --case D10 --backend postgresql --output $O/D10/postgresql
python3 fs-storage-dsh/src/run.py run --environment $E --cache $C --case D03 --backend sqlite --output $O/D03/sqlite
python3 fs-storage-dsh/src/run.py run --environment $E --cache $C --case D03 --backend postgresql --output $O/D03/postgresql
python3 fs-storage-dsh/src/run.py finish --environment $E --cache $C
# release the worker, PostgreSQL and image, recording final-cleanup.json, then:
python3 fs-storage-dsh/src/report.py --cache $C [--repeat-cache $R] --references <refs dir> \
  --environment $E --cleanup final-cleanup.json --output result/YYYY-MM-DD/fs-storage-dsh/FULL_LAYERFS_SHA/report.md
```

References are computed once per workload version ([AGENTS.md](AGENTS.md#references)).
Run the harness checks with an explicit bound:

```bash
python3 -c 'import subprocess; subprocess.run(["python3", "-m", "unittest", "discover", "-s", "fs-storage-dsh/tests", "-v"], check=True, timeout=120)'
```

## Past runs

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-06 | `7691ac20b0` | 4 of 4 rows PASS (applied, committed, measured and verified at state 157); net Store bytes D10 47,927,296 B SQLite / 53,272,576 B PostgreSQL, D03 61,014,016 B / 68,419,584 B, against a Git pack + idx of 41,805,317 / 48,166,223 B; final cleanup COMPLETE | [report](../result/2026-11-06/fs-storage-dsh/7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3/report.md) |
| 2026-11-06 | `b4fa173e40` | 3 of 4 rows PASS (applied, committed, measured and verified at state 157); net Store bytes D10 57,081,856 B SQLite / 70,008,832 B PostgreSQL, D03 72,966,144 B / — B, against a Git pack + idx of 41,805,317 / 48,166,223 B; final cleanup COMPLETE | [report](../result/2026-11-06/fs-storage-dsh/b4fa173e401fc87af6610c151225096288e4ba57/report.md) |
| 2026-11-06 | `6d820c756b` | 4 of 4 rows PASS (applied, committed, measured and verified at state 157); net Store bytes D10 56,139,776 B SQLite / 69,967,872 B PostgreSQL, D03 73,015,296 B / 93,388,800 B, against a Git pack + idx of 41,805,317 / 48,166,223 B; final cleanup COMPLETE | [report](../result/2026-11-06/fs-storage-dsh/6d820c756b9b12541ac84af7b88467069f31bcbf/report.md) |
<!-- runs:end -->
