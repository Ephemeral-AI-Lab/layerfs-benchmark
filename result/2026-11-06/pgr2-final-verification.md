# #98 round-2 final PostgreSQL vs SQLite verification

> Status: Diagnostic observations; timings are performance-ineligible (no cold-cache protocol). One sample per row, no reruns. Counts are the primary evidence.

Final identity: local branch `pg-r2` at `76a32a9a10` (release CLI `5f673410…`, daemon `d32ec78a…`, Linux bundle `cfe04f0c…`, source tree `2f838ed5…`; the gate-05 sealed artifacts). Before: round-1 final `ddd1bc83cd` (#71: CLI `04a4c120…`, daemon `0472e2a6…`, bundle `4c7499ce…`), campaigns `pg71-final-1106` and `pg71-six-1106`. Round 2's base `b4fa173e40` (round 1 merged in layerfs#581) has the same tree as `ddd1bc83cd` (`8275e954…`), so before → after is exactly the eleven round-2 merges below. Harness `a4f55ca` (branch `pg-r2-bench`; runner and cases as round 1's `c731387`: `git diff c731387 a4f55ca` on the cases and runners changes only an unused `budget_exceptions` option in `shared/src/runner.py`; none is configured here). New campaign ids, fresh LayerFS home, Docker worker, Lima `pgr2b-lima` and Apple Container `pgr2b-apple`; PostgreSQL 17.11 server `pgr2b-pg` (host-published 55442), `SHOW ALL` vs round 1's `pgbench-pg`: identical except the server default `synchronous_commit` off (round 1: on); the product sets `SET LOCAL synchronous_commit TO off` in every write transaction on both, so product writes behave the same. Sandbox image `1d91885d…` (round 1 receipts: `d5839688…`). The two rounds sealed their Linux bundles from different guest images: round 1 deliberately from `fs-bench-computer:gawk-20261020` (`66aeb6bb…`, bundle image `feeb1435…`) to match its baseline; round 2 from the launcher's registered runtime image `layerfs-352-runtime:node24-https-apt-20261024` (`afa1ef9c…` → `1d91885d…`), the image every round-2 gate build (control and treatment) used. fs-bench-quick guest Sandboxes therefore ran a different userland than in round 1 (an unpaired campaign condition; the paired checks below hold it equal). The six-suite guests ran the `fs-bench-computer`-derived tool image in both rounds.

Reports:

- fs-bench-quick C01–C18, 162 rows: [`fs-bench-quick/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-final/report.md`](fs-bench-quick/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-final/report.md)
- fio, smallfile, mdtest, fsx, fsstress, pjdfstest: `<suite>/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md` ([fio](fio/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md), [smallfile](smallfile/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md), [mdtest](mdtest/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md), [fsx](fsx/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md), [fsstress](fsstress/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md), [pjdfstest](pjdfstest/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md))
- Before → after tables: `fill.py` (report drafter, stdlib) cross-checked against the harness's new `fs-bench-quick/src/compare.py`; the fs-bench-quick medians, gaps, counts and storage agree cell for cell.
- Harness after the rows: `e65b57c` adds `fs-bench-quick/src/compare.py` and the `gate.py` `--suite/--machine/--tool-root/--worker-image` options used only by the paired attribution gates; campaign rows ran at `a4f55ca`.
- Infrastructure ledger (local): `~/.cache/pg-perf-r2/bench/final/infrastructure.jsonl`. Setup (tools image, machines, 175 databases) finished before row 1 (09:59:10Z); the six-suite machines were created at the suite boundary with no row running. Every row was attempted once.
- Receipts (local, untracked): `fs-bench-quick/results/pgr2-final-1106/`, `<suite>/results/<campaign>/`; campaign state `~/.cache/pg-perf-r2/bench/final/`.
- Tables below were filled by `fill.py` (stdlib). Pointed at #71's own inputs (before = the b919f50eaf runs, after = round-1 final) it reproduces all 527 compared cells of #71's tables exactly. Rule: per-row times as the suite reports print them (0.01 ms), median over cells that PASS in both campaigns, rounded half-up to whole ms.

## Outcomes

<!-- BEGIN outcomes -->
| suite | rows | PASS | FAIL | NOT_RUN | pending | round 1 rows: P/F/N | note |
|---|---:|---:|---:|---:|---:|---|---|
| fs-bench-quick | 162 | 162 | 0 | 0 | 0 | 162: 162/0/0 |  |
| fio | 36 | 36 | 0 | 0 | 0 | 36: 36/0/0 |  |
| smallfile | 45 | 45 | 0 | 0 | 0 | 45: 45/0/0 |  |
| mdtest | 18 | 4 | 0 | 14 | 0 | 18: 4/0/14 | guest rows NOT_RUN expected (no Linux mdtest/Open MPI in the offline tool image; carry-over) |
| fsx | 9 | 9 | 0 | 0 | 0 | 9: 9/0/0 |  |
| fsstress | 9 | 2 | 7 | 0 | 0 | 9: 2/7/0 | guest rows FAIL expected (EPERM on a hard link of a symlink; product rule, carry-over) |
| pjdfstest | 36 | 36 | 0 | 0 | 0 | 36: 36/0/0 |  |
<!-- END outcomes -->

Correctness suites ran on both backends and the Docker co-located PostgreSQL arm.

Failed, NOT_RUN and pending rows (all kept):

<!-- BEGIN nonpass -->
| suite | outcome | n | rows | reason / evidence | round 1 outcome of these rows |
|---|---|---:|---|---|---|
| mdtest | NOT_RUN | 14 | M01/apple-container/postgresql, M01/apple-container/sqlite, M01/docker/pg-colocated, M01/docker/postgresql, M01/docker/sqlite, M01/lima/postgresql, M01/lima/sqlite, M02/apple-container/postgresql, M02/apple-container/sqlite, M02/docker/pg-colocated, M02/docker/postgresql, M02/docker/sqlite, M02/lima/postgresql, M02/lima/sqlite | Linux mdtest and Open MPI are not in the offline guest tool image (carry-over from round 1: the ior source and MPI build were removed at the 2026-11-06 cleanup; rebuilding needs network downloads) | NOT_RUN 14 |
| fsstress | FAIL | 7 | S01/apple-container/postgresql, S01/apple-container/sqlite, S01/docker/pg-colocated, S01/docker/postgresql, S01/docker/sqlite, S01/lima/postgresql, S01/lima/sqlite | exec: workload exit 1<br>apple-container/postgresql: link:EPERM 6; unexpected 6, of which links of a symlink 6<br>apple-container/sqlite: link:EPERM 6; unexpected 6, of which links of a symlink 6<br>docker/pg-colocated: link:EPERM 6; unexpected 6, of which links of a symlink 6<br>docker/postgresql: link:EPERM 6; unexpected 6, of which links of a symlink 6<br>docker/sqlite: link:EPERM 6; unexpected 6, of which links of a symlink 6<br>lima/postgresql: link:EPERM 6; unexpected 6, of which links of a symlink 6<br>lima/sqlite: link:EPERM 6; unexpected 6, of which links of a symlink 6 | FAIL 7 |
<!-- END nonpass -->

## Main observations

fs-bench-quick (`pgr2-final-1106`, 162 rows, finished 10:16:55Z):

- **All 162 rows PASS**, as in round 1. Host 1-minute load 5.3–29.0, median 9.1 (round 1: 3.5–6.0, median 4.5). The load peaked during the write cells C03–C08.
- **Create: 6/2 → 4/3 on every PostgreSQL route.** Committed-base cells (C09–C11, C17, C18) went 5/1 → 3/2. #96 cut 3 statements. The extra connection and statement are the daemon's idle reader, which opens after readiness and before the mount marker, so they count under create. Median PG − SQLite create gap: Docker +53 → −7 ms, co-located +43 → −20, Lima +58 → +2, Apple Container +66 → +8, native +3 → +9.
- **Mount: 30/3 → 14/0 on every guest route** (#64 B: the daemon binds by Branch name on its idle reader, and the caller opens nothing). C18 went 32/3 → 16/0. Native went 24/2 → 14/0 (C18 52/2 → 27/0) and Apple Container 23/1 → 14/0. Mount gap: Docker +29 → +8, co-located +27 → +4, Lima +33 → +9, Apple +17 → +9, native +15 → +4.
- **Commit: 2 → 1 connection and 4–7 fewer statements in every non-UpToDate cell; C16 685–699 → 251 on every route.** UpToDate Commits stay at 1/0. Commit gap: Docker +48 → +36, co-located +21 → +18, Lima +48 → +35, Apple +47 → +43, native +36 → +22. C16 Commit time fell on both backends (Docker SQLite 1,080 → 772 ms, PostgreSQL 1,395 → 963 ms), because #95's batched difference-walk reads are backend-neutral.
- **Exec: C17 847 → 68 on every route (Lima 876 → 68), and C18 39 → 24** (native 13 → 13). Every other Exec count is unchanged. C17 Exec time: Docker PostgreSQL 917 → 339 ms, co-located 576 → 316, Lima 1,108 → 491, Apple 976 → 378, native 673 → 277.
- **The Docker Exec gap rose (+6 → +23 ms; co-located −2 → +36). The rise comes from load, not from PostgreSQL work.** It sits in the 64 MiB write cells C03–C08, which ran at load 10–29. All three Docker arms slowed there, SQLite included (C06 190 → 516 ms, C07 408 → 972 ms), while the PostgreSQL Exec counts stayed at 8/0 or 0/0. Read and small cells are flat or faster. Not rerun (one sample per row); the paired `fp-c06` check at load 7 puts C06 Exec at 223–242 ms for both identities, near round 1.
- **Storage:** `new_stored`/`new_metadata` match round 1 within 1% on every row that commits. The only larger change is C10 at 294 vs 300 bytes, a two-value variation that round 1 already showed across routes. No database file sizes are recorded.

Six suites (`pgr2-<suite>-1106`, 153 rows, 10:23–10:45Z):

- **Outcomes match round 1 exactly**: fio 36/36, smallfile 45/45, fsx 9/9 (intrinsic checks PASS), pjdfstest 36/36 PASS; mdtest 4 PASS + 14 NOT_RUN (guests: no Linux mdtest/Open MPI in the offline tool image); fsstress 2 PASS + 7 FAIL (every Linux guest row: `link:EPERM` ×6, all hard links of a symlink inode; the product restricts hard links to regular files). No new failure.
- **Counts move as in fs-bench-quick on every suite**: create 6/2 → 4/3 (committed base 5/1 → 3/2), mount 30/3 → 14/0 (smallfile 31/3 → 15/0), Commit 2 → 1 connection with 6–15 fewer statements (smallfile L05 115 → 100). smallfile's read cells L02–L05 also lose 5–6 Exec statements (43 → 38, 50 → 44), the same path as C18 39 → 24.
- **PostgreSQL − SQLite create and mount gaps closed on every machine and suite** (create gap now −40…+19 ms, i.e. PostgreSQL at or below SQLite plus noise, with single-row fsx outliers down to −279 ms; mount +2…+14 ms). Commit gaps are similar in size to round 1 (Docker +20…+63, Lima +17…+59, Apple +17…+56 ms): the remaining Commit cost, as below.
- **Timings are noisier than round 1** (load median 5–6 vs 3–6; tool image `ac383307…` rebuilt from round 1's unchanged context). Both backends slowed together in several single rows (fsx Docker SQLite Exec 194 → 661 ms, fio guest SQLite Exec 340 → 589 ms); native Commit rose on both backends (fio native 76 → 116 SQLite, 84 → 123 PostgreSQL). These are not PostgreSQL-specific; one sample, not rerun. The paired checks (`fp-natpjd`, `fp-fio`) show the round-1-tree control equally affected: campaign conditions, not product.
- **First Sandbox on a fresh machine**: the first SQLite row on each new guest paid a one-off create (C01 Lima 4,225 ms / Apple 3,385 ms; F01 Lima 2,491 / Apple 1,590 ms; native C01 649 ms). Round 1 reused warm machines. Medians absorb it; the rows are kept.

## fs-bench-quick before → after

### Per machine × backend medians, before (ddd1bc83cd) → after (76a32a9a10), ms

Median over the cells that PASS in both campaigns for that machine/arm (count `n`). One sample per row.

<!-- BEGIN quick_medians -->
| machine | backend | n | create | mount | Exec | Commit | unmount |
|---|---|---:|---|---|---|---|---|
| native | sqlite | 18 | 42 → 39 | 38 → 35 | 354 → 417 | 139 → 163 | 32 → 31 |
| native | postgresql | 18 | 44 → 45 | 54 → 42 | 444 → 318 | 175 → 199 | 29 → 27 |
| docker | sqlite | 18 | 334 → 360 | 23 → 16 | 259 → 253 | 85 → 72 | 18 → 16 |
| docker | postgresql | 18 | 386 → 344 | 53 → 24 | 305 → 338 | 145 → 120 | 17 → 16 |
| docker | pg-colocated | 18 | 377 → 337 | 49 → 21 | 262 → 336 | 110 → 91 | 18 → 15 |
| lima | sqlite | 18 | 737 → 693 | 21 → 16 | 219 → 214 | 84 → 63 | 17 → 16 |
| lima | postgresql | 18 | 795 → 696 | 54 → 25 | 228 → 225 | 140 → 103 | 17 → 15 |
| apple-container | sqlite | 18 | 58 → 58 | 18 → 17 | 203 → 188 | 94 → 70 | 14 → 16 |
| apple-container | postgresql | 18 | 125 → 70 | 34 → 25 | 213 → 232 | 144 → 117 | 14 → 15 |
<!-- END quick_medians -->

### PostgreSQL − SQLite median gap per machine, before → after, ms

Median over cells of (PostgreSQL row − SQLite row) for cells where both arms PASS in both campaigns. `coloc` is the Docker co-located arm minus Docker SQLite.

<!-- BEGIN quick_gaps -->
| machine | arm | n | create | mount | Exec | Commit | unmount |
|---|---|---:|---|---|---|---|---|
| native | pg | 18 | +3 → +9 | +15 → +4 | -1 → -15 | +36 → +22 | -4 → -3 |
| docker | pg | 18 | +53 → -7 | +29 → +8 | +6 → +23 | +48 → +36 | -0 → -0 |
| docker | coloc | 18 | +43 → -20 | +27 → +4 | -2 → +36 | +21 → +18 | +0 → -1 |
| lima | pg | 18 | +58 → +2 | +33 → +9 | -1 → +2 | +48 → +35 | -0 → +0 |
| apple-container | pg | 18 | +66 → +8 | +17 → +9 | +3 → +3 | +47 → +43 | -0 → -0 |
<!-- END quick_gaps -->

### pg_stat_statements per phase, Docker PostgreSQL (published port), statements/connections before → after

All 18 cells (#71 showed 11). The daemon's idle reader opens after readiness and before the measured mount marker, so its 1 statement / 1 connection is counted under create (gate-04).

<!-- BEGIN quick_pg_docker -->
| cell | create | mount | Exec | Commit | unmount | follow-up |
|---|---|---|---|---|---|---|
| C01 | 6/2 → 4/3 | 30/3 → 14/0 | 8/0 → 8/0 | 91/2 → 85/1 | 0/0 → 0/0 |  |
| C02 | 6/2 → 4/3 | 30/3 → 14/0 | 8/0 → 8/0 | 91/2 → 85/1 | 0/0 → 0/0 |  |
| C03 | 6/2 → 4/3 | 30/3 → 14/0 | 8/0 → 8/0 | 37/2 → 33/1 | 0/0 → 0/0 |  |
| C04 | 6/2 → 4/3 | 30/3 → 14/0 | 8/0 → 8/0 | 89/2 → 83/1 | 0/0 → 0/0 |  |
| C05 | 6/2 → 4/3 | 30/3 → 14/0 | 8/0 → 8/0 | 89/2 → 83/1 | 0/0 → 0/0 |  |
| C06 | 6/2 → 4/3 | 30/3 → 14/0 | 0/0 → 0/0 | 84/2 → 78/1 | 0/0 → 0/0 |  |
| C07 | 6/2 → 4/3 | 30/3 → 14/0 | 0/0 → 0/0 | 85/2 → 79/1 | 0/0 → 0/0 |  |
| C08 | 6/2 → 4/3 | 30/3 → 14/0 | 0/0 → 0/0 | 84/2 → 78/1 | 0/0 → 0/0 |  |
| C09 | 5/1 → 3/2 | 30/3 → 14/0 | 6/0 → 6/0 | 1/0 → 1/0 | 0/0 → 0/0 |  |
| C10 | 5/1 → 3/2 | 30/3 → 14/0 | 6/0 → 6/0 | 70/2 → 64/1 | 0/0 → 0/0 |  |
| C11 | 5/1 → 3/2 | 30/3 → 14/0 | 4/0 → 4/0 | 38/2 → 34/1 | 0/0 → 0/0 |  |
| C12 | 6/2 → 4/3 | 30/3 → 14/0 | 0/0 → 0/0 | 97/2 → 90/1 | 0/0 → 0/0 |  |
| C13 | 6/2 → 4/3 | 30/3 → 14/0 | 0/0 → 0/0 | 79/2 → 73/1 | 0/0 → 0/0 | Exec 2 0/0 → 0/0; Commit 2 71/0 → 66/0 |
| C14 | 6/2 → 4/3 | 30/3 → 14/0 | 0/0 → 0/0 | 1/0 → 1/0 | 0/0 → 0/0 |  |
| C15 | 6/2 → 4/3 | 30/3 → 14/0 | 0/0 → 0/0 | 81/2 → 74/1 | 0/0 → 0/0 |  |
| C16 | 6/2 → 4/3 | 30/3 → 14/0 | 80/0 → 80/0 | 696/2 → 251/1 | 0/0 → 0/0 |  |
| C17 | 5/1 → 3/2 | 30/3 → 14/0 | 847/0 → 68/0 | 1/0 → 1/0 | 0/0 → 0/0 |  |
| C18 | 5/1 → 3/2 | 32/3 → 16/0 | 39/0 → 24/0 | 1/0 → 1/0 | 0/0 → 0/0 |  |
<!-- END quick_pg_docker -->

Other routes, distinct values over the 18 cells (cell count in parentheses):

<!-- BEGIN quick_pg_route_summary -->
| phase | native | docker | lima | apple | docker coloc |
|---|---|---|---|---|---|
| create | 6/2 (18) → 4/3 (18) | 6/2 (13), 5/1 (5) → 4/3 (13), 3/2 (5) | 6/2 (13), 5/1 (5) → 4/3 (13), 3/2 (5) | 6/2 (13), 5/1 (5) → 4/3 (13), 3/2 (5) | 6/2 (13), 5/1 (5) → 4/3 (13), 3/2 (5) |
| mount | 24/2 (17), 52/2 (1) → 14/0 (17), 27/0 (1) | 30/3 (17), 32/3 (1) → 14/0 (17), 16/0 (1) | 30/3 (17), 32/3 (1) → 14/0 (17), 16/0 (1) | 23/1 (17), 25/1 (1) → 14/0 (17), 16/0 (1) | 30/3 (17), 32/3 (1) → 14/0 (17), 16/0 (1) |
| unmount | 0/0 (18) → 0/0 (18) | 0/0 (18) → 0/0 (18) | 0/0 (18) → 0/0 (18) | 0/0 (18) → 0/0 (18) | 0/0 (18) → 0/0 (18) |
<!-- END quick_pg_route_summary -->

Exec, every PostgreSQL route (cells with statements):

<!-- BEGIN quick_pg_exec_routes -->
| cell | native | docker | lima | apple | docker coloc |
|---|---|---|---|---|---|
| C01 | 8/0 → 8/0 | 8/0 → 8/0 | 8/0 → 8/0 | 8/0 → 8/0 | 8/0 → 8/0 |
| C02 | 8/0 → 8/0 | 8/0 → 8/0 | 8/0 → 8/0 | 8/0 → 8/0 | 8/0 → 8/0 |
| C03 | 8/0 → 8/0 | 8/0 → 8/0 | 8/0 → 8/0 | 8/0 → 8/0 | 8/0 → 8/0 |
| C04 | 8/0 → 8/0 | 8/0 → 8/0 | 8/0 → 8/0 | 8/0 → 8/0 | 8/0 → 8/0 |
| C05 | 8/0 → 8/0 | 8/0 → 8/0 | 8/0 → 8/0 | 8/0 → 8/0 | 8/0 → 8/0 |
| C09 | 6/0 → 6/0 | 6/0 → 6/0 | 6/0 → 6/0 | 6/0 → 6/0 | 6/0 → 6/0 |
| C10 | 6/0 → 6/0 | 6/0 → 6/0 | 6/0 → 6/0 | 6/0 → 6/0 | 6/0 → 6/0 |
| C11 | 4/0 → 4/0 | 4/0 → 4/0 | 4/0 → 4/0 | 4/0 → 4/0 | 4/0 → 4/0 |
| C16 | 80/0 → 80/0 | 80/0 → 80/0 | 80/0 → 80/0 | 80/0 → 80/0 | 80/0 → 80/0 |
| C17 | 847/0 → 68/0 | 847/0 → 68/0 | 876/0 → 68/0 | 847/0 → 68/0 | 847/0 → 68/0 |
| C18 | 13/0 → 13/0 | 39/0 → 24/0 | 39/0 → 24/0 | 39/0 → 24/0 | 39/0 → 24/0 |
<!-- END quick_pg_exec_routes -->

Commit, every PostgreSQL route:

<!-- BEGIN quick_pg_commit_routes -->
| cell | native | docker | lima | apple | docker coloc |
|---|---|---|---|---|---|
| C01 | 91/2 → 85/1 | 91/2 → 85/1 | 91/2 → 85/1 | 91/2 → 85/1 | 91/2 → 85/1 |
| C02 | 91/2 → 85/1 | 91/2 → 85/1 | 91/2 → 85/1 | 91/2 → 85/1 | 91/2 → 85/1 |
| C03 | 37/2 → 33/1 | 37/2 → 33/1 | 37/2 → 33/1 | 37/2 → 33/1 | 37/2 → 33/1 |
| C04 | 89/2 → 83/1 | 89/2 → 83/1 | 89/2 → 83/1 | 89/2 → 83/1 | 89/2 → 83/1 |
| C05 | 89/2 → 83/1 | 89/2 → 83/1 | 89/2 → 83/1 | 89/2 → 83/1 | 89/2 → 83/1 |
| C06 | 84/2 → 78/1 | 84/2 → 78/1 | 84/2 → 78/1 | 84/2 → 78/1 | 84/2 → 78/1 |
| C07 | 85/2 → 79/1 | 85/2 → 79/1 | 85/2 → 79/1 | 85/2 → 79/1 | 85/2 → 79/1 |
| C08 | 84/2 → 78/1 | 84/2 → 78/1 | 84/2 → 78/1 | 84/2 → 78/1 | 84/2 → 78/1 |
| C09 | 1/0 → 1/0 | 1/0 → 1/0 | 1/0 → 1/0 | 1/0 → 1/0 | 1/0 → 1/0 |
| C10 | 70/2 → 64/1 | 70/2 → 64/1 | 70/2 → 64/1 | 70/2 → 64/1 | 70/2 → 64/1 |
| C11 | 38/2 → 34/1 | 38/2 → 34/1 | 38/2 → 34/1 | 38/2 → 34/1 | 38/2 → 34/1 |
| C12 | 97/2 → 90/1 | 97/2 → 90/1 | 97/2 → 90/1 | 97/2 → 90/1 | 97/2 → 90/1 |
| C13 | 79/2 → 73/1 | 79/2 → 73/1 | 79/2 → 73/1 | 79/2 → 73/1 | 79/2 → 73/1 |
| C14 | 1/0 → 1/0 | 1/0 → 1/0 | 1/0 → 1/0 | 1/0 → 1/0 | 1/0 → 1/0 |
| C15 | 81/2 → 74/1 | 81/2 → 74/1 | 81/2 → 74/1 | 81/2 → 74/1 | 81/2 → 74/1 |
| C16 | 686/2 → 251/1 | 696/2 → 251/1 | 685/2 → 251/1 | 690/2 → 251/1 | 699/2 → 251/1 |
| C17 | 1/0 → 1/0 | 1/0 → 1/0 | 1/0 → 1/0 | 1/0 → 1/0 | 1/0 → 1/0 |
| C18 | 1/0 → 1/0 | 1/0 → 1/0 | 1/0 → 1/0 | 1/0 → 1/0 | 1/0 → 1/0 |
<!-- END quick_pg_commit_routes -->

### Storage recorded by Commit (bytes), Docker rows, before → after

`new_stored` / `new_metadata` from the Commit result. The harness records no database file size; no storage-efficiency claim.

<!-- BEGIN quick_storage -->
| cell | SQLite new_stored | PostgreSQL new_stored | coloc new_stored | SQLite new_metadata | PostgreSQL new_metadata | coloc new_metadata |
|---|---|---|---|---|---|---|
| C01 | 18516 → 18515 | 18512 → 18516 | 18516 → 18516 | 9591 → 9590 | 9587 → 9591 | 9591 → 9591 |
| C02 | 18516 → 18521 | 18516 → 18516 | 18516 → 18516 | 9591 → 9596 | 9591 → 9591 | 9591 → 9591 |
| C03 | — → — | — → — | — → — | — → — | — → — | — → — |
| C04 | 8028 → 8033 | 8032 → 8041 | 8032 → 8042 | 8028 → 8033 | 8032 → 8041 | 8032 → 8042 |
| C05 | 8036 → 8042 | 8040 → 8035 | 8029 → 8052 | 8036 → 8042 | 8040 → 8035 | 8029 → 8052 |
| C06 | 748 → 748 | 748 → 748 | 749 → 748 | 672 → 672 | 672 → 672 | 673 → 672 |
| C07 | 832 → 832 | 832 → 832 | 832 → 832 | 756 → 756 | 756 → 756 | 756 → 756 |
| C08 | 748 → 748 | 748 → 748 | 749 → 748 | 672 → 672 | 672 → 672 | 673 → 672 |
| C09 | — → — | — → — | — → — | — → — | — → — | — → — |
| C10 | 300 → 300 | 294 → 300 | 300 → 300 | 300 → 300 | 294 → 300 | 300 → 300 |
| C11 | — → — | — → — | — → — | — → — | — → — | — → — |
| C12 | 26943 → 26942 | 26938 → 26944 | 26951 → 26944 | 6546 → 6547 | 6542 → 6548 | 6555 → 6546 |
| C13 | 319 → 319 | 319 → 319 | 319 → 319 | 280 → 280 | 280 → 280 | 280 → 280 |
| C14 | — → — | — → — | — → — | — → — | — → — | — → — |
| C15 | 1980 → 1983 | 1980 → 1980 | 1981 → 1980 | 1156 → 1159 | 1156 → 1156 | 1157 → 1156 |
| C16 | 186858 → 186864 | 186919 → 186857 | 186857 → 186912 | 87836 → 87842 | 87897 → 87835 | 87835 → 87890 |
| C17 | — → — | — → — | — → — | — → — | — → — | — → — |
| C18 | — → — | — → — | — → — | — → — | — → — | — → — |

- Rows with a Commit result in both campaigns: 108.
- Largest relative `new_metadata` change: +2.04% (C10/docker/postgresql: 294 → 300).
- Largest relative `new_stored` change: +2.04% (C10/docker/postgresql: 294 → 300).
<!-- END quick_storage -->

## Other suites before → after (round-1 final pg71-six at ddd1bc83cd)

Same arms on both sides (co-located arm and observer in both). Medians over cells that PASS in both; mount and unmount now have a before value too.

<!-- BEGIN six_medians -->
| suite | machine | backend | rows PASS before → after | create | mount | Exec | Commit | unmount |
|---|---|---|---|---|---|---|---|---|
| fio | native | sqlite | 4/4 → 4/4 | 32 → 44 | 34 → 37 | 474 → 475 | 76 → 116 | 28 → 31 |
| fio | native | postgresql | 4/4 → 4/4 | 43 → 45 | 46 → 41 | 466 → 472 | 84 → 123 | 25 → 27 |
| fio | docker | sqlite | 4/4 → 4/4 | 287 → 418 | 20 → 19 | 520 → 645 | 42 → 43 | 16 → 18 |
| fio | docker | postgresql | 4/4 → 4/4 | 307 → 407 | 44 → 28 | 511 → 632 | 63 → 63 | 15 → 18 |
| fio | docker | pg-colocated | 4/4 → 4/4 | 303 → 405 | 42 → 24 | 506 → 622 | 44 → 52 | 15 → 19 |
| fio | lima | sqlite | 4/4 → 4/4 | 727 → 701 | 22 → 19 | 340 → 589 | 31 → 42 | 14 → 18 |
| fio | lima | postgresql | 4/4 → 4/4 | 780 → 700 | 46 → 26 | 343 → 463 | 51 → 59 | 14 → 17 |
| fio | apple-container | sqlite | 4/4 → 4/4 | 73 → 66 | 18 → 18 | 348 → 597 | 61 → 61 | 15 → 18 |
| fio | apple-container | postgresql | 4/4 → 4/4 | 130 → 65 | 36 → 28 | 363 → 474 | 72 → 65 | 14 → 16 |
| smallfile | native | sqlite | 5/5 → 5/5 | 26 → 44 | 34 → 39 | 3745 → 3798 | 61 → 106 | 28 → 37 |
| smallfile | native | postgresql | 5/5 → 5/5 | 42 → 47 | 46 → 46 | 3772 → 3791 | 88 → 144 | 26 → 33 |
| smallfile | docker | sqlite | 5/5 → 5/5 | 264 → 400 | 19 → 19 | 3676 → 3780 | 33 → 44 | 15 → 15 |
| smallfile | docker | postgresql | 5/5 → 5/5 | 305 → 406 | 43 → 30 | 3696 → 3765 | 81 → 101 | 14 → 16 |
| smallfile | docker | pg-colocated | 5/5 → 5/5 | 299 → 403 | 42 → 24 | 3686 → 3709 | 52 → 62 | 15 → 16 |
| smallfile | lima | sqlite | 5/5 → 5/5 | 738 → 693 | 18 → 19 | 3740 → 3851 | 30 → 43 | 13 → 16 |
| smallfile | lima | postgresql | 5/5 → 5/5 | 782 → 699 | 48 → 27 | 3752 → 3864 | 78 → 96 | 13 → 16 |
| smallfile | apple-container | sqlite | 5/5 → 5/5 | 68 → 57 | 18 → 17 | 3797 → 3848 | 56 → 57 | 13 → 13 |
| smallfile | apple-container | postgresql | 5/5 → 5/5 | 120 → 64 | 40 → 28 | 3826 → 3867 | 123 → 123 | 12 → 14 |
| mdtest | native | sqlite | 2/2 → 2/2 | 39 → 44 | 37 → 39 | 1505 → 1775 | 40 → 84 | 29 → 35 |
| mdtest | native | postgresql | 2/2 → 2/2 | 41 → 50 | 50 → 43 | 1465 → 1659 | 55 → 115 | 22 → 30 |
| mdtest | docker | sqlite | 0/2 → 0/2 | — | — | — | — | — |
| mdtest | docker | postgresql | 0/2 → 0/2 | — | — | — | — | — |
| mdtest | docker | pg-colocated | 0/2 → 0/2 | — | — | — | — | — |
| mdtest | lima | sqlite | 0/2 → 0/2 | — | — | — | — | — |
| mdtest | lima | postgresql | 0/2 → 0/2 | — | — | — | — | — |
| mdtest | apple-container | sqlite | 0/2 → 0/2 | — | — | — | — | — |
| mdtest | apple-container | postgresql | 0/2 → 0/2 | — | — | — | — | — |
| fsx | native | sqlite | 1/1 → 1/1 | 42 → 39 | 38 → 40 | 260 → 382 | 49 → 82 | 29 → 29 |
| fsx | native | postgresql | 1/1 → 1/1 | 41 → 59 | 46 → 48 | 248 → 363 | 81 → 127 | 26 → 26 |
| fsx | docker | sqlite | 1/1 → 1/1 | 302 → 903 | 21 → 19 | 194 → 661 | 17 → 20 | 18 → 17 |
| fsx | docker | postgresql | 1/1 → 1/1 | 315 → 624 | 49 → 34 | 189 → 639 | 53 → 83 | 15 → 17 |
| fsx | docker | pg-colocated | 1/1 → 1/1 | 325 → 755 | 43 → 25 | 190 → 241 | 35 → 39 | 17 → 19 |
| fsx | lima | sqlite | 1/1 → 1/1 | 743 → 717 | 25 → 19 | 187 → 271 | 44 → 19 | 17 → 16 |
| fsx | lima | postgresql | 1/1 → 1/1 | 788 → 692 | 63 → 27 | 210 → 225 | 57 → 78 | 16 → 17 |
| fsx | apple-container | sqlite | 1/1 → 1/1 | 63 → 63 | 17 → 18 | 208 → 254 | 13 → 16 | 13 → 13 |
| fsx | apple-container | postgresql | 1/1 → 1/1 | 132 → 75 | 36 → 27 | 199 → 293 | 53 → 51 | 10 → 12 |
| fsstress | native | sqlite | 1/1 → 1/1 | 42 → 44 | 36 → 41 | 317 → 419 | 153 → 228 | 30 → 39 |
| fsstress | native | postgresql | 1/1 → 1/1 | 67 → 46 | 61 → 45 | 347 → 421 | 184 → 266 | 25 → 34 |
| fsstress | docker | sqlite | 0/1 → 0/1 | — | — | — | — | — |
| fsstress | docker | postgresql | 0/1 → 0/1 | — | — | — | — | — |
| fsstress | docker | pg-colocated | 0/1 → 0/1 | — | — | — | — | — |
| fsstress | lima | sqlite | 0/1 → 0/1 | — | — | — | — | — |
| fsstress | lima | postgresql | 0/1 → 0/1 | — | — | — | — | — |
| fsstress | apple-container | sqlite | 0/1 → 0/1 | — | — | — | — | — |
| fsstress | apple-container | postgresql | 0/1 → 0/1 | — | — | — | — | — |
| pjdfstest | native | sqlite | 4/4 → 4/4 | 40 → 46 | 34 → 41 | 225 → 264 | 57 → 98 | 28 → 31 |
| pjdfstest | native | postgresql | 4/4 → 4/4 | 43 → 47 | 46 → 43 | 190 → 224 | 68 → 93 | 25 → 28 |
| pjdfstest | docker | sqlite | 4/4 → 4/4 | 282 → 427 | 19 → 20 | 121 → 161 | 14 → 16 | 13 → 17 |
| pjdfstest | docker | postgresql | 4/4 → 4/4 | 310 → 427 | 46 → 28 | 105 → 131 | 35 → 40 | 13 → 16 |
| pjdfstest | docker | pg-colocated | 4/4 → 4/4 | 324 → 426 | 45 → 22 | 125 → 118 | 24 → 26 | 14 → 17 |
| pjdfstest | lima | sqlite | 4/4 → 4/4 | 739 → 694 | 20 → 19 | 95 → 124 | 13 → 16 | 13 → 16 |
| pjdfstest | lima | postgresql | 4/4 → 4/4 | 769 → 712 | 47 → 27 | 72 → 94 | 34 → 38 | 13 → 15 |
| pjdfstest | apple-container | sqlite | 4/4 → 4/4 | 68 → 62 | 17 → 18 | 100 → 124 | 13 → 13 | 12 → 12 |
| pjdfstest | apple-container | postgresql | 4/4 → 4/4 | 134 → 75 | 38 → 27 | 99 → 123 | 68 → 40 | 13 → 12 |
<!-- END six_medians -->

PostgreSQL − SQLite, median of per-cell differences (cells where both arms PASS in both campaigns), ms:

<!-- BEGIN six_gaps -->
| suite | machine | arm | n | create | mount | Exec | Commit |
|---|---|---|---:|---|---|---|---|
| fio | native | pg | 4 | +10 → -1 | +11 → +2 | -9 → -6 | +11 → +5 |
| fio | docker | pg | 4 | +26 → -2 | +23 → +9 | -5 → -23 | +27 → +20 |
| fio | docker | coloc | 4 | +23 → -14 | +22 → +4 | -7 → -21 | +3 → +9 |
| fio | lima | pg | 4 | +44 → -1 | +26 → +8 | +2 → -6 | +20 → +17 |
| fio | apple-container | pg | 4 | +64 → -3 | +19 → +11 | +16 → +0 | +11 → +17 |
| smallfile | native | pg | 5 | +14 → +2 | +13 → +4 | +6 → +3 | +23 → +29 |
| smallfile | docker | pg | 5 | +43 → +7 | +24 → +12 | +17 → +4 | +43 → +59 |
| smallfile | docker | coloc | 5 | +32 → -6 | +24 → +5 | +9 → -33 | +18 → +18 |
| smallfile | lima | pg | 5 | +42 → +7 | +31 → +8 | +24 → +17 | +46 → +46 |
| smallfile | apple-container | pg | 5 | +63 → +7 | +20 → +11 | +66 → +23 | +67 → +56 |
| mdtest | native | pg | 2 | +2 → +6 | +12 → +4 | -40 → -116 | +15 → +30 |
| fsx | native | pg | 1 | -1 → +19 | +8 → +8 | -12 → -18 | +32 → +45 |
| fsx | docker | pg | 1 | +13 → -279 | +28 → +14 | -5 → -22 | +36 → +63 |
| fsx | docker | coloc | 1 | +22 → -148 | +22 → +6 | -3 → -421 | +17 → +19 |
| fsx | lima | pg | 1 | +45 → -25 | +38 → +8 | +23 → -46 | +13 → +59 |
| fsx | apple-container | pg | 1 | +69 → +12 | +20 → +9 | -9 → +39 | +41 → +35 |
| fsstress | native | pg | 1 | +26 → +2 | +25 → +4 | +30 → +2 | +32 → +39 |
| pjdfstest | native | pg | 4 | +3 → +3 | +12 → +2 | +5 → -13 | +15 → -9 |
| pjdfstest | docker | pg | 4 | +31 → -40 | +27 → +9 | -11 → -34 | +22 → +24 |
| pjdfstest | docker | coloc | 4 | +40 → +15 | +27 → +3 | -8 → -43 | +11 → +10 |
| pjdfstest | lima | pg | 4 | +28 → +16 | +27 → +9 | -16 → -20 | +22 → +21 |
| pjdfstest | apple-container | pg | 4 | +65 → +14 | +19 → +11 | -5 → -12 | +54 → +28 |
<!-- END six_gaps -->

pg_stat_statements per phase, Docker PostgreSQL (published), statements/connections before → after:

<!-- BEGIN six_pg_docker -->
| suite cell | create | mount | Exec | Commit | unmount | follow-up |
|---|---|---|---|---|---|---|
| fio F01 | 6/2 → 4/3 | 30/3 → 14/0 | 0/0 → 0/0 | 84/2 → 78/1 | 0/0 → 0/0 |  |
| fio F02 | 5/1 → 3/2 | 30/3 → 14/0 | 6/0 → 6/0 | 1/0 → 1/0 | 0/0 → 0/0 |  |
| fio F03 | 6/2 → 4/3 | 30/3 → 14/0 | 0/0 → 0/0 | 67/2 → 61/1 | 0/0 → 0/0 |  |
| fio F04 | 5/1 → 3/2 | 30/3 → 14/0 | 5/0 → 5/0 | 1/0 → 1/0 | 0/0 → 0/0 |  |
| smallfile L01 | 6/2 → 4/3 | 30/3 → 14/0 | 0/0 → 0/0 | 98/2 → 91/1 | 0/0 → 0/0 |  |
| smallfile L02 | 5/1 → 3/2 | 31/3 → 15/0 | 43/0 → 38/0 | 84/2 → 74/1 | 0/0 → 0/0 |  |
| smallfile L03 | 5/1 → 3/2 | 31/3 → 15/0 | 42/0 → 37/0 | 84/2 → 74/1 | 0/0 → 0/0 |  |
| smallfile L04 | 5/1 → 3/2 | 31/3 → 15/0 | 50/0 → 44/0 | 102/2 → 92/1 | 0/0 → 0/0 |  |
| smallfile L05 | 5/1 → 3/2 | 31/3 → 15/0 | 42/0 → 37/0 | 115/2 → 100/1 | 0/0 → 0/0 |  |
| mdtest M01 | NOT_RUN → NOT_RUN | NOT_RUN → NOT_RUN | NOT_RUN → NOT_RUN | NOT_RUN → NOT_RUN | NOT_RUN → NOT_RUN |  |
| mdtest M02 | NOT_RUN → NOT_RUN | NOT_RUN → NOT_RUN | NOT_RUN → NOT_RUN | NOT_RUN → NOT_RUN | NOT_RUN → NOT_RUN |  |
| fsx X01 | 6/2 → 4/3 | 30/3 → 14/0 | 0/0 → 0/0 | 67/2 → 61/1 | 0/0 → 0/0 |  |
| fsstress S01 | FAIL → FAIL | FAIL → FAIL | FAIL → FAIL | FAIL → FAIL | FAIL → FAIL |  |
| pjdfstest P01 | 6/2 → 4/3 | 30/3 → 14/0 | 0/0 → 0/0 | 37/2 → 33/1 | 0/0 → 0/0 |  |
| pjdfstest P02 | 6/2 → 4/3 | 30/3 → 14/0 | 0/0 → 0/0 | 37/2 → 33/1 | 0/0 → 0/0 |  |
| pjdfstest P03 | 6/2 → 4/3 | 30/3 → 14/0 | 0/0 → 0/0 | 37/2 → 33/1 | 0/0 → 0/0 |  |
| pjdfstest P04 | 6/2 → 4/3 | 30/3 → 14/0 | 0/0 → 0/0 | 37/2 → 33/1 | 0/0 → 0/0 |  |
<!-- END six_pg_docker -->

## Paired attribution (`final-pair`)

The unpaired before → after comparison showed three shifts that are not PostgreSQL gaps, and native was never gated. Four paired gates (`gate.py`, the round-2 gate procedure: control `b4fa173e40` gatebuild-warm artifacts, the same tree as round 1's `ddd1bc83cd`, vs the final `76a32a9a10`; control and treatment alternating, two paired rounds, fresh homes/workers/databases, one row per command, counts first, aggregate rule as the timing verdict, per-row 2-pair flags diagnostic) ran after the campaign on the same host, 72 rows, all PASS and cleaned up. Summaries: `~/.cache/pg-perf-r2/bench/<gate>/summary.md`; receipts `fs-bench-quick/results/pg-r2-gate/<gate>/`.

| gate | machine, suite, cells, arms | rows | load | aggregate verdict | identity medians, control → treatment (ms) | round 1 → unpaired final (ms) | attribution |
|---|---|---:|---|---|---|---|---|
| `fp-natq` | native, fs-bench-quick C01 C09 C13, SQLite + PostgreSQL | 24 | 6.6–11.4 | no flag | Commit SQLite 119 → 113, PostgreSQL 153 → 123 | native Commit SQLite 139 → 163, PostgreSQL 175 → 199 (18-cell medians) | **campaign conditions**: the control (round-1 tree) is as slow as the treatment |
| `fp-natpjd` | native, pjdfstest P01–P04, SQLite + PostgreSQL | 32 | 3.8–5.6 | no flag | Commit SQLite 106 → 94, PostgreSQL 115 → 108 | pjdfstest native SQLite Commit 49–64 → 91–115 | **campaign conditions**: the control shows the same +40–55 ms; treatment is level or faster |
| `fp-fio` | Docker, fio F01 on the six-suite tool image, SQLite + PostgreSQL | 8 | 4.7–7.1 | no flag | create SQLite 368 → 356, PostgreSQL 426 → 372 | F01 Docker create SQLite 303 → 371, PostgreSQL 346 → 374 | **campaign conditions** (fresh worker on the rebuilt tool image, host): the control has the same higher create |
| `fp-c06` | Docker, fs-bench-quick C06, SQLite + PostgreSQL | 8 | 7.0–7.5 | no flag | Exec SQLite 239 → 229, PostgreSQL 223 → 242 | C06 Docker Exec SQLite 190 → 516, PostgreSQL 203 → 700 | **host load** during the final's write cells (C06 ran at load 13.7): paired at load 7 both identities are near round 1 |

- Counts in every paired row match the campaign: native create 6/2 → 4/3, mount 24/2 → 14/0, Commit 2 → 1 connection (pjdfstest 37/2 → 33/1, C01 91/2 → 85/1); Docker F01 Commit 84/2 → 78/1, mount 30/3 → 14/0.
- Per-row 2-pair flags (diagnostic): `fp-natq` C09/sqlite/unmount +8 ms; `fp-natpjd` P01/sqlite/unmount +6 ms, P03/postgresql/commit +51 ms (control 109/148, treatment 146/212; the other three pjdfstest cells' PostgreSQL Commit are level or faster and the aggregate PostgreSQL Commit is −4.0 ms), P03/postgresql/unmount +9 ms; `fp-fio` and `fp-c06` none. Native has no A/A reference, so these are not cross-checked.
- **Verdict: none of the three shifts is a product change.** The product effect at the final head is the counts and the PostgreSQL create/mount/Commit savings above; native's higher Commit, Docker's higher create on the tool image and the C06 Exec rise are campaign conditions (host state, fresh workers/image, load), present in the round-1-tree control as well.

## Round-2 changes (`b4fa173e40` → `76a32a9a10`)

Production LOC 139,048 → 139,821 (delta +773), first-parent merges, `tools/production_loc.py`. Every merge passed a Docker-subset paired gate (counts first; aggregate timing rule: FLAG if median relative delta > 15% and > 5 ms and ≥ 12/16 pairs slower).

| merge | issue | commits | change | LOC | counts at its gate (Docker PG, control → treatment) |
|---|---|---|---|---:|---|
| `eefa936f08` | #64 A | `7af41a4eb7` | forwarded mount reads project + Branch on the CLI's held PostgreSQL session | +53 | mount 30/3 → 24/2 (gate-01/02) |
| `499078be5c` | #97 | `b9093b61d2` | 8 MiB read-ahead window fetched in one demand; 16 MiB per-reader cap; pack cohorts | +185 | C17 Exec 847 → 847: not effective live (gate-01) |
| `435f0a99ad` | #94 | `eba818e303` | per-step PostgreSQL attribution test, Commit phase marks (instrumentation) | +19 | — |
| `90bad45a7b` | #96, #66 | `2399fdb3c3`, `3a676c8f65` | no TLS connector for `sslmode=disable` (first open ~50 → ~8 ms); provider-command exit seen when it ends, not at a 20 ms poll step | +7 | create 6/2 unchanged (cost, not round trips) |
| `7832f3686d` | #95 | `617ee1f166`, `ad6afd11a9` | validate a Commit on its Workspace's reader; Commit/Layer by id in one statement | +8 | Commit 2 → 1 connection, −6 statements (gate-03) |
| `2bb6782b9d` | #97 | `910f686c5a` | follow read-ahead streams in the Store's shared cache state, not per request | +10 | C17 Exec 847 → 68 (gate-03, 03x) |
| `55f9b45323` | #64 B + idle reader | `9962df8d29`, `ed797caaf7` | daemon binds a mount by Branch name in one statement; one idle Store reader opened after readiness (pool cap 4, failure recorded, not retried) | +285 | mount 24/2 → 14/0; create +1/+1 (idle reader) (gate-04) |
| `ca5e0b8804` | #95 | `61748eb674` | difference walk reads the pages it will expand in batched demands (≤ 128 pages, 1 MiB) | +65 | C16 Commit ~690 → 363 (gate-04) |
| `91198bf24f` | #64 | `f773d9b8c1` | daemon tests adapted to `BindIntent` (tests only) | 0 | gate-04: 96/96 PASS, no flag |
| `dee3eecc1b` | #96 | `3d0e82acc3` | find a LayerStack by name in one PostgreSQL statement | +4 | create 7/3 → 4/3 (C09/C17/C18 6/2 → 3/2) (gate-05) |
| `76a32a9a10` | #95 | `723b9573f5` | look up a demand's pooled-leaf values together | +137 | C16 Commit 363 → 251 (gate-05) |

Owner decisions (2026-11-06): #64 option B and the eager idle reader approved; #95 "no held lane when unmoved" (`5ddaf6d673`) rejected and not merged (evidence branch `pg-r2-commit-unheld-lane`). Not done: pipelining (the sync `postgres` client exposes no pipeline), recording `host.docker.internal`'s address (~0.6 ms per connect, under the 5 ms rule). Gates: gate-01 94/96 (two C16 rows hit the 25 s budget at load up to 44; released), gate-02 96/96, gate-03 92/96 + gate-03x 4/4 (rows 81–84 NOT_RUN: Docker VM disk full), gate-04 96/96, gate-05 96/96; no aggregate flag after gate-01 (its SQLite mount +5.7 ms flag did not reappear).

## Remaining gap attribution

Docker only (the one machine with both PostgreSQL routes): route cost = published − co-located; Store cost = co-located − SQLite; their sum is the published gap (medians of per-cell differences, so the rows need not add exactly). Cells where all three arms PASS in both campaigns, ms.

<!-- BEGIN attribution -->
| Docker component | n | create | mount | Exec | Commit | unmount |
|---|---:|---|---|---|---|---|
| route (published − co-located) | 18 | +9 → -6 | +4 → +5 | +1 → -5 | +28 → +22 | -0 → -0 |
| Store (co-located − SQLite) | 18 | +43 → -20 | +27 → +4 | -2 → +36 | +21 → +18 | +0 → -1 |
| total (published − SQLite) | 18 | +53 → -7 | +29 → +8 | +6 → +23 | +48 → +36 | -0 → -0 |
<!-- END attribution -->

- **Create and mount gaps are closed.** Create is now at or below SQLite on both Docker routes (route −6, Store −20 ms). Mount keeps about 5 ms of route cost and 4 ms of Store cost. 14 statements still run on the Workspace's own reader; the mount connection is pre-opened.
- **Commit is the remaining PostgreSQL cost: about +22 ms of route and +18 ms of Store on Docker** (round 1: +28 / +21). The route part fits round trips: a typical Commit runs 73–90 statements on one connection, at a published-route `SELECT 1` of about 0.2–0.35 ms each (round-1 calibration). Round-2 calibration: NOT_RUN (`pgr2b-pg` has no trust-authenticated calibration role; the gap attribution uses the co-located arm instead). Fewer round trips (pipelining) would need an async client (#95 note). The co-located Store part is server work and is unchanged within noise.
- **Exec (Docker):** see the observation above; no PostgreSQL statements were added and the route component is −5 ms.

- **Apple Container create gap (#66):** +66 → +8 ms (median of 18 per-cell differences; PostgreSQL create 125 → 70 ms, SQLite 58 → 58). Round 1 left +65 ms (#71 started at +203). #66 measured one `container inspect` per create at ~44 ms (~26 ms the CLI's XPC call, ~17 ms the 20 ms exit poll); at `b4fa173e40` it runs only when the machine record lacks the gateway, and `3a676c8f65` removes the poll quantization from every provider call.
- **SQLite create vs round 1:** gate-05 showed SQLite create +36 ms (+7.2%, 11/16 pairs slower) against the control, under the aggregate threshold (gate-04: −24 ms on the same arm). Final campaign, per machine (cells PASS in both; delta = median of per-cell after − before). Docker SQLite create is +31 ms (11/18 cells slower) at a load median about twice round 1's. The other machines are flat or faster, and no SQLite create code changed (#96 is PostgreSQL-only). This is worth one look, not a regression claim:

<!-- BEGIN sqlite_create -->
| machine | n | SQLite create median, round 1 → round 2 | median per-cell delta | cells slower |
|---|---:|---|---|---|
| native | 18 | 42 → 39 | -4 | 6/18 |
| docker | 18 | 334 → 360 | +31 | 11/18 |
| lima | 18 | 737 → 693 | -51 | 2/18 |
| apple-container | 18 | 58 → 58 | +1 | 11/18 |
<!-- END sqlite_create -->

## Host load (1-minute, at row start)

<!-- BEGIN load -->
| suite | side, campaign | rows | min | median | max |
|---|---|---:|---:|---:|---:|
| fs-bench-quick | before `pg71-final-1106` | 162 | 3.5 | 4.5 | 6.0 |
| fs-bench-quick | after `pgr2-final-1106` | 162 | 5.3 | 9.1 | 29.0 |
| fio | before `pg71-fio-1106` | 36 | 2.5 | 3.2 | 3.6 |
| fio | after `pgr2-fio-1106` | 36 | 4.9 | 6.2 | 7.8 |
| smallfile | before `pg71-sf-1106` | 45 | 3.0 | 3.7 | 4.7 |
| smallfile | after `pgr2-sf-1106` | 45 | 4.0 | 5.6 | 7.2 |
| mdtest | before `pg71-md-1106` | 4 | 2.9 | 2.9 | 2.9 |
| mdtest | after `pgr2-md-1106` | 4 | 3.4 | 3.8 | 4.1 |
| fsx | before `pg71-fsx-1106` | 9 | 2.9 | 3.5 | 3.8 |
| fsx | after `pgr2-fsx-1106` | 9 | 3.9 | 4.6 | 4.8 |
| fsstress | before `pg71-fss-1106` | 9 | 4.0 | 4.7 | 4.8 |
| fsstress | after `pgr2-fss-1106` | 9 | 4.4 | 5.1 | 5.1 |
| pjdfstest | before `pg71-pjd-1106` | 36 | 4.9 | 5.8 | 7.3 |
| pjdfstest | after `pgr2-pjd-1106` | 36 | 4.4 | 5.9 | 7.8 |
<!-- END load -->

## Inputs read

<!-- BEGIN sources -->
- fs-bench-quick: before pg71-final-1106; after pgr2-final-1106 (162 rows read)
- fio: before pg71-fio-1106; after pgr2-fio-1106 (36 rows read)
- smallfile: before pg71-sf-1106; after pgr2-sf-1106 (45 rows read)
- mdtest: before pg71-md-1106; after pgr2-md-1106 (18 rows read)
- fsx: before pg71-fsx-1106; after pgr2-fsx-1106 (9 rows read)
- fsstress: before pg71-fss-1106; after pgr2-fss-1106 (9 rows read)
- pjdfstest: before pg71-pjd-1106; after pgr2-pjd-1106 (36 rows read)
<!-- END sources -->

## Resources kept (owner=pg-perf-r2) and release commands

- PostgreSQL server `pgr2b-pg` and volume `pgr2b-pg-data` (all row databases `r2f_*`, `r2s_*`, gate databases already dropped): kept until the coordinator releases round 2; release `docker rm -f pgr2b-pg; docker volume rm pgr2b-pg-data`.
- Machines in `LAYERFS_HOME=~/.cache/pg-perf-r2/bench/final/home` (CLI `~/.cache/pg-perf-r2/bench/artifacts/76a32a9a10/layerfs`, `XDG_CACHE_HOME=~/.cache/pg-perf-r2/bench/final/xdg`): `machine remove pgr2b-lima`, `pgr2b-apple`, `pgr2b-lima6`, `pgr2b-apple6`; `machine stop docker`. Released after this report (see the handoff).
- Tool image `pgr2b-six-tools:20261106` (`ac383307…`) and its archive `~/.cache/pg-perf-r2/bench/final/tools-image/tools-image.tar`: removed after the machines.
- Receipts stay local and untracked: `fs-bench-quick/results/pgr2-final-1106/`, `<suite>/results/pgr2-six-1106/`.
