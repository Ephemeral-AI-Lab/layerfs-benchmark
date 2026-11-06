# fs-bench-quick — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: INCOMPLETE.** 162 registered rows; execution {'PASS': 162}. Final infrastructure cleanup: **INCOMPLETE**.

LayerFS `ddd1bc83cda03d223c9dde6be86b08024db0c5e5` (branch `pg-perf` at `ddd1bc83cd` (worktree layerfs-pg-perf, read-only source); 28 commits after the baseline b919f50eaf). Harness: rows and calibration ran at `c731387` (branch `pg-perf-62`, local, unpushed); runner and cases identical to the baseline `3fdb4ef`, report options from `023698a`. Built from `ddd1bc83cd` through the worktree launcher, release profile: macOS CLI and daemon with `layerfs-node/postgresql` (build `build-macos-ecee12a823984af49e8d4d9cfa169268`; CLI sha256 `04a4c120…88ee`, daemon `0472e2a6…c7ceef`) and the Linux aarch64 bundle with PostgreSQL (bundle hash `4c7499ce…dabc45f`, sealed with the baseline Sandbox image `66aeb6bb…` so the guest image matches). Copied into a private cache after SHA-256 checks. Same machines as the baseline (native, docker worker, pg62-lima, pg62-apple), updated to the new daemon/bundle; same PostgreSQL 17.11 server and settings (`pg_settings` dump identical).

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 162}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Close is Sandbox close; Store release is Store remove (SQLite) or disconnect (PostgreSQL). End-to-end is the sum of the measured calls from create through Store release, without harness gaps; it excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: macOS 26.4.1, Apple M3 Max, 14 CPUs, 36 GiB; Docker Desktop 29.5.2 VM 8 CPUs / 7.75 GiB shared with other agents' Rust builds and another benchmark campaign; Lima `pg62-lima` and Apple Container `pg62-apple` 2 CPUs / 2 GiB each; PostgreSQL 17.11 container `pgbench-pg` with 2 CPUs / 2 GiB; 1-minute load during rows 3.5–6.0, median 4.5 (baseline 4.6–11.2, median 7.2). Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

## Main observations (#71 final verification)

- **All 162 rows PASS** (baseline 160 PASS, C04/apple-container FAIL/NOT_RUN from an Apple Container service outage). Every cleanup COMPLETE. pgbench-pg and the Docker worker had been stopped by another session ~02:09 UTC; both restarted with no configuration change before row 1 (ledger `infra/infrastructure.jsonl`). The co-located server address moved from 172.17.0.9 to 172.17.0.10 with that restart.
- **Fixed PostgreSQL cost fell sharply.** Sandbox create 54 statements / 5 connections → 6 / 2 (committed base 32/3 → 5/1); mount 60/3 → 30/3 (Apple 38/1 → 23/1, native 24/2); native Exec/unmount/close 22/2 → 0/0. PG−SQLite median create gap on Docker +228 → +53 ms, mount +90 → +29 ms; Apple +203 → +65 and +113 → +17 ms.
- **Commit statements fell 1.5–6×; connections rose 1 → 2.** C01 346 → 91, C04 541 → 89, C12 381 → 97, C15 136 → 81, C16 ~2,745 → ~690, C13 118+113 → 79+71, UpToDate (C09/C14/C17/C18) 6–7 → 1. Every non-UpToDate Commit now opens 2 connections (was 1). Median PG−SQLite Commit gap: Docker +59 → +48 ms, Lima +96 → +48, Apple +95 → +47, native +78 → +36; co-located +19 → +21 ms (unchanged: on the near route the remaining gap is not round trips).
- **Non-repeating committed read (C17) round trips almost halved:** 1,573 → 847 statements. Exec SQLite / PG / co-located: Docker 362/1,305/591 → 369/917/576; Lima 349/2,072 → 353/1,108; Apple 309/1,444 → 342/976; native 277/935 → 301/673 ms. C18 stat over 1,000 committed files unchanged at 39 statements.
- **Regression to check (both backends): write-heavy Exec and 64 MiB Commit got slower at ddd1bc83cd.** Median after/before over write cells (C01, C04–C08, C16; all machines): SQLite Exec ×1.33, PostgreSQL ×1.18, co-located ×1.27; 64 MiB Commit (C06–C08) SQLite ×1.35, PostgreSQL ×1.24 — e.g. C06 Docker SQLite Commit 245 → 332 ms, C01 Docker SQLite Exec 276 → 377 ms — while host load was lower than in the baseline. Read and small Exec cells are unchanged (SQLite ×1.02). One sample per row; not rerun. The likely candidate is `7a625d855d` (digest window and overlay page widened to 1,024, #69); not isolated here.
- **Storage:** the harness records only the Commit result. `new_stored`/`new_metadata` are equal within 0.5% before and after on both backends (C04 +0.4%, C16 PostgreSQL +52 bytes). No database file sizes are recorded.
- **Route calibration** (`SELECT 1` median, ms) after: host published 0.21, host bridge tunnel 0.36, native 0.24, Docker via host.docker.internal 0.35, co-located 0.08, Lima 0.34, Apple 0.29 (baseline 0.18 / – / 0.20 / 0.36 / 0.07 / 0.44 / 0.26).

## Before → after (baseline pg62-base-1106 at b919f50eaf)

### Per machine × backend medians, before (b919f50eaf) → after (ddd1bc83cd), ms

Median over the cells that PASS in both campaigns for that machine/arm (count `n`). One sample per row.

| machine | backend | n | create | mount | Exec | Commit | unmount |
|---|---|---:|---|---|---|---|---|
| native | sqlite | 18 | 41 → 42 | 37 → 38 | 279 → 354 | 144 → 139 | 32 → 32 |
| native | postgresql | 18 | 103 → 44 | 89 → 54 | 440 → 444 | 261 → 175 | 60 → 29 |
| docker | sqlite | 18 | 362 → 334 | 24 → 23 | 260 → 259 | 71 → 85 | 18 → 18 |
| docker | postgresql | 18 | 566 → 386 | 116 → 53 | 225 → 305 | 178 → 145 | 18 → 17 |
| docker | pg-colocated | 18 | 528 → 377 | 112 → 49 | 235 → 262 | 111 → 110 | 18 → 18 |
| lima | sqlite | 18 | 739 → 737 | 20 → 21 | 166 → 219 | 68 → 84 | 17 → 17 |
| lima | postgresql | 18 | 950 → 795 | 125 → 54 | 222 → 228 | 243 → 140 | 19 → 17 |
| apple-container | sqlite | 17 | 60 → 58 | 17 → 18 | 178 → 193 | 77 → 88 | 14 → 14 |
| apple-container | postgresql | 17 | 273 → 123 | 130 → 34 | 215 → 206 | 222 → 135 | 54 → 14 |

### PostgreSQL − SQLite median gap per machine, before → after, ms

Median over cells of (PostgreSQL row − SQLite row) for cells where both arms PASS in both campaigns. `coloc` is the Docker co-located arm minus Docker SQLite.

| machine | arm | n | create | mount | Exec | Commit | unmount |
|---|---|---:|---|---|---|---|---|
| native | pg | 18 | +60 → +3 | +50 → +15 | +30 → -1 | +78 → +36 | +24 → -4 |
| docker | pg | 18 | +228 → +53 | +90 → +29 | -0 → +6 | +59 → +48 | +1 → -0 |
| docker | coloc | 18 | +161 → +43 | +89 → +27 | -22 → -2 | +19 → +21 | +1 → +0 |
| lima | pg | 18 | +214 → +58 | +100 → +33 | +25 → -1 | +96 → +48 | +1 → -0 |
| apple-container | pg | 17 | +203 → +65 | +113 → +17 | +37 → +4 | +95 → +47 | +28 → +0 |

### pg_stat_statements per phase, Docker PostgreSQL (published port), statements/connections before → after

| cell | create | mount | Exec | Commit | unmount | follow-up |
|---|---|---|---|---|---|---|
| C01 | 54/5 → 6/2 | 60/3 → 30/3 | 8/0 → 8/0 | 346/1 → 91/2 | 0/0 → 0/0 |  |
| C03 | 54/5 → 6/2 | 60/3 → 30/3 | 8/0 → 8/0 | 53/1 → 37/2 | 0/0 → 0/0 |  |
| C04 | 54/5 → 6/2 | 60/3 → 30/3 | 8/0 → 8/0 | 541/1 → 89/2 | 0/0 → 0/0 |  |
| C09 | 32/3 → 5/1 | 61/3 → 30/3 | 6/0 → 6/0 | 7/0 → 1/0 | 0/0 → 0/0 |  |
| C12 | 54/5 → 6/2 | 60/3 → 30/3 | 0/0 → 0/0 | 381/1 → 97/2 | 0/0 → 0/0 |  |
| C13 | 54/5 → 6/2 | 60/3 → 30/3 | 0/0 → 0/0 | 118/1 → 79/2 | 0/0 → 0/0 | followup_exec 0/0 → 0/0 |
| C14 | 54/5 → 6/2 | 60/3 → 30/3 | 0/0 → 0/0 | 6/0 → 1/0 | 0/0 → 0/0 |  |
| C15 | 54/5 → 6/2 | 60/3 → 30/3 | 0/0 → 0/0 | 136/1 → 81/2 | 0/0 → 0/0 |  |
| C16 | 54/5 → 6/2 | 60/3 → 30/3 | 80/0 → 80/0 | 2745/1 → 696/2 | 0/0 → 0/0 |  |
| C17 | 32/3 → 5/1 | 61/3 → 30/3 | 1573/0 → 847/0 | 7/0 → 1/0 | 0/0 → 0/0 |  |
| C18 | 32/3 → 5/1 | 63/3 → 32/3 | 39/0 → 39/0 | 7/0 → 1/0 | 0/0 → 0/0 |  |

Other machines (after): same Commit/Exec counts within ±3 statements on every route; mount differs by route (see below).

| machine | C01 create | C01 mount | C01 Exec | C01 unmount | C01 sandbox close |
|---|---|---|---|---|---|
| native (before) | 54/5 | 60/3 | 30/2 | 22/2 | 22/2 |
| native (after) | 6/2 | 24/2 | 8/0 | 0/0 | 0/0 |
| docker (before) | 54/5 | 60/3 | 8/0 | 0/0 | 0/0 |
| docker (after) | 6/2 | 30/3 | 8/0 | 0/0 | 0/0 |
| lima (before) | 54/5 | 60/3 | 8/0 | 0/0 | 0/0 |
| lima (after) | 6/2 | 30/3 | 8/0 | 0/0 | 0/0 |
| apple-container (before) | 54/5 | 38/1 | 8/0 | 0/0 | 0/0 |
| apple-container (after) | 6/2 | 23/1 | 8/0 | 0/0 | 0/0 |

Commit statements/connections after, all PostgreSQL rows:

| cell | native | docker | lima | apple | docker coloc |
|---|---|---|---|---|---|
| C01 | 91/2 | 91/2 | 91/2 | 91/2 | 91/2 |
| C03 | 37/2 | 37/2 | 37/2 | 37/2 | 37/2 |
| C04 | 89/2 | 89/2 | 89/2 | 89/2 | 89/2 |
| C09 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| C12 | 97/2 | 97/2 | 97/2 | 97/2 | 97/2 |
| C13 | 79/2 | 79/2 | 79/2 | 79/2 | 79/2 |
| C14 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| C15 | 81/2 | 81/2 | 81/2 | 81/2 | 81/2 |
| C16 | 686/2 | 696/2 | 685/2 | 690/2 | 699/2 |
| C17 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |
| C18 | 1/0 | 1/0 | 1/0 | 1/0 | 1/0 |

### Storage recorded by Commit (bytes), Docker rows, before → after

`new_stored` / `new_canonical` / `new_metadata` from the Commit result. The harness records no database file size.

| cell | SQLite new_stored | PostgreSQL new_stored | SQLite new_metadata | PostgreSQL new_metadata |
|---|---|---|---|---|
| C01 | 18516 → 18516 | 18516 → 18512 | 9591 → 9591 | 9591 → 9587 |
| C02 | 18516 → 18516 | 18516 → 18516 | 9591 → 9591 | 9591 → 9591 |
| C03 | — | — | — | — |
| C04 | 7995 → 8028 | 8005 → 8032 | 7995 → 8028 | 8005 → 8032 |
| C05 | 8007 → 8036 | 8009 → 8040 | 8007 → 8036 | 8009 → 8040 |
| C06 | 748 → 748 | 748 → 748 | 672 → 672 | 672 → 672 |
| C07 | 832 → 832 | 832 → 832 | 756 → 756 | 756 → 756 |
| C08 | 748 → 748 | 748 → 748 | 672 → 672 | 672 → 672 |
| C09 | — | — | — | — |
| C10 | 300 → 300 | 295 → 294 | 300 → 300 | 295 → 294 |
| C11 | — | — | — | — |
| C12 | 26949 → 26943 | 26949 → 26938 | 6545 → 6546 | 6552 → 6542 |
| C13 | 319 → 319 | 319 → 319 | 280 → 280 | 280 → 280 |
| C14 | — | — | — | — |
| C15 | 1979 → 1980 | 1980 → 1980 | 1155 → 1156 | 1156 → 1156 |
| C16 | 186859 → 186858 | 186867 → 186919 | 87837 → 87836 | 87845 → 87897 |
| C17 | — | — | — | — |
| C18 | — | — | — | — |

### Row outcomes

- before: {'PASS': 160, 'FAIL': 1, 'NOT_RUN': 1} of 162
  - C04/apple-container/postgresql: FAIL — sandbox_create: CLI/process exit 125
  - C04/apple-container/sqlite: NOT_RUN — store_push: CLI/process exit 125
- after: {'PASS': 162} of 162

## Resources kept and release

- PostgreSQL server: `docker rm -f pgbench-pg`; `docker volume rm pgbench-pg-data` (all row databases q_*, f_*, s_*).
- Machines (CLI `~/.cache/pg-perf-62/pg71-final/artifacts/layerfs`, `LAYERFS_HOME=~/.cache/pg-perf-62/pg62-base/home`, `XDG_CACHE_HOME=~/.cache/pg-perf-62/pg71-final/xdg`): `layerfs machine remove pg62-lima`, `pg62-apple`, `pg71-lima6`, `pg71-apple6`; `layerfs machine stop docker` (worker lfs-c0bfb23a-docker, volume lfs-c0bfb23a-docker-data).
- Guest tool image: `docker image rm pg71-six-tools:20261106`; private caches `rm -rf ~/.cache/pg-perf-62` after the machines are removed.

## PostgreSQL minus SQLite

Median over cells of (PostgreSQL arm − SQLite) per machine, milliseconds, using only cells where both rows passed. Close is Sandbox close; Store release is `store disconnect` (PostgreSQL) versus `store remove` (SQLite), which the product does not unify.

| Machine | Arm | Cells | Create | Mount | Exec | Commit | Unmount | Close | Store release | End-to-end |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 18 | +52.8 | +29.0 | +6.0 | +48.0 | -0.1 | -2.4 | -8.1 | +138.6 |
| docker | pg-colocated | 18 | +43.1 | +26.6 | -1.9 | +21.0 | +0.1 | +0.5 | -8.1 | +92.6 |
| native | postgresql | 18 | +3.0 | +15.4 | -1.5 | +35.7 | -3.6 | -3.1 | -3.2 | +44.7 |
| lima | postgresql | 18 | +58.0 | +32.6 | -0.7 | +47.8 | -0.4 | +1.4 | -6.7 | +127.3 |
| apple-container | postgresql | 18 | +65.6 | +16.7 | +2.5 | +46.9 | -0.0 | -0.7 | -7.3 | +125.0 |

## Round-trip calibration

`pgrtt.py` from each client location: address resolution, then 20 fresh connections (TCP connect; one SSLRequest probe, which a plaintext server answers `N` and which an unset `sslmode` (`prefer`) adds to every connection; as the first server reply it also includes the server starting a backend; startup to ReadyForQuery), then 200 simple-protocol `SELECT 1` on one connection. Milliseconds, medians unless marked p90. Resolve is one `getaddrinfo` call and includes the client's first-call library loading. Guests and the trust rows use a trust-authenticated calibration role; the SCRAM rows add the Store user's SCRAM-SHA-256 exchange.

| Client | Route | Target | Peer | Auth | Resolve | TCP connect | SSL probe | Startup | SELECT 1 | SELECT 1 p90 |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| apple-container | postgresql | 192.168.64.1:55432 | 192.168.64.1 | trust | 5.782 | 0.353 | 1.090 | 1.135 | 0.293 | 0.341 |
| docker | pg-colocated | 172.17.0.10:5432 | 172.17.0.10 | trust | 0.743 | 0.057 | 0.436 | 0.853 | 0.081 | 0.101 |
| docker | postgresql | host.docker.internal:55432 | 192.168.65.254 | trust | 2.023 | 0.872 | 0.868 | 1.251 | 0.354 | 0.413 |
| lima | postgresql | 192.168.5.2:55432 | 192.168.5.2 | trust | 6.284 | 0.361 | 0.926 | 1.187 | 0.342 | 0.395 |
| native | postgresql | 127.0.0.1:55432 | 127.0.0.1 | trust | 2.164 | 0.184 | 1.015 | 1.168 | 0.240 | 0.275 |
| host (host/bridge-tunnel) | host/bridge-tunnel | 172.17.0.10:5432 | 172.17.0.10 | scram | 3.078 | 0.743 | 0.871 | 3.057 | 0.353 | 0.418 |
| host (host/bridge-tunnel) | host/bridge-tunnel | 172.17.0.10:5432 | 172.17.0.10 | trust | 4.330 | 0.640 | 0.876 | 1.227 | 0.357 | 0.408 |
| host (host/published) | host/published | 127.0.0.1:55432 | 127.0.0.1 | scram | 2.016 | 0.174 | 0.965 | 2.430 | 0.230 | 0.280 |
| host (host/published) | host/published | 127.0.0.1:55432 | 127.0.0.1 | trust | 23.223 | 0.160 | 0.902 | 1.086 | 0.211 | 0.265 |

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `04a4c1202d0fab8ce2be764122a2637824e6a59d1030f05f9704eaecbc2f88ee` |
| Native daemon | `0472e2a60075008f79f34304d2c7669d7f47846c5fda36847d0ef34711c7ceef` |
| Linux bundle seal | `4c7499ceac02b7e471cb014c2f12404837421ed61c89b1c6e3a6e5c33dabc45f` |
| Docker tool image | `sha256:d58396888e87e971b74b84f099e7b0db493c9041e3aafe2111e30984a0ad3cec` |
| Namespace archive config | `UNAVAILABLE` |

## C01

Create 1,000 numbered files (also the sweep's 1,000-file point). Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 4.57 | 334.70 | 24.20 | 377.01 | 107.97 | 19.01 | 231.14 | 16.97 | 1110.99 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 4.57 | 446.00 | 64.93 | 322.04 | 174.41 | 17.33 | 232.29 | 8.86 | 1265.85 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.69 | 389.40 | 55.32 | 370.66 | 139.04 | 17.68 | 269.11 | 9.60 | 1250.80 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 4.19 | 43.70 | 41.33 | 861.45 | 140.92 | 43.05 | 72.54 | 12.77 | 1215.76 | 2.28 | 1.31 | 1.09 |
| native | postgresql | PASS | COMPLETE | 4.19 | 41.65 | 59.27 | 876.45 | 189.30 | 44.52 | 62.71 | 8.88 | 1282.79 | 2.72 | 1.09 | 1.01 |
| lima | sqlite | PASS | COMPLETE | 4.28 | 737.49 | 22.47 | 245.07 | 103.68 | 16.71 | 114.58 | 18.82 | 1258.81 | 0.65 | 0.96 | 1.13 |
| lima | postgresql | PASS | COMPLETE | 4.28 | 823.84 | 53.69 | 329.66 | 167.24 | 17.42 | 118.46 | 13.70 | 1523.99 | 1.02 | 0.96 | 1.20 |
| apple-container | sqlite | PASS | COMPLETE | 4.26 | 67.65 | 17.95 | 323.96 | 100.28 | 11.99 | 37.00 | 16.84 | 575.67 | 0.86 | 0.93 | 0.52 |
| apple-container | postgresql | PASS | COMPLETE | 4.26 | 126.66 | 36.30 | 301.88 | 159.56 | 13.11 | 38.32 | 8.86 | 684.68 | 0.94 | 0.91 | 0.54 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 8 / 0 | 91 / 2 | 0 / 0 | 0 / 0 | 135 | 7 | 20.4 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 8 / 0 | 91 / 2 | 0 / 0 | 0 / 0 | 135 | 7 | 19.1 |
| native | postgresql | 6 / 2 | 24 / 2 | 8 / 0 | 91 / 2 | 0 / 0 | 0 / 0 | 129 | 6 | 18.7 |
| lima | postgresql | 6 / 2 | 30 / 3 | 8 / 0 | 91 / 2 | 0 / 0 | 0 / 0 | 135 | 7 | 20.2 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 8 / 0 | 91 / 2 | 0 / 0 | 0 / 0 | 128 | 5 | 17.3 |

## C02

Create 1,000 files, then `stat` each (one process per file). Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 4.62 | 329.07 | 20.57 | 990.81 | 107.68 | 16.28 | 252.62 | 16.69 | 1733.72 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 4.62 | 372.36 | 49.65 | 976.34 | 172.80 | 17.39 | 245.31 | 8.76 | 1842.62 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.50 | 375.70 | 48.62 | 986.15 | 137.11 | 16.94 | 245.82 | 8.47 | 1818.82 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 4.74 | 43.43 | 38.24 | 8094.57 | 154.57 | 51.22 | 76.55 | 12.03 | 8470.60 | 8.17 | 1.44 | 4.89 |
| native | postgresql | PASS | COMPLETE | 4.80 | 47.35 | 52.62 | 8255.08 | 214.03 | 41.48 | 61.73 | 9.18 | 8681.47 | 8.46 | 1.24 | 4.71 |
| lima | sqlite | PASS | COMPLETE | 4.68 | 738.23 | 21.85 | 932.30 | 103.55 | 16.37 | 110.82 | 17.47 | 1940.59 | 0.94 | 0.96 | 1.12 |
| lima | postgresql | PASS | COMPLETE | 4.65 | 796.70 | 53.96 | 915.17 | 167.91 | 16.46 | 113.83 | 8.60 | 2072.63 | 0.94 | 0.97 | 1.12 |
| apple-container | sqlite | PASS | COMPLETE | 4.87 | 64.83 | 42.98 | 743.61 | 99.51 | 10.89 | 37.07 | 14.62 | 1013.52 | 0.75 | 0.92 | 0.58 |
| apple-container | postgresql | PASS | COMPLETE | 4.68 | 132.07 | 36.07 | 800.04 | 153.06 | 13.39 | 36.28 | 8.54 | 1179.44 | 0.82 | 0.89 | 0.64 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 8 / 0 | 91 / 2 | 0 / 0 | 0 / 0 | 135 | 7 | 19.4 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 8 / 0 | 91 / 2 | 0 / 0 | 0 / 0 | 135 | 7 | 18.2 |
| native | postgresql | 6 / 2 | 24 / 2 | 8 / 0 | 91 / 2 | 0 / 0 | 0 / 0 | 129 | 6 | 17.8 |
| lima | postgresql | 6 / 2 | 30 / 3 | 8 / 0 | 91 / 2 | 0 / 0 | 0 / 0 | 135 | 7 | 19.2 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 8 / 0 | 91 / 2 | 0 / 0 | 0 / 0 | 128 | 5 | 16.0 |

## C03

Create 1,000 files, then remove them. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 4.67 | 333.74 | 22.79 | 591.79 | 18.00 | 15.06 | 296.33 | 16.70 | 1294.41 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 4.53 | 387.98 | 49.71 | 397.65 | 42.97 | 15.01 | 240.65 | 8.37 | 1142.33 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.53 | 391.24 | 46.33 | 592.56 | 27.78 | 14.97 | 247.88 | 8.31 | 1329.06 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 4.73 | 56.61 | 49.62 | 1487.71 | 86.34 | 32.39 | 61.93 | 11.88 | 1786.48 | 2.51 | 4.80 | 1.38 |
| native | postgresql | PASS | COMPLETE | 4.67 | 43.21 | 50.57 | 1245.24 | 75.71 | 27.51 | 62.72 | 9.56 | 1514.51 | 3.13 | 1.76 | 1.33 |
| lima | sqlite | PASS | COMPLETE | 4.57 | 777.60 | 19.06 | 519.84 | 17.87 | 15.71 | 111.84 | 14.22 | 1476.13 | 0.88 | 0.99 | 1.14 |
| lima | postgresql | PASS | COMPLETE | 4.44 | 793.48 | 51.06 | 505.68 | 42.68 | 15.51 | 110.45 | 8.55 | 1527.41 | 1.27 | 0.99 | 1.34 |
| apple-container | sqlite | PASS | COMPLETE | 4.60 | 57.09 | 18.74 | 513.38 | 41.19 | 13.87 | 37.84 | 14.56 | 696.68 | 0.87 | 2.29 | 0.54 |
| apple-container | postgresql | PASS | COMPLETE | 4.60 | 120.72 | 35.92 | 510.54 | 44.97 | 13.18 | 38.08 | 8.67 | 772.07 | 1.28 | 1.05 | 0.68 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 8 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 81 | 7 | 2.5 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 8 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 81 | 7 | 2.5 |
| native | postgresql | 6 / 2 | 24 / 2 | 8 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 75 | 6 | 1.0 |
| lima | postgresql | 6 / 2 | 30 / 3 | 8 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 81 | 7 | 2.5 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 8 / 0 | 37 / 2 | 0 / 0 | 0 / 0 | 74 | 5 | 1.0 |

## C04

Create 110 directories and 1,000 empty files. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 4.55 | 330.70 | 22.43 | 835.63 | 115.77 | 16.13 | 263.82 | 15.77 | 1600.26 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 4.51 | 368.05 | 49.19 | 870.29 | 182.47 | 16.68 | 264.15 | 8.07 | 1758.89 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.56 | 368.28 | 48.38 | 826.36 | 141.03 | 16.88 | 260.79 | 8.70 | 1670.42 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 4.52 | 42.18 | 36.52 | 4526.26 | 163.14 | 43.14 | 62.04 | 11.87 | 4885.14 | 5.42 | 1.41 | 3.05 |
| native | postgresql | PASS | COMPLETE | 4.48 | 41.52 | 49.17 | 4617.15 | 204.80 | 38.15 | 59.13 | 8.24 | 5018.17 | 5.31 | 1.12 | 2.85 |
| lima | sqlite | PASS | COMPLETE | 4.37 | 740.32 | 18.58 | 778.96 | 113.44 | 15.94 | 116.58 | 15.04 | 1798.86 | 0.93 | 0.98 | 1.12 |
| lima | postgresql | PASS | COMPLETE | 4.32 | 791.89 | 51.29 | 808.72 | 174.83 | 15.60 | 115.81 | 8.79 | 1966.93 | 0.93 | 0.96 | 1.12 |
| apple-container | sqlite | PASS | COMPLETE | 4.34 | 52.45 | 15.68 | 685.46 | 120.82 | 13.06 | 37.57 | 14.61 | 939.66 | 0.82 | 1.04 | 0.59 |
| apple-container | postgresql | PASS | COMPLETE | 4.37 | 135.81 | 33.92 | 681.11 | 185.06 | 12.89 | 37.07 | 8.48 | 1094.34 | 0.78 | 1.01 | 0.62 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 8 / 0 | 89 / 2 | 0 / 0 | 0 / 0 | 133 | 7 | 10.8 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 8 / 0 | 89 / 2 | 0 / 0 | 0 / 0 | 133 | 7 | 9.6 |
| native | postgresql | 6 / 2 | 24 / 2 | 8 / 0 | 89 / 2 | 0 / 0 | 0 / 0 | 127 | 6 | 8.7 |
| lima | postgresql | 6 / 2 | 30 / 3 | 8 / 0 | 89 / 2 | 0 / 0 | 0 / 0 | 133 | 7 | 10.8 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 8 / 0 | 89 / 2 | 0 / 0 | 0 / 0 | 126 | 5 | 8.8 |

## C05

C04, then `find . -type f \| wc -l`. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 5.57 | 339.01 | 21.76 | 878.29 | 117.10 | 16.31 | 233.65 | 16.78 | 1622.91 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.68 | 379.97 | 51.23 | 885.33 | 181.11 | 16.31 | 227.30 | 8.40 | 1749.65 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.39 | 382.38 | 46.90 | 854.79 | 144.67 | 17.31 | 234.84 | 8.60 | 1689.48 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 4.23 | 42.21 | 38.50 | 4670.45 | 155.56 | 43.14 | 64.83 | 11.63 | 5026.33 | 5.32 | 1.33 | 3.10 |
| native | postgresql | PASS | COMPLETE | 4.13 | 45.54 | 49.23 | 4959.89 | 218.32 | 32.78 | 63.57 | 8.97 | 5378.30 | 5.60 | 1.21 | 3.07 |
| lima | sqlite | PASS | COMPLETE | 5.39 | 733.43 | 19.49 | 815.31 | 112.19 | 16.77 | 111.44 | 14.34 | 1822.97 | 0.93 | 0.96 | 1.12 |
| lima | postgresql | PASS | COMPLETE | 5.04 | 788.55 | 51.97 | 799.49 | 170.01 | 15.02 | 114.84 | 8.81 | 1948.69 | 0.90 | 0.94 | 1.11 |
| apple-container | sqlite | PASS | COMPLETE | 5.19 | 50.52 | 16.18 | 716.15 | 123.66 | 13.03 | 37.55 | 14.65 | 971.74 | 0.82 | 1.06 | 0.60 |
| apple-container | postgresql | PASS | COMPLETE | 5.18 | 129.62 | 32.39 | 694.82 | 187.96 | 13.98 | 36.05 | 9.63 | 1104.43 | 0.78 | 1.04 | 0.63 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 8 / 0 | 89 / 2 | 0 / 0 | 0 / 0 | 133 | 7 | 10.7 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 8 / 0 | 89 / 2 | 0 / 0 | 0 / 0 | 133 | 7 | 10.1 |
| native | postgresql | 6 / 2 | 24 / 2 | 8 / 0 | 89 / 2 | 0 / 0 | 0 / 0 | 127 | 6 | 8.9 |
| lima | postgresql | 6 / 2 | 30 / 3 | 8 / 0 | 89 / 2 | 0 / 0 | 0 / 0 | 133 | 7 | 10.3 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 8 / 0 | 89 / 2 | 0 / 0 | 0 / 0 | 126 | 5 | 9.0 |

## C06

Write 64 MiB of zeros. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 4.56 | 335.42 | 21.25 | 190.44 | 332.07 | 21.23 | 264.91 | 16.29 | 1181.61 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 4.70 | 420.32 | 52.75 | 203.40 | 387.55 | 19.50 | 262.87 | 8.73 | 1355.11 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.76 | 385.33 | 48.11 | 214.08 | 352.63 | 22.82 | 256.28 | 8.36 | 1287.61 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 4.91 | 40.01 | 36.45 | 208.56 | 396.18 | 29.60 | 61.41 | 11.00 | 783.20 | 1.10 | 1.19 | 0.66 |
| native | postgresql | PASS | COMPLETE | 4.91 | 45.29 | 49.84 | 207.67 | 441.52 | 26.47 | 59.21 | 8.65 | 838.65 | 1.02 | 1.14 | 0.62 |
| lima | sqlite | PASS | COMPLETE | 4.43 | 742.33 | 21.95 | 211.14 | 327.04 | 23.34 | 112.35 | 14.62 | 1452.77 | 1.11 | 0.98 | 1.23 |
| lima | postgresql | PASS | COMPLETE | 4.56 | 794.51 | 54.76 | 230.45 | 391.58 | 23.92 | 113.92 | 9.16 | 1618.31 | 1.13 | 1.01 | 1.19 |
| apple-container | sqlite | PASS | COMPLETE | 4.77 | 75.83 | 16.76 | 183.08 | 324.64 | 27.48 | 37.13 | 16.61 | 681.53 | 0.96 | 0.98 | 0.58 |
| apple-container | postgresql | PASS | COMPLETE | 4.58 | 132.84 | 32.12 | 191.30 | 365.01 | 23.89 | 36.94 | 8.73 | 790.84 | 0.94 | 0.94 | 0.58 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 120 | 7 | 5.0 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 0 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 120 | 7 | 5.0 |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 114 | 6 | 3.3 |
| lima | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 120 | 7 | 6.0 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 0 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 113 | 5 | 3.2 |

## C07

Write 64 MiB of zeros, then copy it. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 5.20 | 330.27 | 24.33 | 407.54 | 632.04 | 27.78 | 264.77 | 45.28 | 1732.02 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.03 | 390.57 | 50.37 | 387.81 | 690.18 | 28.40 | 260.57 | 9.23 | 1817.14 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.78 | 372.33 | 51.84 | 391.31 | 660.19 | 25.73 | 264.64 | 8.74 | 1774.80 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 4.79 | 40.91 | 36.73 | 407.82 | 736.91 | 35.12 | 63.64 | 12.55 | 1333.67 | 1.00 | 1.17 | 0.77 |
| native | postgresql | PASS | COMPLETE | 4.79 | 44.71 | 53.67 | 395.21 | 782.64 | 30.34 | 59.58 | 9.37 | 1375.52 | 1.02 | 1.13 | 0.76 |
| lima | sqlite | PASS | COMPLETE | 4.75 | 719.99 | 20.50 | 405.85 | 630.69 | 30.96 | 116.74 | 15.72 | 1940.45 | 1.00 | 1.00 | 1.12 |
| lima | postgresql | PASS | COMPLETE | 4.53 | 791.01 | 49.74 | 368.85 | 686.52 | 30.17 | 116.21 | 8.95 | 2051.45 | 0.95 | 0.99 | 1.13 |
| apple-container | sqlite | PASS | COMPLETE | 4.57 | 63.33 | 18.63 | 365.83 | 627.44 | 40.71 | 38.52 | 16.42 | 1170.88 | 0.90 | 0.99 | 0.68 |
| apple-container | postgresql | PASS | COMPLETE | 4.44 | 123.45 | 34.74 | 328.88 | 663.22 | 39.12 | 37.26 | 9.04 | 1235.71 | 0.85 | 0.96 | 0.68 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 85 / 2 | 0 / 0 | 0 / 0 | 121 | 7 | 5.6 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 0 / 0 | 85 / 2 | 0 / 0 | 0 / 0 | 121 | 7 | 5.2 |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 85 / 2 | 0 / 0 | 0 / 0 | 115 | 6 | 3.8 |
| lima | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 85 / 2 | 0 / 0 | 0 / 0 | 121 | 7 | 5.3 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 0 / 0 | 85 / 2 | 0 / 0 | 0 / 0 | 114 | 5 | 3.7 |

## C08

Write 64 MiB of zeros, then read it. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 4.24 | 337.51 | 22.83 | 210.31 | 327.25 | 21.66 | 219.94 | 16.57 | 1156.06 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 4.09 | 379.42 | 50.21 | 185.56 | 376.22 | 21.51 | 242.30 | 8.51 | 1263.74 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.18 | 383.62 | 48.51 | 213.04 | 346.47 | 21.94 | 263.67 | 10.24 | 1287.49 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 4.41 | 40.52 | 36.90 | 222.35 | 393.11 | 32.26 | 69.16 | 12.00 | 806.31 | 1.06 | 1.20 | 0.70 |
| native | postgresql | PASS | COMPLETE | 4.41 | 43.49 | 53.87 | 213.73 | 440.39 | 29.21 | 59.97 | 9.00 | 849.66 | 1.15 | 1.17 | 0.67 |
| lima | sqlite | PASS | COMPLETE | 4.66 | 740.86 | 21.78 | 177.75 | 323.79 | 24.58 | 116.38 | 15.30 | 1420.44 | 0.85 | 0.99 | 1.23 |
| lima | postgresql | PASS | COMPLETE | 4.54 | 805.55 | 58.30 | 166.54 | 371.64 | 22.90 | 115.01 | 8.45 | 1548.40 | 0.90 | 0.99 | 1.23 |
| apple-container | sqlite | PASS | COMPLETE | 4.77 | 47.57 | 14.92 | 180.54 | 323.56 | 26.29 | 37.02 | 14.22 | 644.13 | 0.86 | 0.99 | 0.56 |
| apple-container | postgresql | PASS | COMPLETE | 4.77 | 126.48 | 57.98 | 205.53 | 371.85 | 28.18 | 37.86 | 8.98 | 836.87 | 1.11 | 0.99 | 0.66 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 120 | 7 | 5.0 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 0 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 120 | 7 | 4.4 |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 114 | 6 | 3.7 |
| lima | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 120 | 7 | 5.6 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 0 / 0 | 84 / 2 | 0 / 0 | 0 / 0 | 113 | 5 | 3.4 |

## C09

Read the committed 64 MiB zero file (dedups to about one chunk). Committed base.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 5.02 | 305.39 | 23.48 | 104.73 | 15.29 | 17.73 | 258.38 | 17.32 | 742.31 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.10 | 379.14 | 52.36 | 107.44 | 16.48 | 17.73 | 241.93 | 9.22 | 824.30 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.09 | 372.18 | 50.22 | 97.56 | 42.23 | 18.68 | 293.39 | 9.10 | 883.35 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 5.13 | 43.87 | 38.84 | 62.44 | 55.03 | 30.20 | 62.54 | 12.61 | 305.52 | 0.60 | 3.60 | 0.41 |
| native | postgresql | PASS | COMPLETE | 5.20 | 43.68 | 56.32 | 62.14 | 49.40 | 26.68 | 60.44 | 8.67 | 307.33 | 0.58 | 3.00 | 0.37 |
| lima | sqlite | PASS | COMPLETE | 5.00 | 734.07 | 20.54 | 81.73 | 14.67 | 18.32 | 112.69 | 41.62 | 1023.64 | 0.78 | 0.96 | 1.38 |
| lima | postgresql | PASS | COMPLETE | 4.93 | 790.32 | 53.88 | 84.19 | 16.41 | 18.01 | 112.21 | 8.56 | 1083.57 | 0.78 | 1.00 | 1.31 |
| apple-container | sqlite | PASS | COMPLETE | 4.56 | 58.07 | 18.01 | 70.94 | 11.77 | 15.38 | 38.13 | 15.89 | 228.20 | 0.68 | 0.77 | 0.31 |
| apple-container | postgresql | PASS | COMPLETE | 4.52 | 112.26 | 34.44 | 74.78 | 13.78 | 15.54 | 37.47 | 8.73 | 297.00 | 0.70 | 0.84 | 0.36 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 5 / 1 | 30 / 3 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 42 | 4 | 2.1 |
| docker | pg-colocated | 5 / 1 | 30 / 3 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 42 | 4 | 2.1 |
| native | postgresql | 6 / 2 | 24 / 2 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 37 | 4 | 0.6 |
| lima | postgresql | 5 / 1 | 30 / 3 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 42 | 4 | 2.2 |
| apple-container | postgresql | 5 / 1 | 23 / 1 | 6 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 35 | 2 | 0.5 |

## C10

Copy the committed 64 MiB zero file. Committed base.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 4.32 | 314.73 | 21.40 | 258.97 | 62.75 | 24.36 | 238.62 | 17.78 | 938.61 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 4.35 | 367.81 | 50.08 | 338.94 | 109.57 | 22.78 | 224.87 | 8.53 | 1122.58 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.31 | 357.47 | 49.22 | 251.59 | 83.67 | 24.72 | 262.53 | 9.42 | 1038.62 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 4.51 | 39.30 | 42.39 | 254.30 | 137.12 | 31.30 | 64.05 | 12.59 | 581.05 | 0.98 | 2.19 | 0.62 |
| native | postgresql | PASS | COMPLETE | 4.56 | 42.35 | 54.39 | 249.10 | 157.93 | 27.72 | 60.82 | 8.75 | 601.05 | 0.73 | 1.44 | 0.54 |
| lima | sqlite | PASS | COMPLETE | 3.72 | 737.76 | 20.03 | 225.87 | 64.73 | 26.40 | 115.75 | 15.78 | 1206.32 | 0.87 | 1.03 | 1.29 |
| lima | postgresql | PASS | COMPLETE | 3.96 | 795.33 | 53.85 | 226.00 | 106.83 | 25.61 | 116.40 | 9.05 | 1333.06 | 0.67 | 0.98 | 1.19 |
| apple-container | sqlite | PASS | COMPLETE | 3.60 | 45.03 | 15.65 | 213.30 | 72.84 | 121.86 | 37.89 | 15.73 | 522.30 | 0.82 | 1.16 | 0.56 |
| apple-container | postgresql | PASS | COMPLETE | 3.82 | 128.82 | 33.27 | 221.08 | 120.54 | 29.20 | 37.01 | 8.21 | 578.13 | 0.65 | 1.10 | 0.51 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 5 / 1 | 30 / 3 | 6 / 0 | 70 / 2 | 0 / 0 | 0 / 0 | 111 | 6 | 4.5 |
| docker | pg-colocated | 5 / 1 | 30 / 3 | 6 / 0 | 70 / 2 | 0 / 0 | 0 / 0 | 111 | 6 | 4.1 |
| native | postgresql | 6 / 2 | 24 / 2 | 6 / 0 | 70 / 2 | 0 / 0 | 0 / 0 | 106 | 6 | 2.7 |
| lima | postgresql | 5 / 1 | 30 / 3 | 6 / 0 | 70 / 2 | 0 / 0 | 0 / 0 | 111 | 6 | 4.8 |
| apple-container | postgresql | 5 / 1 | 23 / 1 | 6 / 0 | 70 / 2 | 0 / 0 | 0 / 0 | 104 | 4 | 2.7 |

## C11

Overwrite the committed zero file with zeros (`conv=notrunc`). Committed base.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 3.56 | 322.30 | 25.31 | 159.34 | 160.04 | 21.31 | 253.76 | 16.49 | 958.53 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 3.51 | 365.61 | 54.15 | 148.86 | 185.88 | 20.39 | 251.01 | 12.46 | 1038.36 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 3.58 | 382.41 | 48.65 | 140.24 | 169.61 | 20.54 | 262.28 | 9.30 | 1033.01 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 3.71 | 41.60 | 37.18 | 162.78 | 226.29 | 32.26 | 62.32 | 12.20 | 574.62 | 1.02 | 1.41 | 0.60 |
| native | postgresql | PASS | COMPLETE | 3.65 | 44.66 | 51.37 | 160.70 | 244.58 | 28.24 | 64.30 | 8.95 | 602.80 | 1.08 | 1.32 | 0.58 |
| lima | sqlite | PASS | COMPLETE | 3.69 | 733.10 | 18.74 | 137.01 | 151.99 | 23.03 | 112.20 | 14.56 | 1190.64 | 0.86 | 0.95 | 1.24 |
| lima | postgresql | PASS | COMPLETE | 3.66 | 785.41 | 55.39 | 120.71 | 181.79 | 22.49 | 114.07 | 8.76 | 1288.62 | 0.81 | 0.98 | 1.24 |
| apple-container | sqlite | PASS | COMPLETE | 3.77 | 66.51 | 41.92 | 121.94 | 156.15 | 26.11 | 37.48 | 16.60 | 466.72 | 0.77 | 0.98 | 0.49 |
| apple-container | postgresql | PASS | COMPLETE | 3.95 | 120.82 | 32.87 | 118.05 | 180.64 | 24.13 | 37.61 | 8.42 | 522.54 | 0.79 | 0.97 | 0.50 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 5 / 1 | 30 / 3 | 4 / 0 | 38 / 2 | 0 / 0 | 0 / 0 | 77 | 6 | 2.7 |
| docker | pg-colocated | 5 / 1 | 30 / 3 | 4 / 0 | 38 / 2 | 0 / 0 | 0 / 0 | 77 | 6 | 2.6 |
| native | postgresql | 6 / 2 | 24 / 2 | 4 / 0 | 38 / 2 | 0 / 0 | 0 / 0 | 72 | 6 | 1.1 |
| lima | postgresql | 5 / 1 | 30 / 3 | 4 / 0 | 38 / 2 | 0 / 0 | 0 / 0 | 77 | 6 | 2.6 |
| apple-container | postgresql | 5 / 1 | 23 / 1 | 4 / 0 | 38 / 2 | 0 / 0 | 0 / 0 | 70 | 4 | 1.0 |

## C12

Git init, 100 files, add and Git commit. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 4.57 | 343.42 | 22.70 | 259.55 | 54.37 | 15.72 | 242.33 | 16.47 | 954.56 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 4.27 | 399.06 | 51.58 | 287.46 | 117.12 | 15.03 | 262.96 | 9.17 | 1142.36 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.12 | 377.83 | 50.25 | 271.53 | 78.39 | 17.80 | 285.82 | 9.10 | 1090.72 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 4.13 | 41.34 | 38.34 | 506.56 | 90.70 | 30.75 | 67.52 | 13.48 | 788.69 | 1.95 | 1.67 | 0.83 |
| native | postgresql | PASS | COMPLETE | 3.97 | 42.87 | 57.68 | 492.14 | 160.37 | 27.19 | 63.83 | 9.06 | 853.14 | 1.71 | 1.37 | 0.75 |
| lima | sqlite | PASS | COMPLETE | 4.25 | 736.99 | 19.63 | 205.74 | 53.41 | 15.74 | 115.35 | 14.53 | 1161.38 | 0.79 | 0.98 | 1.22 |
| lima | postgresql | PASS | COMPLETE | 4.44 | 788.34 | 50.38 | 211.30 | 113.44 | 16.33 | 116.48 | 9.16 | 1305.42 | 0.74 | 0.97 | 1.14 |
| apple-container | sqlite | PASS | COMPLETE | 3.97 | 52.15 | 16.89 | 192.80 | 88.28 | 12.79 | 38.20 | 15.83 | 416.94 | 0.74 | 1.62 | 0.44 |
| apple-container | postgresql | PASS | COMPLETE | 3.97 | 120.75 | 33.60 | 200.46 | 134.99 | 13.24 | 36.41 | 8.55 | 547.99 | 0.70 | 1.15 | 0.48 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 97 / 2 | 0 / 0 | 0 / 0 | 133 | 7 | 10.2 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 0 / 0 | 97 / 2 | 0 / 0 | 0 / 0 | 133 | 7 | 9.2 |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 97 / 2 | 0 / 0 | 0 / 0 | 127 | 6 | 8.5 |
| lima | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 97 / 2 | 0 / 0 | 0 / 0 | 133 | 7 | 10.4 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 0 / 0 | 97 / 2 | 0 / 0 | 0 / 0 | 126 | 5 | 8.8 |

## C13

New in pg62-v1: `echo 1 > a` and Commit, then `echo 2 > b` and a second Commit on the same Workspace (Commit 2). Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Commit 2 ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 3.75 | 355.74 | 23.18 | 55.01 | 16.48 | 15.55 | 16.06 | 271.19 | 16.45 | 813.84 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 4.01 | 408.27 | 53.55 | 66.70 | 59.95 | 38.39 | 17.71 | 262.53 | 9.13 | 964.26 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.01 | 356.76 | 48.26 | 83.66 | 37.10 | 22.78 | 15.17 | 262.38 | 9.26 | 888.10 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 3.89 | 40.69 | 37.60 | 28.55 | 57.55 | 51.10 | 30.11 | 64.46 | 11.86 | 351.37 | 0.52 | 3.49 | 0.43 |
| native | postgresql | PASS | COMPLETE | 3.82 | 43.57 | 55.97 | 24.73 | 86.40 | 59.16 | 26.07 | 59.54 | 9.00 | 387.72 | 0.37 | 1.44 | 0.40 |
| lima | sqlite | PASS | COMPLETE | 4.15 | 737.37 | 19.76 | 22.59 | 15.84 | 16.59 | 15.29 | 111.28 | 13.46 | 974.70 | 0.41 | 0.96 | 1.20 |
| lima | postgresql | PASS | COMPLETE | 4.22 | 791.23 | 53.54 | 21.01 | 63.59 | 34.77 | 15.39 | 119.45 | 9.01 | 1133.59 | 0.32 | 1.06 | 1.18 |
| apple-container | sqlite | PASS | COMPLETE | 4.19 | 63.94 | 15.86 | 22.55 | 14.29 | 13.43 | 11.40 | 37.03 | 16.00 | 219.15 | 0.41 | 0.87 | 0.27 |
| apple-container | postgresql | PASS | COMPLETE | 4.34 | 131.96 | 33.09 | 23.71 | 61.68 | 37.92 | 12.67 | 37.19 | 8.45 | 368.14 | 0.36 | 1.03 | 0.38 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Exec 2 | Commit 2 | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 79 / 2 | 0 / 0 | 71 / 0 | 0 / 0 | 0 / 0 | 186 | 7 | 6.0 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 0 / 0 | 79 / 2 | 0 / 0 | 71 / 0 | 0 / 0 | 0 / 0 | 186 | 7 | 5.5 |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 79 / 2 | 0 / 0 | 71 / 0 | 0 / 0 | 0 / 0 | 180 | 6 | 4.1 |
| lima | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 79 / 2 | 0 / 0 | 71 / 0 | 0 / 0 | 0 / 0 | 186 | 7 | 5.9 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 0 / 0 | 79 / 2 | 0 / 0 | 71 / 0 | 0 / 0 | 0 / 0 | 179 | 5 | 4.3 |

## C14

New in pg62-v1: file sweep, 0 files (`true`); the Commit is UpToDate. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 5.75 | 340.84 | 25.12 | 44.74 | 14.07 | 14.45 | 270.36 | 16.09 | 725.68 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.11 | 389.63 | 55.97 | 49.65 | 16.99 | 16.48 | 283.53 | 9.23 | 821.48 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.43 | 374.75 | 51.62 | 55.05 | 15.53 | 16.68 | 246.72 | 9.42 | 769.77 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 4.47 | 43.71 | 36.51 | 27.80 | 56.46 | 29.20 | 64.11 | 12.00 | 269.78 | 0.62 | 4.01 | 0.37 |
| native | postgresql | PASS | COMPLETE | 4.47 | 46.74 | 53.02 | 21.71 | 47.91 | 26.82 | 61.38 | 8.44 | 266.01 | 0.44 | 2.82 | 0.32 |
| lima | sqlite | PASS | COMPLETE | 5.96 | 739.82 | 19.59 | 18.46 | 13.60 | 16.04 | 111.95 | 15.50 | 934.97 | 0.41 | 0.97 | 1.29 |
| lima | postgresql | PASS | COMPLETE | 5.61 | 811.34 | 53.35 | 20.41 | 16.32 | 15.83 | 114.71 | 8.59 | 1040.54 | 0.41 | 0.96 | 1.27 |
| apple-container | sqlite | PASS | COMPLETE | 5.65 | 54.14 | 19.59 | 22.44 | 10.20 | 12.55 | 38.66 | 14.20 | 171.79 | 0.50 | 0.72 | 0.24 |
| apple-container | postgresql | PASS | COMPLETE | 5.88 | 120.04 | 33.11 | 21.45 | 14.64 | 12.71 | 36.61 | 8.71 | 247.27 | 0.43 | 0.86 | 0.30 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 37 | 5 | 2.2 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 0 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 37 | 5 | 2.1 |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 31 | 4 | 0.4 |
| lima | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 37 | 5 | 2.1 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 0 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 30 | 3 | 0.4 |

## C15

New in pg62-v1: file sweep, 100 numbered files. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 5.25 | 337.51 | 22.89 | 93.18 | 25.62 | 18.30 | 214.67 | 16.21 | 728.38 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.31 | 394.26 | 56.02 | 83.22 | 72.59 | 16.42 | 264.51 | 8.80 | 895.81 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.44 | 380.04 | 52.25 | 82.55 | 46.77 | 16.58 | 243.76 | 8.29 | 830.25 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 5.48 | 39.27 | 40.97 | 109.73 | 67.02 | 30.14 | 70.58 | 12.05 | 369.77 | 1.18 | 2.62 | 0.51 |
| native | postgresql | PASS | COMPLETE | 5.36 | 55.72 | 51.66 | 114.04 | 96.77 | 28.54 | 58.83 | 9.44 | 415.00 | 1.37 | 1.33 | 0.46 |
| lima | sqlite | PASS | COMPLETE | 5.33 | 734.01 | 21.86 | 52.70 | 24.97 | 15.95 | 110.79 | 15.19 | 975.48 | 0.57 | 0.97 | 1.34 |
| lima | postgresql | PASS | COMPLETE | 5.22 | 794.53 | 52.14 | 59.79 | 72.48 | 15.39 | 113.47 | 8.55 | 1116.36 | 0.72 | 1.00 | 1.25 |
| apple-container | sqlite | PASS | COMPLETE | 5.08 | 53.91 | 17.54 | 55.16 | 32.65 | 13.82 | 39.85 | 15.43 | 228.38 | 0.59 | 1.27 | 0.31 |
| apple-container | postgresql | PASS | COMPLETE | 5.16 | 118.36 | 37.97 | 60.19 | 79.76 | 13.26 | 37.28 | 9.11 | 355.93 | 0.72 | 1.10 | 0.40 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 81 / 2 | 0 / 0 | 0 / 0 | 117 | 7 | 5.9 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 0 / 0 | 81 / 2 | 0 / 0 | 0 / 0 | 117 | 7 | 6.0 |
| native | postgresql | 6 / 2 | 24 / 2 | 0 / 0 | 81 / 2 | 0 / 0 | 0 / 0 | 111 | 6 | 4.6 |
| lima | postgresql | 6 / 2 | 30 / 3 | 0 / 0 | 81 / 2 | 0 / 0 | 0 / 0 | 117 | 7 | 6.6 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 0 / 0 | 81 / 2 | 0 / 0 | 0 / 0 | 110 | 5 | 4.6 |

## C16

New in pg62-v1: file sweep, 10,000 numbered files; prospectively declared 25 s budget. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 5.27 | 366.73 | 24.04 | 3135.39 | 1079.74 | 25.96 | 255.56 | 18.36 | 4905.78 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.41 | 383.88 | 52.85 | 3180.27 | 1394.95 | 26.12 | 263.52 | 8.75 | 5310.33 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.40 | 406.00 | 48.78 | 3179.79 | 1213.02 | 25.22 | 247.13 | 9.54 | 5129.49 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 4.76 | 41.93 | 40.58 | 6030.34 | 1066.41 | 151.33 | 68.83 | 13.15 | 7412.57 | 1.92 | 0.99 | 1.51 |
| native | postgresql | PASS | COMPLETE | 4.99 | 45.70 | 57.23 | 5947.78 | 1353.91 | 140.36 | 57.49 | 8.84 | 7611.32 | 1.87 | 0.97 | 1.43 |
| lima | sqlite | PASS | COMPLETE | 4.68 | 735.32 | 20.57 | 2924.05 | 1013.48 | 28.11 | 118.09 | 16.09 | 4855.71 | 0.93 | 0.94 | 0.99 |
| lima | postgresql | PASS | COMPLETE | 4.89 | 823.74 | 60.01 | 2462.25 | 1410.18 | 26.76 | 112.70 | 9.33 | 4904.97 | 0.77 | 1.01 | 0.92 |
| apple-container | sqlite | PASS | COMPLETE | 4.61 | 73.11 | 15.37 | 2702.54 | 1036.01 | 52.31 | 59.62 | 18.58 | 3957.55 | 0.86 | 0.96 | 0.81 |
| apple-container | postgresql | PASS | COMPLETE | 4.72 | 138.50 | 32.40 | 2640.00 | 1330.98 | 25.72 | 35.58 | 8.59 | 4211.77 | 0.83 | 0.95 | 0.79 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 6 / 2 | 30 / 3 | 80 / 0 | 696 / 2 | 0 / 0 | 0 / 0 | 812 | 7 | 161.0 |
| docker | pg-colocated | 6 / 2 | 30 / 3 | 80 / 0 | 699 / 2 | 0 / 0 | 0 / 0 | 815 | 7 | 158.6 |
| native | postgresql | 6 / 2 | 24 / 2 | 80 / 0 | 686 / 2 | 0 / 0 | 0 / 0 | 796 | 6 | 159.8 |
| lima | postgresql | 6 / 2 | 30 / 3 | 80 / 0 | 685 / 2 | 0 / 0 | 0 / 0 | 801 | 7 | 167.9 |
| apple-container | postgresql | 6 / 2 | 23 / 1 | 80 / 0 | 690 / 2 | 0 / 0 | 0 / 0 | 799 | 5 | 162.6 |

## C17

New in pg62-v1: `cat` a committed 64 MiB non-repeating file (AES-128-CTR keystream, pinned SHA-256). Committed base.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 4.17 | 327.77 | 22.00 | 368.72 | 13.83 | 18.17 | 242.38 | 19.97 | 1012.85 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 4.08 | 390.15 | 58.14 | 916.54 | 14.80 | 17.49 | 260.88 | 8.99 | 1666.99 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.21 | 352.07 | 52.00 | 576.35 | 14.01 | 17.33 | 265.40 | 8.93 | 1286.09 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 4.44 | 40.68 | 43.02 | 300.99 | 58.52 | 29.03 | 63.16 | 11.64 | 547.03 | 0.82 | 4.23 | 0.54 |
| native | postgresql | PASS | COMPLETE | 4.38 | 42.81 | 55.68 | 672.91 | 72.20 | 32.05 | 65.04 | 9.04 | 949.74 | 0.73 | 4.88 | 0.57 |
| lima | sqlite | PASS | COMPLETE | 3.73 | 733.95 | 21.60 | 353.21 | 13.53 | 17.86 | 116.22 | 18.67 | 1275.04 | 0.96 | 0.98 | 1.26 |
| lima | postgresql | PASS | COMPLETE | 3.77 | 801.65 | 54.01 | 1108.22 | 16.88 | 17.45 | 120.76 | 9.62 | 2128.59 | 1.21 | 1.14 | 1.28 |
| apple-container | sqlite | PASS | COMPLETE | 3.80 | 60.38 | 20.30 | 342.14 | 13.41 | 17.70 | 62.80 | 23.61 | 540.34 | 0.93 | 0.97 | 0.53 |
| apple-container | postgresql | PASS | COMPLETE | 3.98 | 110.70 | 35.39 | 976.12 | 13.69 | 16.70 | 36.98 | 9.13 | 1198.72 | 1.07 | 0.93 | 0.72 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 5 / 1 | 30 / 3 | 847 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 883 | 4 | 112.7 |
| docker | pg-colocated | 5 / 1 | 30 / 3 | 847 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 883 | 4 | 110.8 |
| native | postgresql | 6 / 2 | 24 / 2 | 847 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 878 | 4 | 111.3 |
| lima | postgresql | 5 / 1 | 30 / 3 | 876 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 912 | 4 | 118.2 |
| apple-container | postgresql | 5 / 1 | 23 / 1 | 847 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 876 | 2 | 109.7 |

## C18

New in pg62-v1: `stat f{1..1000}` in one process over 1,000 committed files. Committed base.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 4.22 | 326.85 | 21.95 | 152.39 | 13.63 | 16.73 | 299.35 | 17.98 | 848.86 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 4.42 | 360.52 | 52.69 | 199.62 | 17.46 | 16.57 | 260.35 | 8.85 | 916.06 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.67 | 372.15 | 47.41 | 155.27 | 15.67 | 16.53 | 246.16 | 9.27 | 862.45 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 4.34 | 44.32 | 42.16 | 1652.98 | 50.86 | 31.11 | 63.39 | 13.14 | 1897.96 | 10.85 | 3.73 | 2.24 |
| native | postgresql | PASS | COMPLETE | 3.94 | 43.32 | 67.69 | 1679.93 | 52.17 | 28.59 | 61.49 | 8.86 | 1942.05 | 8.42 | 2.99 | 2.12 |
| lima | sqlite | PASS | COMPLETE | 4.41 | 733.56 | 23.00 | 129.26 | 14.37 | 16.64 | 111.96 | 15.02 | 1043.80 | 0.85 | 1.05 | 1.23 |
| lima | postgresql | PASS | COMPLETE | 4.39 | 794.62 | 50.94 | 114.78 | 15.62 | 16.04 | 109.21 | 7.96 | 1109.18 | 0.57 | 0.89 | 1.21 |
| apple-container | sqlite | PASS | COMPLETE | 4.52 | 43.20 | 18.03 | 107.38 | 10.45 | 12.14 | 37.86 | 17.90 | 246.95 | 0.70 | 0.77 | 0.29 |
| apple-container | postgresql | PASS | COMPLETE | 4.61 | 113.58 | 34.76 | 148.26 | 13.64 | 12.30 | 37.67 | 9.26 | 369.47 | 0.74 | 0.78 | 0.40 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 5 / 1 | 32 / 3 | 39 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 77 | 4 | 5.1 |
| docker | pg-colocated | 5 / 1 | 32 / 3 | 39 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 77 | 4 | 5.2 |
| native | postgresql | 6 / 2 | 52 / 2 | 13 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 72 | 4 | 3.1 |
| lima | postgresql | 5 / 1 | 32 / 3 | 39 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 77 | 4 | 4.7 |
| apple-container | postgresql | 5 / 1 | 25 / 1 | 39 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 70 | 2 | 3.1 |

## Preparation, limits and cleanup

Attempted row preparation: 194.794 s total; maximum 5.695 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **INCOMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. 

Final disposition recorded by campaign owner.



Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

