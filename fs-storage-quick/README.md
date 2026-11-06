# fs-storage-quick — quick Store-bytes gate for LayerFS storage optimizations, SQLite and PostgreSQL
> group: filesystem · measures: storage

## Basic info

| Item | Value |
| --- | --- |
| Tool | Stdlib generator/verifier [image/gen.py](image/gen.py) (Q1–Q5) and edit model [image/model.py](image/model.py) (Q6), workload `fs-storage-quick-v1`, run inside the Sandbox |
| Runs on | Docker machine only: 6 cases × SQLite, PostgreSQL = 12 rows, all SQLite rows then all PostgreSQL rows |
| Budget | ≤ 120 s matrix wall per backend is the target (INELIGIBLE diagnostic; measured values are in the past runs) |
| Measures | Store bytes at a quiesced boundary (SQLite file and WAL separately, PostgreSQL schema), per-Commit `new_canonical`/`new_stored`/`new_metadata`, optional late re-probe; no timing claims |
| Gate | `run.py compare` of a candidate against the pinned [baseline](baseline/) with a documented noise rule |
| Rules | [AGENTS.md](AGENTS.md); shared measurement in [shared/STORAGE.md](../shared/STORAGE.md) |

## Overview

A subset of fs-storage-micro and fs-storage-history sized to run quickly, made
for the layerfs-project#84 optimizations (#86–#92): each candidate build runs
the matrix with its own CLI, bundle, home and PostgreSQL server, and compares
against the base build's pinned export. The full fs-storage suites stay the
release check.

| Case | Workload | Write method | Commits | Exercises |
| --- | --- | --- | ---: | --- |
| Q1 tiny files | 2,000 files of 0–4,096 B in 20 directories | New paths | 1 | Per-file rows; PostgreSQL row/index overhead |
| Q2 in-place edits | 25 synthetic text files of 16–64 KiB, then 12 Commits each replacing 1% of lines | In place, `O_TRUNC` | 13 | Chain budget / chain-root re-base |
| Q3 rename-over edits | The Q2 content sequence | Temp file + rename | 13 | Small-file delta base |
| Q4 new-path edits | The Q2 content sequence, each version at a new path | New path + unlink | 13 | Similarity ring |
| Q5 large file | 32 MiB random file; insert 1 B at start; insert 1 B at middle; overwrite 4 KiB; append 1 MiB; delete first byte | In place, `O_TRUNC` | 6 | Extent / directory page metadata |
| Q6 history | `project init` of the 65.0 MB DSH-157 base; 20 edit Commits (5 seeded operations each); 3 Branches from `main` with the same single Commit | Edit model | 23 | Init staging, per-Commit rows and metadata, Branch cost |

Per row: a fresh Store, `project init` of an empty folder (`store push` to
Docker for SQLite), floor probe, (Q6: base Init + probe), forks, one Sandbox,
one Exec per part and one Commit per plan entry, unmount, a fresh mount of each
head in the same Sandbox for final-state verification, close, quiesced final
probe, paged `commit list`, release (or deferral for the late probe).
Q6 verifies `lane` and `b01` by content (namespace digest plus SHA-256 of
every touched path) and `b02`, `b03` by root object identity with `b01`.

Counts were cut from #85's initial table after two probes on a loaded Docker
host (other owners' Linux builds running): PostgreSQL took 314 s with 50 × 20
text edits, 64 MiB, 2 Inits, 50 Commits, 5 Branches and full-manifest checks.
Cut: text files 50 → 25 and edits 20 → 12 (still past the depth 6–7 at which
the 512 KiB chain budget re-stores a 64 KiB file), Q5 64 → 32 MiB, Q6 Inits
2 → 1 (each Init of the base costs 20–30 s on PostgreSQL), Q6 Commits 50 → 20,
Branches 5 → 3, and Q6's full-content hash per head → namespace + touched paths.

## Setup

1. A matched release CLI (+ `layerfs-daemon` beside it) and sealed Linux
   bundle of the build under test, installed into a private
   `XDG_CACHE_HOME/layerfs/bundle/2.0.0/linux-aarch64/`; a private
   `LAYERFS_HOME` (mode 0700) and an empty folder.
2. Suite image: `docker build --pull=false --platform linux/arm64 -t fs-storage-quick:v1 fs-storage-quick/image`,
   then `layerfs machine update docker --image <image id>` and
   `layerfs machine start docker`.
3. Base tree: `python3 fs-storage-history/src/base.py --seed <git-snapshots-157-v1/snapshots.git> --dest <private>/base-157`.
4. A PostgreSQL server (`postgres:17-bookworm`, 1 CPU / 512 MiB, loopback
   port), password only in `BENCH_PG_PASSWORD`.
5. Environment: `python3 fs-storage-quick/src/env.py --campaign-id … --out <campaign dir>/environment.json`
   (see [environments.example.json](environments.example.json)); then
   `run.py createdb` creates the campaign's six empty databases.
6. Pins are committed ([src/pins.json](src/pins.json)); `src/pin.py` only
   when the workload version changes.

Run (rows serial; each command ≤ 120 s):

```bash
E=<campaign dir>/environment.json C=<campaign dir>/campaign
python3 fs-storage-quick/src/run.py createdb --environment $E --cache $C
python3 fs-storage-quick/src/run.py run --environment $E --cache $C --late-probe-wait-s 75
python3 fs-storage-quick/src/run.py finish --environment $E --cache $C
python3 fs-storage-quick/src/run.py export --cache $C --output <campaign dir>/rows.json
python3 fs-storage-quick/src/run.py compare --baseline fs-storage-quick/baseline/b4fa173e401fc87af6610c151225096288e4ba57.json --candidate $C
python3 fs-storage-quick/src/report.py --rows <campaign dir>/rows.json --notes notes.md \
  --output result/YYYY-MM-DD/fs-storage-quick/FULL_LAYERFS_SHA/report.md
python3 shared/src/readme_index.py
```

`--attribution <private dir>` (with the late probe) adds DIAGNOSTIC per-table
attribution; it is off by default pending the owner's decision (#85 task 1).

Tests (no LayerFS):
`python3 -c 'import subprocess; subprocess.run(["python3", "-m", "unittest", "discover", "-s", "fs-storage-quick/tests", "-v"], check=True, timeout=120)'`

## Past runs

<!-- runs:begin -->
<!-- runs:end -->
