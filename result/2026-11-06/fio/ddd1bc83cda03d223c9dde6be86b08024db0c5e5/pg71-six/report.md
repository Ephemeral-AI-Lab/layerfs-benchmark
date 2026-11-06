# fio — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: INCOMPLETE.** 36 registered rows; execution {'PASS': 36}. Final infrastructure cleanup: **INCOMPLETE**.

LayerFS `ddd1bc83cda03d223c9dde6be86b08024db0c5e5` (branch `pg-perf` at `ddd1bc83cd` (worktree layerfs-pg-perf, read-only source); 28 commits after the baseline b919f50eaf). Harness: `c731387` (branch `pg-perf-62`, local, unpushed); suite harness unchanged since the published 2026-11-06 run apart from the shared runner arms/observer of #62. Built from `ddd1bc83cd` through the worktree launcher, release profile: macOS CLI and daemon with `layerfs-node/postgresql` (build `build-macos-ecee12a823984af49e8d4d9cfa169268`; CLI sha256 `04a4c120…88ee`, daemon `0472e2a6…c7ceef`) and the Linux aarch64 bundle with PostgreSQL (bundle hash `4c7499ce…dabc45f`, sealed with the baseline Sandbox image `66aeb6bb…` so the guest image matches). Copied into a private cache after SHA-256 checks. Machines: native, docker worker (image = Sandbox image + /opt/fs-six-tools, `pg71-six-tools:20261106` 88f1d872…), fresh Lima `pg71-lima6` and Apple Container `pg71-apple6` created from that image; same PostgreSQL 17.11 server and settings (`pg_settings` dump identical).

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 36}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Close is Sandbox close; Store release is Store remove (SQLite) or disconnect (PostgreSQL). End-to-end is the sum of the measured calls from create through Store release, without harness gaps; it excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: macOS 26.4.1, Apple M3 Max, 14 CPUs, 36 GiB; Docker Desktop 29.5.2 VM 8 CPUs / 7.75 GiB shared with other agents' Rust builds and another benchmark campaign; Lima `pg71-lima6` and Apple Container `pg71-apple6` 2 CPUs / 2 GiB each; PostgreSQL 17.11 container `pgbench-pg` 2 CPUs / 2 GiB. Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

## #71 final verification notes

- All 36 rows PASS. Tool rates are in the per-case tables; F02/F04 (committed reads of a repeating pattern) need 5–6 statements in Exec.

Before = the published 2026-11-06 run at b919f50eaf (`result/2026-11-06/fio/b919f50eaf…/report.md`): different machines (fresh then, reused now), no co-located arm, no PostgreSQL observer, load and first-touch effects differ; one sample per row on both sides. Medians over cells that PASS in both.

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

| suite | machine | PG−SQLite create before → after | Exec | Commit |
|---|---|---|---|---|
| fio | native | +48 → +10 | +17 → -9 | +37 → +11 |
| fio | docker | +166 → +26 | +0 → -5 | +4 → +27 |
| fio | lima | +169 → +44 | -7 → +2 | +28 → +20 |
| fio | apple-container | +221 → +64 | +18 → +16 | +64 → +11 |

pg_stat_statements per phase, Docker PostgreSQL (statements/connections):

| suite cell | create | mount | Exec | Commit |
|---|---|---|---|---|
| fio F01 | 6/2 | 30/3 | 0/0 | 84/2 |
| fio F02 | 5/1 | 30/3 | 6/0 | 1/0 |
| fio F03 | 6/2 | 30/3 | 0/0 | 67/2 |
| fio F04 | 5/1 | 30/3 | 5/0 | 1/0 |

## PostgreSQL minus SQLite

Median over cells of (PostgreSQL arm − SQLite) per machine, milliseconds, using only cells where both rows passed. Close is Sandbox close; Store release is `store disconnect` (PostgreSQL) versus `store remove` (SQLite), which the product does not unify.

| Machine | Arm | Cells | Create | Mount | Exec | Commit | Unmount | Close | Store release | End-to-end |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 | +26.1 | +23.2 | -5.3 | +27.4 | -2.1 | -11.4 | -8.2 | +64.6 |
| docker | pg-colocated | 4 | +23.0 | +22.0 | -7.2 | +3.4 | -1.4 | +13.1 | -7.3 | +61.0 |
| native | postgresql | 4 | +9.6 | +10.7 | -9.1 | +11.1 | -5.0 | -3.6 | -3.1 | -6.3 |
| lima | postgresql | 4 | +43.9 | +26.4 | +2.1 | +19.8 | +0.0 | -3.8 | -7.8 | +63.1 |
| apple-container | postgresql | 4 | +64.1 | +18.5 | +16.3 | +11.1 | -0.2 | -0.4 | -6.9 | -40.0 |

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `04a4c1202d0fab8ce2be764122a2637824e6a59d1030f05f9704eaecbc2f88ee` |
| Native daemon | `0472e2a60075008f79f34304d2c7669d7f47846c5fda36847d0ef34711c7ceef` |
| Linux bundle seal | `4c7499ceac02b7e471cb014c2f12404837421ed61c89b1c6e3a6e5c33dabc45f` |
| Docker tool image | `sha256:88f1d8720fec4f50f876bc9266ce8b76bbbcdab8aa857722c769f29d87d9d14c` |
| Namespace archive config | `sha256:504b072822cb4dad540ccb93f3e0e3d02d9225944b6857478d4d306e7e8a1861` |

## F01

Sequential write: 64 MiB, 1024 KiB blocks; buffered synchronous engine, one job/depth 1, seed 1, nonzero 0x5a pattern. fio-buffered-single-pass-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 3.64 | 303.18 | 18.83 | 633.71 | 217.43 | 21.01 | 227.31 | 12.89 | 1434.36 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 3.43 | 345.76 | 45.10 | 662.02 | 288.71 | 18.98 | 197.55 | 8.38 | 1566.50 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 3.43 | 301.36 | 42.94 | 667.71 | 250.30 | 18.15 | 215.39 | 7.90 | 1503.74 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 3.50 | 54.01 | 41.45 | 680.25 | 286.95 | 38.76 | 60.55 | 8.66 | 1170.63 | 1.07 | 1.32 | 0.82 |
| native | postgresql | PASS | COMPLETE | 3.50 | 43.01 | 49.79 | 596.63 | 331.73 | 26.86 | 52.77 | 6.98 | 1107.76 | 0.90 | 1.15 | 0.71 |
| lima | sqlite | PASS | COMPLETE | 3.23 | 2105.87 | 23.39 | 346.69 | 206.45 | 17.76 | 156.17 | 18.77 | 2875.11 | 0.55 | 0.95 | 2.00 |
| lima | postgresql | PASS | COMPLETE | 3.13 | 804.84 | 59.93 | 345.38 | 251.75 | 17.46 | 118.05 | 7.64 | 1605.05 | 0.52 | 0.87 | 1.02 |
| apple-container | sqlite | PASS | COMPLETE | 3.13 | 873.85 | 17.87 | 345.69 | 220.63 | 44.20 | 601.75 | 12.03 | 2116.02 | 0.55 | 1.01 | 1.48 |
| apple-container | postgresql | PASS | COMPLETE | 3.04 | 128.40 | 40.35 | 598.42 | 276.03 | 12.26 | 34.74 | 7.00 | 1097.21 | 0.90 | 0.96 | 0.70 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 120 | 7 | 4.3 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 0 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 120 | 7 | 3.6 |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 114 | 6 | 3.4 |
| lima | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 120 | 7 | 4.3 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 0 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 113 | 5 | 3.2 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | I/O MiB | I/O count | MiB/s | IOPS | Mean completion μs |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / sqlite | 64.00 | 64 | 365.71 | 365.71 | 2711.75 |
| docker / postgresql | 64.00 | 64 | 470.59 | 470.59 | 2107.24 |
| docker / pg-colocated | 64.00 | 64 | 474.07 | 474.07 | 2080.85 |
| native / sqlite | 64.00 | 64 | 492.31 | 492.31 | 1980.17 |
| native / postgresql | 64.00 | 64 | 488.55 | 488.55 | 2005.61 |
| lima / sqlite | 64.00 | 64 | 587.16 | 587.16 | 1683.75 |
| lima / postgresql | 64.00 | 64 | 592.59 | 592.59 | 1669.93 |
| apple-container / sqlite | 64.00 | 64 | 496.12 | 496.12 | 1988.68 |
| apple-container / postgresql | 64.00 | 64 | 492.31 | 492.31 | 1993.61 |

## F02

Sequential read: 64 MiB, 1024 KiB blocks; buffered synchronous engine, one job/depth 1, seed 1, nonzero 0x5a pattern. fio-buffered-single-pass-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 3.23 | 284.13 | 19.85 | 406.58 | 13.28 | 16.42 | 206.57 | 18.07 | 964.90 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 3.34 | 291.24 | 43.55 | 377.39 | 39.84 | 14.31 | 212.67 | 7.42 | 986.43 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 3.46 | 292.82 | 41.91 | 375.09 | 12.06 | 16.28 | 213.33 | 8.59 | 960.07 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 3.50 | 24.08 | 33.03 | 346.12 | 59.86 | 27.56 | 58.25 | 9.78 | 558.68 | 0.85 | 4.51 | 0.58 |
| native | postgresql | PASS | COMPLETE | 3.50 | 43.16 | 46.33 | 341.82 | 38.73 | 23.46 | 53.60 | 6.36 | 553.44 | 0.91 | 0.97 | 0.56 |
| lima | sqlite | PASS | COMPLETE | 3.14 | 718.13 | 19.27 | 342.10 | 13.35 | 15.76 | 114.98 | 17.56 | 1241.14 | 0.84 | 1.00 | 1.29 |
| lima | postgresql | PASS | COMPLETE | 3.23 | 779.49 | 49.12 | 347.83 | 18.68 | 15.56 | 115.32 | 8.67 | 1334.67 | 0.92 | 0.47 | 1.35 |
| apple-container | sqlite | PASS | COMPLETE | 3.20 | 57.21 | 17.62 | 350.74 | 13.74 | 14.84 | 38.01 | 14.75 | 506.92 | 0.86 | 1.03 | 0.53 |
| apple-container | postgresql | PASS | COMPLETE | 3.20 | 130.85 | 37.40 | 352.99 | 16.20 | 16.17 | 37.47 | 7.09 | 598.17 | 0.94 | 0.41 | 0.61 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 5 / 1 | 30 / 3 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 42 | 4 | 1.7 |
| docker | pg-colocated | 5 / 1 | 30 / 3 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 42 | 4 | 1.8 |
| native | postgresql | 6 / 2 | 24 / 2 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 37 | 4 | 0.5 |
| lima | postgresql | 5 / 1 | 30 / 3 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 42 | 4 | 1.8 |
| apple-container | postgresql | 5 / 1 | 23 / 1 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 35 | 2 | 0.6 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | I/O MiB | I/O count | MiB/s | IOPS | Mean completion μs |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / pg-colocated | 64.00 | 64 | 1828.57 | 1828.57 | 533.21 |
| docker / postgresql | 64.00 | 64 | 1142.86 | 1142.86 | 869.67 |
| docker / sqlite | 64.00 | 64 | 1230.77 | 1230.77 | 804.52 |
| native / postgresql | 64.00 | 64 | 2000.00 | 2000.00 | 493.42 |
| native / sqlite | 64.00 | 64 | 2461.54 | 2461.54 | 395.69 |
| lima / postgresql | 64.00 | 64 | 1230.77 | 1230.77 | 798.49 |
| lima / sqlite | 64.00 | 64 | 1422.22 | 1422.22 | 698.44 |
| apple-container / postgresql | 64.00 | 64 | 1066.67 | 1066.67 | 916.40 |
| apple-container / sqlite | 64.00 | 64 | 1254.90 | 1254.90 | 787.96 |

## F03

Random write: 8 MiB, 4 KiB blocks; buffered synchronous engine, one job/depth 1, seed 1, nonzero 0x5a pattern. fio-buffered-single-pass-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 2.79 | 290.48 | 21.05 | 649.71 | 69.73 | 15.42 | 245.68 | 18.43 | 1310.49 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 2.65 | 300.16 | 43.66 | 645.44 | 86.18 | 13.04 | 216.78 | 8.28 | 1313.54 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 2.59 | 327.74 | 42.91 | 631.03 | 74.06 | 12.74 | 265.14 | 9.47 | 1363.08 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 2.79 | 39.73 | 33.64 | 600.12 | 92.13 | 27.70 | 55.14 | 9.70 | 858.16 | 0.92 | 1.32 | 0.65 |
| native | postgresql | PASS | COMPLETE | 2.79 | 43.77 | 46.62 | 590.98 | 123.77 | 25.77 | 54.94 | 6.38 | 892.25 | 0.92 | 1.44 | 0.68 |
| lima | sqlite | PASS | COMPLETE | 2.59 | 735.79 | 20.32 | 337.78 | 49.37 | 12.62 | 111.48 | 16.32 | 1283.67 | 0.52 | 0.71 | 0.98 |
| lima | postgresql | PASS | COMPLETE | 2.55 | 780.54 | 43.28 | 338.35 | 83.68 | 13.31 | 112.51 | 34.50 | 1406.17 | 0.52 | 0.97 | 1.07 |
| apple-container | sqlite | PASS | COMPLETE | 2.55 | 89.27 | 19.81 | 599.52 | 107.39 | 15.53 | 35.89 | 13.20 | 880.61 | 0.92 | 1.54 | 0.67 |
| apple-container | postgresql | PASS | COMPLETE | 2.50 | 143.93 | 34.72 | 343.14 | 127.22 | 17.34 | 36.46 | 6.51 | 709.31 | 0.53 | 1.48 | 0.54 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 67 / 2 | 0 / 0 | 0 / 0 | 103 | 7 | 3.9 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 0 / 0 | 67 / 2 | 0 / 0 | 0 / 0 | 103 | 7 | 3.3 |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 67 / 2 | 0 / 0 | 0 / 0 | 97 | 6 | 2.2 |
| lima | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 67 / 2 | 0 / 0 | 0 / 0 | 103 | 7 | 3.7 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 0 / 0 | 67 / 2 | 0 / 0 | 0 / 0 | 96 | 5 | 3.3 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | I/O MiB | I/O count | MiB/s | IOPS | Mean completion μs |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / sqlite | 8.00 | 2048 | 57.97 | 14840.58 | 65.26 |
| docker / postgresql | 8.00 | 2048 | 62.02 | 15875.97 | 61.20 |
| docker / pg-colocated | 8.00 | 2048 | 58.39 | 14948.91 | 65.02 |
| native / sqlite | 8.00 | 2048 | 52.98 | 13562.91 | 71.58 |
| native / postgresql | 8.00 | 2048 | 52.29 | 13385.62 | 73.08 |
| lima / sqlite | 8.00 | 2048 | 62.99 | 16125.98 | 60.27 |
| lima / postgresql | 8.00 | 2048 | 62.99 | 16125.98 | 60.32 |
| apple-container / sqlite | 8.00 | 2048 | 57.55 | 14733.81 | 66.13 |
| apple-container / postgresql | 8.00 | 2048 | 62.99 | 16125.98 | 60.50 |

## F04

Random read: 8 MiB, 4 KiB blocks; buffered synchronous engine, one job/depth 1, seed 1, nonzero 0x5a pattern. fio-buffered-single-pass-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 3.26 | 264.20 | 19.77 | 377.72 | 12.04 | 13.25 | 215.42 | 13.70 | 916.11 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 3.37 | 313.94 | 41.06 | 371.34 | 40.26 | 15.14 | 234.55 | 7.45 | 1023.74 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 2.62 | 304.05 | 40.30 | 381.93 | 14.50 | 13.81 | 245.21 | 8.12 | 1007.91 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 2.58 | 25.09 | 33.90 | 347.53 | 53.06 | 28.80 | 55.31 | 9.39 | 553.08 | 0.92 | 4.41 | 0.60 |
| native | postgresql | PASS | COMPLETE | 2.58 | 40.34 | 41.17 | 338.38 | 43.67 | 22.93 | 52.82 | 6.48 | 545.79 | 0.91 | 1.08 | 0.53 |
| lima | sqlite | PASS | COMPLETE | 3.48 | 709.44 | 42.71 | 336.41 | 12.00 | 11.60 | 113.23 | 13.55 | 1238.95 | 0.89 | 1.00 | 1.35 |
| lima | postgresql | PASS | COMPLETE | 3.26 | 752.54 | 43.26 | 340.12 | 11.70 | 11.86 | 105.35 | 6.76 | 1271.60 | 0.92 | 0.29 | 1.24 |
| apple-container | sqlite | PASS | COMPLETE | 3.25 | 44.10 | 17.71 | 341.71 | 12.37 | 11.60 | 35.45 | 13.35 | 476.30 | 0.90 | 1.03 | 0.52 |
| apple-container | postgresql | PASS | COMPLETE | 3.36 | 124.92 | 35.02 | 372.01 | 12.63 | 9.93 | 35.18 | 6.30 | 595.99 | 1.00 | 0.31 | 0.58 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 5 / 1 | 30 / 3 | 5 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 41 | 4 | 1.7 |
| docker | pg-colocated | 5 / 1 | 30 / 3 | 5 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 41 | 4 | 1.7 |
| native | postgresql | 6 / 2 | 24 / 2 | 5 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 36 | 4 | 0.5 |
| lima | postgresql | 5 / 1 | 30 / 3 | 5 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 41 | 4 | 1.8 |
| apple-container | postgresql | 5 / 1 | 23 / 1 | 5 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 34 | 2 | 0.6 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | I/O MiB | I/O count | MiB/s | IOPS | Mean completion μs |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / pg-colocated | 8.00 | 2048 | 75.47 | 19320.75 | 50.43 |
| docker / postgresql | 8.00 | 2048 | 77.67 | 19883.50 | 49.02 |
| docker / sqlite | 8.00 | 2048 | 77.67 | 19883.50 | 48.69 |
| native / postgresql | 8.00 | 2048 | 571.43 | 146285.71 | 6.14 |
| native / sqlite | 8.00 | 2048 | 470.59 | 120470.59 | 7.53 |
| lima / postgresql | 8.00 | 2048 | 78.43 | 20078.43 | 48.43 |
| lima / sqlite | 8.00 | 2048 | 82.47 | 21113.40 | 45.97 |
| apple-container / postgresql | 8.00 | 2048 | 72.73 | 18618.18 | 52.31 |
| apple-container / sqlite | 8.00 | 2048 | 77.67 | 19883.50 | 48.74 |

## Preparation, limits and cleanup

Attempted row preparation: 30.142 s total; maximum 1.918 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **INCOMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. 

Final disposition recorded by campaign owner.



Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

fio writes the declared compressible nonzero 0x5a pattern. Bandwidth and completion latency come from fio's own single job interval; CLI Exec and End-to-end above include additional lifecycle/routing costs.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

