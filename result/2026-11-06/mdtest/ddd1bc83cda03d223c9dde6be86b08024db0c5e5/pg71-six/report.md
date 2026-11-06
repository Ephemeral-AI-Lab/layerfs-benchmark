# mdtest — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: INCOMPLETE.** 18 registered rows; execution {'PASS': 4, 'NOT_RUN': 14}. Final infrastructure cleanup: **INCOMPLETE**.

LayerFS `ddd1bc83cda03d223c9dde6be86b08024db0c5e5` (branch `pg-perf` at `ddd1bc83cd` (worktree layerfs-pg-perf, read-only source); 28 commits after the baseline b919f50eaf). Harness: `c731387` (branch `pg-perf-62`, local, unpushed); suite harness unchanged since the published 2026-11-06 run apart from the shared runner arms/observer of #62. Built from `ddd1bc83cd` through the worktree launcher, release profile: macOS CLI and daemon with `layerfs-node/postgresql` (build `build-macos-ecee12a823984af49e8d4d9cfa169268`; CLI sha256 `04a4c120…88ee`, daemon `0472e2a6…c7ceef`) and the Linux aarch64 bundle with PostgreSQL (bundle hash `4c7499ce…dabc45f`, sealed with the baseline Sandbox image `66aeb6bb…` so the guest image matches). Copied into a private cache after SHA-256 checks. Machines: native, docker worker (image = Sandbox image + /opt/fs-six-tools, `pg71-six-tools:20261106` 88f1d872…), fresh Lima `pg71-lima6` and Apple Container `pg71-apple6` created from that image; same PostgreSQL 17.11 server and settings (`pg_settings` dump identical).

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 18}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Close is Sandbox close; Store release is Store remove (SQLite) or disconnect (PostgreSQL). End-to-end is the sum of the measured calls from create through Store release, without harness gaps; it excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: macOS 26.4.1, Apple M3 Max, 14 CPUs, 36 GiB; Docker Desktop 29.5.2 VM 8 CPUs / 7.75 GiB shared with other agents' Rust builds and another benchmark campaign; Lima `pg71-lima6` and Apple Container `pg71-apple6` 2 CPUs / 2 GiB each; PostgreSQL 17.11 container `pgbench-pg` 2 CPUs / 2 GiB. Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

## #71 final verification notes

- **NOT_RUN on docker, lima and apple-container (all arms, 14 rows):** Linux mdtest and Open MPI are not in the offline guest tool image; the ior source and MPI build of the 2026-11-06 campaign were removed at its cleanup and rebuilding needs network downloads. M01 guest selections were recorded NOT_RUN by `prepare` in campaign.json; their row receipts are absent because the order cursor had already passed (native M02 ran first). Native M01–M02 PASS on both backends.

Before = the published 2026-11-06 run at b919f50eaf (`result/2026-11-06/mdtest/b919f50eaf…/report.md`): different machines (fresh then, reused now), no co-located arm, no PostgreSQL observer, load and first-touch effects differ; one sample per row on both sides. Medians over cells that PASS in both.

| suite | machine | backend | rows PASS before → after | create | Exec | Commit | mount (after) | unmount (after) |
|---|---|---|---|---|---|---|---|---|
| mdtest | native | sqlite | 2/2 → 2/2 | 33 → 39 | 1484 → 1505 | 75 → 40 | 37 | 29 |
| mdtest | native | postgresql | 2/2 → 2/2 | 85 → 41 | 1513 → 1465 | 121 → 55 | 50 | 22 |
| mdtest | docker | sqlite | 2/2 → 0/2 | — | — | — | — | — |
| mdtest | docker | postgresql | 2/2 → 0/2 | — | — | — | — | — |
| mdtest | docker | pg-colocated | 0/0 → 0/2 | — | — | — | — | — |
| mdtest | lima | sqlite | 2/2 → 0/2 | — | — | — | — | — |
| mdtest | lima | postgresql | 2/2 → 0/2 | — | — | — | — | — |
| mdtest | apple-container | sqlite | 2/2 → 0/2 | — | — | — | — | — |
| mdtest | apple-container | postgresql | 2/2 → 0/2 | — | — | — | — | — |

| suite | machine | PG−SQLite create before → after | Exec | Commit |
|---|---|---|---|---|
| mdtest | native | +52 → +2 | +29 → -40 | +46 → +15 |

pg_stat_statements per phase, Docker PostgreSQL (statements/connections):

| suite cell | create | mount | Exec | Commit |
|---|---|---|---|---|

## PostgreSQL minus SQLite

Median over cells of (PostgreSQL arm − SQLite) per machine, milliseconds, using only cells where both rows passed. Close is Sandbox close; Store release is `store disconnect` (PostgreSQL) versus `store remove` (SQLite), which the product does not unify.

| Machine | Arm | Cells | Create | Mount | Exec | Commit | Unmount | Close | Store release | End-to-end |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| native | postgresql | 2 | +2.3 | +12.1 | -39.7 | +14.8 | -7.0 | -6.6 | -2.3 | -26.3 |

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `04a4c1202d0fab8ce2be764122a2637824e6a59d1030f05f9704eaecbc2f88ee` |
| Native daemon | `0472e2a60075008f79f34304d2c7669d7f47846c5fda36847d0ef34711c7ceef` |
| Linux bundle seal | `4c7499ceac02b7e471cb014c2f12404837421ed61c89b1c6e3a6e5c33dabc45f` |
| Docker tool image | `sha256:88f1d8720fec4f50f876bc9266ce8b76bbbcdab8aa857722c769f29d87d9d14c` |
| Namespace archive config | `sha256:504b072822cb4dad540ccb93f3e0e3d02d9225944b6857478d4d306e7e8a1861` |

## M01

512 empty files; one MPI rank; one create/stat/remove iteration. one-rank-512-create-stat-remove-v2.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| docker | postgresql | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| docker | pg-colocated | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| native | sqlite | PASS | COMPLETE | 2.91 | 39.32 | 37.15 | 1577.47 | 40.23 | 30.62 | 63.06 | 10.78 | 1798.62 | — | — | — |
| native | postgresql | PASS | COMPLETE | 2.91 | 40.53 | 47.60 | 1504.63 | 56.10 | 18.57 | 54.78 | 7.56 | 1729.77 | — | — | — |
| lima | sqlite | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| lima | postgresql | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| apple-container | sqlite | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| apple-container | postgresql | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 67 | 6 | 0.9 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Entries | Create ops/s | Stat ops/s | Remove ops/s |
| --- | ---: | ---: | ---: | ---: |
| native / sqlite | 512 | 1996.76 | 435418.42 | 3099.29 |
| native / postgresql | 512 | 2131.61 | 388473.89 | 2642.25 |

- docker/sqlite, docker/postgresql, docker/pg-colocated, lima/sqlite, lima/postgresql, apple-container/sqlite, apple-container/postgresql: Linux mdtest and Open MPI are not in the offline guest tool image: the ior source and MPI build of the 2026-11-06 campaign were removed at its cleanup, and rebuilding them needs network downloads

## M02

512 directories; one MPI rank; one create/stat/remove iteration. one-rank-512-create-stat-remove-v2.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| docker | postgresql | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| docker | pg-colocated | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| native | sqlite | PASS | COMPLETE | 2.92 | 38.02 | 37.81 | 1432.40 | 39.77 | 27.78 | 62.26 | 9.30 | 1647.33 | — | — | — |
| native | postgresql | PASS | COMPLETE | 2.92 | 41.47 | 51.51 | 1425.88 | 53.59 | 25.83 | 57.32 | 8.00 | 1663.60 | — | — | — |
| lima | sqlite | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| lima | postgresql | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| apple-container | sqlite | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |
| apple-container | postgresql | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | — | — | — | — | — |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 67 | 6 | 0.9 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Entries | Create ops/s | Stat ops/s | Remove ops/s |
| --- | ---: | ---: | ---: | ---: |
| native / postgresql | 512 | 2195.31 | 390806.85 | 3881.61 |
| native / sqlite | 512 | 2301.26 | 399383.23 | 3734.03 |

- docker/pg-colocated, docker/postgresql, docker/sqlite, lima/postgresql, lima/sqlite, apple-container/postgresql, apple-container/sqlite: Linux mdtest and Open MPI are not in the offline guest tool image: the ior source and MPI build of the 2026-11-06 campaign were removed at its cleanup, and rebuilding them needs network downloads

## Preparation, limits and cleanup

Attempted row preparation: 0.377 s total; maximum 0.157 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **INCOMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. 

Final disposition recorded by campaign owner.



Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

