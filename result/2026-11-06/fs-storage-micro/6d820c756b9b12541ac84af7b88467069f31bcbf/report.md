# fs-storage-micro — 6d820c756b

**16 of 16 fs-storage-micro rows PASS with verified final state; repeat M03/docker/postgresql/r2: page-granular Store bytes identical, total +0 B, per-Commit new_stored ±25 B; repeat M03/docker/sqlite/r2: page-granular Store bytes identical, total -8,240 B, per-Commit new_stored ±15 B; final cleanup COMPLETE.**

Store bytes for eight single-mechanism workloads on LayerFS 2.0 (Docker machine, SQLite and PostgreSQL Stores), measured at a quiesced boundary through the public CLI. Bytes are reported against each case's expected result, not gated by it. Bytes are exact integers. MB = 10⁶ B; MiB = 2²⁰ B = 1,048,576 B. Wall times are INELIGIBLE diagnostics, never speed claims.

## Configuration

| Item | Value |
| --- | --- |
| LayerFS source | `6d820c756b9b12541ac84af7b88467069f31bcbf` (`layerfs_v2_0_0`) |
| CLI / daemon (macOS, release) | `da25a81bdc692b9a2989650a35716648ab3a64f360281edaff51f870b322e57f` / `b0b961bf004bef7bb0e53724ad5a4a4155e731128093cddfb0a0d3bdd8ff803f` |
| Linux bundle seal | `05891b572d5bcad989f7f05821a856e2ea9cf540186fb18f813ccacbd4cbb0e3` |
| Sandbox image | `sha256:bed5e0a65ac07c69cc0989663ab155d84ac6cbbb42a887996d00b5e937480f34 (fs-storage-micro:6d820c75)` (FROM runtime `sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e`) |
| Machine | Docker (`docker`), private `LAYERFS_HOME`, `LAYERFS_CONSTRUCTION_WORKERS=1` |
| PostgreSQL | postgres:17-bookworm sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652, 1 CPU / 512 MiB, 127.0.0.1:55481; one pre-created empty database per row; `--synchronous-commit off` |
| Workload | `fs-storage-micro-v1`, generator `image/gen.py` SHA-256 `9efa7744f4bce76933ad1db066da53f7e723a08f7dfa9f50caf17b2b3ec3031d` |
| Pins | `src/pins.json` SHA-256 `0b2b57732ae89b8bc49e230990d31b99e9eaf618765c529e6c86dbf815f872e1` (oracles and references) |
| Storage policy (fixed in 2.0) | GEAR 8/16/32 KiB (min/avg/max) for files of 128 KiB and up; delta depth caps 16/8/8 (whole file/chunk/metadata); per-object zstd level 3 |
| Store bytes | SQLite: `store status` `file.bytes` + `file.wal_bytes`; allocated = st_blocks×512 of `store.sqlite` + `-wal` in the worker volume. PostgreSQL: `server.schemas.layerfs` |
| Floor | the row's own Store after create/connect + `project init` of an empty folder (+ `store push` for SQLite), before any fork |

## Rows

| Row | Execution | Final-state verification | Cleanup | Commits | Wall s (INELIGIBLE) | Reason |
| --- | --- | --- | --- | --- | ---: | --- |
| M01/docker/sqlite | PASS | PASS | COMPLETE | 1 | 14.6 |  |
| M01/docker/postgresql | PASS | PASS | COMPLETE | 1 | 49.3 |  |
| M02/docker/sqlite | PASS | PASS | COMPLETE | 2 | 26.5 |  |
| M02/docker/postgresql | PASS | PASS | COMPLETE | 2 | 37.4 |  |
| M03/docker/sqlite | PASS | PASS | COMPLETE | 21 | 22.3 |  |
| M03/docker/sqlite/r2 | PASS | PASS | COMPLETE | 21 | 14.4 |  |
| M03/docker/postgresql | PASS | PASS | COMPLETE | 21 | 26.2 |  |
| M03/docker/postgresql/r2 | PASS | PASS | COMPLETE | 21 | 20.3 |  |
| M04/docker/sqlite | PASS | PASS | COMPLETE | 21 | 15.6 |  |
| M04/docker/postgresql | PASS | PASS | COMPLETE | 21 | 23.1 |  |
| M05/docker/sqlite | PASS | PASS | COMPLETE | 21 | 15.4 |  |
| M05/docker/postgresql | PASS | PASS | COMPLETE | 21 | 22.1 |  |
| M06/docker/sqlite | PASS | PASS | COMPLETE | 6 | 8.3 |  |
| M06/docker/postgresql | PASS | PASS | COMPLETE | 6 | 12.5 |  |
| M07/docker/sqlite | PASS | PASS | COMPLETE | 3 | 10.4 |  |
| M07/docker/postgresql | PASS | PASS | COMPLETE | 3 | 16.2 |  |
| M08/docker/sqlite | PASS | PASS | COMPLETE | 12 | 141.3 |  |
| M08/docker/postgresql | PASS | PASS | COMPLETE | 12 | 198.5 |  |

## Store bytes

| Case | Database | Outcome | Floor (B) | Final (B) | Net (B) | Net (MB) | Net (MiB) | Net file (B) | Net WAL (B) | Net allocated (B) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| M01 | SQLite | PASS | 212,992 | 27,914,240 | 27,701,248 | 27.701 | 26.418 | 23,506,944 | 4,194,304 | 27,701,248 |
| M01 | PostgreSQL | PASS | 753,664 | 30,818,304 | 30,064,640 | 30.065 | 28.672 | — | — | — |
| M02 | SQLite | PASS | 212,992 | 39,346,176 | 39,133,184 | 39.133 | 37.320 | 34,938,880 | 4,194,304 | 39,133,184 |
| M02 | PostgreSQL | PASS | 753,664 | 38,453,248 | 37,699,584 | 37.700 | 35.953 | — | — | — |
| M03 | SQLite | PASS | 212,992 | 7,044,696 | 6,831,704 | 6.832 | 6.515 | 2,691,072 | 4,140,632 | 6,832,128 |
| M03 | PostgreSQL | PASS | 753,664 | 5,971,968 | 5,218,304 | 5.218 | 4.977 | — | — | — |
| M04 | SQLite | PASS | 212,992 | 10,973,184 | 10,760,192 | 10.760 | 10.262 | 6,565,888 | 4,194,304 | 10,760,192 |
| M04 | PostgreSQL | PASS | 753,664 | 10,240,000 | 9,486,336 | 9.486 | 9.047 | — | — | — |
| M05 | SQLite | PASS | 212,992 | 10,989,568 | 10,776,576 | 10.777 | 10.277 | 6,582,272 | 4,194,304 | 10,776,576 |
| M05 | PostgreSQL | PASS | 753,664 | 10,223,616 | 9,469,952 | 9.470 | 9.031 | — | — | — |
| M06 | SQLite | PASS | 212,992 | 71,528,448 | 71,315,456 | 71.315 | 68.012 | 67,121,152 | 4,194,304 | 71,319,552 |
| M06 | PostgreSQL | PASS | 753,664 | 72,794,112 | 72,040,448 | 72.040 | 68.703 | — | — | — |
| M07 | SQLite | PASS | 212,992 | 98,242,560 | 98,029,568 | 98.030 | 93.488 | 93,835,264 | 4,194,304 | 98,033,664 |
| M07 | PostgreSQL | PASS | 753,664 | 98,918,400 | 98,164,736 | 98.165 | 93.617 | — | — | — |
| M08 | SQLite | PASS | 212,992 | 34,324,480 | 34,111,488 | 34.111 | 32.531 | 29,917,184 | 4,194,304 | 34,119,680 |
| M08 | PostgreSQL | PASS | 753,664 | 33,873,920 | 33,120,256 | 33.120 | 31.586 | — | — | — |

## Per-Commit attribution

`logical` is each Commit's whole-tree size, so Σ logical sums the states. In LayerFS 2.0 `new_stored` counts all new pack bytes and `new_metadata` is its metadata-domain subset, so payload = stored − metadata and **net − Σ new_stored** is what no Commit's packs account for (database pages, indexes, free space, the SQLite WAL). The spec's unattributed = net − (Σ new_stored + Σ new_metadata) counts metadata twice; it is shown for comparability only.

| Case | Database | Commits | Σ logical (B) | Σ new_canonical (B) | Σ new_stored (B) | Σ new_metadata (B) | Σ payload = stored − metadata (B) | Net (B) | Net − Σ new_stored (B) | Spec unattributed (B) | Logical ÷ net |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| M01 | SQLite | 1 | 20,647,445 | 21,908,867 | 20,785,323 | 82,320 | 20,703,003 | 27,701,248 | +6,915,925 | +6,833,605 | 0.75 |
| M01 | PostgreSQL | 1 | 20,647,445 | 21,908,867 | 20,785,318 | 82,315 | 20,703,003 | 30,064,640 | +9,279,322 | +9,197,007 | 0.69 |
| M02 | SQLite | 2 | 600,000,000 | 50,426,618 | 34,836,456 | 116,443 | 34,720,013 | 39,133,184 | +4,296,728 | +4,180,285 | 15.33 |
| M02 | PostgreSQL | 2 | 600,000,000 | 50,426,618 | 34,836,447 | 116,434 | 34,720,013 | 37,699,584 | +2,863,137 | +2,746,703 | 15.92 |
| M03 | SQLite | 21 | 85,718,215 | 85,964,901 | 4,060,667 | 18,415 | 4,042,252 | 6,831,704 | +2,771,037 | +2,752,622 | 12.55 |
| M03 | PostgreSQL | 21 | 85,718,215 | 85,964,901 | 4,060,633 | 18,381 | 4,042,252 | 5,218,304 | +1,157,671 | +1,139,290 | 16.43 |
| M04 | SQLite | 21 | 85,718,215 | 86,009,701 | 7,462,759 | 26,164 | 7,436,595 | 10,760,192 | +3,297,433 | +3,271,269 | 7.97 |
| M04 | PostgreSQL | 21 | 85,718,215 | 86,009,701 | 7,462,751 | 26,156 | 7,436,595 | 9,486,336 | +2,023,585 | +1,997,429 | 9.04 |
| M05 | SQLite | 21 | 85,718,215 | 86,018,101 | 7,462,909 | 26,314 | 7,436,595 | 10,776,576 | +3,313,667 | +3,287,353 | 7.95 |
| M05 | PostgreSQL | 21 | 85,718,215 | 86,018,101 | 7,462,928 | 26,333 | 7,436,595 | 9,469,952 | +2,007,024 | +1,980,691 | 9.05 |
| M06 | SQLite | 6 | 404,750,344 | 68,621,666 | 68,440,101 | 199,633 | 68,240,468 | 71,315,456 | +2,875,355 | +2,675,722 | 5.68 |
| M06 | PostgreSQL | 6 | 404,750,344 | 68,621,666 | 68,440,098 | 199,630 | 68,240,468 | 72,040,448 | +3,600,350 | +3,400,720 | 5.62 |
| M07 | SQLite | 3 | 402,653,184 | 134,684,385 | 92,963,117 | 242,493 | 92,720,624 | 98,029,568 | +5,066,451 | +4,823,958 | 4.11 |
| M07 | PostgreSQL | 3 | 402,653,184 | 134,684,385 | 92,963,117 | 242,493 | 92,720,624 | 98,164,736 | +5,201,619 | +4,959,126 | 4.10 |
| M08 | SQLite | 12 | 402,505,728 | 125,539,131 | 28,877,854 | 2,196,591 | 26,681,263 | 34,111,488 | +5,233,634 | +3,037,043 | 11.80 |
| M08 | PostgreSQL | 12 | 402,505,728 | 125,539,131 | 28,877,851 | 2,196,588 | 26,681,263 | 33,120,256 | +4,242,405 | +2,045,817 | 12.15 |

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
| M01 | SQLite | 27,701,248 | 1.342 | 1.326 | 1.300 | 1.342 |
| M01 | PostgreSQL | 30,064,640 | 1.456 | 1.439 | 1.411 | 1.456 |
| M02 | SQLite | 39,133,184 | 0.783 | 0.099 | 1.170 | 1.131 |
| M02 | PostgreSQL | 37,699,584 | 0.754 | 0.095 | 1.127 | 1.089 |
| M03 | SQLite | 6,831,704 | 0.080 | 0.260 | 2.780 | 0.222 |
| M03 | PostgreSQL | 5,218,304 | 0.061 | 0.198 | 2.123 | 0.169 |
| M04 | SQLite | 10,760,192 | 0.126 | 0.409 | 4.378 | 0.349 |
| M04 | PostgreSQL | 9,486,336 | 0.111 | 0.360 | 3.860 | 0.308 |
| M05 | SQLite | 10,776,576 | 0.126 | 0.409 | 0.356 | 0.350 |
| M05 | PostgreSQL | 9,469,952 | 0.110 | 0.360 | 0.313 | 0.307 |
| M06 | SQLite | 71,315,456 | 0.176 | 0.176 | 1.046 | 1.045 |
| M06 | PostgreSQL | 72,040,448 | 0.178 | 0.178 | 1.056 | 1.055 |
| M07 | SQLite | 98,029,568 | 0.487 | 0.442 | 1.103 | 1.061 |
| M07 | PostgreSQL | 98,164,736 | 0.488 | 0.443 | 1.104 | 1.062 |
| M08 | SQLite | 34,111,488 | 0.085 | 0.258 | 2.624 | 0.335 |
| M08 | PostgreSQL | 33,120,256 | 0.082 | 0.250 | 2.547 | 0.325 |

## Cases

### M01 tiny files

- **Workload:** 10,000 files of 0–4,096 B (uniform, SHAKE-256 bytes) in 100 directories.
- **Write method:** new path; Commits: 1.
- **Expected:** net bytes ÷ 10,000 = overhead per small file.
- **Actual, SQLite:** net ÷ 10,000 = 2,770.1 B per file; new_stored 20,785,323 B for 20,647,445 B logical; (net − new_stored) ÷ 10,000 = 691.6 B per file.
- **Actual, PostgreSQL:** net ÷ 10,000 = 3,006.5 B per file; new_stored 20,785,318 B for 20,647,445 B logical; (net − new_stored) ÷ 10,000 = 927.9 B per file.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 20,647,445 | 20,785,323 | 82,320 | 20,785,318 | 82,315 |

### M02 duplicates

- **Workload:** one 50,000,000 B tree (200 files, half synthetic text, half random), then 10 copies at new paths.
- **Write method:** new path (copies read base/ and write new files); Commits: 2.
- **Expected:** second Commit stores only tree/metadata (≈0 payload).
- **Actual, SQLite:** Commit 1 new_stored 34,820,177 B (payload 34,720,013 B); Commit 2 (500,000,000 B of copies) new_stored 16,279 B, new_metadata 16,279 B, payload 0 B.
- **Actual, PostgreSQL:** Commit 1 new_stored 34,820,174 B (payload 34,720,013 B); Commit 2 (500,000,000 B of copies) new_stored 16,273 B, new_metadata 16,273 B, payload 0 B.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 50,000,000 | 34,820,177 | 100,164 | 34,820,174 | 100,161 |
| 2 | 550,000,000 | 16,279 | 16,279 | 16,273 | 16,273 |

### M03 in-place edits

- **Workload:** 100 synthetic text files of 16–64 KiB; 20 Commits each replacing 1% of lines in every file.
- **Write method:** in-place rewrite (same inode, O_WRONLY|O_TRUNC); Commits: 21.
- **Expected:** deltas against the previous version; the chain passes depth 16 (a fuller object re-stored).
- **Actual, SQLite:** Commit 1 new_stored 1,457,781 B; 20 edit Commits Σ 2,602,886 B (mean 130,144 B, largest 404,890 B at Commit 17); Σ new_metadata 18,415 B.
- **Actual, PostgreSQL:** Commit 1 new_stored 1,457,786 B; 20 edit Commits Σ 2,602,847 B (mean 130,142 B, largest 404,889 B at Commit 17); Σ new_metadata 18,381 B.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 4,080,060 | 1,457,781 | 1,141 | 1,457,786 | 1,146 |
| 2 | 4,081,201 | 30,787 | 815 | 30,786 | 814 |
| 3 | 4,081,398 | 30,461 | 851 | 30,469 | 859 |
| 4 | 4,080,719 | 30,494 | 892 | 30,469 | 867 |
| 5 | 4,081,684 | 30,982 | 886 | 30,972 | 876 |
| 6 | 4,082,545 | 30,510 | 867 | 30,512 | 869 |
| 7 | 4,081,352 | 30,495 | 871 | 30,497 | 873 |
| 8 | 4,081,814 | 96,561 | 868 | 96,571 | 878 |
| 9 | 4,082,151 | 371,677 | 872 | 371,679 | 874 |
| 10 | 4,082,030 | 183,023 | 790 | 183,011 | 778 |
| 11 | 4,083,059 | 240,044 | 891 | 240,032 | 879 |
| 12 | 4,082,562 | 140,549 | 884 | 140,550 | 885 |
| 13 | 4,082,014 | 118,230 | 879 | 118,232 | 881 |
| 14 | 4,081,968 | 71,066 | 870 | 71,071 | 875 |
| 15 | 4,081,399 | 117,209 | 870 | 117,212 | 873 |
| 16 | 4,081,846 | 146,759 | 885 | 146,755 | 881 |
| 17 | 4,081,701 | 404,890 | 882 | 404,889 | 881 |
| 18 | 4,082,665 | 91,954 | 870 | 91,953 | 869 |
| 19 | 4,082,049 | 165,946 | 766 | 165,945 | 765 |
| 20 | 4,082,106 | 48,452 | 876 | 48,447 | 871 |
| 21 | 4,081,892 | 222,797 | 889 | 222,795 | 887 |

### M04 rename-over edits

- **Workload:** same content sequence as M03.
- **Write method:** write temp file then rename over the old path; Commits: 21.
- **Expected:** compare with M03 (rename-over also deltas against the previous version).
- **Actual, SQLite:** Commit 1 new_stored 1,457,780 B; 20 edit Commits Σ 6,004,979 B (mean 300,249 B, largest 429,901 B at Commit 21); Σ new_metadata 26,164 B.
- **Actual, PostgreSQL:** Commit 1 new_stored 1,457,784 B; 20 edit Commits Σ 6,004,967 B (mean 300,248 B, largest 429,904 B at Commit 21); Σ new_metadata 26,156 B.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 4,080,060 | 1,457,780 | 1,140 | 1,457,784 | 1,144 |
| 2 | 4,081,201 | 225,308 | 1,104 | 225,310 | 1,106 |
| 3 | 4,081,398 | 180,626 | 1,225 | 180,627 | 1,226 |
| 4 | 4,080,719 | 196,923 | 1,217 | 196,924 | 1,218 |
| 5 | 4,081,684 | 213,644 | 1,256 | 213,645 | 1,257 |
| 6 | 4,082,545 | 229,587 | 1,233 | 229,588 | 1,234 |
| 7 | 4,081,352 | 245,266 | 1,242 | 245,269 | 1,245 |
| 8 | 4,081,814 | 261,793 | 1,277 | 261,790 | 1,274 |
| 9 | 4,082,151 | 262,614 | 1,251 | 262,601 | 1,238 |
| 10 | 4,082,030 | 277,796 | 1,274 | 277,795 | 1,273 |
| 11 | 4,083,059 | 294,278 | 1,277 | 294,276 | 1,275 |
| 12 | 4,082,562 | 292,029 | 1,261 | 292,028 | 1,260 |
| 13 | 4,082,014 | 306,223 | 1,277 | 306,222 | 1,276 |
| 14 | 4,081,968 | 320,599 | 1,255 | 320,603 | 1,259 |
| 15 | 4,081,399 | 333,828 | 1,264 | 333,829 | 1,265 |
| 16 | 4,081,846 | 348,024 | 1,287 | 348,024 | 1,287 |
| 17 | 4,081,701 | 377,017 | 1,262 | 377,016 | 1,261 |
| 18 | 4,082,665 | 390,060 | 1,273 | 390,055 | 1,268 |
| 19 | 4,082,049 | 403,143 | 1,249 | 403,147 | 1,253 |
| 20 | 4,082,106 | 416,320 | 1,258 | 416,314 | 1,252 |
| 21 | 4,081,892 | 429,901 | 1,282 | 429,904 | 1,285 |

### M05 new-path edits

- **Workload:** same content sequence as M03; version v at fNNN.vVV.txt.
- **Write method:** new path per version, old path unlinked; Commits: 21.
- **Expected:** similarity ring only; compare with M03.
- **Actual, SQLite:** Commit 1 new_stored 1,457,787 B; 20 edit Commits Σ 6,005,122 B (mean 300,256 B, largest 429,911 B at Commit 21); Σ new_metadata 26,314 B.
- **Actual, PostgreSQL:** Commit 1 new_stored 1,457,789 B; 20 edit Commits Σ 6,005,139 B (mean 300,257 B, largest 429,901 B at Commit 21); Σ new_metadata 26,333 B.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 4,080,060 | 1,457,787 | 1,147 | 1,457,789 | 1,149 |
| 2 | 4,081,201 | 225,312 | 1,108 | 225,314 | 1,110 |
| 3 | 4,081,398 | 180,633 | 1,232 | 180,632 | 1,231 |
| 4 | 4,080,719 | 196,939 | 1,233 | 196,941 | 1,235 |
| 5 | 4,081,684 | 213,651 | 1,263 | 213,652 | 1,264 |
| 6 | 4,082,545 | 229,595 | 1,241 | 229,592 | 1,238 |
| 7 | 4,081,352 | 245,276 | 1,252 | 245,275 | 1,251 |
| 8 | 4,081,814 | 261,797 | 1,281 | 261,797 | 1,281 |
| 9 | 4,082,151 | 262,617 | 1,254 | 262,619 | 1,256 |
| 10 | 4,082,030 | 277,806 | 1,284 | 277,806 | 1,284 |
| 11 | 4,083,059 | 294,283 | 1,282 | 294,285 | 1,284 |
| 12 | 4,082,562 | 292,025 | 1,257 | 292,025 | 1,257 |
| 13 | 4,082,014 | 306,237 | 1,291 | 306,237 | 1,291 |
| 14 | 4,081,968 | 320,596 | 1,252 | 320,609 | 1,265 |
| 15 | 4,081,399 | 333,839 | 1,275 | 333,841 | 1,277 |
| 16 | 4,081,846 | 348,027 | 1,290 | 348,030 | 1,293 |
| 17 | 4,081,701 | 377,024 | 1,269 | 377,025 | 1,270 |
| 18 | 4,082,665 | 390,071 | 1,284 | 390,070 | 1,283 |
| 19 | 4,082,049 | 403,151 | 1,257 | 403,153 | 1,259 |
| 20 | 4,082,106 | 416,332 | 1,270 | 416,335 | 1,273 |
| 21 | 4,081,892 | 429,911 | 1,292 | 429,901 | 1,282 |

### M06 large file

- **Workload:** 64 MiB random file; insert 1 B at start; insert 1 B at middle; overwrite 4 KiB at middle; append 1 MiB; delete first byte.
- **Write method:** in-place rewrite (same inode, O_WRONLY|O_TRUNC); Commits: 6.
- **Expected:** each edit adds ≈1–2 chunks (≤64 KiB), except append (≈1 MiB).
- **Actual, SQLite:** new_stored (payload = stored − metadata): base 67,302,167 B (67,181,341 B); insert start 6,091 B (54 B); insert middle 17,331 B (183 B); overwrite 4 KiB 40,776 B (8,277 B); append 1 MiB 1,067,474 B (1,050,505 B); delete first 6,262 B (108 B).
- **Actual, PostgreSQL:** new_stored (payload = stored − metadata): base 67,302,167 B (67,181,341 B); insert start 6,092 B (54 B); insert middle 17,331 B (183 B); overwrite 4 KiB 40,776 B (8,277 B); append 1 MiB 1,067,474 B (1,050,505 B); delete first 6,258 B (108 B).

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 67,108,864 | 67,302,167 | 120,826 | 67,302,167 | 120,826 |
| 2 | 67,108,865 | 6,091 | 6,037 | 6,092 | 6,038 |
| 3 | 67,108,866 | 17,331 | 17,148 | 17,331 | 17,148 |
| 4 | 67,108,866 | 40,776 | 32,499 | 40,776 | 32,499 |
| 5 | 68,157,442 | 1,067,474 | 16,969 | 1,067,474 | 16,969 |
| 6 | 68,157,441 | 6,262 | 6,154 | 6,258 | 6,150 |

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
- **Actual, PostgreSQL:** create 13,947,277 B; 10 update Commits Σ 6,759,669 B (mean 675,967 B); VACUUM 8,170,905 B.

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 33,542,144 | 13,947,277 | 60,419 | 13,947,277 | 60,419 |
| 2 | 33,542,144 | 497,695 | 110,489 | 497,695 | 110,489 |
| 3 | 33,542,144 | 556,743 | 148,545 | 556,743 | 148,545 |
| 4 | 33,542,144 | 613,113 | 176,510 | 613,114 | 176,511 |
| 5 | 33,542,144 | 627,641 | 199,279 | 627,641 | 199,279 |
| 6 | 33,542,144 | 681,983 | 216,699 | 681,982 | 216,698 |
| 7 | 33,542,144 | 723,464 | 230,204 | 723,462 | 230,202 |
| 8 | 33,542,144 | 735,404 | 240,212 | 735,402 | 240,210 |
| 9 | 33,542,144 | 769,781 | 247,328 | 769,781 | 247,328 |
| 10 | 33,542,144 | 778,867 | 252,124 | 778,867 | 252,124 |
| 11 | 33,542,144 | 774,982 | 254,973 | 774,982 | 254,973 |
| 12 | 33,542,144 | 8,170,904 | 59,809 | 8,170,905 | 59,810 |

## PostgreSQL server WAL

Server-wide `pg_current_wal_lsn()` advance between the floor and final probes (owning-container admin command; this server served only these rows, serially). It is not part of Store bytes.

| Case | Schema net (B) | Server WAL floor→final (B) |
| --- | ---: | ---: |
| M01 | 30,064,640 | 37,385,824 |
| M02 | 37,699,584 | 39,621,048 |
| M03 | 5,218,304 | 6,292,360 |
| M04 | 9,486,336 | 10,772,384 |
| M05 | 9,469,952 | 10,667,760 |
| M06 | 72,040,448 | 75,256,976 |
| M07 | 98,164,736 | 102,562,648 |
| M08 | 33,120,256 | 36,840,152 |

## Determinism

| Repeat | Pages first (B) | Pages repeat (B) | Final first (B) | Final repeat (B) | Max per-Commit Δ new_stored (B) | Max per-Commit Δ new_metadata (B) | new_canonical and logical identical | Per-Commit payload identical | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| M03/docker/postgresql/r2 | 5,971,968 | 5,971,968 | 5,971,968 | 5,971,968 | 25 | 25 | yes | yes | page-granular Store bytes identical, total +0 B, per-Commit new_stored ±25 B |
| M03/docker/sqlite/r2 | 2,904,064 | 2,904,064 | 7,044,696 | 7,036,456 | 15 | 15 | yes | yes | page-granular Store bytes identical, total -8,240 B, per-Commit new_stored ±15 B |

Pages = SQLite `file.bytes` or PostgreSQL schema bytes; Final = Store bytes as defined above (SQLite adds `wal_bytes`).

## Observations

- **Payload is deterministic; metadata is not.** Per-Commit payload (`new_stored − new_metadata`) and `new_canonical` were identical between SQLite and PostgreSQL rows and between both M03 repeats. Only `new_metadata` (and so `new_stored`) moved, by up to 25 B per Commit. Page-granular totals (SQLite `file.bytes`, PostgreSQL schema bytes) repeated exactly. The SQLite WAL differed by 8,240 B (2 frames). The likely source of the metadata variance is Commit time and file mtimes inside metadata objects; this was not verified in source.
- **`new_stored` includes `new_metadata`.** The 2.0 source (`CommitStatistics`) defines `new_stored` as all new pack bytes and `new_metadata` as the metadata-domain packs. M02's copy Commit confirms it: `new_stored == new_metadata` = 16,279 B. The spec's unattributed formula therefore counts metadata twice. The tables show net − Σ new_stored next to it.
- **M01 tiny files.** Payload is 20,703,003 B for 20,647,445 B of random content (+0.27%). Metadata is 82,320 B, or 8.2 B per file. Store overhead beyond packs is 6,915,925 B (SQLite, of which 4,194,304 B is the WAL) and 9,279,322 B (PostgreSQL). That is about 692 and 928 B per file, so database row/page overhead dominates per-file cost, not LayerFS metadata.
- **M02 duplicates: as expected.** The 500,000,000 B of copies stored 0 B of payload and 16,279 B of metadata. Commit 1 stored 34,720,013 B of payload for 50,000,000 B (the text half compresses).
- **M03 in-place edits.** Commits 2–7 cost about 29.6–30.1 KB of payload each, roughly 300 B per file per edit: true previous-version deltas. From Commit 8 the cost becomes irregular (47–404 KB). That is consistent with some files being stored as fuller objects again before depth 16 (largest jump at Commit 17). Σ over the 20 edits is 2.60 MB, against 1.46 MB for the initial tree.
- **M04 rename-over ≈ M05 new-path, not ≈ M03.** M04 and M05 have identical payload per Commit, 6,004,979 B in total versus M03's 2,602,886 B. Their edit cost grows almost linearly with the Commit number (224 KB at Commit 2, 429 KB at Commit 21). The changed fraction grows the same way when it is measured against the first version. The spec says rename-over deltas against the previous version. That is not what these bytes show: rename-over behaved like the similarity ring and seems to pick an old base. This needs a product check; it is a likely storage-efficiency defect or a spec misunderstanding.
- **M06 large file: better than expected.** Edit payloads were 54 B (insert at start), 183 B (insert in the middle), 8,277 B (4 KiB overwrite, random), 1,050,505 B (1 MiB append) and 108 B (delete first byte). Chunk deltas make a shifted chunk nearly free. Metadata per edit is 6–32 KB for one 64 MiB file, so metadata dominates these small edits.
- **M07 compressibility.** Random: 67,181,294 B of payload (1.0011 × 64 MiB, stored essentially raw). Zeros: 76 B of payload. Text: 25,539,254 B, which is 1.251 × whole-file `zstd -3` (20,412,198 B). The approximate CDC oracle predicts the same kind of loss from compressing each chunk separately.
- **M08 SQLite churn.** The create Commit stored 13,886,858 B of payload for 33,542,144 B logical. Each 1% update Commit stored 387–527 KB of payload, growing over the 10 Commits, while `new_canonical` was about 5.6–5.9 MB, so deltas recover about 90%. `new_metadata` grew from 110 KB to 255 KB per Commit. VACUUM stored 8,111,095 B of payload (about 58% of the create).
- **SQLite vs PostgreSQL.** The counters match. Store bytes differ through database overhead. PostgreSQL is larger for many small objects (M01 +2.4 MB) and for M06/M07. It is smaller wherever the SQLite total includes its 4 MiB WAL. Net ÷ the Git pack is 1.05–1.17 for M02, M06 and M07, 1.30–1.41 for M01, 2.1–2.8 for M03, 3.9–4.4 for M04 and 2.5–2.6 for M08. Git's path-based delta search fails on M05's renames (30.3 MB pack), where LayerFS is 0.31–0.36 of Git.

## Limits

- One sample per row plus one repeat case; no machine other than Docker. Wall times are INELIGIBLE diagnostics. Measured commands were bounded at 120 s each; the longest rows (M08) took 141 s and 199 s in total.
- SQLite Store bytes include the `-wal` file. After quiesce it is held at the 4 MiB `journal_size_limit`, and it can contain frames not yet checkpointed (M03 SQLite file-only net is smaller than Σ new_stored). File-only net is therefore not a lower bound either. Allocated bytes were read read-only from the worker volume and track `file + wal` within one 4 KiB block.
- PostgreSQL schema bytes come from `pg_total_relation_size` (`--synchronous-commit off`). Server WAL is a server-wide LSN delta, listed separately and not part of Store bytes.
- There is no Store-wide payload/metadata/"other" breakdown (internal `get_storage` is not in the CLI), so "net − Σ new_stored" lumps database pages, indexes, free space and WAL together.
- References are computed offline from the same generator's states (emitted in a throwaway container of the suite image). The CDC oracle uses a different gear table and masks, so it is approximate context only. Git does not track empty directories or full modes.
- Explanations of the M03 re-basing points and the M04/M05 base choice are inferences from bytes, not from product traces.

## Cleanup

All 18 row Stores were released by the driver: SQLite `store remove`, PostgreSQL `store disconnect`. Campaign finish then released, in order: the Docker machine (`machine stop`), worker container `lfs-d9bc3fef-docker`, worker volume `lfs-d9bc3fef-docker-data`, and PostgreSQL server `fsm-pg` with its data volume `fsm-pg-data` (all databases). **Final cleanup: COMPLETE.** The suite image `fs-storage-micro:6d820c75` and the private bundle copy were also removed. Compact ledgers, receipts and the reference JSON stay local under the private campaign directory.
