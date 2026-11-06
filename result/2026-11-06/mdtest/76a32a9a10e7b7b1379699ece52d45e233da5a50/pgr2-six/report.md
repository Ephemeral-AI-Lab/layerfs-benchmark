# mdtest — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: INCOMPLETE.** 18 registered rows; execution {'PASS': 4, 'NOT_RUN': 14}. Final infrastructure cleanup: **INCOMPLETE**.

LayerFS `76a32a9a10e7b7b1379699ece52d45e233da5a50` (pg-r2 at 76a32a9a10 (frozen final head, layerfs-project #98); gate-05 sealed release artifacts). Harness: rows ran at `a4f55ca` (branch `pg-r2-bench`, local; runner and cases identical to round 1's `c731387`); report from the same commit's shared/src/report.py. Gate-05 sealed release artifacts, built from `76a32a9a10` (clean detached checkout in the bench gatebuild worktree) through the worktree launcher: macOS CLI and daemon with `layerfs-node/postgresql` (build `build-macos-d1ee1858a2e64ecdba069d39d801533b`; CLI sha256 `5f673410…`, daemon `d32ec78a…`) and the Linux aarch64 bundle with PostgreSQL support (daemon `--features layerfs-daemon/postgresql`, worker CLI `--no-default-features --features postgresql`; bundle hash `cfe04f0c…`, Sandbox image `1d91885d…` saved from the registered runtime image `afa1ef9c…`). Fresh LayerFS home; native daemon set with `machine update native --daemon`; fresh Docker worker; fresh Lima `pgr2b-lima` and Apple Container `pgr2b-apple` (2 CPUs / 2G each). Six-suite guests use the tool image `pgr2b-six-tools:20261106` (`ac383307…`, archive config `fcad6365…`) built from round 1's unchanged tool context; Lima `pgr2b-lima6` and Apple Container `pgr2b-apple6` were created from its archive.

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 18}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Close is Sandbox close; Store release is Store remove (SQLite) or disconnect (PostgreSQL). End-to-end is the sum of the measured calls from create through Store release, without harness gaps; it excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: macOS 26.4.1, Apple M3 Max, 14 CPUs, 36 GiB; Docker Desktop 29.5.2 VM 8 CPUs / 7.75 GiB shared with other agents' builds; Lima and Apple Container machines 2 CPUs / 2 GiB each; PostgreSQL 17.11 container `pgr2b-pg` with 2 CPUs / 2 GiB (pg_stat_statements, synchronous_commit=off), host-published port 55442, co-located on the default bridge; 1-minute load during rows 3.4–4.1, median 3.8 (PASS rows). Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

## PostgreSQL minus SQLite

Median over cells of (PostgreSQL arm − SQLite) per machine, milliseconds, using only cells where both rows passed. Close is Sandbox close; Store release is `store disconnect` (PostgreSQL) versus `store remove` (SQLite), which the product does not unify.

| Machine | Arm | Cells | Create | Mount | Exec | Commit | Unmount | Close | Store release | End-to-end |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| native | postgresql | 2 | +6.1 | +4.0 | -115.8 | +30.4 | -5.0 | +0.5 | -3.1 | -82.8 |

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `5f673410fc5125081485326443bf368f9d501af5f678dd3bb1c7bd58f1d32e3c` |
| Native daemon | `d32ec78aa0e1a07f58a223b79a0aab7dabfc98274701be595de6c5f6bff1836d` |
| Linux bundle seal | `cfe04f0cb50472f51e0b8397360558b87e501f75bfea76ba048f80d68bdad953` |
| Docker tool image | `sha256:ac3833075ba13404feeacc765ddb5b5cc293b900eda1b60aea4fd94e141ca264` |
| Namespace archive config | `sha256:fcad636533c35f9ac95f0f4026d6db06ff58e61f3bb489b447f9a7944c4558db` |

## M01

512 empty files; one MPI rank; one create/stat/remove iteration. one-rank-512-create-stat-remove-v2.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| docker | postgresql | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| docker | pg-colocated | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| native | sqlite | PASS | COMPLETE | 4.10 | 46.87 | 40.75 | 1854.44 | 87.16 | 34.44 | 71.36 | 12.54 | 2147.56 | — | — | — |
| native | postgresql | PASS | COMPLETE | 4.01 | 53.04 | 45.01 | 1744.25 | 98.13 | 29.01 | 65.42 | 9.64 | 2044.49 | — | — | — |
| lima | sqlite | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| lima | postgresql | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| apple-container | sqlite | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| apple-container | postgresql | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.8 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Entries | Create ops/s | Stat ops/s | Remove ops/s |
| --- | ---: | ---: | ---: | ---: |
| native / sqlite | 512 | 1300.43 | 293412.17 | 1826.93 |
| native / postgresql | 512 | 1320.01 | 281637.20 | 1826.03 |

- docker/sqlite, docker/postgresql, docker/pg-colocated, lima/sqlite, lima/postgresql, apple-container/sqlite, apple-container/postgresql: Linux mdtest and Open MPI are not in the offline guest tool image (carry-over from round 1: the ior source and MPI build were removed at the 2026-11-06 cleanup; rebuilding needs network downloads)

## M02

512 directories; one MPI rank; one create/stat/remove iteration. one-rank-512-create-stat-remove-v2.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| docker | postgresql | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| docker | pg-colocated | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| native | sqlite | PASS | COMPLETE | 3.45 | 40.85 | 37.74 | 1695.34 | 81.16 | 34.65 | 61.43 | 12.04 | 1963.21 | — | — | — |
| native | postgresql | PASS | COMPLETE | 3.66 | 46.87 | 41.51 | 1573.95 | 131.09 | 30.04 | 68.46 | 8.71 | 1900.63 | — | — | — |
| lima | sqlite | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| lima | postgresql | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| apple-container | sqlite | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| apple-container | postgresql | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 33 / 1 | 0 / 0 | 0 / 0 | 51 | 4 | 0.9 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Entries | Create ops/s | Stat ops/s | Remove ops/s |
| --- | ---: | ---: | ---: | ---: |
| native / postgresql | 512 | 1699.32 | 261760.56 | 2730.65 |
| native / sqlite | 512 | 1438.83 | 287789.28 | 2019.21 |

- docker/pg-colocated, docker/postgresql, docker/sqlite, lima/postgresql, lima/sqlite, apple-container/postgresql, apple-container/sqlite: Linux mdtest and Open MPI are not in the offline guest tool image (carry-over from round 1: the ior source and MPI build were removed at the 2026-11-06 cleanup; rebuilding needs network downloads)

## Preparation, limits and cleanup

Attempted row preparation: 0.601 s total; maximum 0.252 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **INCOMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. 

Final disposition recorded by campaign owner.



Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

