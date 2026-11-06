# #71 final PostgreSQL vs SQLite verification

> Status: Diagnostic observations; timings are performance-ineligible (no cold-cache protocol). One sample per row, no reruns.

Final identity: branch `pg-perf` at `ddd1bc83cd` (release CLI `04a4c120…`, daemon `0472e2a6…`, Linux bundle `4c7499ce…`). Before: baseline campaign `pg62-base-1106` at `b919f50eaf` (published 2026-11-06 artifacts). Harness `c731387` (runner and cases identical to the baseline's `3fdb4ef`). Same machines, PostgreSQL 17.11 server `pgbench-pg` and `pg_settings` as the baseline; new campaign ids and new databases.

Reports:

- fs-bench-quick C01–C18, 162 rows: [`fs-bench-quick/ddd1bc83cda03d223c9dde6be86b08024db0c5e5/pg71-final/report.md`](fs-bench-quick/ddd1bc83cda03d223c9dde6be86b08024db0c5e5/pg71-final/report.md)
- fio, smallfile, mdtest, fsx, fsstress, pjdfstest: `<suite>/ddd1bc83cda03d223c9dde6be86b08024db0c5e5/pg71-six/report.md`
- Receipts (local, untracked): `fs-bench-quick/results/pg71-final-1106/`, `<suite>/results/pg71-six-1106/`; infrastructure ledger `fs-bench-quick/results/pg71-final-1106/infra/infrastructure.jsonl`.

## Outcomes

| suite | rows | PASS | FAIL | NOT_RUN | note |
|---|---:|---:|---:|---:|---|
| fs-bench-quick | 162 | 162 | 0 | 0 | baseline 160/1/1 (Apple outage) |
| fio | 36 | 36 | 0 | 0 | |
| smallfile | 45 | 45 | 0 | 0 | |
| mdtest | 18 | 4 | 0 | 14 | guests: Linux mdtest/Open MPI not in the offline tool image (M01 guest receipts absent, recorded NOT_RUN in campaign.json) |
| fsx | 9 | 9 | 0 | 0 | intrinsic checks PASS, 997 effective ops everywhere |
| fsstress | 9 | 2 | 7 | 0 | every Linux guest row: EPERM on hard link of a symlink inode (product restricts hard links to regular files; same failure as the baseline) |
| pjdfstest | 36 | 36 | 0 | 0 | P01 4/4, P02 6/6, P03 5/5, P04 14/14 assertions everywhere |

Correctness suites ran on both backends and the Docker co-located PostgreSQL arm.

## fs-bench-quick before → after

### Per machine × backend medians, before (b919f50eaf) → after (ddd1bc83cd), ms

Median over the cells that PASS in both campaigns for that machine/arm (count `n`). One sample per row.

| machine | backend | n | create | mount | Exec | Commit | unmount |
|---|---|---:|---|---|---|---|---|
| native | sqlite | 18 | 41 → 42 | 37 → 38 | 279 → 354 | 144 → 139 | 32 → 32 |
| native | postgresql | 18 | 103 → 44 | 89 → 54 | 440 → 444 | 261 → 175 | 60 → 29 |
| docker | sqlite | 18 | 362 → 334 | 24 → 23 | 260 → 259 | 71 → 85 | 18 → 18 |
| docker | postgresql | 18 | 566 → 386 | 116 → 53 | 225 → 305 | 178 → 145 | 18 → 17 |
| docker | pg-colocated | 18 | 528 → 377 | 112 → 49 | 235 → 262 | 111 → 110 | 18 → 18 |
| lima | sqlite | 18 | 739 → 737 | 20 → 21 | 166 → 219 | 68 → 84 | 17 → 17 |
| lima | postgresql | 18 | 950 → 795 | 125 → 54 | 222 → 228 | 243 → 140 | 19 → 17 |
| apple-container | sqlite | 17 | 60 → 58 | 17 → 18 | 178 → 193 | 77 → 88 | 14 → 14 |
| apple-container | postgresql | 17 | 273 → 123 | 130 → 34 | 215 → 206 | 222 → 135 | 54 → 14 |


### PostgreSQL − SQLite median gap per machine, before → after, ms

Median over cells of (PostgreSQL row − SQLite row) for cells where both arms PASS in both campaigns. `coloc` is the Docker co-located arm minus Docker SQLite.

| machine | arm | n | create | mount | Exec | Commit | unmount |
|---|---|---:|---|---|---|---|---|
| native | pg | 18 | +60 → +3 | +50 → +15 | +30 → -1 | +78 → +36 | +24 → -4 |
| docker | pg | 18 | +228 → +53 | +90 → +29 | -0 → +6 | +59 → +48 | +1 → -0 |
| docker | coloc | 18 | +161 → +43 | +89 → +27 | -22 → -2 | +19 → +21 | +1 → +0 |
| lima | pg | 18 | +214 → +58 | +100 → +33 | +25 → -1 | +96 → +48 | +1 → -0 |
| apple-container | pg | 17 | +203 → +65 | +113 → +17 | +37 → +4 | +95 → +47 | +28 → +0 |


### pg_stat_statements per phase, Docker PostgreSQL (published port), statements/connections before → after

| cell | create | mount | Exec | Commit | unmount | follow-up |
|---|---|---|---|---|---|---|
| C01 | 54/5 → 6/2 | 60/3 → 30/3 | 8/0 → 8/0 | 346/1 → 91/2 | 0/0 → 0/0 |  |
| C03 | 54/5 → 6/2 | 60/3 → 30/3 | 8/0 → 8/0 | 53/1 → 37/2 | 0/0 → 0/0 |  |
| C04 | 54/5 → 6/2 | 60/3 → 30/3 | 8/0 → 8/0 | 541/1 → 89/2 | 0/0 → 0/0 |  |
| C09 | 32/3 → 5/1 | 61/3 → 30/3 | 6/0 → 6/0 | 7/0 → 1/0 | 0/0 → 0/0 |  |
| C12 | 54/5 → 6/2 | 60/3 → 30/3 | 0/0 → 0/0 | 381/1 → 97/2 | 0/0 → 0/0 |  |
| C13 | 54/5 → 6/2 | 60/3 → 30/3 | 0/0 → 0/0 | 118/1 → 79/2 | 0/0 → 0/0 | followup_exec 0/0 → 0/0 |
| C14 | 54/5 → 6/2 | 60/3 → 30/3 | 0/0 → 0/0 | 6/0 → 1/0 | 0/0 → 0/0 |  |
| C15 | 54/5 → 6/2 | 60/3 → 30/3 | 0/0 → 0/0 | 136/1 → 81/2 | 0/0 → 0/0 |  |
| C16 | 54/5 → 6/2 | 60/3 → 30/3 | 80/0 → 80/0 | 2745/1 → 696/2 | 0/0 → 0/0 |  |
| C17 | 32/3 → 5/1 | 61/3 → 30/3 | 1573/0 → 847/0 | 7/0 → 1/0 | 0/0 → 0/0 |  |
| C18 | 32/3 → 5/1 | 63/3 → 32/3 | 39/0 → 39/0 | 7/0 → 1/0 | 0/0 → 0/0 |  |


Commit counts are the same on every route (C16 685–699). Every non-UpToDate Commit now opens 2 connections (was 1).

**Regression to check:** write-heavy Exec and 64 MiB Commit are slower at `ddd1bc83cd` on both backends (median after/before: write Exec SQLite ×1.33, PostgreSQL ×1.18; 64 MiB Commit SQLite ×1.35, PostgreSQL ×1.24), with lower host load than the baseline. Read Exec is unchanged. Suspect `7a625d855d` (digest window/overlay page 1,024, #69); not isolated. **Resolved by the bisect below: not a code regression.**

Storage: only Commit results are recorded; `new_stored`/`new_metadata` match the baseline within 0.5% on both backends. No database file sizes.

## Other suites before → after (published 2026-11-06 run at b919f50eaf)

Confounds: the published run used fresh machines, no co-located arm and no observer; first-touch outliers (e.g. native SQLite Exec fsx 1,055 ms, pjdfstest 603 ms before) dominate some medians.

| suite | machine | backend | rows PASS before → after | create | Exec | Commit | mount (after) | unmount (after) |
|---|---|---|---|---|---|---|---|---|
| fio | native | sqlite | 4/4 → 4/4 | 27 → 32 | 474 → 474 | 141 → 76 | 34 | 28 |
| fio | native | postgresql | 4/4 → 4/4 | 75 → 43 | 366 → 466 | 159 → 84 | 46 | 25 |
| fio | docker | sqlite | 4/4 → 4/4 | 309 → 287 | 501 → 520 | 52 → 42 | 20 | 16 |
| fio | docker | postgresql | 4/4 → 4/4 | 485 → 307 | 372 → 511 | 56 → 63 | 44 | 15 |
| fio | docker | pg-colocated | 0/0 → 4/4 | — → 303 | — → 506 | — → 44 | 42 | 15 |
| fio | lima | sqlite | 4/4 → 4/4 | 739 → 727 | 471 → 340 | 33 → 31 | 22 | 14 |
| fio | lima | postgresql | 4/4 → 4/4 | 912 → 780 | 357 → 343 | 60 → 51 | 46 | 14 |
| fio | apple-container | sqlite | 4/4 → 4/4 | 59 → 73 | 349 → 348 | 31 → 61 | 18 | 15 |
| fio | apple-container | postgresql | 4/4 → 4/4 | 274 → 130 | 370 → 363 | 94 → 72 | 36 | 14 |
| smallfile | native | sqlite | 5/5 → 5/5 | 38 → 26 | 3720 → 3745 | 97 → 61 | 34 | 28 |
| smallfile | native | postgresql | 5/5 → 5/5 | 89 → 42 | 3780 → 3772 | 174 → 88 | 46 | 26 |
| smallfile | docker | sqlite | 5/5 → 5/5 | 306 → 264 | 3711 → 3676 | 37 → 33 | 19 | 15 |
| smallfile | docker | postgresql | 5/5 → 5/5 | 460 → 305 | 3680 → 3696 | 101 → 81 | 43 | 14 |
| smallfile | docker | pg-colocated | 0/0 → 5/5 | — → 299 | — → 3686 | — → 52 | 42 | 15 |
| smallfile | lima | sqlite | 5/5 → 5/5 | 724 → 738 | 3749 → 3740 | 33 → 30 | 18 | 13 |
| smallfile | lima | postgresql | 5/5 → 5/5 | 876 → 782 | 3763 → 3752 | 108 → 78 | 48 | 13 |
| smallfile | apple-container | sqlite | 5/5 → 5/5 | 55 → 68 | 3782 → 3797 | 32 → 56 | 18 | 13 |
| smallfile | apple-container | postgresql | 5/5 → 5/5 | 255 → 120 | 3855 → 3826 | 176 → 123 | 40 | 12 |
| mdtest | native | sqlite | 2/2 → 2/2 | 33 → 39 | 1484 → 1505 | 75 → 40 | 37 | 29 |
| mdtest | native | postgresql | 2/2 → 2/2 | 85 → 41 | 1513 → 1465 | 121 → 55 | 50 | 22 |
| mdtest | docker | sqlite | 2/2 → 0/2 | — | — | — | — | — |
| mdtest | docker | postgresql | 2/2 → 0/2 | — | — | — | — | — |
| mdtest | docker | pg-colocated | 0/0 → 0/2 | — | — | — | — | — |
| mdtest | lima | sqlite | 2/2 → 0/2 | — | — | — | — | — |
| mdtest | lima | postgresql | 2/2 → 0/2 | — | — | — | — | — |
| mdtest | apple-container | sqlite | 2/2 → 0/2 | — | — | — | — | — |
| mdtest | apple-container | postgresql | 2/2 → 0/2 | — | — | — | — | — |
| fsx | native | sqlite | 1/1 → 1/1 | 25 → 42 | 1055 → 260 | 74 → 49 | 38 | 29 |
| fsx | native | postgresql | 1/1 → 1/1 | 73 → 41 | 252 → 248 | 125 → 81 | 46 | 26 |
| fsx | docker | sqlite | 1/1 → 1/1 | 303 → 302 | 241 → 194 | 17 → 17 | 21 | 18 |
| fsx | docker | postgresql | 1/1 → 1/1 | 514 → 315 | 197 → 189 | 56 → 53 | 49 | 15 |
| fsx | docker | pg-colocated | 0/0 → 1/1 | — → 325 | — → 190 | — → 35 | 43 | 17 |
| fsx | lima | sqlite | 1/1 → 1/1 | 740 → 743 | 205 → 187 | 14 → 44 | 25 | 17 |
| fsx | lima | postgresql | 1/1 → 1/1 | 895 → 788 | 173 → 210 | 57 → 57 | 63 | 16 |
| fsx | apple-container | sqlite | 1/1 → 1/1 | 61 → 63 | 200 → 208 | 13 → 13 | 17 | 13 |
| fsx | apple-container | postgresql | 1/1 → 1/1 | 287 → 132 | 215 → 199 | 86 → 53 | 36 | 10 |
| fsstress | native | sqlite | 1/1 → 1/1 | 26 → 42 | 794 → 317 | 174 → 153 | 36 | 30 |
| fsstress | native | postgresql | 1/1 → 1/1 | 73 → 67 | 319 → 347 | 301 → 184 | 61 | 25 |
| fsstress | docker | sqlite | 0/1 → 0/1 | — | — | — | — | — |
| fsstress | docker | postgresql | 0/1 → 0/1 | — | — | — | — | — |
| fsstress | docker | pg-colocated | 0/0 → 0/1 | — | — | — | — | — |
| fsstress | lima | sqlite | 0/1 → 0/1 | — | — | — | — | — |
| fsstress | lima | postgresql | 0/1 → 0/1 | — | — | — | — | — |
| fsstress | apple-container | sqlite | 0/1 → 0/1 | — | — | — | — | — |
| fsstress | apple-container | postgresql | 0/1 → 0/1 | — | — | — | — | — |
| pjdfstest | native | sqlite | 4/4 → 4/4 | 44 → 40 | 603 → 225 | 80 → 57 | 34 | 28 |
| pjdfstest | native | postgresql | 4/4 → 4/4 | 91 → 43 | 192 → 190 | 128 → 68 | 46 | 25 |
| pjdfstest | docker | sqlite | 4/4 → 4/4 | 315 → 282 | 135 → 121 | 13 → 14 | 19 | 13 |
| pjdfstest | docker | postgresql | 4/4 → 4/4 | 545 → 310 | 115 → 105 | 39 → 35 | 46 | 13 |
| pjdfstest | docker | pg-colocated | 0/0 → 4/4 | — → 324 | — → 125 | — → 24 | 45 | 14 |
| pjdfstest | lima | sqlite | 4/4 → 4/4 | 752 → 739 | 79 → 95 | 15 → 13 | 20 | 13 |
| pjdfstest | lima | postgresql | 4/4 → 4/4 | 931 → 769 | 75 → 72 | 40 → 34 | 47 | 13 |
| pjdfstest | apple-container | sqlite | 4/4 → 4/4 | 65 → 68 | 117 → 100 | 12 → 13 | 17 | 12 |
| pjdfstest | apple-container | postgresql | 4/4 → 4/4 | 336 → 134 | 112 → 99 | 81 → 68 | 38 | 13 |

| suite | machine | PG−SQLite create before → after | Exec | Commit |
|---|---|---|---|---|
| fio | native | +48 → +10 | +17 → -9 | +37 → +11 |
| fio | docker | +166 → +26 | +0 → -5 | +4 → +27 |
| fio | lima | +169 → +44 | -7 → +2 | +28 → +20 |
| fio | apple-container | +221 → +64 | +18 → +16 | +64 → +11 |
| smallfile | native | +51 → +14 | +56 → +6 | +73 → +23 |
| smallfile | docker | +142 → +43 | +14 → +17 | +63 → +43 |
| smallfile | lima | +154 → +42 | +4 → +24 | +74 → +46 |
| smallfile | apple-container | +203 → +63 | +60 → +66 | +144 → +67 |
| mdtest | native | +52 → +2 | +29 → -40 | +46 → +15 |
| fsx | native | +47 → -1 | -803 → -12 | +51 → +32 |
| fsx | docker | +210 → +13 | -44 → -5 | +40 → +36 |
| fsx | lima | +155 → +45 | -33 → +23 | +43 → +13 |
| fsx | apple-container | +226 → +69 | +15 → -9 | +73 → +41 |
| fsstress | native | +47 → +26 | -475 → +30 | +127 → +32 |
| pjdfstest | native | +47 → +3 | -31 → +5 | +44 → +15 |
| pjdfstest | docker | +222 → +31 | -16 → -11 | +26 → +22 |
| pjdfstest | lima | +177 → +28 | -4 → -16 | +25 → +22 |
| pjdfstest | apple-container | +262 → +65 | -4 → -5 | +68 → +54 |


## Bisect follow-up: the write-path slowdown is not in the code

Campaign `pg71-bisect-1106` re-measured selected rows at five identities with the same harness and machines: the published baseline artifacts (`p919`), our own build of the base `6d820c756b` (`a6d8`), `f45fef94bd` (`bf45`), `7a625d855d` (`c7a6`) and `ddd1bc83cd` (`dddd`). It ran 2–3 rounds per row, and every pair was checked with the paired-delta rule. Exec / Commit ms, median:

| Row | a6d8 | bf45 | c7a6 | dddd |
|---|---|---|---|---|
| C06 Docker SQLite | 185 / 241 | 161 / 237 | — | 158 / 242 |
| C05 Docker SQLite (`find`) | 668 / 86 | 651 / 83 | — | 638 / 96 |
| C01 Docker SQLite | 263 / 80 | 264 / 81 | 218 / 77 | 275 / 80 |
| C04 native SQLite | 3,174 / 132 | 3,251 / 128 | 3,337 / 134 | 3,008 / 132 |
| C01 Docker PostgreSQL | 273 / 185 | 252 / 146 | 273 / 122 | 278 / 125 |
| C04 native PostgreSQL | 3,131 / 271 | 2,794 / 170 | 2,877 / 170 | 2,972 / 168 |

- **No product step is flagged.** The single flag is C01 native SQLite Exec between `p919` and `a6d8`, whose product source is identical, so it is a build or run artifact.
- **The slowdown is not reproduced.** The final run's C06 SQLite Commit of 332 ms is 242 ms at the same artifacts. The ×1.2–1.37 above is attributed to the final campaign's conditions: it reused the baseline home and worker after the outage restart.
- **#69's readdir change has no cost.** C05 shows none from the 1,024-entry kernel directory pages.
- **Not re-measured:** PostgreSQL Commit on C06–C08, and C07, C10 and C16.

Receipts (local, untracked): `fs-bench-quick/results/pg71-bisect-1106/` (`infra/summary.md`, `infra/ledger.jsonl`, `g2/<identity>/r<n>/rows/`).

## Resources kept (owner=pg-perf-62) and release commands

CLI `~/.cache/pg-perf-62/pg71-final/artifacts/layerfs` with `LAYERFS_HOME=~/.cache/pg-perf-62/pg62-base/home XDG_CACHE_HOME=~/.cache/pg-perf-62/pg71-final/xdg`:

- `layerfs machine remove pg62-lima`; `layerfs machine remove pg62-apple` (stopped); `layerfs machine remove pg71-lima6`; `layerfs machine remove pg71-apple6`
- `layerfs machine stop docker` (worker `lfs-c0bfb23a-docker`, volume `lfs-c0bfb23a-docker-data`; its image is now `pg71-six-tools:20261106`)
- `docker rm -f pgbench-pg`; `docker volume rm pgbench-pg-data`
- `docker image rm pg71-six-tools:20261106`
- then `rm -rf ~/.cache/pg-perf-62` (homes, artifacts, bundle, tool image context, configs)
