**3 of 4 rows PASS (applied, committed, measured and verified at state 157); net Store bytes D10 57,081,856 B SQLite / 70,008,832 B PostgreSQL, D03 72,966,144 B / — B, against a Git pack + idx of 41,805,317 / 48,166,223 B; final cleanup INCOMPLETE.**

Storage only: every number is an exact byte count from the public CLI (`store status`, `commit list`) or the Docker worker volume; wall times are INELIGIBLE diagnostics. Bytes are exact integers. MB = 10⁶ B; MiB = 2²⁰ B = 1,048,576 B. Wall times are INELIGIBLE diagnostics, never speed claims.

## Raw vs stored

**Raw** is Σ logical: the bytes of every committed snapshot, as if each were stored in full. **Stored** is the net Store bytes (SQLite: file + WAL; PostgreSQL: schema). **Raw ÷ stored** is the overall reduction, = exact dedup × delta + zstd ÷ Store overhead: **exact dedup** = raw ÷ Σ new_canonical (identical files, chunks and trees stored once); **delta + zstd** = Σ new_canonical ÷ Σ new_stored (delta encoding and compression of the new objects); **Store overhead** = stored ÷ Σ new_stored (database pages, indexes and free space around the packs; 1.35 means the Store is 35% larger than its packs).

| Case | Database | Raw (MB) | Stored (MB) | Raw ÷ stored (×) | Exact dedup (×) | Delta + zstd (×) | Store overhead (×) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| D10 | SQLite | 561.0 | 57.1 | 9.83 | 1.48 | 9.17 | 1.38 |
| D10 | PostgreSQL | 561.0 | 70.0 | 8.01 | 1.48 | 9.17 | 1.69 |
| D03 | SQLite | 1,676.8 | 73.0 | 22.98 | 2.84 | 11.37 | 1.41 |

## Configuration

| Item | Value |
| --- | --- |
| LayerFS source | `b4fa173e401fc87af6610c151225096288e4ba57` (`layerfs_v2_0_0`) |
| CLI / daemon SHA-256 | `69d320f8f9fe86bf78ac18ab7c1a9c0e44c933b2c2493763bd2282e1dff9a348` / `e04a45593a206338696fd7748f205a272f46ebb754e4b49c40aeb0953ce70000` |
| Linux bundle seal | `a8c8daf34097cc61e21ac07b6f5de32b76a7c4a485601ee7c8d6668a2c612d37` (release, reused unchanged) |
| Sandbox image | `fs-storage-dsh:v1-b4fa173e` = `sha256:2ffe8b95d8568171126f1afb6e43cb67d8f1e77d0419dbf7f4da7d560cbe7c39`, FROM `sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e` (Debian 12, Python 3.11.2, git 2.39.5) |
| Seed | `git-snapshots-157-v1/snapshots.git` (157 trees, linear Commits), local pinned copy, not published; pack SHA-256 `27c7598c04404730200654a1a4ad8f000d63d41da87531cc6e8f206a4e8133bc`; seed file-set identity `898134b8a7b5fbc3f5aeb9366347c427fce35629e82dcef671e4a787eda5ba2b` (pack, idx, rev, bitmap, refs, `mapping.json`, corpus `checkpoint-manifest.json` `03f21acf…334271`, state-157 oracle `10e705a3…295e3c`) |
| Workload | `fs-storage-dsh-v1`: empty project → per state one Exec `apply.py <prev> <k>` + one Commit → final `verify.py 157` |
| Write method | in-place O_WRONLY\|O_TRUNC rewrite of changed regular files (same inode); unlink for removed paths and file<->symlink type changes; O_CREAT\|O_EXCL for new paths; symlink retarget = unlink + symlink; chmod for mode-only changes; emptied directories removed |
| Storage policy | LayerFS 2.0 fixed policy: CDC GEAR 8/16/32 KiB for files >= 128 KiB, whole-file objects below; zstd prefix deltas depth 16 (whole file) / 8 (chunk) / 8 (metadata); per-object zstd level 3; append-only packs (fixed in 2.0; recorded, not varied) |
| Machine | Docker only (private home, `LAYERFS_CONSTRUCTION_WORKERS=1`); Apple M3 Max (14 cores, 36 GiB), macOS 26.4; Docker Desktop (linuxkit, 8 CPUs, 7.75 GiB, shared with other #84 subagents); dedicated PostgreSQL 17 container fsopt-ref-pg (1 CPU, 512 MiB) at 127.0.0.1:55484 |
| PostgreSQL | sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652 (postgres:17-bookworm), 1 CPU / 512 MiB, 127.0.0.1:55484, container `fsopt-ref-pg`, one fresh empty database per row, `--synchronous-commit off` |
| Command bound | each CLI call 110 s; no retries |
| Campaigns | `fsd-ref-b4fa`; repeat `fsd-ref-b4fa-r` |

## Rows

| Case | Database | Campaign | Outcome | Commits | Verify | Row cleanup | Wall s (INELIGIBLE) |
| --- | --- | --- | --- | --- | --- | --- | ---: |
| D10 | SQLite | fsd-ref-b4fa | PASS | 17 | PASS | COMPLETE | 145.2 |
| D10 | PostgreSQL | fsd-ref-b4fa | PASS | 17 | PASS | COMPLETE | 683.4 |
| D03 | SQLite | fsd-ref-b4fa | PASS | 53 | PASS | COMPLETE | 219.9 |
| D03 | PostgreSQL | fsd-ref-b4fa | FAIL | 0 | SKIPPED | INCOMPLETE | 363.6 |

## D10: 17 states

Selection `[1, 11, 21, 31, 41, 51, 61, 71, 81, 91, 101, 111, 121, 131, 141, 151, 157]`. Logical bytes (Σ states, files + symlink targets) 561,010,345 B; LayerFS Σ Commit `logical` counts regular files only.

### Store bytes

| Case | Database | Outcome | Floor (B) | Final (B) | Net (B) | Net (MB) | Net (MiB) | Net file (B) | Net WAL (B) | Net allocated (B) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D10 | SQLite | PASS | 212,992 | 57,294,848 | 57,081,856 | 57.082 | 54.438 | 52,887,552 | 4,194,304 | 57,085,952 |
| D10 | PostgreSQL | PASS | 753,664 | 70,762,496 | 70,008,832 | 70.009 | 66.766 | — | — | — |

### Attribution

| Case | Database | Commits | Σ logical (B) | Σ new_canonical (B) | Σ new_stored (B) | Σ new_metadata (B) | Σ payload = stored − metadata (B) | Net (B) | Net − Σ new_stored (B) | Spec unattributed (B) | Logical ÷ net |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| D10 | SQLite | 17 | 561,008,218 | 380,287,990 | 41,473,188 | 1,019,473 | 40,453,715 | 57,081,856 | +15,608,668 | +14,589,195 | 9.83 |
| D10 | PostgreSQL | 17 | 561,008,218 | 380,287,990 | 41,472,330 | 1,018,663 | 40,453,667 | 70,008,832 | +28,536,502 | +27,517,839 | 8.01 |

### References and ratios

| Case | Whole-file unique (B) | Σ tar\|zstd-3 (B) | Git pack+idx (B) | CDC oracle, approx. (B) |
| --- | ---: | ---: | ---: | ---: |
| D10 | 371,937,053 | 144,803,423 | 41,805,317 | 125,322,715 |

| Case | Database | Net (B) | Net ÷ whole-file unique | Net ÷ Σ tar\|zstd-3 | Net ÷ Git pack+idx | Net ÷ CDC oracle (approx.) |
| --- | --- | ---: | --- | --- | --- | ---: |
| D10 | SQLite | 57,081,856 | 0.153 | 0.394 | 1.365 | 0.455 |
| D10 | PostgreSQL | 70,008,832 | 0.188 | 0.483 | 1.675 | 0.559 |

Net ÷ whole-file unique is the space amplification against ideal unique (uncompressed) bytes.

### new_stored curve

| Database | Commit 1 new_stored (B) | Σ Commits 2… (B) | Median Commit 2… (B) | Max Commit 2… (B) | Largest three |
| --- | ---: | ---: | ---: | ---: | --- |
| SQLite | 510,070 | 40,963,118 | 2,691,329 | 5,387,736 | state 141, state 131, state 101 |
| PostgreSQL | 510,072 | 40,962,258 | 2,691,149 | 5,387,566 | state 141, state 131, state 101 |

<details><summary>Per-Commit bytes</summary>

| Commit | State | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 1,499,065 | 510,070 | 5,920 | 510,072 | 5,922 |
| 2 | 11 | 6,673,091 | 1,707,482 | 16,787 | 1,707,497 | 16,802 |
| 3 | 21 | 9,643,584 | 1,367,421 | 19,967 | 1,367,975 | 20,521 |
| 4 | 31 | 11,884,222 | 1,045,651 | 21,902 | 1,045,660 | 21,911 |
| 5 | 41 | 18,790,418 | 2,806,349 | 44,308 | 2,807,847 | 45,806 |
| 6 | 51 | 21,988,592 | 2,468,275 | 45,172 | 2,468,818 | 45,715 |
| 7 | 61 | 26,001,039 | 2,642,136 | 60,741 | 2,641,794 | 60,399 |
| 8 | 71 | 27,706,574 | 1,131,885 | 37,674 | 1,131,317 | 37,106 |
| 9 | 81 | 33,740,150 | 2,740,522 | 53,930 | 2,740,504 | 53,912 |
| 10 | 91 | 36,248,656 | 1,465,042 | 49,874 | 1,464,924 | 49,756 |
| 11 | 101 | 40,562,402 | 3,259,445 | 79,849 | 3,259,397 | 79,801 |
| 12 | 111 | 44,387,500 | 2,788,944 | 72,772 | 2,788,428 | 72,256 |
| 13 | 121 | 46,737,173 | 2,195,493 | 81,909 | 2,194,607 | 81,023 |
| 14 | 131 | 50,909,755 | 3,940,926 | 100,506 | 3,939,718 | 99,274 |
| 15 | 141 | 57,785,130 | 5,387,736 | 112,193 | 5,387,566 | 112,023 |
| 16 | 151 | 61,430,344 | 2,894,801 | 106,090 | 2,895,356 | 106,693 |
| 17 | 157 | 65,020,523 | 3,121,010 | 109,879 | 3,120,850 | 109,743 |

</details>

## D03: 53 states

Selection `[1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34, 37, 40, 43, 46, 49, 52, 55, 58, 61, 64, 67, 70, 73, 76, 79, 82, 85, 88, 91, 94, 97, 100, 103, 106, 109, 112, 115, 118, 121, 124, 127, 130, 133, 136, 139, 142, 145, 148, 151, 154, 157]`. Logical bytes (Σ states, files + symlink targets) 1,676,767,835 B; LayerFS Σ Commit `logical` counts regular files only.

### Store bytes

| Case | Database | Outcome | Floor (B) | Final (B) | Net (B) | Net (MB) | Net (MiB) | Net file (B) | Net WAL (B) | Net allocated (B) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D03 | SQLite | PASS | 212,992 | 73,179,136 | 72,966,144 | 72.966 | 69.586 | 68,771,840 | 4,194,304 | 72,974,336 |
| D03 | PostgreSQL | FAIL | — | — | — | — | — | — | — | — |

### Attribution

| Case | Database | Commits | Σ logical (B) | Σ new_canonical (B) | Σ new_stored (B) | Σ new_metadata (B) | Σ payload = stored − metadata (B) | Net (B) | Net − Σ new_stored (B) | Spec unattributed (B) | Logical ÷ net |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| D03 | SQLite | 53 | 1,676,761,730 | 590,109,407 | 51,914,676 | 2,153,449 | 49,761,227 | 72,966,144 | +21,051,468 | +18,898,019 | 22.98 |
| D03 | PostgreSQL | — | — | — | — | — | — | — | — | — | — |

### References and ratios

| Case | Whole-file unique (B) | Σ tar\|zstd-3 (B) | Git pack+idx (B) | CDC oracle, approx. (B) |
| --- | ---: | ---: | ---: | ---: |
| D03 | 583,508,670 | 431,678,858 | 48,166,223 | 185,578,564 |

| Case | Database | Net (B) | Net ÷ whole-file unique | Net ÷ Σ tar\|zstd-3 | Net ÷ Git pack+idx | Net ÷ CDC oracle (approx.) |
| --- | --- | ---: | --- | --- | --- | ---: |
| D03 | SQLite | 72,966,144 | 0.125 | 0.169 | 1.515 | 0.393 |
| D03 | PostgreSQL | — | — | — | — | — |

Net ÷ whole-file unique is the space amplification against ideal unique (uncompressed) bytes.

### new_stored curve

| Database | Commit 1 new_stored (B) | Σ Commits 2… (B) | Median Commit 2… (B) | Max Commit 2… (B) | Largest three |
| --- | ---: | ---: | ---: | ---: | --- |
| SQLite | 510,070 | 51,404,606 | 722,027 | 4,228,483 | state 139, state 112, state 124 |

<details><summary>Per-Commit bytes</summary>

| Commit | State | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) |
| ---: | --- | ---: | ---: | ---: |
| 1 | 1 | 1,499,065 | 510,070 | 5,920 |
| 2 | 4 | 2,755,783 | 616,983 | 9,228 |
| 3 | 7 | 4,730,480 | 533,553 | 9,507 |
| 4 | 10 | 6,292,998 | 560,320 | 11,555 |
| 5 | 13 | 8,090,311 | 755,800 | 14,335 |
| 6 | 16 | 10,134,675 | 828,977 | 14,478 |
| 7 | 19 | 9,928,676 | 636,579 | 16,738 |
| 8 | 22 | 11,918,884 | 862,257 | 19,850 |
| 9 | 25 | 9,619,865 | 182,229 | 9,999 |
| 10 | 28 | 9,571,541 | 271,657 | 9,875 |
| 11 | 31 | 11,884,222 | 99,873 | 22,182 |
| 12 | 34 | 13,725,702 | 927,415 | 26,028 |
| 13 | 37 | 14,079,233 | 486,408 | 21,838 |
| 14 | 40 | 15,681,876 | 555,995 | 25,048 |
| 15 | 43 | 15,133,981 | 244,891 | 16,166 |
| 16 | 46 | 20,707,366 | 1,973,306 | 40,743 |
| 17 | 49 | 21,455,669 | 502,940 | 23,899 |
| 18 | 52 | 23,613,743 | 2,277,604 | 49,405 |
| 19 | 55 | 24,603,261 | 887,156 | 38,076 |
| 20 | 58 | 24,832,756 | 545,250 | 29,345 |
| 21 | 61 | 26,001,039 | 753,908 | 39,666 |
| 22 | 64 | 26,000,102 | 144,109 | 20,665 |
| 23 | 67 | 27,352,902 | 854,656 | 35,804 |
| 24 | 70 | 29,109,146 | 848,653 | 34,334 |
| 25 | 73 | 29,605,381 | 393,452 | 27,050 |
| 26 | 76 | 25,923,290 | 165,537 | 27,721 |
| 27 | 79 | 29,818,502 | 235,968 | 49,929 |
| 28 | 82 | 30,071,409 | 201,677 | 16,773 |
| 29 | 85 | 35,732,482 | 2,698,743 | 56,341 |
| 30 | 88 | 36,405,883 | 384,642 | 30,155 |
| 31 | 91 | 36,248,656 | 505,446 | 30,119 |
| 32 | 94 | 35,569,851 | 486,788 | 43,561 |
| 33 | 97 | 37,903,402 | 1,745,093 | 56,995 |
| 34 | 100 | 39,890,945 | 1,145,702 | 51,627 |
| 35 | 103 | 42,098,284 | 1,746,633 | 59,746 |
| 36 | 106 | 38,526,923 | 392,817 | 55,325 |
| 37 | 109 | 27,578,572 | 377,276 | 46,417 |
| 38 | 112 | 44,749,350 | 4,050,127 | 102,616 |
| 39 | 115 | 45,895,027 | 819,467 | 50,046 |
| 40 | 118 | 46,505,955 | 831,983 | 48,744 |
| 41 | 121 | 46,737,173 | 499,722 | 42,874 |
| 42 | 124 | 48,051,342 | 2,760,927 | 84,670 |
| 43 | 127 | 49,186,602 | 737,440 | 49,511 |
| 44 | 130 | 50,310,613 | 706,614 | 48,957 |
| 45 | 133 | 52,740,991 | 1,727,402 | 76,721 |
| 46 | 136 | 50,949,557 | 237,882 | 48,292 |
| 47 | 139 | 57,151,518 | 4,228,483 | 103,651 |
| 48 | 142 | 59,351,166 | 1,231,862 | 62,200 |
| 49 | 145 | 60,447,336 | 1,548,503 | 77,712 |
| 50 | 148 | 60,711,516 | 617,549 | 35,668 |
| 51 | 151 | 61,430,344 | 1,302,796 | 78,355 |
| 52 | 154 | 63,425,861 | 2,466,416 | 104,857 |
| 53 | 157 | 65,020,523 | 807,140 | 42,132 |

</details>

## Determinism

D10 SQLite repeated once in campaign `fsd-ref-b4fa-r` (outcome PASS), same product, image and seed. Per-Commit new_stored identical: **False** (largest per-Commit difference 185 B); per-Commit new_metadata identical: **False**. The Store is not byte-identical on repeat; see the table.

| Metric | First run | Repeat | Δ |
| --- | --- | --- | --- |
| Net file bytes, no WAL (B) | 52,887,552 | 52,809,728 | -77,824 |
| Net WAL bytes (B) | 4,194,304 | 4,194,304 | +0 |
| Net file + WAL (B) | 57,081,856 | 57,004,032 | -77,824 |
| Net allocated (B) | 57,085,952 | 57,012,224 | -73,728 |
| Σ new_stored (B) | 41,473,188 | 41,472,970 | -218 |
| Σ new_metadata (B) | 1,019,473 | 1,019,255 | -218 |

## Reference pins

| Case | references JSON SHA-256 | State manifests | Git pack+idx recomputed (B) | dsh-dedup v1.0.0 pin (B) | Δ (B) |
| --- | --- | --- | ---: | ---: | ---: |
| D10 | `2cce87d007082e687e32b0bf7136f95b76c1278f5619924e554278c8e9cf561a` | `5208278e51ad9e9a…` | 41,805,317 | 41,797,536 | +7,781 |
| D03 | `ec492f61045c327ac4d590b93e73d109bb8c241e165b757d9879ac11f597b3ac` | `d4872e67f21170f4…` | 48,166,223 | 48,169,384 | -3,161 |

Git: git version 2.39.5, dsh-dedup v1.0.0 (commit-tree from seed trees, repack -a -d -f -F --window=10 --depth=50 --threads=2). With `--threads=2` the pack varies by a few kB between runs (a second D10 run gave 41,801,497 B); the pins (git 2.47.1) are confirmed within 0.02%. Whole-file unique, Σ tar|zstd-3 (deterministic PAX tar, zstd 1.5.7 `-3 -T1`) and the CDC oracle (**approximate**: gear 8/16/32 KiB, cutoff 128 KiB, own gear table; Σ min(raw, zstd-3) of unique objects, no deltas) come from `shared/src/references.py` over the states materialized in the suite image with the workload's own `apply.py`; state 157 matched its corpus oracle.

## Observations

- `new_stored` is all new pack bytes of a Commit and `new_metadata` its metadata subset (LayerFS 2.0 CommitStatistics), so payload = stored − metadata and the Store bytes no Commit accounts for are net − Σ new_stored. The spec formula net − (Σ new_stored + Σ new_metadata) counts metadata twice; it is listed as "Spec unattributed" only for comparability.
- D10 SQLite: net 57,081,856 B = 1.365× Git pack+idx, 0.394× Σ tar|zstd-3, 0.455× the CDC oracle. Σ new_stored 41,473,188 B = 0.992× Git (payload 40,453,715 B, metadata 1,019,473 B); net − Σ new_stored +15,608,668 B (27.3% of net); file-only net (no WAL) 52,887,552 B = 1.265× Git, WAL 4,194,304 B.
- D10 PostgreSQL: net 70,008,832 B = 1.675× Git pack+idx, 0.483× Σ tar|zstd-3, 0.559× the CDC oracle. Σ new_stored 41,472,330 B = 0.992× Git (payload 40,453,667 B, metadata 1,018,663 B); net − Σ new_stored +28,536,502 B (40.8% of net); server WAL generated floor→final 93,533,472 B (diagnostic, not Store bytes).
- D03 SQLite: net 72,966,144 B = 1.515× Git pack+idx, 0.169× Σ tar|zstd-3, 0.393× the CDC oracle. Σ new_stored 51,914,676 B = 1.078× Git (payload 49,761,227 B, metadata 2,153,449 B); net − Σ new_stored +21,051,468 B (28.9% of net); file-only net (no WAL) 68,771,840 B = 1.428× Git, WAL 4,194,304 B.
- Context only: dsh-dedup v1.0.0 (SDK route, Init of state 1, older policy history) recorded 53,125,120 B (D10) and 69,455,872 B (D03) of Store allocation, with offline payload 41,472,751 B / 51,897,185 B and metadata 1,325,047 B / 2,457,063 B. Not comparable as a baseline.

## Before/after vs 6d820c756b

Post-#581 reference for layerfs-project#84. Base `layerfs_v2_0_0` @ `b4fa173e40` against the 2026-11-06 report on `6d820c756b` ([report](../../fs-storage-dsh/6d820c756b9b12541ac84af7b88467069f31bcbf/report.md)), same workload, seed, references and route. Δ = base − 6d820c756b; Δ% of the 6d820c756b value. Bytes are exact.

| Case | Database | Net 6d820c756b (B) | Net base (B) | Δ net (B) | Δ net % | Σ new_stored 6d820c756b (B) | Σ new_stored base (B) | Δ (B) | Δ % | Σ new_metadata 6d820c756b (B) | Σ new_metadata base (B) | Δ (B) | Δ % |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D10 | SQLite | 56,139,776 | 57,081,856 | +942,080 | +1.68% | 41,473,149 | 41,473,188 | +39 | +0.00% | 1,019,282 | 1,019,473 | +191 | +0.02% |
| D10 | PostgreSQL | 69,967,872 | 70,008,832 | +40,960 | +0.06% | 41,473,341 | 41,472,330 | -1,011 | -0.00% | 1,019,474 | 1,018,663 | -811 | -0.08% |
| D03 | SQLite | 73,015,296 | 72,966,144 | -49,152 | -0.07% | 51,914,555 | 51,914,676 | +121 | +0.00% | 2,153,168 | 2,153,449 | +281 | +0.01% |
| D03 | PostgreSQL | 93,388,800 | — | — | — | 51,914,864 | — | — | — | 2,153,477 | — | — | — |

- **Commit counters are unchanged within metadata drift.** Σ new_canonical and Σ logical are identical. Σ new_stored moves by +39 B (D10 SQLite), −1,011 B (D10 PostgreSQL) and +121 B (D03 SQLite), almost all in new_metadata; Σ payload (new_stored − new_metadata) is 40,453,715 B on D10 SQLite (both base runs) and 40,453,667 B on D10 PostgreSQL, against 40,453,867 B on 6d820c756b (−152 B / −200 B, 0.0004%).
- **PostgreSQL D10 net +40,960 B (+0.06%)**, five pages' worth of schema bytes.
- **SQLite moves only in the main file** (WAL 4,194,304 B in every row): D10 file-only net +942,080 B (51,945,472 → 52,887,552 B), D03 −49,152 B. The D10 repeat on the base differed by −77,824 B file-only, and the 6d820c756b repeat by +28,672 B, so the D10 SQLite move is larger than either repeat but its packs are the same; it is SQLite page layout/free space, not LayerFS objects (not traced; no dbstat).
- **D03 PostgreSQL has no reference value on the base (FAIL, see below).** Over the 33 Commits it did complete (states 1–97), Σ new_canonical and Σ logical equal 6d820c756b's first 33 Commits exactly and Σ new_stored is 23,675,918 B against 23,677,888 B (−1,970 B, all metadata: −1,986 B). Its Store held 41,664,512 B of schema bytes at state 97 (not a quiesced-final measurement).

## D03 PostgreSQL failure

The 33rd Commit (state 94 → 97, an Exec that rewrote 2,435 files / 19,900,592 B) exceeded the per-command bound: the harness killed the CLI at 110 s (`process exit -9`, uncertain), so the row is **FAIL** and its Store is kept. Read-only inspection afterwards (`store status`, `commit list`) showed the Commit had landed about 117 s after it started (≈7 s after the kill), the Store idle with no holders. The Workspace was then unmounted and the Sandbox closed through the CLI; Store bytes were 41,664,512 B before and after. The row was not rerun.

Wall times (INELIGIBLE diagnostics, not speed claims): the earlier Commits of this row took 0–20 s each, and the same Commit took about 16 s on 6d820c756b. Row walls were D10 SQLite 145.2 s (54.0 s on 6d820c756b), D10 PostgreSQL 683.4 s (192.5 s) and D03 SQLite 219.9 s (182.1 s). During the run, other #84 subagents were running Linux cargo builds on the shared Docker Desktop VM (two build containers at ≈290% CPU each were observed right after the failure). Contention therefore can't be separated from the product. A D03 PostgreSQL reference needs a new row on a fresh Store in a quieter window; whether the PostgreSQL Commit path is slower on the base is a separate question for a timing benchmark.

## Limits

- One sample per row on Docker Desktop (arm64 Mac). Byte counts, not speed; no other machine is run.
- SQLite Store bytes are `file.bytes + file.wal_bytes`; the product leaves a WAL after quiesce (capped at 4 MiB here), which can hold already-checkpointed frames. The parts and the allocated bytes are listed separately.
- PostgreSQL Store bytes are the `layerfs` schema's relation sizes (tables, TOAST, indexes); server WAL is not part of the Store and is recorded only as a WAL position (diagnostic).
- Bytes outside Commit packs (net − Σ new_stored) are measured once per row, not per Commit: the CLI exposes no Store-wide total between Commits without closing the Workspace.
- The CDC oracle is approximate and has no delta encoding, so it is a dedup-only reference, not a lower bound.
- dsh-dedup v1.0.0 numbers came through the SDK route (Init of state 1, older policy history) and are context, not a baseline.

## Cleanup

Final cleanup: **INCOMPLETE**.
- D10 SQLite, D03 SQLite and the D10 SQLite repeat Stores: `store remove` by the driver; D10 PostgreSQL Store: `store disconnect` by the driver, then its database `fsr_d10_docker` dropped (`dropdb`)
- Failed row D03 PostgreSQL: Workspace `unmount` and Sandbox `close` through the CLI after a read-only inspection showed the killed Commit had landed (no Store bytes changed: 41,664,512 B before and after)
- docker-worker: `machine stop docker` exit 0
- docker-worker-container: `docker rm lfs-263153b4-docker` exit 0
- docker-data: `docker volume rm lfs-263153b4-docker-data` exit 0
- suite-image: `docker image rm fs-storage-dsh:v1-b4fa173e` exit 0
- Retained: failed-row evidence: Store `q-fsd-ref-b4fa-d03-docker-postgresql` (PostgreSQL database `fsr_d03_docker`, 33 Commits through state 97, schema 41,664,512 B) and its record in the private home
- Retained: PostgreSQL server `fsopt-ref-pg` and data volume `fsopt-ref-pg-data`, which hold that database (`run.py finish` retained every resource for retained row custody; the non-evidence ones were then released as listed above)
