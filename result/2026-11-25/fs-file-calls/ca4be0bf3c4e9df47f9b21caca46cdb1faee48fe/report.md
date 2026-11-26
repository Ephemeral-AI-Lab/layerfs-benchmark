# fs-file-calls — ca4be0bf3c

**PARTIAL (diagnostic warm): measured the mountless LayerFS 2.0 `file.*` + `commit.diff` calls across CLI and persistent `@layerfs/node` SDK on native SQLite (ext4) and PostgreSQL 18.7 (Debian 18.7-1.pgdg13+5) and the docker machine's worker (SQLite) (file.stat (F1k) p50: SQLite SDK `2.126 ms`, SQLite CLI `8.525 ms`, PG SDK `25.106 ms`, PG CLI `59.652 ms`, docker-route SDK `3.16 ms`, docker-route CLI `5.218 ms`); rows by status: FAIL 2, NOT_RUN 10, OK 321, REFUSED 8; 222 cold rows registered as INELIGIBLE (no cold claim); fixture and export proofs passed; 2 unavailable routes recorded as NOT_RUN.**

## Configuration & Provenance

| Field | Value |
| --- | --- |
| LayerFS commit | `ca4be0bf3c4e9df47f9b21caca46cdb1faee48fe` |
| CLI binary SHA-256 | `9f1d1e2abd9596624a77567a6ed417f3360c74b70661dac3c8e4e893a80dfc25` |
| Node addon SHA-256 | `d1ec12ae0c15f81a66ebebc07a728cb4001ca8a8fe00773527f126d03126dfec` |
| Host | 13th Gen Intel(R) Core(TM) i9-13900HX, 32 CPUs, 7.8 GiB RAM, kernel 6.6.87.2-microsoft-standard-WSL2 |
| Machine route | `native` (`LAYERFS_TEST_TMPDIR` on ext4); Node SDK arm is a persistent-client exception to "public CLI for every operation" |
| PostgreSQL | 18.7 (Debian 18.7-1.pgdg13+5), pg_stat_statements: True, store `synchronous_commit=off`; settings `{"effective_cache_size": "524288", "fsync": "on", "full_page_writes": "on", "max_connections": "200", "shared_buffers": "16384", "shared_preload_libraries": "pg_stat_statements", "synchronous_commit": "off", "wal_level": "replica"}` |
| Worker route | `docker` machine (backend `sqlite`), worker build id `02d37a3e8ad9/63035e1da40f`: sealed bundle `02d37a3e8ad9` (`release` profile, protocol 3, source `ca4be0bf3c`, worker sha256 `63035e1da40f`); `machine doctor docker` clean |
| Sample sizes | reads `N=15` (F10k/F100k/deeper history capped), writes `N=10`, trees F100, F1k, F10k, F100k, history H1, H50, H100, H1000 |
| Per-call cap | 120 s; a call over it is a FAIL row and the run continues |
| Disk free (GB) | start 849.3, end 848.8 (stop below 25) |
| Cache protocol | warm (declared preconditioning; OS page cache not dropped — labelled diagnostic) |
| Local receipts | `results.json` / `results.csv` under `--output`, not committed (AGENTS.md:64-65) |

## Fixtures (manifest = sha256 over sorted path, size, content sha256)

| Fixture | Files | Bytes | Manifest SHA-256 | Unchanged after write rows |
| --- | ---: | ---: | --- | --- |
| F100 | 100 | 4894 | `e091298ea2f83ce4…` | sqlite: True, pg: True, docker: True |
| F1k | 1000 | 49894 | `aafb8b20c3ebaca0…` | sqlite: True, pg: True, docker: True |
| F10k | 10000 | 508894 | `3fafd345351ec254…` | sqlite: True, pg: True, docker: True |
| F100k | 100000 | 5188894 | `609329791afefb7c…` | sqlite: True |
| sizes | 5 | 17892352 | `a9738398f610334d…` | sqlite: True, pg: True, docker: True |
| hist | 1 | 11 | `16239d6e3d6c3a70…` | sqlite: True, pg: True, docker: True |

## Latency by Call (p50 / p95 ms, warm diagnostic)

| Case | SQLite SDK p50 / p95 | SQLite CLI p50 / p95 | PG SDK p50 / p95 | PG CLI p50 / p95 | Docker SDK p50 / p95 | Docker CLI p50 / p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `file.read (1k)` | 0.59 / 0.80 (n=15) | 6.68 / 6.84 (n=15) | 7.26 / 8.69 (n=15) | 43.46 / 51.84 (n=15) | 1.80 / 2.28 (n=15) | 3.30 / 3.80 (n=15) |
| `file.read (64k)` | 1.45 / 1.64 (n=15) | 7.87 / 9.43 (n=15) | 8.12 / 9.10 (n=15) | 40.57 / 47.09 (n=15) | 3.55 / 3.73 (n=15) | 4.92 / 5.77 (n=15) |
| `file.read (1m)` | 1.48 / 1.83 (n=15) | 8.06 / 9.23 (n=15) | 10.37 / 11.98 (n=15) | 42.20 / 53.65 (n=15) | 3.32 / 4.07 (n=15) | 5.24 / 7.16 (n=15) |
| `file.read (16m_win2000)` | 1.59 / 1.71 (n=15) | 8.80 / 10.30 (n=15) | 11.15 / 11.44 (n=15) | 42.91 / 51.81 (n=15) | 3.48 / 4.52 (n=15) | 5.25 / 5.99 (n=15) |
| `file.stat (F100)` | 1.76 / 2.15 (n=15) | 9.31 / 11.22 (n=15) | 24.22 / 29.43 (n=15) | 61.11 / 70.75 (n=15) | 2.99 / 3.52 (n=15) | 4.71 / 5.15 (n=15) |
| `file.list first-page (F100)` | 0.57 / 0.71 (n=15) | 7.87 / 8.19 (n=15) | 5.88 / 7.29 (n=15) | 39.21 / 46.29 (n=15) | 1.58 / 2.69 (n=15) | 3.36 / 4.70 (n=15) |
| `file.glob (F100)` | 1.97 / 2.27 (n=15) | 9.90 / 10.80 (n=15) | 11.52 / 13.48 (n=15) | 160.47 / 186.94 (n=15) | 2.97 / 3.41 (n=15) | 4.80 / 7.37 (n=15) |
| `file.grep rare (F100)` | 2.37 / 2.62 (n=15) | 11.03 / 11.93 (n=15) | 13.25 / 14.73 (n=15) | 168.08 / 191.77 (n=15) | 3.79 / 4.53 (n=15) | 5.52 / 6.62 (n=15) |
| `file.grep frequent (F100)` | 1.91 / 2.13 (n=15) | 9.58 / 10.44 (n=15) | 11.26 / 12.37 (n=15) | 124.96 / 154.76 (n=15) | 3.13 / 4.67 (n=15) | 5.49 / 7.68 (n=15) |
| `file.stat (F1k)` | 2.13 / 2.29 (n=15) | 8.53 / 9.37 (n=15) | 25.11 / 27.16 (n=15) | 59.65 / 68.36 (n=15) | 3.16 / 3.54 (n=15) | 5.22 / 5.92 (n=15) |
| `file.list first-page (F1k)` | 0.62 / 0.71 (n=15) | 7.14 / 9.48 (n=15) | 7.26 / 9.28 (n=15) | 38.45 / 44.61 (n=15) | 1.73 / 1.96 (n=15) | 3.69 / 4.15 (n=15) |
| `file.glob (F1k)` | 2.51 / 3.80 (n=15) | 10.77 / 11.47 (n=15) | 16.96 / 18.76 (n=15) | 180.20 / 234.82 (n=15) | 3.76 / 4.40 (n=15) | 5.51 / 6.08 (n=15) |
| `file.grep rare (F1k)` | 21.01 / 22.18 (n=15) | 37.55 / 39.29 (n=15) | 65.77 / 71.91 (n=15) | 711.22 / 820.24 (n=15) | 23.25 / 24.49 (n=15) | 24.62 / 26.36 (n=15) |
| `file.grep frequent (F1k)` | 1.90 / 2.11 (n=15) | 9.09 / 11.48 (n=15) | 13.47 / 14.77 (n=15) | 81.42 / 97.10 (n=15) | 3.02 / 3.34 (n=15) | 5.16 / 5.81 (n=15) |
| `file.stat (F10k)` | 3.05 / 3.36 (n=10) | 9.46 / 9.71 (n=5) | 33.20 / 36.80 (n=10) | 75.13 / 79.03 (n=5) | 4.29 / 4.49 (n=10) | 5.92 / 6.30 (n=5) |
| `file.list first-page (F10k)` | 0.81 / 0.90 (n=10) | 7.22 / 7.40 (n=5) | 8.26 / 9.06 (n=10) | 41.33 / 45.48 (n=5) | 1.84 / 2.27 (n=10) | 3.62 / 3.76 (n=5) |
| `file.glob (F10k)` | 1.61 / 1.83 (n=10) | 7.69 / 8.10 (n=5) | 13.84 / 15.59 (n=10) | 60.06 / 64.61 (n=5) | 2.59 / 2.75 (n=10) | 4.35 / 4.67 (n=5) |
| `file.grep rare (F10k)` | 250.13 / 276.42 (n=10) | 248.82 / 273.76 (n=5) | 1052.02 / 1207.21 (n=10) | 1088.10 / 1218.22 (n=5) | 245.94 / 251.46 (n=10) | 251.82 / 259.90 (n=5) |
| `file.grep frequent (F10k)` | 1.99 / 2.21 (n=10) | 8.84 / 8.99 (n=5) | 12.15 / 15.38 (n=10) | 57.29 / 63.58 (n=5) | 3.11 / 4.03 (n=10) | 5.04 / 5.52 (n=5) |
| `file.stat (F100k)` | 3.00 / 3.27 (n=10) | 9.14 / 9.27 (n=5) | NOT_RUN | NOT_RUN | — | — |
| `file.list first-page (F100k)` | 0.82 / 0.95 (n=10) | 7.57 / 7.79 (n=5) | NOT_RUN | NOT_RUN | — | — |
| `file.glob (F100k)` | 1.61 / 1.80 (n=10) | 8.78 / 9.69 (n=5) | NOT_RUN | NOT_RUN | — | — |
| `file.grep rare (F100k)` | 3216.45 / 3251.78 (n=10) | 3092.52 / 3161.91 (n=5) | NOT_RUN | NOT_RUN | — | — |
| `file.grep frequent (F100k)` | 1.67 / 1.87 (n=10) | 8.32 / 9.12 (n=5) | NOT_RUN | NOT_RUN | — | — |
| `file.blame (H1, head)` | 0.85 / 1.05 (n=15) | 7.27 / 7.95 (n=15) | 14.07 / 15.95 (n=15) | 51.50 / 61.81 (n=15) | 2.15 / 2.65 (n=15) | 4.15 / 6.63 (n=15) |
| `file.history (H1, head)` | 1.36 / 1.48 (n=15) | 7.80 / 10.75 (n=15) | 21.29 / 23.05 (n=15) | 64.77 / 78.77 (n=15) | 2.39 / 3.02 (n=15) | 4.16 / 4.49 (n=15) |
| `file.history (H1, pinned)` | 1.36 / 1.48 (n=15) | 7.67 / 8.71 (n=15) | 20.77 / 27.66 (n=15) | 59.43 / 72.58 (n=15) | 2.48 / 3.67 (n=15) | 4.24 / 4.91 (n=15) |
| `commit.diff (H1, head)` | 0.70 / 0.77 (n=15) | 6.92 / 7.33 (n=15) | 9.69 / 11.01 (n=15) | 50.39 / 57.80 (n=15) | 1.65 / 3.17 (n=15) | 3.73 / 4.78 (n=15) |
| `file.blame (H50, head)` | 20.17 / 22.05 (n=10) | 28.82 / 30.35 (n=5) | 290.82 / 341.06 (n=10) | 435.64 / 457.43 (n=5) | 21.31 / 23.36 (n=10) | 24.03 / 24.68 (n=5) |
| `file.history (H50, head)` | 35.13 / 36.27 (n=10) | 43.85 / 47.02 (n=5) | 564.53 / 591.82 (n=10) | 694.12 / 728.23 (n=5) | 38.21 / 40.24 (n=10) | 41.07 / 44.68 (n=5) |
| `file.history (H50, pinned)` | 35.82 / 38.03 (n=10) | 46.47 / 48.46 (n=5) | 567.39 / 628.34 (n=10) | 792.09 / 858.53 (n=5) | 41.08 / 46.79 (n=10) | 41.18 / 44.60 (n=5) |
| `commit.diff (H50, head)` | 0.76 / 0.88 (n=10) | 8.16 / 9.24 (n=5) | 10.55 / 13.64 (n=10) | 48.58 / 61.57 (n=5) | 1.81 / 2.97 (n=10) | 4.53 / 5.35 (n=5) |
| `file.blame (H100, head)` | 39.39 / 42.00 (n=10) | 53.66 / 55.30 (n=5) | 551.53 / 588.95 (n=10) | 824.54 / 855.73 (n=5) | 43.75 / 49.21 (n=10) | 45.71 / 47.51 (n=5) |
| `file.history (H100, head)` | 35.63 / 36.92 (n=10) | 47.30 / 49.36 (n=5) | 525.83 / 574.05 (n=10) | 724.95 / 789.43 (n=5) | 38.70 / 45.65 (n=10) | 41.34 / 42.94 (n=5) |
| `file.history (H100, pinned)` | 37.11 / 39.73 (n=10) | 46.70 / 48.75 (n=5) | 544.13 / 591.87 (n=10) | 725.77 / 931.63 (n=5) | 37.47 / 39.18 (n=10) | 42.52 / 43.07 (n=5) |
| `commit.diff (H100, head)` | 0.85 / 0.96 (n=10) | 7.30 / 7.52 (n=5) | 10.86 / 12.92 (n=10) | 46.89 / 47.81 (n=5) | 1.62 / 1.75 (n=10) | 4.26 / 4.89 (n=5) |
| `file.blame (H1000, head)` | 406.44 / 428.49 (n=10) | 424.76 / 435.45 (n=5) | 5506.22 / 5963.43 (n=10) | 7882.79 / 8536.85 (n=5) | — | — |
| `file.history (H1000, head)` | 36.69 / 39.77 (n=10) | 47.07 / 49.36 (n=5) | 589.98 / 646.33 (n=10) | 779.80 / 1366.80 (n=5) | — | — |
| `file.history (H1000, pinned)` | 36.80 / 38.79 (n=10) | 44.16 / 44.54 (n=5) | 569.93 / 631.22 (n=10) | 729.30 / 745.07 (n=5) | — | — |
| `commit.diff (H1000, head)` | 0.71 / 0.85 (n=10) | 6.92 / 7.58 (n=5) | 10.55 / 12.13 (n=10) | 48.30 / 49.77 (n=5) | — | — |
| `file.write (0b)` | 19.54 / 30.52 (n=10) | 51.42 / 53.95 (n=10) | 17.01 / 22.55 (n=10) | 90.86 / 97.84 (n=10) | 16.19 / 19.29 (n=10) | 17.68 / 19.03 (n=10) |
| `file.write (1k)` | 18.31 / 75.60 (n=10) | 47.77 / 49.66 (n=10) | 13.69 / 17.49 (n=10) | 81.46 / 101.48 (n=10) | 17.02 / 18.38 (n=10) | 17.25 / 21.04 (n=10) |
| `file.write (64k)` | 19.26 / 22.54 (n=10) | 47.60 / 52.34 (n=10) | 15.13 / 17.65 (n=10) | 96.03 / 104.36 (n=10) | 17.93 / 20.23 (n=10) | 18.50 / 21.79 (n=10) |
| `file.write (1m)` | 20.04 / 22.79 (n=5) | 47.58 / 55.45 (n=3) | 21.63 / 28.47 (n=5) | 86.57 / 104.62 (n=3) | 29.63 / 30.57 (n=5) | 26.16 / 29.23 (n=3) |
| `file.write (64m)` | 372.87 / 541.34 (n=3) | 208.21 / 356.32 (n=3) | 385.78 / 1055.12 (n=3) | 268.63 / 409.30 (n=3) | — | — |
| `file.edit (small)` | 20.10 / 21.61 (n=10) | 48.20 / 52.85 (n=10) | 13.51 / 17.51 (n=10) | 95.83 / 108.62 (n=10) | 16.24 / 18.68 (n=10) | 18.64 / 21.33 (n=10) |
| `file.mkdir` | 20.02 / 21.48 (n=10) | 47.75 / 50.25 (n=10) | 22.34 / 24.92 (n=10) | 82.45 / 90.91 (n=10) | 17.75 / 18.62 (n=10) | 18.76 / 21.10 (n=10) |
| `file.cp (file)` | 22.12 / 24.77 (n=10) | 45.53 / 50.98 (n=10) | 27.76 / 31.21 (n=10) | 83.22 / 90.52 (n=10) | 17.70 / 19.62 (n=10) | 19.03 / 20.66 (n=10) |
| `file.mv (file)` | 21.63 / 24.16 (n=10) | 47.48 / 48.70 (n=10) | 14.63 / 17.61 (n=10) | 83.37 / 106.58 (n=10) | 16.32 / 18.20 (n=10) | 16.97 / 20.09 (n=10) |
| `file.rm (file)` | 21.95 / 23.40 (n=10) | 43.82 / 48.48 (n=10) | 25.38 / 32.42 (n=10) | 83.81 / 91.05 (n=10) | 17.84 / 20.48 (n=10) | 18.72 / 76.50 (n=10) |
| `file.apply (batch=1)` | 19.01 / 21.48 (n=10) | — | 14.29 / 16.11 (n=10) | — | 15.99 / 18.46 (n=10) | — |
| `file.apply (batch=10)` | 20.59 / 21.75 (n=10) | — | 21.75 / 24.66 (n=10) | — | 18.19 / 21.49 (n=10) | — |
| `file.apply (batch=100)` | 35.35 / 42.12 (n=5) | — | 46.10 / 53.77 (n=5) | — | 33.44 / 40.02 (n=5) | — |

## Resources and native dispatch (CLI: per-call rusage; SDK: process deltas per call)

| Case | CLI CPU ms p50 | CLI max RSS MiB | CLI dispatch ms p50 | SDK CPU ms/call | SDK RSS delta MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| `file.read (1k)` | 6.456 | 225.7 | 0.03 | 0.624 | 0.0 |
| `file.read (64k)` | 7.609 | 225.7 | 0.032 | 1.487 | 3.0 |
| `file.read (1m)` | 7.903 | 225.7 | 0.029 | 1.526 | 2.0 |
| `file.read (16m_win2000)` | 8.512 | 225.7 | 0.035 | 1.566 | -1.3 |
| `file.stat (F100)` | 8.644 | 225.7 | 0.04 | 1.808 | 0.0 |
| `file.list first-page (F100)` | 7.276 | 225.7 | 0.036 | 0.577 | 0.0 |
| `file.glob (F100)` | 9.57 | 225.7 | 0.035 | 1.972 | 0.0 |
| `file.grep rare (F100)` | 10.558 | 225.7 | 0.034 | 2.378 | 0.5 |
| `file.grep frequent (F100)` | 9.222 | 225.7 | 0.032 | 1.95 | 0.2 |
| `file.stat (F1k)` | 8.271 | 225.7 | 0.03 | 2.13 | 0.0 |
| `file.list first-page (F1k)` | 6.518 | 225.7 | 0.031 | 0.604 | 0.0 |
| `file.glob (F1k)` | 10.468 | 225.7 | 0.032 | 2.543 | 1.0 |
| `file.grep rare (F1k)` | 37.262 | 225.7 | 0.034 | 21.183 | 1.8 |
| `file.grep frequent (F1k)` | 8.793 | 225.7 | 0.033 | 1.902 | 0.0 |
| `file.stat (F10k)` | 9.214 | 225.7 | 0.031 | 3.064 | 0.0 |
| `file.list first-page (F10k)` | 6.638 | 225.7 | 0.032 | 0.772 | 0.0 |
| `file.glob (F10k)` | 7.268 | 225.7 | 0.031 | 1.605 | 0.0 |
| `file.grep rare (F10k)` | 248.204 | 225.7 | 0.034 | 253.985 | 11.5 |
| `file.grep frequent (F10k)` | 8.416 | 225.7 | 0.039 | 1.997 | 0.0 |
| `file.stat (F100k)` | 8.486 | 225.7 | 0.029 | 3.032 | 0.0 |
| `file.list first-page (F100k)` | 6.94 | 225.7 | 0.033 | 0.825 | 0.0 |
| `file.glob (F100k)` | 7.754 | 225.7 | 0.037 | 1.644 | 0.0 |
| `file.grep rare (F100k)` | 3091.882 | 225.7 | 0.035 | 3201.376 | 5.2 |
| `file.grep frequent (F100k)` | 8.032 | 225.7 | 0.033 | 1.645 | 0.0 |
| `file.blame (H1, head)` | 6.899 | 225.7 | 0.032 | 0.879 | 0.0 |
| `file.history (H1, head)` | 7.57 | 225.7 | 0.033 | 1.323 | 0.0 |
| `file.history (H1, pinned)` | 7.293 | 225.7 | 0.032 | 1.338 | 0.0 |
| `commit.diff (H1, head)` | 6.576 | 225.7 | 0.031 | 0.669 | 0.0 |
| `file.blame (H50, head)` | 28.554 | 225.7 | 0.032 | 20.373 | 0.0 |
| `file.history (H50, head)` | 43.422 | 225.7 | 0.031 | 35.068 | 0.0 |
| `file.history (H50, pinned)` | 45.992 | 225.7 | 0.044 | 35.795 | 0.0 |
| `commit.diff (H50, head)` | 7.885 | 225.7 | 0.039 | 0.729 | 0.0 |
| `file.blame (H100, head)` | 53.136 | 225.7 | 0.037 | 39.485 | 0.0 |
| `file.history (H100, head)` | 46.989 | 225.7 | 0.037 | 35.564 | 0.0 |
| `file.history (H100, pinned)` | 45.631 | 225.7 | 0.035 | 37.333 | 0.0 |
| `commit.diff (H100, head)` | 6.878 | 225.7 | 0.036 | 0.849 | 0.0 |
| `file.blame (H1000, head)` | 422.561 | 225.7 | 0.039 | 407.335 | 0.0 |
| `file.history (H1000, head)` | 46.486 | 225.7 | 0.034 | 37.094 | 0.0 |
| `file.history (H1000, pinned)` | 44.014 | 225.7 | 0.037 | 36.922 | 0.0 |
| `commit.diff (H1000, head)` | 6.784 | 225.7 | 0.034 | 0.716 | 0.0 |
| `file.write (0b)` | 17.461 | 240.7 | 0.053 | 7.179 | 1.2 |
| `file.write (1k)` | 14.328 | 240.7 | 0.054 | 4.296 | 0.0 |
| `file.write (64k)` | 15.553 | 240.7 | 0.085 | 5.179 | 0.5 |
| `file.write (1m)` | 17.17 | 240.7 | 0.43 | 9.912 | 1.4 |
| `file.write (64m)` | 172.192 | 368.7 | 23.547 | 447.258 | 47.0 |
| `file.edit (small)` | 18.891 | 368.7 | 0.055 | 4.447 | 0.0 |
| `file.mkdir` | 14.839 | 368.7 | 0.058 | 6.153 | 0.0 |
| `file.cp (file)` | 14.883 | 368.7 | 0.053 | 6.974 | 0.0 |
| `file.mv (file)` | 13.967 | 368.7 | 0.053 | 5.833 | -65.0 |
| `file.rm (file)` | 14.586 | 368.7 | 0.054 | 6.183 | 0.0 |
| `file.apply (batch=1)` | — | — | UNAVAILABLE | 4.652 | 0.0 |
| `file.apply (batch=10)` | — | — | UNAVAILABLE | 6.097 | 0.0 |
| `file.apply (batch=100)` | — | — | UNAVAILABLE | 22.859 | 0.0 |

Step attribution: native rows carry the `dispatch` step only; `route`, `connect`, `request` are UNAVAILABLE on native. Source: control/crates/layerfs-home/src/trace.rs:24-37 (steps are written only when LAYERFS_TRACE and LAYERFS_TRACE_STEP are both set; the native route writes `step: dispatch` events only, observed in T1).

## Worker route (docker machine, SQLite Store)

The same `sqlite` Store grammar, created with `layerfs store create dk --machine docker`; every call goes CLI/SDK -> the machine's worker (a container on the host's Docker Engine) -> daemon. Warm diagnostic, no cold claim. Rows run F10k and smaller, history H1/H100; no 64 MiB write, no limit probes, no concurrency on this route. Native p50 is from the same run.

| Case | native SQLite CLI p50 ms | docker CLI p50 ms | native SQLite SDK p50 ms | docker SDK p50 ms |
| --- | ---: | ---: | ---: | ---: |
| `file.read (1k)` | 6.68 | 3.30 | 0.59 | 1.80 |
| `file.stat (F1k)` | 8.53 | 5.22 | 2.13 | 3.16 |
| `file.list first-page (F10k)` | 7.22 | 3.62 | 0.81 | 1.84 |
| `file.grep rare (F10k)` | 248.82 | 251.82 | 250.13 | 245.94 |
| `file.write (1k)` | 47.77 | 17.25 | 18.31 | 17.02 |

Step table (docker CLI rows, `LAYERFS_TRACE` + `LAYERFS_TRACE_STEP`): median over cases of each case's per-call p50, ms. The SDK arm is not traced. Source: control/crates/layerfs-home/src/trace.rs:1-10,82-97 and control/crates/layerfs-control/src/worker_server.rs:27 (a worker-routed call asks its worker for its steps: dispatch, route, connect, ready, request, answer from the caller, worker.<step> from the worker; route..answer repeat per worker hop and are summed per call).

| Step | read cases (median ms) | cases | write cases (median ms) | cases |
| --- | ---: | ---: | ---: | ---: |
| `dispatch` | 0.035 | 31 | 0.06 | 9 |
| `route` | 0.149 | 31 | 0.173 | 9 |
| `connect` | 0.306 | 31 | 0.457 | 9 |
| `ready` | 0.331 | 31 | 0.423 | 9 |
| `request` | 0.053 | 31 | 0.062 | 9 |
| `answer` | 2.211 | 31 | 14.822 | 9 |
| `worker.result` | 1.711 | 31 | 13.681 | 9 |

| Case | `dispatch` | `route` | `connect` | `ready` | `request` | `answer` | `worker.result` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `file.read (1k)` | 0.031 | 0.137 | 0.252 | 0.287 | 0.054 | 0.754 | 0.488 |
| `file.stat (F1k)` | 0.031 | 0.136 | 0.27 | 0.331 | 0.05 | 2.434 | 2.204 |
| `file.list first-page (F10k)` | 0.032 | 0.151 | 0.266 | 0.372 | 0.048 | 0.946 | 0.674 |
| `file.grep rare (F10k)` | 0.041 | 0.185 | 0.481 | 0.456 | 0.056 | 248.208 | 247.367 |
| `file.write (1k)` | 0.06 | 0.167 | 0.567 | 0.512 | 0.06 | 13.774 | 13.184 |

## Write Commit Storage Growth

| Write Case | SQLite SDK `delta_stored_bytes` / `delta_size_bytes` | SQLite CLI `delta_stored_bytes` / `delta_size_bytes` | PG SDK `delta_stored_bytes` / `delta_size_bytes` | PG CLI `delta_stored_bytes` / `delta_size_bytes` | Docker SDK `delta_stored_bytes` / `delta_size_bytes` | Docker CLI `delta_stored_bytes` / `delta_size_bytes` |
| --- | --- | --- | --- | --- | --- | --- |
| `file.write (0b)` | 2848 / 8192 | 3227 / 8192 | 2838 / 32768 | 3231 / 32768 | 2837 / 16384 | 3231 / 20480 |
| `file.write (1k)` | 2944 / 12288 | 3903 / 16384 | 2947 / 24576 | 3902 / 16384 | 2940 / 8192 | 3894 / 16384 |
| `file.write (64k)` | 2956 / 20480 | 3958 / 16384 | 2956 / 8192 | 3959 / 16384 | 2951 / 16384 | 3964 / 8192 |
| `file.write (1m)` | 2550 / 12288 | 2338 / 4096 | 2547 / 40960 | 2338 / 57344 | 2542 / 0 | 2325 / 8192 |
| `file.write (64m)` | 1532 / 8192 | 2670 / 4096 | 1531 / 0 | 2667 / 16384 | — / — | — / — |

## Limits (one row per probe; cites the source that sets the limit)

| Probe | Arm | Status | Code | ms | Detail | Source |
| --- | --- | --- | --- | ---: | --- | --- |
| `limit: file.write content 16 MiB` | sqlite_cli | OK |  | 153.947 | `{"content_bytes": 16777217}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 64 MiB` | sqlite_cli | OK |  | 450.47 | `{"content_bytes": 67108865}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 256 MiB` | sqlite_cli | OK |  | 1770.635 | `{"content_bytes": 268435457}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.apply 1000 rows` | sqlite_cli | OK |  | 175.814 | `{"rows": 1000}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8191 rows` | sqlite_cli | OK |  | 978.608 | `{"rows": 8191}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8192 rows` | sqlite_cli | OK |  | 925.509 | `{"rows": 8192}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: commit.diff page limit 1000` | sqlite_cli | OK |  | 333.224 | `{"changed_paths": 8192, "page_limit": 1000, "items": 220, "has_next": true}`  | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: commit.diff page limit 1001` | sqlite_cli | REFUSED | InvalidInput | — | `{}` commit diff: commit.diff: `limit` is 1 to 1000 | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: file.read window 2000 lines` | sqlite_cli | OK |  | 9.131 | `{"lines_asked": 2000, "reply_bytes": 48388, "text_bytes": 47616, "has_next_line": true}`  | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |
| `limit: file.read window 2001 lines` | sqlite_cli | REFUSED | InvalidInput | — | `{}` file read: file.read: `limit` is 1 to 2000 | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |
| `limit: file.write content 16 MiB` | sqlite_sdk | OK |  | 133.003 | `{"content_bytes": 16777217}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 64 MiB` | sqlite_sdk | OK |  | 520.52 | `{"content_bytes": 67108865}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 256 MiB` | sqlite_sdk | OK |  | 2487.269 | `{"content_bytes": 268435457}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.apply 1000 rows` | sqlite_sdk | OK |  | 128.04 | `{"rows": 1000}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8191 rows` | sqlite_sdk | OK |  | 965.392 | `{"rows": 8191}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8192 rows` | sqlite_sdk | OK |  | 867.997 | `{"rows": 8192}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: commit.diff page limit 1000` | sqlite_sdk | OK |  | 331 | `{"changed_paths": 8192, "page_limit": 1000, "items": 220, "has_next": true}`  | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: commit.diff page limit 1001` | sqlite_sdk | REFUSED | InvalidInput | — | `{}` commit.diff: `limit` is 1 to 1000 | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: file.read window 2000 lines` | sqlite_sdk | OK |  | 2.206 | `{"lines_asked": 2000, "reply_bytes": 48387, "text_bytes": 47616, "has_next_line": true}`  | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |
| `limit: file.read window 2001 lines` | sqlite_sdk | REFUSED | InvalidInput | — | `{}` file.read: `limit` is 1 to 2000 | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |
| `limit: file.write content 16 MiB` | pg_cli | OK |  | 215.094 | `{"content_bytes": 16777217}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 64 MiB` | pg_cli | OK |  | 526.963 | `{"content_bytes": 67108865}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 256 MiB` | pg_cli | OK |  | 2061.345 | `{"content_bytes": 268435457}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.apply 1000 rows` | pg_cli | OK |  | 426.876 | `{"rows": 1000}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8191 rows` | pg_cli | OK |  | 4683.168 | `{"rows": 8191}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8192 rows` | pg_cli | OK |  | 1062.337 | `{"rows": 8192}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: commit.diff page limit 1000` | pg_cli | OK |  | 7758.398 | `{"changed_paths": 8192, "page_limit": 1000, "items": 220, "has_next": true}`  | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: commit.diff page limit 1001` | pg_cli | REFUSED | InvalidInput | — | `{}` commit diff: commit.diff: `limit` is 1 to 1000 | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: file.read window 2000 lines` | pg_cli | OK |  | 45.105 | `{"lines_asked": 2000, "reply_bytes": 48388, "text_bytes": 47616, "has_next_line": true}`  | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |
| `limit: file.read window 2001 lines` | pg_cli | REFUSED | InvalidInput | — | `{}` file read: file.read: `limit` is 1 to 2000 | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |
| `limit: file.write content 16 MiB` | pg_sdk | OK |  | 141.773 | `{"content_bytes": 16777217}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 64 MiB` | pg_sdk | OK |  | 473.452 | `{"content_bytes": 67108865}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 256 MiB` | pg_sdk | OK |  | 2438.272 | `{"content_bytes": 268435457}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.apply 1000 rows` | pg_sdk | OK |  | 145.152 | `{"rows": 1000}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8191 rows` | pg_sdk | OK |  | 989.365 | `{"rows": 8191}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8192 rows` | pg_sdk | OK |  | 1051.225 | `{"rows": 8192}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: commit.diff page limit 1000` | pg_sdk | OK |  | 8287.83 | `{"changed_paths": 8192, "page_limit": 1000, "items": 220, "has_next": true}`  | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: commit.diff page limit 1001` | pg_sdk | REFUSED | InvalidInput | — | `{}` commit.diff: `limit` is 1 to 1000 | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: file.read window 2000 lines` | pg_sdk | OK |  | 10.103 | `{"lines_asked": 2000, "reply_bytes": 48387, "text_bytes": 47616, "has_next_line": true}`  | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |
| `limit: file.read window 2001 lines` | pg_sdk | REFUSED | InvalidInput | — | `{}` file.read: `limit` is 1 to 2000 | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |

## Cold rows

Cold rows are registered per read case and gated by `shared/src/measure.py:181 assess_cache`; none is measured, none is labelled cold (`shared/AGENTS.md:7`).

| Arm | Cold rows | Status | Required domains | Reason |
| --- | ---: | --- | --- | --- |
| sqlite_cli | 40 | INELIGIBLE | layerfs-daemon-worker, filesystem-metadata, host-page-cache | No implemented, demonstrated owned cold-cache enforcement and residency protocol for this route/phase. Fresh CLI process/mount, distinct database and copied fixture do not prove coldness. |
| sqlite_sdk | 40 | INELIGIBLE | layerfs-daemon-worker, filesystem-metadata, host-page-cache | No implemented, demonstrated owned cold-cache enforcement and residency protocol for this route/phase. Fresh CLI process/mount, distinct database and copied fixture do not prove coldness. |
| pg_cli | 40 | INELIGIBLE | layerfs-daemon-worker, filesystem-metadata, host-page-cache, postgresql-shared-buffers, postgresql-server-page-cache | No implemented, demonstrated owned cold-cache enforcement and residency protocol for this route/phase. Fresh CLI process/mount, distinct database and copied fixture do not prove coldness. |
| pg_sdk | 40 | INELIGIBLE | layerfs-daemon-worker, filesystem-metadata, host-page-cache, postgresql-shared-buffers, postgresql-server-page-cache | No implemented, demonstrated owned cold-cache enforcement and residency protocol for this route/phase. Fresh CLI process/mount, distinct database and copied fixture do not prove coldness. |
| docker_cli | 31 | INELIGIBLE | layerfs-daemon-worker, filesystem-metadata, host-page-cache, guest-page-cache | No implemented, demonstrated owned cold-cache enforcement and residency protocol for this route/phase. Fresh CLI process/mount, distinct database and copied fixture do not prove coldness. |
| docker_sdk | 31 | INELIGIBLE | layerfs-daemon-worker, filesystem-metadata, host-page-cache, guest-page-cache | No implemented, demonstrated owned cold-cache enforcement and residency protocol for this route/phase. Fresh CLI process/mount, distinct database and copied fixture do not prove coldness. |

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
| SQLite | CLI readers x1 | 8 / 8 | 69.19 | `none` |
| SQLite | CLI readers x4 | 32 / 32 | 303.65 | `none` |
| SQLite | CLI readers x8 | 64 / 64 | 481.61 | `none` |
| SQLite | CLI writers x4 (separate branches) | 16 / 16 | 60.04 | `none` |
| SQLite | CLI writers x4 (same branch) | 16 / 16 | 57.39 | `none` |
| PostgreSQL | CLI readers x1 | 8 / 8 | 15.09 | `none` |
| PostgreSQL | CLI readers x4 | 32 / 32 | 62.0 | `none` |
| PostgreSQL | CLI readers x8 | 64 / 64 | 101.22 | `none` |
| PostgreSQL | CLI writers x4 (separate branches) | 16 / 16 | 36.96 | `none` |
| PostgreSQL | CLI writers x4 (same branch) | 16 / 16 | 18.59 | `none` |

## Registered NOT_RUN Routes

| Route | Status & Reason |
| --- | --- |
| `worker:lima` | NOT_RUN: Lima VM unavailable on this Linux host |
| `worker:apple-container` | NOT_RUN: macOS-only route |

## Answers to the #157 "Done when" questions

All numbers are p50 values from the tables above (warm, diagnostic, single unified run at `ca4be0bf3c` on this host). These answers were written from those tables and local `results.json` (`pg_statements`).

1. **What does one CLI file call cost against an SDK call?** On native SQLite (`ext4`), spawning a fresh CLI process adds **~6–7 ms** on reads and **~27–30 ms** on small single-file writes over the persistent `@layerfs/node` client:
   - `file.read (1k)`: `6.68 ms` (CLI) vs `0.59 ms` (SDK);
   - `file.stat (F1k)`: `8.53 ms` vs `2.13 ms`;
   - `file.list` first page: `7.14–7.87 ms` vs `0.57–0.82 ms` across F100–F100k;
   - `commit.diff`: `6.92–8.16 ms` vs `0.70–0.85 ms`;
   - `file.write (1k)`: `47.77 ms` vs `18.31 ms`.

   The native trace's `dispatch` step is only `0.03–0.05 ms` of that. The rest is process startup, opening home records, opening the SQLite Store + WAL, and acquiring/releasing the Store lease. Once the operation itself takes hundreds of milliseconds, the fixed CLI cost disappears (`file.grep rare (F10k)`: `248.82 ms` CLI vs `250.13 ms` SDK).
2. **How do reads scale with tree size and history depth?** (native SQLite SDK p50):
   - `file.list` first page stays flat from F100 to F100k: `0.57 → 0.82 ms`.
   - `file.glob` stays flat: `1.61–2.51 ms` (`file.stat`: `1.76–3.05 ms`).
   - `file.grep rare` scales linearly with file count: `2.37 ms` (F100) → `21.01 ms` (F1k) → `250.13 ms` (F10k) → `3.22 s` (`3216.45 ms`, F100k).
   - `file.blame` scales linearly with history depth: `0.85 ms` (H1) → `20.17 ms` (H50) → `39.39 ms` (H100) → `406.44 ms` (H1000).
   - `file.history` first page (`limit=100`) grows until the 100-commit page fills (`1.36 ms` H1 → `35.13 ms` H50 → `35.63 ms` H100) and stays flat at `36.69 ms` (H1000).
   - `commit.diff` stays O(1): `0.70–0.85 ms` from H1 to H1000.
3. **What does one write Commit cost in time and stored bytes?** Time (native SQLite):
   - `file.write`: `18.31–20.04 ms` (SDK) and `47.58–51.42 ms` (CLI) from `0 B` to `1 MiB`.
   - `file.write (64m)`: `372.87 ms` (SDK) and `208.21 ms` (CLI).
   - `file.edit (small)`: `20.10 ms` (SDK), `48.20 ms` (CLI).
   - `file.apply (batch=100)`: `35.35 ms` (SDK), or `0.35 ms` per file (~50× faster per file than single-file `file.write`).
   - `limit: file.apply 8192 rows` commits in `868.00 ms` (SDK) / `925.51 ms` (CLI) and is **not** refused; `8,191` (`TRANSACTION_ROW_LIMIT`) only switches from the fused path to `Fused::Overflow`.

   Stored bytes (`delta_stored_bytes`): `1.5–4.0 KB` (`1532–3958 B`) per write row. Write payloads use deterministic repeating lines, so content-defined deduplication folds repeated chunks; these figures measure per-Commit and metadata overhead, not incompressible payload storage.
4. **What does the worker route add?** Measured on a SQLite Store on the built-in `docker` machine (`layerfs store create dk --machine docker`, sealed release bundle `02d37a3e8ad9/63035e1da40f`, F100–F10k and H1–H100; `lima` and `apple-container` are `NOT_RUN` on Linux):
   - **Against the persistent SDK client**, routing through the container worker adds **~0.8–1.2 ms** on 1 KiB and metadata reads (`~1.8–2.1 ms` on 48–64 KiB read windows):
     - `file.read (1k)`: `1.80 ms` vs `0.59 ms` (+1.21 ms);
     - `file.stat (F1k)`: `3.16 ms` vs `2.13 ms` (+1.03 ms);
     - `file.list` first page (F10k): `1.84 ms` vs `0.81 ms` (+1.03 ms);
     - `commit.diff (H100)`: `1.62 ms` vs `0.85 ms` (+0.77 ms).
     On heavy scans and writes, the hop cost is within noise or slightly faster (`file.grep rare (F10k)`: `245.94 ms` vs `250.13 ms`; `file.write (1k)`: `17.02 ms` vs `18.31 ms`).
   - **Against fresh-process CLI calls**, the `docker` worker route is **faster** than native SQLite (`file.read (1k)`: `3.30` vs `6.68 ms`; `file.stat (F1k)`: `5.22` vs `8.53 ms`; `file.list (F10k)`: `3.62` vs `7.22 ms`; `file.write (1k)`: `17.25` vs `47.77 ms`), because each short-lived CLI process sends a loopback RPC to the long-lived container worker rather than opening the SQLite database, WAL and Store lease in-process on every call.
   - **`LAYERFS_TRACE_STEP` step attribution** (`docker_cli` median across 31 read cases / 9 write cases): caller pre-execution steps sum to **~0.87 ms** on reads (`dispatch` `0.035 ms`, `route` `0.149 ms`, `connect` `0.306 ms`, `ready` `0.331 ms`, `request` `0.053 ms`) and **~1.18 ms** on writes (`0.060 + 0.173 + 0.457 + 0.423 + 0.062 ms`), plus **~0.5–1.1 ms** wire framing between caller `answer` (`2.211 ms` read / `14.822 ms` write) and worker `worker.result` (`1.711 ms` read / `13.681 ms` write).
5. **What does PostgreSQL cost against SQLite for each call?** PostgreSQL 18.7 ran in Docker Desktop with default container settings (`shared_buffers` 128 MB, `fsync` on, Store `synchronous_commit=off`), reached from WSL2 via Docker Desktop port forwarding. Figures below are SDK p50 (CLI p50 in brackets):
   - **Small and metadata reads are ~6–17× slower (~10–13× on the representative cases below):**
     - `file.read (1k)`: `7.26 ms` vs `0.59 ms` (CLI `43.46` vs `6.68 ms`).
     - `file.stat (F1k)`: `25.11 ms` vs `2.13 ms` (CLI `59.65` vs `8.53 ms`).
     - `file.list` first page (F10k): `8.26 ms` vs `0.81 ms` (CLI `41.33` vs `7.22 ms`).
     - `commit.diff (H100)`: `10.86 ms` vs `0.85 ms` (CLI `46.89` vs `7.30 ms`).

     `pg_stat_statements` (top-5 recorded statement templates per case) shows server-side SQL execution is under 1 ms (`~0.22 ms` across `14+` SQL executions per `file.read (1k)`; `~0.86 ms` across `41+` SQL executions per `file.stat (F1k)`), so wall latency is dominated by sequential network round-trips (plus per-process TCP/login setup on CLI).
   - **Deep-history reads are ~14–16× slower:** `file.blame (H1000)` takes `5.51 s` (`5506.22 ms`) vs `0.41 s` (`406.44 ms`), and `file.history (H1000)` takes `0.59 s` (`589.98 ms`) vs `0.037 s` (`36.69 ms`). In `pg_stat_statements` (top-5 templates), one `blame (H1000)` issues `~13,000+` (`13004.8`) SQL queries totaling `~0.43 s` (`427.84 ms`) of server execution time; the remaining `~5.08 s` (`92.2%`) is round-trip latency.
   - **`file.grep rare (F10k)` is ~4.2× slower:** `1.05 s` (`1052.02 ms`) vs `0.25 s` (`250.13 ms`).
   - **Single writes are comparable or slightly faster on persistent SDK, slower on CLI:**
     - `file.write (1k)`: `13.69 ms` vs `18.31 ms` (CLI `81.46` vs `47.77 ms`).
     - `file.edit (small)`: `13.51 ms` vs `20.10 ms` (CLI `95.83` vs `48.20 ms`).
     - `file.apply (batch=100)`: `46.10 ms` vs `35.35 ms`.
   - **Bulk import is the outlier:**
     - `project.init (F10k)` takes `40.38 s` vs `1.72 s` on native SQLite (`1.56 s` on the `docker` worker route).
     - `project.init (F100k)` exceeds the 120 s per-call cap on PostgreSQL (`FAIL` row on both `pg_cli` and `pg_sdk`; its five `F100k` reads are `NOT_RUN`), whereas native SQLite completes in `16.79 s`.

   These numbers include Docker Desktop port forwarding and default container settings; they compare backends within this run and are not directly comparable to the 2026-11-22 report's host setup.

**Change from the 2026-11-22 report:** SDK `file.write (1k)` was `7.44 ms` there and is `18.31 ms` here. Source commit (`54937e6434` → `ca4be0bf3c`), host, and CLI content staging (`--from` instead of stdin) all differ, so this report does not attribute the delta without a same-host A/B run.

## Main Observations & Cleanup

- **CLI vs persistent SDK**: on SQLite `file.stat (F1k)` a fresh CLI process takes `8.525 ms` p50 against `2.126 ms` for the persistent client.
- **PostgreSQL vs SQLite**: persistent client `file.stat (F1k)` `25.106 ms` (PostgreSQL) against `2.126 ms` (SQLite).
- **Docker worker route vs native SQLite**: `file.stat (F1k)` p50 is `3.16 ms` vs `2.126 ms` on persistent SDK, and `5.218 ms` vs `8.525 ms` on fresh-process CLI.
- **Cleanup**: owned SQLite store removed via `layerfs store remove`, PostgreSQL store disconnected via `layerfs store disconnect`, scratch database dropped, docker-machine Store removed, the private home's `docker` machine stopped (`layerfs machine stop docker`), and its owned stopped `layerfs-*-docker` container and `-data` volume released (the Docker daemon and the cached sandbox image left alone), temporary home/fixtures deleted.
