# fsstress — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: INCOMPLETE.** 9 registered rows; execution {'PASS': 2, 'FAIL': 7}. Final infrastructure cleanup: **INCOMPLETE**.

LayerFS `76a32a9a10e7b7b1379699ece52d45e233da5a50` (pg-r2 at 76a32a9a10 (frozen final head, layerfs-project #98); gate-05 sealed release artifacts). Harness: rows ran at `a4f55ca` (branch `pg-r2-bench`, local; runner and cases identical to round 1's `c731387`); report from the same commit's shared/src/report.py. Gate-05 sealed release artifacts, built from `76a32a9a10` (clean detached checkout in the bench gatebuild worktree) through the worktree launcher: macOS CLI and daemon with `layerfs-node/postgresql` (build `build-macos-d1ee1858a2e64ecdba069d39d801533b`; CLI sha256 `5f673410…`, daemon `d32ec78a…`) and the Linux aarch64 bundle with PostgreSQL support (daemon `--features layerfs-daemon/postgresql`, worker CLI `--no-default-features --features postgresql`; bundle hash `cfe04f0c…`, Sandbox image `1d91885d…` saved from the registered runtime image `afa1ef9c…`). Fresh LayerFS home; native daemon set with `machine update native --daemon`; fresh Docker worker; fresh Lima `pgr2b-lima` and Apple Container `pgr2b-apple` (2 CPUs / 2G each). Six-suite guests use the tool image `pgr2b-six-tools:20261106` (`ac383307…`, archive config `fcad6365…`) built from round 1's unchanged tool context; Lima `pgr2b-lima6` and Apple Container `pgr2b-apple6` were created from its archive.

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 9}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Close is Sandbox close; Store release is Store remove (SQLite) or disconnect (PostgreSQL). End-to-end is the sum of the measured calls from create through Store release, without harness gaps; it excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: macOS 26.4.1, Apple M3 Max, 14 CPUs, 36 GiB; Docker Desktop 29.5.2 VM 8 CPUs / 7.75 GiB shared with other agents' builds; Lima and Apple Container machines 2 CPUs / 2 GiB each; PostgreSQL 17.11 container `pgr2b-pg` with 2 CPUs / 2 GiB (pg_stat_statements, synchronous_commit=off), host-published port 55442, co-located on the default bridge; 1-minute load during rows 4.4–5.1, median 5.1. Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

## PostgreSQL minus SQLite

Median over cells of (PostgreSQL arm − SQLite) per machine, milliseconds, using only cells where both rows passed. Close is Sandbox close; Store release is `store disconnect` (PostgreSQL) versus `store remove` (SQLite), which the product does not unify.

| Machine | Arm | Cells | Create | Mount | Exec | Commit | Unmount | Close | Store release | End-to-end |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| native | postgresql | 1 | +2.3 | +3.5 | +1.6 | +38.5 | -5.4 | +0.2 | -2.5 | +38.2 |

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `5f673410fc5125081485326443bf368f9d501af5f678dd3bb1c7bd58f1d32e3c` |
| Native daemon | `d32ec78aa0e1a07f58a223b79a0aab7dabfc98274701be595de6c5f6bff1836d` |
| Linux bundle seal | `cfe04f0cb50472f51e0b8397360558b87e501f75bfea76ba048f80d68bdad953` |
| Docker tool image | `sha256:ac3833075ba13404feeacc765ddb5b5cc293b900eda1b60aea4fd94e141ca264` |
| Namespace archive config | `sha256:fcad636533c35f9ac95f0f4026d6db06ff58e61f3bb489b447f9a7944c4558db` |

## S01

Two processes × 512 requested operation slots, seed 1; frozen operation weights and per-operation allocation bounds. Effective work, skipped slots and expected errno are separate below. fsstress-S01-v2.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | FAIL | COMPLETE | 4.76 | 404.28 | 18.50 | 206.80 | — | — | 242.85 | 20.27 | — | — | — | — |
| docker | postgresql | FAIL | COMPLETE | 4.76 | 402.79 | 29.27 | 161.77 | — | — | 229.62 | 8.85 | — | — | — | — |
| docker | pg-colocated | FAIL | COMPLETE | 5.10 | 377.80 | 21.06 | 308.06 | — | — | 202.61 | 9.26 | — | — | — | — |
| native | sqlite | PASS | COMPLETE | 4.39 | 43.79 | 41.24 | 419.36 | 227.69 | 39.45 | 65.14 | 11.78 | 848.46 | — | — | — |
| native | postgresql | PASS | COMPLETE | 4.39 | 46.09 | 44.75 | 420.95 | 266.21 | 34.02 | 65.34 | 9.26 | 886.62 | — | — | — |
| lima | sqlite | FAIL | COMPLETE | 5.10 | 698.28 | 19.84 | 152.42 | — | — | 95.70 | 15.28 | — | — | — | — |
| lima | postgresql | FAIL | COMPLETE | 5.09 | 698.83 | 27.96 | 170.27 | — | — | 93.55 | 9.27 | — | — | — | — |
| apple-container | sqlite | FAIL | COMPLETE | 5.09 | 68.44 | 18.36 | 165.21 | — | — | 35.58 | 15.23 | — | — | — | — |
| apple-container | postgresql | FAIL | COMPLETE | 5.09 | 69.92 | 27.53 | 182.38 | — | — | 36.20 | 8.18 | — | — | — | — |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | — / — | — / — | 0 / 0 | 18 | 3 | 0.4 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 0 / 0 | — / — | — / — | 0 / 0 | 18 | 3 | 0.4 |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 83 / 1 | 0 / 0 | 0 / 0 | 101 | 4 | 8.3 |
| lima | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | — / — | — / — | 0 / 0 | 18 | 3 | 0.4 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | — / — | — / — | 0 / 0 | 18 | 3 | 0.4 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Requested slots | Completed slots | Effective operations | Skipped slots | Expected errno | Unexpected errors | Page bytes | Requested write bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| native / sqlite | 1024 | 1024 | 921 | 61 | 42 | 0 | 16384 | 27481153 |
| native / postgresql | 1024 | 1024 | 921 | 61 | 42 | 0 | 16384 | 27481153 |

- docker/sqlite, docker/postgresql, docker/pg-colocated, lima/sqlite, lima/postgresql, apple-container/sqlite, apple-container/postgresql: exec: workload exit 1

## Preparation, limits and cleanup

Attempted row preparation: 1.774 s total; maximum 0.298 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **INCOMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. 

Final disposition recorded by campaign owner.



Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

