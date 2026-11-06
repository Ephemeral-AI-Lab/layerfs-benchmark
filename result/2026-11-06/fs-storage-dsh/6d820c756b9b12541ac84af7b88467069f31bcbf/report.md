**4 of 4 rows PASS (applied, committed, measured and verified at state 157); net Store bytes D10 56,139,776 B SQLite / 69,967,872 B PostgreSQL, D03 73,015,296 B / 93,388,800 B, against a Git pack + idx of 41,805,317 / 48,166,223 B; final cleanup COMPLETE.**

Storage only: every number is an exact byte count from the public CLI (`store status`, `commit list`) or the Docker worker volume; wall times are INELIGIBLE diagnostics. Bytes are exact integers. MB = 10⁶ B; MiB = 2²⁰ B = 1,048,576 B. Wall times are INELIGIBLE diagnostics, never speed claims.

## Raw vs stored

**Raw** is Σ logical: the bytes of every committed snapshot, as if each were stored in full. **Stored** is the net Store bytes (SQLite: file + WAL; PostgreSQL: schema). **Raw ÷ stored** is the overall reduction, = exact dedup × delta + zstd ÷ Store overhead: **exact dedup** = raw ÷ Σ new_canonical (identical files, chunks and trees stored once); **delta + zstd** = Σ new_canonical ÷ Σ new_stored (delta encoding and compression of the new objects); **Store overhead** = stored ÷ Σ new_stored (database pages, indexes and free space around the packs; 1.35 means the Store is 35% larger than its packs).

| Case | Database | Raw (MB) | Stored (MB) | Raw ÷ stored (×) | Exact dedup (×) | Delta + zstd (×) | Store overhead (×) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| D10 | SQLite | 561.0 | 56.1 | 9.99 | 1.48 | 9.17 | 1.35 |
| D10 | PostgreSQL | 561.0 | 70.0 | 8.02 | 1.48 | 9.17 | 1.69 |
| D03 | SQLite | 1,676.8 | 73.0 | 22.96 | 2.84 | 11.37 | 1.41 |
| D03 | PostgreSQL | 1,676.8 | 93.4 | 17.95 | 2.84 | 11.37 | 1.80 |

## Configuration

| Item | Value |
| --- | --- |
| LayerFS source | `6d820c756b9b12541ac84af7b88467069f31bcbf` (`layerfs_v2_0_0`) |
| CLI / daemon SHA-256 | `da25a81bdc692b9a2989650a35716648ab3a64f360281edaff51f870b322e57f` / `b0b961bf004bef7bb0e53724ad5a4a4155e731128093cddfb0a0d3bdd8ff803f` |
| Linux bundle seal | `05891b572d5bcad989f7f05821a856e2ea9cf540186fb18f813ccacbd4cbb0e3` (release, reused unchanged) |
| Sandbox image | `fs-storage-dsh:v1-6d820c75` = `sha256:52ef88a47b340ef809b54f2cd44b3e6a83728ef7f30d9382abe5566f583ba26e`, FROM `sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e` (Debian 12, Python 3.11.2, git 2.39.5) |
| Seed | `git-snapshots-157-v1/snapshots.git` (157 trees, linear Commits), local pinned copy, not published; pack SHA-256 `27c7598c04404730200654a1a4ad8f000d63d41da87531cc6e8f206a4e8133bc`; seed file-set identity `898134b8a7b5fbc3f5aeb9366347c427fce35629e82dcef671e4a787eda5ba2b` (pack, idx, rev, bitmap, refs, `mapping.json`, corpus `checkpoint-manifest.json` `03f21acf…334271`, state-157 oracle `10e705a3…295e3c`) |
| Workload | `fs-storage-dsh-v1`: empty project → per state one Exec `apply.py <prev> <k>` + one Commit → final `verify.py 157` |
| Write method | in-place O_WRONLY\|O_TRUNC rewrite of changed regular files (same inode); unlink for removed paths and file<->symlink type changes; O_CREAT\|O_EXCL for new paths; symlink retarget = unlink + symlink; chmod for mode-only changes; emptied directories removed |
| Storage policy | LayerFS 2.0 fixed policy: CDC GEAR 8/16/32 KiB for files >= 128 KiB, whole-file objects below; zstd prefix deltas depth 16 (whole file) / 8 (chunk) / 8 (metadata); per-object zstd level 3; append-only packs (fixed in 2.0; recorded, not varied) |
| Machine | Docker only (private home, `LAYERFS_CONSTRUCTION_WORKERS=1`); Apple M3 Max (14 cores, 36 GiB), macOS 26.4.1; Docker Desktop (linuxkit, 8 CPUs, 7.75 GiB, shared with two sibling campaigns); dedicated PostgreSQL 17 container fsd-pg (1 CPU, 512 MiB) at 127.0.0.1:55482 |
| PostgreSQL | sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652 (postgres:17-bookworm), container `fsd-pg`, one fresh empty database per row, `--synchronous-commit off` |
| Command bound | each CLI call 110 s; no retries |
| Campaigns | `fsd-1106a`, `fsd-1106b`; repeat `fsd-1106c` |

## Rows

| Case | Database | Campaign | Outcome | Commits | Verify | Row cleanup | Wall s (INELIGIBLE) |
| --- | --- | --- | --- | --- | --- | --- | ---: |
| D10 | SQLite | fsd-1106a | PASS | 17 | PASS | COMPLETE | 54.0 |
| D10 | PostgreSQL | fsd-1106b | PASS | 17 | PASS | COMPLETE | 192.5 |
| D03 | SQLite | fsd-1106b | PASS | 53 | PASS | COMPLETE | 182.1 |
| D03 | PostgreSQL | fsd-1106b | PASS | 53 | PASS | COMPLETE | 597.3 |

Superseded attempt `fsd-1106a` `D10/docker/postgresql`: FAIL — Failure: 00001_store_connect: CLI/process exit 125. infrastructure: the owned PostgreSQL server fsd-pg had crashed (PANIC: No space left on device) during another owner's Docker-disk exhaustion at 01:30 UTC; store connect was refused before any Store effect. The server recovered and restarted; fresh databases are used.

## D10: 17 states

Selection `[1, 11, 21, 31, 41, 51, 61, 71, 81, 91, 101, 111, 121, 131, 141, 151, 157]`. Logical bytes (Σ states, files + symlink targets) 561,010,345 B; LayerFS Σ Commit `logical` counts regular files only.

### Store bytes

| Case | Database | Outcome | Floor (B) | Final (B) | Net (B) | Net (MB) | Net (MiB) | Net file (B) | Net WAL (B) | Net allocated (B) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D10 | SQLite | PASS | 212,992 | 56,352,768 | 56,139,776 | 56.140 | 53.539 | 51,945,472 | 4,194,304 | 56,143,872 |
| D10 | PostgreSQL | PASS | 753,664 | 70,721,536 | 69,967,872 | 69.968 | 66.727 | — | — | — |

### Attribution

| Case | Database | Commits | Σ logical (B) | Σ new_canonical (B) | Σ new_stored (B) | Σ new_metadata (B) | Σ payload = stored − metadata (B) | Net (B) | Net − Σ new_stored (B) | Spec unattributed (B) | Logical ÷ net |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| D10 | SQLite | 17 | 561,008,218 | 380,287,990 | 41,473,149 | 1,019,282 | 40,453,867 | 56,139,776 | +14,666,627 | +13,647,345 | 9.99 |
| D10 | PostgreSQL | 17 | 561,008,218 | 380,287,990 | 41,473,341 | 1,019,474 | 40,453,867 | 69,967,872 | +28,494,531 | +27,475,057 | 8.02 |

### References and ratios

| Case | Whole-file unique (B) | Σ tar\|zstd-3 (B) | Git pack+idx (B) | CDC oracle, approx. (B) |
| --- | ---: | ---: | ---: | ---: |
| D10 | 371,937,053 | 144,803,423 | 41,805,317 | 125,322,715 |

| Case | Database | Net (B) | Net ÷ whole-file unique | Net ÷ Σ tar\|zstd-3 | Net ÷ Git pack+idx | Net ÷ CDC oracle (approx.) |
| --- | --- | ---: | --- | --- | --- | ---: |
| D10 | SQLite | 56,139,776 | 0.151 | 0.388 | 1.343 | 0.448 |
| D10 | PostgreSQL | 69,967,872 | 0.188 | 0.483 | 1.674 | 0.558 |

Net ÷ whole-file unique is the space amplification against ideal unique (uncompressed) bytes.

### new_stored curve

| Database | Commit 1 new_stored (B) | Σ Commits 2… (B) | Median Commit 2… (B) | Max Commit 2… (B) | Largest three |
| --- | ---: | ---: | ---: | ---: | --- |
| SQLite | 510,069 | 40,963,080 | 2,691,338 | 5,387,716 | state 141, state 131, state 101 |
| PostgreSQL | 510,063 | 40,963,278 | 2,691,363 | 5,387,731 | state 141, state 131, state 101 |

<details><summary>Per-Commit bytes</summary>

| Commit | State | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 1,499,065 | 510,069 | 5,919 | 510,063 | 5,913 |
| 2 | 11 | 6,673,091 | 1,707,490 | 16,795 | 1,707,479 | 16,784 |
| 3 | 21 | 9,643,584 | 1,367,442 | 19,988 | 1,367,434 | 19,980 |
| 4 | 31 | 11,884,222 | 1,045,689 | 21,908 | 1,045,694 | 21,913 |
| 5 | 41 | 18,790,418 | 2,806,426 | 44,385 | 2,806,421 | 44,380 |
| 6 | 51 | 21,988,592 | 2,468,213 | 45,110 | 2,468,269 | 45,166 |
| 7 | 61 | 26,001,039 | 2,642,164 | 60,769 | 2,642,208 | 60,813 |
| 8 | 71 | 27,706,574 | 1,131,882 | 37,671 | 1,131,849 | 37,638 |
| 9 | 81 | 33,740,150 | 2,740,513 | 53,921 | 2,740,519 | 53,927 |
| 10 | 91 | 36,248,656 | 1,464,976 | 49,808 | 1,465,128 | 49,960 |
| 11 | 101 | 40,562,402 | 3,259,539 | 79,943 | 3,259,484 | 79,888 |
| 12 | 111 | 44,387,500 | 2,788,960 | 72,788 | 2,788,885 | 72,713 |
| 13 | 121 | 46,737,173 | 2,195,317 | 81,733 | 2,195,315 | 81,731 |
| 14 | 131 | 50,909,755 | 3,940,865 | 100,349 | 3,941,007 | 100,491 |
| 15 | 141 | 57,785,130 | 5,387,716 | 112,149 | 5,387,731 | 112,164 |
| 16 | 151 | 61,430,344 | 2,894,756 | 106,045 | 2,894,736 | 106,025 |
| 17 | 157 | 65,020,523 | 3,121,132 | 110,001 | 3,121,119 | 109,988 |

</details>

## D03: 53 states

Selection `[1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34, 37, 40, 43, 46, 49, 52, 55, 58, 61, 64, 67, 70, 73, 76, 79, 82, 85, 88, 91, 94, 97, 100, 103, 106, 109, 112, 115, 118, 121, 124, 127, 130, 133, 136, 139, 142, 145, 148, 151, 154, 157]`. Logical bytes (Σ states, files + symlink targets) 1,676,767,835 B; LayerFS Σ Commit `logical` counts regular files only.

### Store bytes

| Case | Database | Outcome | Floor (B) | Final (B) | Net (B) | Net (MB) | Net (MiB) | Net file (B) | Net WAL (B) | Net allocated (B) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D03 | SQLite | PASS | 212,992 | 73,228,288 | 73,015,296 | 73.015 | 69.633 | 68,820,992 | 4,194,304 | 73,019,392 |
| D03 | PostgreSQL | PASS | 753,664 | 94,142,464 | 93,388,800 | 93.389 | 89.062 | — | — | — |

### Attribution

| Case | Database | Commits | Σ logical (B) | Σ new_canonical (B) | Σ new_stored (B) | Σ new_metadata (B) | Σ payload = stored − metadata (B) | Net (B) | Net − Σ new_stored (B) | Spec unattributed (B) | Logical ÷ net |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| D03 | SQLite | 53 | 1,676,761,730 | 590,109,407 | 51,914,555 | 2,153,168 | 49,761,387 | 73,015,296 | +21,100,741 | +18,947,573 | 22.96 |
| D03 | PostgreSQL | 53 | 1,676,761,730 | 590,109,407 | 51,914,864 | 2,153,477 | 49,761,387 | 93,388,800 | +41,473,936 | +39,320,459 | 17.95 |

### References and ratios

| Case | Whole-file unique (B) | Σ tar\|zstd-3 (B) | Git pack+idx (B) | CDC oracle, approx. (B) |
| --- | ---: | ---: | ---: | ---: |
| D03 | 583,508,670 | 431,678,858 | 48,166,223 | 185,578,564 |

| Case | Database | Net (B) | Net ÷ whole-file unique | Net ÷ Σ tar\|zstd-3 | Net ÷ Git pack+idx | Net ÷ CDC oracle (approx.) |
| --- | --- | ---: | --- | --- | --- | ---: |
| D03 | SQLite | 73,015,296 | 0.125 | 0.169 | 1.516 | 0.393 |
| D03 | PostgreSQL | 93,388,800 | 0.160 | 0.216 | 1.939 | 0.503 |

Net ÷ whole-file unique is the space amplification against ideal unique (uncompressed) bytes.

### new_stored curve

| Database | Commit 1 new_stored (B) | Σ Commits 2… (B) | Median Commit 2… (B) | Max Commit 2… (B) | Largest three |
| --- | ---: | ---: | ---: | ---: | --- |
| SQLite | 510,069 | 51,404,486 | 722,070 | 4,228,417 | state 139, state 112, state 124 |
| PostgreSQL | 510,065 | 51,404,799 | 722,036 | 4,228,685 | state 139, state 112, state 124 |

<details><summary>Per-Commit bytes</summary>

| Commit | State | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 1,499,065 | 510,069 | 5,919 | 510,065 | 5,915 |
| 2 | 4 | 2,755,783 | 616,975 | 9,220 | 616,984 | 9,229 |
| 3 | 7 | 4,730,480 | 533,556 | 9,510 | 533,555 | 9,509 |
| 4 | 10 | 6,292,998 | 560,330 | 11,565 | 560,321 | 11,556 |
| 5 | 13 | 8,090,311 | 755,802 | 14,337 | 755,816 | 14,351 |
| 6 | 16 | 10,134,675 | 828,996 | 14,497 | 828,987 | 14,488 |
| 7 | 19 | 9,928,676 | 636,571 | 16,730 | 636,560 | 16,719 |
| 8 | 22 | 11,918,884 | 862,284 | 19,845 | 862,268 | 19,829 |
| 9 | 25 | 9,619,865 | 182,239 | 10,009 | 182,224 | 9,994 |
| 10 | 28 | 9,571,541 | 271,647 | 9,865 | 271,648 | 9,866 |
| 11 | 31 | 11,884,222 | 99,855 | 22,164 | 99,856 | 22,165 |
| 12 | 34 | 13,725,702 | 927,410 | 26,023 | 927,394 | 26,007 |
| 13 | 37 | 14,079,233 | 486,407 | 21,837 | 486,466 | 21,896 |
| 14 | 40 | 15,681,876 | 555,954 | 25,007 | 555,963 | 25,016 |
| 15 | 43 | 15,133,981 | 244,890 | 16,165 | 244,885 | 16,160 |
| 16 | 46 | 20,707,366 | 1,973,152 | 40,589 | 1,973,330 | 40,767 |
| 17 | 49 | 21,455,669 | 502,922 | 23,881 | 502,916 | 23,875 |
| 18 | 52 | 23,613,743 | 2,277,621 | 49,422 | 2,277,594 | 49,395 |
| 19 | 55 | 24,603,261 | 887,176 | 38,096 | 887,150 | 38,070 |
| 20 | 58 | 24,832,756 | 545,247 | 29,342 | 545,252 | 29,347 |
| 21 | 61 | 26,001,039 | 753,899 | 39,657 | 753,925 | 39,683 |
| 22 | 64 | 26,000,102 | 144,129 | 20,685 | 144,094 | 20,650 |
| 23 | 67 | 27,352,902 | 854,637 | 35,785 | 854,658 | 35,806 |
| 24 | 70 | 29,109,146 | 848,665 | 34,346 | 848,662 | 34,343 |
| 25 | 73 | 29,605,381 | 393,430 | 27,028 | 393,421 | 27,019 |
| 26 | 76 | 25,923,290 | 165,542 | 27,726 | 165,499 | 27,683 |
| 27 | 79 | 29,818,502 | 235,955 | 49,916 | 236,000 | 49,961 |
| 28 | 82 | 30,071,409 | 201,675 | 16,771 | 201,669 | 16,765 |
| 29 | 85 | 35,732,482 | 2,698,772 | 56,370 | 2,698,786 | 56,384 |
| 30 | 88 | 36,405,883 | 384,640 | 30,153 | 384,627 | 30,140 |
| 31 | 91 | 36,248,656 | 505,419 | 30,092 | 505,444 | 30,117 |
| 32 | 94 | 35,569,851 | 486,817 | 43,590 | 486,797 | 43,570 |
| 33 | 97 | 37,903,402 | 1,745,065 | 56,967 | 1,745,072 | 56,974 |
| 34 | 100 | 39,890,945 | 1,145,736 | 51,661 | 1,145,765 | 51,690 |
| 35 | 103 | 42,098,284 | 1,746,640 | 59,753 | 1,746,630 | 59,743 |
| 36 | 106 | 38,526,923 | 392,789 | 55,297 | 392,780 | 55,288 |
| 37 | 109 | 27,578,572 | 377,324 | 46,465 | 377,264 | 46,405 |
| 38 | 112 | 44,749,350 | 4,050,150 | 102,639 | 4,050,299 | 102,788 |
| 39 | 115 | 45,895,027 | 819,448 | 50,027 | 819,446 | 50,025 |
| 40 | 118 | 46,505,955 | 831,976 | 48,737 | 832,015 | 48,776 |
| 41 | 121 | 46,737,173 | 499,815 | 42,967 | 499,756 | 42,908 |
| 42 | 124 | 48,051,342 | 2,760,948 | 84,691 | 2,760,836 | 84,579 |
| 43 | 127 | 49,186,602 | 737,391 | 49,462 | 737,370 | 49,441 |
| 44 | 130 | 50,310,613 | 706,749 | 48,996 | 706,703 | 48,950 |
| 45 | 133 | 52,740,991 | 1,727,459 | 76,778 | 1,727,470 | 76,789 |
| 46 | 136 | 50,949,557 | 237,932 | 48,342 | 237,876 | 48,286 |
| 47 | 139 | 57,151,518 | 4,228,417 | 103,585 | 4,228,685 | 103,853 |
| 48 | 142 | 59,351,166 | 1,231,852 | 62,158 | 1,231,849 | 62,155 |
| 49 | 145 | 60,447,336 | 1,548,521 | 77,730 | 1,548,450 | 77,659 |
| 50 | 148 | 60,711,516 | 617,548 | 35,667 | 617,536 | 35,655 |
| 51 | 151 | 61,430,344 | 1,302,792 | 78,351 | 1,302,768 | 78,327 |
| 52 | 154 | 63,425,861 | 2,466,415 | 104,856 | 2,466,387 | 104,828 |
| 53 | 157 | 65,020,523 | 806,905 | 41,897 | 807,091 | 42,083 |

</details>

## Determinism

D10 SQLite repeated once in campaign `fsd-1106c` (outcome PASS), same product, image and seed. Per-Commit new_stored identical: **False** (largest per-Commit difference 101 B); per-Commit new_metadata identical: **False**. The Store is not byte-identical on repeat; see the table.

| Metric | First run | Repeat | Δ |
| --- | --- | --- | --- |
| Net file bytes, no WAL (B) | 51,945,472 | 51,974,144 | +28,672 |
| Net WAL bytes (B) | 4,194,304 | 4,194,304 | +0 |
| Net file + WAL (B) | 56,139,776 | 56,168,448 | +28,672 |
| Net allocated (B) | 56,143,872 | 56,172,544 | +28,672 |
| Σ new_stored (B) | 41,473,149 | 41,473,061 | -88 |
| Σ new_metadata (B) | 1,019,282 | 1,019,194 | -88 |

## Reference pins

| Case | references JSON SHA-256 | State manifests | Git pack+idx recomputed (B) | dsh-dedup v1.0.0 pin (B) | Δ (B) |
| --- | --- | --- | ---: | ---: | ---: |
| D10 | `2cce87d007082e687e32b0bf7136f95b76c1278f5619924e554278c8e9cf561a` | `5208278e51ad9e9a…` | 41,805,317 | 41,797,536 | +7,781 |
| D03 | `ec492f61045c327ac4d590b93e73d109bb8c241e165b757d9879ac11f597b3ac` | `d4872e67f21170f4…` | 48,166,223 | 48,169,384 | -3,161 |

Git: git version 2.39.5, dsh-dedup v1.0.0 (commit-tree from seed trees, repack -a -d -f -F --window=10 --depth=50 --threads=2). With `--threads=2` the pack varies by a few kB between runs (a second D10 run gave 41,801,497 B); the pins (git 2.47.1) are confirmed within 0.02%. Whole-file unique, Σ tar|zstd-3 (deterministic PAX tar, zstd 1.5.7 `-3 -T1`) and the CDC oracle (**approximate**: gear 8/16/32 KiB, cutoff 128 KiB, own gear table; Σ min(raw, zstd-3) of unique objects, no deltas) come from `shared/src/references.py` over the states materialized in the suite image with the workload's own `apply.py`; state 157 matched its corpus oracle.

## Observations

- `new_stored` is all new pack bytes of a Commit and `new_metadata` its metadata subset (LayerFS 2.0 CommitStatistics), so payload = stored − metadata and the Store bytes no Commit accounts for are net − Σ new_stored. The spec formula net − (Σ new_stored + Σ new_metadata) counts metadata twice; it is listed as "Spec unattributed" only for comparability.
- D10 SQLite: net 56,139,776 B = 1.343× Git pack+idx, 0.388× Σ tar|zstd-3, 0.448× the CDC oracle. Σ new_stored 41,473,149 B = 0.992× Git (payload 40,453,867 B, metadata 1,019,282 B); net − Σ new_stored +14,666,627 B (26.1% of net); file-only net (no WAL) 51,945,472 B = 1.243× Git, WAL 4,194,304 B.
- D10 PostgreSQL: net 69,967,872 B = 1.674× Git pack+idx, 0.483× Σ tar|zstd-3, 0.558× the CDC oracle. Σ new_stored 41,473,341 B = 0.992× Git (payload 40,453,867 B, metadata 1,019,474 B); net − Σ new_stored +28,494,531 B (40.7% of net); server WAL generated floor→final 88,668,840 B (diagnostic, not Store bytes).
- D03 SQLite: net 73,015,296 B = 1.516× Git pack+idx, 0.169× Σ tar|zstd-3, 0.393× the CDC oracle. Σ new_stored 51,914,555 B = 1.078× Git (payload 49,761,387 B, metadata 2,153,168 B); net − Σ new_stored +21,100,741 B (28.9% of net); file-only net (no WAL) 68,820,992 B = 1.429× Git, WAL 4,194,304 B.
- D03 PostgreSQL: net 93,388,800 B = 1.939× Git pack+idx, 0.216× Σ tar|zstd-3, 0.503× the CDC oracle. Σ new_stored 51,914,864 B = 1.078× Git (payload 49,761,387 B, metadata 2,153,477 B); net − Σ new_stored +41,473,936 B (44.4% of net); server WAL generated floor→final 125,954,808 B (diagnostic, not Store bytes).
- Context only: dsh-dedup v1.0.0 (SDK route, Init of state 1, older policy history) recorded 53,125,120 B (D10) and 69,455,872 B (D03) of Store allocation, with offline payload 41,472,751 B / 51,897,185 B and metadata 1,325,047 B / 2,457,063 B. Not comparable as a baseline.

## Limits

- One sample per row on Docker Desktop (arm64 Mac). Byte counts, not speed; no other machine is run.
- SQLite Store bytes are `file.bytes + file.wal_bytes`; the product leaves a WAL after quiesce (capped at 4 MiB here), which can hold already-checkpointed frames. The parts and the allocated bytes are listed separately.
- PostgreSQL Store bytes are the `layerfs` schema's relation sizes (tables, TOAST, indexes); server WAL is not part of the Store and is recorded only as a WAL position (diagnostic).
- Bytes outside Commit packs (net − Σ new_stored) are measured once per row, not per Commit: the CLI exposes no Store-wide total between Commits without closing the Workspace.
- The CDC oracle is approximate and has no delta encoding, so it is a dedup-only reference, not a lower bound.
- dsh-dedup v1.0.0 numbers came through the SDK route (Init of state 1, older policy history) and are context, not a baseline.

## Cleanup

Final cleanup: **COMPLETE**.
- docker-worker: `machine stop docker` exit 0
- docker-worker-container: `docker rm lfs-07d9bae0-docker` exit 0
- docker-data: `volume rm lfs-07d9bae0-docker-data` exit 0
- postgres-stop: `-t 5 fsd-pg` exit 0
- postgres-container: `docker rm fsd-pg` exit 0
- postgres-data: `volume rm fsd-pg-data` exit 0
- suite-image: `image rm fs-storage-dsh:v1-6d820c75` exit 0
