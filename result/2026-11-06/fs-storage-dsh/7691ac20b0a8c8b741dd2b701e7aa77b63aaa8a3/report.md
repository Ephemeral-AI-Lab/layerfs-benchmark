**4 of 4 rows PASS (applied, committed, measured and verified at state 157); net Store bytes D10 47,927,296 B SQLite / 53,272,576 B PostgreSQL, D03 61,014,016 B / 68,419,584 B, against a Git pack + idx of 41,805,317 / 48,166,223 B; final cleanup COMPLETE.**

Storage only: every number is an exact byte count from the public CLI (`store status`, `commit list`) or the Docker worker volume; wall times are INELIGIBLE diagnostics. Bytes are exact integers. MB = 10⁶ B; MiB = 2²⁰ B = 1,048,576 B. Wall times are INELIGIBLE diagnostics, never speed claims.

## Raw vs stored

**Raw** is Σ logical: the bytes of every committed snapshot, as if each were stored in full. **Stored** is the net Store bytes (SQLite: file + WAL; PostgreSQL: schema). **Raw ÷ stored** is the overall reduction, = exact dedup × delta + zstd ÷ Store overhead: **exact dedup** = raw ÷ Σ new_canonical (identical files, chunks and trees stored once); **delta + zstd** = Σ new_canonical ÷ Σ new_stored (delta encoding and compression of the new objects); **Store overhead** = stored ÷ Σ new_stored (database pages, indexes and free space around the packs; 1.35 means the Store is 35% larger than its packs).

| Case | Database | Raw (MB) | Stored (MB) | Raw ÷ stored (×) | Exact dedup (×) | Delta + zstd (×) | Store overhead (×) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| D10 | SQLite | 561.0 | 47.9 | 11.71 | 1.48 | 9.26 | 1.17 |
| D10 | PostgreSQL | 561.0 | 53.3 | 10.53 | 1.48 | 9.26 | 1.30 |
| D03 | SQLite | 1,676.8 | 61.0 | 27.48 | 2.84 | 11.59 | 1.20 |
| D03 | PostgreSQL | 1,676.8 | 68.4 | 24.51 | 2.84 | 11.59 | 1.34 |

## Configuration

| Item | Value |
| --- | --- |
| LayerFS source | `7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3` (`layerfs_v2_0_0`) |
| CLI / daemon SHA-256 | `7f573b61995229fbbd7aeef74a6d756a8637cdd3a2effae0f5321c1863696d40` / `8b4c806d62abfe37a606cfe296e3cb001bc9c66c6615ed1808131cc0e2014409` |
| Linux bundle seal | `b7eddfc9c99da4443f933e483e97a8b2bc9d983c03a45fd20be80c5df7f685e4` (release, reused unchanged) |
| Sandbox image | `fs-storage-dsh:v1-7691ac20` = `sha256:f87606d05686658cae526de651f96db72ecea625eb571c0905e21375420a8de3`, FROM `sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e` (Debian 12, Python 3.11.2, git 2.39.5) |
| Seed | `git-snapshots-157-v1/snapshots.git` (157 trees, linear Commits), local pinned copy, not published; pack SHA-256 `27c7598c04404730200654a1a4ad8f000d63d41da87531cc6e8f206a4e8133bc`; seed file-set identity `898134b8a7b5fbc3f5aeb9366347c427fce35629e82dcef671e4a787eda5ba2b` (pack, idx, rev, bitmap, refs, `mapping.json`, corpus `checkpoint-manifest.json` `03f21acf…334271`, state-157 oracle `10e705a3…295e3c`) |
| Workload | `fs-storage-dsh-v1`: empty project → per state one Exec `apply.py <prev> <k>` + one Commit → final `verify.py 157` |
| Write method | in-place O_WRONLY\|O_TRUNC rewrite of changed regular files (same inode); unlink for removed paths and file<->symlink type changes; O_CREAT\|O_EXCL for new paths; symlink retarget = unlink + symlink; chmod for mode-only changes; emptied directories removed |
| Storage policy | LayerFS 2.0 fixed policy: CDC GEAR 8/16/32 KiB for files >= 128 KiB, whole-file objects below; zstd prefix deltas depth 16 (whole file) / 8 (chunk) / 8 (metadata); per-object zstd level 3; append-only packs (fixed in 2.0; recorded, not varied) |
| Machine | Docker only (private home, `LAYERFS_CONSTRUCTION_WORKERS=1`); Apple M3 Max (14 cores, 36 GiB), macOS 26.4; Docker Desktop (linuxkit, 8 CPUs, 7.75 GiB, shared with other #84 subagents); dedicated PostgreSQL 17 container fsopt-final-pg (1 CPU, 512 MiB) at 127.0.0.1:55494 |
| PostgreSQL | sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652 (postgres:17-bookworm), 1 CPU / 512 MiB, 127.0.0.1:55494, container `fsopt-final-pg`, one fresh empty database per row, `--synchronous-commit off` |
| Command bound | each CLI call 110 s; no retries |
| Campaigns | `fsd-fin-7691`; repeat `fsd-fin-7691-r` |

## Rows

| Case | Database | Campaign | Outcome | Commits | Verify | Row cleanup | Wall s (INELIGIBLE) |
| --- | --- | --- | --- | --- | --- | --- | ---: |
| D10 | SQLite | fsd-fin-7691 | PASS | 17 | PASS | COMPLETE | 50.8 |
| D10 | PostgreSQL | fsd-fin-7691 | PASS | 17 | PASS | COMPLETE | 249.5 |
| D03 | SQLite | fsd-fin-7691 | PASS | 53 | PASS | COMPLETE | 110.8 |
| D03 | PostgreSQL | fsd-fin-7691 | PASS | 53 | PASS | COMPLETE | 879.0 |

## D10: 17 states

Selection `[1, 11, 21, 31, 41, 51, 61, 71, 81, 91, 101, 111, 121, 131, 141, 151, 157]`. Logical bytes (Σ states, files + symlink targets) 561,010,345 B; LayerFS Σ Commit `logical` counts regular files only.

### Store bytes

| Case | Database | Outcome | Floor (B) | Final (B) | Net (B) | Net (MB) | Net (MiB) | Net file (B) | Net WAL (B) | Net allocated (B) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D10 | SQLite | PASS | 217,088 | 48,144,384 | 47,927,296 | 47.927 | 45.707 | 47,927,296 | 0 | 47,927,296 |
| D10 | PostgreSQL | PASS | 598,016 | 53,870,592 | 53,272,576 | 53.273 | 50.805 | — | — | — |

### Attribution

| Case | Database | Commits | Σ logical (B) | Σ new_canonical (B) | Σ new_stored (B) | Σ new_metadata (B) | Σ payload = stored − metadata (B) | Net (B) | Net − Σ new_stored (B) | Spec unattributed (B) | Logical ÷ net |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| D10 | SQLite | 17 | 561,008,218 | 380,287,990 | 41,052,735 | 821,887 | 40,230,848 | 47,927,296 | +6,874,561 | +6,052,674 | 11.71 |
| D10 | PostgreSQL | 17 | 561,008,218 | 380,287,990 | 41,054,142 | 823,262 | 40,230,880 | 53,272,576 | +12,218,434 | +11,395,172 | 10.53 |

### References and ratios

| Case | Whole-file unique (B) | Σ tar\|zstd-3 (B) | Git pack+idx (B) | CDC oracle, approx. (B) |
| --- | ---: | ---: | ---: | ---: |
| D10 | 371,937,053 | 144,803,423 | 41,805,317 | 125,322,715 |

| Case | Database | Net (B) | Net ÷ whole-file unique | Net ÷ Σ tar\|zstd-3 | Net ÷ Git pack+idx | Net ÷ CDC oracle (approx.) |
| --- | --- | ---: | --- | --- | --- | ---: |
| D10 | SQLite | 47,927,296 | 0.129 | 0.331 | 1.146 | 0.382 |
| D10 | PostgreSQL | 53,272,576 | 0.143 | 0.368 | 1.274 | 0.425 |

Net ÷ whole-file unique is the space amplification against ideal unique (uncompressed) bytes.

### new_stored curve

| Database | Commit 1 new_stored (B) | Σ Commits 2… (B) | Median Commit 2… (B) | Max Commit 2… (B) | Largest three |
| --- | ---: | ---: | ---: | ---: | --- |
| SQLite | 509,970 | 40,542,765 | 2,659,714 | 5,216,050 | state 141, state 131, state 157 |
| PostgreSQL | 509,967 | 40,544,175 | 2,659,240 | 5,216,150 | state 141, state 131, state 157 |

<details><summary>Per-Commit bytes</summary>

| Commit | State | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 1,499,065 | 509,970 | 5,919 | 509,967 | 5,916 |
| 2 | 11 | 6,673,091 | 1,707,559 | 16,657 | 1,707,554 | 16,652 |
| 3 | 21 | 9,643,584 | 1,355,712 | 17,517 | 1,355,881 | 17,686 |
| 4 | 31 | 11,884,222 | 1,031,141 | 18,845 | 1,031,072 | 18,776 |
| 5 | 41 | 18,790,418 | 2,796,155 | 43,872 | 2,797,032 | 44,749 |
| 6 | 51 | 21,988,592 | 2,452,753 | 37,930 | 2,453,489 | 38,666 |
| 7 | 61 | 26,001,039 | 2,592,779 | 51,350 | 2,591,895 | 50,466 |
| 8 | 71 | 27,706,574 | 1,101,153 | 29,284 | 1,100,849 | 28,980 |
| 9 | 81 | 33,740,150 | 2,726,649 | 42,270 | 2,726,586 | 42,231 |
| 10 | 91 | 36,248,656 | 1,393,461 | 34,840 | 1,393,676 | 35,055 |
| 11 | 101 | 40,562,402 | 3,180,839 | 63,818 | 3,180,768 | 63,747 |
| 12 | 111 | 44,387,500 | 2,737,853 | 56,006 | 2,737,895 | 56,048 |
| 13 | 121 | 46,737,173 | 2,070,389 | 58,286 | 2,069,927 | 57,824 |
| 14 | 131 | 50,909,755 | 3,877,955 | 80,195 | 3,878,552 | 80,744 |
| 15 | 141 | 57,785,130 | 5,216,050 | 91,585 | 5,216,150 | 91,653 |
| 16 | 151 | 61,430,344 | 2,898,745 | 79,123 | 2,899,269 | 79,695 |
| 17 | 157 | 65,020,523 | 3,403,572 | 94,390 | 3,403,580 | 94,374 |

</details>

## D03: 53 states

Selection `[1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34, 37, 40, 43, 46, 49, 52, 55, 58, 61, 64, 67, 70, 73, 76, 79, 82, 85, 88, 91, 94, 97, 100, 103, 106, 109, 112, 115, 118, 121, 124, 127, 130, 133, 136, 139, 142, 145, 148, 151, 154, 157]`. Logical bytes (Σ states, files + symlink targets) 1,676,767,835 B; LayerFS Σ Commit `logical` counts regular files only.

### Store bytes

| Case | Database | Outcome | Floor (B) | Final (B) | Net (B) | Net (MB) | Net (MiB) | Net file (B) | Net WAL (B) | Net allocated (B) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D03 | SQLite | PASS | 217,088 | 61,231,104 | 61,014,016 | 61.014 | 58.188 | 61,014,016 | 0 | 61,014,016 |
| D03 | PostgreSQL | PASS | 598,016 | 69,017,600 | 68,419,584 | 68.420 | 65.250 | — | — | — |

### Attribution

| Case | Database | Commits | Σ logical (B) | Σ new_canonical (B) | Σ new_stored (B) | Σ new_metadata (B) | Σ payload = stored − metadata (B) | Net (B) | Net − Σ new_stored (B) | Spec unattributed (B) | Logical ÷ net |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| D03 | SQLite | 53 | 1,676,761,730 | 590,109,407 | 50,908,808 | 1,640,102 | 49,268,706 | 61,014,016 | +10,105,208 | +8,465,106 | 27.48 |
| D03 | PostgreSQL | 53 | 1,676,761,730 | 590,109,407 | 50,906,808 | 1,638,078 | 49,268,730 | 68,419,584 | +17,512,776 | +15,874,698 | 24.51 |

### References and ratios

| Case | Whole-file unique (B) | Σ tar\|zstd-3 (B) | Git pack+idx (B) | CDC oracle, approx. (B) |
| --- | ---: | ---: | ---: | ---: |
| D03 | 583,508,670 | 431,678,858 | 48,166,223 | 185,578,564 |

| Case | Database | Net (B) | Net ÷ whole-file unique | Net ÷ Σ tar\|zstd-3 | Net ÷ Git pack+idx | Net ÷ CDC oracle (approx.) |
| --- | --- | ---: | --- | --- | --- | ---: |
| D03 | SQLite | 61,014,016 | 0.105 | 0.141 | 1.267 | 0.329 |
| D03 | PostgreSQL | 68,419,584 | 0.117 | 0.158 | 1.420 | 0.369 |

Net ÷ whole-file unique is the space amplification against ideal unique (uncompressed) bytes.

### new_stored curve

| Database | Commit 1 new_stored (B) | Σ Commits 2… (B) | Median Commit 2… (B) | Max Commit 2… (B) | Largest three |
| --- | ---: | ---: | ---: | ---: | --- |
| SQLite | 509,975 | 50,398,833 | 689,947 | 4,139,324 | state 139, state 112, state 154 |
| PostgreSQL | 509,964 | 50,396,844 | 690,046 | 4,139,243 | state 139, state 112, state 154 |

<details><summary>Per-Commit bytes</summary>

| Commit | State | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 1,499,065 | 509,975 | 5,924 | 509,964 | 5,913 |
| 2 | 4 | 2,755,783 | 617,962 | 9,116 | 617,960 | 9,114 |
| 3 | 7 | 4,730,480 | 532,307 | 8,420 | 532,291 | 8,404 |
| 4 | 10 | 6,292,998 | 555,510 | 9,808 | 555,740 | 10,038 |
| 5 | 13 | 8,090,311 | 749,586 | 11,614 | 749,590 | 11,618 |
| 6 | 16 | 10,134,675 | 823,361 | 11,467 | 823,342 | 11,448 |
| 7 | 19 | 9,928,676 | 626,555 | 13,390 | 626,611 | 13,446 |
| 8 | 22 | 11,918,884 | 850,492 | 15,665 | 850,537 | 15,710 |
| 9 | 25 | 9,619,865 | 165,236 | 8,417 | 165,235 | 8,416 |
| 10 | 28 | 9,571,541 | 258,398 | 8,368 | 258,550 | 8,520 |
| 11 | 31 | 11,884,222 | 96,154 | 19,470 | 96,693 | 20,009 |
| 12 | 34 | 13,725,702 | 913,903 | 24,064 | 913,904 | 24,065 |
| 13 | 37 | 14,079,233 | 466,832 | 16,414 | 466,870 | 16,428 |
| 14 | 40 | 15,681,876 | 529,496 | 19,782 | 529,136 | 19,422 |
| 15 | 43 | 15,133,981 | 237,505 | 12,632 | 237,513 | 12,640 |
| 16 | 46 | 20,707,366 | 1,911,272 | 34,290 | 1,911,374 | 34,416 |
| 17 | 49 | 21,455,669 | 486,215 | 14,122 | 486,277 | 14,160 |
| 18 | 52 | 23,613,743 | 2,273,344 | 41,157 | 2,272,797 | 40,610 |
| 19 | 55 | 24,603,261 | 844,216 | 27,550 | 844,329 | 27,663 |
| 20 | 58 | 24,832,756 | 536,193 | 20,077 | 536,197 | 20,081 |
| 21 | 61 | 26,001,039 | 745,588 | 29,787 | 745,647 | 29,846 |
| 22 | 64 | 26,000,102 | 106,829 | 15,978 | 106,756 | 15,905 |
| 23 | 67 | 27,352,902 | 837,838 | 28,102 | 837,864 | 28,128 |
| 24 | 70 | 29,109,146 | 845,437 | 24,801 | 845,416 | 24,780 |
| 25 | 73 | 29,605,381 | 434,921 | 19,327 | 434,863 | 19,269 |
| 26 | 76 | 25,923,290 | 101,491 | 24,285 | 101,526 | 24,320 |
| 27 | 79 | 29,818,502 | 231,717 | 40,339 | 231,752 | 40,374 |
| 28 | 82 | 30,071,409 | 182,992 | 11,390 | 183,029 | 11,427 |
| 29 | 85 | 35,732,482 | 2,669,904 | 43,315 | 2,670,289 | 43,700 |
| 30 | 88 | 36,405,883 | 375,594 | 23,583 | 375,564 | 23,553 |
| 31 | 91 | 36,248,656 | 454,226 | 23,800 | 454,188 | 23,762 |
| 32 | 94 | 35,569,851 | 418,047 | 31,114 | 417,401 | 30,468 |
| 33 | 97 | 37,903,402 | 1,728,771 | 43,650 | 1,728,672 | 43,551 |
| 34 | 100 | 39,890,945 | 1,121,779 | 32,105 | 1,122,026 | 32,352 |
| 35 | 103 | 42,098,284 | 1,702,921 | 44,174 | 1,702,959 | 44,212 |
| 36 | 106 | 38,526,923 | 363,798 | 42,721 | 363,713 | 42,636 |
| 37 | 109 | 27,578,572 | 415,063 | 39,605 | 415,053 | 39,595 |
| 38 | 112 | 44,749,350 | 3,540,828 | 92,448 | 3,540,827 | 92,447 |
| 39 | 115 | 45,895,027 | 720,614 | 32,471 | 720,680 | 32,537 |
| 40 | 118 | 46,505,955 | 863,536 | 33,992 | 863,298 | 33,754 |
| 41 | 121 | 46,737,173 | 466,713 | 28,882 | 466,251 | 28,420 |
| 42 | 124 | 48,051,342 | 2,760,424 | 66,561 | 2,760,272 | 66,385 |
| 43 | 127 | 49,186,602 | 744,867 | 32,825 | 744,948 | 32,906 |
| 44 | 130 | 50,310,613 | 659,281 | 30,143 | 659,413 | 30,275 |
| 45 | 133 | 52,740,991 | 1,728,177 | 53,535 | 1,728,501 | 53,859 |
| 46 | 136 | 50,949,557 | 269,819 | 35,915 | 269,405 | 35,501 |
| 47 | 139 | 57,151,518 | 4,139,324 | 86,103 | 4,139,243 | 86,022 |
| 48 | 142 | 59,351,166 | 1,265,343 | 44,901 | 1,265,207 | 44,765 |
| 49 | 145 | 60,447,336 | 1,406,526 | 50,938 | 1,405,910 | 50,322 |
| 50 | 148 | 60,711,516 | 617,173 | 23,857 | 617,172 | 23,856 |
| 51 | 151 | 61,430,344 | 1,237,841 | 57,100 | 1,237,279 | 56,538 |
| 52 | 154 | 63,425,861 | 3,006,441 | 90,743 | 3,006,521 | 90,847 |
| 53 | 157 | 65,020,523 | 760,473 | 29,865 | 760,253 | 29,645 |

</details>

## Determinism

D10 SQLite repeated once in campaign `fsd-fin-7691-r` (outcome PASS), same product, image and seed. Per-Commit new_stored identical: **False** (largest per-Commit difference 138 B); per-Commit new_metadata identical: **False**. The Store is not byte-identical on repeat; see the table.

| Metric | First run | Repeat | Δ |
| --- | --- | --- | --- |
| Net file bytes, no WAL (B) | 47,927,296 | 47,955,968 | +28,672 |
| Net WAL bytes (B) | 0 | 0 | +0 |
| Net file + WAL (B) | 47,927,296 | 47,955,968 | +28,672 |
| Net allocated (B) | 47,927,296 | 47,960,064 | +32,768 |
| Σ new_stored (B) | 41,052,735 | 41,052,972 | +237 |
| Σ new_metadata (B) | 821,887 | 822,124 | +237 |

## Reference pins

| Case | references JSON SHA-256 | State manifests | Git pack+idx recomputed (B) | dsh-dedup v1.0.0 pin (B) | Δ (B) |
| --- | --- | --- | ---: | ---: | ---: |
| D10 | `2cce87d007082e687e32b0bf7136f95b76c1278f5619924e554278c8e9cf561a` | `5208278e51ad9e9a…` | 41,805,317 | 41,797,536 | +7,781 |
| D03 | `ec492f61045c327ac4d590b93e73d109bb8c241e165b757d9879ac11f597b3ac` | `d4872e67f21170f4…` | 48,166,223 | 48,169,384 | -3,161 |

Git: git version 2.39.5, dsh-dedup v1.0.0 (commit-tree from seed trees, repack -a -d -f -F --window=10 --depth=50 --threads=2). With `--threads=2` the pack varies by a few kB between runs (a second D10 run gave 41,801,497 B); the pins (git 2.47.1) are confirmed within 0.02%. Whole-file unique, Σ tar|zstd-3 (deterministic PAX tar, zstd 1.5.7 `-3 -T1`) and the CDC oracle (**approximate**: gear 8/16/32 KiB, cutoff 128 KiB, own gear table; Σ min(raw, zstd-3) of unique objects, no deltas) come from `shared/src/references.py` over the states materialized in the suite image with the workload's own `apply.py`; state 157 matched its corpus oracle.

## Observations

- `new_stored` is all new pack bytes of a Commit and `new_metadata` its metadata subset (LayerFS 2.0 CommitStatistics), so payload = stored − metadata and the Store bytes no Commit accounts for are net − Σ new_stored. The spec formula net − (Σ new_stored + Σ new_metadata) counts metadata twice; it is listed as "Spec unattributed" only for comparability.
- D10 SQLite: net 47,927,296 B = 1.146× Git pack+idx, 0.331× Σ tar|zstd-3, 0.382× the CDC oracle. Σ new_stored 41,052,735 B = 0.982× Git (payload 40,230,848 B, metadata 821,887 B); net − Σ new_stored +6,874,561 B (14.3% of net); file-only net (no WAL) 47,927,296 B = 1.146× Git, WAL 0 B.
- D10 PostgreSQL: net 53,272,576 B = 1.274× Git pack+idx, 0.368× Σ tar|zstd-3, 0.425× the CDC oracle. Σ new_stored 41,054,142 B = 0.982× Git (payload 40,230,880 B, metadata 823,262 B); net − Σ new_stored +12,218,434 B (22.9% of net); server WAL generated floor→final 61,181,000 B (diagnostic, not Store bytes).
- D03 SQLite: net 61,014,016 B = 1.267× Git pack+idx, 0.141× Σ tar|zstd-3, 0.329× the CDC oracle. Σ new_stored 50,908,808 B = 1.057× Git (payload 49,268,706 B, metadata 1,640,102 B); net − Σ new_stored +10,105,208 B (16.6% of net); file-only net (no WAL) 61,014,016 B = 1.267× Git, WAL 0 B.
- D03 PostgreSQL: net 68,419,584 B = 1.420× Git pack+idx, 0.158× Σ tar|zstd-3, 0.369× the CDC oracle. Σ new_stored 50,906,808 B = 1.057× Git (payload 49,268,730 B, metadata 1,638,078 B); net − Σ new_stored +17,512,776 B (25.6% of net); server WAL generated floor→final 84,235,976 B (diagnostic, not Store bytes).
- Context only: dsh-dedup v1.0.0 (SDK route, Init of state 1, older policy history) recorded 53,125,120 B (D10) and 69,455,872 B (D03) of Store allocation, with offline payload 41,472,751 B / 51,897,185 B and metadata 1,325,047 B / 2,457,063 B. Not comparable as a baseline.

## Build under test

Final integration `7691ac20b0` (= `layerfs_v2_0_0` @ `8b701f42f0` + #92 + #91 + #90, PRs pending owner merge): branch `opt/84-final-int` @ `7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3`. `8b701f42f0` holds the merged Phase 1 fixes #86–#89 and follow-ups; #92 (directory/extent page deltas, pack framing v26) and #91 + #90 (gap stages 1–2, schema v2) are open PRs awaiting the owner's merge, so this is the final identity candidate. This is the #84 final validation (handoff §5).

## Before/after against the Phase 0 reference (b4fa173e40)

Phase 0 = the 2026-11-06 reference on `b4fa173e40` ([report](../b4fa173e401fc87af6610c151225096288e4ba57/report.md)), same workload, seed, references and route. Raw (Σ logical: D10 561,008,218 B; D03 1,676,761,730 B) and Σ new_canonical are the same workload in both runs. Δ = final − Phase 0; Δ% of the Phase 0 value. Bytes are exact.

| Case | Database | Net Phase 0 (B) | Net final (B) | Δ net (B) | Δ net % | Σ new_stored Phase 0 (B) | Σ new_stored final (B) | Δ (B) | Δ % | Σ new_metadata Phase 0 (B) | Σ new_metadata final (B) | Δ (B) | Δ % |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D10 | SQLite | 57,081,856 | 47,927,296 | -9,154,560 | -16.04% | 41,473,188 | 41,052,735 | -420,453 | -1.01% | 1,019,473 | 821,887 | -197,586 | -19.38% |
| D10 | PostgreSQL | 70,008,832 | 53,272,576 | -16,736,256 | -23.91% | 41,472,330 | 41,054,142 | -418,188 | -1.01% | 1,018,663 | 823,262 | -195,401 | -19.18% |
| D03 | SQLite | 72,966,144 | 61,014,016 | -11,952,128 | -16.38% | 51,914,676 | 50,908,808 | -1,005,868 | -1.94% | 2,153,449 | 1,640,102 | -513,347 | -23.84% |
| D03 | PostgreSQL | — | 68,419,584 | — | — | — | 50,906,808 | — | — | — | 1,638,078 | — | — |

| Case | PostgreSQL ÷ SQLite net, Phase 0 | PostgreSQL ÷ SQLite net, final |
| --- | ---: | ---: |
| D10 | 1.226× | 1.112× |
| D03 | — | 1.121× |

| Case | SQLite net file Phase 0 (B) | net WAL Phase 0 (B) | net file final (B) | net WAL final (B) | Δ file (B) | Δ file % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| D10 | 52,887,552 | 4,194,304 | 47,927,296 | 0 | -4,960,256 | -9.38% |
| D03 | 68,771,840 | 4,194,304 | 61,014,016 | 0 | -7,757,824 | -11.28% |

SQLite file-only bytes are not comparable across #86 (Phase 0 kept a 4,194,304 B WAL after quiesce; the final build checkpoints it into the file), so judge SQLite on file + WAL (net).

**D03 PostgreSQL has no Phase 0 value**: its Phase 0 row failed (a Commit killed at the 110 s bound under Docker contention) and was not rerun. For context only, against the earlier 2026-11-06 run on `6d820c756b` ([report](../../fs-storage-dsh/6d820c756b9b12541ac84af7b88467069f31bcbf/report.md)) D03 PostgreSQL moved 93,388,800 → 68,419,584 B (−24,969,216 B, −26.74 %), Σ new_stored 51,914,864 → 50,906,808 B (−1.94 %), Σ new_metadata 2,153,477 → 1,638,078 B (−23.93 %); its PostgreSQL ÷ SQLite was 1.279× there and is 1.121× here. In this run all 53 D03 PostgreSQL Commits finished inside the per-command bound.

## Final validation: observations

- **All four rows PASS, including D03 PostgreSQL** (the Phase 0 failure).
- **Net Store bytes fell 16–24 %.** D10: SQLite −9,154,560 B (−16.04 %), PostgreSQL −16,736,256 B (−23.91 %); D03 SQLite −11,952,128 B (−16.38 %).
- **Most of it is overhead outside the packs.** Net − Σ new_stored: D10 SQLite 15,608,668 → 6,874,561 B, D10 PostgreSQL 28,536,502 → 12,218,434 B, D03 SQLite 21,051,468 → 10,105,208 B. This is the #86 WAL checkpoint (SQLite) and the #91/#90 inode-value blocks, binding hints and narrow PostgreSQL locations (both backends), consistent with the gap agent's D10 diagnostics.
- **Packs shrank too.** Σ new_metadata −19.4 % (D10) / −23.8 % (D03), consistent with #92's directory page deltas; Σ payload fell 0.55 % on D10 (40,453,715 → 40,230,848 B SQLite), consistent with #88/#89 delta selection.
- **The PostgreSQL ÷ SQLite gap narrowed** on D10 from 1.226× to 1.112×; D10 PostgreSQL net is 1.274× the Git pack + idx (was 1.675×), SQLite 1.146× (was 1.365×).
- **Determinism.** The D10 SQLite repeat differed by +28,672 B file-only (7 pages) and +237 B Σ new_stored (all metadata, ≤ 138 B per Commit) — the same order as earlier repeats.

## Final validation: limits

- One sample per row plus the D10 SQLite repeat, on Docker Desktop (arm64) shared with other #84 agents. Wall times are INELIGIBLE.
- The per-mechanism attribution is an inference from which counters moved; this run measured the integrated build only. #92, #91 and #90 are not merged yet.
- References (whole-file unique, Σ tar|zstd-3, Git pack + idx, CDC oracle) are the pinned workload references reused from the Phase 0 run (same JSON SHA-256).
- The suite image was rebuilt from the same staged context (`fs-storage-dsh:v1-7691ac20`, `sha256:f87606d0…`); the seed pins are rechecked in the image and by the driver.

## Limits

- One sample per row on Docker Desktop (arm64 Mac). Byte counts, not speed; no other machine is run.
- SQLite Store bytes are `file.bytes + file.wal_bytes`; the product leaves a WAL after quiesce (capped at 4 MiB here), which can hold already-checkpointed frames. The parts and the allocated bytes are listed separately.
- PostgreSQL Store bytes are the `layerfs` schema's relation sizes (tables, TOAST, indexes); server WAL is not part of the Store and is recorded only as a WAL position (diagnostic).
- Bytes outside Commit packs (net − Σ new_stored) are measured once per row, not per Commit: the CLI exposes no Store-wide total between Commits without closing the Workspace.
- The CDC oracle is approximate and has no delta encoding, so it is a dedup-only reference, not a lower bound.
- dsh-dedup v1.0.0 numbers came through the SDK route (Init of state 1, older policy history) and are context, not a baseline.

## Cleanup

Final cleanup: **COMPLETE**.
- All five row Stores (D10/D03 SQLite and the D10 SQLite repeat: `store remove`; D10/D03 PostgreSQL: `store disconnect`) by the driver
- docker-worker: `machine stop docker` exit 0
- docker-worker-container: `docker rm lfs-34565e00-docker` exit 0
- docker-data: `docker volume rm lfs-34565e00-docker-data` exit 0
- postgres-data: `DROP DATABASE fsf_d03_docker`, `DROP DATABASE fsf_d10_docker` on the dedicated server fsopt-final-pg, exit 0
- suite-image: `docker image rm fs-storage-dsh:v1-7691ac20` exit 0
- The dedicated PostgreSQL server fsopt-final-pg (and its volume) served the final-validation suites one after another and is released by the campaign owner after the last suite
