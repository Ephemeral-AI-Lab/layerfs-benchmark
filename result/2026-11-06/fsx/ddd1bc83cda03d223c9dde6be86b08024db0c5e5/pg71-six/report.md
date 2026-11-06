# fsx — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: INCOMPLETE.** 9 registered rows; execution {'PASS': 9}. Final infrastructure cleanup: **INCOMPLETE**.

LayerFS `ddd1bc83cda03d223c9dde6be86b08024db0c5e5` (branch `pg-perf` at `ddd1bc83cd` (worktree layerfs-pg-perf, read-only source); 28 commits after the baseline b919f50eaf). Harness: `c731387` (branch `pg-perf-62`, local, unpushed); suite harness unchanged since the published 2026-11-06 run apart from the shared runner arms/observer of #62. Built from `ddd1bc83cd` through the worktree launcher, release profile: macOS CLI and daemon with `layerfs-node/postgresql` (build `build-macos-ecee12a823984af49e8d4d9cfa169268`; CLI sha256 `04a4c120…88ee`, daemon `0472e2a6…c7ceef`) and the Linux aarch64 bundle with PostgreSQL (bundle hash `4c7499ce…dabc45f`, sealed with the baseline Sandbox image `66aeb6bb…` so the guest image matches). Copied into a private cache after SHA-256 checks. Machines: native, docker worker (image = Sandbox image + /opt/fs-six-tools, `pg71-six-tools:20261106` 88f1d872…), fresh Lima `pg71-lima6` and Apple Container `pg71-apple6` created from that image; same PostgreSQL 17.11 server and settings (`pg_settings` dump identical).

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 9}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Close is Sandbox close; Store release is Store remove (SQLite) or disconnect (PostgreSQL). End-to-end is the sum of the measured calls from create through Store release, without harness gaps; it excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: macOS 26.4.1, Apple M3 Max, 14 CPUs, 36 GiB; Docker Desktop 29.5.2 VM 8 CPUs / 7.75 GiB shared with other agents' Rust builds and another benchmark campaign; Lima `pg71-lima6` and Apple Container `pg71-apple6` 2 CPUs / 2 GiB each; PostgreSQL 17.11 container `pgbench-pg` 2 CPUs / 2 GiB. Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

## #71 final verification notes

- All 9 rows PASS with intrinsic checks PASS: 1,000 requested operations, 997 effective, identical operation counts on every route and backend.

Before = the published 2026-11-06 run at b919f50eaf (`result/2026-11-06/fsx/b919f50eaf…/report.md`): different machines (fresh then, reused now), no co-located arm, no PostgreSQL observer, load and first-touch effects differ; one sample per row on both sides. Medians over cells that PASS in both.

| suite | machine | backend | rows PASS before → after | create | Exec | Commit | mount (after) | unmount (after) |
|---|---|---|---|---|---|---|---|---|
| fsx | native | sqlite | 1/1 → 1/1 | 25 → 42 | 1055 → 260 | 74 → 49 | 38 | 29 |
| fsx | native | postgresql | 1/1 → 1/1 | 73 → 41 | 252 → 248 | 125 → 81 | 46 | 26 |
| fsx | docker | sqlite | 1/1 → 1/1 | 303 → 302 | 241 → 194 | 17 → 17 | 21 | 18 |
| fsx | docker | postgresql | 1/1 → 1/1 | 514 → 315 | 197 → 189 | 56 → 53 | 49 | 15 |
| fsx | docker | pg-colocated | 0/0 → 1/1 | — → 325 | — → 190 | — → 35 | 43 | 17 |
| fsx | lima | sqlite | 1/1 → 1/1 | 740 → 743 | 205 → 187 | 14 → 44 | 25 | 17 |
| fsx | lima | postgresql | 1/1 → 1/1 | 895 → 788 | 173 → 210 | 57 → 57 | 63 | 16 |
| fsx | apple-container | sqlite | 1/1 → 1/1 | 61 → 63 | 200 → 208 | 13 → 13 | 17 | 13 |
| fsx | apple-container | postgresql | 1/1 → 1/1 | 287 → 132 | 215 → 199 | 86 → 53 | 36 | 10 |

| suite | machine | PG−SQLite create before → after | Exec | Commit |
|---|---|---|---|---|
| fsx | native | +47 → -1 | -803 → -12 | +51 → +32 |
| fsx | docker | +210 → +13 | -44 → -5 | +40 → +36 |
| fsx | lima | +155 → +45 | -33 → +23 | +43 → +13 |
| fsx | apple-container | +226 → +69 | +15 → -9 | +73 → +41 |

pg_stat_statements per phase, Docker PostgreSQL (statements/connections):

| suite cell | create | mount | Exec | Commit |
|---|---|---|---|---|
| fsx X01 | 6/2 | 30/3 | 0/0 | 67/2 |

## PostgreSQL minus SQLite

Median over cells of (PostgreSQL arm − SQLite) per machine, milliseconds, using only cells where both rows passed. Close is Sandbox close; Store release is `store disconnect` (PostgreSQL) versus `store remove` (SQLite), which the product does not unify.

| Machine | Arm | Cells | Create | Mount | Exec | Commit | Unmount | Close | Store release | End-to-end |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 1 | +12.7 | +28.4 | -4.8 | +36.0 | -2.6 | -4.9 | -36.6 | +28.3 |
| docker | pg-colocated | 1 | +22.4 | +22.5 | -3.4 | +17.4 | -1.2 | -20.4 | -34.8 | +2.5 |
| native | postgresql | 1 | -0.7 | +7.6 | -11.8 | +31.5 | -3.0 | -5.9 | -2.6 | +15.2 |
| lima | postgresql | 1 | +45.5 | +38.0 | +23.2 | +13.1 | -0.4 | +2.0 | -7.3 | +114.0 |
| apple-container | postgresql | 1 | +68.8 | +19.8 | -8.9 | +40.8 | -2.8 | -1.4 | -7.9 | +108.4 |

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `04a4c1202d0fab8ce2be764122a2637824e6a59d1030f05f9704eaecbc2f88ee` |
| Native daemon | `0472e2a60075008f79f34304d2c7669d7f47846c5fda36847d0ef34711c7ceef` |
| Linux bundle seal | `4c7499ceac02b7e471cb014c2f12404837421ed61c89b1c6e3a6e5c33dabc45f` |
| Docker tool image | `sha256:88f1d8720fec4f50f876bc9266ce8b76bbbcdab8aa857722c769f29d87d9d14c` |
| Namespace archive config | `sha256:504b072822cb4dad540ccb93f3e0e3d02d9225944b6857478d4d306e7e8a1861` |

## X01

1,000 operation slots, seed 1, file ≤8 MiB, operation ≤64 KiB; read/write/truncate and upstream consistency checks. Skipped slots remain explicit. fsx-X01-v2-secfs-portable.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 3.21 | 302.36 | 20.74 | 193.68 | 17.20 | 18.05 | 244.95 | 47.21 | 844.19 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 3.21 | 315.11 | 49.17 | 188.88 | 53.23 | 15.47 | 240.09 | 10.59 | 872.54 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 3.51 | 324.80 | 43.20 | 190.26 | 34.58 | 16.81 | 224.59 | 12.44 | 846.68 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 2.88 | 41.53 | 37.94 | 259.64 | 49.05 | 28.86 | 62.99 | 10.77 | 490.77 | 1.34 | 2.85 | 0.58 |
| native | postgresql | PASS | COMPLETE | 3.21 | 40.80 | 45.58 | 247.82 | 80.58 | 25.90 | 57.11 | 8.20 | 506.00 | 1.31 | 1.51 | 0.58 |
| lima | sqlite | PASS | COMPLETE | 3.51 | 742.90 | 24.87 | 186.65 | 43.60 | 16.64 | 113.32 | 14.17 | 1142.15 | 0.96 | 2.53 | 1.35 |
| lima | postgresql | PASS | COMPLETE | 3.79 | 788.35 | 62.86 | 209.84 | 56.69 | 16.27 | 115.27 | 6.84 | 1256.12 | 1.11 | 1.07 | 1.44 |
| apple-container | sqlite | PASS | COMPLETE | 3.79 | 63.45 | 16.62 | 207.71 | 12.70 | 12.52 | 35.23 | 14.62 | 362.85 | 1.07 | 0.74 | 0.43 |
| apple-container | postgresql | PASS | COMPLETE | 3.79 | 132.22 | 36.47 | 198.86 | 53.48 | 9.71 | 33.80 | 6.75 | 471.28 | 1.05 | 1.00 | 0.54 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 67 / 2 | 0 / 0 | 0 / 0 | 103 | 7 | 4.1 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 0 / 0 | 67 / 2 | 0 / 0 | 0 / 0 | 103 | 7 | 3.5 |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 67 / 2 | 0 / 0 | 0 / 0 | 97 | 6 | 3.1 |
| lima | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 67 / 2 | 0 / 0 | 0 / 0 | 103 | 7 | 5.5 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 0 / 0 | 67 / 2 | 0 / 0 | 0 / 0 | 96 | 5 | 3.3 |

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

Attempted row preparation: 1.165 s total; maximum 0.208 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **INCOMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. 

Final disposition recorded by campaign owner.



Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

