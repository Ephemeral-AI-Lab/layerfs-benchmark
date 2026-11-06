# fs-bench-quick — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: INCOMPLETE.** 162 registered rows; execution {'PASS': 162}. Final infrastructure cleanup: **INCOMPLETE**.

LayerFS `76a32a9a10e7b7b1379699ece52d45e233da5a50` (pg-r2 at 76a32a9a10 (frozen final head, layerfs-project #98); gate-05 sealed release artifacts). Harness: rows ran at `a4f55ca` (branch `pg-r2-bench`, local; runner and cases identical to round 1's `c731387`); report from the same commit's shared/src/report.py. Gate-05 sealed release artifacts, built from `76a32a9a10` (clean detached checkout in the bench gatebuild worktree) through the worktree launcher: macOS CLI and daemon with `layerfs-node/postgresql` (build `build-macos-d1ee1858a2e64ecdba069d39d801533b`; CLI sha256 `5f673410…`, daemon `d32ec78a…`) and the Linux aarch64 bundle with PostgreSQL support (daemon `--features layerfs-daemon/postgresql`, worker CLI `--no-default-features --features postgresql`; bundle hash `cfe04f0c…`, Sandbox image `1d91885d…` saved from the registered runtime image `afa1ef9c…`). Fresh LayerFS home; native daemon set with `machine update native --daemon`; fresh Docker worker; fresh Lima `pgr2b-lima` and Apple Container `pgr2b-apple` (2 CPUs / 2G each).

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 162}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Close is Sandbox close; Store release is Store remove (SQLite) or disconnect (PostgreSQL). End-to-end is the sum of the measured calls from create through Store release, without harness gaps; it excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: macOS 26.4.1, Apple M3 Max, 14 CPUs, 36 GiB; Docker Desktop 29.5.2 VM 8 CPUs / 7.75 GiB shared with other agents' builds; Lima and Apple Container machines 2 CPUs / 2 GiB each; PostgreSQL 17.11 container `pgr2b-pg` with 2 CPUs / 2 GiB (pg_stat_statements, synchronous_commit=off), host-published port 55442, co-located on the default bridge; 1-minute load during rows 5.3–29.0, median 9.1. Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

## PostgreSQL minus SQLite

Median over cells of (PostgreSQL arm − SQLite) per machine, milliseconds, using only cells where both rows passed. Close is Sandbox close; Store release is `store disconnect` (PostgreSQL) versus `store remove` (SQLite), which the product does not unify.

| Machine | Arm | Cells | Create | Mount | Exec | Commit | Unmount | Close | Store release | End-to-end |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 18 | -7.4 | +8.1 | +23.0 | +35.7 | -0.2 | +5.1 | -9.5 | +50.5 |
| docker | pg-colocated | 18 | -19.6 | +4.4 | +36.3 | +18.3 | -1.1 | +15.6 | -7.8 | +35.2 |
| native | postgresql | 18 | +9.4 | +4.5 | -15.4 | +22.4 | -2.9 | -3.3 | -2.7 | +2.1 |
| lima | postgresql | 18 | +2.1 | +9.4 | +2.1 | +35.0 | +0.1 | +0.0 | -5.2 | +50.0 |
| apple-container | postgresql | 18 | +8.1 | +8.6 | +3.4 | +42.5 | -0.1 | -0.1 | -6.5 | +53.4 |

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `5f673410fc5125081485326443bf368f9d501af5f678dd3bb1c7bd58f1d32e3c` |
| Native daemon | `d32ec78aa0e1a07f58a223b79a0aab7dabfc98274701be595de6c5f6bff1836d` |
| Linux bundle seal | `cfe04f0cb50472f51e0b8397360558b87e501f75bfea76ba048f80d68bdad953` |
| Docker tool image | `sha256:1d91885de27a20805af0d1b99602ace066f0514983613e391ee1f73ac8e7c2e9` |
| Namespace archive config | `UNAVAILABLE` |

## C01

Create 1,000 numbered files (also the sweep's 1,000-file point). Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 6.78 | 354.65 | 14.86 | 318.03 | 89.23 | 14.19 | 225.53 | 17.43 | 1033.92 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 7.60 | 338.32 | 24.41 | 337.13 | 143.59 | 13.93 | 218.29 | 7.51 | 1083.19 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 7.60 | 331.12 | 21.91 | 355.68 | 112.09 | 14.72 | 256.71 | 10.58 | 1102.80 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 6.45 | 648.54 | 34.83 | 701.60 | 151.33 | 39.83 | 57.67 | 11.37 | 1645.19 | 2.21 | 1.70 | 1.59 |
| native | postgresql | PASS | COMPLETE | 6.78 | 42.63 | 36.55 | 698.26 | 190.41 | 37.57 | 56.14 | 6.73 | 1068.29 | 2.07 | 1.33 | 0.99 |
| lima | sqlite | PASS | COMPLETE | 8.03 | 4224.78 | 16.60 | 225.38 | 80.48 | 12.76 | 983.29 | 12.19 | 5555.47 | 0.71 | 0.90 | 5.37 |
| lima | postgresql | PASS | COMPLETE | 8.16 | 698.31 | 22.33 | 277.56 | 145.01 | 13.22 | 89.52 | 9.65 | 1255.60 | 0.82 | 1.01 | 1.16 |
| apple-container | sqlite | PASS | COMPLETE | 8.16 | 3384.54 | 20.69 | 239.50 | 76.44 | 10.44 | 1321.92 | 19.23 | 5072.75 | 0.75 | 0.86 | 4.91 |
| apple-container | postgresql | PASS | COMPLETE | 9.99 | 70.81 | 19.19 | 260.02 | 119.48 | 10.51 | 34.82 | 6.78 | 521.62 | 0.77 | 0.83 | 0.48 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 85 / 1 | 0 / 0 | 0 / 0 | 111 | 4 | 14.2 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 8 / 0 | 85 / 1 | 0 / 0 | 0 / 0 | 111 | 4 | 14.0 |
| native | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 85 / 1 | 0 / 0 | 0 / 0 | 111 | 4 | 12.9 |
| lima | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 85 / 1 | 0 / 0 | 0 / 0 | 111 | 4 | 16.3 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 85 / 1 | 0 / 0 | 0 / 0 | 111 | 4 | 14.8 |

## C02

Create 1,000 files, then `stat` each (one process per file). Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 9.84 | 303.82 | 14.91 | 903.61 | 79.18 | 17.21 | 223.79 | 17.56 | 1560.07 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 9.31 | 323.39 | 35.18 | 983.61 | 141.34 | 14.91 | 226.71 | 7.50 | 1732.64 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 9.31 | 339.00 | 21.65 | 1010.10 | 110.87 | 15.16 | 231.34 | 7.68 | 1735.80 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 9.02 | 39.32 | 34.10 | 6513.01 | 183.54 | 40.59 | 58.52 | 9.86 | 6878.94 | 7.21 | 2.32 | 4.41 |
| native | postgresql | PASS | COMPLETE | 9.99 | 50.33 | 40.87 | 5948.42 | 208.06 | 34.53 | 52.24 | 6.93 | 6341.37 | 6.05 | 1.47 | 3.66 |
| lima | sqlite | PASS | COMPLETE | 10.01 | 704.90 | 16.19 | 925.92 | 81.56 | 16.04 | 108.28 | 12.92 | 1865.81 | 1.02 | 1.03 | 1.20 |
| lima | postgresql | PASS | COMPLETE | 10.02 | 730.80 | 28.30 | 912.73 | 181.79 | 15.22 | 90.63 | 8.24 | 1967.70 | 0.93 | 1.29 | 1.14 |
| apple-container | sqlite | PASS | COMPLETE | 10.33 | 43.46 | 13.60 | 653.35 | 73.92 | 9.68 | 33.23 | 12.26 | 839.50 | 0.72 | 0.93 | 0.54 |
| apple-container | postgresql | PASS | COMPLETE | 10.33 | 94.78 | 27.53 | 771.58 | 129.24 | 11.34 | 33.13 | 7.44 | 1075.03 | 0.78 | 0.91 | 0.62 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 85 / 1 | 0 / 0 | 0 / 0 | 111 | 4 | 15.6 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 8 / 0 | 85 / 1 | 0 / 0 | 0 / 0 | 111 | 4 | 15.2 |
| native | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 85 / 1 | 0 / 0 | 0 / 0 | 111 | 4 | 13.3 |
| lima | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 85 / 1 | 0 / 0 | 0 / 0 | 111 | 4 | 19.5 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 85 / 1 | 0 / 0 | 0 / 0 | 111 | 4 | 14.4 |

## C03

Create 1,000 files, then remove them. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 10.80 | 647.32 | 31.48 | 625.96 | 14.86 | 13.63 | 265.23 | 19.48 | 1617.96 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 10.82 | 410.67 | 36.70 | 791.84 | 52.42 | 14.30 | 278.57 | 9.25 | 1593.75 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 13.23 | 488.27 | 31.87 | 769.68 | 48.76 | 33.48 | 268.20 | 11.89 | 1652.14 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 10.86 | 46.67 | 38.84 | 1468.10 | 107.92 | 29.26 | 58.80 | 10.49 | 1760.07 | 2.35 | 7.26 | 1.09 |
| native | postgresql | PASS | COMPLETE | 10.86 | 41.91 | 36.63 | 1336.36 | 112.38 | 24.36 | 61.89 | 8.11 | 1621.65 | 1.69 | 2.14 | 1.02 |
| lima | sqlite | PASS | COMPLETE | 14.34 | 726.13 | 21.36 | 620.00 | 17.29 | 20.10 | 97.16 | 44.53 | 1546.59 | 0.99 | 1.16 | 0.96 |
| lima | postgresql | PASS | COMPLETE | 14.34 | 690.49 | 34.81 | 474.44 | 37.37 | 15.30 | 103.03 | 7.54 | 1362.98 | 0.60 | 0.71 | 0.86 |
| apple-container | sqlite | PASS | COMPLETE | 22.19 | 98.70 | 17.16 | 905.53 | 24.91 | 16.13 | 44.59 | 26.04 | 1133.06 | 1.45 | 1.68 | 0.70 |
| apple-container | postgresql | PASS | COMPLETE | 22.19 | 71.30 | 25.44 | 511.01 | 38.71 | 10.98 | 37.07 | 9.27 | 703.79 | 0.65 | 0.74 | 0.44 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 59 | 4 | 1.0 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 8 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 59 | 4 | 1.3 |
| native | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 59 | 4 | 0.8 |
| lima | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 59 | 4 | 0.8 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 59 | 4 | 0.9 |

## C04

Create 110 directories and 1,000 empty files. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 28.08 | 361.99 | 20.08 | 785.44 | 111.78 | 14.58 | 239.50 | 17.28 | 1550.64 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 28.96 | 451.09 | 26.86 | 668.37 | 137.23 | 20.42 | 259.20 | 8.39 | 1571.55 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 25.45 | 503.74 | 23.69 | 1259.46 | 144.44 | 27.82 | 422.72 | 10.49 | 2392.37 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 22.93 | 70.09 | 34.91 | 5541.11 | 231.25 | 41.87 | 72.76 | 11.03 | 6003.02 | 7.05 | 2.07 | 3.87 |
| native | postgresql | PASS | COMPLETE | 23.53 | 58.63 | 66.69 | 5017.17 | 318.74 | 39.94 | 63.85 | 9.61 | 5574.62 | 7.51 | 2.32 | 3.55 |
| lima | sqlite | PASS | COMPLETE | 26.48 | 682.19 | 13.80 | 573.37 | 83.94 | 13.35 | 89.51 | 11.38 | 1467.53 | 0.73 | 0.75 | 0.95 |
| lima | postgresql | PASS | COMPLETE | 28.08 | 739.03 | 23.06 | 582.96 | 131.58 | 13.55 | 94.18 | 6.96 | 1591.32 | 0.87 | 0.96 | 1.01 |
| apple-container | sqlite | PASS | COMPLETE | 25.00 | 67.30 | 17.97 | 496.97 | 81.18 | 11.07 | 35.09 | 14.23 | 723.80 | 0.63 | 0.73 | 0.47 |
| apple-container | postgresql | PASS | COMPLETE | 25.00 | 58.92 | 23.38 | 461.64 | 176.53 | 10.64 | 36.32 | 6.58 | 774.01 | 0.69 | 1.29 | 0.49 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 83 / 1 | 0 / 0 | 0 / 0 | 109 | 4 | 8.4 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 8 / 0 | 83 / 1 | 0 / 0 | 0 / 0 | 109 | 4 | 9.5 |
| native | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 83 / 1 | 0 / 0 | 0 / 0 | 109 | 4 | 10.7 |
| lima | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 83 / 1 | 0 / 0 | 0 / 0 | 109 | 4 | 8.0 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 83 / 1 | 0 / 0 | 0 / 0 | 109 | 4 | 7.4 |

## C05

C04, then `find . -type f \| wc -l`. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 18.35 | 749.32 | 20.97 | 1191.73 | 95.44 | 15.27 | 296.42 | 22.18 | 2391.32 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 17.84 | 547.04 | 29.24 | 1307.24 | 150.82 | 16.30 | 513.42 | 7.11 | 2571.17 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 17.84 | 636.88 | 20.87 | 1226.78 | 119.08 | 14.50 | 549.42 | 7.55 | 2575.08 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 21.91 | 49.56 | 40.26 | 3503.56 | 232.47 | 35.61 | 59.55 | 9.51 | 3930.52 | 2.94 | 2.44 | 1.64 |
| native | postgresql | PASS | COMPLETE | 20.48 | 41.03 | 45.07 | 4252.88 | 213.29 | 34.41 | 51.60 | 9.69 | 4647.98 | 3.25 | 1.41 | 1.81 |
| lima | sqlite | PASS | COMPLETE | 17.61 | 708.58 | 16.07 | 718.07 | 91.13 | 50.98 | 96.18 | 12.75 | 1693.77 | 0.60 | 0.95 | 0.71 |
| lima | postgresql | PASS | COMPLETE | 15.53 | 677.40 | 23.06 | 576.58 | 123.19 | 12.34 | 86.99 | 6.53 | 1506.08 | 0.44 | 0.82 | 0.59 |
| apple-container | sqlite | PASS | COMPLETE | 14.76 | 60.50 | 19.50 | 506.66 | 94.28 | 35.09 | 34.70 | 10.64 | 761.38 | 0.43 | 0.99 | 0.32 |
| apple-container | postgresql | PASS | COMPLETE | 14.76 | 68.80 | 25.45 | 500.77 | 153.62 | 15.27 | 34.97 | 6.48 | 805.35 | 0.38 | 1.02 | 0.31 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 83 / 1 | 0 / 0 | 0 / 0 | 109 | 4 | 9.4 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 8 / 0 | 83 / 1 | 0 / 0 | 0 / 0 | 109 | 4 | 7.9 |
| native | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 83 / 1 | 0 / 0 | 0 / 0 | 109 | 4 | 9.3 |
| lima | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 83 / 1 | 0 / 0 | 0 / 0 | 109 | 4 | 7.7 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 8 / 0 | 83 / 1 | 0 / 0 | 0 / 0 | 109 | 4 | 10.6 |

## C06

Write 64 MiB of zeros. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 13.01 | 629.46 | 21.53 | 515.75 | 352.62 | 24.29 | 488.29 | 28.31 | 2060.25 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 13.27 | 825.67 | 47.07 | 699.73 | 422.43 | 24.08 | 427.06 | 11.29 | 2457.34 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 13.74 | 654.76 | 25.91 | 424.54 | 332.31 | 22.89 | 298.74 | 11.29 | 1770.45 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 13.98 | 37.83 | 43.79 | 313.09 | 415.06 | 67.25 | 62.09 | 11.27 | 950.39 | 0.61 | 1.18 | 0.46 |
| native | postgresql | PASS | COMPLETE | 13.98 | 55.55 | 46.03 | 220.62 | 437.57 | 26.17 | 53.42 | 6.73 | 846.08 | 0.32 | 1.04 | 0.34 |
| lima | sqlite | PASS | COMPLETE | 12.32 | 691.89 | 16.60 | 202.71 | 323.28 | 24.70 | 97.56 | 16.00 | 1372.74 | 0.39 | 0.92 | 0.67 |
| lima | postgresql | PASS | COMPLETE | 12.52 | 784.96 | 38.97 | 253.89 | 390.69 | 23.39 | 94.20 | 9.08 | 1595.18 | 0.36 | 0.92 | 0.65 |
| apple-container | sqlite | PASS | COMPLETE | 12.22 | 58.36 | 16.63 | 181.23 | 328.71 | 22.88 | 34.75 | 12.98 | 655.54 | 0.35 | 0.93 | 0.32 |
| apple-container | postgresql | PASS | COMPLETE | 12.22 | 84.94 | 29.00 | 230.63 | 370.72 | 23.97 | 61.89 | 9.30 | 810.45 | 0.33 | 0.88 | 0.33 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 78 / 1 | 0 / 0 | 0 / 0 | 96 | 4 | 5.8 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 0 / 0 | 78 / 1 | 0 / 0 | 0 / 0 | 96 | 4 | 4.2 |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 78 / 1 | 0 / 0 | 0 / 0 | 96 | 4 | 3.6 |
| lima | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 78 / 1 | 0 / 0 | 0 / 0 | 96 | 4 | 5.4 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 78 / 1 | 0 / 0 | 0 / 0 | 96 | 4 | 4.0 |

## C07

Write 64 MiB of zeros, then copy it. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 11.43 | 885.02 | 25.29 | 971.96 | 734.12 | 34.26 | 443.82 | 30.28 | 3124.76 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 11.55 | 708.26 | 52.09 | 1007.63 | 879.18 | 34.27 | 504.12 | 13.46 | 3199.00 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 11.56 | 827.00 | 36.28 | 1139.12 | 796.75 | 35.47 | 418.95 | 12.23 | 3265.79 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 11.87 | 49.60 | 43.60 | 457.68 | 902.97 | 69.21 | 66.34 | 12.21 | 1601.61 | 0.47 | 1.23 | 0.51 |
| native | postgresql | PASS | COMPLETE | 11.64 | 58.96 | 52.85 | 412.14 | 807.29 | 36.63 | 64.28 | 10.64 | 1442.77 | 0.41 | 0.92 | 0.45 |
| lima | sqlite | PASS | COMPLETE | 13.84 | 714.56 | 20.62 | 502.34 | 666.88 | 32.75 | 95.69 | 18.48 | 2051.33 | 0.52 | 0.91 | 0.66 |
| lima | postgresql | PASS | COMPLETE | 12.54 | 694.55 | 32.90 | 382.49 | 677.53 | 44.99 | 97.65 | 9.23 | 1939.33 | 0.38 | 0.77 | 0.61 |
| apple-container | sqlite | PASS | COMPLETE | 12.25 | 63.48 | 17.92 | 389.91 | 696.50 | 44.04 | 42.21 | 20.15 | 1274.21 | 0.40 | 0.95 | 0.41 |
| apple-container | postgresql | PASS | COMPLETE | 12.15 | 66.06 | 50.38 | 426.15 | 750.26 | 36.52 | 38.75 | 11.33 | 1379.44 | 0.42 | 0.85 | 0.43 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 79 / 1 | 0 / 0 | 0 / 0 | 97 | 4 | 6.4 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 0 / 0 | 79 / 1 | 0 / 0 | 0 / 0 | 97 | 4 | 7.6 |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 79 / 1 | 0 / 0 | 0 / 0 | 97 | 4 | 4.5 |
| lima | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 79 / 1 | 0 / 0 | 0 / 0 | 97 | 4 | 4.0 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 79 / 1 | 0 / 0 | 0 / 0 | 97 | 4 | 5.1 |

## C08

Write 64 MiB of zeros, then read it. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 12.60 | 632.02 | 23.98 | 255.97 | 408.27 | 26.79 | 279.80 | 20.65 | 1647.48 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 12.83 | 1022.87 | 41.73 | 549.27 | 383.34 | 27.01 | 283.01 | 10.64 | 2317.86 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 13.82 | 711.40 | 38.36 | 704.43 | 754.52 | 31.58 | 471.30 | 16.83 | 2728.40 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 12.76 | 69.32 | 55.74 | 523.45 | 608.75 | 42.67 | 75.04 | 16.20 | 1391.17 | 2.04 | 1.49 | 0.84 |
| native | postgresql | PASS | COMPLETE | 12.22 | 59.58 | 47.83 | 285.39 | 683.19 | 39.03 | 76.97 | 10.76 | 1202.75 | 0.52 | 1.78 | 0.52 |
| lima | sqlite | PASS | COMPLETE | 12.88 | 670.66 | 26.71 | 241.82 | 307.88 | 38.26 | 92.91 | 17.00 | 1395.23 | 0.94 | 0.75 | 0.85 |
| lima | postgresql | PASS | COMPLETE | 12.95 | 723.16 | 36.31 | 181.71 | 352.74 | 20.95 | 116.16 | 10.92 | 1441.95 | 0.33 | 0.92 | 0.62 |
| apple-container | sqlite | PASS | COMPLETE | 12.46 | 48.04 | 16.31 | 193.86 | 337.39 | 24.13 | 63.22 | 20.80 | 703.75 | 0.76 | 0.83 | 0.43 |
| apple-container | postgresql | PASS | COMPLETE | 12.33 | 65.31 | 25.24 | 233.29 | 406.60 | 24.94 | 40.57 | 12.70 | 808.65 | 0.42 | 1.06 | 0.35 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 78 / 1 | 0 / 0 | 0 / 0 | 96 | 4 | 3.8 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 0 / 0 | 78 / 1 | 0 / 0 | 0 / 0 | 96 | 4 | 9.2 |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 78 / 1 | 0 / 0 | 0 / 0 | 96 | 4 | 6.0 |
| lima | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 78 / 1 | 0 / 0 | 0 / 0 | 96 | 4 | 3.4 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 78 / 1 | 0 / 0 | 0 / 0 | 96 | 4 | 4.2 |

## C09

Read the committed 64 MiB zero file (dedups to about one chunk). Committed base.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 12.53 | 413.93 | 19.51 | 87.31 | 13.41 | 16.86 | 208.29 | 30.70 | 790.01 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 12.41 | 474.00 | 32.70 | 89.55 | 13.20 | 15.39 | 208.26 | 8.74 | 841.83 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 12.05 | 561.33 | 24.35 | 87.17 | 13.05 | 13.86 | 224.82 | 8.51 | 933.09 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 11.51 | 43.34 | 43.60 | 57.21 | 71.42 | 30.30 | 74.48 | 14.13 | 334.48 | 0.66 | 5.33 | 0.42 |
| native | postgresql | PASS | COMPLETE | 11.79 | 46.32 | 46.52 | 59.76 | 93.63 | 26.54 | 57.95 | 8.86 | 339.59 | 0.67 | 7.10 | 0.40 |
| lima | sqlite | PASS | COMPLETE | 11.63 | 682.48 | 15.94 | 54.57 | 13.47 | 15.51 | 93.09 | 13.25 | 888.31 | 0.63 | 1.00 | 1.12 |
| lima | postgresql | PASS | COMPLETE | 10.84 | 676.05 | 26.62 | 105.91 | 16.38 | 16.70 | 91.38 | 8.53 | 941.56 | 1.18 | 1.24 | 1.12 |
| apple-container | sqlite | PASS | COMPLETE | 10.61 | 54.64 | 15.43 | 86.03 | 10.64 | 15.44 | 40.14 | 14.04 | 236.35 | 0.99 | 0.79 | 0.30 |
| apple-container | postgresql | PASS | COMPLETE | 11.44 | 58.28 | 33.90 | 91.00 | 16.62 | 16.58 | 38.90 | 10.24 | 265.52 | 1.02 | 1.26 | 0.32 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 3 / 2 | 14 / 0 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 24 | 2 | 0.5 |
| docker | pg-colocated | 3 / 2 | 14 / 0 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 24 | 2 | 0.6 |
| native | postgresql | 4 / 3 | 14 / 0 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 25 | 3 | 0.5 |
| lima | postgresql | 3 / 2 | 14 / 0 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 24 | 2 | 0.6 |
| apple-container | postgresql | 3 / 2 | 14 / 0 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 24 | 2 | 0.9 |

## C10

Copy the committed 64 MiB zero file. Committed base.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 9.84 | 380.08 | 14.62 | 211.09 | 51.44 | 18.42 | 229.46 | 13.72 | 918.84 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 9.99 | 264.68 | 24.34 | 238.03 | 85.23 | 20.98 | 223.95 | 7.04 | 864.25 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 10.69 | 292.38 | 19.20 | 224.56 | 71.22 | 23.42 | 244.08 | 7.21 | 882.07 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 11.36 | 26.62 | 32.01 | 234.11 | 173.97 | 31.02 | 85.18 | 9.71 | 592.63 | 1.11 | 3.38 | 0.64 |
| native | postgresql | PASS | COMPLETE | 11.65 | 48.71 | 45.97 | 241.50 | 242.05 | 28.49 | 62.06 | 7.86 | 676.65 | 1.01 | 2.84 | 0.78 |
| lima | sqlite | PASS | COMPLETE | 9.19 | 872.18 | 22.92 | 193.34 | 45.73 | 18.45 | 121.63 | 11.06 | 1285.30 | 0.92 | 0.89 | 1.40 |
| lima | postgresql | PASS | COMPLETE | 9.29 | 673.74 | 20.91 | 196.01 | 74.06 | 44.06 | 90.13 | 6.39 | 1105.29 | 0.82 | 0.87 | 1.28 |
| apple-container | sqlite | PASS | COMPLETE | 8.83 | 47.75 | 15.46 | 178.89 | 66.23 | 31.00 | 34.85 | 13.20 | 387.39 | 0.85 | 1.29 | 0.42 |
| apple-container | postgresql | PASS | COMPLETE | 9.33 | 80.69 | 29.48 | 187.13 | 94.78 | 26.55 | 35.81 | 6.78 | 461.22 | 0.79 | 1.11 | 0.53 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 3 / 2 | 14 / 0 | 6 / 0 | 64 / 1 | 0 / 0 | 0 / 0 | 87 | 3 | 2.5 |
| docker | pg-colocated | 3 / 2 | 14 / 0 | 6 / 0 | 64 / 1 | 0 / 0 | 0 / 0 | 87 | 3 | 1.9 |
| native | postgresql | 4 / 3 | 14 / 0 | 6 / 0 | 64 / 1 | 0 / 0 | 0 / 0 | 88 | 4 | 3.3 |
| lima | postgresql | 3 / 2 | 14 / 0 | 6 / 0 | 64 / 1 | 0 / 0 | 0 / 0 | 87 | 3 | 2.2 |
| apple-container | postgresql | 3 / 2 | 14 / 0 | 6 / 0 | 64 / 1 | 0 / 0 | 0 / 0 | 87 | 3 | 2.5 |

## C11

Overwrite the committed zero file with zeros (`conv=notrunc`). Committed base.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 7.69 | 285.39 | 14.47 | 155.31 | 134.74 | 23.09 | 246.17 | 14.55 | 873.72 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 7.40 | 273.03 | 22.98 | 146.80 | 186.76 | 18.71 | 250.51 | 6.67 | 905.45 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 7.61 | 269.72 | 18.86 | 156.80 | 135.54 | 19.11 | 236.34 | 7.27 | 843.65 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 8.18 | 30.84 | 34.21 | 115.13 | 184.38 | 27.27 | 54.41 | 9.47 | 455.71 | 0.74 | 1.37 | 0.52 |
| native | postgresql | PASS | COMPLETE | 7.84 | 40.34 | 36.97 | 149.38 | 261.89 | 26.15 | 53.08 | 6.81 | 574.62 | 1.02 | 1.40 | 0.63 |
| lima | sqlite | PASS | COMPLETE | 7.20 | 694.74 | 13.45 | 94.92 | 108.06 | 16.19 | 91.75 | 11.03 | 1030.14 | 0.61 | 0.80 | 1.18 |
| lima | postgresql | PASS | COMPLETE | 7.33 | 675.01 | 20.66 | 96.40 | 139.29 | 18.01 | 92.14 | 6.54 | 1048.05 | 0.66 | 0.75 | 1.16 |
| apple-container | sqlite | PASS | COMPLETE | 7.07 | 56.68 | 18.20 | 109.36 | 149.42 | 31.00 | 35.00 | 12.70 | 412.36 | 0.70 | 1.11 | 0.47 |
| apple-container | postgresql | PASS | COMPLETE | 6.98 | 64.53 | 25.74 | 102.86 | 149.03 | 23.41 | 34.17 | 6.62 | 406.36 | 0.70 | 0.80 | 0.45 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 3 / 2 | 14 / 0 | 4 / 0 | 34 / 1 | 0 / 0 | 0 / 0 | 55 | 3 | 1.1 |
| docker | pg-colocated | 3 / 2 | 14 / 0 | 4 / 0 | 34 / 1 | 0 / 0 | 0 / 0 | 55 | 3 | 0.9 |
| native | postgresql | 4 / 3 | 14 / 0 | 4 / 0 | 34 / 1 | 0 / 0 | 0 / 0 | 56 | 4 | 1.2 |
| lima | postgresql | 3 / 2 | 14 / 0 | 4 / 0 | 34 / 1 | 0 / 0 | 0 / 0 | 55 | 3 | 1.1 |
| apple-container | postgresql | 3 / 2 | 14 / 0 | 4 / 0 | 34 / 1 | 0 / 0 | 0 / 0 | 55 | 3 | 1.1 |

## C12

Git init, 100 files, add and Git commit. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 5.96 | 320.90 | 13.16 | 160.24 | 64.88 | 11.94 | 224.84 | 14.44 | 810.40 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.96 | 290.87 | 20.46 | 189.63 | 79.80 | 12.34 | 211.92 | 6.92 | 811.92 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 6.45 | 321.16 | 17.95 | 209.73 | 58.14 | 13.27 | 232.94 | 6.98 | 860.17 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 6.45 | 26.32 | 33.83 | 376.75 | 91.65 | 27.95 | 58.21 | 9.77 | 624.47 | 2.35 | 1.41 | 0.77 |
| native | postgresql | PASS | COMPLETE | 6.66 | 42.90 | 37.98 | 351.59 | 158.58 | 23.35 | 55.15 | 6.42 | 675.97 | 1.85 | 1.99 | 0.83 |
| lima | sqlite | PASS | COMPLETE | 6.36 | 675.38 | 15.40 | 155.86 | 39.54 | 12.56 | 88.82 | 11.27 | 998.83 | 0.97 | 0.61 | 1.23 |
| lima | postgresql | PASS | COMPLETE | 5.96 | 681.55 | 21.24 | 155.95 | 83.25 | 12.58 | 89.60 | 9.02 | 1053.19 | 0.82 | 1.04 | 1.30 |
| apple-container | sqlite | PASS | COMPLETE | 6.25 | 49.58 | 14.93 | 170.91 | 59.59 | 11.30 | 33.96 | 13.28 | 353.57 | 1.07 | 0.92 | 0.44 |
| apple-container | postgresql | PASS | COMPLETE | 6.25 | 45.67 | 22.27 | 167.06 | 114.22 | 14.50 | 34.29 | 6.79 | 404.81 | 0.88 | 1.43 | 0.50 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 90 / 1 | 0 / 0 | 0 / 0 | 108 | 4 | 6.2 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 0 / 0 | 90 / 1 | 0 / 0 | 0 / 0 | 108 | 4 | 6.5 |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 90 / 1 | 0 / 0 | 0 / 0 | 108 | 4 | 9.6 |
| lima | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 90 / 1 | 0 / 0 | 0 / 0 | 108 | 4 | 6.7 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 90 / 1 | 0 / 0 | 0 / 0 | 108 | 4 | 6.7 |

## C13

New in pg62-v1: `echo 1 > a` and Commit, then `echo 2 > b` and a second Commit on the same Workspace (Commit 2). Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Commit 2 ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 6.17 | 323.02 | 13.63 | 45.65 | 12.32 | 12.59 | 13.04 | 233.62 | 14.26 | 718.61 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 6.00 | 320.55 | 20.17 | 41.44 | 44.52 | 52.65 | 12.90 | 253.65 | 6.88 | 802.53 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.92 | 296.95 | 16.21 | 40.04 | 23.11 | 15.83 | 11.75 | 233.21 | 7.32 | 687.65 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 6.01 | 36.05 | 33.74 | 21.86 | 66.93 | 60.54 | 26.43 | 51.34 | 8.86 | 327.62 | 0.48 | 5.43 | 0.46 |
| native | postgresql | PASS | COMPLETE | 6.17 | 43.75 | 37.86 | 18.24 | 80.16 | 61.88 | 23.67 | 49.30 | 6.60 | 339.79 | 0.44 | 1.80 | 0.42 |
| lima | sqlite | PASS | COMPLETE | 6.08 | 664.06 | 15.71 | 19.51 | 12.80 | 12.10 | 12.82 | 88.59 | 12.09 | 857.54 | 0.43 | 1.04 | 1.19 |
| lima | postgresql | PASS | COMPLETE | 6.88 | 710.58 | 23.25 | 19.81 | 56.81 | 31.98 | 13.02 | 92.53 | 6.95 | 975.55 | 0.48 | 1.28 | 1.22 |
| apple-container | sqlite | PASS | COMPLETE | 7.13 | 56.37 | 39.76 | 45.33 | 12.34 | 11.12 | 11.60 | 35.76 | 13.41 | 260.02 | 0.99 | 1.00 | 0.36 |
| apple-container | postgresql | PASS | COMPLETE | 7.13 | 74.83 | 24.96 | 25.32 | 88.67 | 33.88 | 9.46 | 34.53 | 6.61 | 318.31 | 0.61 | 1.99 | 0.40 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Exec 2 | Commit 2 | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 73 / 1 | 0 / 0 | 66 / 0 | 0 / 0 | 0 / 0 | 157 | 4 | 3.4 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 0 / 0 | 73 / 1 | 0 / 0 | 66 / 0 | 0 / 0 | 0 / 0 | 157 | 4 | 2.6 |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 73 / 1 | 0 / 0 | 66 / 0 | 0 / 0 | 0 / 0 | 157 | 4 | 3.2 |
| lima | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 73 / 1 | 0 / 0 | 66 / 0 | 0 / 0 | 0 / 0 | 157 | 4 | 4.3 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 73 / 1 | 0 / 0 | 66 / 0 | 0 / 0 | 0 / 0 | 157 | 4 | 7.7 |

## C14

New in pg62-v1: file sweep, 0 files (`true`); the Commit is UpToDate. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 5.61 | 303.21 | 14.43 | 63.34 | 14.23 | 14.88 | 229.72 | 14.53 | 654.34 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.83 | 350.30 | 22.14 | 59.45 | 16.91 | 12.24 | 269.29 | 7.62 | 737.94 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 6.00 | 337.74 | 15.77 | 51.50 | 12.33 | 12.62 | 253.86 | 6.81 | 690.63 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 6.35 | 26.41 | 33.97 | 22.29 | 62.08 | 30.74 | 55.13 | 8.75 | 239.36 | 0.35 | 4.36 | 0.37 |
| native | postgresql | PASS | COMPLETE | 6.64 | 43.16 | 39.78 | 16.60 | 55.98 | 24.56 | 51.67 | 6.75 | 238.51 | 0.28 | 3.31 | 0.32 |
| lima | sqlite | PASS | COMPLETE | 5.67 | 676.05 | 13.77 | 18.25 | 10.26 | 11.47 | 92.04 | 10.42 | 832.26 | 0.29 | 0.72 | 1.27 |
| lima | postgresql | PASS | COMPLETE | 5.64 | 719.58 | 29.59 | 21.54 | 15.91 | 11.88 | 91.74 | 31.98 | 922.22 | 0.36 | 0.94 | 1.25 |
| apple-container | sqlite | PASS | COMPLETE | 5.53 | 55.90 | 14.71 | 19.18 | 9.98 | 9.97 | 35.65 | 13.29 | 158.67 | 0.30 | 0.70 | 0.24 |
| apple-container | postgresql | PASS | COMPLETE | 5.53 | 72.66 | 27.42 | 21.10 | 14.82 | 10.21 | 35.62 | 6.94 | 188.77 | 0.35 | 0.88 | 0.26 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 19 | 3 | 0.4 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 0 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 19 | 3 | 0.3 |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 19 | 3 | 0.4 |
| lima | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 19 | 3 | 0.6 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 19 | 3 | 0.6 |

## C15

New in pg62-v1: file sweep, 100 numbered files. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 5.40 | 369.68 | 17.29 | 87.19 | 21.36 | 13.85 | 231.63 | 15.19 | 756.17 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.53 | 315.68 | 21.80 | 81.43 | 103.37 | 12.50 | 237.54 | 7.02 | 779.35 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.49 | 296.91 | 15.33 | 81.39 | 38.17 | 12.61 | 262.04 | 6.74 | 713.20 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 5.27 | 46.77 | 36.86 | 114.10 | 93.77 | 27.10 | 53.04 | 9.67 | 381.31 | 1.31 | 4.39 | 0.50 |
| native | postgresql | PASS | COMPLETE | 5.27 | 61.03 | 52.53 | 134.74 | 114.52 | 24.87 | 63.78 | 7.66 | 459.12 | 1.65 | 1.11 | 0.59 |
| lima | sqlite | PASS | COMPLETE | 5.77 | 716.41 | 18.00 | 72.51 | 20.09 | 13.65 | 94.17 | 13.29 | 948.12 | 0.83 | 0.94 | 1.25 |
| lima | postgresql | PASS | COMPLETE | 6.18 | 705.70 | 34.91 | 45.61 | 58.07 | 13.27 | 93.09 | 7.70 | 958.36 | 0.56 | 0.56 | 1.23 |
| apple-container | sqlite | PASS | COMPLETE | 6.33 | 75.45 | 15.54 | 61.71 | 28.57 | 12.48 | 35.05 | 12.54 | 241.34 | 0.71 | 1.34 | 0.32 |
| apple-container | postgresql | PASS | COMPLETE | 6.38 | 70.53 | 24.16 | 58.92 | 61.39 | 12.12 | 35.58 | 7.30 | 270.02 | 0.72 | 0.59 | 0.35 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 74 / 1 | 0 / 0 | 0 / 0 | 92 | 4 | 7.6 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 0 / 0 | 74 / 1 | 0 / 0 | 0 / 0 | 92 | 4 | 4.2 |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 74 / 1 | 0 / 0 | 0 / 0 | 92 | 4 | 9.3 |
| lima | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 74 / 1 | 0 / 0 | 0 / 0 | 92 | 4 | 4.7 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 74 / 1 | 0 / 0 | 0 / 0 | 92 | 4 | 4.9 |

## C16

New in pg62-v1: file sweep, 10,000 numbered files; prospectively declared 25 s budget. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 7.68 | 339.43 | 14.91 | 2765.86 | 771.71 | 49.47 | 192.44 | 16.23 | 4150.04 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 7.83 | 317.63 | 20.09 | 2298.09 | 963.25 | 23.61 | 300.01 | 7.06 | 3929.74 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 7.01 | 286.18 | 17.17 | 2616.87 | 906.77 | 25.40 | 263.47 | 6.78 | 4122.63 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 6.57 | 38.43 | 32.22 | 4937.12 | 793.92 | 119.99 | 61.54 | 9.31 | 5992.54 | 1.79 | 1.03 | 1.44 |
| native | postgresql | PASS | COMPLETE | 6.11 | 53.47 | 39.62 | 4881.46 | 977.16 | 143.40 | 49.33 | 6.43 | 6150.87 | 2.12 | 1.01 | 1.57 |
| lima | sqlite | PASS | COMPLETE | 7.69 | 698.51 | 15.58 | 1952.49 | 750.88 | 21.84 | 91.54 | 12.95 | 3543.80 | 0.71 | 0.97 | 0.85 |
| lima | postgresql | PASS | COMPLETE | 7.57 | 699.48 | 19.05 | 2182.21 | 955.48 | 18.45 | 92.71 | 6.59 | 3973.96 | 0.95 | 0.99 | 1.01 |
| apple-container | sqlite | PASS | COMPLETE | 7.34 | 59.59 | 15.96 | 2023.00 | 780.63 | 25.63 | 55.90 | 14.29 | 2975.01 | 0.73 | 1.01 | 0.72 |
| apple-container | postgresql | PASS | COMPLETE | 7.28 | 77.73 | 24.82 | 1935.50 | 935.31 | 23.88 | 34.55 | 7.15 | 3038.93 | 0.84 | 0.97 | 0.77 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 80 / 0 | 251 / 1 | 0 / 0 | 0 / 0 | 349 | 4 | 123.6 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 80 / 0 | 251 / 1 | 0 / 0 | 0 / 0 | 349 | 4 | 129.0 |
| native | postgresql | 4 / 3 | 14 / 0 | 80 / 0 | 251 / 1 | 0 / 0 | 0 / 0 | 349 | 4 | 124.4 |
| lima | postgresql | 4 / 3 | 14 / 0 | 80 / 0 | 251 / 1 | 0 / 0 | 0 / 0 | 349 | 4 | 126.0 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 80 / 0 | 251 / 1 | 0 / 0 | 0 / 0 | 349 | 4 | 126.5 |

## C17

New in pg62-v1: `cat` a committed 64 MiB non-repeating file (AES-128-CTR keystream, pinned SHA-256). Committed base.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 8.19 | 357.79 | 15.84 | 250.08 | 11.35 | 18.79 | 222.47 | 18.80 | 895.12 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 8.77 | 383.11 | 21.78 | 339.30 | 13.05 | 15.97 | 252.48 | 7.42 | 1033.11 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 9.11 | 295.21 | 21.59 | 315.82 | 11.04 | 15.03 | 242.78 | 8.35 | 909.82 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 6.97 | 26.42 | 34.10 | 218.48 | 62.65 | 27.16 | 58.55 | 10.99 | 438.35 | 0.87 | 5.52 | 0.49 |
| native | postgresql | PASS | COMPLETE | 7.94 | 39.97 | 36.49 | 276.78 | 60.37 | 25.02 | 53.78 | 6.83 | 499.25 | 0.82 | 4.63 | 0.48 |
| lima | sqlite | PASS | COMPLETE | 8.41 | 673.53 | 15.98 | 270.74 | 12.93 | 15.09 | 90.84 | 15.85 | 1094.95 | 1.08 | 1.14 | 1.22 |
| lima | postgresql | PASS | COMPLETE | 8.18 | 676.70 | 25.51 | 491.27 | 18.73 | 15.01 | 87.68 | 6.99 | 1321.89 | 1.45 | 1.44 | 1.28 |
| apple-container | sqlite | PASS | COMPLETE | 8.24 | 63.49 | 16.95 | 240.39 | 9.78 | 16.94 | 34.09 | 23.66 | 405.31 | 0.96 | 0.86 | 0.45 |
| apple-container | postgresql | PASS | COMPLETE | 8.13 | 60.91 | 25.54 | 378.06 | 12.18 | 17.12 | 57.01 | 6.93 | 557.74 | 1.11 | 0.93 | 0.54 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 3 / 2 | 14 / 0 | 68 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 86 | 2 | 46.3 |
| docker | pg-colocated | 3 / 2 | 14 / 0 | 68 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 86 | 2 | 42.1 |
| native | postgresql | 4 / 3 | 14 / 0 | 68 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 87 | 3 | 47.9 |
| lima | postgresql | 3 / 2 | 14 / 0 | 68 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 86 | 2 | 46.5 |
| apple-container | postgresql | 3 / 2 | 14 / 0 | 68 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 86 | 2 | 62.8 |

## C18

New in pg62-v1: `stat f{1..1000}` in one process over 1,000 committed files. Committed base.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 8.07 | 299.18 | 15.24 | 111.61 | 11.41 | 14.06 | 268.69 | 15.12 | 735.31 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 7.31 | 306.71 | 23.14 | 110.13 | 13.64 | 31.35 | 209.75 | 7.19 | 701.91 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 7.53 | 337.07 | 18.78 | 149.22 | 12.70 | 13.10 | 202.59 | 7.20 | 740.66 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 7.90 | 37.86 | 34.98 | 1446.07 | 74.88 | 29.64 | 54.37 | 9.77 | 1687.57 | 12.96 | 6.56 | 2.30 |
| native | postgresql | PASS | COMPLETE | 7.80 | 40.29 | 43.33 | 1308.95 | 87.29 | 26.58 | 57.02 | 6.96 | 1570.41 | 11.89 | 6.40 | 2.24 |
| lima | sqlite | PASS | COMPLETE | 7.28 | 668.11 | 15.03 | 96.12 | 11.23 | 11.94 | 88.09 | 12.18 | 902.69 | 0.86 | 0.98 | 1.23 |
| lima | postgresql | PASS | COMPLETE | 7.82 | 675.87 | 23.89 | 107.29 | 12.36 | 12.36 | 89.11 | 6.95 | 927.82 | 0.97 | 0.91 | 1.32 |
| apple-container | sqlite | PASS | COMPLETE | 6.85 | 46.06 | 18.00 | 100.96 | 10.14 | 13.15 | 35.16 | 12.87 | 236.34 | 0.90 | 0.89 | 0.32 |
| apple-container | postgresql | PASS | COMPLETE | 6.92 | 57.89 | 23.04 | 138.97 | 14.84 | 14.12 | 35.21 | 7.74 | 291.82 | 1.26 | 1.09 | 0.42 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 3 / 2 | 16 / 0 | 24 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 44 | 2 | 2.3 |
| docker | pg-colocated | 3 / 2 | 16 / 0 | 24 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 44 | 2 | 2.2 |
| native | postgresql | 4 / 3 | 27 / 0 | 13 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 45 | 3 | 2.9 |
| lima | postgresql | 3 / 2 | 16 / 0 | 24 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 44 | 2 | 2.3 |
| apple-container | postgresql | 3 / 2 | 16 / 0 | 24 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 44 | 2 | 2.5 |

## Preparation, limits and cleanup

Attempted row preparation: 163.715 s total; maximum 4.989 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **INCOMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. 

Final disposition recorded by campaign owner.



Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

