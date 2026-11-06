# fsx — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: INCOMPLETE.** 9 registered rows; execution {'PASS': 9}. Final infrastructure cleanup: **INCOMPLETE**.

LayerFS `76a32a9a10e7b7b1379699ece52d45e233da5a50` (pg-r2 at 76a32a9a10 (frozen final head, layerfs-project #98); gate-05 sealed release artifacts). Harness: rows ran at `a4f55ca` (branch `pg-r2-bench`, local; runner and cases identical to round 1's `c731387`); report from the same commit's shared/src/report.py. Gate-05 sealed release artifacts, built from `76a32a9a10` (clean detached checkout in the bench gatebuild worktree) through the worktree launcher: macOS CLI and daemon with `layerfs-node/postgresql` (build `build-macos-d1ee1858a2e64ecdba069d39d801533b`; CLI sha256 `5f673410…`, daemon `d32ec78a…`) and the Linux aarch64 bundle with PostgreSQL support (daemon `--features layerfs-daemon/postgresql`, worker CLI `--no-default-features --features postgresql`; bundle hash `cfe04f0c…`, Sandbox image `1d91885d…` saved from the registered runtime image `afa1ef9c…`). Fresh LayerFS home; native daemon set with `machine update native --daemon`; fresh Docker worker; fresh Lima `pgr2b-lima` and Apple Container `pgr2b-apple` (2 CPUs / 2G each). Six-suite guests use the tool image `pgr2b-six-tools:20261106` (`ac383307…`, archive config `fcad6365…`) built from round 1's unchanged tool context; Lima `pgr2b-lima6` and Apple Container `pgr2b-apple6` were created from its archive.

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 9}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Close is Sandbox close; Store release is Store remove (SQLite) or disconnect (PostgreSQL). End-to-end is the sum of the measured calls from create through Store release, without harness gaps; it excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: macOS 26.4.1, Apple M3 Max, 14 CPUs, 36 GiB; Docker Desktop 29.5.2 VM 8 CPUs / 7.75 GiB shared with other agents' builds; Lima and Apple Container machines 2 CPUs / 2 GiB each; PostgreSQL 17.11 container `pgr2b-pg` with 2 CPUs / 2 GiB (pg_stat_statements, synchronous_commit=off), host-published port 55442, co-located on the default bridge; 1-minute load during rows 3.9–4.8, median 4.6. Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

## PostgreSQL minus SQLite

Median over cells of (PostgreSQL arm − SQLite) per machine, milliseconds, using only cells where both rows passed. Close is Sandbox close; Store release is `store disconnect` (PostgreSQL) versus `store remove` (SQLite), which the product does not unify.

| Machine | Arm | Cells | Create | Mount | Exec | Commit | Unmount | Close | Store release | End-to-end |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 1 | -278.9 | +14.4 | -21.8 | +63.4 | -0.4 | +64.3 | -13.7 | -172.8 |
| docker | pg-colocated | 1 | -148.0 | +5.6 | -420.6 | +19.5 | +1.6 | -120.9 | -12.6 | -675.3 |
| native | postgresql | 1 | +19.3 | +7.9 | -18.4 | +45.4 | -3.0 | -2.9 | -3.1 | +45.3 |
| lima | postgresql | 1 | -24.6 | +8.1 | -45.9 | +59.3 | +1.9 | +2.4 | -6.6 | -5.4 |
| apple-container | postgresql | 1 | +11.5 | +9.4 | +38.7 | +34.9 | -0.7 | -2.1 | -8.0 | +83.7 |

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `5f673410fc5125081485326443bf368f9d501af5f678dd3bb1c7bd58f1d32e3c` |
| Native daemon | `d32ec78aa0e1a07f58a223b79a0aab7dabfc98274701be595de6c5f6bff1836d` |
| Linux bundle seal | `cfe04f0cb50472f51e0b8397360558b87e501f75bfea76ba048f80d68bdad953` |
| Docker tool image | `sha256:ac3833075ba13404feeacc765ddb5b5cc293b900eda1b60aea4fd94e141ca264` |
| Namespace archive config | `sha256:fcad636533c35f9ac95f0f4026d6db06ff58e61f3bb489b447f9a7944c4558db` |

## X01

1,000 operation slots, seed 1, file ≤8 MiB, operation ≤64 KiB; read/write/truncate and upstream consistency checks. Skipped slots remain explicit. fsx-X01-v2-secfs-portable.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 4.41 | 903.37 | 19.48 | 661.10 | 19.55 | 16.93 | 416.70 | 22.75 | 2059.88 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 4.54 | 624.43 | 33.90 | 639.32 | 82.94 | 16.50 | 480.97 | 9.04 | 1887.10 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.73 | 755.37 | 25.12 | 240.52 | 39.04 | 18.58 | 295.77 | 10.17 | 1384.57 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 3.92 | 39.22 | 40.43 | 381.55 | 81.97 | 28.84 | 64.46 | 11.86 | 648.33 | 0.58 | 4.19 | 0.31 |
| native | postgresql | PASS | COMPLETE | 4.41 | 58.56 | 48.31 | 363.16 | 127.38 | 25.83 | 61.58 | 8.81 | 693.62 | 0.57 | 1.54 | 0.37 |
| lima | sqlite | PASS | COMPLETE | 4.73 | 717.06 | 18.62 | 270.61 | 18.77 | 15.56 | 97.56 | 15.75 | 1153.94 | 0.41 | 0.96 | 0.56 |
| lima | postgresql | PASS | COMPLETE | 4.76 | 692.47 | 26.68 | 224.74 | 78.02 | 17.49 | 99.98 | 9.16 | 1148.54 | 0.35 | 0.94 | 0.61 |
| apple-container | sqlite | PASS | COMPLETE | 4.76 | 63.13 | 17.65 | 253.88 | 15.81 | 13.21 | 39.53 | 16.72 | 419.93 | 0.38 | 0.81 | 0.20 |
| apple-container | postgresql | PASS | COMPLETE | 4.61 | 74.67 | 27.01 | 292.58 | 50.68 | 12.46 | 37.45 | 8.74 | 503.59 | 0.46 | 0.61 | 0.27 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 61 / 1 | 0 / 0 | 0 / 0 | 79 | 4 | 4.5 |
| docker | pg-colocated | 4 / 3 | 14 / 0 | 0 / 0 | 61 / 1 | 0 / 0 | 0 / 0 | 79 | 4 | 3.2 |
| native | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 61 / 1 | 0 / 0 | 0 / 0 | 79 | 4 | 4.1 |
| lima | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 61 / 1 | 0 / 0 | 0 / 0 | 79 | 4 | 3.2 |
| apple-container | postgresql | 4 / 3 | 14 / 0 | 0 / 0 | 61 / 1 | 0 / 0 | 0 / 0 | 79 | 4 | 3.7 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Requested slots | Completed slots | Effective operations | Skipped slots | Reads | Writes | Truncates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker / sqlite | 1000 | 1000 | 997 | 3 | 539 | 237 | 221 |
| docker / postgresql | 1000 | 1000 | 997 | 3 | 539 | 237 | 221 |
| docker / pg-colocated | 1000 | 1000 | 997 | 3 | 539 | 237 | 221 |
| native / sqlite | 1000 | 1000 | 997 | 3 | 539 | 237 | 221 |
| native / postgresql | 1000 | 1000 | 997 | 3 | 539 | 237 | 221 |
| lima / sqlite | 1000 | 1000 | 997 | 3 | 539 | 237 | 221 |
| lima / postgresql | 1000 | 1000 | 997 | 3 | 539 | 237 | 221 |
| apple-container / sqlite | 1000 | 1000 | 997 | 3 | 539 | 237 | 221 |
| apple-container / postgresql | 1000 | 1000 | 997 | 3 | 539 | 237 | 221 |

## Preparation, limits and cleanup

Attempted row preparation: 2.452 s total; maximum 0.881 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **INCOMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. 

Final disposition recorded by campaign owner.



Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

