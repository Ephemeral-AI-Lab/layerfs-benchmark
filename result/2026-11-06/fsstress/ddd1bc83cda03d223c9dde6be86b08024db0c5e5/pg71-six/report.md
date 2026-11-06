# fsstress — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: INCOMPLETE.** 9 registered rows; execution {'PASS': 2, 'FAIL': 7}. Final infrastructure cleanup: **INCOMPLETE**.

LayerFS `ddd1bc83cda03d223c9dde6be86b08024db0c5e5` (branch `pg-perf` at `ddd1bc83cd` (worktree layerfs-pg-perf, read-only source); 28 commits after the baseline b919f50eaf). Harness: `c731387` (branch `pg-perf-62`, local, unpushed); suite harness unchanged since the published 2026-11-06 run apart from the shared runner arms/observer of #62. Built from `ddd1bc83cd` through the worktree launcher, release profile: macOS CLI and daemon with `layerfs-node/postgresql` (build `build-macos-ecee12a823984af49e8d4d9cfa169268`; CLI sha256 `04a4c120…88ee`, daemon `0472e2a6…c7ceef`) and the Linux aarch64 bundle with PostgreSQL (bundle hash `4c7499ce…dabc45f`, sealed with the baseline Sandbox image `66aeb6bb…` so the guest image matches). Copied into a private cache after SHA-256 checks. Machines: native, docker worker (image = Sandbox image + /opt/fs-six-tools, `pg71-six-tools:20261106` 88f1d872…), fresh Lima `pg71-lima6` and Apple Container `pg71-apple6` created from that image; same PostgreSQL 17.11 server and settings (`pg_settings` dump identical).

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 9}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Close is Sandbox close; Store release is Store remove (SQLite) or disconnect (PostgreSQL). End-to-end is the sum of the measured calls from create through Store release, without harness gaps; it excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: macOS 26.4.1, Apple M3 Max, 14 CPUs, 36 GiB; Docker Desktop 29.5.2 VM 8 CPUs / 7.75 GiB shared with other agents' Rust builds and another benchmark campaign; Lima `pg71-lima6` and Apple Container `pg71-apple6` 2 CPUs / 2 GiB each; PostgreSQL 17.11 container `pgbench-pg` 2 CPUs / 2 GiB. Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

## #71 final verification notes

- **FAIL on every Linux guest row (7 rows: docker sqlite/postgresql/co-located, lima and apple-container sqlite/postgresql), as in the baseline:** fsstress `link` of a symlink inode returned EPERM 6 times (`unexpected_details`, e.g. `1/31: link d6/la d6/dc/ld 1`). The product restricts hard links to regular files; the baseline recorded the same failure on docker/sqlite and withdrew the other five. This is a retained product-capability failure, not an allowed errno; no rerun. Native rows PASS (Apple `link` follows the final symlink, so no symlink inode is linked).

Before = the published 2026-11-06 run at b919f50eaf (`result/2026-11-06/fsstress/b919f50eaf…/report.md`): different machines (fresh then, reused now), no co-located arm, no PostgreSQL observer, load and first-touch effects differ; one sample per row on both sides. Medians over cells that PASS in both.

| suite | machine | backend | rows PASS before → after | create | Exec | Commit | mount (after) | unmount (after) |
|---|---|---|---|---|---|---|---|---|
| fsstress | native | sqlite | 1/1 → 1/1 | 26 → 42 | 794 → 317 | 174 → 153 | 36 | 30 |
| fsstress | native | postgresql | 1/1 → 1/1 | 73 → 67 | 319 → 347 | 301 → 184 | 61 | 25 |
| fsstress | docker | sqlite | 0/1 → 0/1 | — | — | — | — | — |
| fsstress | docker | postgresql | 0/1 → 0/1 | — | — | — | — | — |
| fsstress | docker | pg-colocated | 0/0 → 0/1 | — | — | — | — | — |
| fsstress | lima | sqlite | 0/1 → 0/1 | — | — | — | — | — |
| fsstress | lima | postgresql | 0/1 → 0/1 | — | — | — | — | — |
| fsstress | apple-container | sqlite | 0/1 → 0/1 | — | — | — | — | — |
| fsstress | apple-container | postgresql | 0/1 → 0/1 | — | — | — | — | — |

| suite | machine | PG−SQLite create before → after | Exec | Commit |
|---|---|---|---|---|
| fsstress | native | +47 → +26 | -475 → +30 | +127 → +32 |

pg_stat_statements per phase, Docker PostgreSQL (statements/connections):

| suite cell | create | mount | Exec | Commit |
|---|---|---|---|---|
| fsstress S01 | 6/2 | 30/3 | 0/0 | — |

## PostgreSQL minus SQLite

Median over cells of (PostgreSQL arm − SQLite) per machine, milliseconds, using only cells where both rows passed. Close is Sandbox close; Store release is `store disconnect` (PostgreSQL) versus `store remove` (SQLite), which the product does not unify.

| Machine | Arm | Cells | Create | Mount | Exec | Commit | Unmount | Close | Store release | End-to-end |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| native | postgresql | 1 | +25.5 | +25.0 | +30.5 | +31.5 | -5.1 | -5.8 | -3.2 | +98.4 |

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `04a4c1202d0fab8ce2be764122a2637824e6a59d1030f05f9704eaecbc2f88ee` |
| Native daemon | `0472e2a60075008f79f34304d2c7669d7f47846c5fda36847d0ef34711c7ceef` |
| Linux bundle seal | `4c7499ceac02b7e471cb014c2f12404837421ed61c89b1c6e3a6e5c33dabc45f` |
| Docker tool image | `sha256:88f1d8720fec4f50f876bc9266ce8b76bbbcdab8aa857722c769f29d87d9d14c` |
| Namespace archive config | `sha256:504b072822cb4dad540ccb93f3e0e3d02d9225944b6857478d4d306e7e8a1861` |

## S01

Two processes × 512 requested operation slots, seed 1; frozen operation weights and per-operation allocation bounds. Effective work, skipped slots and expected errno are separate below. fsstress-S01-v2.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | FAIL | COMPLETE | 4.80 | 292.81 | 18.32 | 135.43 | — | — | 245.94 | 24.53 | — | — | — | — |
| docker | postgresql | FAIL | COMPLETE | 4.80 | 340.24 | 43.28 | 148.42 | — | — | 210.32 | 7.35 | — | — | — | — |
| docker | pg-colocated | FAIL | COMPLETE | 4.65 | 319.75 | 43.38 | 153.38 | — | — | 204.92 | 6.69 | — | — | — | — |
| native | sqlite | PASS | COMPLETE | 3.99 | 41.66 | 36.43 | 316.66 | 152.88 | 30.22 | 66.01 | 10.86 | 654.72 | — | — | — |
| native | postgresql | PASS | COMPLETE | 4.80 | 67.20 | 61.42 | 347.13 | 184.38 | 25.08 | 60.25 | 7.62 | 753.08 | — | — | — |
| lima | sqlite | FAIL | COMPLETE | 4.65 | 738.96 | 18.01 | 114.25 | — | — | 109.42 | 12.52 | — | — | — | — |
| lima | postgresql | FAIL | COMPLETE | 4.65 | 777.70 | 50.62 | 127.00 | — | — | 114.92 | 7.60 | — | — | — | — |
| apple-container | sqlite | FAIL | COMPLETE | 4.52 | 76.09 | 17.05 | 147.48 | — | — | 32.75 | 11.41 | — | — | — | — |
| apple-container | postgresql | FAIL | COMPLETE | 4.52 | 126.80 | 35.63 | 152.55 | — | — | 33.44 | 6.95 | — | — | — | — |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | — / — | — / — | 0 / 0 | 36 | 5 | 1.8 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 0 / 0 | — / — | — / — | 0 / 0 | 36 | 5 | 1.6 |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 90 / 2 | 0 / 0 | 0 / 0 | 120 | 6 | 6.6 |
| lima | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | — / — | — / — | 0 / 0 | 36 | 5 | 2.1 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 0 / 0 | — / — | — / — | 0 / 0 | 29 | 3 | 0.5 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Requested slots | Completed slots | Effective operations | Skipped slots | Expected errno | Unexpected errors | Page bytes | Requested write bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| native / sqlite | 1024 | 1024 | 921 | 61 | 42 | 0 | 16384 | 27481153 |
| native / postgresql | 1024 | 1024 | 921 | 61 | 42 | 0 | 16384 | 27481153 |

- docker/sqlite, docker/postgresql, docker/pg-colocated, lima/sqlite, lima/postgresql, apple-container/sqlite, apple-container/postgresql: exec: workload exit 1

## Preparation, limits and cleanup

Attempted row preparation: 1.267 s total; maximum 0.233 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **INCOMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. 

Final disposition recorded by campaign owner.



Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

