# fs-storage-micro — Store bytes for one LayerFS storage mechanism per case
> group: filesystem · measures: storage

## Basic info

| Item | Value |
| --- | --- |
| Tool | Stdlib generator and verifier [image/gen.py](image/gen.py) (`fs-storage-micro-v1`), run inside the Sandbox |
| Runs on | Docker machine only, SQLite then PostgreSQL Store: 8 cases, 16 rows, plus one determinism repeat |
| Measures | Store bytes at a quiesced boundary, per-Commit `new_stored`/`new_metadata`, offline references. No timing claims |
| Rules | [AGENTS.md](AGENTS.md); shared measurement in [shared/STORAGE.md](../shared/STORAGE.md) |
| Lifecycle | [shared/src/storage.py](../shared/src/storage.py) on `runner.Campaign` custody; entry [src/run.py](src/run.py) |

## Overview

Each case exercises one storage mechanism of LayerFS 2.0 (CAS, whole-file
objects below 128 KiB, GEAR CDC at 8/16/32 KiB, zstd prefix deltas, per-object
zstd-3) on generated data with a known expected result. A case passes when it
runs and its final state verifies; bytes are reported against the expectation,
not gated by it. Generated text is synthetic (a seeded word model).

| Case | Workload | Write method | Commits | Expected result |
| --- | --- | --- | ---: | --- |
| M01 tiny files | 10,000 files of 0–4,096 B in 100 directories | New paths | 1 | Net bytes ÷ 10,000 = overhead per small file |
| M02 duplicates | One 50,000,000 B tree, then 10 copies at new paths | New paths | 2 | Second Commit stores only tree/metadata (≈0 payload) |
| M03 in-place edits | 100 text files of 16–64 KiB, 20 Commits each changing 1% of lines | In-place `O_TRUNC` | 21 | Deltas against the previous version; chain passes depth 16 |
| M04 rename-over edits | Same content as M03 | Write temp + rename | 21 | Compare with M03 |
| M05 new-path edits | Same content as M03, each version at a new path, old removed | New path + unlink | 21 | Similarity ring only; compare with M03 |
| M06 large file | 64 MiB random file, then insert 1 B at start, insert 1 B at middle, overwrite 4 KiB at middle, append 1 MiB, delete first byte | In-place `O_TRUNC` | 6 | Each edit adds ≈1–2 chunks (≤64 KiB), except append (≈1 MiB) |
| M07 compressibility | 64 MiB random, 64 MiB zeros, 64 MiB synthetic text, one file per Commit | New paths | 3 | Random ≈64 MiB stored raw, zeros ≈0, text at the zstd-3 ratio |
| M08 SQLite churn | 33,542,144 B SQLite database, 10 Commits each updating 1% of rows, then `VACUUM` | In-place (SQLite writes) | 12 | Page-local churn reuses most chunks; `VACUUM` reshuffles |

Per row: a fresh Store, `project init` of an empty folder, `store push` to
Docker (SQLite), floor probe, fork `lane`, one Sandbox and Workspace, one Exec
per generator part and one Commit per plan entry, unmount, close, final probe,
paged `commit list`, then a fresh Sandbox verifies the branch head's canonical
manifest against the pinned oracle, and the Store is released.

## Setup

1. Matched release CLI/daemon and Linux bundle of the pinned LayerFS commit in
   a private campaign directory (outside Git); private `LAYERFS_HOME`
   (mode 0700) and `XDG_CACHE_HOME`.
2. Suite image (no network needed):
   `docker build --pull=false --platform linux/arm64 -t fs-storage-micro:<product-short-sha> fs-storage-micro/image`,
   then `layerfs machine update docker --image <image id>`.
3. A dedicated PostgreSQL server (`postgres:17-bookworm`, 1 CPU / 512 MiB,
   loopback port) with one pre-created empty database per PostgreSQL row; the
   password only in the environment variable named in the config.
4. Pins: `python3 fs-storage-micro/src/pin.py --work <private dir> --docker-image <image id>`
   emits every state in a throwaway container of the suite image, computes
   the references and writes `src/pins.json` (oracles + reference bytes).
   Rows refuse to run when the pins do not match `gen.py`.
5. Config: copy [environments.example.json](environments.example.json) and
   replace the placeholders.

Run (each row serial; each command bounded at ≤120 s):

```bash
E=/private/fsm/environment.json C=/private/fsm/campaign
python3 fs-storage-micro/src/run.py run --environment $E --cache $C --matrix
python3 fs-storage-micro/src/run.py run --environment $E --cache $C --case M03 --backend sqlite --repeat 2
python3 fs-storage-micro/src/run.py finish --environment $E --cache $C
python3 fs-storage-micro/src/report.py --cache $C --environment $E --notes notes.md \
  --output result/YYYY-MM-DD/fs-storage-micro/FULL_LAYERFS_SHA/report.md
python3 shared/src/readme_index.py
```

Tests (no LayerFS):
`python3 -c 'import subprocess; subprocess.run(["python3", "-m", "unittest", "discover", "-s", "fs-storage-micro/tests", "-v"], check=True, timeout=120)'`

## Past runs

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-06 | `7691ac20b0` | 16 of 16 fs-storage-micro rows PASS with verified final state; repeat M03/docker/postgresql/r2: page-granular Store bytes identical in this repeat, total +0 B, per-Commit new_stored ±15 B; repeat M03/docker/sqlite/r2: Store pages DIFFER, total +8,192 B, per-Commit new_stored ±14 B; final cleanup COMPLETE | [report](../result/2026-11-06/fs-storage-micro/7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3/report.md) |
| 2026-11-06 | `b4fa173e40` | 16 of 16 fs-storage-micro rows PASS with verified final state; repeat M03/docker/postgresql/r2: page-granular Store bytes identical in this repeat, total +0 B, per-Commit new_stored ±16 B; repeat M03/docker/sqlite/r2: Store pages DIFFER, total -98,800 B, per-Commit new_stored ±20 B; final cleanup COMPLETE | [report](../result/2026-11-06/fs-storage-micro/b4fa173e401fc87af6610c151225096288e4ba57/report.md) |
| 2026-11-06 | `6d820c756b` | 16 of 16 fs-storage-micro rows PASS with verified final state; repeat M03/docker/postgresql/r2: page-granular Store bytes identical in this repeat, total +0 B, per-Commit new_stored ±25 B; repeat M03/docker/sqlite/r2: page-granular Store bytes identical in this repeat, total -8,240 B, per-Commit new_stored ±15 B; final cleanup COMPLETE | [report](../result/2026-11-06/fs-storage-micro/6d820c756b9b12541ac84af7b88467069f31bcbf/report.md) |
<!-- runs:end -->
