# fs-file-calls — 54937e6434

**PASS (diagnostic warm): measured all 15 mountless LayerFS 2.0 `file.*` + `commit.diff` calls across CLI and persistent `@layerfs/node` SDK on native SQLite (ext4) and PostgreSQL 18.6 (F1k `file.stat` p50: SQLite SDK `5.104 ms` vs CLI `17.042 ms`, PG18 SDK `15.822 ms`; independent export SHA-256 proofs passed; 3 unavailable worker routes recorded as NOT_RUN).**

## Configuration & Provenance

| Field | Value |
| --- | --- |
| LayerFS commit | `54937e64348dc8c2c801fc6d98db28b995a48ac8` (`layerfs_v2_0_0`) |
| CLI binary SHA-256 | `3c6da5664ed9e37c…` |
| Host | Linux 7.0.0-43-generic (x86_64) (`ext4` `LAYERFS_TEST_TMPDIR`) |
| PostgreSQL | 18.6 (`127.0.0.1:55432`, `synchronous_commit=off`) |
| Sample sizes | reads `N=15` (F10k/H50 capped), writes `N=10`, history `H1` / `H50` |
| Cache protocol | warm (declared preconditioning; OS page cache not dropped — labelled diagnostic) |
| Independent proof | SQLite F100 export SHA-256 match: `True`; PG18 F100 export SHA-256 match: `True` |

## Latency & Throughput by Call (p50 / p95 ms, warm diagnostic)

| Case | SQLite SDK p50 (ms) | SQLite CLI p50 (ms) | PG18 SDK p50 (ms) | PG18 CLI p50 (ms) | SQLite SDK calls/s |
| --- | ---: | ---: | ---: | ---: | ---: |
| `file.read (1k)` | 1.07 / 1.33 | 12.36 / 12.93 | 4.34 / 5.84 | 50.99 / 52.51 | 898.29 |
| `file.read (64k)` | 3.94 / 4.30 | 17.11 / 17.97 | 9.01 / 12.60 | 56.67 / 58.20 | 259.21 |
| `file.read (1m)` | 3.99 / 4.42 | 16.89 / 17.77 | 7.96 / 9.44 | 58.36 / 63.08 | 251.04 |
| `file.read (16m_win2000)` | 4.19 / 4.86 | 17.25 / 18.84 | 7.70 / 8.45 | 57.91 / 59.50 | 232 |
| `file.stat (F100)` | 3.83 / 4.72 | 16.04 / 16.97 | 11.02 / 12.75 | 63.24 / 67.27 | 250.87 |
| `file.list first-page (F100)` | 1.10 / 1.37 | 12.33 / 12.66 | 2.70 / 3.08 | 51.13 / 53.92 | 876.63 |
| `file.glob (F100)` | 3.20 / 3.64 | 20.23 / 22.55 | 8.57 / 10.69 | 119.98 / 129.50 | 303.4 |
| `file.grep rare (F100)` | 4.51 / 5.10 | 21.66 / 22.53 | 10.77 / 11.81 | 125.36 / 133.37 | 219.11 |
| `file.grep frequent (F100)` | 3.67 / 4.03 | 19.07 / 20.17 | 9.74 / 11.69 | 99.92 / 110.45 | 268.97 |
| `file.stat (F1k)` | 5.10 / 5.78 | 17.04 / 17.61 | 15.82 / 19.33 | 72.84 / 91.25 | 191.52 |
| `file.list first-page (F1k)` | 1.35 / 1.60 | 12.76 / 13.35 | 3.17 / 3.62 | 55.51 / 63.47 | 717.77 |
| `file.glob (F1k)` | 5.34 / 5.88 | 22.32 / 23.11 | 11.94 / 13.14 | 159.70 / 185.31 | 183.54 |
| `file.grep rare (F1k)` | 38.33 / 39.40 | 89.08 / 120.11 | 59.25 / 64.18 | 627.74 / 747.29 | 26.1 |
| `file.grep frequent (F1k)` | 3.74 / 4.42 | 18.61 / 20.73 | 7.52 / 9.15 | 99.27 / 110.45 | 255.96 |
| `file.stat (F10k)` | 6.09 / 6.80 | 18.35 / 18.39 | 24.30 / 28.57 | 87.00 / 87.65 | 161.81 |
| `file.list first-page (F10k)` | 1.29 / 1.53 | 13.09 / 13.26 | 5.34 / 6.26 | 56.99 / 58.04 | 755.59 |
| `file.glob (F10k)` | 3.06 / 3.58 | 15.78 / 16.29 | 9.29 / 10.64 | 72.44 / 77.15 | 317.12 |
| `file.grep rare (F10k)` | 461.71 / 469.10 | 650.66 / 660.77 | 1188.65 / 1251.03 | 1306.29 / 1327.20 | 2.16 |
| `file.grep frequent (F10k)` | 3.93 / 4.32 | 15.92 / 16.37 | 10.30 / 13.66 | 73.50 / 78.87 | 251.77 |
| `file.blame (H1, head)` | 2.01 / 2.44 | 13.45 / 13.80 | 6.34 / 7.87 | 61.12 / 67.39 | 482.88 |
| `file.history (H1, head)` | 3.07 / 3.91 | 14.71 / 15.12 | 10.18 / 10.99 | 64.63 / 73.35 | 310.45 |
| `file.history (H1, pinned)` | 3.08 / 3.50 | 14.64 / 15.07 | 10.40 / 11.93 | 66.62 / 74.01 | 313.95 |
| `commit.diff (H1, head)` | 1.52 / 2.00 | 13.04 / 13.40 | 4.65 / 5.97 | 59.27 / 66.34 | 630.59 |
| `file.blame (H100, head)` | 45.06 / 46.77 | 65.76 / 68.31 | 146.84 / 160.27 | 282.00 / 298.94 | 22.13 |
| `file.history (H100, head)` | 79.99 / 80.77 | 116.58 / 148.84 | 276.13 / 286.28 | 438.78 / 504.74 | 12.62 |
| `file.history (H100, pinned)` | 79.66 / 83.41 | 108.13 / 125.81 | 283.64 / 295.50 | 417.10 / 429.23 | 12.48 |
| `commit.diff (H100, head)` | 1.36 / 2.00 | 12.75 / 13.46 | 4.57 / 5.28 | 61.78 / 71.15 | 671.82 |
| `file.write (0b)` | 7.53 / 8.08 | 32.48 / 36.08 | 16.74 / 21.07 | 126.80 / 159.22 | 133.41 |
| `file.write (1k)` | 7.44 / 7.83 | 25.54 / 36.55 | 16.95 / 18.76 | 120.45 / 124.74 | 136.44 |
| `file.write (64k)` | 8.23 / 8.56 | 27.68 / 28.44 | 18.95 / 20.36 | 128.03 / 132.56 | 122.12 |
| `file.write (1m)` | 15.60 / 19.52 | 31.53 / 36.40 | 29.10 / 33.71 | 131.36 / 136.42 | 60.45 |
| `file.edit (small)` | 7.16 / 8.09 | 33.12 / 34.92 | 17.54 / 18.74 | 133.18 / 172.48 | 137.24 |
| `file.apply (batch=1)` | 7.83 / 8.29 | — | 18.30 / 19.07 | — | 129.25 |
| `file.apply (batch=10)` | 11.17 / 11.73 | — | 25.70 / 27.25 | — | 89.7 |
| `file.apply (batch=100)` | 38.20 / 46.66 | — | 54.88 / 63.49 | — | 24.63 |
| `file.mkdir` | 9.99 / 11.06 | 25.61 / 26.66 | 21.59 / 22.88 | 123.90 / 140.19 | 99.12 |
| `file.cp (file)` | 10.58 / 11.78 | 27.62 / 28.93 | 23.42 / 25.34 | 127.70 / 135.80 | 93.89 |
| `file.mv (file)` | 9.17 / 10.26 | 26.35 / 27.87 | 21.82 / 23.20 | 122.21 / 128.28 | 107.82 |
| `file.rm (file)` | 10.35 / 11.46 | 26.41 / 26.77 | 21.20 / 24.73 | 127.06 / 141.47 | 95.94 |

## Write Commit Storage Growth (SQLite SDK & PG18 SDK)

| Write Case | SQLite `delta_stored_bytes` | SQLite `delta_size_bytes` | PG18 `delta_stored_bytes` | PG18 `delta_size_bytes` |
| --- | ---: | ---: | ---: | ---: |
| `file.write (0b)` | 2842 | 4096 | 2841 | 8192 |
| `file.write (1k)` | 2947 | 16384 | 2944 | 16384 |
| `file.write (64k)` | 2955 | 16384 | 2956 | 16384 |
| `file.write (1m)` | 2554 | 0 | 2564 | 8192 |

## Concurrency & Refusals (CLI Process-per-Call)

| Backend | Workload | OK / Total | Throughput (calls/s) | Refusals by Code |
| --- | --- | ---: | ---: | --- |
| SQLite | CLI readers x1 | 8 / 8 | 56.03 | `none` |
| SQLite | CLI readers x4 | 32 / 32 | 174.12 | `none` |
| SQLite | CLI readers x8 | 64 / 64 | 199.71 | `none` |
| SQLite | CLI writers x4 (separate branches) | 16 / 16 | 95.01 | `none` |
| SQLite | CLI writers x4 (same branch) | 16 / 16 | 95.88 | `none` |
| PostgreSQL 18 | CLI readers x1 | 8 / 8 | 14.26 | `none` |
| PostgreSQL 18 | CLI readers x4 | 32 / 32 | 43.36 | `none` |
| PostgreSQL 18 | CLI readers x8 | 64 / 64 | 55.46 | `none` |
| PostgreSQL 18 | CLI writers x4 (separate branches) | 16 / 16 | 19.94 | `none` |
| PostgreSQL 18 | CLI writers x4 (same branch) | 16 / 16 | 16.31 | `none` |

## Registered NOT_RUN Routes

| Route | Status & Reason |
| --- | --- |
| `worker:docker` | NOT_RUN: Docker daemon unavailable on this non-root Linux host |
| `worker:lima` | NOT_RUN: Lima VM unavailable on this Linux host |
| `worker:apple-container` | NOT_RUN: macOS-only route |

## Main Observations & Cleanup

- **CLI vs persistent SDK**: On native SQLite (`F1k` `file.stat`), a fresh CLI process adds fixed process-spawn + home/Store open overhead (`17.042 ms` p50) compared to the persistent `@layerfs/node` client (`5.104 ms` p50).
- **PostgreSQL 18 vs SQLite**: Persistent `@layerfs/node` calls against local PostgreSQL 18.6 (`15.822 ms` p50 on `F1k` `file.stat`) incur loopback TCP + SQL round-trip overhead compared to local SQLite (`5.104 ms`), while supporting concurrent CLI writers cleanly.
- **Cleanup**: Owned SQLite store removed via `layerfs store remove`, PostgreSQL store disconnected via `layerfs store disconnect`, scratch database dropped, and temporary home/fixtures deleted.
