# pjdfstest — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: INCOMPLETE.** 36 registered rows; execution {'PASS': 36}. Final infrastructure cleanup: **INCOMPLETE**.

LayerFS `ddd1bc83cda03d223c9dde6be86b08024db0c5e5` (branch `pg-perf` at `ddd1bc83cd` (worktree layerfs-pg-perf, read-only source); 28 commits after the baseline b919f50eaf). Harness: `c731387` (branch `pg-perf-62`, local, unpushed); suite harness unchanged since the published 2026-11-06 run apart from the shared runner arms/observer of #62. Built from `ddd1bc83cd` through the worktree launcher, release profile: macOS CLI and daemon with `layerfs-node/postgresql` (build `build-macos-ecee12a823984af49e8d4d9cfa169268`; CLI sha256 `04a4c120…88ee`, daemon `0472e2a6…c7ceef`) and the Linux aarch64 bundle with PostgreSQL (bundle hash `4c7499ce…dabc45f`, sealed with the baseline Sandbox image `66aeb6bb…` so the guest image matches). Copied into a private cache after SHA-256 checks. Machines: native, docker worker (image = Sandbox image + /opt/fs-six-tools, `pg71-six-tools:20261106` 88f1d872…), fresh Lima `pg71-lima6` and Apple Container `pg71-apple6` created from that image; same PostgreSQL 17.11 server and settings (`pg_settings` dump identical).

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 36}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Close is Sandbox close; Store release is Store remove (SQLite) or disconnect (PostgreSQL). End-to-end is the sum of the measured calls from create through Store release, without harness gaps; it excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: macOS 26.4.1, Apple M3 Max, 14 CPUs, 36 GiB; Docker Desktop 29.5.2 VM 8 CPUs / 7.75 GiB shared with other agents' Rust builds and another benchmark campaign; Lima `pg71-lima6` and Apple Container `pg71-apple6` 2 CPUs / 2 GiB each; PostgreSQL 17.11 container `pgbench-pg` 2 CPUs / 2 GiB. Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

## #71 final verification notes

- All 36 rows PASS: P01 4/4, P02 6/6, P03 5/5, P04 14/14 assertions on every machine and backend, including the co-located arm.

Before = the published 2026-11-06 run at b919f50eaf (`result/2026-11-06/pjdfstest/b919f50eaf…/report.md`): different machines (fresh then, reused now), no co-located arm, no PostgreSQL observer, load and first-touch effects differ; one sample per row on both sides. Medians over cells that PASS in both.

| suite | machine | backend | rows PASS before → after | create | Exec | Commit | mount (after) | unmount (after) |
|---|---|---|---|---|---|---|---|---|
| pjdfstest | native | sqlite | 4/4 → 4/4 | 44 → 40 | 603 → 225 | 80 → 57 | 34 | 28 |
| pjdfstest | native | postgresql | 4/4 → 4/4 | 91 → 43 | 192 → 190 | 128 → 68 | 46 | 25 |
| pjdfstest | docker | sqlite | 4/4 → 4/4 | 315 → 282 | 135 → 121 | 13 → 14 | 19 | 13 |
| pjdfstest | docker | postgresql | 4/4 → 4/4 | 545 → 310 | 115 → 105 | 39 → 35 | 46 | 13 |
| pjdfstest | docker | pg-colocated | 0/0 → 4/4 | — → 324 | — → 125 | — → 24 | 45 | 14 |
| pjdfstest | lima | sqlite | 4/4 → 4/4 | 752 → 739 | 79 → 95 | 15 → 13 | 20 | 13 |
| pjdfstest | lima | postgresql | 4/4 → 4/4 | 931 → 769 | 75 → 72 | 40 → 34 | 47 | 13 |
| pjdfstest | apple-container | sqlite | 4/4 → 4/4 | 65 → 68 | 117 → 100 | 12 → 13 | 17 | 12 |
| pjdfstest | apple-container | postgresql | 4/4 → 4/4 | 336 → 134 | 112 → 99 | 81 → 68 | 38 | 13 |

| suite | machine | PG−SQLite create before → after | Exec | Commit |
|---|---|---|---|---|
| pjdfstest | native | +47 → +3 | -31 → +5 | +44 → +15 |
| pjdfstest | docker | +222 → +31 | -16 → -11 | +26 → +22 |
| pjdfstest | lima | +177 → +28 | -4 → -16 | +25 → +22 |
| pjdfstest | apple-container | +262 → +65 | -4 → -5 | +68 → +54 |

pg_stat_statements per phase, Docker PostgreSQL (statements/connections):

| suite cell | create | mount | Exec | Commit |
|---|---|---|---|---|
| pjdfstest P01 | 6/2 | 30/3 | 0/0 | 37/2 |
| pjdfstest P02 | 6/2 | 30/3 | 0/0 | 37/2 |
| pjdfstest P03 | 6/2 | 30/3 | 0/0 | 37/2 |
| pjdfstest P04 | 6/2 | 30/3 | 0/0 | 37/2 |

## PostgreSQL minus SQLite

Median over cells of (PostgreSQL arm − SQLite) per machine, milliseconds, using only cells where both rows passed. Close is Sandbox close; Store release is `store disconnect` (PostgreSQL) versus `store remove` (SQLite), which the product does not unify.

| Machine | Arm | Cells | Create | Mount | Exec | Commit | Unmount | Close | Store release | End-to-end |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 4 | +31.2 | +27.4 | -11.4 | +22.1 | +0.2 | -16.2 | -8.8 | +9.5 |
| docker | pg-colocated | 4 | +39.7 | +26.8 | -7.5 | +10.7 | +0.9 | +1.7 | -8.6 | +58.9 |
| native | postgresql | 4 | +3.4 | +11.8 | +5.2 | +14.9 | -3.5 | -7.5 | -2.3 | +24.4 |
| lima | postgresql | 4 | +27.8 | +27.1 | -15.7 | +21.6 | -0.3 | -3.5 | -9.0 | +52.1 |
| apple-container | postgresql | 4 | +65.5 | +19.3 | -5.4 | +53.5 | -0.9 | +0.7 | -6.7 | +125.9 |

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `04a4c1202d0fab8ce2be764122a2637824e6a59d1030f05f9704eaecbc2f88ee` |
| Native daemon | `0472e2a60075008f79f34304d2c7669d7f47846c5fda36847d0ef34711c7ceef` |
| Linux bundle seal | `4c7499ceac02b7e471cb014c2f12404837421ed61c89b1c6e3a6e5c33dabc45f` |
| Docker tool image | `sha256:88f1d8720fec4f50f876bc9266ce8b76bbbcdab8aa857722c769f29d87d9d14c` |
| Namespace archive config | `sha256:504b072822cb4dad540ccb93f3e0e3d02d9225944b6857478d4d306e7e8a1861` |

## P01

tests/open/04.t: 4 planned TAP assertions; selected scripts run unprivileged. fixed-posix-tap-unprivileged-subset-v2.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 5.44 | 285.53 | 22.48 | 126.58 | 39.71 | 17.16 | 234.42 | 19.10 | 744.99 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.44 | 307.01 | 42.22 | 86.42 | 33.98 | 12.49 | 218.30 | 7.65 | 708.07 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.81 | 320.02 | 51.79 | 95.27 | 24.66 | 15.87 | 206.29 | 9.89 | 723.81 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 5.65 | 43.16 | 36.54 | 230.21 | 57.09 | 30.24 | 67.29 | 11.36 | 475.89 | 1.82 | 1.44 | 0.64 |
| native | postgresql | PASS | COMPLETE | 5.44 | 42.61 | 44.07 | 132.61 | 68.05 | 26.54 | 59.74 | 8.14 | 381.75 | 1.53 | 2.00 | 0.54 |
| lima | sqlite | PASS | COMPLETE | 5.81 | 744.92 | 21.40 | 87.63 | 13.40 | 13.75 | 120.20 | 19.45 | 1020.75 | 0.69 | 0.34 | 1.37 |
| lima | postgresql | PASS | COMPLETE | 5.81 | 766.08 | 46.34 | 61.85 | 40.79 | 13.09 | 112.12 | 7.46 | 1047.73 | 0.72 | 1.20 | 1.48 |
| apple-container | sqlite | PASS | COMPLETE | 5.74 | 66.94 | 15.16 | 86.96 | 12.28 | 12.85 | 36.08 | 13.49 | 243.76 | 0.69 | 0.31 | 0.33 |
| apple-container | postgresql | PASS | COMPLETE | 5.74 | 128.31 | 68.07 | 96.14 | 67.91 | 12.02 | 37.07 | 6.85 | 416.38 | 1.11 | 2.00 | 0.59 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 73 | 7 | 2.0 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 73 | 7 | 2.1 |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 67 | 6 | 0.7 |
| lima | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 73 | 7 | 2.3 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 66 | 5 | 0.8 |

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
| docker | sqlite | PASS | COMPLETE | 5.30 | 279.30 | 18.62 | 92.70 | 14.46 | 13.05 | 225.49 | 14.05 | 657.67 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.30 | 328.73 | 46.77 | 101.28 | 37.16 | 12.70 | 236.60 | 7.88 | 771.13 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.76 | 324.25 | 44.25 | 139.11 | 24.88 | 14.63 | 239.77 | 10.63 | 797.51 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 5.76 | 40.62 | 33.09 | 150.66 | 57.00 | 28.62 | 63.72 | 9.20 | 382.90 | 1.63 | 3.94 | 0.58 |
| native | postgresql | PASS | COMPLETE | 5.74 | 44.18 | 48.69 | 169.05 | 87.97 | 25.26 | 56.28 | 7.89 | 439.31 | 1.67 | 2.37 | 0.57 |
| lima | sqlite | PASS | COMPLETE | 5.20 | 739.53 | 21.26 | 66.10 | 12.63 | 13.62 | 116.65 | 21.70 | 991.48 | 0.71 | 0.87 | 1.51 |
| lima | postgresql | PASS | COMPLETE | 5.30 | 785.86 | 47.47 | 65.74 | 29.31 | 14.25 | 111.57 | 11.06 | 1065.26 | 0.65 | 0.79 | 1.38 |
| apple-container | sqlite | PASS | COMPLETE | 4.94 | 66.66 | 21.44 | 89.88 | 13.86 | 14.02 | 37.01 | 14.23 | 257.10 | 0.97 | 0.96 | 0.39 |
| apple-container | postgresql | PASS | COMPLETE | 5.20 | 138.03 | 40.03 | 86.79 | 37.71 | 13.04 | 37.37 | 7.43 | 360.40 | 0.86 | 1.01 | 0.47 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 73 | 7 | 2.4 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 73 | 7 | 2.1 |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 67 | 6 | 0.9 |
| lima | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 73 | 7 | 2.4 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 66 | 5 | 1.0 |

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
| docker | sqlite | PASS | COMPLETE | 6.87 | 310.71 | 19.01 | 114.82 | 12.05 | 11.82 | 237.57 | 18.21 | 724.18 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 7.28 | 299.52 | 45.60 | 109.36 | 33.48 | 13.72 | 221.19 | 9.77 | 732.63 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 7.28 | 327.48 | 45.83 | 111.47 | 23.59 | 13.43 | 252.52 | 8.39 | 782.71 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 6.87 | 38.80 | 35.28 | 219.58 | 63.51 | 20.74 | 61.70 | 10.54 | 450.14 | 1.91 | 5.27 | 0.62 |
| native | postgresql | PASS | COMPLETE | 6.87 | 42.61 | 46.61 | 211.52 | 59.78 | 24.74 | 50.48 | 6.85 | 442.58 | 1.93 | 1.79 | 0.60 |
| lima | sqlite | PASS | COMPLETE | 7.17 | 738.72 | 18.89 | 101.99 | 12.75 | 12.19 | 111.59 | 14.15 | 1010.28 | 0.89 | 1.06 | 1.40 |
| lima | postgresql | PASS | COMPLETE | 7.17 | 755.99 | 50.79 | 77.60 | 32.89 | 12.28 | 110.36 | 7.13 | 1047.06 | 0.71 | 0.98 | 1.43 |
| apple-container | sqlite | PASS | COMPLETE | 6.84 | 68.11 | 16.62 | 110.88 | 11.52 | 11.31 | 36.98 | 11.61 | 267.04 | 0.97 | 0.96 | 0.37 |
| apple-container | postgresql | PASS | COMPLETE | 6.84 | 129.80 | 35.40 | 101.08 | 68.89 | 14.41 | 36.74 | 7.53 | 393.84 | 0.92 | 2.06 | 0.54 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 73 | 7 | 2.2 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 73 | 7 | 2.2 |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 67 | 6 | 0.9 |
| lima | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 73 | 7 | 2.4 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 66 | 5 | 0.8 |

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
| docker | sqlite | PASS | COMPLETE | 6.06 | 272.26 | 17.60 | 1124.51 | 12.76 | 12.66 | 266.16 | 16.87 | 1722.82 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 6.33 | 313.23 | 46.67 | 1107.24 | 36.38 | 13.38 | 208.78 | 7.63 | 1733.32 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 6.33 | 324.34 | 44.39 | 1112.80 | 23.71 | 12.82 | 255.25 | 8.85 | 1782.17 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 6.53 | 40.11 | 33.40 | 1186.51 | 48.60 | 26.60 | 55.77 | 8.33 | 1399.33 | 1.06 | 3.81 | 0.81 |
| native | postgresql | PASS | COMPLETE | 6.84 | 43.42 | 45.58 | 1233.48 | 67.43 | 17.64 | 57.64 | 6.87 | 1472.07 | 1.11 | 1.85 | 0.85 |
| lima | sqlite | PASS | COMPLETE | 5.82 | 737.49 | 18.13 | 1075.38 | 12.08 | 13.29 | 114.49 | 14.16 | 1985.03 | 0.96 | 0.95 | 1.15 |
| lima | postgresql | PASS | COMPLETE | 5.82 | 771.97 | 46.06 | 1068.33 | 35.07 | 11.70 | 112.47 | 6.88 | 2052.48 | 0.96 | 0.96 | 1.18 |
| apple-container | sqlite | PASS | COMPLETE | 5.54 | 73.53 | 16.99 | 1108.05 | 15.68 | 10.44 | 34.52 | 15.05 | 1274.25 | 0.99 | 1.23 | 0.74 |
| apple-container | postgresql | PASS | COMPLETE | 5.67 | 142.77 | 36.79 | 1100.35 | 67.11 | 9.55 | 35.48 | 7.13 | 1399.17 | 0.99 | 1.84 | 0.81 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 73 | 7 | 2.3 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 73 | 7 | 2.2 |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 67 | 6 | 0.7 |
| lima | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 73 | 7 | 2.2 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 0 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 66 | 5 | 0.9 |

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

Attempted row preparation: 6.418 s total; maximum 0.326 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **INCOMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. 

Final disposition recorded by campaign owner.



Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

