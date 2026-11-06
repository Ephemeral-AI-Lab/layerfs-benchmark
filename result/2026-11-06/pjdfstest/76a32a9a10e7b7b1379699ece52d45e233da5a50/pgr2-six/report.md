# pjdfstest — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: INCOMPLETE.** 36 registered rows; execution {'PASS': 36}. Final infrastructure cleanup: **INCOMPLETE**.

LayerFS `76a32a9a10e7b7b1379699ece52d45e233da5a50` (pg-r2 at 76a32a9a10 (frozen final head, layerfs-project #98); gate-05 sealed release artifacts). Harness: rows ran at `a4f55ca` (branch `pg-r2-bench`, local; runner and cases identical to round 1's `c731387`); report from the same commit's shared/src/report.py. Gate-05 sealed release artifacts, built from `76a32a9a10` (clean detached checkout in the bench gatebuild worktree) through the worktree launcher: macOS CLI and daemon with `layerfs-node/postgresql` (build `build-macos-d1ee1858a2e64ecdba069d39d801533b`; CLI sha256 `5f673410…`, daemon `d32ec78a…`) and the Linux aarch64 bundle with PostgreSQL support (daemon `--features layerfs-daemon/postgresql`, worker CLI `--no-default-features --features postgresql`; bundle hash `cfe04f0c…`, Sandbox image `1d91885d…` saved from the registered runtime image `afa1ef9c…`). Fresh LayerFS home; native daemon set with `machine update native --daemon`; fresh Docker worker; fresh Lima `pgr2b-lima` and Apple Container `pgr2b-apple` (2 CPUs / 2G each). Six-suite guests use the tool image `pgr2b-six-tools:20261106` (`ac383307…`, archive config `fcad6365…`) built from round 1's unchanged tool context; Lima `pgr2b-lima6` and Apple Container `pgr2b-apple6` were created from its archive.

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 36}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Close is Sandbox close; Store release is Store remove (SQLite) or disconnect (PostgreSQL). End-to-end is the sum of the measured calls from create through Store release, without harness gaps; it excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: macOS 26.4.1, Apple M3 Max, 14 CPUs, 36 GiB; Docker Desktop 29.5.2 VM 8 CPUs / 7.75 GiB shared with other agents' builds; Lima and Apple Container machines 2 CPUs / 2 GiB each; PostgreSQL 17.11 container `pgr2b-pg` with 2 CPUs / 2 GiB (pg_stat_statements, synchronous_commit=off), host-published port 55442, co-located on the default bridge; 1-minute load during rows 4.4–7.8, median 5.9. Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

## PostgreSQL minus SQLite

Median over cells of (PostgreSQL arm − SQLite) per machine, milliseconds, using only cells where both rows passed. Close is Sandbox close; Store release is `store disconnect` (PostgreSQL) versus `store remove` (SQLite), which the product does not unify.

| Machine | Arm | Cells | Create | Mount | Exec | Commit | Unmount | Close | Store release | End-to-end |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 | -39.8 | +9.1 | -34.3 | +24.2 | -0.3 | +2.7 | -9.0 | +5.8 |
| docker | pg-colocated | 4 | +15.4 | +3.3 | -42.7 | +9.9 | +0.1 | -4.5 | -8.9 | -21.4 |
| native | postgresql | 4 | +2.5 | +2.4 | -12.5 | -8.9 | -3.3 | -9.1 | -2.8 | -32.5 |
| lima | postgresql | 4 | +16.4 | +8.6 | -19.6 | +21.2 | -0.5 | -0.3 | -6.2 | +11.5 |
| apple-container | postgresql | 4 | +13.8 | +10.7 | -12.2 | +28.1 | +1.1 | +1.1 | -7.1 | +41.1 |

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `5f673410fc5125081485326443bf368f9d501af5f678dd3bb1c7bd58f1d32e3c` |
| Native daemon | `d32ec78aa0e1a07f58a223b79a0aab7dabfc98274701be595de6c5f6bff1836d` |
| Linux bundle seal | `cfe04f0cb50472f51e0b8397360558b87e501f75bfea76ba048f80d68bdad953` |
| Docker tool image | `sha256:ac3833075ba13404feeacc765ddb5b5cc293b900eda1b60aea4fd94e141ca264` |
| Namespace archive config | `sha256:fcad636533c35f9ac95f0f4026d6db06ff58e61f3bb489b447f9a7944c4558db` |

## P01

tests/open/04.t: 4 planned TAP assertions; selected scripts run unprivileged. fixed-posix-tap-unprivileged-subset-v2.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 4.54 | 381.40 | 19.18 | 171.36 | 16.01 | 16.84 | 273.44 | 18.70 | 896.93 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 4.54 | 461.11 | 27.59 | 99.55 | 40.96 | 15.35 | 276.01 | 9.00 | 929.56 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.66 | 399.24 | 20.78 | 104.91 | 26.34 | 16.82 | 270.36 | 8.73 | 847.19 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 4.42 | 42.70 | 42.20 | 255.46 | 114.60 | 33.82 | 65.61 | 11.78 | 566.16 | 1.49 | 7.16 | 0.63 |
| native | postgresql | PASS | COMPLETE | 4.42 | 46.91 | 42.54 | 167.58 | 99.02 | 27.67 | 58.51 | 8.48 | 450.70 | 1.68 | 2.42 | 0.48 |
| lima | sqlite | PASS | COMPLETE | 4.66 | 696.64 | 18.76 | 137.83 | 15.10 | 15.58 | 97.02 | 15.76 | 996.69 | 0.80 | 0.94 | 1.11 |
| lima | postgresql | PASS | COMPLETE | 4.66 | 709.61 | 26.25 | 77.18 | 39.22 | 14.88 | 97.31 | 9.06 | 973.51 | 0.78 | 0.96 | 1.05 |
| apple-container | sqlite | PASS | COMPLETE | 5.01 | 61.82 | 15.59 | 96.99 | 11.79 | 11.33 | 36.05 | 14.72 | 248.28 | 0.57 | 0.74 | 0.28 |
| apple-container | postgresql | PASS | COMPLETE | 5.01 | 71.76 | 27.39 | 91.41 | 40.20 | 12.15 | 36.80 | 8.65 | 288.36 | 0.92 | 0.98 | 0.31 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.8 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.8 |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.8 |
| lima | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.8 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.9 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Assertions | Passed | Failed | Skipped | TODO |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / sqlite | 4 | 4 | 0 | 0 | 0 |
| docker / postgresql | 4 | 4 | 0 | 0 | 0 |
| docker / pg-colocated | 4 | 4 | 0 | 0 | 0 |
| native / sqlite | 4 | 4 | 0 | 0 | 0 |
| native / postgresql | 4 | 4 | 0 | 0 | 0 |
| lima / sqlite | 4 | 4 | 0 | 0 | 0 |
| lima / postgresql | 4 | 4 | 0 | 0 | 0 |
| apple-container / sqlite | 4 | 4 | 0 | 0 | 0 |
| apple-container / postgresql | 4 | 4 | 0 | 0 | 0 |

## P02

tests/rename/18.t: 6 planned TAP assertions; selected scripts run unprivileged. fixed-posix-tap-unprivileged-subset-v2.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 7.44 | 410.66 | 18.10 | 108.48 | 15.80 | 15.26 | 248.35 | 16.60 | 833.25 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 7.44 | 393.67 | 27.91 | 133.99 | 39.17 | 15.05 | 251.19 | 8.54 | 869.53 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 7.39 | 423.55 | 22.38 | 101.93 | 25.31 | 15.79 | 242.46 | 8.74 | 840.17 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 7.39 | 44.75 | 37.07 | 199.94 | 90.85 | 30.91 | 70.00 | 12.20 | 485.73 | 1.84 | 5.75 | 0.58 |
| native | postgresql | PASS | COMPLETE | 7.78 | 45.70 | 44.69 | 198.11 | 85.83 | 27.58 | 58.83 | 10.11 | 470.85 | 1.48 | 2.19 | 0.54 |
| lima | sqlite | PASS | COMPLETE | 7.08 | 692.18 | 17.23 | 84.40 | 15.44 | 15.46 | 92.69 | 14.55 | 931.92 | 0.78 | 0.98 | 1.12 |
| lima | postgresql | PASS | COMPLETE | 7.08 | 712.00 | 30.73 | 90.25 | 37.96 | 15.10 | 98.91 | 8.78 | 993.72 | 0.67 | 0.97 | 1.14 |
| apple-container | sqlite | PASS | COMPLETE | 6.84 | 62.65 | 18.56 | 108.02 | 12.59 | 11.73 | 38.59 | 15.54 | 267.68 | 1.00 | 0.80 | 0.32 |
| apple-container | postgresql | PASS | COMPLETE | 6.84 | 78.53 | 25.86 | 134.67 | 40.36 | 13.82 | 38.48 | 8.22 | 339.93 | 1.01 | 1.03 | 0.39 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.9 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.9 |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.8 |
| lima | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.9 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.9 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Assertions | Passed | Failed | Skipped | TODO |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / pg-colocated | 6 | 6 | 0 | 0 | 0 |
| docker / postgresql | 6 | 6 | 0 | 0 | 0 |
| docker / sqlite | 6 | 6 | 0 | 0 | 0 |
| native / postgresql | 6 | 6 | 0 | 0 | 0 |
| native / sqlite | 6 | 6 | 0 | 0 | 0 |
| lima / postgresql | 6 | 6 | 0 | 0 | 0 |
| lima / sqlite | 6 | 6 | 0 | 0 | 0 |
| apple-container / postgresql | 6 | 6 | 0 | 0 | 0 |
| apple-container / sqlite | 6 | 6 | 0 | 0 | 0 |

## P03

tests/chmod/02.t: 5 planned TAP assertions; selected scripts run unprivileged. fixed-posix-tap-unprivileged-subset-v2.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 5.85 | 443.17 | 19.85 | 150.77 | 16.30 | 16.39 | 233.27 | 17.42 | 897.17 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.85 | 380.64 | 28.21 | 128.54 | 35.88 | 16.06 | 277.68 | 9.15 | 876.15 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 6.58 | 429.00 | 22.54 | 131.92 | 22.73 | 16.48 | 321.81 | 9.98 | 954.46 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 5.84 | 46.88 | 39.83 | 272.98 | 99.63 | 30.81 | 72.37 | 11.64 | 574.15 | 1.81 | 6.11 | 0.64 |
| native | postgresql | PASS | COMPLETE | 5.84 | 46.85 | 44.29 | 249.73 | 86.87 | 28.04 | 59.17 | 9.05 | 524.00 | 1.94 | 2.42 | 0.60 |
| lima | sqlite | PASS | COMPLETE | 6.58 | 709.18 | 22.21 | 110.49 | 16.32 | 15.51 | 97.77 | 22.94 | 994.41 | 0.73 | 1.00 | 1.11 |
| lima | postgresql | PASS | COMPLETE | 6.22 | 711.80 | 25.71 | 98.31 | 36.04 | 22.29 | 94.67 | 18.76 | 1007.58 | 0.76 | 1.00 | 1.15 |
| apple-container | sqlite | PASS | COMPLETE | 6.22 | 54.05 | 17.74 | 139.39 | 13.68 | 13.36 | 37.50 | 16.02 | 291.75 | 0.92 | 0.84 | 0.33 |
| apple-container | postgresql | PASS | COMPLETE | 6.04 | 65.68 | 27.30 | 110.92 | 31.35 | 11.90 | 38.89 | 8.87 | 294.90 | 0.86 | 0.87 | 0.34 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.8 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.7 |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.7 |
| lima | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.9 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.8 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Assertions | Passed | Failed | Skipped | TODO |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / sqlite | 5 | 5 | 0 | 0 | 0 |
| docker / postgresql | 5 | 5 | 0 | 0 | 0 |
| docker / pg-colocated | 5 | 5 | 0 | 0 | 0 |
| native / sqlite | 5 | 5 | 0 | 0 | 0 |
| native / postgresql | 5 | 5 | 0 | 0 | 0 |
| lima / sqlite | 5 | 5 | 0 | 0 | 0 |
| lima / postgresql | 5 | 5 | 0 | 0 | 0 |
| apple-container / sqlite | 5 | 5 | 0 | 0 | 0 |
| apple-container / postgresql | 5 | 5 | 0 | 0 | 0 |

## P04

tests/symlink/00.t: 14 planned TAP assertions; selected scripts run unprivileged. fixed-posix-tap-unprivileged-subset-v2.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 5.90 | 685.50 | 20.84 | 1209.01 | 16.73 | 16.70 | 490.37 | 23.13 | 2462.28 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.80 | 538.86 | 36.78 | 1162.69 | 53.97 | 17.34 | 458.61 | 10.61 | 2278.86 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.52 | 726.21 | 24.68 | 1137.06 | 42.04 | 16.88 | 374.51 | 8.93 | 2330.31 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 5.57 | 46.34 | 41.58 | 1277.18 | 95.97 | 30.10 | 69.28 | 11.63 | 1572.08 | 1.06 | 5.74 | 0.64 |
| native | postgresql | PASS | COMPLETE | 5.57 | 50.39 | 41.25 | 1276.99 | 104.47 | 26.85 | 65.35 | 8.68 | 1573.97 | 1.10 | 1.94 | 0.69 |
| lima | sqlite | PASS | COMPLETE | 6.16 | 688.35 | 18.52 | 1130.45 | 18.20 | 16.87 | 100.55 | 42.23 | 2015.17 | 0.94 | 1.09 | 0.82 |
| lima | postgresql | PASS | COMPLETE | 5.82 | 731.14 | 28.24 | 1103.34 | 38.04 | 15.43 | 99.75 | 9.11 | 2025.05 | 0.95 | 0.70 | 0.89 |
| apple-container | sqlite | PASS | COMPLETE | 5.91 | 66.27 | 18.47 | 1143.27 | 15.36 | 11.40 | 36.81 | 15.62 | 1307.20 | 0.95 | 0.92 | 0.53 |
| apple-container | postgresql | PASS | COMPLETE | 6.16 | 83.67 | 32.00 | 1124.52 | 48.94 | 12.75 | 38.86 | 8.63 | 1349.38 | 0.97 | 0.91 | 0.59 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 1.1 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 1.0 |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 1.0 |
| lima | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.9 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 1.0 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Assertions | Passed | Failed | Skipped | TODO |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / pg-colocated | 14 | 14 | 0 | 0 | 0 |
| docker / postgresql | 14 | 14 | 0 | 0 | 0 |
| docker / sqlite | 14 | 14 | 0 | 0 | 0 |
| native / postgresql | 14 | 14 | 0 | 0 | 0 |
| native / sqlite | 14 | 14 | 0 | 0 | 0 |
| lima / postgresql | 14 | 14 | 0 | 0 | 0 |
| lima / sqlite | 14 | 14 | 0 | 0 | 0 |
| apple-container / postgresql | 14 | 14 | 0 | 0 | 0 |
| apple-container / sqlite | 14 | 14 | 0 | 0 | 0 |

## Preparation, limits and cleanup

Attempted row preparation: 8.972 s total; maximum 0.523 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **INCOMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. 

Final disposition recorded by campaign owner.



Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

