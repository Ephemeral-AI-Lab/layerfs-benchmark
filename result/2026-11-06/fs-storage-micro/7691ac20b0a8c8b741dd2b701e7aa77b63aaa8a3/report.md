# fs-storage-micro — 7691ac20b0

**16 of 16 fs-storage-micro rows PASS with verified final state; repeat M03/docker/postgresql/r2: page-granular Store bytes identical in this repeat, total +0 B, per-Commit new_stored ±15 B; repeat M03/docker/sqlite/r2: Store pages DIFFER, total +8,192 B, per-Commit new_stored ±14 B; final cleanup COMPLETE.**

Store bytes for eight single-mechanism workloads on LayerFS 2.0 (Docker machine, SQLite and PostgreSQL Stores), measured at a quiesced boundary through the public CLI. Bytes are reported against each case's expected result, not gated by it. Bytes are exact integers. MB = 10⁶ B; MiB = 2²⁰ B = 1,048,576 B. Wall times are INELIGIBLE diagnostics, never speed claims.

## Raw vs stored

**Raw** is Σ logical: the bytes of every committed snapshot, as if each were stored in full. **Stored** is the net Store bytes (SQLite: file + WAL; PostgreSQL: schema). **Raw ÷ stored** is the overall reduction, = exact dedup × delta + zstd ÷ Store overhead: **exact dedup** = raw ÷ Σ new_canonical (identical files, chunks and trees stored once); **delta + zstd** = Σ new_canonical ÷ Σ new_stored (delta encoding and compression of the new objects); **Store overhead** = stored ÷ Σ new_stored (database pages, indexes and free space around the packs; 1.35 means the Store is 35% larger than its packs).

| Case | Database | Raw (MB) | Stored (MB) | Raw ÷ stored (×) | Exact dedup (×) | Delta + zstd (×) | Store overhead (×) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| M01 | SQLite | 20.6 | 22.6 | 0.91 | 0.94 | 1.05 | 1.09 |
| M01 | PostgreSQL | 20.6 | 24.9 | 0.83 | 0.94 | 1.05 | 1.20 |
| M02 | SQLite | 600.0 | 35.4 | 16.97 | 11.90 | 1.45 | 1.01 |
| M02 | PostgreSQL | 600.0 | 37.0 | 16.21 | 11.90 | 1.45 | 1.06 |
| M03 | SQLite | 85.7 | 2.9 | 29.27 | 1.00 | 32.12 | 1.09 |
| M03 | PostgreSQL | 85.7 | 3.4 | 25.52 | 1.00 | 32.12 | 1.25 |
| M04 | SQLite | 85.7 | 3.1 | 28.02 | 1.00 | 32.04 | 1.14 |
| M04 | PostgreSQL | 85.7 | 3.5 | 24.45 | 1.00 | 32.04 | 1.31 |
| M05 | SQLite | 85.7 | 3.4 | 25.15 | 1.00 | 30.07 | 1.19 |
| M05 | PostgreSQL | 85.7 | 4.0 | 21.49 | 1.00 | 30.07 | 1.39 |
| M06 | SQLite | 404.8 | 68.9 | 5.87 | 5.90 | 1.00 | 1.01 |
| M06 | PostgreSQL | 404.8 | 71.7 | 5.64 | 5.90 | 1.00 | 1.05 |
| M07 | SQLite | 402.7 | 93.8 | 4.29 | 2.99 | 1.45 | 1.01 |
| M07 | PostgreSQL | 402.7 | 97.7 | 4.12 | 2.99 | 1.45 | 1.05 |
| M08 | SQLite | 402.5 | 29.3 | 13.73 | 3.21 | 4.44 | 1.04 |
| M08 | PostgreSQL | 402.5 | 31.4 | 12.81 | 3.21 | 4.44 | 1.11 |

## Configuration

| Item | Value |
| --- | --- |
| LayerFS source | `7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3` (`layerfs_v2_0_0`) |
| CLI / daemon (macOS, release) | `7f573b61995229fbbd7aeef74a6d756a8637cdd3a2effae0f5321c1863696d40` / `8b4c806d62abfe37a606cfe296e3cb001bc9c66c6615ed1808131cc0e2014409` |
| Linux bundle seal | `b7eddfc9c99da4443f933e483e97a8b2bc9d983c03a45fd20be80c5df7f685e4` |
| Sandbox image | `sha256:6934abcee1bababd92e844d57256d4feb6d8e29d1dbb65c579768a85a92d7ba7 (fs-storage-micro:7691ac20)` (FROM runtime `sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e`) |
| Machine | Docker (`docker`), private `LAYERFS_HOME`, `LAYERFS_CONSTRUCTION_WORKERS=1` |
| PostgreSQL | sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652 (postgres:17-bookworm), 1 CPU / 512 MiB, 127.0.0.1:55494; one pre-created empty database per row; `--synchronous-commit off` |
| Workload | `fs-storage-micro-v1`, generator `image/gen.py` SHA-256 `9efa7744f4bce76933ad1db066da53f7e723a08f7dfa9f50caf17b2b3ec3031d` |
| Pins | `src/pins.json` SHA-256 `0b2b57732ae89b8bc49e230990d31b99e9eaf618765c529e6c86dbf815f872e1` (oracles and references) |
| Storage policy (fixed in 2.0) | GEAR 8/16/32 KiB (min/avg/max) for files of 128 KiB and up; delta depth caps 16/8/8 (whole file/chunk/metadata); per-object zstd level 3 |
| Store bytes | SQLite: `store status` `file.bytes` + `file.wal_bytes`; allocated = st_blocks×512 of `store.sqlite` + `-wal` in the worker volume. PostgreSQL: `server.schemas.layerfs` |
| Floor | the row's own Store after create/connect + `project init` of an empty folder (+ `store push` for SQLite), before any fork |

## Rows

| Row | Execution | Final-state verification | Cleanup | Commits | Wall s (INELIGIBLE) | Reason |
| --- | --- | --- | --- | --- | ---: | --- |
| M01/docker/sqlite | PASS | PASS | COMPLETE | 1 | 11.1 |  |
| M01/docker/postgresql | PASS | PASS | COMPLETE | 1 | 13.0 |  |
| M02/docker/sqlite | PASS | PASS | COMPLETE | 2 | 8.2 |  |
| M02/docker/postgresql | PASS | PASS | COMPLETE | 2 | 9.2 |  |
| M03/docker/sqlite | PASS | PASS | COMPLETE | 21 | 8.8 |  |
| M03/docker/sqlite/r2 | PASS | PASS | COMPLETE | 21 | 12.8 |  |
| M03/docker/postgresql | PASS | PASS | COMPLETE | 21 | 11.8 |  |
| M03/docker/postgresql/r2 | PASS | PASS | COMPLETE | 21 | 15.7 |  |
| M04/docker/sqlite | PASS | PASS | COMPLETE | 21 | 10.4 |  |
| M04/docker/postgresql | PASS | PASS | COMPLETE | 21 | 13.7 |  |
| M05/docker/sqlite | PASS | PASS | COMPLETE | 21 | 12.1 |  |
| M05/docker/postgresql | PASS | PASS | COMPLETE | 21 | 17.5 |  |
| M06/docker/sqlite | PASS | PASS | COMPLETE | 6 | 6.5 |  |
| M06/docker/postgresql | PASS | PASS | COMPLETE | 6 | 8.4 |  |
| M07/docker/sqlite | PASS | PASS | COMPLETE | 3 | 8.8 |  |
| M07/docker/postgresql | PASS | PASS | COMPLETE | 3 | 11.7 |  |
| M08/docker/sqlite | PASS | PASS | COMPLETE | 12 | 122.7 |  |
| M08/docker/postgresql | PASS | PASS | COMPLETE | 12 | 157.9 |  |

## Store bytes

| Case | Database | Outcome | Floor (B) | Final (B) | Net (B) | Net (MB) | Net (MiB) | Net file (B) | Net WAL (B) | Net allocated (B) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| M01 | SQLite | PASS | 217,088 | 22,827,008 | 22,609,920 | 22.610 | 21.562 | 22,609,920 | 0 | 22,609,920 |
| M01 | PostgreSQL | PASS | 598,016 | 25,518,080 | 24,920,064 | 24.920 | 23.766 | — | — | — |
| M02 | SQLite | PASS | 217,088 | 35,569,664 | 35,352,576 | 35.353 | 33.715 | 35,352,576 | 0 | 35,356,672 |
| M02 | PostgreSQL | PASS | 598,016 | 37,617,664 | 37,019,648 | 37.020 | 35.305 | — | — | — |
| M03 | SQLite | PASS | 217,088 | 3,145,728 | 2,928,640 | 2.929 | 2.793 | 2,928,640 | 0 | 2,928,640 |
| M03 | PostgreSQL | PASS | 598,016 | 3,956,736 | 3,358,720 | 3.359 | 3.203 | — | — | — |
| M04 | SQLite | PASS | 217,088 | 3,276,800 | 3,059,712 | 3.060 | 2.918 | 3,059,712 | 0 | 3,059,712 |
| M04 | PostgreSQL | PASS | 598,016 | 4,104,192 | 3,506,176 | 3.506 | 3.344 | — | — | — |
| M05 | SQLite | PASS | 217,088 | 3,624,960 | 3,407,872 | 3.408 | 3.250 | 3,407,872 | 0 | 3,407,872 |
| M05 | PostgreSQL | PASS | 598,016 | 4,587,520 | 3,989,504 | 3.990 | 3.805 | — | — | — |
| M06 | SQLite | PASS | 217,088 | 69,136,384 | 68,919,296 | 68.919 | 65.727 | 68,919,296 | 0 | 68,919,296 |
| M06 | PostgreSQL | PASS | 598,016 | 72,327,168 | 71,729,152 | 71.729 | 68.406 | — | — | — |
| M07 | SQLite | PASS | 217,088 | 94,040,064 | 93,822,976 | 93.823 | 89.477 | 93,822,976 | 0 | 93,827,072 |
| M07 | PostgreSQL | PASS | 598,016 | 98,263,040 | 97,665,024 | 97.665 | 93.141 | — | — | — |
| M08 | SQLite | PASS | 217,088 | 29,528,064 | 29,310,976 | 29.311 | 27.953 | 29,310,976 | 0 | 29,310,976 |
| M08 | PostgreSQL | PASS | 598,016 | 32,014,336 | 31,416,320 | 31.416 | 29.961 | — | — | — |

## Per-Commit attribution

`logical` is each Commit's whole-tree size, so Σ logical sums the states. In LayerFS 2.0 `new_stored` counts all new pack bytes and `new_metadata` is its metadata-domain subset, so payload = stored − metadata and **net − Σ new_stored** is what no Commit's packs account for (database pages, indexes, free space, the SQLite WAL). The spec's unattributed = net − (Σ new_stored + Σ new_metadata) counts metadata twice; it is shown for comparability only.

| Case | Database | Commits | Σ logical (B) | Σ new_canonical (B) | Σ new_stored (B) | Σ new_metadata (B) | Σ payload = stored − metadata (B) | Net (B) | Net − Σ new_stored (B) | Spec unattributed (B) | Logical ÷ net |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| M01 | SQLite | 1 | 20,647,445 | 21,908,867 | 20,785,302 | 82,299 | 20,703,003 | 22,609,920 | +1,824,618 | +1,742,319 | 0.91 |
| M01 | PostgreSQL | 1 | 20,647,445 | 21,908,867 | 20,785,335 | 82,332 | 20,703,003 | 24,920,064 | +4,134,729 | +4,052,397 | 0.83 |
| M02 | SQLite | 2 | 600,000,000 | 50,426,618 | 34,836,115 | 116,102 | 34,720,013 | 35,352,576 | +516,461 | +400,359 | 16.97 |
| M02 | PostgreSQL | 2 | 600,000,000 | 50,426,618 | 34,836,087 | 116,074 | 34,720,013 | 37,019,648 | +2,183,561 | +2,067,487 | 16.21 |
| M03 | SQLite | 21 | 85,718,215 | 85,964,901 | 2,676,418 | 18,438 | 2,657,980 | 2,928,640 | +252,222 | +233,784 | 29.27 |
| M03 | PostgreSQL | 21 | 85,718,215 | 85,964,901 | 2,676,420 | 18,440 | 2,657,980 | 3,358,720 | +682,300 | +663,860 | 25.52 |
| M04 | SQLite | 21 | 85,718,215 | 86,009,701 | 2,684,295 | 26,315 | 2,657,980 | 3,059,712 | +375,417 | +349,102 | 28.02 |
| M04 | PostgreSQL | 21 | 85,718,215 | 86,009,701 | 2,684,294 | 26,314 | 2,657,980 | 3,506,176 | +821,882 | +795,568 | 24.45 |
| M05 | SQLite | 21 | 85,718,215 | 86,018,101 | 2,860,637 | 26,580 | 2,834,057 | 3,407,872 | +547,235 | +520,655 | 25.15 |
| M05 | PostgreSQL | 21 | 85,718,215 | 86,018,101 | 2,860,639 | 26,582 | 2,834,057 | 3,989,504 | +1,128,865 | +1,102,283 | 21.49 |
| M06 | SQLite | 6 | 404,750,344 | 68,621,666 | 68,380,882 | 140,414 | 68,240,468 | 68,919,296 | +538,414 | +398,000 | 5.87 |
| M06 | PostgreSQL | 6 | 404,750,344 | 68,621,666 | 68,380,901 | 140,433 | 68,240,468 | 71,729,152 | +3,348,251 | +3,207,818 | 5.64 |
| M07 | SQLite | 3 | 402,653,184 | 134,684,385 | 92,963,117 | 242,493 | 92,720,624 | 93,822,976 | +859,859 | +617,366 | 4.29 |
| M07 | PostgreSQL | 3 | 402,653,184 | 134,684,385 | 92,963,118 | 242,494 | 92,720,624 | 97,665,024 | +4,701,906 | +4,459,412 | 4.12 |
| M08 | SQLite | 12 | 402,505,728 | 125,539,131 | 28,271,000 | 1,589,915 | 26,681,085 | 29,310,976 | +1,039,976 | -549,939 | 13.73 |
| M08 | PostgreSQL | 12 | 402,505,728 | 125,539,131 | 28,271,001 | 1,589,916 | 26,681,085 | 31,416,320 | +3,145,319 | +1,555,403 | 12.81 |

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
| M01 | SQLite | 22,609,920 | 1.095 | 1.082 | 1.061 | 1.095 |
| M01 | PostgreSQL | 24,920,064 | 1.207 | 1.193 | 1.169 | 1.207 |
| M02 | SQLite | 35,352,576 | 0.707 | 0.089 | 1.057 | 1.022 |
| M02 | PostgreSQL | 37,019,648 | 0.740 | 0.093 | 1.107 | 1.070 |
| M03 | SQLite | 2,928,640 | 0.034 | 0.111 | 1.192 | 0.095 |
| M03 | PostgreSQL | 3,358,720 | 0.039 | 0.128 | 1.367 | 0.109 |
| M04 | SQLite | 3,059,712 | 0.036 | 0.116 | 1.245 | 0.099 |
| M04 | PostgreSQL | 3,506,176 | 0.041 | 0.133 | 1.427 | 0.114 |
| M05 | SQLite | 3,407,872 | 0.040 | 0.129 | 0.113 | 0.111 |
| M05 | PostgreSQL | 3,989,504 | 0.047 | 0.152 | 0.132 | 0.129 |
| M06 | SQLite | 68,919,296 | 0.170 | 0.170 | 1.011 | 1.010 |
| M06 | PostgreSQL | 71,729,152 | 0.177 | 0.177 | 1.052 | 1.051 |
| M07 | SQLite | 93,822,976 | 0.466 | 0.423 | 1.055 | 1.015 |
| M07 | PostgreSQL | 97,665,024 | 0.485 | 0.440 | 1.098 | 1.057 |
| M08 | SQLite | 29,310,976 | 0.073 | 0.222 | 2.254 | 0.288 |
| M08 | PostgreSQL | 31,416,320 | 0.078 | 0.238 | 2.416 | 0.308 |

## Cases

### M01 tiny files

- **Workload:** 10,000 files of 0–4,096 B (uniform, SHAKE-256 bytes) in 100 directories.
- **Write method:** new path; Commits: 1.
- **Expected:** net bytes ÷ 10,000 = overhead per small file.
- **Actual, SQLite:** net ÷ 10,000 = 2,261.0 B per file; new_stored 20,785,302 B for 20,647,445 B logical; (net − new_stored) ÷ 10,000 = 182.5 B per file.
- **Actual, PostgreSQL:** net ÷ 10,000 = 2,492.0 B per file; new_stored 20,785,335 B for 20,647,445 B logical; (net − new_stored) ÷ 10,000 = 413.5 B per file.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 20,647,445 | 20,785,302 | 82,299 | 20,785,335 | 82,332 |

### M02 duplicates

- **Workload:** one 50,000,000 B tree (200 files, half synthetic text, half random), then 10 copies at new paths.
- **Write method:** new path (copies read base/ and write new files); Commits: 2.
- **Expected:** second Commit stores only tree/metadata (≈0 payload).
- **Actual, SQLite:** Commit 1 new_stored 34,820,177 B (payload 34,720,013 B); Commit 2 (500,000,000 B of copies) new_stored 15,938 B, new_metadata 15,938 B, payload 0 B.
- **Actual, PostgreSQL:** Commit 1 new_stored 34,820,176 B (payload 34,720,013 B); Commit 2 (500,000,000 B of copies) new_stored 15,911 B, new_metadata 15,911 B, payload 0 B.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 50,000,000 | 34,820,177 | 100,164 | 34,820,176 | 100,163 |
| 2 | 550,000,000 | 15,938 | 15,938 | 15,911 | 15,911 |

### M03 in-place edits

- **Workload:** 100 synthetic text files of 16–64 KiB; 20 Commits each replacing 1% of lines in every file.
- **Write method:** in-place rewrite (same inode, O_WRONLY|O_TRUNC); Commits: 21.
- **Expected:** deltas against the previous version; the chain passes depth 16 (a fuller object re-stored).
- **Actual, SQLite:** Commit 1 new_stored 1,457,645 B; 20 edit Commits Σ 1,218,773 B (mean 60,939 B, largest 102,617 B at Commit 15); Σ new_metadata 18,438 B.
- **Actual, PostgreSQL:** Commit 1 new_stored 1,457,642 B; 20 edit Commits Σ 1,218,778 B (mean 60,939 B, largest 102,620 B at Commit 15); Σ new_metadata 18,440 B.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 4,080,060 | 1,457,645 | 1,144 | 1,457,642 | 1,141 |
| 2 | 4,081,201 | 30,787 | 815 | 30,790 | 818 |
| 3 | 4,081,398 | 30,465 | 855 | 30,469 | 859 |
| 4 | 4,080,719 | 30,479 | 877 | 30,480 | 878 |
| 5 | 4,081,684 | 30,980 | 884 | 30,985 | 889 |
| 6 | 4,082,545 | 30,515 | 872 | 30,523 | 880 |
| 7 | 4,081,352 | 30,495 | 871 | 30,496 | 872 |
| 8 | 4,081,814 | 92,854 | 881 | 92,854 | 881 |
| 9 | 4,082,151 | 94,412 | 875 | 94,412 | 875 |
| 10 | 4,082,030 | 60,571 | 802 | 60,558 | 789 |
| 11 | 4,083,059 | 81,964 | 893 | 81,951 | 880 |
| 12 | 4,082,562 | 67,697 | 883 | 67,697 | 883 |
| 13 | 4,082,014 | 41,530 | 878 | 41,530 | 878 |
| 14 | 4,081,968 | 36,138 | 871 | 36,141 | 874 |
| 15 | 4,081,399 | 102,617 | 873 | 102,620 | 876 |
| 16 | 4,081,846 | 100,621 | 890 | 100,621 | 890 |
| 17 | 4,081,701 | 82,307 | 882 | 82,307 | 882 |
| 18 | 4,082,665 | 98,411 | 875 | 98,407 | 871 |
| 19 | 4,082,049 | 47,558 | 764 | 47,560 | 766 |
| 20 | 4,082,106 | 66,750 | 872 | 66,751 | 873 |
| 21 | 4,081,892 | 61,622 | 881 | 61,626 | 885 |

### M04 rename-over edits

- **Workload:** same content sequence as M03.
- **Write method:** write temp file then rename over the old path; Commits: 21.
- **Expected:** compare with M03 (rename-over also deltas against the previous version).
- **Actual, SQLite:** Commit 1 new_stored 1,457,646 B; 20 edit Commits Σ 1,226,649 B (mean 61,332 B, largest 103,043 B at Commit 15); Σ new_metadata 26,315 B.
- **Actual, PostgreSQL:** Commit 1 new_stored 1,457,642 B; 20 edit Commits Σ 1,226,652 B (mean 61,333 B, largest 103,047 B at Commit 15); Σ new_metadata 26,314 B.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 4,080,060 | 1,457,646 | 1,145 | 1,457,642 | 1,141 |
| 2 | 4,081,201 | 31,074 | 1,102 | 31,076 | 1,104 |
| 3 | 4,081,398 | 30,845 | 1,235 | 30,840 | 1,230 |
| 4 | 4,080,719 | 30,839 | 1,237 | 30,841 | 1,239 |
| 5 | 4,081,684 | 31,337 | 1,241 | 31,331 | 1,235 |
| 6 | 4,082,545 | 30,869 | 1,226 | 30,864 | 1,221 |
| 7 | 4,081,352 | 30,847 | 1,223 | 30,848 | 1,224 |
| 8 | 4,081,814 | 93,245 | 1,272 | 93,243 | 1,270 |
| 9 | 4,082,151 | 94,779 | 1,242 | 94,791 | 1,254 |
| 10 | 4,082,030 | 61,065 | 1,296 | 61,064 | 1,295 |
| 11 | 4,083,059 | 82,344 | 1,273 | 82,347 | 1,276 |
| 12 | 4,082,562 | 68,090 | 1,276 | 68,079 | 1,265 |
| 13 | 4,082,014 | 41,953 | 1,301 | 41,950 | 1,298 |
| 14 | 4,081,968 | 36,532 | 1,265 | 36,541 | 1,274 |
| 15 | 4,081,399 | 103,043 | 1,299 | 103,047 | 1,303 |
| 16 | 4,081,846 | 101,006 | 1,275 | 101,024 | 1,293 |
| 17 | 4,081,701 | 82,716 | 1,291 | 82,712 | 1,287 |
| 18 | 4,082,665 | 98,835 | 1,299 | 98,833 | 1,297 |
| 19 | 4,082,049 | 48,054 | 1,260 | 48,052 | 1,258 |
| 20 | 4,082,106 | 67,167 | 1,289 | 67,164 | 1,286 |
| 21 | 4,081,892 | 62,009 | 1,268 | 62,005 | 1,264 |

### M05 new-path edits

- **Workload:** same content sequence as M03; version v at fNNN.vVV.txt.
- **Write method:** new path per version, old path unlinked; Commits: 21.
- **Expected:** similarity ring only; compare with M03.
- **Actual, SQLite:** Commit 1 new_stored 1,457,648 B; 20 edit Commits Σ 1,402,989 B (mean 70,149 B, largest 221,946 B at Commit 2); Σ new_metadata 26,580 B.
- **Actual, PostgreSQL:** Commit 1 new_stored 1,457,649 B; 20 edit Commits Σ 1,402,990 B (mean 70,150 B, largest 221,940 B at Commit 2); Σ new_metadata 26,582 B.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 4,080,060 | 1,457,648 | 1,147 | 1,457,649 | 1,148 |
| 2 | 4,081,201 | 221,946 | 1,111 | 221,940 | 1,105 |
| 3 | 4,081,398 | 30,848 | 1,238 | 30,849 | 1,239 |
| 4 | 4,080,719 | 30,857 | 1,255 | 30,856 | 1,254 |
| 5 | 4,081,684 | 31,369 | 1,273 | 31,369 | 1,273 |
| 6 | 4,082,545 | 30,881 | 1,238 | 30,883 | 1,240 |
| 7 | 4,081,352 | 30,868 | 1,244 | 30,869 | 1,245 |
| 8 | 4,081,814 | 30,990 | 1,274 | 30,988 | 1,272 |
| 9 | 4,082,151 | 119,138 | 1,265 | 119,136 | 1,263 |
| 10 | 4,082,030 | 81,592 | 1,296 | 81,590 | 1,294 |
| 11 | 4,083,059 | 82,645 | 1,298 | 82,647 | 1,300 |
| 12 | 4,082,562 | 56,670 | 1,266 | 56,668 | 1,264 |
| 13 | 4,082,014 | 69,561 | 1,316 | 69,560 | 1,315 |
| 14 | 4,081,968 | 37,228 | 1,291 | 37,210 | 1,273 |
| 15 | 4,081,399 | 40,968 | 1,310 | 40,967 | 1,309 |
| 16 | 4,081,846 | 153,012 | 1,293 | 153,028 | 1,309 |
| 17 | 4,081,701 | 50,883 | 1,286 | 50,890 | 1,293 |
| 18 | 4,082,665 | 141,548 | 1,313 | 141,550 | 1,315 |
| 19 | 4,082,049 | 31,201 | 1,281 | 31,202 | 1,282 |
| 20 | 4,082,106 | 84,952 | 1,299 | 84,958 | 1,305 |
| 21 | 4,081,892 | 45,832 | 1,286 | 45,830 | 1,284 |

### M06 large file

- **Workload:** 64 MiB random file; insert 1 B at start; insert 1 B at middle; overwrite 4 KiB at middle; append 1 MiB; delete first byte.
- **Write method:** in-place rewrite (same inode, O_WRONLY|O_TRUNC); Commits: 6.
- **Expected:** each edit adds ≈1–2 chunks (≤64 KiB), except append (≈1 MiB).
- **Actual, SQLite:** new_stored (payload = stored − metadata): base 67,302,167 B (67,181,341 B); insert start 1,001 B (54 B); insert middle 4,771 B (183 B); overwrite 4 KiB 17,737 B (8,277 B); append 1 MiB 1,053,928 B (1,050,505 B); delete first 1,278 B (108 B).
- **Actual, PostgreSQL:** new_stored (payload = stored − metadata): base 67,302,167 B (67,181,341 B); insert start 1,018 B (54 B); insert middle 4,774 B (183 B); overwrite 4 KiB 17,736 B (8,277 B); append 1 MiB 1,053,928 B (1,050,505 B); delete first 1,278 B (108 B).

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 67,108,864 | 67,302,167 | 120,826 | 67,302,167 | 120,826 |
| 2 | 67,108,865 | 1,001 | 947 | 1,018 | 964 |
| 3 | 67,108,866 | 4,771 | 4,588 | 4,774 | 4,591 |
| 4 | 67,108,866 | 17,737 | 9,460 | 17,736 | 9,459 |
| 5 | 68,157,442 | 1,053,928 | 3,423 | 1,053,928 | 3,423 |
| 6 | 68,157,441 | 1,278 | 1,170 | 1,278 | 1,170 |

### M07 compressibility

- **Workload:** 64 MiB random, 64 MiB zeros, 64 MiB synthetic text; one file per Commit.
- **Write method:** new path; Commits: 3.
- **Expected:** random ≈64 MiB stored raw, zeros ≈0, text at the zstd-3 ratio.
- **Actual, SQLite:** payload (stored − metadata): random 67,181,294 B (1.0011 × 64 MiB); zeros 76 B; text 25,539,254 B vs whole-file zstd -3 20,412,198 B (1.251×); metadata 120,840 / 684 / 120,969 B.
- **Actual, PostgreSQL:** payload (stored − metadata): random 67,181,294 B (1.0011 × 64 MiB); zeros 76 B; text 25,539,254 B vs whole-file zstd -3 20,412,198 B (1.251×); metadata 120,841 / 684 / 120,969 B.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 67,108,864 | 67,302,134 | 120,840 | 67,302,135 | 120,841 |
| 2 | 134,217,728 | 760 | 684 | 760 | 684 |
| 3 | 201,326,592 | 25,660,223 | 120,969 | 25,660,223 | 120,969 |

### M08 SQLite churn

- **Workload:** SQLite database of 147,000 rows (33,542,144 B, page 4,096); 10 Commits each updating 1% of rows (same-length values); then VACUUM.
- **Write method:** in-place (SQLite page writes, rollback journal); Commits: 12.
- **Expected:** page-local churn reuses most chunks; VACUUM reshuffles.
- **Actual, SQLite:** create 13,947,277 B; 10 update Commits Σ 6,152,817 B (mean 615,282 B); VACUUM 8,170,906 B.
- **Actual, PostgreSQL:** create 13,947,277 B; 10 update Commits Σ 6,152,820 B (mean 615,282 B); VACUUM 8,170,904 B.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 33,542,144 | 13,947,277 | 60,419 | 13,947,277 | 60,419 |
| 2 | 33,542,144 | 463,062 | 75,856 | 463,062 | 75,856 |
| 3 | 33,542,144 | 508,750 | 100,552 | 508,750 | 100,552 |
| 4 | 33,542,144 | 551,060 | 114,457 | 551,061 | 114,458 |
| 5 | 33,542,144 | 554,630 | 126,292 | 554,631 | 126,293 |
| 6 | 33,542,144 | 601,870 | 136,610 | 601,870 | 136,610 |
| 7 | 33,542,144 | 651,768 | 158,508 | 651,769 | 158,509 |
| 8 | 33,542,144 | 658,338 | 163,170 | 658,338 | 163,170 |
| 9 | 33,542,144 | 691,029 | 168,576 | 691,029 | 168,576 |
| 10 | 33,542,144 | 760,305 | 233,668 | 760,305 | 233,668 |
| 11 | 33,542,144 | 712,005 | 191,996 | 712,005 | 191,996 |
| 12 | 33,542,144 | 8,170,906 | 59,811 | 8,170,904 | 59,809 |

## PostgreSQL server WAL

Server-wide `pg_current_wal_lsn()` advance between the floor and final probes (owning-container admin command; this server served only these rows, serially). It is not part of Store bytes.

| Case | Schema net (B) | Server WAL floor→final (B) |
| --- | ---: | ---: |
| M01 | 24,920,064 | 27,555,904 |
| M02 | 37,019,648 | 38,467,904 |
| M03 | 3,358,720 | 3,451,536 |
| M04 | 3,506,176 | 3,615,072 |
| M05 | 3,989,504 | 4,371,088 |
| M06 | 71,729,152 | 73,963,528 |
| M07 | 97,665,024 | 101,574,672 |
| M08 | 31,416,320 | 33,705,368 |

## Determinism

| Repeat | Pages first (B) | Pages repeat (B) | Final first (B) | Final repeat (B) | Max per-Commit Δ new_stored (B) | Max per-Commit Δ new_metadata (B) | new_canonical and logical identical | Per-Commit payload identical | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| M03/docker/postgresql/r2 | 3,956,736 | 3,956,736 | 3,956,736 | 3,956,736 | 15 | 15 | yes | yes | page-granular Store bytes identical in this repeat, total +0 B, per-Commit new_stored ±15 B |
| M03/docker/sqlite/r2 | 3,145,728 | 3,153,920 | 3,145,728 | 3,153,920 | 14 | 14 | yes | yes | Store pages DIFFER, total +8,192 B, per-Commit new_stored ±14 B |

Pages = SQLite `file.bytes` or PostgreSQL schema bytes; Final = Store bytes as defined above (SQLite adds `wal_bytes`).

## Build under test

Final integration `7691ac20b0` (= `layerfs_v2_0_0` @ `8b701f42f0` + #92 + #91 + #90, PRs pending owner merge): branch `opt/84-final-int` @ `7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3`. `8b701f42f0` holds the merged Phase 1 fixes #86–#89 and follow-ups; #92 (directory/extent page deltas, pack framing v26) and #91 + #90 (gap stages 1–2, schema v2) are open PRs awaiting the owner's merge, so this is the final identity candidate, not a merged head. This is the #84 final validation (handoff §5).

## Before/after against the Phase 0 reference (b4fa173e40)

Phase 0 = the 2026-11-06 reference on `b4fa173e40` ([report](../b4fa173e401fc87af6610c151225096288e4ba57/report.md)), same workload, pins, image recipe and route. Net = final − floor (SQLite file + WAL; PostgreSQL schema). Raw (Σ logical) is unchanged in every row (see Raw vs stored below and the Phase 0 report). Δ = final − Phase 0; Δ% of the Phase 0 value. Bytes are exact.

| Case | Database | Net Phase 0 (B) | Net final (B) | Δ net (B) | Δ net % | Σ new_stored Phase 0 (B) | Σ new_stored final (B) | Δ (B) | Δ % | Σ new_metadata Phase 0 (B) | Σ new_metadata final (B) | Δ (B) | Δ % |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| M01 | SQLite | 27,316,224 | 22,609,920 | -4,706,304 | -17.23% | 20,785,320 | 20,785,302 | -18 | -0.00% | 82,317 | 82,299 | -18 | -0.02% |
| M01 | PostgreSQL | 30,064,640 | 24,920,064 | -5,144,576 | -17.11% | 20,785,328 | 20,785,335 | +7 | +0.00% | 82,325 | 82,332 | +7 | +0.01% |
| M02 | SQLite | 39,116,800 | 35,352,576 | -3,764,224 | -9.62% | 34,836,446 | 34,836,115 | -331 | -0.00% | 116,433 | 116,102 | -331 | -0.28% |
| M02 | PostgreSQL | 37,724,160 | 37,019,648 | -704,512 | -1.87% | 34,836,449 | 34,836,087 | -362 | -0.00% | 116,436 | 116,074 | -362 | -0.31% |
| M03 | SQLite | 6,918,144 | 2,928,640 | -3,989,504 | -57.67% | 4,060,694 | 2,676,418 | -1,384,276 | -34.09% | 18,442 | 18,438 | -4 | -0.02% |
| M03 | PostgreSQL | 5,218,304 | 3,358,720 | -1,859,584 | -35.64% | 4,060,696 | 2,676,420 | -1,384,276 | -34.09% | 18,444 | 18,440 | -4 | -0.02% |
| M04 | SQLite | 11,358,208 | 3,059,712 | -8,298,496 | -73.06% | 7,462,743 | 2,684,295 | -4,778,448 | -64.03% | 26,148 | 26,315 | +167 | +0.64% |
| M04 | PostgreSQL | 9,478,144 | 3,506,176 | -5,971,968 | -63.01% | 7,462,731 | 2,684,294 | -4,778,437 | -64.03% | 26,136 | 26,314 | +178 | +0.68% |
| M05 | SQLite | 11,362,304 | 3,407,872 | -7,954,432 | -70.01% | 7,462,923 | 2,860,637 | -4,602,286 | -61.67% | 26,328 | 26,580 | +252 | +0.96% |
| M05 | PostgreSQL | 9,469,952 | 3,989,504 | -5,480,448 | -57.87% | 7,462,938 | 2,860,639 | -4,602,299 | -61.67% | 26,343 | 26,582 | +239 | +0.91% |
| M06 | SQLite | 71,311,360 | 68,919,296 | -2,392,064 | -3.35% | 68,440,097 | 68,380,882 | -59,215 | -0.09% | 199,629 | 140,414 | -59,215 | -29.66% |
| M06 | PostgreSQL | 72,024,064 | 71,729,152 | -294,912 | -0.41% | 68,440,099 | 68,380,901 | -59,198 | -0.09% | 199,631 | 140,433 | -59,198 | -29.65% |
| M07 | SQLite | 98,029,568 | 93,822,976 | -4,206,592 | -4.29% | 92,963,117 | 92,963,117 | +0 | +0.00% | 242,493 | 242,493 | +0 | +0.00% |
| M07 | PostgreSQL | 98,172,928 | 97,665,024 | -507,904 | -0.52% | 92,963,117 | 92,963,118 | +1 | +0.00% | 242,493 | 242,494 | +1 | +0.00% |
| M08 | SQLite | 31,879,168 | 29,310,976 | -2,568,192 | -8.06% | 28,877,854 | 28,271,000 | -606,854 | -2.10% | 2,196,591 | 1,589,915 | -606,676 | -27.62% |
| M08 | PostgreSQL | 33,144,832 | 31,416,320 | -1,728,512 | -5.22% | 28,877,853 | 28,271,001 | -606,852 | -2.10% | 2,196,590 | 1,589,916 | -606,674 | -27.62% |

| Case | PostgreSQL ÷ SQLite net, Phase 0 | PostgreSQL ÷ SQLite net, final |
| --- | ---: | ---: |
| M01 | 1.101× | 1.102× |
| M02 | 0.964× | 1.047× |
| M03 | 0.754× | 1.147× |
| M04 | 0.834× | 1.146× |
| M05 | 0.833× | 1.171× |
| M06 | 1.010× | 1.041× |
| M07 | 1.001× | 1.041× |
| M08 | 1.040× | 1.072× |

| Case | SQLite net file Phase 0 (B) | net WAL Phase 0 (B) | net file final (B) | net WAL final (B) | Δ file (B) | Δ file % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| M01 | 23,121,920 | 4,194,304 | 22,609,920 | 0 | -512,000 | -2.21% |
| M02 | 34,922,496 | 4,194,304 | 35,352,576 | 0 | +430,080 | +1.23% |
| M03 | 2,723,840 | 4,194,304 | 2,928,640 | 0 | +204,800 | +7.52% |
| M04 | 7,163,904 | 4,194,304 | 3,059,712 | 0 | -4,104,192 | -57.29% |
| M05 | 7,168,000 | 4,194,304 | 3,407,872 | 0 | -3,760,128 | -52.46% |
| M06 | 67,117,056 | 4,194,304 | 68,919,296 | 0 | +1,802,240 | +2.69% |
| M07 | 93,835,264 | 4,194,304 | 93,822,976 | 0 | -12,288 | -0.01% |
| M08 | 27,684,864 | 4,194,304 | 29,310,976 | 0 | +1,626,112 | +5.87% |

SQLite file-only bytes are not comparable across #86: Phase 0 kept a 4,194,304 B WAL after quiesce, and the final build checkpoints it into the main file (0 B WAL), so pages that lived in the WAL now count in the file. Judge SQLite on file + WAL (the net column).

## Observations

- **Every row is smaller on both backends.** Net Store bytes fell in all 16 rows: SQLite −3.35 % (M06) to −73.06 % (M04), PostgreSQL −0.41 % (M06) to −63.01 % (M04). Payload-free counters (Σ new_canonical, Σ logical) are unchanged, so the same content is stored in fewer bytes.
- **Small-file edits are the largest win.** Σ new_stored fell 34.1 % for M03 (in-place), 64.0 % for M04 (rename-over) and 61.7 % for M05 (new path); M04/M05 now store about as little as M03 (2,684,295 / 2,860,637 B vs 2,676,418 B), where Phase 0 stored 7,462,743 / 7,462,923 B. This is consistent with #88 (small-file delta base) and #89 (chain root rebase) in delta selection; the codec is unchanged.
- **Metadata shrank where directories and extents change.** Σ new_metadata −29.7 % on M06 (large file) and −27.6 % on M08 (SQLite churn), consistent with #92 (directory/extent page deltas). M01–M05 metadata moved by ≤ +252 B.
- **Store overhead around the packs shrank.** M01 (10,000 tiny files) net − Σ new_stored: SQLite 6,530,904 → 1,824,618 B, PostgreSQL 9,279,312 → 4,134,729 B (#86 WAL checkpoint; #91/#90 inode-value blocks and narrow PostgreSQL locations). PostgreSQL ÷ SQLite stays 1.10× on M01; on the rows where Phase 0's SQLite total carried the 4 MiB WAL, the ratio rose because the SQLite side lost the WAL (e.g. M03 0.754× → 1.147×), not because PostgreSQL grew: PostgreSQL net fell in every row.
- **Determinism.** The M03 PostgreSQL repeat gave identical schema bytes; the M03 SQLite repeat differed by +8,192 B (2 pages). Per-Commit payload, new_canonical and logical were identical; new_stored moved by ≤ 15 B per Commit.

## Limits

- One sample per row plus one repeat case (M03, both backends) on Docker Desktop (arm64), shared with other #84 agents. Wall times are INELIGIBLE diagnostics. Each command was bounded at ≤ 120 s.
- The PRs #92, #91 and #90 are not merged; if the owner merges them unchanged, the merged head's tree equals this build's tree only if no other change lands first.
- The per-mechanism attribution above (#86, #88, #89, #90–#92) is an inference from which counters moved; this run measured the integrated build only.
- PostgreSQL schema bytes are `pg_total_relation_size` of the `layerfs` schema; server WAL is server-wide and diagnostic only.
- The suite image was rebuilt from the same recipe (`fs-storage-micro:7691ac20`, `sha256:6934abce…`); gen.py's SHA-256 is checked in every Exec and the pins are unchanged.

## Cleanup

All 18 row Stores were released by the driver (SQLite `store remove`, PostgreSQL `store disconnect`). Campaign `finish` then released, in order: the Docker machine worker (`machine stop docker`), worker container `lfs-34565e00-docker`, worker volume `lfs-34565e00-docker-data`, this suite's nine databases on the dedicated server `fsopt-final-pg` (`DROP DATABASE`), and the suite image `fs-storage-micro:7691ac20`. The dedicated PostgreSQL server was shared by the final-validation suites run one after another (one fresh database per Store) and released after the last suite. **Final cleanup: COMPLETE.** Ledgers, receipts and the campaign state stay local.
