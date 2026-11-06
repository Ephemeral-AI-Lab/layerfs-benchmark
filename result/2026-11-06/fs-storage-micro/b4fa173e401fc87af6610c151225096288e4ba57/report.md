# fs-storage-micro — b4fa173e40

**16 of 16 fs-storage-micro rows PASS with verified final state; repeat M03/docker/postgresql/r2: page-granular Store bytes identical in this repeat, total +0 B, per-Commit new_stored ±16 B; repeat M03/docker/sqlite/r2: Store pages DIFFER, total -98,800 B, per-Commit new_stored ±20 B; final cleanup COMPLETE.**

Store bytes for eight single-mechanism workloads on LayerFS 2.0 (Docker machine, SQLite and PostgreSQL Stores), measured at a quiesced boundary through the public CLI. Bytes are reported against each case's expected result, not gated by it. Bytes are exact integers. MB = 10⁶ B; MiB = 2²⁰ B = 1,048,576 B. Wall times are INELIGIBLE diagnostics, never speed claims.

## Raw vs stored

**Raw** is Σ logical: the bytes of every committed snapshot, as if each were stored in full. **Stored** is the net Store bytes (SQLite: file + WAL; PostgreSQL: schema). **Raw ÷ stored** is the overall reduction, = exact dedup × delta + zstd ÷ Store overhead: **exact dedup** = raw ÷ Σ new_canonical (identical files, chunks and trees stored once); **delta + zstd** = Σ new_canonical ÷ Σ new_stored (delta encoding and compression of the new objects); **Store overhead** = stored ÷ Σ new_stored (database pages, indexes and free space around the packs; 1.35 means the Store is 35% larger than its packs).

| Case | Database | Raw (MB) | Stored (MB) | Raw ÷ stored (×) | Exact dedup (×) | Delta + zstd (×) | Store overhead (×) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| M01 | SQLite | 20.6 | 27.3 | 0.76 | 0.94 | 1.05 | 1.31 |
| M01 | PostgreSQL | 20.6 | 30.1 | 0.69 | 0.94 | 1.05 | 1.45 |
| M02 | SQLite | 600.0 | 39.1 | 15.34 | 11.90 | 1.45 | 1.12 |
| M02 | PostgreSQL | 600.0 | 37.7 | 15.90 | 11.90 | 1.45 | 1.08 |
| M03 | SQLite | 85.7 | 6.9 | 12.39 | 1.00 | 21.17 | 1.70 |
| M03 | PostgreSQL | 85.7 | 5.2 | 16.43 | 1.00 | 21.17 | 1.29 |
| M04 | SQLite | 85.7 | 11.4 | 7.55 | 1.00 | 11.53 | 1.52 |
| M04 | PostgreSQL | 85.7 | 9.5 | 9.04 | 1.00 | 11.53 | 1.27 |
| M05 | SQLite | 85.7 | 11.4 | 7.54 | 1.00 | 11.53 | 1.52 |
| M05 | PostgreSQL | 85.7 | 9.5 | 9.05 | 1.00 | 11.53 | 1.27 |
| M06 | SQLite | 404.8 | 71.3 | 5.68 | 5.90 | 1.00 | 1.04 |
| M06 | PostgreSQL | 404.8 | 72.0 | 5.62 | 5.90 | 1.00 | 1.05 |
| M07 | SQLite | 402.7 | 98.0 | 4.11 | 2.99 | 1.45 | 1.05 |
| M07 | PostgreSQL | 402.7 | 98.2 | 4.10 | 2.99 | 1.45 | 1.06 |
| M08 | SQLite | 402.5 | 31.9 | 12.63 | 3.21 | 4.35 | 1.10 |
| M08 | PostgreSQL | 402.5 | 33.1 | 12.14 | 3.21 | 4.35 | 1.15 |

## Configuration

| Item | Value |
| --- | --- |
| LayerFS source | `b4fa173e401fc87af6610c151225096288e4ba57` (`layerfs_v2_0_0`) |
| CLI / daemon (macOS, release) | `69d320f8f9fe86bf78ac18ab7c1a9c0e44c933b2c2493763bd2282e1dff9a348` / `e04a45593a206338696fd7748f205a272f46ebb754e4b49c40aeb0953ce70000` |
| Linux bundle seal | `a8c8daf34097cc61e21ac07b6f5de32b76a7c4a485601ee7c8d6668a2c612d37` |
| Sandbox image | `sha256:ede53683cd218d267ff5368c4fd3ee76bea360ab9efe984814fc776587732aae (fs-storage-micro:b4fa173e)` (FROM runtime `sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e`) |
| Machine | Docker (`docker`), private `LAYERFS_HOME`, `LAYERFS_CONSTRUCTION_WORKERS=1` |
| PostgreSQL | postgres:17-bookworm sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652, 1 CPU / 512 MiB, 127.0.0.1:55484; one pre-created empty database per row; `--synchronous-commit off` |
| Workload | `fs-storage-micro-v1`, generator `image/gen.py` SHA-256 `9efa7744f4bce76933ad1db066da53f7e723a08f7dfa9f50caf17b2b3ec3031d` |
| Pins | `src/pins.json` SHA-256 `0b2b57732ae89b8bc49e230990d31b99e9eaf618765c529e6c86dbf815f872e1` (oracles and references) |
| Storage policy (fixed in 2.0) | GEAR 8/16/32 KiB (min/avg/max) for files of 128 KiB and up; delta depth caps 16/8/8 (whole file/chunk/metadata); per-object zstd level 3 |
| Store bytes | SQLite: `store status` `file.bytes` + `file.wal_bytes`; allocated = st_blocks×512 of `store.sqlite` + `-wal` in the worker volume. PostgreSQL: `server.schemas.layerfs` |
| Floor | the row's own Store after create/connect + `project init` of an empty folder (+ `store push` for SQLite), before any fork |

## Rows

| Row | Execution | Final-state verification | Cleanup | Commits | Wall s (INELIGIBLE) | Reason |
| --- | --- | --- | --- | --- | ---: | --- |
| M01/docker/sqlite | PASS | PASS | COMPLETE | 1 | 14.0 |  |
| M01/docker/postgresql | PASS | PASS | COMPLETE | 1 | 27.5 |  |
| M02/docker/sqlite | PASS | PASS | COMPLETE | 2 | 32.3 |  |
| M02/docker/postgresql | PASS | PASS | COMPLETE | 2 | 20.1 |  |
| M03/docker/sqlite | PASS | PASS | COMPLETE | 21 | 20.1 |  |
| M03/docker/sqlite/r2 | PASS | PASS | COMPLETE | 21 | 27.4 |  |
| M03/docker/postgresql | PASS | PASS | COMPLETE | 21 | 42.9 |  |
| M03/docker/postgresql/r2 | PASS | PASS | COMPLETE | 21 | 32.0 |  |
| M04/docker/sqlite | PASS | PASS | COMPLETE | 21 | 21.3 |  |
| M04/docker/postgresql | PASS | PASS | COMPLETE | 21 | 26.5 |  |
| M05/docker/sqlite | PASS | PASS | COMPLETE | 21 | 21.0 |  |
| M05/docker/postgresql | PASS | PASS | COMPLETE | 21 | 34.6 |  |
| M06/docker/sqlite | PASS | PASS | COMPLETE | 6 | 13.7 |  |
| M06/docker/postgresql | PASS | PASS | COMPLETE | 6 | 14.2 |  |
| M07/docker/sqlite | PASS | PASS | COMPLETE | 3 | 11.3 |  |
| M07/docker/postgresql | PASS | PASS | COMPLETE | 3 | 15.2 |  |
| M08/docker/sqlite | PASS | PASS | COMPLETE | 12 | 279.9 |  |
| M08/docker/postgresql | PASS | PASS | COMPLETE | 12 | 312.8 |  |

## Store bytes

| Case | Database | Outcome | Floor (B) | Final (B) | Net (B) | Net (MB) | Net (MiB) | Net file (B) | Net WAL (B) | Net allocated (B) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| M01 | SQLite | PASS | 212,992 | 27,529,216 | 27,316,224 | 27.316 | 26.051 | 23,121,920 | 4,194,304 | 27,320,320 |
| M01 | PostgreSQL | PASS | 753,664 | 30,818,304 | 30,064,640 | 30.065 | 28.672 | — | — | — |
| M02 | SQLite | PASS | 212,992 | 39,329,792 | 39,116,800 | 39.117 | 37.305 | 34,922,496 | 4,194,304 | 39,116,800 |
| M02 | PostgreSQL | PASS | 753,664 | 38,477,824 | 37,724,160 | 37.724 | 35.977 | — | — | — |
| M03 | SQLite | PASS | 212,992 | 7,131,136 | 6,918,144 | 6.918 | 6.598 | 2,723,840 | 4,194,304 | 6,918,144 |
| M03 | PostgreSQL | PASS | 753,664 | 5,971,968 | 5,218,304 | 5.218 | 4.977 | — | — | — |
| M04 | SQLite | PASS | 212,992 | 11,571,200 | 11,358,208 | 11.358 | 10.832 | 7,163,904 | 4,194,304 | 11,358,208 |
| M04 | PostgreSQL | PASS | 753,664 | 10,231,808 | 9,478,144 | 9.478 | 9.039 | — | — | — |
| M05 | SQLite | PASS | 212,992 | 11,575,296 | 11,362,304 | 11.362 | 10.836 | 7,168,000 | 4,194,304 | 11,362,304 |
| M05 | PostgreSQL | PASS | 753,664 | 10,223,616 | 9,469,952 | 9.470 | 9.031 | — | — | — |
| M06 | SQLite | PASS | 212,992 | 71,524,352 | 71,311,360 | 71.311 | 68.008 | 67,117,056 | 4,194,304 | 71,315,456 |
| M06 | PostgreSQL | PASS | 753,664 | 72,777,728 | 72,024,064 | 72.024 | 68.688 | — | — | — |
| M07 | SQLite | PASS | 212,992 | 98,242,560 | 98,029,568 | 98.030 | 93.488 | 93,835,264 | 4,194,304 | 98,033,664 |
| M07 | PostgreSQL | PASS | 753,664 | 98,926,592 | 98,172,928 | 98.173 | 93.625 | — | — | — |
| M08 | SQLite | PASS | 212,992 | 32,092,160 | 31,879,168 | 31.879 | 30.402 | 27,684,864 | 4,194,304 | 31,883,264 |
| M08 | PostgreSQL | PASS | 753,664 | 33,898,496 | 33,144,832 | 33.145 | 31.609 | — | — | — |

## Per-Commit attribution

`logical` is each Commit's whole-tree size, so Σ logical sums the states. In LayerFS 2.0 `new_stored` counts all new pack bytes and `new_metadata` is its metadata-domain subset, so payload = stored − metadata and **net − Σ new_stored** is what no Commit's packs account for (database pages, indexes, free space, the SQLite WAL). The spec's unattributed = net − (Σ new_stored + Σ new_metadata) counts metadata twice; it is shown for comparability only.

| Case | Database | Commits | Σ logical (B) | Σ new_canonical (B) | Σ new_stored (B) | Σ new_metadata (B) | Σ payload = stored − metadata (B) | Net (B) | Net − Σ new_stored (B) | Spec unattributed (B) | Logical ÷ net |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| M01 | SQLite | 1 | 20,647,445 | 21,908,867 | 20,785,320 | 82,317 | 20,703,003 | 27,316,224 | +6,530,904 | +6,448,587 | 0.76 |
| M01 | PostgreSQL | 1 | 20,647,445 | 21,908,867 | 20,785,328 | 82,325 | 20,703,003 | 30,064,640 | +9,279,312 | +9,196,987 | 0.69 |
| M02 | SQLite | 2 | 600,000,000 | 50,426,618 | 34,836,446 | 116,433 | 34,720,013 | 39,116,800 | +4,280,354 | +4,163,921 | 15.34 |
| M02 | PostgreSQL | 2 | 600,000,000 | 50,426,618 | 34,836,449 | 116,436 | 34,720,013 | 37,724,160 | +2,887,711 | +2,771,275 | 15.90 |
| M03 | SQLite | 21 | 85,718,215 | 85,964,901 | 4,060,694 | 18,442 | 4,042,252 | 6,918,144 | +2,857,450 | +2,839,008 | 12.39 |
| M03 | PostgreSQL | 21 | 85,718,215 | 85,964,901 | 4,060,696 | 18,444 | 4,042,252 | 5,218,304 | +1,157,608 | +1,139,164 | 16.43 |
| M04 | SQLite | 21 | 85,718,215 | 86,009,701 | 7,462,743 | 26,148 | 7,436,595 | 11,358,208 | +3,895,465 | +3,869,317 | 7.55 |
| M04 | PostgreSQL | 21 | 85,718,215 | 86,009,701 | 7,462,731 | 26,136 | 7,436,595 | 9,478,144 | +2,015,413 | +1,989,277 | 9.04 |
| M05 | SQLite | 21 | 85,718,215 | 86,018,101 | 7,462,923 | 26,328 | 7,436,595 | 11,362,304 | +3,899,381 | +3,873,053 | 7.54 |
| M05 | PostgreSQL | 21 | 85,718,215 | 86,018,101 | 7,462,938 | 26,343 | 7,436,595 | 9,469,952 | +2,007,014 | +1,980,671 | 9.05 |
| M06 | SQLite | 6 | 404,750,344 | 68,621,666 | 68,440,097 | 199,629 | 68,240,468 | 71,311,360 | +2,871,263 | +2,671,634 | 5.68 |
| M06 | PostgreSQL | 6 | 404,750,344 | 68,621,666 | 68,440,099 | 199,631 | 68,240,468 | 72,024,064 | +3,583,965 | +3,384,334 | 5.62 |
| M07 | SQLite | 3 | 402,653,184 | 134,684,385 | 92,963,117 | 242,493 | 92,720,624 | 98,029,568 | +5,066,451 | +4,823,958 | 4.11 |
| M07 | PostgreSQL | 3 | 402,653,184 | 134,684,385 | 92,963,117 | 242,493 | 92,720,624 | 98,172,928 | +5,209,811 | +4,967,318 | 4.10 |
| M08 | SQLite | 12 | 402,505,728 | 125,539,131 | 28,877,854 | 2,196,591 | 26,681,263 | 31,879,168 | +3,001,314 | +804,723 | 12.63 |
| M08 | PostgreSQL | 12 | 402,505,728 | 125,539,131 | 28,877,853 | 2,196,590 | 26,681,263 | 33,144,832 | +4,266,979 | +2,070,389 | 12.14 |

## References

Computed offline once per workload version from the same generator's states (pinned in `src/pins.json`). The CDC oracle is approximate: its gear table and masks differ from LayerFS's.

| Case | Whole-file unique (B) | Σ tar\|zstd-3 (B) | Git pack+idx (B) | CDC oracle, approx. (B) |
| --- | ---: | ---: | ---: | ---: |
| M01 | 20,647,445 | 20,891,541 | 21,314,353 | 20,647,445 |
| M02 | 50,000,000 | 396,879,583 | 33,444,866 | 34,607,799 |
| M03 | 85,718,215 | 26,316,489 | 2,457,557 | 30,832,515 |
| M04 | 85,718,215 | 26,316,489 | 2,457,557 | 30,832,515 |
| M05 | 85,718,215 | 26,316,957 | 30,268,553 | 30,832,515 |
| M06 | 404,750,344 | 404,762,832 | 68,194,222 | 68,256,206 |
| M07 | 201,326,592 | 221,762,925 | 88,915,283 | 92,435,496 |
| M08 | 402,505,728 | 132,242,533 | 13,001,168 | 101,912,518 |

| Case | Database | Net (B) | Net ÷ whole-file unique | Net ÷ Σ tar\|zstd-3 | Net ÷ Git pack+idx | Net ÷ CDC oracle (approx.) |
| --- | --- | ---: | --- | --- | --- | ---: |
| M01 | SQLite | 27,316,224 | 1.323 | 1.308 | 1.282 | 1.323 |
| M01 | PostgreSQL | 30,064,640 | 1.456 | 1.439 | 1.411 | 1.456 |
| M02 | SQLite | 39,116,800 | 0.782 | 0.099 | 1.170 | 1.130 |
| M02 | PostgreSQL | 37,724,160 | 0.754 | 0.095 | 1.128 | 1.090 |
| M03 | SQLite | 6,918,144 | 0.081 | 0.263 | 2.815 | 0.224 |
| M03 | PostgreSQL | 5,218,304 | 0.061 | 0.198 | 2.123 | 0.169 |
| M04 | SQLite | 11,358,208 | 0.133 | 0.432 | 4.622 | 0.368 |
| M04 | PostgreSQL | 9,478,144 | 0.111 | 0.360 | 3.857 | 0.307 |
| M05 | SQLite | 11,362,304 | 0.133 | 0.432 | 0.375 | 0.369 |
| M05 | PostgreSQL | 9,469,952 | 0.110 | 0.360 | 0.313 | 0.307 |
| M06 | SQLite | 71,311,360 | 0.176 | 0.176 | 1.046 | 1.045 |
| M06 | PostgreSQL | 72,024,064 | 0.178 | 0.178 | 1.056 | 1.055 |
| M07 | SQLite | 98,029,568 | 0.487 | 0.442 | 1.103 | 1.061 |
| M07 | PostgreSQL | 98,172,928 | 0.488 | 0.443 | 1.104 | 1.062 |
| M08 | SQLite | 31,879,168 | 0.079 | 0.241 | 2.452 | 0.313 |
| M08 | PostgreSQL | 33,144,832 | 0.082 | 0.251 | 2.549 | 0.325 |

## Cases

### M01 tiny files

- **Workload:** 10,000 files of 0–4,096 B (uniform, SHAKE-256 bytes) in 100 directories.
- **Write method:** new path; Commits: 1.
- **Expected:** net bytes ÷ 10,000 = overhead per small file.
- **Actual, SQLite:** net ÷ 10,000 = 2,731.6 B per file; new_stored 20,785,320 B for 20,647,445 B logical; (net − new_stored) ÷ 10,000 = 653.1 B per file.
- **Actual, PostgreSQL:** net ÷ 10,000 = 3,006.5 B per file; new_stored 20,785,328 B for 20,647,445 B logical; (net − new_stored) ÷ 10,000 = 927.9 B per file.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 20,647,445 | 20,785,320 | 82,317 | 20,785,328 | 82,325 |

### M02 duplicates

- **Workload:** one 50,000,000 B tree (200 files, half synthetic text, half random), then 10 copies at new paths.
- **Write method:** new path (copies read base/ and write new files); Commits: 2.
- **Expected:** second Commit stores only tree/metadata (≈0 payload).
- **Actual, SQLite:** Commit 1 new_stored 34,820,177 B (payload 34,720,013 B); Commit 2 (500,000,000 B of copies) new_stored 16,269 B, new_metadata 16,269 B, payload 0 B.
- **Actual, PostgreSQL:** Commit 1 new_stored 34,820,174 B (payload 34,720,013 B); Commit 2 (500,000,000 B of copies) new_stored 16,275 B, new_metadata 16,275 B, payload 0 B.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 50,000,000 | 34,820,177 | 100,164 | 34,820,174 | 100,161 |
| 2 | 550,000,000 | 16,269 | 16,269 | 16,275 | 16,275 |

### M03 in-place edits

- **Workload:** 100 synthetic text files of 16–64 KiB; 20 Commits each replacing 1% of lines in every file.
- **Write method:** in-place rewrite (same inode, O_WRONLY|O_TRUNC); Commits: 21.
- **Expected:** deltas against the previous version; the chain passes depth 16 (a fuller object re-stored).
- **Actual, SQLite:** Commit 1 new_stored 1,457,782 B; 20 edit Commits Σ 2,602,912 B (mean 130,146 B, largest 404,887 B at Commit 17); Σ new_metadata 18,442 B.
- **Actual, PostgreSQL:** Commit 1 new_stored 1,457,778 B; 20 edit Commits Σ 2,602,918 B (mean 130,146 B, largest 404,890 B at Commit 17); Σ new_metadata 18,444 B.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 4,080,060 | 1,457,782 | 1,142 | 1,457,778 | 1,138 |
| 2 | 4,081,201 | 30,790 | 818 | 30,788 | 816 |
| 3 | 4,081,398 | 30,470 | 860 | 30,464 | 854 |
| 4 | 4,080,719 | 30,491 | 889 | 30,495 | 893 |
| 5 | 4,081,684 | 30,979 | 883 | 30,980 | 884 |
| 6 | 4,082,545 | 30,513 | 870 | 30,510 | 867 |
| 7 | 4,081,352 | 30,496 | 872 | 30,499 | 875 |
| 8 | 4,081,814 | 96,574 | 881 | 96,573 | 880 |
| 9 | 4,082,151 | 371,682 | 877 | 371,680 | 875 |
| 10 | 4,082,030 | 183,032 | 799 | 183,036 | 803 |
| 11 | 4,083,059 | 240,031 | 878 | 240,046 | 893 |
| 12 | 4,082,562 | 140,548 | 883 | 140,548 | 883 |
| 13 | 4,082,014 | 118,227 | 876 | 118,233 | 882 |
| 14 | 4,081,968 | 71,071 | 875 | 71,067 | 871 |
| 15 | 4,081,399 | 117,215 | 876 | 117,210 | 871 |
| 16 | 4,081,846 | 146,754 | 880 | 146,756 | 882 |
| 17 | 4,081,701 | 404,887 | 879 | 404,890 | 882 |
| 18 | 4,082,665 | 91,955 | 871 | 91,956 | 872 |
| 19 | 4,082,049 | 165,945 | 765 | 165,945 | 765 |
| 20 | 4,082,106 | 48,458 | 882 | 48,448 | 872 |
| 21 | 4,081,892 | 222,794 | 886 | 222,794 | 886 |

### M04 rename-over edits

- **Workload:** same content sequence as M03.
- **Write method:** write temp file then rename over the old path; Commits: 21.
- **Expected:** compare with M03 (rename-over also deltas against the previous version).
- **Actual, SQLite:** Commit 1 new_stored 1,457,777 B; 20 edit Commits Σ 6,004,966 B (mean 300,248 B, largest 429,890 B at Commit 21); Σ new_metadata 26,148 B.
- **Actual, PostgreSQL:** Commit 1 new_stored 1,457,782 B; 20 edit Commits Σ 6,004,949 B (mean 300,247 B, largest 429,890 B at Commit 21); Σ new_metadata 26,136 B.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 4,080,060 | 1,457,777 | 1,137 | 1,457,782 | 1,142 |
| 2 | 4,081,201 | 225,312 | 1,108 | 225,312 | 1,108 |
| 3 | 4,081,398 | 180,626 | 1,225 | 180,627 | 1,226 |
| 4 | 4,080,719 | 196,923 | 1,217 | 196,924 | 1,218 |
| 5 | 4,081,684 | 213,645 | 1,257 | 213,644 | 1,256 |
| 6 | 4,082,545 | 229,599 | 1,245 | 229,599 | 1,245 |
| 7 | 4,081,352 | 245,269 | 1,245 | 245,268 | 1,244 |
| 8 | 4,081,814 | 261,791 | 1,275 | 261,789 | 1,273 |
| 9 | 4,082,151 | 262,610 | 1,247 | 262,597 | 1,234 |
| 10 | 4,082,030 | 277,796 | 1,274 | 277,798 | 1,276 |
| 11 | 4,083,059 | 294,278 | 1,277 | 294,275 | 1,274 |
| 12 | 4,082,562 | 292,026 | 1,258 | 292,027 | 1,259 |
| 13 | 4,082,014 | 306,223 | 1,277 | 306,219 | 1,273 |
| 14 | 4,081,968 | 320,586 | 1,242 | 320,586 | 1,242 |
| 15 | 4,081,399 | 333,825 | 1,261 | 333,833 | 1,269 |
| 16 | 4,081,846 | 348,023 | 1,286 | 348,023 | 1,286 |
| 17 | 4,081,701 | 377,015 | 1,260 | 377,015 | 1,260 |
| 18 | 4,082,665 | 390,060 | 1,273 | 390,054 | 1,267 |
| 19 | 4,082,049 | 403,148 | 1,254 | 403,150 | 1,256 |
| 20 | 4,082,106 | 416,321 | 1,259 | 416,319 | 1,257 |
| 21 | 4,081,892 | 429,890 | 1,271 | 429,890 | 1,271 |

### M05 new-path edits

- **Workload:** same content sequence as M03; version v at fNNN.vVV.txt.
- **Write method:** new path per version, old path unlinked; Commits: 21.
- **Expected:** similarity ring only; compare with M03.
- **Actual, SQLite:** Commit 1 new_stored 1,457,786 B; 20 edit Commits Σ 6,005,137 B (mean 300,257 B, largest 429,899 B at Commit 21); Σ new_metadata 26,328 B.
- **Actual, PostgreSQL:** Commit 1 new_stored 1,457,787 B; 20 edit Commits Σ 6,005,151 B (mean 300,258 B, largest 429,908 B at Commit 21); Σ new_metadata 26,343 B.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 4,080,060 | 1,457,786 | 1,146 | 1,457,787 | 1,147 |
| 2 | 4,081,201 | 225,317 | 1,113 | 225,316 | 1,112 |
| 3 | 4,081,398 | 180,632 | 1,231 | 180,630 | 1,229 |
| 4 | 4,080,719 | 196,938 | 1,232 | 196,941 | 1,235 |
| 5 | 4,081,684 | 213,653 | 1,265 | 213,653 | 1,265 |
| 6 | 4,082,545 | 229,608 | 1,254 | 229,612 | 1,258 |
| 7 | 4,081,352 | 245,275 | 1,251 | 245,277 | 1,253 |
| 8 | 4,081,814 | 261,796 | 1,280 | 261,799 | 1,283 |
| 9 | 4,082,151 | 262,620 | 1,257 | 262,608 | 1,245 |
| 10 | 4,082,030 | 277,807 | 1,285 | 277,805 | 1,283 |
| 11 | 4,083,059 | 294,284 | 1,283 | 294,284 | 1,283 |
| 12 | 4,082,562 | 292,018 | 1,250 | 292,023 | 1,255 |
| 13 | 4,082,014 | 306,235 | 1,289 | 306,237 | 1,291 |
| 14 | 4,081,968 | 320,597 | 1,253 | 320,598 | 1,254 |
| 15 | 4,081,399 | 333,839 | 1,275 | 333,842 | 1,278 |
| 16 | 4,081,846 | 348,027 | 1,290 | 348,032 | 1,295 |
| 17 | 4,081,701 | 377,026 | 1,271 | 377,024 | 1,269 |
| 18 | 4,082,665 | 390,071 | 1,284 | 390,073 | 1,286 |
| 19 | 4,082,049 | 403,158 | 1,264 | 403,153 | 1,259 |
| 20 | 4,082,106 | 416,337 | 1,275 | 416,336 | 1,274 |
| 21 | 4,081,892 | 429,899 | 1,280 | 429,908 | 1,289 |

### M06 large file

- **Workload:** 64 MiB random file; insert 1 B at start; insert 1 B at middle; overwrite 4 KiB at middle; append 1 MiB; delete first byte.
- **Write method:** in-place rewrite (same inode, O_WRONLY|O_TRUNC); Commits: 6.
- **Expected:** each edit adds ≈1–2 chunks (≤64 KiB), except append (≈1 MiB).
- **Actual, SQLite:** new_stored (payload = stored − metadata): base 67,302,166 B (67,181,341 B); insert start 6,092 B (54 B); insert middle 17,331 B (183 B); overwrite 4 KiB 40,775 B (8,277 B); append 1 MiB 1,067,474 B (1,050,505 B); delete first 6,259 B (108 B).
- **Actual, PostgreSQL:** new_stored (payload = stored − metadata): base 67,302,166 B (67,181,341 B); insert start 6,092 B (54 B); insert middle 17,331 B (183 B); overwrite 4 KiB 40,775 B (8,277 B); append 1 MiB 1,067,476 B (1,050,505 B); delete first 6,259 B (108 B).

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 67,108,864 | 67,302,166 | 120,825 | 67,302,166 | 120,825 |
| 2 | 67,108,865 | 6,092 | 6,038 | 6,092 | 6,038 |
| 3 | 67,108,866 | 17,331 | 17,148 | 17,331 | 17,148 |
| 4 | 67,108,866 | 40,775 | 32,498 | 40,775 | 32,498 |
| 5 | 68,157,442 | 1,067,474 | 16,969 | 1,067,476 | 16,971 |
| 6 | 68,157,441 | 6,259 | 6,151 | 6,259 | 6,151 |

### M07 compressibility

- **Workload:** 64 MiB random, 64 MiB zeros, 64 MiB synthetic text; one file per Commit.
- **Write method:** new path; Commits: 3.
- **Expected:** random ≈64 MiB stored raw, zeros ≈0, text at the zstd-3 ratio.
- **Actual, SQLite:** payload (stored − metadata): random 67,181,294 B (1.0011 × 64 MiB); zeros 76 B; text 25,539,254 B vs whole-file zstd -3 20,412,198 B (1.251×); metadata 120,840 / 684 / 120,969 B.
- **Actual, PostgreSQL:** payload (stored − metadata): random 67,181,294 B (1.0011 × 64 MiB); zeros 76 B; text 25,539,254 B vs whole-file zstd -3 20,412,198 B (1.251×); metadata 120,840 / 684 / 120,969 B.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 67,108,864 | 67,302,134 | 120,840 | 67,302,134 | 120,840 |
| 2 | 134,217,728 | 760 | 684 | 760 | 684 |
| 3 | 201,326,592 | 25,660,223 | 120,969 | 25,660,223 | 120,969 |

### M08 SQLite churn

- **Workload:** SQLite database of 147,000 rows (33,542,144 B, page 4,096); 10 Commits each updating 1% of rows (same-length values); then VACUUM.
- **Write method:** in-place (SQLite page writes, rollback journal); Commits: 12.
- **Expected:** page-local churn reuses most chunks; VACUUM reshuffles.
- **Actual, SQLite:** create 13,947,277 B; 10 update Commits Σ 6,759,673 B (mean 675,967 B); VACUUM 8,170,904 B.
- **Actual, PostgreSQL:** create 13,947,277 B; 10 update Commits Σ 6,759,672 B (mean 675,967 B); VACUUM 8,170,904 B.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 33,542,144 | 13,947,277 | 60,419 | 13,947,277 | 60,419 |
| 2 | 33,542,144 | 497,697 | 110,491 | 497,697 | 110,491 |
| 3 | 33,542,144 | 556,743 | 148,545 | 556,743 | 148,545 |
| 4 | 33,542,144 | 613,114 | 176,511 | 613,114 | 176,511 |
| 5 | 33,542,144 | 627,640 | 199,278 | 627,641 | 199,279 |
| 6 | 33,542,144 | 681,982 | 216,698 | 681,982 | 216,698 |
| 7 | 33,542,144 | 723,465 | 230,205 | 723,463 | 230,203 |
| 8 | 33,542,144 | 735,402 | 240,210 | 735,402 | 240,210 |
| 9 | 33,542,144 | 769,781 | 247,328 | 769,781 | 247,328 |
| 10 | 33,542,144 | 778,867 | 252,124 | 778,867 | 252,124 |
| 11 | 33,542,144 | 774,982 | 254,973 | 774,982 | 254,973 |
| 12 | 33,542,144 | 8,170,904 | 59,809 | 8,170,904 | 59,809 |

## PostgreSQL server WAL

Server-wide `pg_current_wal_lsn()` advance between the floor and final probes (owning-container admin command; this server served only these rows, serially). It is not part of Store bytes.

| Case | Schema net (B) | Server WAL floor→final (B) |
| --- | ---: | ---: |
| M01 | 30,064,640 | 36,840,704 |
| M02 | 37,724,160 | 39,457,720 |
| M03 | 5,218,304 | 6,118,480 |
| M04 | 9,478,144 | 10,730,064 |
| M05 | 9,469,952 | 11,100,424 |
| M06 | 72,024,064 | 74,662,680 |
| M07 | 98,172,928 | 102,589,632 |
| M08 | 33,144,832 | 37,126,144 |

## Determinism

| Repeat | Pages first (B) | Pages repeat (B) | Final first (B) | Final repeat (B) | Max per-Commit Δ new_stored (B) | Max per-Commit Δ new_metadata (B) | new_canonical and logical identical | Per-Commit payload identical | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| M03/docker/postgresql/r2 | 5,971,968 | 5,971,968 | 5,971,968 | 5,971,968 | 16 | 16 | yes | yes | page-granular Store bytes identical in this repeat, total +0 B, per-Commit new_stored ±16 B |
| M03/docker/sqlite/r2 | 2,936,832 | 2,904,064 | 7,131,136 | 7,032,336 | 20 | 20 | yes | yes | Store pages DIFFER, total -98,800 B, per-Commit new_stored ±20 B |

Pages = SQLite `file.bytes` or PostgreSQL schema bytes; Final = Store bytes as defined above (SQLite adds `wal_bytes`).

## Before/after vs 6d820c756b

Post-#581 reference for layerfs-project#84. Base `layerfs_v2_0_0` @ `b4fa173e40` against the 2026-11-06 report on `6d820c756b` ([report](../../fs-storage-micro/6d820c756b9b12541ac84af7b88467069f31bcbf/report.md)), same workload, pins, image recipe and route. Δ = base − 6d820c756b; Δ% of the 6d820c756b value. Bytes are exact.

| Case | Database | Net 6d820c756b (B) | Net base (B) | Δ net (B) | Δ net % | Σ new_stored 6d820c756b (B) | Σ new_stored base (B) | Δ (B) | Δ % | Σ new_metadata 6d820c756b (B) | Σ new_metadata base (B) | Δ (B) | Δ % |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| M01 | SQLite | 27,701,248 | 27,316,224 | -385,024 | -1.39% | 20,785,323 | 20,785,320 | -3 | -0.00% | 82,320 | 82,317 | -3 | -0.00% |
| M01 | PostgreSQL | 30,064,640 | 30,064,640 | +0 | +0.00% | 20,785,318 | 20,785,328 | +10 | +0.00% | 82,315 | 82,325 | +10 | +0.01% |
| M02 | SQLite | 39,133,184 | 39,116,800 | -16,384 | -0.04% | 34,836,456 | 34,836,446 | -10 | -0.00% | 116,443 | 116,433 | -10 | -0.01% |
| M02 | PostgreSQL | 37,699,584 | 37,724,160 | +24,576 | +0.07% | 34,836,447 | 34,836,449 | +2 | +0.00% | 116,434 | 116,436 | +2 | +0.00% |
| M03 | SQLite | 6,831,704 | 6,918,144 | +86,440 | +1.27% | 4,060,667 | 4,060,694 | +27 | +0.00% | 18,415 | 18,442 | +27 | +0.15% |
| M03 | PostgreSQL | 5,218,304 | 5,218,304 | +0 | +0.00% | 4,060,633 | 4,060,696 | +63 | +0.00% | 18,381 | 18,444 | +63 | +0.34% |
| M04 | SQLite | 10,760,192 | 11,358,208 | +598,016 | +5.56% | 7,462,759 | 7,462,743 | -16 | -0.00% | 26,164 | 26,148 | -16 | -0.06% |
| M04 | PostgreSQL | 9,486,336 | 9,478,144 | -8,192 | -0.09% | 7,462,751 | 7,462,731 | -20 | -0.00% | 26,156 | 26,136 | -20 | -0.08% |
| M05 | SQLite | 10,776,576 | 11,362,304 | +585,728 | +5.44% | 7,462,909 | 7,462,923 | +14 | +0.00% | 26,314 | 26,328 | +14 | +0.05% |
| M05 | PostgreSQL | 9,469,952 | 9,469,952 | +0 | +0.00% | 7,462,928 | 7,462,938 | +10 | +0.00% | 26,333 | 26,343 | +10 | +0.04% |
| M06 | SQLite | 71,315,456 | 71,311,360 | -4,096 | -0.01% | 68,440,101 | 68,440,097 | -4 | -0.00% | 199,633 | 199,629 | -4 | -0.00% |
| M06 | PostgreSQL | 72,040,448 | 72,024,064 | -16,384 | -0.02% | 68,440,098 | 68,440,099 | +1 | +0.00% | 199,630 | 199,631 | +1 | +0.00% |
| M07 | SQLite | 98,029,568 | 98,029,568 | +0 | +0.00% | 92,963,117 | 92,963,117 | +0 | +0.00% | 242,493 | 242,493 | +0 | +0.00% |
| M07 | PostgreSQL | 98,164,736 | 98,172,928 | +8,192 | +0.01% | 92,963,117 | 92,963,117 | +0 | +0.00% | 242,493 | 242,493 | +0 | +0.00% |
| M08 | SQLite | 34,111,488 | 31,879,168 | -2,232,320 | -6.54% | 28,877,854 | 28,877,854 | +0 | +0.00% | 2,196,591 | 2,196,591 | +0 | +0.00% |
| M08 | PostgreSQL | 33,120,256 | 33,144,832 | +24,576 | +0.07% | 28,877,851 | 28,877,853 | +2 | +0.00% | 2,196,588 | 2,196,590 | +2 | +0.00% |

- **Commit counters are unchanged.** Per row, Σ payload (`new_stored − new_metadata`), Σ new_canonical and Σ logical are identical to 6d820c756b; Σ new_stored and Σ new_metadata move by −20…+63 B per row, inside the ±25 B per-Commit metadata drift both campaigns' M03 repeats show.
- **PostgreSQL net is unchanged within a few pages** (−16,384 … +24,576 B, ≤0.09%).
- **SQLite net moves only through the main file.** The WAL is 4,194,304 B in every row except M03. File-only net: M08 −2,232,320 B (−7.46% of its file part), M01 −385,024 B, M04 +598,016 B, M05 +585,728 B, M03 +32,768 B; the others ≤16,384 B. The packs are identical, so this is SQLite page layout and free space (checkpoint timing, freelist), not LayerFS objects. The source of the M04/M05/M08 shifts was not traced (no dbstat run); the M03 repeat here differs by 32,768 B file-only, so moves of this size are not noise-free. #86 (WAL checkpoint) and closed-byte reporting should make these rows comparable.

## Observations

- **The storage story of 6d820c756b holds unchanged on the base.** Payload per Commit is byte-identical, so every per-case finding of the 6d820c756b report still applies: M02 copies store 0 B payload; M03 in-place edits delta against the previous version (≈30 KB per edit before irregular re-bases); M04 rename-over and M05 new-path both store 7,436,595 B payload against M03's 4,042,252 B (rename-over does not delta against the previous version, #88); M06 chunk deltas make small edits nearly free; M07 random is stored raw, zeros ≈0, text 1.25× whole-file zstd-3; M08 deltas recover ≈90% of each 1% churn Commit.
- **Database overhead is the remaining gap** (net − Σ new_stored): M01 6.53 MB SQLite / 9.28 MB PostgreSQL for 10,000 tiny files, the target of the #84 gap stages (#90, #91).
- **Determinism.** The M03 PostgreSQL repeat gave identical schema bytes; the SQLite repeat differed by 32,768 B in the main file and −66,032 B in the WAL (total −98,800 B). Per-Commit payload, new_canonical and logical were identical in both repeats; new_metadata moved by ≤20 B per Commit.

## Limits

- One sample per row plus one repeat case (M03, both backends) on Docker Desktop (arm64). Wall times are INELIGIBLE diagnostics. Each command was bounded at ≤120 s.
- SQLite Store bytes include the `-wal` file (held near the 4 MiB `journal_size_limit` after quiesce), so file-only and WAL parts are shown separately; neither is a lower bound until #86 lands.
- PostgreSQL schema bytes are `pg_total_relation_size` of the `layerfs` schema with `--synchronous-commit off`; server WAL is server-wide and diagnostic only.
- No Store-wide payload/metadata/"other" breakdown is exposed by the CLI; the SQLite page-layout explanation above is an inference from identical packs, not a dbstat attribution.
- The suite image was rebuilt from the same recipe (`fs-storage-micro:b4fa173e`, `sha256:ede53683…`); the image id differs from 6d820c756b's (`sha256:bed5e0a6…`) only by build metadata — gen.py's SHA-256 is checked in every Exec and the pins are unchanged.

## Cleanup

All 18 row Stores were released by the driver (SQLite `store remove`, PostgreSQL `store disconnect`). Campaign `finish` then released, in order: the Docker machine worker (`machine stop docker`), worker container `lfs-263153b4-docker`, worker volume `lfs-263153b4-docker-data`, PostgreSQL server `fsopt-ref-pg` and its data volume `fsopt-ref-pg-data` (all databases), and the suite image `fs-storage-micro:b4fa173e`. **Final cleanup: COMPLETE.** Ledgers, receipts and the campaign state stay local under the private campaign directory.
