# fio — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: INCOMPLETE.** 36 registered rows; execution {'PASS': 36}. Final infrastructure cleanup: **INCOMPLETE**.

LayerFS `76a32a9a10e7b7b1379699ece52d45e233da5a50` (pg-r2 at 76a32a9a10 (frozen final head, layerfs-project #98); gate-05 sealed release artifacts). Harness: rows ran at `a4f55ca` (branch `pg-r2-bench`, local; runner and cases identical to round 1's `c731387`); report from the same commit's shared/src/report.py. Gate-05 sealed release artifacts, built from `76a32a9a10` (clean detached checkout in the bench gatebuild worktree) through the worktree launcher: macOS CLI and daemon with `layerfs-node/postgresql` (build `build-macos-d1ee1858a2e64ecdba069d39d801533b`; CLI sha256 `5f673410…`, daemon `d32ec78a…`) and the Linux aarch64 bundle with PostgreSQL support (daemon `--features layerfs-daemon/postgresql`, worker CLI `--no-default-features --features postgresql`; bundle hash `cfe04f0c…`, Sandbox image `1d91885d…` saved from the registered runtime image `afa1ef9c…`). Fresh LayerFS home; native daemon set with `machine update native --daemon`; fresh Docker worker; fresh Lima `pgr2b-lima` and Apple Container `pgr2b-apple` (2 CPUs / 2G each). Six-suite guests use the tool image `pgr2b-six-tools:20261106` (`ac383307…`, archive config `fcad6365…`) built from round 1's unchanged tool context; Lima `pgr2b-lima6` and Apple Container `pgr2b-apple6` were created from its archive.

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 36}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Close is Sandbox close; Store release is Store remove (SQLite) or disconnect (PostgreSQL). End-to-end is the sum of the measured calls from create through Store release, without harness gaps; it excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: macOS 26.4.1, Apple M3 Max, 14 CPUs, 36 GiB; Docker Desktop 29.5.2 VM 8 CPUs / 7.75 GiB shared with other agents' builds; Lima and Apple Container machines 2 CPUs / 2 GiB each; PostgreSQL 17.11 container `pgr2b-pg` with 2 CPUs / 2 GiB (pg_stat_statements, synchronous_commit=off), host-published port 55442, co-located on the default bridge; 1-minute load during rows 4.9–7.8, median 6.2. Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

## PostgreSQL minus SQLite

Median over cells of (PostgreSQL arm − SQLite) per machine, milliseconds, using only cells where both rows passed. Close is Sandbox close; Store release is `store disconnect` (PostgreSQL) versus `store remove` (SQLite), which the product does not unify.

| Machine | Arm | Cells | Create | Mount | Exec | Commit | Unmount | Close | Store release | End-to-end |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 | -2.2 | +8.7 | -23.1 | +19.9 | +0.3 | +7.2 | -10.1 | +38.4 |
| docker | pg-colocated | 4 | -13.7 | +3.8 | -21.4 | +8.8 | +0.5 | +22.0 | -8.3 | +53.6 |
| native | postgresql | 4 | -0.8 | +2.3 | -5.8 | +5.1 | -4.6 | -3.9 | -4.4 | -16.6 |
| lima | postgresql | 4 | -1.5 | +7.7 | -5.6 | +16.7 | -0.9 | -2.2 | -5.7 | -114.6 |
| apple-container | postgresql | 4 | -2.8 | +10.8 | +0.4 | +16.7 | -0.1 | -1.2 | -7.5 | -14.8 |

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `5f673410fc5125081485326443bf368f9d501af5f678dd3bb1c7bd58f1d32e3c` |
| Native daemon | `d32ec78aa0e1a07f58a223b79a0aab7dabfc98274701be595de6c5f6bff1836d` |
| Linux bundle seal | `cfe04f0cb50472f51e0b8397360558b87e501f75bfea76ba048f80d68bdad953` |
| Docker tool image | `sha256:ac3833075ba13404feeacc765ddb5b5cc293b900eda1b60aea4fd94e141ca264` |
| Namespace archive config | `sha256:fcad636533c35f9ac95f0f4026d6db06ff58e61f3bb489b447f9a7944c4558db` |

## F01

Sequential write: 64 MiB, 1024 KiB blocks; buffered synchronous engine, one job/depth 1, seed 1, nonzero 0x5a pattern. fio-buffered-single-pass-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 6.62 | 371.00 | 19.12 | 670.46 | 312.88 | 21.61 | 266.20 | 19.27 | 1680.54 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 6.73 | 373.71 | 28.27 | 628.50 | 357.90 | 24.68 | 308.12 | 8.84 | 1730.03 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 6.99 | 472.09 | 25.82 | 626.97 | 330.95 | 25.21 | 261.83 | 8.71 | 1751.57 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 7.01 | 51.17 | 48.27 | 609.76 | 405.49 | 30.98 | 69.16 | 11.47 | 1226.30 | 0.91 | 1.30 | 0.73 |
| native | postgresql | PASS | COMPLETE | 6.62 | 46.74 | 41.56 | 594.00 | 418.66 | 27.13 | 57.47 | 8.99 | 1194.54 | 0.95 | 1.17 | 0.69 |
| lima | sqlite | PASS | COMPLETE | 6.99 | 2491.38 | 20.49 | 594.81 | 297.84 | 24.78 | 295.38 | 15.97 | 3740.65 | 0.89 | 0.95 | 2.23 |
| lima | postgresql | PASS | COMPLETE | 7.40 | 699.84 | 26.93 | 593.51 | 350.43 | 22.11 | 96.77 | 10.58 | 1800.17 | 0.94 | 0.98 | 1.04 |
| apple-container | sqlite | PASS | COMPLETE | 7.28 | 1590.32 | 15.47 | 604.84 | 295.68 | 16.52 | 831.07 | 15.09 | 3368.99 | 0.90 | 0.95 | 2.00 |
| apple-container | postgresql | PASS | COMPLETE | 7.02 | 81.61 | 28.37 | 345.93 | 329.37 | 16.52 | 37.54 | 9.08 | 848.41 | 0.55 | 0.92 | 0.49 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 78 / 1 | 0 / 0 | 0 / 0 | 96 | 4 | 4.1 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 0 / 0 | 78 / 1 | 0 / 0 | 0 / 0 | 96 | 4 | 3.2 |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 78 / 1 | 0 / 0 | 0 / 0 | 96 | 4 | 3.8 |
| lima | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 78 / 1 | 0 / 0 | 0 / 0 | 96 | 4 | 4.4 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 78 / 1 | 0 / 0 | 0 / 0 | 96 | 4 | 3.7 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | I/O MiB | I/O count | MiB/s | IOPS | Mean completion μs |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / sqlite | 64.00 | 64 | 383.23 | 383.23 | 2590.75 |
| docker / postgresql | 64.00 | 64 | 387.88 | 387.88 | 2559.21 |
| docker / pg-colocated | 64.00 | 64 | 367.82 | 367.82 | 2700.34 |
| native / sqlite | 64.00 | 64 | 412.90 | 412.90 | 2382.58 |
| native / postgresql | 64.00 | 64 | 372.09 | 372.09 | 2657.72 |
| lima / sqlite | 64.00 | 64 | 438.36 | 438.36 | 2260.88 |
| lima / postgresql | 64.00 | 64 | 450.70 | 450.70 | 2209.29 |
| apple-container / sqlite | 64.00 | 64 | 438.36 | 438.36 | 2259.18 |
| apple-container / postgresql | 64.00 | 64 | 503.94 | 503.94 | 1973.19 |

## F02

Sequential read: 64 MiB, 1024 KiB blocks; buffered synchronous engine, one job/depth 1, seed 1, nonzero 0x5a pattern. fio-buffered-single-pass-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 6.00 | 408.75 | 19.47 | 376.41 | 15.01 | 18.97 | 239.32 | 15.94 | 1093.87 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.83 | 429.52 | 27.64 | 372.14 | 17.10 | 17.99 | 248.36 | 8.53 | 1121.28 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.83 | 393.13 | 22.70 | 384.28 | 13.78 | 19.64 | 287.66 | 8.83 | 1130.03 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 6.16 | 44.20 | 36.72 | 348.04 | 88.40 | 30.28 | 62.79 | 12.68 | 623.12 | 0.92 | 5.89 | 0.57 |
| native | postgresql | PASS | COMPLETE | 6.26 | 41.97 | 44.93 | 345.44 | 73.78 | 25.00 | 62.08 | 7.97 | 601.18 | 0.93 | 4.32 | 0.54 |
| lima | sqlite | PASS | COMPLETE | 5.84 | 690.01 | 18.62 | 346.28 | 13.73 | 18.62 | 96.08 | 20.74 | 1204.08 | 0.92 | 0.91 | 1.10 |
| lima | postgresql | PASS | COMPLETE | 6.08 | 707.13 | 25.67 | 341.51 | 15.91 | 17.47 | 122.23 | 23.90 | 1253.83 | 0.92 | 0.93 | 1.12 |
| apple-container | sqlite | PASS | COMPLETE | 6.61 | 69.25 | 18.86 | 347.24 | 38.10 | 21.42 | 37.45 | 14.58 | 546.91 | 0.92 | 2.54 | 0.50 |
| apple-container | postgresql | PASS | COMPLETE | 5.53 | 63.97 | 27.47 | 349.70 | 14.31 | 21.21 | 37.17 | 8.72 | 522.55 | 0.94 | 0.84 | 0.47 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 3 / 2 | 14 / 0 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 24 | 2 | 0.5 |
| docker | pg-colocated | 3 / 2 | 14 / 0 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 24 | 2 | 0.5 |
| native | postgresql | 4 / 3 | 14 / 0 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 25 | 3 | 0.5 |
| lima | postgresql | 3 / 2 | 14 / 0 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 24 | 2 | 0.5 |
| apple-container | postgresql | 3 / 2 | 14 / 0 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 24 | 2 | 0.5 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | I/O MiB | I/O count | MiB/s | IOPS | Mean completion μs |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / pg-colocated | 64.00 | 64 | 1015.87 | 1015.87 | 970.03 |
| docker / postgresql | 64.00 | 64 | 1185.19 | 1185.19 | 831.46 |
| docker / sqlite | 64.00 | 64 | 1142.86 | 1142.86 | 855.93 |
| native / postgresql | 64.00 | 64 | 1882.35 | 1882.35 | 519.47 |
| native / sqlite | 64.00 | 64 | 2000.00 | 2000.00 | 483.98 |
| lima / postgresql | 64.00 | 64 | 1066.67 | 1066.67 | 917.53 |
| lima / sqlite | 64.00 | 64 | 1015.87 | 1015.87 | 973.23 |
| apple-container / postgresql | 64.00 | 64 | 1185.19 | 1185.19 | 835.29 |
| apple-container / sqlite | 64.00 | 64 | 1391.30 | 1391.30 | 708.75 |

## F03

Random write: 8 MiB, 4 KiB blocks; buffered synchronous engine, one job/depth 1, seed 1, nonzero 0x5a pattern. fio-buffered-single-pass-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 6.19 | 427.77 | 18.20 | 619.34 | 71.64 | 17.77 | 287.88 | 18.20 | 1460.79 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.85 | 420.70 | 28.98 | 635.06 | 109.26 | 17.21 | 293.16 | 8.51 | 1512.88 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.71 | 415.99 | 20.68 | 620.01 | 84.62 | 17.22 | 404.44 | 8.69 | 1571.65 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 6.12 | 42.07 | 37.51 | 600.56 | 143.61 | 33.15 | 61.67 | 12.41 | 930.99 | 0.97 | 2.00 | 0.64 |
| native | postgresql | PASS | COMPLETE | 6.19 | 45.65 | 39.23 | 591.62 | 161.15 | 26.93 | 62.86 | 8.38 | 935.81 | 0.93 | 1.47 | 0.62 |
| lima | sqlite | PASS | COMPLETE | 5.49 | 693.47 | 17.61 | 591.36 | 70.11 | 17.24 | 93.74 | 22.75 | 1506.27 | 0.95 | 0.98 | 1.03 |
| lima | postgresql | PASS | COMPLETE | 5.49 | 700.93 | 25.99 | 585.00 | 101.27 | 16.55 | 91.72 | 9.13 | 1530.60 | 0.92 | 0.93 | 1.01 |
| apple-container | sqlite | PASS | COMPLETE | 5.53 | 63.06 | 17.06 | 594.25 | 83.99 | 16.07 | 37.88 | 17.07 | 829.39 | 0.96 | 1.17 | 0.57 |
| apple-container | postgresql | PASS | COMPLETE | 5.53 | 66.95 | 28.27 | 598.42 | 114.94 | 16.19 | 36.94 | 8.03 | 869.74 | 0.94 | 1.05 | 0.57 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 61 / 1 | 0 / 0 | 0 / 0 | 79 | 4 | 3.4 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 0 / 0 | 61 / 1 | 0 / 0 | 0 / 0 | 79 | 4 | 2.8 |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 61 / 1 | 0 / 0 | 0 / 0 | 79 | 4 | 3.0 |
| lima | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 61 / 1 | 0 / 0 | 0 / 0 | 79 | 4 | 3.5 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 61 / 1 | 0 / 0 | 0 / 0 | 79 | 4 | 3.4 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | I/O MiB | I/O count | MiB/s | IOPS | Mean completion μs |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / sqlite | 8.00 | 2048 | 53.69 | 13744.97 | 70.90 |
| docker / postgresql | 8.00 | 2048 | 47.34 | 12118.34 | 80.14 |
| docker / pg-colocated | 8.00 | 2048 | 43.24 | 11070.27 | 87.84 |
| native / sqlite | 8.00 | 2048 | 42.11 | 10778.95 | 90.62 |
| native / postgresql | 8.00 | 2048 | 43.72 | 11191.26 | 87.33 |
| lima / sqlite | 8.00 | 2048 | 46.78 | 11976.61 | 81.55 |
| lima / postgresql | 8.00 | 2048 | 50.96 | 13044.59 | 75.14 |
| apple-container / sqlite | 8.00 | 2048 | 44.44 | 11377.78 | 85.62 |
| apple-container / postgresql | 8.00 | 2048 | 55.56 | 14222.22 | 68.83 |

## F04

Random read: 8 MiB, 4 KiB blocks; buffered synchronous engine, one job/depth 1, seed 1, nonzero 0x5a pattern. fio-buffered-single-pass-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 6.38 | 587.71 | 20.10 | 737.25 | 14.83 | 17.61 | 510.98 | 25.79 | 1914.28 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.80 | 393.41 | 26.81 | 635.51 | 15.70 | 18.72 | 361.82 | 9.21 | 1461.18 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.79 | 388.40 | 24.43 | 624.57 | 19.52 | 18.02 | 297.12 | 18.60 | 1390.66 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 5.16 | 43.66 | 37.41 | 348.62 | 87.26 | 29.43 | 64.58 | 13.51 | 624.48 | 0.47 | 5.88 | 0.33 |
| native | postgresql | PASS | COMPLETE | 4.91 | 44.31 | 40.20 | 351.77 | 84.32 | 26.39 | 57.55 | 8.77 | 613.30 | 0.55 | 5.37 | 0.42 |
| lima | sqlite | PASS | COMPLETE | 7.73 | 708.70 | 19.04 | 586.65 | 14.41 | 16.77 | 93.91 | 14.83 | 1454.31 | 0.80 | 0.97 | 0.76 |
| lima | postgresql | PASS | COMPLETE | 7.79 | 698.31 | 28.91 | 340.40 | 16.48 | 16.35 | 91.52 | 8.77 | 1200.74 | 0.54 | 1.05 | 0.82 |
| apple-container | sqlite | PASS | COMPLETE | 7.61 | 60.86 | 17.97 | 599.72 | 11.40 | 19.06 | 38.00 | 18.80 | 765.80 | 0.81 | 0.77 | 0.40 |
| apple-container | postgresql | PASS | COMPLETE | 7.75 | 60.57 | 28.35 | 598.10 | 13.93 | 14.48 | 36.57 | 8.52 | 760.52 | 0.94 | 0.89 | 0.52 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 3 / 2 | 14 / 0 | 5 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 23 | 2 | 0.5 |
| docker | pg-colocated | 3 / 2 | 14 / 0 | 5 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 23 | 2 | 0.5 |
| native | postgresql | 4 / 3 | 14 / 0 | 5 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 24 | 3 | 0.5 |
| lima | postgresql | 3 / 2 | 14 / 0 | 5 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 23 | 2 | 0.6 |
| apple-container | postgresql | 3 / 2 | 14 / 0 | 5 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 23 | 2 | 0.7 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | I/O MiB | I/O count | MiB/s | IOPS | Mean completion μs |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / pg-colocated | 8.00 | 2048 | 65.04 | 16650.41 | 58.34 |
| docker / postgresql | 8.00 | 2048 | 63.49 | 16253.97 | 59.97 |
| docker / sqlite | 8.00 | 2048 | 18.82 | 4818.82 | 197.31 |
| native / postgresql | 8.00 | 2048 | 400.00 | 102400.00 | 8.76 |
| native / sqlite | 8.00 | 2048 | 444.44 | 113777.78 | 7.88 |
| lima / postgresql | 8.00 | 2048 | 80.81 | 20686.87 | 47.07 |
| lima / sqlite | 8.00 | 2048 | 54.05 | 13837.84 | 70.47 |
| apple-container / postgresql | 8.00 | 2048 | 56.74 | 14524.82 | 67.19 |
| apple-container / sqlite | 8.00 | 2048 | 58.39 | 14948.91 | 65.18 |

## Preparation, limits and cleanup

Attempted row preparation: 37.739 s total; maximum 2.500 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **INCOMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. 

Final disposition recorded by campaign owner.



Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

fio writes the declared compressible nonzero 0x5a pattern. Bandwidth and completion latency come from fio's own single job interval; CLI Exec and End-to-end above include additional lifecycle/routing costs.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

