# fs-storage-history — Store bytes by history shape: long history, branches, forks and projects
> group: filesystem · measures: storage

## Basic info

| Item | Value |
| --- | --- |
| Measures | Bytes a LayerFS Store holds after a seeded edit history; never speed |
| Runs on | Docker only, SQLite then PostgreSQL: 7 cases, 14 rows |
| Base tree | DSH checkpoint 157 (9,404 files + 11 symlinks, 65,020,822 B) from the local seed `git-snapshots-157-v1/snapshots.git`; never published |
| Status | Implemented; workload `fs-storage-history-v1` frozen after a SQLite probe |
| Frozen rules | [AGENTS.md](AGENTS.md); shapes and pins in [src/cases.py](src/cases.py); edit model in [src/model.py](src/model.py); image in [TOOL.md](TOOL.md) |
| Measurement | [shared/STORAGE.md](../shared/STORAGE.md) (`storage.Driver` on the shared `runner.Campaign` custody) |

## Overview

Every project imports the same base tree with `project init`. Each Commit
then applies five operations drawn deterministically from `(seed, step)`:

| Share | Operation | Write method |
| ---: | --- | --- |
| 70% | Edit 1–5 lines of a text file (replace, insert or delete) | In place: same inode, `O_WRONLY\|O_TRUNC` |
| 10% | New 256–4,096 B synthetic text file | New path, `O_CREAT\|O_EXCL`, 0644 |
| 5% | Delete a file | `unlink(2)` |
| 10% | Rename a file (80% same directory) | `rename(2)` to a new path |
| 5% | Append one 80–240 B line to a `*.jsonl`/`*.log` file | In place, `O_APPEND` |

| Case | Shape | Commits | What it shows |
| --- | --- | ---: | --- |
| H01 long history | 1 project, 1 Branch × 500 Commits | 500 | Delta chains past the depth cap; growth per Commit |
| H02 many branches | 50 Branches from the base, 5 Commits each, distinct seeds | 250 | Extra bytes per Branch |
| H03 identical branches | 50 Branches from the base, the same single Commit | 50 | ≈ metadata only per Branch |
| H04 nested forks | Fork chain 10 deep, 5 Commits per level | 50 | Branches of Branches |
| H05 projects in one Store | 20 projects from the base, 5 Commits each, distinct seeds | 100 | Cross-project sharing |
| H06 projects in separate Stores | The same 20 projects, one Store each | 100 | Baseline: Σ H06 ÷ H05 = cross-project gain |
| H07 combined | 4 projects × 5 Branches × 10 Commits in one Store | 200 | Everything at once |

A row reports the empty-Store floor, the Init floor (after every base
import), final and net Store bytes, per-Commit `new_stored`/`new_metadata`
from the paged `commit list`, per-Branch and per-project marginal bytes, and
offline references (whole-file unique, Σ `tar | zstd -3`, Git pack + idx,
approximate CDC). Each Branch head is verified once against the host oracle.

## Setup

Prerequisites ([TOOL.md](TOOL.md)): the pinned release CLI and matched
Linux bundle, the suite image on the Docker machine, a dedicated PostgreSQL
server with one empty database per Store (26: H06 needs 20), and the base
tree extracted from the seed:

```bash
python3 fs-storage-history/src/base.py --seed <seed>/snapshots.git --dest ~/.cache/fs-storage-history/base-157
python3 fs-storage-history/src/refs.py --base ~/.cache/fs-storage-history/base-157 --output <private>/references.json
```

Copy [environments.example.json](environments.example.json), replace the
placeholders, export the PostgreSQL password variable, then run one row at
a time, SQLite rows first:

```bash
python3 fs-storage-history/src/run.py row --environment E --case H01 --backend sqlite --output <private>/results/H01-sqlite
```

Publish from the local results:

```bash
python3 fs-storage-history/src/report.py --results <private>/results --references <private>/references.json \
  --environment E --notes <private>/notes.md --output result/YYYY-MM-DD/fs-storage-history/FULL_LAYERFS_SHA/report.md
python3 shared/src/readme_index.py
```

Harness checks (no LayerFS execution):

```bash
python3 -c 'import subprocess; subprocess.run(["python3", "-m", "unittest", "discover", "-s", "fs-storage-history/tests", "-v"], check=True, timeout=120)'
```

## Past runs

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-06 | `7691ac20b0` | All 14 rows (7 cases × Docker × SQLite, PostgreSQL) PASS with every Branch head verified on final integration 7691ac20b0 (= 8b701f42f0 + #92 + #91 + #90, PRs pending owner merge); against the Phase 0 reference b4fa173e40, net Store bytes fell in every comparable row (SQLite −2.93 % … −17.93 %, PostgreSQL −18.03 % … −53.26 %), Σ new_metadata fell 19–41 % with payload unchanged, and PostgreSQL ÷ SQLite is now 1.07–1.10× in every case (Phase 0: 1.11–2.22×). Final cleanup COMPLETE | [report](../result/2026-11-06/fs-storage-history/7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3/report.md) |
| 2026-11-06 | `b4fa173e40` | 13 of 14 rows PASS with every Branch head verified (171 heads on PostgreSQL; 168 on SQLite, including the 47 H02 heads committed before the failure). H02 SQLite is an infrastructure FAIL: the Docker Desktop disk filled up, and the row was not rerun. Against 6d820c756b, Commit pack bytes moved by at most 243 B per row; Store bytes moved by −2.8 MB … +32,768 B, mostly in PostgreSQL Init. Final cleanup COMPLETE for this suite's resources | [report](../result/2026-11-06/fs-storage-history/b4fa173e401fc87af6610c151225096288e4ba57/report.md) |
| 2026-11-06 | `6d820c756b` | All 14 rows (7 cases × Docker × SQLite, PostgreSQL) PASS with every Branch head verified (171 heads per backend); 50 identical Branches cost ≈ 5.3 KB of metadata each, 20 projects in separate Stores need 17.1× (SQLite) / 11.2× (PostgreSQL) the net bytes of one shared Store, and 500 Commits add a flat ≈ 3.4 KB of packs each; final cleanup COMPLETE | [report](../result/2026-11-06/fs-storage-history/6d820c756b9b12541ac84af7b88467069f31bcbf/report.md) |
<!-- runs:end -->
