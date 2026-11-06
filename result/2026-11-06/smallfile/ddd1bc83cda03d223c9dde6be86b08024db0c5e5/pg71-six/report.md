# smallfile — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: INCOMPLETE.** 45 registered rows; execution {'PASS': 45}. Final infrastructure cleanup: **INCOMPLETE**.

LayerFS `ddd1bc83cda03d223c9dde6be86b08024db0c5e5` (branch `pg-perf` at `ddd1bc83cd` (worktree layerfs-pg-perf, read-only source); 28 commits after the baseline b919f50eaf). Harness: `c731387` (branch `pg-perf-62`, local, unpushed); suite harness unchanged since the published 2026-11-06 run apart from the shared runner arms/observer of #62. Built from `ddd1bc83cd` through the worktree launcher, release profile: macOS CLI and daemon with `layerfs-node/postgresql` (build `build-macos-ecee12a823984af49e8d4d9cfa169268`; CLI sha256 `04a4c120…88ee`, daemon `0472e2a6…c7ceef`) and the Linux aarch64 bundle with PostgreSQL (bundle hash `4c7499ce…dabc45f`, sealed with the baseline Sandbox image `66aeb6bb…` so the guest image matches). Copied into a private cache after SHA-256 checks. Machines: native, docker worker (image = Sandbox image + /opt/fs-six-tools, `pg71-six-tools:20261106` 88f1d872…), fresh Lima `pg71-lima6` and Apple Container `pg71-apple6` created from that image; same PostgreSQL 17.11 server and settings (`pg_settings` dump identical).

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 45}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Close is Sandbox close; Store release is Store remove (SQLite) or disconnect (PostgreSQL). End-to-end is the sum of the measured calls from create through Store release, without harness gaps; it excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: macOS 26.4.1, Apple M3 Max, 14 CPUs, 36 GiB; Docker Desktop 29.5.2 VM 8 CPUs / 7.75 GiB shared with other agents' Rust builds and another benchmark campaign; Lima `pg71-lima6` and Apple Container `pg71-apple6` 2 CPUs / 2 GiB each; PostgreSQL 17.11 container `pgbench-pg` 2 CPUs / 2 GiB. Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

## #71 final verification notes

- All 45 rows PASS. L02–L05 issue 42–54 statements in Exec on PostgreSQL (prepared committed input read); the read/stat/rename/delete Commits are 84–115 statements because smallfile writes its own result files.

Before = the published 2026-11-06 run at b919f50eaf (`result/2026-11-06/smallfile/b919f50eaf…/report.md`): different machines (fresh then, reused now), no co-located arm, no PostgreSQL observer, load and first-touch effects differ; one sample per row on both sides. Medians over cells that PASS in both.

| suite | machine | backend | rows PASS before → after | create | Exec | Commit | mount (after) | unmount (after) |
|---|---|---|---|---|---|---|---|---|
| smallfile | native | sqlite | 5/5 → 5/5 | 38 → 26 | 3720 → 3745 | 97 → 61 | 34 | 28 |
| smallfile | native | postgresql | 5/5 → 5/5 | 89 → 42 | 3780 → 3772 | 174 → 88 | 46 | 26 |
| smallfile | docker | sqlite | 5/5 → 5/5 | 306 → 264 | 3711 → 3676 | 37 → 33 | 19 | 15 |
| smallfile | docker | postgresql | 5/5 → 5/5 | 460 → 305 | 3680 → 3696 | 101 → 81 | 43 | 14 |
| smallfile | docker | pg-colocated | 0/0 → 5/5 | — → 299 | — → 3686 | — → 52 | 42 | 15 |
| smallfile | lima | sqlite | 5/5 → 5/5 | 724 → 738 | 3749 → 3740 | 33 → 30 | 18 | 13 |
| smallfile | lima | postgresql | 5/5 → 5/5 | 876 → 782 | 3763 → 3752 | 108 → 78 | 48 | 13 |
| smallfile | apple-container | sqlite | 5/5 → 5/5 | 55 → 68 | 3782 → 3797 | 32 → 56 | 18 | 13 |
| smallfile | apple-container | postgresql | 5/5 → 5/5 | 255 → 120 | 3855 → 3826 | 176 → 123 | 40 | 12 |

| suite | machine | PG−SQLite create before → after | Exec | Commit |
|---|---|---|---|---|
| smallfile | native | +51 → +14 | +56 → +6 | +73 → +23 |
| smallfile | docker | +142 → +43 | +14 → +17 | +63 → +43 |
| smallfile | lima | +154 → +42 | +4 → +24 | +74 → +46 |
| smallfile | apple-container | +203 → +63 | +60 → +66 | +144 → +67 |

pg_stat_statements per phase, Docker PostgreSQL (statements/connections):

| suite cell | create | mount | Exec | Commit |
|---|---|---|---|---|
| smallfile L01 | 6/2 | 30/3 | 0/0 | 98/2 |
| smallfile L02 | 5/1 | 31/3 | 43/0 | 84/2 |
| smallfile L03 | 5/1 | 31/3 | 42/0 | 84/2 |
| smallfile L04 | 5/1 | 31/3 | 50/0 | 102/2 |
| smallfile L05 | 5/1 | 31/3 | 42/0 | 115/2 |

## PostgreSQL minus SQLite

Median over cells of (PostgreSQL arm − SQLite) per machine, milliseconds, using only cells where both rows passed. Close is Sandbox close; Store release is `store disconnect` (PostgreSQL) versus `store remove` (SQLite), which the product does not unify.

| Machine | Arm | Cells | Create | Mount | Exec | Commit | Unmount | Close | Store release | End-to-end |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 5 | +42.6 | +24.4 | +17.0 | +42.9 | -0.4 | -10.4 | -6.9 | +87.3 |
| docker | pg-colocated | 5 | +32.1 | +23.5 | +9.3 | +18.3 | +1.0 | -25.5 | -7.7 | +49.1 |
| native | postgresql | 5 | +13.5 | +12.6 | +5.6 | +22.7 | -3.5 | -4.4 | -2.6 | +40.8 |
| lima | postgresql | 5 | +41.6 | +31.4 | +23.6 | +45.8 | -0.5 | -1.4 | -5.9 | +136.3 |
| apple-container | postgresql | 5 | +62.8 | +20.1 | +65.5 | +66.9 | -1.3 | -2.0 | -6.6 | +220.9 |

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `04a4c1202d0fab8ce2be764122a2637824e6a59d1030f05f9704eaecbc2f88ee` |
| Native daemon | `0472e2a60075008f79f34304d2c7669d7f47846c5fda36847d0ef34711c7ceef` |
| Linux bundle seal | `4c7499ceac02b7e471cb014c2f12404837421ed61c89b1c6e3a6e5c33dabc45f` |
| Docker tool image | `sha256:88f1d8720fec4f50f876bc9266ce8b76bbbcdab8aa857722c769f29d87d9d14c` |
| Namespace archive config | `sha256:504b072822cb4dad540ccb93f3e0e3d02d9225944b6857478d4d306e7e8a1861` |

## L01

Create 512 files: two workers × 256 files, 4 KiB/file, 64 files/directory. two-worker-256x4k-as-host-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 3.15 | 288.03 | 18.45 | 3705.99 | 60.95 | 14.52 | 240.37 | 13.99 | 4342.30 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 3.53 | 299.80 | 42.84 | 3697.32 | 108.81 | 14.67 | 229.93 | 7.09 | 4400.45 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 3.41 | 317.19 | 42.18 | 3679.20 | 83.10 | 15.48 | 208.24 | 8.72 | 4354.11 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 2.99 | 38.34 | 36.48 | 3885.50 | 96.37 | 34.75 | 57.45 | 9.14 | 4158.03 | 1.05 | 1.58 | 0.96 |
| native | postgresql | PASS | COMPLETE | 3.07 | 42.93 | 45.03 | 3859.34 | 116.49 | 29.06 | 53.03 | 6.96 | 4152.83 | 1.04 | 1.07 | 0.94 |
| lima | sqlite | PASS | COMPLETE | 4.03 | 741.96 | 20.38 | 3807.69 | 59.21 | 13.14 | 115.76 | 16.77 | 4774.90 | 1.03 | 0.97 | 1.10 |
| lima | postgresql | PASS | COMPLETE | 3.95 | 783.57 | 55.28 | 3743.19 | 108.20 | 13.19 | 111.72 | 8.84 | 4823.98 | 1.01 | 0.99 | 1.10 |
| apple-container | sqlite | PASS | COMPLETE | 3.79 | 71.31 | 19.52 | 3801.11 | 63.28 | 10.91 | 36.38 | 14.36 | 4016.87 | 1.03 | 1.04 | 0.93 |
| apple-container | postgresql | PASS | COMPLETE | 3.73 | 119.59 | 38.98 | 3815.64 | 134.57 | 15.44 | 38.10 | 7.81 | 4170.14 | 1.03 | 1.24 | 0.95 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 98 / 2 | 0 / 0 | 0 / 0 | 134 | 7 | 7.6 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 0 / 0 | 98 / 2 | 0 / 0 | 0 / 0 | 134 | 7 | 6.7 |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 98 / 2 | 0 / 0 | 0 / 0 | 128 | 6 | 6.0 |
| lima | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 98 / 2 | 0 / 0 | 0 / 0 | 134 | 7 | 7.8 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 0 / 0 | 98 / 2 | 0 / 0 | 0 / 0 | 127 | 5 | 7.4 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Files | Σ worker files/s | Worker 00 records | Worker 01 records |
| --- | ---: | ---: | ---: | ---: |
| docker / sqlite | 512 | 6238.25 | 256 | 256 |
| docker / postgresql | 512 | 5866.11 | 256 | 256 |
| docker / pg-colocated | 512 | 6698.61 | 256 | 256 |
| native / sqlite | 512 | 2127.46 | 256 | 256 |
| native / postgresql | 512 | 2044.83 | 256 | 256 |
| lima / sqlite | 512 | 6169.43 | 256 | 256 |
| lima / postgresql | 512 | 6890.33 | 256 | 256 |
| apple-container / sqlite | 512 | 6254.51 | 256 | 256 |
| apple-container / postgresql | 512 | 6526.82 | 256 | 256 |

## L02

Read 512 files: two workers × 256 files, 4 KiB/file, 64 files/directory. two-worker-256x4k-as-host-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 3.87 | 262.84 | 19.45 | 3676.11 | 17.10 | 14.67 | 279.36 | 16.02 | 4285.55 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 3.81 | 305.47 | 47.25 | 3696.26 | 52.84 | 14.25 | 231.25 | 9.12 | 4356.43 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 3.86 | 294.98 | 41.32 | 3686.20 | 33.15 | 17.35 | 228.80 | 7.12 | 4308.92 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 3.93 | 26.90 | 34.38 | 3711.25 | 48.63 | 28.12 | 57.52 | 10.00 | 3916.80 | 1.01 | 2.84 | 0.91 |
| native | postgresql | PASS | COMPLETE | 3.64 | 41.73 | 48.00 | 3702.43 | 71.29 | 26.37 | 58.37 | 7.43 | 3955.64 | 1.00 | 1.35 | 0.91 |
| lima | sqlite | PASS | COMPLETE | 3.20 | 750.60 | 19.24 | 3731.26 | 16.68 | 15.46 | 113.77 | 11.21 | 4658.22 | 1.02 | 0.98 | 1.09 |
| lima | postgresql | PASS | COMPLETE | 3.51 | 782.45 | 44.40 | 3752.09 | 58.67 | 13.54 | 110.12 | 6.66 | 4767.92 | 1.02 | 1.11 | 1.09 |
| apple-container | sqlite | PASS | COMPLETE | 3.58 | 71.97 | 19.77 | 3787.86 | 25.29 | 16.38 | 59.12 | 15.58 | 3995.98 | 1.03 | 1.48 | 0.93 |
| apple-container | postgresql | PASS | COMPLETE | 3.24 | 116.75 | 39.86 | 3860.97 | 85.88 | 11.54 | 35.23 | 7.21 | 4157.45 | 1.04 | 1.63 | 0.95 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 5 / 1 | 31 / 3 | 43 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 163 | 6 | 5.8 |
| docker | pg-colocated | 5 / 1 | 31 / 3 | 43 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 163 | 6 | 5.3 |
| native | postgresql | 6 / 2 | 25 / 2 | 46 / 0 | 83 / 2 | 0 / 0 | 0 / 0 | 160 | 6 | 4.6 |
| lima | postgresql | 5 / 1 | 31 / 3 | 45 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 165 | 6 | 6.9 |
| apple-container | postgresql | 5 / 1 | 24 / 1 | 43 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 156 | 4 | 7.0 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Files | Σ worker files/s | Worker 00 records | Worker 01 records |
| --- | ---: | ---: | ---: | ---: |
| docker / pg-colocated | 512 | 8171.12 | 256 | 256 |
| docker / postgresql | 512 | 6703.73 | 256 | 256 |
| docker / sqlite | 512 | 8379.00 | 256 | 256 |
| native / postgresql | 512 | 6139.34 | 256 | 256 |
| native / sqlite | 512 | 6891.21 | 256 | 256 |
| lima / postgresql | 512 | 7627.91 | 256 | 256 |
| lima / sqlite | 512 | 10312.58 | 256 | 256 |
| apple-container / postgresql | 512 | 4154.59 | 256 | 256 |
| apple-container / sqlite | 512 | 7411.78 | 256 | 256 |

## L03

Stat 512 files: two workers × 256 files, 4 KiB/file, 64 files/directory. two-worker-256x4k-as-host-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 3.79 | 260.91 | 20.36 | 3651.61 | 17.85 | 16.90 | 236.91 | 19.06 | 4223.60 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 3.44 | 300.24 | 42.54 | 3668.64 | 53.02 | 13.89 | 223.68 | 8.92 | 4310.93 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 3.61 | 298.64 | 43.91 | 3660.86 | 36.13 | 14.22 | 211.39 | 7.58 | 4272.74 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 3.61 | 25.10 | 33.15 | 3667.47 | 60.31 | 27.96 | 58.48 | 9.48 | 3881.95 | 1.00 | 3.38 | 0.92 |
| native | postgresql | PASS | COMPLETE | 3.65 | 38.62 | 45.78 | 3673.04 | 76.83 | 26.75 | 54.16 | 7.53 | 3922.71 | 1.00 | 1.45 | 0.91 |
| lima | sqlite | PASS | COMPLETE | 3.22 | 737.73 | 16.75 | 3720.27 | 16.60 | 16.07 | 113.47 | 13.21 | 4634.11 | 1.02 | 0.93 | 1.10 |
| lima | postgresql | PASS | COMPLETE | 3.25 | 798.03 | 49.69 | 3751.99 | 53.17 | 13.40 | 141.18 | 7.34 | 4814.79 | 1.02 | 1.00 | 1.12 |
| apple-container | sqlite | PASS | COMPLETE | 3.06 | 45.58 | 16.90 | 3754.96 | 27.01 | 13.60 | 35.75 | 11.42 | 3905.23 | 1.03 | 1.51 | 0.92 |
| apple-container | postgresql | PASS | COMPLETE | 3.14 | 116.30 | 62.81 | 3820.49 | 82.65 | 10.74 | 33.73 | 6.74 | 4133.45 | 1.04 | 1.56 | 0.96 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 5 / 1 | 31 / 3 | 42 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 162 | 6 | 5.4 |
| docker | pg-colocated | 5 / 1 | 31 / 3 | 42 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 162 | 6 | 4.8 |
| native | postgresql | 6 / 2 | 25 / 2 | 45 / 0 | 83 / 2 | 0 / 0 | 0 / 0 | 159 | 6 | 4.2 |
| lima | postgresql | 5 / 1 | 31 / 3 | 42 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 162 | 6 | 6.4 |
| apple-container | postgresql | 5 / 1 | 24 / 1 | 42 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 155 | 4 | 6.5 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Files | Σ worker files/s | Worker 00 records | Worker 01 records |
| --- | ---: | ---: | ---: | ---: |
| docker / sqlite | 512 | 16116.21 | 0 | 0 |
| docker / postgresql | 512 | 10981.17 | 0 | 0 |
| docker / pg-colocated | 512 | 23112.80 | 0 | 0 |
| native / sqlite | 512 | 13596.45 | 0 | 0 |
| native / postgresql | 512 | 9773.99 | 0 | 0 |
| lima / sqlite | 512 | 20419.02 | 0 | 0 |
| lima / postgresql | 512 | 10412.79 | 0 | 0 |
| apple-container / sqlite | 512 | 16349.49 | 0 | 0 |
| apple-container / postgresql | 512 | 6039.21 | 0 | 0 |

## L04

Rename 512 files: two workers × 256 files, 4 KiB/file, 64 files/directory. two-worker-256x4k-as-host-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 4.06 | 266.29 | 16.96 | 3718.28 | 38.06 | 14.32 | 231.96 | 13.30 | 4299.16 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 4.16 | 315.51 | 43.07 | 3716.07 | 80.96 | 13.24 | 243.66 | 7.35 | 4419.86 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.28 | 311.25 | 44.82 | 3702.64 | 51.73 | 14.28 | 226.29 | 6.94 | 4357.96 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 3.97 | 26.48 | 33.77 | 3856.77 | 63.98 | 27.80 | 58.12 | 9.33 | 4076.26 | 1.04 | 1.68 | 0.95 |
| native | postgresql | PASS | COMPLETE | 3.79 | 39.74 | 47.28 | 3897.84 | 87.90 | 24.31 | 52.09 | 6.23 | 4155.40 | 1.05 | 1.09 | 0.94 |
| lima | sqlite | PASS | COMPLETE | 3.53 | 718.79 | 18.31 | 3740.12 | 32.59 | 12.02 | 112.99 | 13.01 | 4647.84 | 1.01 | 0.86 | 1.08 |
| lima | postgresql | PASS | COMPLETE | 3.81 | 765.12 | 42.46 | 3795.24 | 78.38 | 12.84 | 111.63 | 34.51 | 4840.17 | 1.02 | 0.97 | 1.10 |
| apple-container | sqlite | PASS | COMPLETE | 3.72 | 67.92 | 17.60 | 3839.97 | 55.81 | 11.46 | 38.63 | 13.01 | 4044.41 | 1.03 | 1.47 | 0.94 |
| apple-container | postgresql | PASS | COMPLETE | 3.43 | 130.71 | 33.61 | 3920.25 | 122.68 | 16.58 | 35.41 | 6.07 | 4265.30 | 1.05 | 1.52 | 0.97 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 5 / 1 | 31 / 3 | 50 / 0 | 102 / 2 | 0 / 0 | 0 / 0 | 188 | 6 | 6.5 |
| docker | pg-colocated | 5 / 1 | 31 / 3 | 50 / 0 | 100 / 2 | 0 / 0 | 0 / 0 | 186 | 6 | 5.9 |
| native | postgresql | 6 / 2 | 25 / 2 | 54 / 0 | 101 / 2 | 0 / 0 | 0 / 0 | 186 | 6 | 5.5 |
| lima | postgresql | 5 / 1 | 31 / 3 | 50 / 0 | 104 / 2 | 0 / 0 | 0 / 0 | 190 | 6 | 8.4 |
| apple-container | postgresql | 5 / 1 | 24 / 1 | 50 / 0 | 100 / 2 | 0 / 0 | 0 / 0 | 179 | 4 | 9.1 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Files | Σ worker files/s | Worker 00 records | Worker 01 records |
| --- | ---: | ---: | ---: | ---: |
| docker / pg-colocated | 512 | 5030.51 | 0 | 0 |
| docker / postgresql | 512 | 4480.46 | 0 | 0 |
| docker / sqlite | 512 | 4927.91 | 0 | 0 |
| native / postgresql | 512 | 1814.71 | 0 | 0 |
| native / sqlite | 512 | 2118.63 | 0 | 0 |
| lima / postgresql | 512 | 3561.47 | 0 | 0 |
| lima / sqlite | 512 | 7368.95 | 0 | 0 |
| apple-container / postgresql | 512 | 2838.54 | 0 | 0 |
| apple-container / sqlite | 512 | 5121.29 | 0 | 0 |

## L05

Delete 512 files: two workers × 256 files, 4 KiB/file, 64 files/directory. two-worker-256x4k-as-host-v1.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 4.67 | 263.86 | 21.43 | 3676.15 | 33.16 | 13.63 | 228.63 | 14.61 | 4251.47 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 4.18 | 310.62 | 42.63 | 3695.86 | 86.65 | 13.50 | 234.33 | 32.09 | 4415.69 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.17 | 294.31 | 41.39 | 3696.13 | 63.50 | 22.56 | 225.10 | 6.91 | 4349.89 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 3.54 | 26.04 | 33.46 | 3744.72 | 61.20 | 28.83 | 56.65 | 9.36 | 3960.27 | 1.02 | 1.85 | 0.93 |
| native | postgresql | PASS | COMPLETE | 4.12 | 41.70 | 45.73 | 3772.49 | 88.61 | 24.28 | 51.34 | 6.21 | 4030.36 | 1.02 | 1.02 | 0.91 |
| lima | sqlite | PASS | COMPLETE | 3.84 | 720.17 | 16.44 | 3764.89 | 30.25 | 12.79 | 113.53 | 39.06 | 4697.13 | 1.02 | 0.91 | 1.10 |
| lima | postgresql | PASS | COMPLETE | 3.67 | 749.37 | 47.82 | 3788.52 | 86.66 | 12.32 | 115.98 | 32.76 | 4833.42 | 1.03 | 1.00 | 1.09 |
| apple-container | sqlite | PASS | COMPLETE | 3.42 | 45.01 | 17.25 | 3797.34 | 58.14 | 13.43 | 35.50 | 12.99 | 3979.66 | 1.03 | 1.75 | 0.94 |
| apple-container | postgresql | PASS | COMPLETE | 2.97 | 124.44 | 63.99 | 3825.51 | 173.92 | 12.12 | 33.73 | 6.63 | 4240.33 | 1.04 | 2.01 | 0.96 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 5 / 1 | 31 / 3 | 42 / 0 | 115 / 2 | 0 / 0 | 0 / 0 | 193 | 6 | 6.0 |
| docker | pg-colocated | 5 / 1 | 31 / 3 | 42 / 0 | 115 / 2 | 0 / 0 | 0 / 0 | 193 | 6 | 5.3 |
| native | postgresql | 6 / 2 | 52 / 2 | 20 / 0 | 114 / 2 | 0 / 0 | 0 / 0 | 192 | 6 | 4.9 |
| lima | postgresql | 5 / 1 | 31 / 3 | 42 / 0 | 115 / 2 | 0 / 0 | 0 / 0 | 193 | 6 | 7.8 |
| apple-container | postgresql | 5 / 1 | 24 / 1 | 42 / 0 | 115 / 2 | 0 / 0 | 0 / 0 | 186 | 4 | 7.8 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Files | Σ worker files/s | Worker 00 records | Worker 01 records |
| --- | ---: | ---: | ---: | ---: |
| docker / sqlite | 512 | 8732.18 | 0 | 0 |
| docker / postgresql | 512 | 6892.46 | 0 | 0 |
| docker / pg-colocated | 512 | 9952.42 | 0 | 0 |
| native / sqlite | 512 | 4078.49 | 0 | 0 |
| native / postgresql | 512 | 3171.41 | 0 | 0 |
| lima / sqlite | 512 | 9251.95 | 0 | 0 |
| lima / postgresql | 512 | 5730.75 | 0 | 0 |
| apple-container / sqlite | 512 | 7219.60 | 0 | 0 |
| apple-container / postgresql | 512 | 5774.18 | 0 | 0 |

## Preparation, limits and cleanup

Attempted row preparation: 174.511 s total; maximum 5.589 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **INCOMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. 

Final disposition recorded by campaign owner.



Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

Smallfile upstream rate = 256/T00 + 256/T01 files/s. Each worker timer starts after directory, seed/buffer preparation and gate waiting; it uses upstream time.time(). It excludes launcher/startup work, so it is not 512 divided by CLI Exec time. Its control-file fsyncs are intrinsic upstream behavior; payload fsync is disabled. The declared 4KiB payload pattern is nonzero and compressible.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

