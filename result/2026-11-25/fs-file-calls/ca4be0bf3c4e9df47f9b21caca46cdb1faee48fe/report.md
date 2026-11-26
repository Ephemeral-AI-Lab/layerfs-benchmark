# fs-file-calls — ca4be0bf3c

**PARTIAL (diagnostic warm): measured the mountless LayerFS 2.0 `file.*` + `commit.diff` calls across CLI and persistent `@layerfs/node` SDK on native SQLite (ext4) and PostgreSQL 18.7 (Debian 18.7-1.pgdg13+5) (file.stat (F1k) p50: SQLite SDK `2.085 ms`, SQLite CLI `8.473 ms`, PG SDK `24.722 ms`, PG CLI `56.207 ms`); rows by status: FAIL 2, NOT_RUN 10, OK 235, REFUSED 8; 160 cold rows registered as INELIGIBLE (no cold claim); fixture and export proofs passed; 3 unavailable routes recorded as NOT_RUN.**

## Configuration & Provenance

| Field | Value |
| --- | --- |
| LayerFS commit | `ca4be0bf3c4e9df47f9b21caca46cdb1faee48fe` |
| CLI binary SHA-256 | `9f1d1e2abd9596624a77567a6ed417f3360c74b70661dac3c8e4e893a80dfc25` |
| Node addon SHA-256 | `d1ec12ae0c15f81a66ebebc07a728cb4001ca8a8fe00773527f126d03126dfec` |
| Host | 13th Gen Intel(R) Core(TM) i9-13900HX, 32 CPUs, 7.8 GiB RAM, kernel 6.6.87.2-microsoft-standard-WSL2 |
| Machine route | `native` (`LAYERFS_TEST_TMPDIR` on ext4); Node SDK arm is a persistent-client exception to "public CLI for every operation" |
| PostgreSQL | 18.7 (Debian 18.7-1.pgdg13+5), pg_stat_statements: True, store `synchronous_commit=off`; settings `{"effective_cache_size": "524288", "fsync": "on", "full_page_writes": "on", "max_connections": "200", "shared_buffers": "16384", "shared_preload_libraries": "pg_stat_statements", "synchronous_commit": "off", "wal_level": "replica"}` |
| Sample sizes | reads `N=15` (F10k/F100k/deeper history capped), writes `N=10`, trees F100, F1k, F10k, F100k, history H1, H50, H100, H1000 |
| Per-call cap | 120 s; a call over it is a FAIL row and the run continues |
| Disk free (GB) | start 851.5, end 851.0 (stop below 25) |
| Cache protocol | warm (declared preconditioning; OS page cache not dropped — labelled diagnostic) |
| Local receipts | `results.json` / `results.csv` under `--output`, not committed (AGENTS.md:64-65) |

## Fixtures (manifest = sha256 over sorted path, size, content sha256)

| Fixture | Files | Bytes | Manifest SHA-256 | Unchanged after write rows |
| --- | ---: | ---: | --- | --- |
| F100 | 100 | 4894 | `e091298ea2f83ce4…` | sqlite: True, pg: True |
| F1k | 1000 | 49894 | `aafb8b20c3ebaca0…` | sqlite: True, pg: True |
| F10k | 10000 | 508894 | `3fafd345351ec254…` | sqlite: True, pg: True |
| F100k | 100000 | 5188894 | `609329791afefb7c…` | sqlite: True |
| sizes | 5 | 17892352 | `a9738398f610334d…` | sqlite: True, pg: True |
| hist | 1 | 11 | `16239d6e3d6c3a70…` | sqlite: True, pg: True |

## Latency by Call (p50 / p95 ms, warm diagnostic)

| Case | SQLite SDK p50 / p95 | SQLite CLI p50 / p95 | PG SDK p50 / p95 | PG CLI p50 / p95 |
| --- | ---: | ---: | ---: | ---: |
| `file.read (1k)` | 0.49 / 0.66 (n=15) | 6.29 / 6.55 (n=15) | 7.66 / 9.70 (n=15) | 33.96 / 35.58 (n=15) |
| `file.read (64k)` | 1.33 / 1.56 (n=15) | 7.47 / 7.93 (n=15) | 8.04 / 10.78 (n=15) | 35.18 / 36.40 (n=15) |
| `file.read (1m)` | 1.39 / 1.60 (n=15) | 7.66 / 8.30 (n=15) | 11.84 / 13.59 (n=15) | 37.90 / 40.40 (n=15) |
| `file.read (16m_win2000)` | 1.53 / 1.66 (n=15) | 7.82 / 9.22 (n=15) | 10.88 / 13.19 (n=15) | 39.38 / 48.84 (n=15) |
| `file.stat (F100)` | 1.73 / 1.90 (n=15) | 7.63 / 8.24 (n=15) | 20.72 / 23.59 (n=15) | 50.93 / 51.80 (n=15) |
| `file.list first-page (F100)` | 0.51 / 0.56 (n=15) | 6.17 / 6.55 (n=15) | 7.93 / 10.86 (n=15) | 32.34 / 37.24 (n=15) |
| `file.glob (F100)` | 1.69 / 1.82 (n=15) | 9.19 / 9.75 (n=15) | 10.03 / 11.91 (n=15) | 140.22 / 145.69 (n=15) |
| `file.grep rare (F100)` | 2.28 / 2.43 (n=15) | 10.68 / 12.10 (n=15) | 11.23 / 12.38 (n=15) | 147.97 / 169.61 (n=15) |
| `file.grep frequent (F100)` | 1.84 / 1.98 (n=15) | 9.61 / 9.98 (n=15) | 10.67 / 12.07 (n=15) | 105.06 / 109.70 (n=15) |
| `file.stat (F1k)` | 2.08 / 2.25 (n=15) | 8.47 / 9.18 (n=15) | 24.72 / 32.21 (n=15) | 56.21 / 58.68 (n=15) |
| `file.list first-page (F1k)` | 0.58 / 0.69 (n=15) | 6.33 / 6.79 (n=15) | 6.84 / 7.77 (n=15) | 36.80 / 42.74 (n=15) |
| `file.glob (F1k)` | 2.48 / 4.16 (n=15) | 10.00 / 11.26 (n=15) | 14.60 / 16.00 (n=15) | 158.99 / 169.91 (n=15) |
| `file.grep rare (F1k)` | 20.65 / 21.28 (n=15) | 36.77 / 38.50 (n=15) | 62.28 / 70.41 (n=15) | 664.72 / 703.00 (n=15) |
| `file.grep frequent (F1k)` | 1.77 / 1.91 (n=15) | 8.54 / 9.13 (n=15) | 11.70 / 14.39 (n=15) | 76.20 / 80.96 (n=15) |
| `file.stat (F10k)` | 2.83 / 3.16 (n=10) | 8.55 / 9.05 (n=5) | 31.14 / 34.07 (n=10) | 62.15 / 63.85 (n=5) |
| `file.list first-page (F10k)` | 0.76 / 0.86 (n=10) | 6.16 / 6.54 (n=5) | 7.61 / 9.87 (n=10) | 34.94 / 35.39 (n=5) |
| `file.glob (F10k)` | 1.51 / 1.63 (n=10) | 7.27 / 7.68 (n=5) | 13.44 / 14.28 (n=10) | 59.41 / 61.32 (n=5) |
| `file.grep rare (F10k)` | 239.95 / 271.11 (n=10) | 242.52 / 277.13 (n=5) | 998.52 / 1181.15 (n=10) | 1032.77 / 1039.60 (n=5) |
| `file.grep frequent (F10k)` | 1.72 / 2.04 (n=10) | 8.60 / 8.82 (n=5) | 11.28 / 13.28 (n=10) | 46.26 / 56.17 (n=5) |
| `file.stat (F100k)` | 2.69 / 2.82 (n=10) | 9.63 / 9.91 (n=5) | NOT_RUN | NOT_RUN |
| `file.list first-page (F100k)` | 0.65 / 0.70 (n=10) | 6.56 / 6.84 (n=5) | NOT_RUN | NOT_RUN |
| `file.glob (F100k)` | 1.39 / 1.47 (n=10) | 7.27 / 7.61 (n=5) | NOT_RUN | NOT_RUN |
| `file.grep rare (F100k)` | 3109.47 / 3242.52 (n=10) | 3023.84 / 3050.58 (n=5) | NOT_RUN | NOT_RUN |
| `file.grep frequent (F100k)` | 1.62 / 1.79 (n=10) | 7.91 / 9.03 (n=5) | NOT_RUN | NOT_RUN |
| `file.blame (H1, head)` | 0.86 / 1.05 (n=15) | 6.65 / 7.06 (n=15) | 11.76 / 13.62 (n=15) | 46.60 / 53.79 (n=15) |
| `file.history (H1, head)` | 1.29 / 1.52 (n=15) | 7.16 / 7.46 (n=15) | 18.89 / 26.50 (n=15) | 53.66 / 56.09 (n=15) |
| `file.history (H1, pinned)` | 1.31 / 1.50 (n=15) | 7.27 / 7.80 (n=15) | 19.07 / 22.69 (n=15) | 56.26 / 59.02 (n=15) |
| `commit.diff (H1, head)` | 0.67 / 0.89 (n=15) | 6.63 / 7.14 (n=15) | 9.00 / 10.10 (n=15) | 41.48 / 43.70 (n=15) |
| `file.blame (H50, head)` | 20.07 / 21.15 (n=10) | 27.89 / 28.25 (n=5) | 256.05 / 328.46 (n=10) | 373.36 / 383.50 (n=5) |
| `file.history (H50, head)` | 37.95 / 39.29 (n=10) | 44.53 / 45.17 (n=5) | 501.44 / 583.67 (n=10) | 704.75 / 735.70 (n=5) |
| `file.history (H50, pinned)` | 35.92 / 36.94 (n=10) | 43.28 / 44.51 (n=5) | 535.65 / 603.34 (n=10) | 658.50 / 705.63 (n=5) |
| `commit.diff (H50, head)` | 0.69 / 1.01 (n=10) | 6.46 / 6.61 (n=5) | 9.85 / 11.23 (n=10) | 45.87 / 47.06 (n=5) |
| `file.blame (H100, head)` | 39.61 / 92.46 (n=10) | 56.67 / 61.25 (n=5) | 507.80 / 557.38 (n=10) | 748.54 / 792.40 (n=5) |
| `file.history (H100, head)` | 35.12 / 36.60 (n=10) | 44.58 / 46.22 (n=5) | 496.00 / 563.76 (n=10) | 639.84 / 657.51 (n=5) |
| `file.history (H100, pinned)` | 35.06 / 36.10 (n=10) | 43.36 / 47.22 (n=5) | 483.70 / 501.14 (n=10) | 647.58 / 651.90 (n=5) |
| `commit.diff (H100, head)` | 0.68 / 1.14 (n=10) | 6.65 / 7.12 (n=5) | 13.33 / 15.29 (n=10) | 43.35 / 44.34 (n=5) |
| `file.blame (H1000, head)` | 395.60 / 444.67 (n=10) | 412.32 / 447.07 (n=5) | 4967.26 / 5073.01 (n=10) | 6859.14 / 7437.67 (n=5) |
| `file.history (H1000, head)` | 35.56 / 36.88 (n=10) | 43.17 / 44.87 (n=5) | 495.62 / 548.64 (n=10) | 691.07 / 783.57 (n=5) |
| `file.history (H1000, pinned)` | 37.59 / 42.13 (n=10) | 42.99 / 43.73 (n=5) | 514.81 / 549.47 (n=10) | 674.22 / 714.46 (n=5) |
| `commit.diff (H1000, head)` | 0.74 / 0.92 (n=10) | 6.31 / 6.88 (n=5) | 10.39 / 11.46 (n=10) | 43.77 / 44.79 (n=5) |
| `file.write (0b)` | 19.09 / 21.52 (n=10) | 48.01 / 82.74 (n=10) | 13.49 / 17.85 (n=10) | 94.39 / 109.45 (n=10) |
| `file.write (1k)` | 19.51 / 27.20 (n=10) | 45.95 / 56.59 (n=10) | 12.64 / 15.03 (n=10) | 74.11 / 78.09 (n=10) |
| `file.write (64k)` | 21.14 / 22.25 (n=10) | 48.04 / 51.69 (n=10) | 14.15 / 14.96 (n=10) | 75.63 / 99.36 (n=10) |
| `file.write (1m)` | 20.78 / 35.11 (n=5) | 48.23 / 48.98 (n=3) | 20.46 / 25.28 (n=5) | 96.83 / 101.38 (n=3) |
| `file.write (64m)` | 342.85 / 520.68 (n=3) | 191.84 / 329.12 (n=3) | 390.82 / 589.32 (n=3) | 237.23 / 456.21 (n=3) |
| `file.edit (small)` | 20.63 / 21.55 (n=10) | 47.88 / 58.02 (n=10) | 13.45 / 15.37 (n=10) | 86.67 / 93.10 (n=10) |
| `file.mkdir` | 22.80 / 23.58 (n=10) | 43.90 / 49.07 (n=10) | 20.53 / 22.83 (n=10) | 77.42 / 82.78 (n=10) |
| `file.cp (file)` | 21.46 / 23.05 (n=10) | 47.80 / 48.99 (n=10) | 19.59 / 22.32 (n=10) | 91.14 / 108.71 (n=10) |
| `file.mv (file)` | 21.59 / 25.00 (n=10) | 45.79 / 47.36 (n=10) | 13.97 / 15.59 (n=10) | 100.45 / 114.58 (n=10) |
| `file.rm (file)` | 22.22 / 23.18 (n=10) | 45.24 / 48.92 (n=10) | 23.70 / 26.97 (n=10) | 96.69 / 113.09 (n=10) |
| `file.apply (batch=1)` | 20.66 / 23.45 (n=10) | — | 13.77 / 15.58 (n=10) | — |
| `file.apply (batch=10)` | 22.82 / 24.79 (n=10) | — | 23.38 / 24.21 (n=10) | — |
| `file.apply (batch=100)` | 40.40 / 40.94 (n=5) | — | 39.89 / 48.69 (n=5) | — |

## Resources and native dispatch (CLI: per-call rusage; SDK: process deltas per call)

| Case | CLI CPU ms p50 | CLI max RSS MiB | CLI dispatch ms p50 | SDK CPU ms/call | SDK RSS delta MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| `file.read (1k)` | 5.956 | 225.0 | 0.029 | 0.532 | 0.0 |
| `file.read (64k)` | 7.245 | 225.0 | 0.029 | 1.418 | 2.8 |
| `file.read (1m)` | 7.274 | 225.0 | 0.028 | 1.416 | 2.0 |
| `file.read (16m_win2000)` | 7.54 | 225.0 | 0.032 | 1.528 | -1.2 |
| `file.stat (F100)` | 7.398 | 225.0 | 0.029 | 1.742 | 0.0 |
| `file.list first-page (F100)` | 5.873 | 225.0 | 0.026 | 0.5 | 0.0 |
| `file.glob (F100)` | 8.946 | 225.0 | 0.031 | 1.674 | 0.2 |
| `file.grep rare (F100)` | 10.335 | 225.0 | 0.031 | 2.303 | 0.0 |
| `file.grep frequent (F100)` | 9.415 | 225.0 | 0.035 | 1.87 | 0.5 |
| `file.stat (F1k)` | 8.206 | 225.0 | 0.031 | 2.092 | 0.2 |
| `file.list first-page (F1k)` | 6.168 | 225.0 | 0.029 | 0.587 | 0.0 |
| `file.glob (F1k)` | 9.598 | 225.0 | 0.029 | 2.509 | 0.8 |
| `file.grep rare (F1k)` | 36.336 | 225.0 | 0.032 | 20.726 | 2.0 |
| `file.grep frequent (F1k)` | 8.317 | 225.0 | 0.031 | 1.769 | 0.0 |
| `file.stat (F10k)` | 8.387 | 225.0 | 0.025 | 2.858 | 0.0 |
| `file.list first-page (F10k)` | 5.886 | 225.0 | 0.029 | 0.759 | 0.0 |
| `file.glob (F10k)` | 7.08 | 225.0 | 0.026 | 1.486 | 0.0 |
| `file.grep rare (F10k)` | 242.13 | 225.0 | 0.035 | 246.293 | 11.2 |
| `file.grep frequent (F10k)` | 8.287 | 225.0 | 0.037 | 1.745 | 0.0 |
| `file.stat (F100k)` | 8.949 | 225.0 | 0.03 | 2.662 | 0.0 |
| `file.list first-page (F100k)` | 6.251 | 225.0 | 0.028 | 0.632 | 0.0 |
| `file.glob (F100k)` | 6.944 | 225.0 | 0.028 | 1.373 | 0.0 |
| `file.grep rare (F100k)` | 3023.522 | 225.0 | 0.035 | 3121.252 | 4.9 |
| `file.grep frequent (F100k)` | 7.748 | 225.0 | 0.03 | 1.626 | -0.6 |
| `file.blame (H1, head)` | 6.477 | 225.0 | 0.028 | 0.886 | 0.0 |
| `file.history (H1, head)` | 7.004 | 225.0 | 0.028 | 1.315 | 0.0 |
| `file.history (H1, pinned)` | 7.047 | 225.0 | 0.031 | 1.334 | 0.0 |
| `commit.diff (H1, head)` | 6.357 | 225.0 | 0.032 | 0.661 | 0.0 |
| `file.blame (H50, head)` | 27.598 | 225.0 | 0.034 | 20.272 | 0.0 |
| `file.history (H50, head)` | 44.211 | 225.0 | 0.031 | 37.595 | 0.0 |
| `file.history (H50, pinned)` | 43.092 | 225.0 | 0.032 | 35.86 | 0.0 |
| `commit.diff (H50, head)` | 6.341 | 225.0 | 0.028 | 0.721 | 0.0 |
| `file.blame (H100, head)` | 55.022 | 225.0 | 0.035 | 49.182 | 0.0 |
| `file.history (H100, head)` | 44.354 | 225.0 | 0.032 | 35.266 | 0.0 |
| `file.history (H100, pinned)` | 43.138 | 225.0 | 0.035 | 35.053 | 0.0 |
| `commit.diff (H100, head)` | 6.386 | 225.0 | 0.031 | 0.745 | 0.0 |
| `file.blame (H1000, head)` | 410.547 | 225.0 | 0.033 | 401.863 | 0.0 |
| `file.history (H1000, head)` | 42.678 | 225.0 | 0.031 | 35.561 | 0.0 |
| `file.history (H1000, pinned)` | 42.728 | 225.0 | 0.03 | 38.016 | 0.0 |
| `commit.diff (H1000, head)` | 5.622 | 225.0 | 0.031 | 0.748 | 0.0 |
| `file.write (0b)` | 16.214 | 243.4 | 0.049 | 4.17 | 1.2 |
| `file.write (1k)` | 12.881 | 243.4 | 0.052 | 4.122 | 0.2 |
| `file.write (64k)` | 14.88 | 243.4 | 0.079 | 4.991 | 0.5 |
| `file.write (1m)` | 15.79 | 243.4 | 0.353 | 9.26 | 1.0 |
| `file.write (64m)` | 154.166 | 371.4 | 20.881 | 420.082 | 46.9 |
| `file.edit (small)` | 16.965 | 371.4 | 0.053 | 4.039 | 0.0 |
| `file.mkdir` | 13.06 | 371.4 | 0.052 | 5.853 | 0.0 |
| `file.cp (file)` | 14.124 | 371.4 | 0.051 | 5.908 | 0.0 |
| `file.mv (file)` | 13.066 | 371.4 | 0.052 | 5.441 | -65.0 |
| `file.rm (file)` | 13.368 | 371.4 | 0.049 | 5.66 | 0.0 |
| `file.apply (batch=1)` | — | — | UNAVAILABLE | 4.208 | 0.0 |
| `file.apply (batch=10)` | — | — | UNAVAILABLE | 5.758 | 0.0 |
| `file.apply (batch=100)` | — | — | UNAVAILABLE | 21.651 | 0.0 |

Step attribution: native rows carry the `dispatch` step only; `route`, `connect`, `request` are UNAVAILABLE on native. Source: control/crates/layerfs-home/src/trace.rs:24-37 (steps are written only when LAYERFS_TRACE and LAYERFS_TRACE_STEP are both set; the native route writes `step: dispatch` events only, observed in T1).
The step table for worker rows needs the worker route (T6).

## Write Commit Storage Growth

| Write Case | SQLite SDK `delta_stored_bytes` / `delta_size_bytes` | SQLite CLI `delta_stored_bytes` / `delta_size_bytes` | PG SDK `delta_stored_bytes` / `delta_size_bytes` | PG CLI `delta_stored_bytes` / `delta_size_bytes` |
| --- | --- | --- | --- | --- |
| `file.write (0b)` | 2848 / 20480 | 3234 / 12288 | 2842 / 16384 | 3231 / 8192 |
| `file.write (1k)` | 2944 / 4096 | 3903 / 20480 | 2944 / 8192 | 3894 / 24576 |
| `file.write (64k)` | 2956 / 4096 | 3966 / 24576 | 2956 / 24576 | 3960 / 8192 |
| `file.write (1m)` | 2555 / 8192 | 2338 / 4096 | 2555 / 16384 | 2338 / 24576 |
| `file.write (64m)` | 1529 / 8192 | 2670 / 4096 | 1534 / 16384 | 2667 / 40960 |

## Limits (one row per probe; cites the source that sets the limit)

| Probe | Arm | Status | Code | ms | Detail | Source |
| --- | --- | --- | --- | ---: | --- | --- |
| `limit: file.write content 16 MiB` | sqlite_cli | OK |  | 162.62 | `{"content_bytes": 16777217}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 64 MiB` | sqlite_cli | OK |  | 423.271 | `{"content_bytes": 67108865}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 256 MiB` | sqlite_cli | OK |  | 2235.711 | `{"content_bytes": 268435457}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.apply 1000 rows` | sqlite_cli | OK |  | 168.844 | `{"rows": 1000}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8191 rows` | sqlite_cli | OK |  | 968.926 | `{"rows": 8191}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8192 rows` | sqlite_cli | OK |  | 959.673 | `{"rows": 8192}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: commit.diff page limit 1000` | sqlite_cli | OK |  | 333.733 | `{"changed_paths": 8192, "page_limit": 1000, "items": 220, "has_next": true}`  | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: commit.diff page limit 1001` | sqlite_cli | REFUSED | InvalidInput | — | `{}` commit diff: commit.diff: `limit` is 1 to 1000 | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: file.read window 2000 lines` | sqlite_cli | OK |  | 8.268 | `{"lines_asked": 2000, "reply_bytes": 48388, "text_bytes": 47616, "has_next_line": true}`  | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |
| `limit: file.read window 2001 lines` | sqlite_cli | REFUSED | InvalidInput | — | `{}` file read: file.read: `limit` is 1 to 2000 | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |
| `limit: file.write content 16 MiB` | sqlite_sdk | OK |  | 131.179 | `{"content_bytes": 16777217}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 64 MiB` | sqlite_sdk | OK |  | 471.79 | `{"content_bytes": 67108865}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 256 MiB` | sqlite_sdk | OK |  | 2707.144 | `{"content_bytes": 268435457}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.apply 1000 rows` | sqlite_sdk | OK |  | 125.649 | `{"rows": 1000}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8191 rows` | sqlite_sdk | OK |  | 855.825 | `{"rows": 8191}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8192 rows` | sqlite_sdk | OK |  | 987.098 | `{"rows": 8192}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: commit.diff page limit 1000` | sqlite_sdk | OK |  | 331.123 | `{"changed_paths": 8192, "page_limit": 1000, "items": 220, "has_next": true}`  | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: commit.diff page limit 1001` | sqlite_sdk | REFUSED | InvalidInput | — | `{}` commit.diff: `limit` is 1 to 1000 | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: file.read window 2000 lines` | sqlite_sdk | OK |  | 2.246 | `{"lines_asked": 2000, "reply_bytes": 48387, "text_bytes": 47616, "has_next_line": true}`  | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |
| `limit: file.read window 2001 lines` | sqlite_sdk | REFUSED | InvalidInput | — | `{}` file.read: `limit` is 1 to 2000 | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |
| `limit: file.write content 16 MiB` | pg_cli | OK |  | 273.132 | `{"content_bytes": 16777217}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 64 MiB` | pg_cli | OK |  | 502.085 | `{"content_bytes": 67108865}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 256 MiB` | pg_cli | OK |  | 2374.212 | `{"content_bytes": 268435457}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.apply 1000 rows` | pg_cli | OK |  | 330.151 | `{"rows": 1000}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8191 rows` | pg_cli | OK |  | 4267.116 | `{"rows": 8191}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8192 rows` | pg_cli | OK |  | 991.069 | `{"rows": 8192}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: commit.diff page limit 1000` | pg_cli | OK |  | 7228.166 | `{"changed_paths": 8192, "page_limit": 1000, "items": 220, "has_next": true}`  | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: commit.diff page limit 1001` | pg_cli | REFUSED | InvalidInput | — | `{}` commit diff: commit.diff: `limit` is 1 to 1000 | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: file.read window 2000 lines` | pg_cli | OK |  | 39.142 | `{"lines_asked": 2000, "reply_bytes": 48388, "text_bytes": 47616, "has_next_line": true}`  | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |
| `limit: file.read window 2001 lines` | pg_cli | REFUSED | InvalidInput | — | `{}` file read: file.read: `limit` is 1 to 2000 | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |
| `limit: file.write content 16 MiB` | pg_sdk | OK |  | 130.258 | `{"content_bytes": 16777217}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 64 MiB` | pg_sdk | OK |  | 455.136 | `{"content_bytes": 67108865}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 256 MiB` | pg_sdk | OK |  | 2917.001 | `{"content_bytes": 268435457}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.apply 1000 rows` | pg_sdk | OK |  | 142.635 | `{"rows": 1000}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8191 rows` | pg_sdk | OK |  | 900.783 | `{"rows": 8191}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8192 rows` | pg_sdk | OK |  | 925.709 | `{"rows": 8192}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: commit.diff page limit 1000` | pg_sdk | OK |  | 7711.312 | `{"changed_paths": 8192, "page_limit": 1000, "items": 220, "has_next": true}`  | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: commit.diff page limit 1001` | pg_sdk | REFUSED | InvalidInput | — | `{}` commit.diff: `limit` is 1 to 1000 | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: file.read window 2000 lines` | pg_sdk | OK |  | 10.394 | `{"lines_asked": 2000, "reply_bytes": 48387, "text_bytes": 47616, "has_next_line": true}`  | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |
| `limit: file.read window 2001 lines` | pg_sdk | REFUSED | InvalidInput | — | `{}` file.read: `limit` is 1 to 2000 | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |

## Cold rows

Cold rows are registered per read case and gated by `shared/src/measure.py:181 assess_cache`; none is measured, none is labelled cold (`shared/AGENTS.md:7`).

| Arm | Cold rows | Status | Required domains | Reason |
| --- | ---: | --- | --- | --- |
| sqlite_cli | 40 | INELIGIBLE | layerfs-daemon-worker, filesystem-metadata, host-page-cache | No implemented, demonstrated owned cold-cache enforcement and residency protocol for this route/phase. Fresh CLI process/mount, distinct database and copied fixture do not prove coldness. |
| sqlite_sdk | 40 | INELIGIBLE | layerfs-daemon-worker, filesystem-metadata, host-page-cache | No implemented, demonstrated owned cold-cache enforcement and residency protocol for this route/phase. Fresh CLI process/mount, distinct database and copied fixture do not prove coldness. |
| pg_cli | 40 | INELIGIBLE | layerfs-daemon-worker, filesystem-metadata, host-page-cache, postgresql-shared-buffers, postgresql-server-page-cache | No implemented, demonstrated owned cold-cache enforcement and residency protocol for this route/phase. Fresh CLI process/mount, distinct database and copied fixture do not prove coldness. |
| pg_sdk | 40 | INELIGIBLE | layerfs-daemon-worker, filesystem-metadata, host-page-cache, postgresql-shared-buffers, postgresql-server-page-cache | No implemented, demonstrated owned cold-cache enforcement and residency protocol for this route/phase. Fresh CLI process/mount, distinct database and copied fixture do not prove coldness. |

## Rows that are not OK (REFUSED / FAIL / NOT_RUN)

| Arm | Case | Status | Code / cap | Message |
| --- | --- | --- | --- | --- |
| pg_cli | `project.init (F100k)` | FAIL | 120 | project init: over the 120 s cap; local process killed, remote effect unknown |
| pg_cli | `file.stat (F100k)` | NOT_RUN |  | dependent on failed setup: project.init (F100k) |
| pg_cli | `file.list first-page (F100k)` | NOT_RUN |  | dependent on failed setup: project.init (F100k) |
| pg_cli | `file.glob (F100k)` | NOT_RUN |  | dependent on failed setup: project.init (F100k) |
| pg_cli | `file.grep rare (F100k)` | NOT_RUN |  | dependent on failed setup: project.init (F100k) |
| pg_cli | `file.grep frequent (F100k)` | NOT_RUN |  | dependent on failed setup: project.init (F100k) |
| pg_sdk | `project.init (F100k)` | FAIL | 120 | project init: over the 120 s cap; local process killed, remote effect unknown |
| pg_sdk | `file.stat (F100k)` | NOT_RUN |  | dependent on failed setup: project.init (F100k) |
| pg_sdk | `file.list first-page (F100k)` | NOT_RUN |  | dependent on failed setup: project.init (F100k) |
| pg_sdk | `file.glob (F100k)` | NOT_RUN |  | dependent on failed setup: project.init (F100k) |
| pg_sdk | `file.grep rare (F100k)` | NOT_RUN |  | dependent on failed setup: project.init (F100k) |
| pg_sdk | `file.grep frequent (F100k)` | NOT_RUN |  | dependent on failed setup: project.init (F100k) |

## Concurrency & Refusals (CLI Process-per-Call)

| Backend | Workload | OK / Total | Throughput (calls/s) | Refusals by Code |
| --- | --- | ---: | ---: | --- |
| SQLite | CLI readers x1 | 8 / 8 | 84.31 | `none` |
| SQLite | CLI readers x4 | 32 / 32 | 320.01 | `none` |
| SQLite | CLI readers x8 | 64 / 64 | 512.36 | `none` |
| SQLite | CLI writers x4 (separate branches) | 16 / 16 | 68.31 | `none` |
| SQLite | CLI writers x4 (same branch) | 16 / 16 | 69.43 | `none` |
| PostgreSQL | CLI readers x1 | 8 / 8 | 15.45 | `none` |
| PostgreSQL | CLI readers x4 | 32 / 32 | 57.85 | `none` |
| PostgreSQL | CLI readers x8 | 64 / 64 | 116.37 | `none` |
| PostgreSQL | CLI writers x4 (separate branches) | 16 / 16 | 40.81 | `none` |
| PostgreSQL | CLI writers x4 (same branch) | 16 / 16 | 20.17 | `none` |

## Registered NOT_RUN Routes

| Route | Status & Reason |
| --- | --- |
| `worker:docker` | NOT_RUN: Docker daemon unavailable on this non-root Linux host |
| `worker:lima` | NOT_RUN: Lima VM unavailable on this Linux host |
| `worker:apple-container` | NOT_RUN: macOS-only route |

## Answers to the #157 "Done when" questions

All numbers are p50 values from the tables above (warm, diagnostic, native SQLite on ext4, this commit). These answers were written by hand from those tables.

1. **What does one CLI file call cost against an SDK call?** A new process adds about 5.5–6.5 ms per call on this host. Examples:
   - `file.read (1k)`: 6.33 ms (CLI) vs 0.57 ms (SDK);
   - `file.list` first page: 6.3–6.4 ms vs 0.5–0.7 ms at any tree size;
   - `commit.diff`: 6.4–6.7 ms vs 0.7 ms.

   The native trace's `dispatch` step is about 0.03 ms of that. The rest is process start, opening the home and Store, and the lease.

   The fixed cost stops mattering once a call itself takes hundreds of milliseconds. `file.grep rare (F10k)` is 237 ms (CLI) vs 244 ms (SDK).
2. **How do reads scale with tree size and history depth?**
   - `file.list` first page is flat from F100 to F100k: 0.53 → 0.68 ms (SDK).
   - `file.glob` stays low: 1.5–2.7 ms (SDK).
   - `file.grep rare` grows linearly with the number of files: 21 ms (F1k) → 244 ms (F10k) → 3.1 s (F100k) (SDK).
   - `file.blame` grows with history depth: 0.9 ms (H1) → 40 ms (H100) → 385 ms (H1000) (SDK).
   - `file.history` first page grows slowly: 1.4 → 35 ms (H1 → H1000).
   - `commit.diff` stays flat: 0.68 → 0.75 ms.
3. **What does one write Commit cost in time and stored bytes?** Time:
   - `file.write`: about 19–20 ms (SDK) and about 49–52 ms (CLI) for 1 KiB to 1 MiB.
   - `file.write` 64 MiB: about 0.2–0.4 s.
   - `file.edit` (small): 21 ms (SDK).
   - `file.apply` batch 100: 51 ms (SDK), so 0.5 ms per file.
   - The 8,192-row `apply` commits in about 0.9 s and is not refused. 8,191 (`TRANSACTION_ROW_LIMIT`) only selects the commit path.

   Stored bytes: about 1.5–4 KB per write. Write payloads are generated repeating text, so content-defined deduplication hides the payload. These rows measure metadata and Commit overhead, not the cost of storing incompressible data.
4. **What does the worker route add?** NOT_RUN in this report. The `docker` route needs Docker Desktop, which was not running on the host. `lima` and `apple-container` need macOS.
5. **What does PostgreSQL cost against SQLite for each call?** PostgreSQL 18.7 ran in Docker Desktop with the image's default settings (`shared_buffers` 128 MB, `fsync` on, Store `synchronous_commit=off`). It was reached from WSL through Docker Desktop's port forward. The figures are SDK p50, with the CLI p50 in brackets.
   - **Small reads are about 4–15× slower:**
     - `file.read (1k)`: 7.7 ms vs 0.49 ms (CLI 34 vs 6.3 ms).
     - `file.stat (F1k)`: 24.7 vs 2.1 ms.
     - `file.list` first page (F10k): 7.6 vs 0.76 ms.
     - `commit.diff`: 10.4 vs 0.74 ms.
     
     Each PostgreSQL call pays round trips, and a CLI call also pays its own connect and login (CLI 34 vs SDK 7.7 ms).
   - **History reads are about 12–16× slower:** `file.blame (H1000)` takes 4.97 s vs 0.40 s, and `file.history (H1000)` 0.50 s vs 0.036 s.
   - **`file.grep rare (F10k)` is about 4× slower:** 1.0 s vs 0.24 s.
   - **Single writes are about the same or faster:**
     - `file.write (1k)`: 12.6 vs 19.5 ms.
     - `file.edit` (small): 13.4 vs 20.6 ms.
     - `file.apply` batch 100: 39.9 vs 40.4 ms.
   - **Bulk import is the outlier:**
     - `project init` F10k takes 36.0 s vs 0.97 s.
     - F100k exceeds the 120 s per-call cap on PostgreSQL (FAIL row), and its five F100k reads are NOT_RUN. On SQLite it takes 11.9 s.

   These numbers include a network hop through Docker Desktop and a server with default settings. They compare the two backends within this run; they are not comparable with the 2026-11-22 PostgreSQL figures, which came from another host and setup.

**Change from the 2026-11-22 report:** SDK `file.write (1k)` was 7.4 ms there and is 18.8 ms here. The source (`54937e6434` → `ca4be0bf3c`), the host and the CLI content transport (`--from` instead of stdin) all differ, so this report does not attribute the change. A same-host A/B run of the two commits would settle it.

## Main Observations & Cleanup

- **CLI vs persistent SDK**: on SQLite `file.stat (F1k)` a fresh CLI process takes `8.473 ms` p50 against `2.085 ms` for the persistent client.
- **PostgreSQL vs SQLite**: persistent client `file.stat (F1k)` `24.722 ms` (PostgreSQL) against `2.085 ms` (SQLite).
- **Cleanup**: owned SQLite store removed via `layerfs store remove`, PostgreSQL store disconnected via `layerfs store disconnect`, scratch database dropped, temporary home/fixtures deleted.
