# smallfile — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: INCOMPLETE.** 45 registered rows; execution {'PASS': 45}. Final infrastructure cleanup: **INCOMPLETE**.

LayerFS `76a32a9a10e7b7b1379699ece52d45e233da5a50` (pg-r2 at 76a32a9a10 (frozen final head, layerfs-project #98); gate-05 sealed release artifacts). Harness: rows ran at `a4f55ca` (branch `pg-r2-bench`, local; runner and cases identical to round 1's `c731387`); report from the same commit's shared/src/report.py. Gate-05 sealed release artifacts, built from `76a32a9a10` (clean detached checkout in the bench gatebuild worktree) through the worktree launcher: macOS CLI and daemon with `layerfs-node/postgresql` (build `build-macos-d1ee1858a2e64ecdba069d39d801533b`; CLI sha256 `5f673410…`, daemon `d32ec78a…`) and the Linux aarch64 bundle with PostgreSQL support (daemon `--features layerfs-daemon/postgresql`, worker CLI `--no-default-features --features postgresql`; bundle hash `cfe04f0c…`, Sandbox image `1d91885d…` saved from the registered runtime image `afa1ef9c…`). Fresh LayerFS home; native daemon set with `machine update native --daemon`; fresh Docker worker; fresh Lima `pgr2b-lima` and Apple Container `pgr2b-apple` (2 CPUs / 2G each). Six-suite guests use the tool image `pgr2b-six-tools:20261106` (`ac383307…`, archive config `fcad6365…`) built from round 1's unchanged tool context; Lima `pgr2b-lima6` and Apple Container `pgr2b-apple6` were created from its archive.

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 45}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Close is Sandbox close; Store release is Store remove (SQLite) or disconnect (PostgreSQL). End-to-end is the sum of the measured calls from create through Store release, without harness gaps; it excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: macOS 26.4.1, Apple M3 Max, 14 CPUs, 36 GiB; Docker Desktop 29.5.2 VM 8 CPUs / 7.75 GiB shared with other agents' builds; Lima and Apple Container machines 2 CPUs / 2 GiB each; PostgreSQL 17.11 container `pgr2b-pg` with 2 CPUs / 2 GiB (pg_stat_statements, synchronous_commit=off), host-published port 55442, co-located on the default bridge; 1-minute load during rows 4.0–7.2, median 5.6. Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

## PostgreSQL minus SQLite

Median over cells of (PostgreSQL arm − SQLite) per machine, milliseconds, using only cells where both rows passed. Close is Sandbox close; Store release is `store disconnect` (PostgreSQL) versus `store remove` (SQLite), which the product does not unify.

| Machine | Arm | Cells | Create | Mount | Exec | Commit | Unmount | Close | Store release | End-to-end |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 5 | +7.0 | +12.1 | +4.4 | +58.5 | +1.0 | +17.2 | -12.3 | +84.2 |
| docker | pg-colocated | 5 | -5.5 | +5.5 | -32.7 | +18.4 | +0.2 | -12.5 | -11.7 | +5.3 |
| native | postgresql | 5 | +2.4 | +3.8 | +2.9 | +28.8 | -3.4 | -6.7 | -4.0 | +32.6 |
| lima | postgresql | 5 | +6.6 | +8.1 | +16.6 | +46.3 | -0.5 | -0.7 | -6.1 | +66.0 |
| apple-container | postgresql | 5 | +6.5 | +10.8 | +23.4 | +55.8 | +0.7 | -1.5 | -6.2 | +90.5 |

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `5f673410fc5125081485326443bf368f9d501af5f678dd3bb1c7bd58f1d32e3c` |
| Native daemon | `d32ec78aa0e1a07f58a223b79a0aab7dabfc98274701be595de6c5f6bff1836d` |
| Linux bundle seal | `cfe04f0cb50472f51e0b8397360558b87e501f75bfea76ba048f80d68bdad953` |
| Docker tool image | `sha256:ac3833075ba13404feeacc765ddb5b5cc293b900eda1b60aea4fd94e141ca264` |
| Namespace archive config | `sha256:fcad636533c35f9ac95f0f4026d6db06ff58e61f3bb489b447f9a7944c4558db` |

## L01

Create 512 files: two workers × 256 files, 4 KiB/file, 64 files/directory. two-worker-256x4k-as-host-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 6.67 | 378.51 | 18.07 | 3787.75 | 79.40 | 17.61 | 254.26 | 22.55 | 4558.15 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 6.37 | 383.01 | 35.73 | 3781.79 | 137.92 | 15.63 | 293.79 | 9.41 | 4657.27 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.94 | 407.22 | 23.55 | 3749.41 | 108.48 | 16.42 | 294.83 | 10.20 | 4610.11 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 7.15 | 44.27 | 34.84 | 3976.93 | 149.60 | 36.87 | 67.75 | 12.77 | 4323.03 | 1.05 | 1.88 | 0.95 |
| native | postgresql | PASS | COMPLETE | 6.90 | 44.49 | 40.42 | 3991.47 | 175.45 | 34.00 | 61.08 | 8.76 | 4355.66 | 1.06 | 1.27 | 0.94 |
| lima | sqlite | PASS | COMPLETE | 5.95 | 710.40 | 19.27 | 3869.05 | 78.07 | 16.56 | 97.77 | 15.83 | 4806.94 | 1.02 | 0.98 | 1.05 |
| lima | postgresql | PASS | COMPLETE | 5.95 | 701.95 | 27.33 | 3842.75 | 132.77 | 17.55 | 91.95 | 9.65 | 4823.95 | 1.02 | 0.96 | 1.04 |
| apple-container | sqlite | PASS | COMPLETE | 7.15 | 52.58 | 15.59 | 3878.99 | 73.80 | 11.63 | 36.94 | 14.82 | 4084.36 | 1.02 | 0.93 | 0.90 |
| apple-container | postgresql | PASS | COMPLETE | 6.82 | 72.31 | 24.71 | 3863.89 | 129.64 | 13.06 | 35.80 | 8.85 | 4148.25 | 1.02 | 0.94 | 0.89 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 91 / 1 | 0 / 0 | 0 / 0 | 109 | 4 | 7.9 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 0 / 0 | 91 / 1 | 0 / 0 | 0 / 0 | 109 | 4 | 7.4 |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 91 / 1 | 0 / 0 | 0 / 0 | 109 | 4 | 7.7 |
| lima | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 91 / 1 | 0 / 0 | 0 / 0 | 109 | 4 | 8.2 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 91 / 1 | 0 / 0 | 0 / 0 | 109 | 4 | 8.6 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Files | Σ worker files/s | Worker 00 records | Worker 01 records |
| --- | ---: | ---: | ---: | ---: |
| docker / sqlite | 512 | 5539.33 | 256 | 256 |
| docker / postgresql | 512 | 3382.03 | 256 | 256 |
| docker / pg-colocated | 512 | 3998.46 | 256 | 256 |
| native / sqlite | 512 | 1863.24 | 256 | 256 |
| native / postgresql | 512 | 1493.13 | 256 | 256 |
| lima / sqlite | 512 | 6552.90 | 256 | 256 |
| lima / postgresql | 512 | 5313.20 | 256 | 256 |
| apple-container / sqlite | 512 | 5762.96 | 256 | 256 |
| apple-container / postgresql | 512 | 5597.54 | 256 | 256 |

## L02

Read 512 files: two workers × 256 files, 4 KiB/file, 64 files/directory. two-worker-256x4k-as-host-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 6.59 | 371.07 | 18.69 | 3700.05 | 18.82 | 14.90 | 285.55 | 20.88 | 4429.95 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.91 | 378.09 | 28.89 | 3718.93 | 61.71 | 16.42 | 301.56 | 8.55 | 4514.15 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.97 | 402.88 | 27.08 | 3709.24 | 37.24 | 18.62 | 266.84 | 9.20 | 4471.10 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 5.62 | 45.13 | 38.69 | 3745.31 | 86.93 | 32.25 | 73.26 | 12.63 | 4034.20 | 1.01 | 4.62 | 0.91 |
| native | postgresql | PASS | COMPLETE | 6.09 | 47.51 | 46.50 | 3747.62 | 121.88 | 37.63 | 68.25 | 8.18 | 4077.57 | 1.01 | 1.98 | 0.90 |
| lima | sqlite | PASS | COMPLETE | 5.89 | 710.07 | 18.67 | 3819.41 | 18.35 | 16.69 | 103.58 | 21.24 | 4708.02 | 1.03 | 0.98 | 1.06 |
| lima | postgresql | PASS | COMPLETE | 6.61 | 686.55 | 39.55 | 3863.77 | 62.02 | 15.60 | 95.54 | 8.66 | 4771.70 | 1.04 | 1.01 | 1.06 |
| apple-container | sqlite | PASS | COMPLETE | 4.79 | 49.62 | 18.11 | 3839.48 | 26.48 | 43.95 | 41.08 | 18.24 | 4036.95 | 1.04 | 1.41 | 0.91 |
| apple-container | postgresql | PASS | COMPLETE | 5.29 | 66.16 | 31.57 | 3896.73 | 60.87 | 17.34 | 39.47 | 9.06 | 4121.20 | 1.05 | 0.99 | 0.91 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 3 / 2 | 15 / 0 | 38 / 0 | 74 / 1 | 0 / 0 | 0 / 0 | 130 | 3 | 4.6 |
| docker | pg-colocated | 3 / 2 | 15 / 0 | 38 / 0 | 74 / 1 | 0 / 0 | 0 / 0 | 130 | 3 | 4.4 |
| native | postgresql | 4 / 3 | 15 / 0 | 39 / 0 | 73 / 1 | 0 / 0 | 0 / 0 | 131 | 4 | 4.9 |
| lima | postgresql | 3 / 2 | 15 / 0 | 39 / 0 | 74 / 1 | 0 / 0 | 0 / 0 | 131 | 3 | 5.4 |
| apple-container | postgresql | 3 / 2 | 15 / 0 | 38 / 0 | 74 / 1 | 0 / 0 | 0 / 0 | 130 | 3 | 7.5 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Files | Σ worker files/s | Worker 00 records | Worker 01 records |
| --- | ---: | ---: | ---: | ---: |
| docker / pg-colocated | 512 | 6088.10 | 256 | 256 |
| docker / postgresql | 512 | 6850.11 | 256 | 256 |
| docker / sqlite | 512 | 7319.82 | 256 | 256 |
| native / postgresql | 512 | 5889.09 | 256 | 256 |
| native / sqlite | 512 | 6101.84 | 256 | 256 |
| lima / postgresql | 512 | 5935.53 | 256 | 256 |
| lima / sqlite | 512 | 9411.87 | 256 | 256 |
| apple-container / postgresql | 512 | 4701.50 | 256 | 256 |
| apple-container / sqlite | 512 | 8166.72 | 256 | 256 |

## L03

Stat 512 files: two workers × 256 files, 4 KiB/file, 64 files/directory. two-worker-256x4k-as-host-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 4.60 | 578.35 | 20.16 | 4068.03 | 22.75 | 17.42 | 356.08 | 34.25 | 5097.03 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.74 | 603.06 | 47.23 | 3764.84 | 96.30 | 21.22 | 562.95 | 8.72 | 5104.31 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.70 | 462.20 | 23.17 | 3683.96 | 34.02 | 15.76 | 282.46 | 8.42 | 4509.99 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 4.37 | 48.13 | 44.26 | 3726.00 | 106.45 | 40.70 | 101.14 | 12.61 | 4079.28 | 0.92 | 4.68 | 0.80 |
| native | postgresql | PASS | COMPLETE | 4.24 | 50.53 | 47.59 | 3728.89 | 135.20 | 29.25 | 67.91 | 35.22 | 4094.58 | 0.99 | 1.40 | 0.80 |
| lima | sqlite | PASS | COMPLETE | 5.44 | 692.77 | 18.02 | 3782.01 | 19.52 | 16.45 | 97.19 | 15.57 | 4641.53 | 0.93 | 0.86 | 0.91 |
| lima | postgresql | PASS | COMPLETE | 5.29 | 699.37 | 25.51 | 3798.57 | 59.71 | 15.93 | 99.01 | 9.43 | 4707.53 | 1.01 | 0.62 | 0.92 |
| apple-container | sqlite | PASS | COMPLETE | 5.14 | 57.31 | 16.54 | 3808.23 | 23.65 | 14.78 | 38.77 | 14.93 | 3974.20 | 0.94 | 1.04 | 0.78 |
| apple-container | postgresql | PASS | COMPLETE | 4.66 | 63.85 | 27.35 | 3847.41 | 72.76 | 42.82 | 37.22 | 8.97 | 4100.38 | 1.02 | 0.76 | 0.80 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 3 / 2 | 15 / 0 | 37 / 0 | 74 / 1 | 0 / 0 | 0 / 0 | 129 | 3 | 9.9 |
| docker | pg-colocated | 3 / 2 | 15 / 0 | 37 / 0 | 74 / 1 | 0 / 0 | 0 / 0 | 129 | 3 | 4.3 |
| native | postgresql | 4 / 3 | 15 / 0 | 38 / 0 | 73 / 1 | 0 / 0 | 0 / 0 | 130 | 4 | 6.7 |
| lima | postgresql | 3 / 2 | 15 / 0 | 38 / 0 | 74 / 1 | 0 / 0 | 0 / 0 | 130 | 3 | 4.9 |
| apple-container | postgresql | 3 / 2 | 15 / 0 | 37 / 0 | 74 / 1 | 0 / 0 | 0 / 0 | 129 | 3 | 5.9 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Files | Σ worker files/s | Worker 00 records | Worker 01 records |
| --- | ---: | ---: | ---: | ---: |
| docker / sqlite | 512 | 11578.81 | 0 | 0 |
| docker / postgresql | 512 | 8459.37 | 0 | 0 |
| docker / pg-colocated | 512 | 15737.65 | 0 | 0 |
| native / sqlite | 512 | 14945.32 | 0 | 0 |
| native / postgresql | 512 | 9644.72 | 0 | 0 |
| lima / sqlite | 512 | 25416.89 | 0 | 0 |
| lima / postgresql | 512 | 15032.19 | 0 | 0 |
| apple-container / sqlite | 512 | 17427.43 | 0 | 0 |
| apple-container / postgresql | 512 | 10689.21 | 0 | 0 |

## L04

Rename 512 files: two workers × 256 files, 4 KiB/file, 64 files/directory. two-worker-256x4k-as-host-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 5.69 | 421.42 | 18.91 | 3779.77 | 44.31 | 15.46 | 296.19 | 18.12 | 4594.18 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 6.19 | 406.18 | 27.99 | 3784.22 | 114.03 | 16.40 | 302.68 | 8.58 | 4660.08 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 6.48 | 388.77 | 21.77 | 3813.04 | 65.40 | 17.43 | 284.51 | 8.59 | 4599.49 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 6.42 | 42.77 | 39.15 | 3939.31 | 116.21 | 39.08 | 74.48 | 12.49 | 4263.48 | 1.04 | 2.62 | 0.93 |
| native | postgresql | PASS | COMPLETE | 6.00 | 43.05 | 39.29 | 3958.41 | 143.73 | 33.03 | 60.84 | 8.56 | 4286.92 | 1.05 | 1.26 | 0.92 |
| lima | sqlite | PASS | COMPLETE | 5.27 | 687.67 | 19.07 | 3881.35 | 49.78 | 16.32 | 93.28 | 14.44 | 4761.91 | 1.03 | 1.12 | 1.04 |
| lima | postgresql | PASS | COMPLETE | 5.20 | 694.49 | 26.84 | 3896.66 | 96.11 | 15.18 | 121.81 | 36.07 | 4887.17 | 1.03 | 0.84 | 1.05 |
| apple-container | sqlite | PASS | COMPLETE | 5.25 | 64.81 | 18.59 | 3912.74 | 56.60 | 11.80 | 38.17 | 15.22 | 4117.94 | 1.04 | 1.28 | 0.90 |
| apple-container | postgresql | PASS | COMPLETE | 5.23 | 60.07 | 28.40 | 3936.09 | 136.74 | 12.51 | 36.52 | 9.05 | 4219.38 | 1.04 | 1.20 | 0.91 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 3 / 2 | 15 / 0 | 44 / 0 | 92 / 1 | 0 / 0 | 0 / 0 | 154 | 3 | 6.2 |
| docker | pg-colocated | 3 / 2 | 15 / 0 | 45 / 0 | 94 / 1 | 0 / 0 | 0 / 0 | 157 | 3 | 6.3 |
| native | postgresql | 4 / 3 | 15 / 0 | 45 / 0 | 91 / 1 | 0 / 0 | 0 / 0 | 155 | 4 | 6.9 |
| lima | postgresql | 3 / 2 | 15 / 0 | 44 / 0 | 93 / 1 | 0 / 0 | 0 / 0 | 155 | 3 | 6.7 |
| apple-container | postgresql | 3 / 2 | 15 / 0 | 45 / 0 | 95 / 1 | 0 / 0 | 0 / 0 | 158 | 3 | 7.5 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Files | Σ worker files/s | Worker 00 records | Worker 01 records |
| --- | ---: | ---: | ---: | ---: |
| docker / pg-colocated | 512 | 3161.65 | 0 | 0 |
| docker / postgresql | 512 | 3440.19 | 0 | 0 |
| docker / sqlite | 512 | 3460.27 | 0 | 0 |
| native / postgresql | 512 | 1697.16 | 0 | 0 |
| native / sqlite | 512 | 1786.44 | 0 | 0 |
| lima / postgresql | 512 | 4149.59 | 0 | 0 |
| lima / sqlite | 512 | 4144.06 | 0 | 0 |
| apple-container / postgresql | 512 | 3523.51 | 0 | 0 |
| apple-container / sqlite | 512 | 4293.72 | 0 | 0 |

## L05

Delete 512 files: two workers × 256 files, 4 KiB/file, 64 files/directory. two-worker-256x4k-as-host-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 4.75 | 399.84 | 17.69 | 3718.59 | 49.66 | 15.14 | 281.24 | 19.02 | 4501.17 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 4.49 | 495.80 | 29.78 | 3728.38 | 101.04 | 16.16 | 298.45 | 8.26 | 4677.87 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.63 | 394.33 | 26.43 | 3685.86 | 62.33 | 15.30 | 268.79 | 8.97 | 4462.00 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 5.07 | 43.31 | 42.21 | 3797.61 | 100.50 | 30.94 | 63.88 | 12.82 | 4091.27 | 1.02 | 2.02 | 0.91 |
| native | postgresql | PASS | COMPLETE | 5.30 | 46.52 | 45.96 | 3790.54 | 193.52 | 27.53 | 68.04 | 8.54 | 4180.65 | 1.02 | 1.92 | 0.89 |
| lima | sqlite | PASS | COMPLETE | 4.79 | 688.04 | 18.79 | 3850.85 | 42.87 | 16.00 | 100.81 | 14.47 | 4731.84 | 1.04 | 0.86 | 1.05 |
| lima | postgresql | PASS | COMPLETE | 4.33 | 706.18 | 31.24 | 3869.87 | 99.45 | 15.48 | 100.12 | 8.77 | 4831.11 | 1.04 | 0.98 | 1.03 |
| apple-container | sqlite | PASS | COMPLETE | 4.05 | 60.15 | 17.05 | 3848.00 | 57.73 | 13.44 | 38.18 | 16.50 | 4051.05 | 1.03 | 1.16 | 0.90 |
| apple-container | postgresql | PASS | COMPLETE | 4.14 | 63.89 | 27.92 | 3867.19 | 123.13 | 13.57 | 37.02 | 8.83 | 4141.55 | 1.04 | 1.22 | 0.89 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 3 / 2 | 15 / 0 | 37 / 0 | 100 / 1 | 0 / 0 | 0 / 0 | 155 | 3 | 5.6 |
| docker | pg-colocated | 3 / 2 | 15 / 0 | 37 / 0 | 100 / 1 | 0 / 0 | 0 / 0 | 155 | 3 | 4.5 |
| native | postgresql | 4 / 3 | 15 / 0 | 39 / 0 | 99 / 1 | 0 / 0 | 0 / 0 | 157 | 4 | 5.8 |
| lima | postgresql | 3 / 2 | 15 / 0 | 37 / 0 | 100 / 1 | 0 / 0 | 0 / 0 | 155 | 3 | 6.5 |
| apple-container | postgresql | 3 / 2 | 15 / 0 | 37 / 0 | 100 / 1 | 0 / 0 | 0 / 0 | 155 | 3 | 5.3 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Files | Σ worker files/s | Worker 00 records | Worker 01 records |
| --- | ---: | ---: | ---: | ---: |
| docker / sqlite | 512 | 6373.85 | 0 | 0 |
| docker / postgresql | 512 | 6343.66 | 0 | 0 |
| docker / pg-colocated | 512 | 8021.71 | 0 | 0 |
| native / sqlite | 512 | 3798.80 | 0 | 0 |
| native / postgresql | 512 | 3630.93 | 0 | 0 |
| lima / sqlite | 512 | 9337.72 | 0 | 0 |
| lima / postgresql | 512 | 5214.46 | 0 | 0 |
| apple-container / sqlite | 512 | 7653.99 | 0 | 0 |
| apple-container / postgresql | 512 | 6448.85 | 0 | 0 |

## Preparation, limits and cleanup

Attempted row preparation: 187.826 s total; maximum 6.224 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **INCOMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. 

Final disposition recorded by campaign owner.



Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

Smallfile upstream rate = 256/T00 + 256/T01 files/s. Each worker timer starts after directory, seed/buffer preparation and gate waiting; it uses upstream time.time(). It excludes launcher/startup work, so it is not 512 divided by CLI Exec time. Its control-file fsyncs are intrinsic upstream behavior; payload fsync is disabled. The declared 4KiB payload pattern is nonzero and compressible.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

