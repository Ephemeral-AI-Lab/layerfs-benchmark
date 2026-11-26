# fs-file-calls — ca4be0bf3c

**PASS (diagnostic warm): measured the mountless LayerFS 2.0 `file.*` + `commit.diff` calls across CLI and persistent `@layerfs/node` SDK on native SQLite (ext4) (file.stat (F1k) p50: SQLite SDK `2.246 ms`, SQLite CLI `8.695 ms`); rows by status: OK 123, REFUSED 4; 80 cold rows registered as INELIGIBLE (no cold claim); fixture and export proofs passed; 4 unavailable routes recorded as NOT_RUN.**

## Configuration & Provenance

| Field | Value |
| --- | --- |
| LayerFS commit | `ca4be0bf3c4e9df47f9b21caca46cdb1faee48fe` |
| CLI binary SHA-256 | `9f1d1e2abd9596624a77567a6ed417f3360c74b70661dac3c8e4e893a80dfc25` |
| Node addon SHA-256 | `d1ec12ae0c15f81a66ebebc07a728cb4001ca8a8fe00773527f126d03126dfec` |
| Host | 13th Gen Intel(R) Core(TM) i9-13900HX, 32 CPUs, 7.8 GiB RAM, kernel 6.6.87.2-microsoft-standard-WSL2 |
| Machine route | `native` (`LAYERFS_TEST_TMPDIR` on ext4); Node SDK arm is a persistent-client exception to "public CLI for every operation" |
| PostgreSQL | NOT_RUN (`--pg-admin-url` not given) |
| Sample sizes | reads `N=15` (F10k/F100k/deeper history capped), writes `N=10`, trees F100, F1k, F10k, F100k, history H1, H50, H100, H1000 |
| Per-call cap | 120 s; a call over it is a FAIL row and the run continues |
| Disk free (GB) | start 851.5, end 851.0 (stop below 25) |
| Cache protocol | warm (declared preconditioning; OS page cache not dropped — labelled diagnostic) |
| Local receipts | `results.json` / `results.csv` under `--output`, not committed (AGENTS.md:64-65) |

## Fixtures (manifest = sha256 over sorted path, size, content sha256)

| Fixture | Files | Bytes | Manifest SHA-256 | Unchanged after write rows |
| --- | ---: | ---: | --- | --- |
| F100 | 100 | 4894 | `e091298ea2f83ce4…` | sqlite: True |
| F1k | 1000 | 49894 | `aafb8b20c3ebaca0…` | sqlite: True |
| F10k | 10000 | 508894 | `3fafd345351ec254…` | sqlite: True |
| F100k | 100000 | 5188894 | `609329791afefb7c…` | sqlite: True |
| sizes | 5 | 17892352 | `a9738398f610334d…` | sqlite: True |
| hist | 1 | 11 | `16239d6e3d6c3a70…` | sqlite: True |

## Latency by Call (p50 / p95 ms, warm diagnostic)

| Case | SQLite SDK p50 / p95 | SQLite CLI p50 / p95 |
| --- | ---: | ---: |
| `file.read (1k)` | 0.57 / 0.86 (n=15) | 6.33 / 6.73 (n=15) |
| `file.read (64k)` | 1.47 / 2.15 (n=15) | 7.57 / 7.97 (n=15) |
| `file.read (1m)` | 1.53 / 1.68 (n=15) | 7.53 / 8.35 (n=15) |
| `file.read (16m_win2000)` | 1.59 / 1.90 (n=15) | 8.23 / 9.48 (n=15) |
| `file.stat (F100)` | 1.74 / 1.89 (n=15) | 7.69 / 8.29 (n=15) |
| `file.list first-page (F100)` | 0.53 / 0.60 (n=15) | 6.45 / 6.81 (n=15) |
| `file.glob (F100)` | 1.71 / 1.97 (n=15) | 10.02 / 10.92 (n=15) |
| `file.grep rare (F100)` | 2.26 / 2.37 (n=15) | 10.60 / 11.06 (n=15) |
| `file.grep frequent (F100)` | 1.85 / 2.21 (n=15) | 9.02 / 9.69 (n=15) |
| `file.stat (F1k)` | 2.25 / 2.62 (n=15) | 8.70 / 9.10 (n=15) |
| `file.list first-page (F1k)` | 0.72 / 0.82 (n=15) | 6.27 / 6.75 (n=15) |
| `file.glob (F1k)` | 2.69 / 3.57 (n=15) | 10.79 / 11.55 (n=15) |
| `file.grep rare (F1k)` | 21.17 / 22.18 (n=15) | 37.27 / 39.85 (n=15) |
| `file.grep frequent (F1k)` | 1.89 / 2.18 (n=15) | 8.73 / 9.59 (n=15) |
| `file.stat (F10k)` | 2.95 / 3.57 (n=10) | 8.76 / 8.84 (n=5) |
| `file.list first-page (F10k)` | 0.73 / 0.90 (n=10) | 6.46 / 6.77 (n=5) |
| `file.glob (F10k)` | 1.55 / 2.12 (n=10) | 7.56 / 7.77 (n=5) |
| `file.grep rare (F10k)` | 243.85 / 255.34 (n=10) | 236.51 / 240.21 (n=5) |
| `file.grep frequent (F10k)` | 1.70 / 2.12 (n=10) | 8.11 / 9.11 (n=5) |
| `file.stat (F100k)` | 2.84 / 3.08 (n=10) | 8.38 / 8.67 (n=5) |
| `file.list first-page (F100k)` | 0.68 / 0.80 (n=10) | 6.33 / 6.64 (n=5) |
| `file.glob (F100k)` | 1.50 / 1.74 (n=10) | 7.35 / 7.46 (n=5) |
| `file.grep rare (F100k)` | 3116.56 / 3196.51 (n=10) | 2984.11 / 3040.31 (n=5) |
| `file.grep frequent (F100k)` | 1.78 / 1.96 (n=10) | 8.14 / 8.22 (n=5) |
| `file.blame (H1, head)` | 0.91 / 1.05 (n=15) | 7.18 / 7.50 (n=15) |
| `file.history (H1, head)` | 1.43 / 1.61 (n=15) | 7.72 / 7.95 (n=15) |
| `file.history (H1, pinned)` | 1.42 / 1.66 (n=15) | 7.33 / 7.71 (n=15) |
| `commit.diff (H1, head)` | 0.68 / 0.76 (n=15) | 6.68 / 7.10 (n=15) |
| `file.blame (H50, head)` | 20.54 / 22.47 (n=10) | 28.55 / 28.83 (n=5) |
| `file.history (H50, head)` | 35.48 / 39.12 (n=10) | 44.15 / 45.22 (n=5) |
| `file.history (H50, pinned)` | 36.53 / 37.62 (n=10) | 43.89 / 44.36 (n=5) |
| `commit.diff (H50, head)` | 0.74 / 0.88 (n=10) | 6.81 / 7.03 (n=5) |
| `file.blame (H100, head)` | 39.64 / 40.52 (n=10) | 50.07 / 50.70 (n=5) |
| `file.history (H100, head)` | 34.90 / 36.31 (n=10) | 44.21 / 392.25 (n=5) |
| `file.history (H100, pinned)` | 34.63 / 35.89 (n=10) | 44.62 / 45.56 (n=5) |
| `commit.diff (H100, head)` | 0.70 / 0.87 (n=10) | 6.84 / 7.52 (n=5) |
| `file.blame (H1000, head)` | 385.13 / 410.58 (n=10) | 418.20 / 426.32 (n=5) |
| `file.history (H1000, head)` | 35.16 / 36.61 (n=10) | 43.33 / 44.20 (n=5) |
| `file.history (H1000, pinned)` | 35.65 / 40.28 (n=10) | 43.55 / 44.76 (n=5) |
| `commit.diff (H1000, head)` | 0.75 / 0.84 (n=10) | 6.42 / 6.59 (n=5) |
| `file.write (0b)` | 19.46 / 21.39 (n=10) | 53.09 / 58.43 (n=10) |
| `file.write (1k)` | 18.83 / 22.25 (n=10) | 48.63 / 50.24 (n=10) |
| `file.write (64k)` | 22.88 / 24.64 (n=10) | 51.73 / 55.03 (n=10) |
| `file.write (1m)` | 19.89 / 20.38 (n=5) | 52.23 / 55.69 (n=3) |
| `file.write (64m)` | 419.24 / 554.39 (n=3) | 200.08 / 334.20 (n=3) |
| `file.edit (small)` | 20.59 / 29.87 (n=10) | 53.62 / 64.98 (n=10) |
| `file.mkdir` | 23.35 / 35.71 (n=10) | 48.00 / 51.45 (n=10) |
| `file.cp (file)` | 20.85 / 24.51 (n=10) | 48.57 / 50.22 (n=10) |
| `file.mv (file)` | 20.93 / 26.45 (n=10) | 46.44 / 48.52 (n=10) |
| `file.rm (file)` | 25.73 / 88.42 (n=10) | 46.97 / 50.92 (n=10) |
| `file.apply (batch=1)` | 20.06 / 22.04 (n=10) | — |
| `file.apply (batch=10)` | 22.33 / 23.93 (n=10) | — |
| `file.apply (batch=100)` | 51.12 / 55.54 (n=5) | — |

## Resources and native dispatch (CLI: per-call rusage; SDK: process deltas per call)

| Case | CLI CPU ms p50 | CLI max RSS MiB | CLI dispatch ms p50 | SDK CPU ms/call | SDK RSS delta MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| `file.read (1k)` | 5.938 | 225.4 | 0.029 | 0.628 | 0.0 |
| `file.read (64k)` | 7.178 | 225.4 | 0.03 | 1.636 | 2.8 |
| `file.read (1m)` | 7.122 | 225.4 | 0.03 | 1.539 | 2.0 |
| `file.read (16m_win2000)` | 7.84 | 225.4 | 0.034 | 1.583 | -0.6 |
| `file.stat (F100)` | 7.432 | 225.4 | 0.029 | 1.729 | 0.0 |
| `file.list first-page (F100)` | 6.348 | 225.4 | 0.031 | 0.516 | 0.0 |
| `file.glob (F100)` | 9.71 | 225.4 | 0.032 | 1.733 | 0.0 |
| `file.grep rare (F100)` | 10.347 | 225.4 | 0.03 | 2.255 | 0.2 |
| `file.grep frequent (F100)` | 8.75 | 225.4 | 0.029 | 1.906 | 0.0 |
| `file.stat (F1k)` | 8.269 | 225.4 | 0.03 | 2.243 | 0.2 |
| `file.list first-page (F1k)` | 6.07 | 225.4 | 0.026 | 0.682 | 0.0 |
| `file.glob (F1k)` | 10.436 | 225.4 | 0.034 | 2.714 | 0.8 |
| `file.grep rare (F1k)` | 36.884 | 225.4 | 0.033 | 21.232 | 1.2 |
| `file.grep frequent (F1k)` | 8.392 | 225.4 | 0.031 | 1.901 | 0.0 |
| `file.stat (F10k)` | 8.318 | 225.4 | 0.03 | 3.037 | 0.0 |
| `file.list first-page (F10k)` | 6.184 | 225.4 | 0.029 | 0.744 | 0.0 |
| `file.glob (F10k)` | 6.88 | 225.4 | 0.026 | 1.623 | 0.0 |
| `file.grep rare (F10k)` | 236.248 | 225.4 | 0.038 | 245.233 | 11.2 |
| `file.grep frequent (F10k)` | 7.764 | 225.4 | 0.03 | 1.774 | 0.0 |
| `file.stat (F100k)` | 8.388 | 225.4 | 0.028 | 2.83 | 0.0 |
| `file.list first-page (F100k)` | 5.62 | 225.4 | 0.025 | 0.691 | 0.0 |
| `file.glob (F100k)` | 6.942 | 225.4 | 0.027 | 1.53 | 0.0 |
| `file.grep rare (F100k)` | 2983.719 | 225.4 | 0.032 | 3126.646 | 4.9 |
| `file.grep frequent (F100k)` | 7.652 | 225.4 | 0.032 | 1.746 | -0.6 |
| `file.blame (H1, head)` | 6.826 | 225.4 | 0.032 | 0.925 | 0.0 |
| `file.history (H1, head)` | 7.377 | 225.4 | 0.031 | 1.421 | 0.0 |
| `file.history (H1, pinned)` | 7.002 | 225.4 | 0.032 | 1.442 | 0.0 |
| `commit.diff (H1, head)` | 6.462 | 225.4 | 0.033 | 0.666 | 0.0 |
| `file.blame (H50, head)` | 28.229 | 225.4 | 0.034 | 20.936 | 0.0 |
| `file.history (H50, head)` | 43.843 | 225.4 | 0.035 | 36.129 | 0.0 |
| `file.history (H50, pinned)` | 43.553 | 225.4 | 0.031 | 36.551 | 0.0 |
| `commit.diff (H50, head)` | 6.688 | 225.4 | 0.03 | 0.738 | 0.0 |
| `file.blame (H100, head)` | 49.602 | 225.4 | 0.032 | 39.37 | 0.0 |
| `file.history (H100, head)` | 43.259 | 225.4 | 0.031 | 34.933 | 0.0 |
| `file.history (H100, pinned)` | 44.247 | 225.4 | 0.032 | 34.71 | 0.0 |
| `commit.diff (H100, head)` | 6.5 | 225.4 | 0.032 | 0.686 | 0.0 |
| `file.blame (H1000, head)` | 415.693 | 225.4 | 0.034 | 383.12 | 0.0 |
| `file.history (H1000, head)` | 43.029 | 225.4 | 0.028 | 35.19 | 0.0 |
| `file.history (H1000, pinned)` | 43.167 | 225.4 | 0.034 | 36.26 | 0.0 |
| `commit.diff (H1000, head)` | 6.159 | 225.4 | 0.031 | 0.714 | 0.0 |
| `file.write (0b)` | 16.264 | 244.0 | 0.053 | 4.162 | 1.2 |
| `file.write (1k)` | 12.705 | 244.0 | 0.049 | 4.145 | 0.0 |
| `file.write (64k)` | 14.19 | 244.0 | 0.074 | 4.973 | 0.5 |
| `file.write (1m)` | 16.352 | 244.0 | 0.367 | 9.534 | 1.2 |
| `file.write (64m)` | 161.557 | 372.0 | 21.157 | 467.814 | 46.8 |
| `file.edit (small)` | 16.714 | 372.0 | 0.053 | 4.343 | 0.0 |
| `file.mkdir` | 13.148 | 372.0 | 0.051 | 6.283 | 0.0 |
| `file.cp (file)` | 13.68 | 372.0 | 0.05 | 6.182 | 0.0 |
| `file.mv (file)` | 13.569 | 372.0 | 0.051 | 5.141 | -65.0 |
| `file.rm (file)` | 13.617 | 372.0 | 0.054 | 5.996 | 0.0 |
| `file.apply (batch=1)` | — | — | UNAVAILABLE | 4.486 | 0.0 |
| `file.apply (batch=10)` | — | — | UNAVAILABLE | 5.885 | 0.0 |
| `file.apply (batch=100)` | — | — | UNAVAILABLE | 22.5 | 0.0 |

Step attribution: native rows carry the `dispatch` step only; `route`, `connect`, `request` are UNAVAILABLE on native. Source: control/crates/layerfs-home/src/trace.rs:24-37 (steps are written only when LAYERFS_TRACE and LAYERFS_TRACE_STEP are both set; the native route writes `step: dispatch` events only, observed in T1).
The step table for worker rows needs the worker route (T6).

## Write Commit Storage Growth

| Write Case | SQLite SDK `delta_stored_bytes` / `delta_size_bytes` | SQLite CLI `delta_stored_bytes` / `delta_size_bytes` |
| --- | --- | --- |
| `file.write (0b)` | 2848 / 12288 | 3234 / 8192 |
| `file.write (1k)` | 2944 / 16384 | 3896 / 16384 |
| `file.write (64k)` | 2956 / 16384 | 3966 / 16384 |
| `file.write (1m)` | 2555 / 0 | 2338 / 4096 |
| `file.write (64m)` | 1531 / 4096 | 2670 / 8192 |

## Limits (one row per probe; cites the source that sets the limit)

| Probe | Arm | Status | Code | ms | Detail | Source |
| --- | --- | --- | --- | ---: | --- | --- |
| `limit: file.write content 16 MiB` | sqlite_cli | OK |  | 123.535 | `{"content_bytes": 16777217}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 64 MiB` | sqlite_cli | OK |  | 438.714 | `{"content_bytes": 67108865}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 256 MiB` | sqlite_cli | OK |  | 1720.203 | `{"content_bytes": 268435457}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.apply 1000 rows` | sqlite_cli | OK |  | 177.895 | `{"rows": 1000}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8191 rows` | sqlite_cli | OK |  | 1035.831 | `{"rows": 8191}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8192 rows` | sqlite_cli | OK |  | 937.507 | `{"rows": 8192}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: commit.diff page limit 1000` | sqlite_cli | OK |  | 329.581 | `{"changed_paths": 8192, "page_limit": 1000, "items": 220, "has_next": true}`  | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: commit.diff page limit 1001` | sqlite_cli | REFUSED | InvalidInput | — | `{}` commit diff: commit.diff: `limit` is 1 to 1000 | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: file.read window 2000 lines` | sqlite_cli | OK |  | 8.777 | `{"lines_asked": 2000, "reply_bytes": 48388, "text_bytes": 47616, "has_next_line": true}`  | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |
| `limit: file.read window 2001 lines` | sqlite_cli | REFUSED | InvalidInput | — | `{}` file read: file.read: `limit` is 1 to 2000 | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |
| `limit: file.write content 16 MiB` | sqlite_sdk | OK |  | 122.568 | `{"content_bytes": 16777217}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 64 MiB` | sqlite_sdk | OK |  | 492.495 | `{"content_bytes": 67108865}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.write content 256 MiB` | sqlite_sdk | OK |  | 2191.947 | `{"content_bytes": 268435457}`  | core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction); core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches) |
| `limit: file.apply 1000 rows` | sqlite_sdk | OK |  | 125.353 | `{"rows": 1000}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8191 rows` | sqlite_sdk | OK |  | 1015.016 | `{"rows": 8191}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: file.apply 8192 rows` | sqlite_sdk | OK |  | 913.627 | `{"rows": 8192}`  | core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows); engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal) |
| `limit: commit.diff page limit 1000` | sqlite_sdk | OK |  | 348.937 | `{"changed_paths": 8192, "page_limit": 1000, "items": 220, "has_next": true}`  | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: commit.diff page limit 1001` | sqlite_sdk | REFUSED | InvalidInput | — | `{}` commit.diff: `limit` is 1 to 1000 | engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput); engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity) |
| `limit: file.read window 2000 lines` | sqlite_sdk | OK |  | 2.093 | `{"lines_asked": 2000, "reply_bytes": 48387, "text_bytes": 47616, "has_next_line": true}`  | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |
| `limit: file.read window 2001 lines` | sqlite_sdk | REFUSED | InvalidInput | — | `{}` file.read: `limit` is 1 to 2000 | control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput); engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000) |

## Cold rows

Cold rows are registered per read case and gated by `shared/src/measure.py:181 assess_cache`; none is measured, none is labelled cold (`shared/AGENTS.md:7`).

| Arm | Cold rows | Status | Required domains | Reason |
| --- | ---: | --- | --- | --- |
| sqlite_cli | 40 | INELIGIBLE | layerfs-daemon-worker, filesystem-metadata, host-page-cache | No implemented, demonstrated owned cold-cache enforcement and residency protocol for this route/phase. Fresh CLI process/mount, distinct database and copied fixture do not prove coldness. |
| sqlite_sdk | 40 | INELIGIBLE | layerfs-daemon-worker, filesystem-metadata, host-page-cache | No implemented, demonstrated owned cold-cache enforcement and residency protocol for this route/phase. Fresh CLI process/mount, distinct database and copied fixture do not prove coldness. |

## Rows that are not OK (REFUSED / FAIL / NOT_RUN)

none

## Concurrency & Refusals (CLI Process-per-Call)

| Backend | Workload | OK / Total | Throughput (calls/s) | Refusals by Code |
| --- | --- | ---: | ---: | --- |
| SQLite | CLI readers x1 | 8 / 8 | 106.64 | `none` |
| SQLite | CLI readers x4 | 32 / 32 | 361.41 | `none` |
| SQLite | CLI readers x8 | 64 / 64 | 545.48 | `none` |
| SQLite | CLI writers x4 (separate branches) | 16 / 16 | 95.6 | `none` |
| SQLite | CLI writers x4 (same branch) | 16 / 16 | 68.93 | `none` |

## Registered NOT_RUN Routes

| Route | Status & Reason |
| --- | --- |
| `worker:docker` | NOT_RUN: Docker daemon unavailable on this non-root Linux host |
| `worker:lima` | NOT_RUN: Lima VM unavailable on this Linux host |
| `worker:apple-container` | NOT_RUN: macOS-only route |
| `native:postgresql` | NOT_RUN: --pg-admin-url not given |

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
5. **What does PostgreSQL cost against SQLite for each call?** NOT_RUN in this report, because no PostgreSQL server was available. The 2026-11-22 report (`54937e6434`, PostgreSQL 18.6) measured it on another host.

**Change from the 2026-11-22 report:** SDK `file.write (1k)` was 7.4 ms there and is 18.8 ms here. The source (`54937e6434` → `ca4be0bf3c`), the host and the CLI content transport (`--from` instead of stdin) all differ, so this report does not attribute the change. A same-host A/B run of the two commits would settle it.

## Main Observations & Cleanup

- **CLI vs persistent SDK**: on SQLite `file.stat (F1k)` a fresh CLI process takes `8.695 ms` p50 against `2.246 ms` for the persistent client.
- **Cleanup**: owned SQLite store removed via `layerfs store remove`, temporary home/fixtures deleted.
