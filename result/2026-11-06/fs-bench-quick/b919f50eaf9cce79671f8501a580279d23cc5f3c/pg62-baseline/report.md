# fs-bench-quick — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: INCOMPLETE.** 162 registered rows; execution {'PASS': 160, 'FAIL': 1, 'NOT_RUN': 1}. Final infrastructure cleanup: **INCOMPLETE**.

LayerFS `b919f50eaf9cce79671f8501a580279d23cc5f3c` (pinned artifacts of the published 2026-11-06 run; origin/layerfs_v2_0_0 head 6d820c756b differs only in one test file). Harness: rows ran at `3fdb4ef`; calibration `--attempt` and the phase-sum report option at `023698a` (branch `pg-perf-62`, local, unpushed). Pinned release CLI/daemon/Linux bundle of the published 2026-11-06 run, copied by APFS clone into a private cache after SHA-256 checks; `origin/layerfs_v2_0_0` head `6d820c756b` differs from it only in one test file. No product changes.

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 162}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Close is Sandbox close; Store release is Store remove (SQLite) or disconnect (PostgreSQL). End-to-end is the sum of the measured calls from create through Store release, without harness gaps; it excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: macOS 26.4.1, Apple M3 Max, 14 CPUs, 36 GiB; Docker Desktop 29.5.2 VM 8 CPUs / 7.75 GiB shared with other agents' Rust builds and another benchmark campaign; Lima `pg62-lima` and Apple Container `pg62-apple` 2 CPUs / 2 GiB each; PostgreSQL 17.11 container `pgbench-pg` with 2 CPUs / 2 GiB. Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

## Main observations

- **Counts confirm the round-trip diagnosis, with corrections.** Sandbox create opens **5 connections / 54 statements** (3 from the machine's worker, 2 from the new daemon; 3 / 32 when the worker still holds the Store from preparation). Mount opens **3 connections / 60 statements**, not 1: the co-located arm shows 2 of them come from the macOS caller and 1 from the daemon (Apple Container: 1 / 38). Exec, unmount and close open none, except on native, where each opens 2 (22 statements). Each connection open costs about 11 statements, including two `information_schema` scans of about 2.6–2.8 ms server time each.
- **Commit:** UpToDate (C14) 6 statements, no new connection. A Commit with changes opens the lane connection once (1 connection, then 0 on the second Commit, C13). Statements grow with entries: C03 53, one new file (C13) 118 then 113 on the second Commit, 100 files 136, 1,000 files 346, 1,110 entries (C04) 541, 10,000 files about 2,745, so about 113 fixed for a non-empty Commit (the parent estimated about 50) and about 0.23–0.27 statements per file beyond that. C01's Commit runs 46 transactions; each carries `BEGIN`, `SET LOCAL search_path`, mostly `SET LOCAL synchronous_commit`, and `COMMIT`.
- **Route cost explains most of the Commit and read gap.** On Docker, C01 Commit is SQLite 84 ms, PostgreSQL over the published port 178 ms (+94 ms for 346 statements ≈ 0.27 ms each), co-located 112 ms (+28 ms ≈ 0.08 ms each). Over all cells the co-located arm halves the Commit gap (median +58.6 → +19.4 ms) and cuts create by about 67 ms, while mount is unchanged (+90 vs +89 ms), so mount's extra cost is connection setup on both sides, not the daemon's route. Server-side statement time is small: all phases of C01 total 25.7 ms.
- **Measured round trips are shorter than the parent's 1–2 ms guess:** `SELECT 1` median 0.18 ms host→published port, 0.20 ms native Sandbox, 0.36 ms Docker via `host.docker.internal`, 0.07 ms Docker co-located, 0.44 ms Lima, 0.26 ms Apple Container. A fresh trust connection takes about 1.0–1.6 ms to ReadyForQuery and SCRAM adds about 1.1 ms on the host. Per-statement Commit cost on routed arms (about 0.27 ms on Docker) is close to one round trip.
- **Non-repeating committed reads are round-trip bound.** C17 reads 64 MiB with about 1,573 statements (about 3 per chunk: locate, pack head, ranged fetch). Exec: Docker SQLite 362 ms, PostgreSQL 1,305 ms, co-located 591 ms; native 277 vs 935; Lima 349 vs 2,072; Apple Container 309 vs 1,444. C09's zero file needs 6 statements and shows no gap, so the old case hid this cost.
- **Stat over committed files shows no PostgreSQL penalty here:** C18 Exec issues 39 statements for 1,000 `stat` calls (Docker 140 vs 162 ms, co-located 154). The smallfile stat gap (0.27–0.54×) is not reproduced by this single-process 1,000-file case.
- **First vs second Commit (C13):** Docker PostgreSQL 90 → 50 ms, co-located 35 → 29 ms, SQLite 18 → 16 ms; Apple Container 221 → 123 ms. Lima's 283 → 48 ms is mostly one 191 ms server-side `INSERT INTO binding_hint` stall, not the lane connection.
- **Server-side stalls occur under host load:** 19 statements took over 50 ms of server time (largest: 267 ms, a C16 Docker `INSERT INTO file_digest`). The Statement exec ms column shows them per row; they come from the shared Docker VM, not the route.
- Median PostgreSQL − SQLite per phase is in the table below; Exec is equal within noise except where reads hit committed data (C17).

## Fairness configuration (declared before the first row)

- **Server:** one dedicated `postgres:17-bookworm` (17.11) container `pgbench-pg`, `--cpus 2 --memory 2g`, its own volume, image defaults plus `shared_preload_libraries=pg_stat_statements`, `pg_stat_statements.track=top`, `track_utility=on`, `log_connections=on`, `max_connections=200`; `ssl=off`. The Store sets `synchronous_commit=off` per transaction (server default `on`). `SHOW ALL` is retained with the local receipts. One empty database per row.
- **`sslmode=disable` is explicit in every URL** (the earlier campaign left it unset, so the driver's `prefer` sent an SSL probe per connection).
- **Arms and routes.** `postgresql` (Docker-Desktop published port, kept as the declared reference arm): URL `127.0.0.1:55432`; the product rewrites it for the daemon to `host.docker.internal` (Docker; a name that resolves to 192.168.65.254 and an IPv6 address, the only route where the product forces a name), `192.168.5.2` (Lima) and the container gateway `192.168.64.1` (Apple Container); native dials the loopback directly. `pg-colocated` (Docker only): URL `172.17.0.9:5432`, the server's address on Docker's default bridge, which every Docker Sandbox joins; it is an IP literal, so it is not rewritten, and the macOS host reaches the same address through Docker Desktop's tunnel. Lima and Apple Container Sandboxes run inside their own VMs, and the owner rule keeps PostgreSQL out of guests, so they have no co-located arm.
- **Order:** declared alternation. Odd cells (C01, C03, …) run SQLite, PostgreSQL, co-located within each machine; even cells reverse it. Machines run native, Docker, Lima, Apple Container.
- **Equal gaps:** every row, SQLite included, makes one administrative `psql` call at each phase boundary (snapshot, reset, log marker); the call is control overhead (median 0.59 s per row) and is excluded from all phase times.
- **Cleanup:** Sandbox close is the same call on both backends and has its own column. Store release cannot be the same operation: `store remove` deletes only sqlite Stores and `store disconnect` only forgets PostgreSQL ones, so it is reported separately.
- **End-to-end** here is the sum of the measured calls (create, mount, Exec, Commit(s), unmount, close, Store release). Harness gaps are excluded because the runner rewrites the whole campaign state file with `fsync` around every call; that file grew to several MB in this 162-row campaign and added up to about 1.8 s of gap per row by the end, outside every phase timer. Raw invocation wall times stay in the receipts.
- **Load:** other agents compiled Rust in Docker and another benchmark campaign ran Lima/Apple machines concurrently; the 1-minute load average at each row's start (4.6–11.2, median 7.2) is in the tables. Timings are diagnostics; the counts are primary.

## Failures and unrun rows

- **C04 / Apple Container:** both rows failed before any measured work. Another owner's campaign cleanup stopped the Apple `container` service while this campaign ran (it had also stopped it once during calibration). PostgreSQL: `sandbox create` refused `Unavailable` (no network gateway; VM not running). SQLite: preparation's `store push` refused `Unavailable` (worker did not answer; nothing sent), so the row is NOT_RUN. No row was rerun; the service and machine were restarted for C05 onward.
- The co-located arm is NOT_RUN on native, Lima and Apple Container by design (above).
- Daemon `SqlWork` counters and PostgreSQL Workspace reader counters are not observed by this harness (product-side work); per-phase counts here are server-side only, and statements are not round trips: a first `prepare` per connection adds round trips that `pg_stat_statements` does not show.

## Resources

Retained for the #71 verification run: PostgreSQL container `pgbench-pg` and volume `pgbench-pg-data` (all 90 row databases kept; disconnect does not drop data), LayerFS machines `pg62-lima` (Lima VM `lfs-c0bfb23a-pg62-lima`) and `pg62-apple` (Apple container `lfs-c0bfb23a-pg62-apple`), the docker machine's worker `lfs-c0bfb23a-docker` and volume `lfs-c0bfb23a-docker-data`, and the private campaign home and cache. All 162 case cleanups are COMPLETE. Final infrastructure cleanup is therefore INCOMPLETE by intent; release commands are recorded in the campaign configuration.

## PostgreSQL minus SQLite

Median over cells of (PostgreSQL arm − SQLite) per machine, milliseconds, using only cells where both rows passed. Close is Sandbox close; Store release is `store disconnect` (PostgreSQL) versus `store remove` (SQLite), which the product does not unify.

| Machine | Arm | Cells | Create | Mount | Exec | Commit | Unmount | Close | Store release | End-to-end |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 18 | +228.1 | +90.3 | -0.2 | +58.6 | +0.7 | +1.9 | -9.8 | +341.0 |
| docker | pg-colocated | 18 | +161.4 | +89.2 | -22.5 | +19.4 | +0.6 | -4.1 | -9.7 | +221.5 |
| native | postgresql | 18 | +60.2 | +50.2 | +29.6 | +78.0 | +24.2 | +24.5 | -3.1 | +284.1 |
| lima | postgresql | 18 | +214.3 | +99.8 | +25.3 | +96.3 | +1.4 | -0.3 | -6.3 | +491.6 |
| apple-container | postgresql | 17 | +202.9 | +112.6 | +37.5 | +95.5 | +27.8 | +25.8 | -7.2 | +552.7 |

## Round-trip calibration

`pgrtt.py` from each client location: address resolution, then 20 fresh connections (TCP connect; one SSLRequest probe, which a plaintext server answers `N` and which an unset `sslmode` (`prefer`) adds to every connection; as the first server reply it also includes the server starting a backend; startup to ReadyForQuery), then 200 simple-protocol `SELECT 1` on one connection. Milliseconds, medians unless marked p90. Resolve is one `getaddrinfo` call and includes the client's first-call library loading. Guests and the trust rows use a trust-authenticated calibration role; the SCRAM rows add the Store user's SCRAM-SHA-256 exchange.

| Client | Route | Target | Peer | Auth | Resolve | TCP connect | SSL probe | Startup | SELECT 1 | SELECT 1 p90 |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| apple-container | postgresql | 192.168.64.1:55432 | 192.168.64.1 | trust | 4.111 | 0.358 | 1.396 | 1.557 | 0.264 | 0.431 |
| docker | pg-colocated | 172.17.0.9:5432 | 172.17.0.9 | trust | 0.587 | 0.058 | 0.400 | 0.750 | 0.071 | 0.086 |
| docker | postgresql | host.docker.internal:55432 | 192.168.65.254 | trust | 6.271 | 0.747 | 0.832 | 1.143 | 0.361 | 0.586 |
| lima | postgresql | 192.168.5.2:55432 | 192.168.5.2 | trust | 6.507 | 0.481 | 1.237 | 1.369 | 0.442 | 0.572 |
| native | postgresql | 127.0.0.1:55432 | 127.0.0.1 | trust | 1.626 | 0.133 | 0.837 | 0.942 | 0.195 | 0.243 |
| host (host/bridge-tunnel) | host/bridge-tunnel | 172.17.0.9:5432 | 172.17.0.9 | scram | 2.240 | 0.487 | 0.786 | 2.390 | 0.281 | 0.372 |
| host (host/bridge-tunnel) | host/bridge-tunnel | 172.17.0.9:5432 | 172.17.0.9 | trust | 2.407 | 0.509 | 0.802 | 1.124 | 0.286 | 0.386 |
| host (host/published) | host/published | 127.0.0.1:55432 | 127.0.0.1 | scram | 1.465 | 0.151 | 0.917 | 2.045 | 0.157 | 0.204 |
| host (host/published) | host/published | 127.0.0.1:55432 | 127.0.0.1 | trust | 3.101 | 0.132 | 0.827 | 0.951 | 0.180 | 0.231 |

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `1bc5e8d2b19e76c40d39de979f5624f54b932c1dba7c5d8165cc6eb56f702415` |
| Native daemon | `0d04f652b96cbffb3ba40775a41718ef0abf3612141347f1378cf2df40c9f375` |
| Linux bundle seal | `653cf3780ff8379c5ece5a832e9bec1fe112135afdc420e898fc5dba814b13df` |
| Docker tool image | `sha256:d58396888e87e971b74b84f099e7b0db493c9041e3aafe2111e30984a0ad3cec` |
| Namespace archive config | `UNAVAILABLE` |

## C01

Create 1,000 numbered files (also the sweep's 1,000-file point). Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 8.17 | 503.73 | 25.13 | 275.72 | 83.65 | 15.44 | 324.88 | 24.33 | 1252.89 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 8.17 | 611.03 | 111.04 | 253.52 | 178.34 | 15.03 | 390.28 | 6.79 | 1566.03 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 7.75 | 501.46 | 104.70 | 241.62 | 112.45 | 15.19 | 213.75 | 6.68 | 1195.84 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 9.19 | 63.12 | 39.25 | 593.41 | 146.88 | 41.55 | 60.88 | 10.33 | 955.42 | 2.15 | 1.76 | 0.76 |
| native | postgresql | PASS | COMPLETE | 8.93 | 86.97 | 74.21 | 657.92 | 230.70 | 63.20 | 81.83 | 6.34 | 1201.17 | 2.60 | 1.29 | 0.77 |
| lima | sqlite | PASS | COMPLETE | 7.75 | 756.83 | 25.19 | 237.73 | 80.13 | 14.73 | 110.91 | 18.43 | 1243.95 | 0.86 | 0.96 | 0.99 |
| lima | postgresql | PASS | COMPLETE | 7.29 | 942.16 | 126.07 | 262.67 | 187.35 | 13.87 | 110.62 | 6.99 | 1649.72 | 1.04 | 1.05 | 1.05 |
| apple-container | sqlite | PASS | COMPLETE | 7.51 | 104.99 | 25.03 | 255.02 | 95.26 | 14.07 | 38.13 | 15.87 | 548.38 | 0.92 | 1.14 | 0.44 |
| apple-container | postgresql | PASS | COMPLETE | 7.23 | 381.07 | 129.21 | 323.79 | 402.27 | 68.13 | 84.82 | 8.65 | 1397.94 | 1.28 | 2.26 | 0.89 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 54 / 5 | 60 / 3 | 8 / 0 | 346 / 1 | 0 / 0 | 0 / 0 | 468 | 9 | 25.7 |
| docker | pg-colocated | 54 / 5 | 60 / 3 | 8 / 0 | 346 / 1 | 0 / 0 | 0 / 0 | 468 | 9 | 23.2 |
| native | postgresql | 54 / 5 | 60 / 3 | 30 / 2 | 368 / 3 | 22 / 2 | 22 / 2 | 556 | 17 | 33.2 |
| lima | postgresql | 54 / 5 | 60 / 3 | 8 / 0 | 346 / 1 | 0 / 0 | 0 / 0 | 468 | 9 | 29.0 |
| apple-container | postgresql | 54 / 5 | 38 / 1 | 8 / 0 | 346 / 1 | 0 / 0 | 0 / 0 | 446 | 7 | 43.3 |

## C02

Create 1,000 files, then `stat` each (one process per file). Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 6.11 | 399.75 | 32.80 | 946.90 | 109.35 | 20.86 | 240.63 | 21.04 | 1771.34 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 6.11 | 516.51 | 119.32 | 815.08 | 178.20 | 13.95 | 256.34 | 7.69 | 1907.09 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.95 | 630.83 | 112.37 | 790.66 | 130.31 | 15.12 | 225.03 | 6.99 | 1911.31 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 6.81 | 39.82 | 35.30 | 5664.51 | 136.87 | 42.35 | 57.52 | 9.09 | 5985.47 | 5.98 | 1.25 | 3.38 |
| native | postgresql | PASS | COMPLETE | 7.23 | 99.83 | 90.27 | 5405.38 | 244.06 | 64.97 | 87.07 | 6.99 | 5998.57 | 6.63 | 1.37 | 3.15 |
| lima | sqlite | PASS | COMPLETE | 6.79 | 763.73 | 19.74 | 951.16 | 106.85 | 16.29 | 115.03 | 25.71 | 1998.50 | 1.00 | 0.98 | 1.13 |
| lima | postgresql | PASS | COMPLETE | 6.43 | 997.38 | 180.08 | 1164.80 | 299.83 | 17.59 | 112.51 | 12.67 | 2784.86 | 1.43 | 1.68 | 1.46 |
| apple-container | sqlite | PASS | COMPLETE | 7.04 | 60.59 | 32.89 | 764.43 | 91.42 | 11.13 | 56.24 | 16.65 | 1033.35 | 0.81 | 0.84 | 0.58 |
| apple-container | postgresql | PASS | COMPLETE | 7.04 | 282.97 | 137.27 | 810.34 | 247.61 | 39.22 | 60.59 | 8.08 | 1586.08 | 0.99 | 1.39 | 0.83 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 54 / 5 | 60 / 3 | 8 / 0 | 346 / 1 | 0 / 0 | 0 / 0 | 468 | 9 | 24.7 |
| docker | pg-colocated | 54 / 5 | 60 / 3 | 8 / 0 | 346 / 1 | 0 / 0 | 0 / 0 | 468 | 9 | 27.0 |
| native | postgresql | 54 / 5 | 60 / 3 | 30 / 2 | 368 / 3 | 22 / 2 | 22 / 2 | 556 | 17 | 35.5 |
| lima | postgresql | 54 / 5 | 60 / 3 | 8 / 0 | 346 / 1 | 0 / 0 | 0 / 0 | 468 | 9 | 40.5 |
| apple-container | postgresql | 54 / 5 | 38 / 1 | 8 / 0 | 346 / 1 | 0 / 0 | 0 / 0 | 446 | 7 | 26.2 |

## C03

Create 1,000 files, then remove them. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 8.24 | 412.57 | 27.50 | 608.06 | 15.98 | 12.82 | 239.37 | 13.44 | 1329.74 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 8.38 | 532.37 | 101.37 | 436.14 | 32.61 | 15.69 | 224.08 | 7.16 | 1349.42 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 8.38 | 500.79 | 99.03 | 566.02 | 29.55 | 17.01 | 248.88 | 7.83 | 1469.12 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 8.00 | 52.80 | 44.17 | 1353.45 | 108.70 | 30.26 | 70.50 | 12.96 | 1672.84 | 2.23 | 6.80 | 1.26 |
| native | postgresql | PASS | COMPLETE | 8.24 | 113.41 | 93.86 | 1596.12 | 132.46 | 59.24 | 110.83 | 9.24 | 2115.16 | 3.66 | 4.06 | 1.57 |
| lima | sqlite | PASS | COMPLETE | 8.31 | 765.13 | 19.57 | 288.06 | 13.71 | 12.97 | 109.74 | 15.23 | 1224.41 | 0.47 | 0.86 | 0.92 |
| lima | postgresql | PASS | COMPLETE | 8.29 | 922.53 | 99.93 | 359.34 | 35.32 | 14.36 | 111.99 | 7.22 | 1550.68 | 0.82 | 1.08 | 1.15 |
| apple-container | sqlite | PASS | COMPLETE | 8.29 | 73.47 | 14.38 | 403.72 | 12.18 | 14.23 | 36.05 | 13.38 | 567.41 | 0.66 | 0.76 | 0.43 |
| apple-container | postgresql | PASS | COMPLETE | 8.50 | 272.90 | 117.75 | 414.25 | 59.06 | 40.35 | 60.65 | 7.85 | 972.80 | 0.95 | 1.81 | 0.72 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 54 / 5 | 60 / 3 | 8 / 0 | 53 / 1 | 0 / 0 | 0 / 0 | 175 | 9 | 9.7 |
| docker | pg-colocated | 54 / 5 | 60 / 3 | 8 / 0 | 53 / 1 | 0 / 0 | 0 / 0 | 175 | 9 | 9.9 |
| native | postgresql | 54 / 5 | 60 / 3 | 30 / 2 | 75 / 3 | 22 / 2 | 22 / 2 | 263 | 17 | 25.7 |
| lima | postgresql | 54 / 5 | 60 / 3 | 8 / 0 | 53 / 1 | 0 / 0 | 0 / 0 | 175 | 9 | 9.6 |
| apple-container | postgresql | 54 / 5 | 38 / 1 | 8 / 0 | 53 / 1 | 0 / 0 | 0 / 0 | 153 | 7 | 9.1 |

## C04

Create 110 directories and 1,000 empty files. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 8.27 | 360.69 | 30.11 | 688.59 | 87.44 | 12.89 | 259.18 | 16.43 | 1455.34 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 8.29 | 644.24 | 112.39 | 665.34 | 247.46 | 14.00 | 251.16 | 7.50 | 1942.09 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 8.29 | 766.75 | 112.13 | 662.59 | 146.25 | 14.21 | 256.50 | 7.73 | 1966.16 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 8.30 | 40.54 | 35.11 | 3819.45 | 145.37 | 34.91 | 58.51 | 10.48 | 4144.38 | 5.55 | 1.66 | 2.85 |
| native | postgresql | PASS | COMPLETE | 8.50 | 140.19 | 79.65 | 4173.04 | 308.59 | 58.06 | 83.32 | 6.91 | 4849.75 | 6.27 | 1.25 | 2.50 |
| lima | sqlite | PASS | COMPLETE | 8.57 | 703.57 | 15.06 | 568.98 | 82.79 | 13.09 | 114.87 | 11.13 | 1509.49 | 0.83 | 0.95 | 1.04 |
| lima | postgresql | PASS | COMPLETE | 8.57 | 958.50 | 98.84 | 546.79 | 257.54 | 14.17 | 115.98 | 7.43 | 1999.27 | 0.82 | 1.04 | 1.03 |
| apple-container | sqlite | NOT_RUN | COMPLETE | UNAVAILABLE | — | — | — | — | — | — | 9.29 | — | — | — | — |
| apple-container | postgresql | FAIL | COMPLETE | 8.20 | 31.46 | — | — | — | — | — | 6.32 | — | — | — | — |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 54 / 5 | 60 / 3 | 8 / 0 | 541 / 1 | 0 / 0 | 0 / 0 | 663 | 9 | 19.9 |
| docker | pg-colocated | 54 / 5 | 60 / 3 | 8 / 0 | 541 / 1 | 0 / 0 | 0 / 0 | 663 | 9 | 18.8 |
| native | postgresql | 54 / 5 | 60 / 3 | 30 / 2 | 563 / 3 | 22 / 2 | 22 / 2 | 751 | 17 | 30.3 |
| lima | postgresql | 54 / 5 | 60 / 3 | 8 / 0 | 541 / 1 | 0 / 0 | 0 / 0 | 663 | 9 | 19.3 |
| apple-container | postgresql | 0 / 0 | — / — | — / — | — / — | — / — | 0 / 0 | 0 | 0 | 0.0 |

- apple-container/postgresql: sandbox_create: CLI/process exit 125
- apple-container/sqlite: store_push: CLI/process exit 125

## C05

C04, then `find . -type f \| wc -l`. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 6.68 | 278.24 | 21.93 | 643.25 | 87.34 | 13.28 | 236.27 | 12.85 | 1293.16 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 6.71 | 519.00 | 98.90 | 658.77 | 244.13 | 15.81 | 241.94 | 7.06 | 1785.62 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 6.73 | 489.36 | 95.68 | 619.09 | 133.17 | 13.61 | 200.80 | 6.81 | 1558.51 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 6.89 | 26.65 | 33.67 | 3404.42 | 146.86 | 34.39 | 55.70 | 9.19 | 3710.88 | 5.29 | 1.68 | 2.87 |
| native | postgresql | PASS | COMPLETE | 6.74 | 76.50 | 76.21 | 3400.17 | 277.18 | 56.40 | 75.05 | 7.03 | 3968.56 | 5.16 | 1.14 | 2.22 |
| lima | sqlite | PASS | COMPLETE | 6.63 | 747.75 | 15.95 | 606.37 | 84.04 | 38.27 | 111.29 | 12.16 | 1615.83 | 0.94 | 0.96 | 1.25 |
| lima | postgresql | PASS | COMPLETE | 6.63 | 928.72 | 103.39 | 631.94 | 307.18 | 13.91 | 112.84 | 6.79 | 2104.76 | 0.96 | 1.26 | 1.18 |
| apple-container | sqlite | PASS | COMPLETE | 6.18 | 67.07 | 14.68 | 517.86 | 94.08 | 11.29 | 34.46 | 12.75 | 752.20 | 0.81 | 1.08 | 0.58 |
| apple-container | postgresql | PASS | COMPLETE | 5.92 | 272.63 | 119.23 | 539.43 | 323.12 | 37.83 | 59.20 | 6.84 | 1358.28 | 0.82 | 1.32 | 0.76 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 54 / 5 | 60 / 3 | 8 / 0 | 541 / 1 | 0 / 0 | 0 / 0 | 663 | 9 | 18.7 |
| docker | pg-colocated | 54 / 5 | 60 / 3 | 8 / 0 | 541 / 1 | 0 / 0 | 0 / 0 | 663 | 9 | 16.9 |
| native | postgresql | 54 / 5 | 60 / 3 | 30 / 2 | 563 / 3 | 22 / 2 | 22 / 2 | 751 | 17 | 27.1 |
| lima | postgresql | 54 / 5 | 60 / 3 | 8 / 0 | 541 / 1 | 0 / 0 | 0 / 0 | 663 | 9 | 21.5 |
| apple-container | postgresql | 54 / 5 | 38 / 1 | 8 / 0 | 541 / 1 | 0 / 0 | 0 / 0 | 641 | 7 | 20.1 |

## C06

Write 64 MiB of zeros. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 5.98 | 338.61 | 24.91 | 167.81 | 245.19 | 19.15 | 220.55 | 14.08 | 1030.30 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 6.07 | 589.88 | 112.82 | 182.50 | 298.15 | 23.20 | 222.57 | 7.50 | 1436.61 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.64 | 580.52 | 112.59 | 181.55 | 320.01 | 20.76 | 264.48 | 7.54 | 1487.46 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 5.61 | 38.86 | 33.55 | 154.07 | 306.74 | 27.12 | 60.26 | 9.16 | 629.76 | 0.92 | 1.25 | 0.61 |
| native | postgresql | PASS | COMPLETE | 5.92 | 94.41 | 79.05 | 183.75 | 386.06 | 49.28 | 78.88 | 6.52 | 877.95 | 1.01 | 1.29 | 0.61 |
| lima | sqlite | PASS | COMPLETE | 6.15 | 709.55 | 16.02 | 137.19 | 228.80 | 17.95 | 111.28 | 11.67 | 1232.46 | 0.82 | 0.93 | 1.20 |
| lima | postgresql | PASS | COMPLETE | 5.98 | 948.57 | 105.02 | 177.41 | 356.27 | 20.12 | 110.91 | 7.51 | 1725.80 | 0.97 | 1.19 | 1.20 |
| apple-container | sqlite | PASS | COMPLETE | 6.13 | 56.61 | 13.22 | 162.92 | 250.14 | 12.19 | 34.72 | 19.73 | 549.53 | 0.97 | 1.02 | 0.53 |
| apple-container | postgresql | PASS | COMPLETE | 6.13 | 233.85 | 118.00 | 189.85 | 324.18 | 68.70 | 59.60 | 6.82 | 1001.00 | 1.04 | 1.09 | 0.70 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 54 / 5 | 60 / 3 | 0 / 0 | 144 / 1 | 0 / 0 | 0 / 0 | 258 | 9 | 14.1 |
| docker | pg-colocated | 54 / 5 | 60 / 3 | 0 / 0 | 144 / 1 | 0 / 0 | 0 / 0 | 258 | 9 | 14.9 |
| native | postgresql | 54 / 5 | 60 / 3 | 22 / 2 | 166 / 3 | 22 / 2 | 22 / 2 | 346 | 17 | 23.7 |
| lima | postgresql | 54 / 5 | 60 / 3 | 0 / 0 | 144 / 1 | 0 / 0 | 0 / 0 | 258 | 9 | 16.8 |
| apple-container | postgresql | 54 / 5 | 38 / 1 | 0 / 0 | 144 / 1 | 0 / 0 | 0 / 0 | 236 | 7 | 10.7 |

## C07

Write 64 MiB of zeros, then copy it. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 6.06 | 310.13 | 20.61 | 369.01 | 466.29 | 25.12 | 249.81 | 15.21 | 1456.18 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 6.46 | 558.74 | 104.26 | 288.67 | 509.82 | 24.61 | 223.68 | 7.32 | 1717.09 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 6.46 | 532.51 | 96.86 | 298.69 | 475.30 | 23.16 | 244.30 | 6.72 | 1677.53 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 6.15 | 25.32 | 33.34 | 281.04 | 573.32 | 28.54 | 62.19 | 9.62 | 1013.37 | 0.76 | 1.23 | 0.70 |
| native | postgresql | PASS | COMPLETE | 6.15 | 79.33 | 83.11 | 393.47 | 620.08 | 56.08 | 87.94 | 6.82 | 1326.84 | 1.36 | 1.22 | 0.77 |
| lima | sqlite | PASS | COMPLETE | 6.42 | 736.00 | 17.29 | 305.16 | 458.30 | 23.95 | 111.95 | 11.74 | 1664.39 | 0.83 | 0.98 | 1.14 |
| lima | postgresql | PASS | COMPLETE | 7.03 | 939.86 | 96.19 | 263.43 | 514.67 | 22.95 | 106.79 | 7.14 | 1951.02 | 0.91 | 1.01 | 1.14 |
| apple-container | sqlite | PASS | COMPLETE | 8.34 | 57.97 | 16.86 | 281.89 | 442.20 | 32.51 | 33.16 | 12.37 | 876.96 | 0.76 | 0.95 | 0.60 |
| apple-container | postgresql | PASS | COMPLETE | 8.34 | 238.84 | 126.59 | 277.60 | 537.67 | 55.04 | 58.87 | 7.05 | 1301.66 | 0.96 | 1.05 | 0.76 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 54 / 5 | 60 / 3 | 0 / 0 | 153 / 1 | 0 / 0 | 0 / 0 | 267 | 9 | 14.5 |
| docker | pg-colocated | 54 / 5 | 60 / 3 | 0 / 0 | 153 / 1 | 0 / 0 | 0 / 0 | 267 | 9 | 12.1 |
| native | postgresql | 54 / 5 | 60 / 3 | 22 / 2 | 175 / 3 | 22 / 2 | 22 / 2 | 355 | 17 | 27.5 |
| lima | postgresql | 54 / 5 | 60 / 3 | 0 / 0 | 153 / 1 | 0 / 0 | 0 / 0 | 267 | 9 | 13.3 |
| apple-container | postgresql | 54 / 5 | 38 / 1 | 0 / 0 | 153 / 1 | 0 / 0 | 0 / 0 | 245 | 7 | 13.5 |

## C08

Write 64 MiB of zeros, then read it. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 7.25 | 279.13 | 18.93 | 181.45 | 253.33 | 18.20 | 213.12 | 14.28 | 978.42 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 7.53 | 514.76 | 97.86 | 189.74 | 303.05 | 19.89 | 214.89 | 7.17 | 1347.35 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 7.84 | 491.21 | 94.32 | 189.73 | 264.37 | 19.12 | 229.23 | 6.77 | 1294.77 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 7.84 | 27.89 | 33.26 | 161.46 | 336.58 | 27.61 | 56.49 | 9.15 | 652.45 | 0.89 | 1.33 | 0.67 |
| native | postgresql | PASS | COMPLETE | 7.91 | 86.36 | 76.18 | 187.45 | 431.36 | 49.82 | 94.80 | 6.88 | 932.84 | 0.99 | 1.42 | 0.69 |
| lima | sqlite | PASS | COMPLETE | 6.45 | 715.60 | 15.68 | 130.67 | 231.00 | 16.87 | 115.02 | 11.21 | 1236.06 | 0.72 | 0.91 | 1.26 |
| lima | postgresql | PASS | COMPLETE | 6.75 | 915.93 | 103.57 | 128.72 | 290.74 | 17.63 | 110.93 | 6.69 | 1574.21 | 0.68 | 0.96 | 1.17 |
| apple-container | sqlite | PASS | COMPLETE | 6.17 | 73.93 | 14.00 | 139.21 | 237.83 | 25.06 | 34.26 | 11.80 | 536.09 | 0.77 | 0.94 | 0.55 |
| apple-container | postgresql | PASS | COMPLETE | 6.17 | 247.98 | 119.59 | 178.95 | 344.01 | 54.28 | 58.73 | 6.79 | 1010.33 | 0.94 | 1.14 | 0.75 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 54 / 5 | 60 / 3 | 0 / 0 | 144 / 1 | 0 / 0 | 0 / 0 | 258 | 9 | 12.4 |
| docker | pg-colocated | 54 / 5 | 60 / 3 | 0 / 0 | 144 / 1 | 0 / 0 | 0 / 0 | 258 | 9 | 11.2 |
| native | postgresql | 54 / 5 | 60 / 3 | 22 / 2 | 166 / 3 | 22 / 2 | 22 / 2 | 346 | 17 | 23.1 |
| lima | postgresql | 54 / 5 | 60 / 3 | 0 / 0 | 144 / 1 | 0 / 0 | 0 / 0 | 258 | 9 | 14.5 |
| apple-container | postgresql | 54 / 5 | 38 / 1 | 0 / 0 | 144 / 1 | 0 / 0 | 0 / 0 | 236 | 7 | 14.6 |

## C09

Read the committed 64 MiB zero file (dedups to about one chunk). Committed base.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 5.69 | 261.73 | 16.13 | 123.25 | 10.82 | 15.77 | 241.06 | 14.12 | 682.89 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.87 | 426.56 | 103.75 | 117.73 | 17.28 | 15.98 | 232.26 | 6.39 | 919.95 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 6.36 | 405.76 | 106.84 | 89.01 | 12.99 | 18.50 | 246.09 | 7.95 | 887.15 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 6.00 | 40.96 | 37.16 | 48.50 | 61.60 | 24.45 | 57.06 | 8.56 | 278.28 | 0.39 | 5.69 | 0.41 |
| native | postgresql | PASS | COMPLETE | 5.92 | 78.35 | 72.52 | 72.17 | 95.21 | 51.31 | 80.78 | 6.54 | 456.88 | 0.61 | 5.51 | 0.50 |
| lima | sqlite | PASS | COMPLETE | 5.90 | 716.89 | 15.08 | 64.03 | 11.07 | 14.09 | 115.07 | 13.18 | 949.42 | 0.52 | 1.02 | 1.39 |
| lima | postgresql | PASS | COMPLETE | 5.59 | 867.82 | 107.66 | 68.05 | 17.75 | 14.02 | 105.81 | 7.18 | 1188.30 | 0.58 | 1.03 | 1.29 |
| apple-container | sqlite | PASS | COMPLETE | 5.30 | 56.50 | 16.10 | 73.68 | 8.89 | 17.98 | 35.36 | 14.30 | 222.81 | 0.60 | 0.82 | 0.33 |
| apple-container | postgresql | PASS | COMPLETE | 5.28 | 233.82 | 164.51 | 110.09 | 40.92 | 45.26 | 59.67 | 5.82 | 660.09 | 0.94 | 2.37 | 0.72 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 32 / 3 | 61 / 3 | 6 / 0 | 7 / 0 | 0 / 0 | 0 / 0 | 106 | 6 | 7.8 |
| docker | pg-colocated | 32 / 3 | 61 / 3 | 6 / 0 | 7 / 0 | 0 / 0 | 0 / 0 | 106 | 6 | 7.8 |
| native | postgresql | 54 / 5 | 61 / 3 | 28 / 2 | 29 / 2 | 22 / 2 | 22 / 2 | 216 | 16 | 22.4 |
| lima | postgresql | 32 / 3 | 61 / 3 | 6 / 0 | 7 / 0 | 0 / 0 | 0 / 0 | 106 | 6 | 11.2 |
| apple-container | postgresql | 32 / 3 | 39 / 1 | 6 / 0 | 7 / 0 | 0 / 0 | 0 / 0 | 84 | 4 | 7.4 |

## C10

Copy the committed 64 MiB zero file. Committed base.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 4.87 | 271.72 | 17.28 | 243.35 | 52.88 | 21.29 | 250.06 | 16.59 | 873.16 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.38 | 424.72 | 109.91 | 225.32 | 117.05 | 25.46 | 271.93 | 7.22 | 1181.61 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 5.59 | 396.99 | 102.10 | 227.67 | 75.73 | 24.43 | 224.19 | 7.53 | 1058.64 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 6.15 | 26.44 | 31.57 | 187.04 | 141.90 | 29.32 | 58.67 | 9.96 | 484.89 | 0.77 | 2.68 | 0.56 |
| native | postgresql | PASS | COMPLETE | 5.90 | 84.36 | 73.63 | 215.24 | 176.46 | 49.09 | 82.62 | 6.98 | 688.38 | 0.96 | 1.51 | 0.58 |
| lima | sqlite | PASS | COMPLETE | 4.58 | 736.62 | 14.07 | 155.24 | 45.94 | 18.19 | 112.19 | 10.12 | 1092.37 | 0.64 | 0.87 | 1.25 |
| lima | postgresql | PASS | COMPLETE | 4.72 | 864.55 | 100.31 | 168.61 | 92.27 | 20.04 | 113.86 | 7.07 | 1366.71 | 0.75 | 0.79 | 1.16 |
| apple-container | sqlite | PASS | COMPLETE | 4.64 | 39.00 | 11.51 | 177.68 | 77.19 | 35.04 | 32.69 | 13.14 | 386.26 | 0.73 | 1.46 | 0.44 |
| apple-container | postgresql | PASS | COMPLETE | 4.69 | 209.48 | 128.92 | 215.17 | 131.37 | 50.83 | 59.42 | 6.74 | 801.93 | 0.95 | 1.12 | 0.68 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 32 / 3 | 61 / 3 | 6 / 0 | 113 / 1 | 0 / 0 | 0 / 0 | 212 | 7 | 9.7 |
| docker | pg-colocated | 32 / 3 | 61 / 3 | 6 / 0 | 113 / 1 | 0 / 0 | 0 / 0 | 212 | 7 | 8.7 |
| native | postgresql | 54 / 5 | 61 / 3 | 28 / 2 | 135 / 3 | 22 / 2 | 22 / 2 | 322 | 17 | 20.1 |
| lima | postgresql | 32 / 3 | 61 / 3 | 6 / 0 | 113 / 1 | 0 / 0 | 0 / 0 | 212 | 7 | 12.4 |
| apple-container | postgresql | 32 / 3 | 39 / 1 | 6 / 0 | 113 / 1 | 0 / 0 | 0 / 0 | 190 | 5 | 8.6 |

## C11

Overwrite the committed zero file with zeros (`conv=notrunc`). Committed base.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 5.11 | 350.74 | 24.14 | 178.31 | 193.71 | 25.51 | 260.70 | 25.23 | 1058.33 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 5.02 | 516.54 | 133.74 | 183.34 | 210.00 | 23.33 | 259.55 | 8.04 | 1334.55 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 4.63 | 501.47 | 130.81 | 157.51 | 186.45 | 26.53 | 268.46 | 8.74 | 1279.95 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 4.69 | 41.67 | 38.33 | 164.53 | 262.72 | 30.86 | 63.22 | 11.36 | 612.68 | 0.92 | 1.36 | 0.58 |
| native | postgresql | PASS | COMPLETE | 4.88 | 113.33 | 92.64 | 197.96 | 339.46 | 74.72 | 98.39 | 9.59 | 926.08 | 1.08 | 1.62 | 0.69 |
| lima | sqlite | PASS | COMPLETE | 4.98 | 736.17 | 19.45 | 115.18 | 151.56 | 24.31 | 117.92 | 17.20 | 1181.79 | 0.65 | 0.78 | 1.12 |
| lima | postgresql | PASS | COMPLETE | 5.52 | 948.00 | 200.94 | 213.38 | 236.99 | 28.08 | 119.54 | 9.72 | 1756.66 | 1.16 | 1.13 | 1.32 |
| apple-container | sqlite | PASS | COMPLETE | 7.09 | 63.88 | 17.81 | 119.54 | 157.79 | 31.04 | 37.34 | 15.22 | 442.61 | 0.67 | 0.81 | 0.42 |
| apple-container | postgresql | PASS | COMPLETE | 7.40 | 266.74 | 130.37 | 153.37 | 208.79 | 78.96 | 86.62 | 8.64 | 933.49 | 0.84 | 0.99 | 0.70 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 32 / 3 | 61 / 3 | 4 / 0 | 58 / 1 | 0 / 0 | 0 / 0 | 155 | 7 | 10.1 |
| docker | pg-colocated | 32 / 3 | 61 / 3 | 4 / 0 | 58 / 1 | 0 / 0 | 0 / 0 | 155 | 7 | 9.8 |
| native | postgresql | 54 / 5 | 61 / 3 | 26 / 2 | 80 / 3 | 22 / 2 | 22 / 2 | 265 | 17 | 27.4 |
| lima | postgresql | 32 / 3 | 61 / 3 | 4 / 0 | 58 / 1 | 0 / 0 | 0 / 0 | 155 | 7 | 12.1 |
| apple-container | postgresql | 32 / 3 | 39 / 1 | 4 / 0 | 58 / 1 | 0 / 0 | 0 / 0 | 133 | 5 | 6.5 |

## C12

Git init, 100 files, add and Git commit. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 6.34 | 622.51 | 25.30 | 393.30 | 59.33 | 16.77 | 481.10 | 19.51 | 1617.80 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 6.41 | 891.92 | 130.55 | 224.36 | 197.72 | 17.14 | 562.50 | 8.49 | 2032.68 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 6.79 | 656.20 | 143.70 | 271.94 | 110.48 | 17.09 | 367.77 | 8.85 | 1576.03 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 7.12 | 48.04 | 41.24 | 483.24 | 138.34 | 41.91 | 70.62 | 14.18 | 837.56 | 1.23 | 2.33 | 0.52 |
| native | postgresql | PASS | COMPLETE | 7.13 | 107.06 | 97.56 | 485.88 | 278.25 | 65.78 | 97.54 | 9.29 | 1141.36 | 2.17 | 1.41 | 0.56 |
| lima | sqlite | PASS | COMPLETE | 7.03 | 746.36 | 20.45 | 177.39 | 55.46 | 16.91 | 118.64 | 54.22 | 1189.43 | 0.45 | 0.93 | 0.74 |
| lima | postgresql | PASS | COMPLETE | 6.60 | 1015.96 | 161.67 | 229.96 | 248.39 | 19.95 | 110.35 | 8.88 | 1795.16 | 1.02 | 1.26 | 0.88 |
| apple-container | sqlite | PASS | COMPLETE | 7.55 | 71.92 | 16.24 | 190.45 | 68.05 | 12.62 | 37.15 | 14.79 | 411.21 | 0.48 | 1.15 | 0.25 |
| apple-container | postgresql | PASS | COMPLETE | 7.43 | 290.09 | 132.78 | 222.63 | 274.55 | 61.12 | 63.90 | 9.10 | 1054.17 | 0.99 | 1.39 | 0.52 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 54 / 5 | 60 / 3 | 0 / 0 | 381 / 1 | 0 / 0 | 0 / 0 | 495 | 9 | 23.1 |
| docker | pg-colocated | 54 / 5 | 60 / 3 | 0 / 0 | 381 / 1 | 0 / 0 | 0 / 0 | 495 | 9 | 24.1 |
| native | postgresql | 54 / 5 | 60 / 3 | 22 / 2 | 399 / 3 | 22 / 2 | 22 / 2 | 579 | 17 | 37.2 |
| lima | postgresql | 54 / 5 | 60 / 3 | 0 / 0 | 381 / 1 | 0 / 0 | 0 / 0 | 495 | 9 | 28.6 |
| apple-container | postgresql | 54 / 5 | 38 / 1 | 0 / 0 | 381 / 1 | 0 / 0 | 0 / 0 | 473 | 7 | 20.3 |

## C13

New in pg62-v1: `echo 1 > a` and Commit, then `echo 2 > b` and a second Commit on the same Workspace (Commit 2). Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Commit 2 ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 7.91 | 1579.83 | 27.27 | 50.40 | 17.94 | 16.22 | 18.46 | 727.30 | 26.66 | 2505.76 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 7.71 | 1336.82 | 144.57 | 57.80 | 90.75 | 50.99 | 17.91 | 577.81 | 9.18 | 2322.26 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 7.89 | 1187.26 | 145.21 | 61.42 | 35.79 | 29.99 | 20.09 | 804.42 | 10.01 | 2330.47 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 7.59 | 45.18 | 37.43 | 26.61 | 86.39 | 199.16 | 29.80 | 67.44 | 14.14 | 535.32 | 0.53 | 4.82 | 0.21 |
| native | postgresql | PASS | COMPLETE | 7.62 | 118.41 | 98.23 | 63.74 | 345.95 | 192.23 | 61.09 | 103.04 | 9.16 | 1049.44 | 1.10 | 3.81 | 0.45 |
| lima | sqlite | PASS | COMPLETE | 9.11 | 763.10 | 22.94 | 21.64 | 18.45 | 17.01 | 17.37 | 122.32 | 15.31 | 1025.89 | 0.43 | 1.03 | 0.41 |
| lima | postgresql | PASS | COMPLETE | 9.02 | 1044.25 | 167.70 | 20.50 | 283.48 | 48.23 | 17.80 | 114.65 | 8.69 | 1727.02 | 0.35 | 3.12 | 0.74 |
| apple-container | sqlite | PASS | COMPLETE | 8.87 | 59.75 | 15.12 | 30.86 | 14.54 | 12.87 | 12.33 | 36.55 | 16.63 | 222.33 | 0.61 | 0.81 | 0.09 |
| apple-container | postgresql | PASS | COMPLETE | 9.04 | 296.77 | 152.25 | 69.91 | 221.94 | 123.28 | 38.18 | 83.79 | 9.05 | 1058.22 | 1.21 | 2.45 | 0.46 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Exec 2 | Commit 2 | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 54 / 5 | 60 / 3 | 0 / 0 | 118 / 1 | 0 / 0 | 113 / 0 | 0 / 0 | 0 / 0 | 345 | 9 | 18.7 |
| docker | pg-colocated | 54 / 5 | 60 / 3 | 0 / 0 | 118 / 1 | 0 / 0 | 113 / 0 | 0 / 0 | 0 / 0 | 345 | 9 | 19.2 |
| native | postgresql | 54 / 5 | 60 / 3 | 22 / 2 | 140 / 3 | 22 / 2 | 135 / 2 | 22 / 2 | 22 / 2 | 477 | 21 | 39.6 |
| lima | postgresql | 54 / 5 | 60 / 3 | 0 / 0 | 118 / 1 | 0 / 0 | 113 / 0 | 0 / 0 | 0 / 0 | 345 | 9 | 211.7 |
| apple-container | postgresql | 54 / 5 | 38 / 1 | 0 / 0 | 118 / 1 | 0 / 0 | 113 / 0 | 0 / 0 | 0 / 0 | 323 | 7 | 29.3 |

## C14

New in pg62-v1: file sweep, 0 files (`true`); the Commit is UpToDate. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 10.03 | 362.68 | 23.36 | 41.05 | 15.73 | 17.76 | 279.92 | 18.33 | 758.84 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 10.47 | 1076.34 | 126.94 | 53.66 | 16.99 | 15.62 | 527.92 | 8.70 | 1826.17 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 10.25 | 1681.60 | 126.12 | 42.47 | 31.24 | 16.42 | 760.10 | 8.50 | 2666.45 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 10.21 | 49.61 | 38.32 | 28.46 | 233.84 | 32.15 | 84.29 | 14.82 | 481.48 | 0.69 | 14.86 | 0.63 |
| native | postgresql | PASS | COMPLETE | 9.36 | 122.74 | 127.85 | 57.92 | 143.35 | 94.74 | 103.14 | 11.54 | 661.28 | 1.08 | 8.44 | 0.36 |
| lima | sqlite | PASS | COMPLETE | 8.96 | 737.50 | 20.48 | 26.48 | 14.83 | 16.21 | 113.89 | 14.60 | 943.98 | 0.65 | 0.94 | 1.24 |
| lima | postgresql | PASS | COMPLETE | 9.95 | 1108.81 | 157.20 | 22.26 | 24.34 | 20.83 | 120.08 | 9.79 | 1463.31 | 0.41 | 1.43 | 0.80 |
| apple-container | sqlite | PASS | COMPLETE | 7.91 | 96.51 | 19.81 | 24.83 | 12.98 | 14.28 | 39.80 | 18.72 | 226.94 | 0.60 | 0.83 | 0.30 |
| apple-container | postgresql | PASS | COMPLETE | 8.33 | 359.11 | 218.20 | 74.11 | 73.17 | 41.16 | 106.73 | 9.82 | 882.30 | 1.38 | 4.31 | 0.48 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 54 / 5 | 60 / 3 | 0 / 0 | 6 / 0 | 0 / 0 | 0 / 0 | 120 | 8 | 12.6 |
| docker | pg-colocated | 54 / 5 | 60 / 3 | 0 / 0 | 6 / 0 | 0 / 0 | 0 / 0 | 120 | 8 | 13.5 |
| native | postgresql | 54 / 5 | 60 / 3 | 22 / 2 | 28 / 2 | 22 / 2 | 22 / 2 | 208 | 16 | 30.3 |
| lima | postgresql | 54 / 5 | 60 / 3 | 0 / 0 | 6 / 0 | 0 / 0 | 0 / 0 | 120 | 8 | 19.3 |
| apple-container | postgresql | 54 / 5 | 38 / 1 | 0 / 0 | 6 / 0 | 0 / 0 | 0 / 0 | 98 | 6 | 13.7 |

## C15

New in pg62-v1: file sweep, 100 numbered files. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 7.43 | 408.46 | 19.76 | 75.59 | 25.13 | 14.06 | 258.14 | 18.61 | 819.75 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 7.63 | 752.97 | 134.76 | 66.50 | 101.51 | 18.41 | 293.93 | 8.61 | 1376.69 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 7.82 | 713.23 | 130.03 | 78.67 | 51.32 | 17.39 | 363.68 | 9.10 | 1363.42 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 7.59 | 40.92 | 37.07 | 116.96 | 109.09 | 38.68 | 66.86 | 12.52 | 422.11 | 1.55 | 4.34 | 0.51 |
| native | postgresql | PASS | COMPLETE | 7.47 | 101.32 | 87.65 | 137.18 | 160.90 | 57.09 | 90.39 | 7.48 | 642.01 | 2.06 | 1.58 | 0.47 |
| lima | sqlite | PASS | COMPLETE | 7.85 | 739.75 | 20.98 | 45.11 | 25.16 | 15.77 | 114.77 | 14.40 | 975.93 | 0.60 | 1.00 | 1.19 |
| lima | postgresql | PASS | COMPLETE | 7.78 | 1012.73 | 129.24 | 49.54 | 192.12 | 17.15 | 114.50 | 8.39 | 1523.68 | 0.74 | 1.89 | 1.11 |
| apple-container | sqlite | PASS | COMPLETE | 7.88 | 60.33 | 18.42 | 61.64 | 35.73 | 12.81 | 37.05 | 14.39 | 240.37 | 0.82 | 1.42 | 0.29 |
| apple-container | postgresql | PASS | COMPLETE | 7.73 | 292.90 | 124.98 | 111.23 | 136.19 | 62.35 | 62.82 | 8.89 | 799.36 | 1.67 | 1.34 | 0.58 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 54 / 5 | 60 / 3 | 0 / 0 | 136 / 1 | 0 / 0 | 0 / 0 | 250 | 9 | 23.8 |
| docker | pg-colocated | 54 / 5 | 60 / 3 | 0 / 0 | 136 / 1 | 0 / 0 | 0 / 0 | 250 | 9 | 21.7 |
| native | postgresql | 54 / 5 | 60 / 3 | 22 / 2 | 158 / 3 | 22 / 2 | 22 / 2 | 338 | 17 | 29.5 |
| lima | postgresql | 54 / 5 | 60 / 3 | 0 / 0 | 136 / 1 | 0 / 0 | 0 / 0 | 250 | 9 | 117.9 |
| apple-container | postgresql | 54 / 5 | 38 / 1 | 0 / 0 | 136 / 1 | 0 / 0 | 0 / 0 | 228 | 7 | 26.0 |

## C16

New in pg62-v1: file sweep, 10,000 numbered files; prospectively declared 25 s budget. Empty start.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 9.30 | 881.71 | 21.15 | 2536.12 | 1106.50 | 24.42 | 668.07 | 25.35 | 5263.31 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 8.90 | 1368.18 | 136.12 | 2994.40 | 2783.15 | 31.38 | 380.44 | 11.95 | 7705.62 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 8.98 | 936.08 | 127.31 | 2503.58 | 1324.36 | 24.30 | 492.24 | 9.18 | 5417.05 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 8.31 | 42.96 | 39.33 | 5904.66 | 1118.32 | 155.87 | 86.22 | 13.21 | 7360.58 | 2.33 | 1.01 | 1.40 |
| native | postgresql | PASS | COMPLETE | 8.29 | 107.79 | 94.71 | 6618.27 | 1920.33 | 180.37 | 99.32 | 8.99 | 9029.78 | 2.21 | 0.69 | 1.17 |
| lima | sqlite | PASS | COMPLETE | 8.31 | 736.27 | 25.96 | 2022.70 | 1036.64 | 24.94 | 116.87 | 15.48 | 3978.86 | 0.80 | 0.94 | 0.76 |
| lima | postgresql | PASS | COMPLETE | 8.89 | 1025.57 | 124.59 | 2470.35 | 1892.28 | 28.92 | 118.26 | 8.58 | 5668.53 | 0.82 | 0.68 | 0.74 |
| apple-container | sqlite | PASS | COMPLETE | 7.80 | 49.75 | 16.73 | 2435.99 | 1022.65 | 28.20 | 36.56 | 19.27 | 3609.15 | 0.96 | 0.92 | 0.69 |
| apple-container | postgresql | PASS | COMPLETE | 7.96 | 284.11 | 132.67 | 2409.32 | 2087.01 | 55.99 | 62.19 | 8.53 | 5039.82 | 0.80 | 0.75 | 0.65 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 54 / 5 | 60 / 3 | 80 / 0 | 2745 / 1 | 0 / 0 | 0 / 0 | 2939 | 9 | 584.7 |
| docker | pg-colocated | 54 / 5 | 60 / 3 | 80 / 0 | 2748 / 1 | 0 / 0 | 0 / 0 | 2942 | 9 | 240.3 |
| native | postgresql | 54 / 5 | 60 / 3 | 102 / 2 | 2769 / 3 | 22 / 2 | 22 / 2 | 3029 | 17 | 283.0 |
| lima | postgresql | 54 / 5 | 60 / 3 | 80 / 0 | 2748 / 1 | 0 / 0 | 0 / 0 | 2942 | 9 | 248.9 |
| apple-container | postgresql | 54 / 5 | 38 / 1 | 80 / 0 | 2744 / 1 | 0 / 0 | 0 / 0 | 2916 | 7 | 274.9 |

## C17

New in pg62-v1: `cat` a committed 64 MiB non-repeating file (AES-128-CTR keystream, pinned SHA-256). Committed base.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 6.57 | 417.57 | 25.13 | 362.18 | 14.48 | 19.13 | 302.26 | 21.58 | 1162.34 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 6.55 | 553.57 | 131.55 | 1305.37 | 20.71 | 20.19 | 560.46 | 9.34 | 2601.19 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 6.14 | 521.92 | 132.43 | 590.63 | 15.64 | 18.51 | 236.65 | 8.60 | 1524.37 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 7.24 | 42.46 | 36.86 | 276.91 | 81.72 | 36.53 | 61.51 | 12.99 | 548.97 | 0.76 | 5.64 | 0.47 |
| native | postgresql | PASS | COMPLETE | 6.90 | 105.12 | 94.45 | 935.01 | 156.79 | 67.56 | 94.39 | 8.17 | 1461.49 | 0.72 | 7.57 | 0.56 |
| lima | sqlite | PASS | COMPLETE | 11.25 | 740.34 | 20.47 | 349.25 | 15.28 | 19.48 | 116.51 | 19.03 | 1280.35 | 0.96 | 1.05 | 1.10 |
| lima | postgresql | PASS | COMPLETE | 10.68 | 957.04 | 156.41 | 2071.59 | 23.92 | 31.99 | 123.27 | 9.75 | 3373.98 | 1.59 | 1.15 | 1.30 |
| apple-container | sqlite | PASS | COMPLETE | 9.72 | 47.59 | 20.41 | 309.06 | 13.93 | 20.50 | 38.67 | 23.67 | 473.82 | 0.85 | 0.96 | 0.41 |
| apple-container | postgresql | PASS | COMPLETE | 9.40 | 229.31 | 173.57 | 1444.39 | 44.87 | 69.21 | 85.53 | 9.40 | 2056.28 | 1.11 | 2.17 | 0.79 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 32 / 3 | 61 / 3 | 1573 / 0 | 7 / 0 | 0 / 0 | 0 / 0 | 1673 | 6 | 125.8 |
| docker | pg-colocated | 32 / 3 | 61 / 3 | 1573 / 0 | 7 / 0 | 0 / 0 | 0 / 0 | 1673 | 6 | 100.7 |
| native | postgresql | 54 / 5 | 61 / 3 | 1595 / 2 | 29 / 2 | 22 / 2 | 22 / 2 | 1783 | 16 | 137.5 |
| lima | postgresql | 32 / 3 | 61 / 3 | 1621 / 0 | 7 / 0 | 0 / 0 | 0 / 0 | 1721 | 6 | 232.8 |
| apple-container | postgresql | 32 / 3 | 39 / 1 | 1573 / 0 | 7 / 0 | 0 / 0 | 0 / 0 | 1651 | 4 | 125.0 |

## C18

New in pg62-v1: `stat f{1..1000}` in one process over 1,000 committed files. Committed base.

| Machine | Database | Execution | Cleanup | Load 1m | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Close ms | Store release ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 7.16 | 352.00 | 21.89 | 139.54 | 15.17 | 17.83 | 341.45 | 20.12 | 908.00 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 7.37 | 572.53 | 135.24 | 162.00 | 18.94 | 17.85 | 294.02 | 9.17 | 1209.76 | 1.00 | 1.00 | 1.00 |
| docker | pg-colocated | PASS | COMPLETE | 7.45 | 524.01 | 131.01 | 154.25 | 16.45 | 17.80 | 279.36 | 9.08 | 1131.95 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 7.78 | 43.43 | 36.37 | 1766.01 | 78.86 | 32.41 | 75.91 | 10.43 | 2043.42 | 12.66 | 5.20 | 2.25 |
| native | postgresql | PASS | COMPLETE | 8.19 | 115.51 | 117.72 | 1784.04 | 121.56 | 84.70 | 100.07 | 7.70 | 2331.30 | 11.01 | 6.42 | 1.93 |
| lima | sqlite | PASS | COMPLETE | 5.70 | 742.15 | 22.18 | 102.70 | 14.47 | 18.05 | 114.81 | 15.87 | 1030.23 | 0.74 | 0.95 | 1.13 |
| lima | postgresql | PASS | COMPLETE | 6.19 | 952.39 | 148.86 | 145.84 | 23.52 | 19.43 | 114.13 | 9.25 | 1413.43 | 0.90 | 1.24 | 1.17 |
| apple-container | sqlite | PASS | COMPLETE | 5.48 | 59.45 | 19.95 | 111.02 | 12.11 | 15.76 | 38.25 | 16.27 | 272.82 | 0.80 | 0.80 | 0.30 |
| apple-container | postgresql | PASS | COMPLETE | 5.43 | 259.74 | 157.94 | 173.19 | 43.53 | 41.82 | 86.94 | 7.52 | 770.69 | 1.07 | 2.30 | 0.64 |

Server-side counts per phase as statements / connections: `pg_stat_statements` calls for the row's database (reset before each phase), and connections authorized for that database while the phase ran (`log_connections`).

| Machine | Database | Create | Mount | Exec | Commit | Unmount | Cleanup | Statements | Connections | Statement exec ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | postgresql | 32 / 3 | 63 / 3 | 39 / 0 | 7 / 0 | 0 / 0 | 0 / 0 | 141 | 6 | 11.8 |
| docker | pg-colocated | 32 / 3 | 63 / 3 | 39 / 0 | 7 / 0 | 0 / 0 | 0 / 0 | 141 | 6 | 11.6 |
| native | postgresql | 54 / 5 | 89 / 3 | 35 / 2 | 29 / 2 | 22 / 2 | 22 / 2 | 251 | 16 | 34.7 |
| lima | postgresql | 32 / 3 | 63 / 3 | 39 / 0 | 7 / 0 | 0 / 0 | 0 / 0 | 141 | 6 | 19.4 |
| apple-container | postgresql | 32 / 3 | 41 / 1 | 39 / 0 | 7 / 0 | 0 / 0 | 0 / 0 | 119 | 4 | 8.8 |

## Preparation, limits and cleanup

Attempted row preparation: 209.242 s total; maximum 6.299 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **INCOMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. 

Final disposition recorded by campaign owner.



Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

