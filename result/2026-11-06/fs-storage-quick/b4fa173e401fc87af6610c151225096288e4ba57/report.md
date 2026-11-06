# fs-storage-quick — b4fa173e40

**12 of 12 fs-storage-quick rows PASS with verified final state on the base build, pinned as the #84 baseline; matrix wall SQLite 52.9 s and PostgreSQL 117.4 s (INELIGIBLE, target ≤ 120 s per backend); after the late probe every SQLite Store had 0 B of WAL (Q1 8,798,208 → 4,796,416 B net) and Q6 PostgreSQL shrank 38,158,336 → 31,358,976 B; a same-build repeat stayed within noise; cleanup COMPLETE.**

Store bytes for six quick storage workloads on LayerFS 2.0 (Docker machine, SQLite and PostgreSQL Stores), measured at a quiesced boundary through the public CLI. This subset is the before/after gate of the #84 storage optimizations (`run.py compare` against this baseline); the full fs-storage suites remain the release check. Bytes are exact integers. MB = 10⁶ B; MiB = 2²⁰ B = 1,048,576 B. Wall times are INELIGIBLE diagnostics, never speed claims.

## Raw vs stored

**Raw** is Σ logical: the bytes of every committed snapshot, as if each were stored in full. **Stored** is the net Store bytes (SQLite: file + WAL; PostgreSQL: schema). **Raw ÷ stored** is the overall reduction, = exact dedup × delta + zstd ÷ Store overhead: **exact dedup** = raw ÷ Σ new_canonical (identical files, chunks and trees stored once); **delta + zstd** = Σ new_canonical ÷ Σ new_stored (delta encoding and compression of the new objects); **Store overhead** = stored ÷ Σ new_stored (database pages, indexes and free space around the packs; 1.35 means the Store is 35% larger than its packs). Q6 imports its base with `project init`, which no Commit covers, so only the overall reduction is shown for it; its raw counts every Commit state plus the Init state.

| Case | Database | Raw (MB) | Stored (MB) | Raw ÷ stored (×) | Exact dedup (×) | Delta + zstd (×) | Store overhead (×) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Q1 | SQLite | 4.1 | 8.8 | 0.47 | 0.94 | 1.05 | 2.13 |
| Q1 | PostgreSQL | 4.1 | 6.1 | 0.67 | 0.94 | 1.05 | 1.48 |
| Q2 | SQLite | 12.1 | 1.7 | 7.02 | 1.00 | 19.86 | 2.82 |
| Q2 | PostgreSQL | 12.1 | 0.9 | 12.86 | 1.00 | 19.86 | 1.54 |
| Q3 | SQLite | 12.1 | 2.3 | 5.38 | 1.00 | 14.92 | 2.76 |
| Q3 | PostgreSQL | 12.1 | 1.3 | 9.02 | 1.00 | 14.92 | 1.65 |
| Q4 | SQLite | 12.1 | 2.3 | 5.36 | 1.00 | 14.92 | 2.77 |
| Q4 | PostgreSQL | 12.1 | 1.3 | 9.02 | 1.00 | 14.92 | 1.65 |
| Q5 | SQLite | 203.4 | 37.6 | 5.41 | 5.82 | 1.00 | 1.08 |
| Q5 | PostgreSQL | 203.4 | 36.7 | 5.54 | 5.82 | 1.00 | 1.05 |
| Q6 | SQLite | 1,560.5 | 27.7 | 56.43 | — | — | — |
| Q6 | PostgreSQL | 1,560.5 | 38.2 | 40.89 | — | — | — |

## Configuration

| Item | Value |
| --- | --- |
| LayerFS source | `b4fa173e401fc87af6610c151225096288e4ba57` |
| CLI / daemon (macOS, release) | `69d320f8f9fe86bf78ac18ab7c1a9c0e44c933b2c2493763bd2282e1dff9a348` / `e04a45593a206338696fd7748f205a272f46ebb754e4b49c40aeb0953ce70000` |
| Linux bundle seal | `a8c8daf34097cc61e21ac07b6f5de32b76a7c4a485601ee7c8d6668a2c612d37` |
| Sandbox image | `sha256:fedbb4077dc7cba7771ff10fd0ee2db8ec063a7cea657559819cdcbb4bfb5db5 (fs-storage-quick:v1)` (FROM runtime `sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e`) |
| Workload | `fs-storage-quick-v1`; gen.py `8ddd0ab6c6d6fc0984890b174c9f7dab085eca10167c1660a96757248e590a8d`; model.py `f44c6b23d3035c1af97da133103b2ddf57cf37d977c09e77f11377a46aa307de` |
| Pins | `src/pins.json` SHA-256 `0d40f379bb114eab63ea4b907fe623d5dab4940ba32c12cebf17b7c8e765b66e` |
| Harness | layerfs-benchmark `275e024a19aaea3f9d268a123774bbdd4e5da9e0` (suite dirty: False), sources `9dbce5c8a4565a9ae18c14aeb3202b0f0cfe21ead657de41dbe2ba442b288f0a` |
| Machine | Docker (`docker`), private `LAYERFS_HOME`, `LAYERFS_CONSTRUCTION_WORKERS=1`; rows serial, all SQLite then all PostgreSQL |
| Store bytes | SQLite: `store status` `file.bytes` (file) + `file.wal_bytes` (WAL); WAL frames = (WAL − 32) ÷ 4,120. PostgreSQL: `server.schemas.layerfs` |
| Floor | the row's own Store after create/connect + `project init` of an empty folder (+ `store push` for SQLite) |
| Late probe | one wait of 75.0 s after the last row (slept 74.95 s), then `store status` of 12 retained Stores, then release |

## Cases

| Case | Workload | Write method | Commits | Exercises |
| --- | --- | --- | --- | --- |
| Q1 | 2,000 files of 0–4,096 B in 20 directories, 1 Commit | new path | 1 | per-file rows: inode_value, object_location, file_digest; PostgreSQL row/index overhead |
| Q2 | 25 synthetic text files of 16–64 KiB, then 12 Commits each replacing 1% of lines in every file (in place) | in-place rewrite (same inode, O_WRONLY\|O_TRUNC) | 13 | chain budget / chain-root re-base |
| Q3 | the Q2 content sequence, written as temp file + rename over the old path | write temp file then rename over the old path | 13 | small-file delta base on rename-over |
| Q4 | the Q2 content sequence, each version at a new path (fNNN.vVV.txt), old path unlinked | new path per version, old path unlinked | 13 | similarity ring |
| Q5 | 32 MiB random file; insert 1 B at start; insert 1 B at middle; overwrite 4 KiB at middle; append 1 MiB; delete first byte | in-place rewrite (same inode, O_WRONLY\|O_TRUNC) | 6 | extent / directory page metadata |
| Q6 | 1 × `project init` of the 65.0 MB DSH-157 base; 20 edit Commits on lane (5 seeded operations each); 3 Branches from main with the same single Commit | model ops: in-place edit/append, new path, unlink, rename | 23 | Init staging cleanup, per-Commit rows and metadata, Branch cost |

## Rows and matrix wall

| Case | Database | Execution | Final-state verification | Cleanup | Commits | Row wall (s, INELIGIBLE) | Reason |
| --- | --- | --- | --- | --- | --- | ---: | --- |
| Q1 | SQLite | PASS | PASS | COMPLETE | 1 | 4.7 |  |
| Q1 | PostgreSQL | PASS | PASS | COMPLETE | 1 | 20.9 |  |
| Q2 | SQLite | PASS | PASS | COMPLETE | 13 | 6.2 |  |
| Q2 | PostgreSQL | PASS | PASS | COMPLETE | 13 | 11.0 |  |
| Q3 | SQLite | PASS | PASS | COMPLETE | 13 | 6.4 |  |
| Q3 | PostgreSQL | PASS | PASS | COMPLETE | 13 | 11.9 |  |
| Q4 | SQLite | PASS | PASS | COMPLETE | 13 | 6.1 |  |
| Q4 | PostgreSQL | PASS | PASS | COMPLETE | 13 | 11.0 |  |
| Q5 | SQLite | PASS | PASS | COMPLETE | 6 | 5.6 |  |
| Q5 | PostgreSQL | PASS | PASS | COMPLETE | 6 | 12.8 |  |
| Q6 | SQLite | PASS | PASS | COMPLETE | 23 | 23.9 |  |
| Q6 | PostgreSQL | PASS | PASS | COMPLETE | 23 | 49.4 |  |

| Database | Rows | Matrix wall, first row start → last row end (s, INELIGIBLE) | Σ row wall (s, INELIGIBLE) |
| --- | --- | ---: | ---: |
| SQLite | 6 | 52.9 | 52.8 |
| PostgreSQL | 6 | 117.4 | 117.0 |

## Store bytes

SQLite file and WAL are separate: a quiesced Store keeps up to 4 MiB of WAL (`journal_size_limit`). The late probe re-reads every Store after one wait (SQLite after the worker's 60 s idle close; PostgreSQL after autovacuum had a chance).

| Case | Database | Floor (B) | Final (B) | Net (B) | Net (MB) | Net file (B) | Final WAL (B) | Final WAL frames | Late net (B) | Late net file (B) | Late WAL (B) | Late idle (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| Q1 | SQLite | 212,992 | 9,011,200 | 8,798,208 | 8.798 | 4,603,904 | 4,194,304 | at 4 MiB limit | 4,796,416 | 4,796,416 | 0 | 240.7 |
| Q1 | PostgreSQL | 753,664 | 6,864,896 | 6,111,232 | 6.111 | — | — | — | 6,160,384 | — | — | 173.1 |
| Q2 | SQLite | 212,992 | 1,939,304 | 1,726,312 | 1.726 | 0 | 1,726,312 | 419 | 675,840 | 675,840 | 0 | 234.8 |
| Q2 | PostgreSQL | 753,664 | 1,695,744 | 942,080 | 0.942 | — | — | — | 942,080 | — | — | 162.6 |
| Q3 | SQLite | 212,992 | 2,466,664 | 2,253,672 | 2.254 | 0 | 2,253,672 | 547 | 917,504 | 917,504 | 0 | 228.7 |
| Q3 | PostgreSQL | 753,664 | 2,097,152 | 1,343,488 | 1.343 | — | — | — | 1,343,488 | — | — | 151.1 |
| Q4 | SQLite | 212,992 | 2,474,904 | 2,261,912 | 2.262 | 0 | 2,261,912 | 549 | 917,504 | 917,504 | 0 | 222.8 |
| Q4 | PostgreSQL | 753,664 | 2,097,152 | 1,343,488 | 1.343 | — | — | — | 1,343,488 | — | — | 140.6 |
| Q5 | SQLite | 212,992 | 37,818,368 | 37,605,376 | 37.605 | 33,411,072 | 4,194,304 | at 4 MiB limit | 35,098,624 | 35,098,624 | 0 | 217.5 |
| Q5 | PostgreSQL | 753,664 | 37,445,632 | 36,691,968 | 36.692 | — | — | — | 36,708,352 | — | — | 128.2 |
| Q6 | SQLite | 212,992 | 27,864,752 | 27,651,760 | 27.652 | 24,199,168 | 3,452,592 | 838 | 24,367,104 | 24,367,104 | 0 | 193.9 |
| Q6 | PostgreSQL | 753,664 | 38,912,000 | 38,158,336 | 38.158 | — | — | — | 31,358,976 | — | — | 79.1 |

## Q6 Init floors

| Case | Database | Probe | Store (B) | Δ previous probe (B) | WAL (B) |
| --- | --- | --- | ---: | ---: | ---: |
| Q6 | SQLite | init_p1 | 24,412,160 | +24,199,168 | 0 |
| Q6 | SQLite | final (after Commits) | 27,864,752 | +3,452,592 | 3,452,592 |
| Q6 | PostgreSQL | init_p1 | 38,633,472 | +37,879,808 | — |
| Q6 | PostgreSQL | final (after Commits) | 38,912,000 | +278,528 | — |

## Per-Commit attribution

In LayerFS 2.0 `new_stored` counts all new pack bytes and `new_metadata` is its metadata-domain subset, so payload = stored − metadata; **net − Σ new_stored** is what no Commit's packs account for (database pages, indexes, free space, the SQLite WAL, and for Q6 the base Init).

| Case | Database | Commits | Raw = Σ logical (+ Init) (B) | Σ new_canonical (B) | Σ new_stored (B) | Σ payload (B) | Σ new_metadata (B) | Net (B) | Net − Σ new_stored (B) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Q1 | SQLite | 1 | 4,103,985 | 4,356,403 | 4,132,314 | 4,115,113 | 17,201 | 8,798,208 | +4,665,894 |
| Q1 | PostgreSQL | 1 | 4,103,985 | 4,356,403 | 4,132,321 | 4,115,113 | 17,208 | 6,111,232 | +1,978,911 |
| Q2 | SQLite | 13 | 12,116,994 | 12,157,920 | 612,161 | 606,688 | 5,473 | 1,726,312 | +1,114,151 |
| Q2 | PostgreSQL | 13 | 12,116,994 | 12,157,920 | 612,151 | 606,688 | 5,463 | 942,080 | +329,929 |
| Q3 | SQLite | 13 | 12,116,994 | 12,164,904 | 815,382 | 808,429 | 6,953 | 2,253,672 | +1,438,290 |
| Q3 | PostgreSQL | 13 | 12,116,994 | 12,164,904 | 815,394 | 808,429 | 6,965 | 1,343,488 | +528,094 |
| Q4 | SQLite | 13 | 12,116,994 | 12,166,204 | 815,499 | 808,429 | 7,070 | 2,261,912 | +1,446,413 |
| Q4 | PostgreSQL | 13 | 12,116,994 | 12,166,204 | 815,488 | 808,429 | 7,059 | 1,343,488 | +528,000 |
| Q5 | SQLite | 6 | 203,423,752 | 34,942,963 | 34,788,498 | 34,653,459 | 135,039 | 37,605,376 | +2,816,878 |
| Q5 | PostgreSQL | 6 | 203,423,752 | 34,942,963 | 34,788,498 | 34,653,459 | 135,039 | 36,691,968 | +1,903,470 |
| Q6 | SQLite | 23 | 1,560,458,138 | 1,292,935 | 72,135 | 20,118 | 52,017 | 27,651,760 | +27,579,625 |
| Q6 | PostgreSQL | 23 | 1,560,458,138 | 1,292,935 | 72,114 | 20,118 | 51,996 | 38,158,336 | +38,086,222 |

## Per-Commit curves

**Q1 tiny files**

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 4,103,985 | 4,132,314 | 17,201 | 4,132,321 | 17,208 |

**Q2 in-place edits**

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 930,725 | 322,083 | 519 | 322,083 | 519 |
| 2 | 930,462 | 7,078 | 412 | 7,076 | 410 |
| 3 | 931,473 | 7,289 | 409 | 7,291 | 411 |
| 4 | 931,535 | 7,374 | 410 | 7,375 | 411 |
| 5 | 932,181 | 7,385 | 411 | 7,386 | 412 |
| 6 | 932,241 | 7,193 | 415 | 7,190 | 412 |
| 7 | 932,570 | 7,385 | 412 | 7,383 | 410 |
| 8 | 932,599 | 7,268 | 416 | 7,264 | 412 |
| 9 | 932,441 | 67,666 | 412 | 67,665 | 411 |
| 10 | 932,476 | 25,544 | 395 | 25,547 | 398 |
| 11 | 932,662 | 72,658 | 421 | 72,654 | 417 |
| 12 | 932,886 | 52,019 | 421 | 52,015 | 417 |
| 13 | 932,743 | 21,219 | 420 | 21,222 | 423 |

**Q3 rename-over edits**

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 930,725 | 322,083 | 519 | 322,083 | 519 |
| 2 | 930,462 | 20,242 | 527 | 20,245 | 530 |
| 3 | 931,473 | 24,416 | 527 | 24,418 | 529 |
| 4 | 931,535 | 28,394 | 529 | 28,392 | 527 |
| 5 | 932,181 | 32,311 | 533 | 32,312 | 534 |
| 6 | 932,241 | 36,073 | 537 | 36,069 | 533 |
| 7 | 932,570 | 39,939 | 535 | 39,938 | 534 |
| 8 | 932,599 | 43,441 | 540 | 43,439 | 538 |
| 9 | 932,441 | 46,846 | 537 | 46,846 | 537 |
| 10 | 932,476 | 50,274 | 530 | 50,276 | 532 |
| 11 | 932,662 | 53,790 | 555 | 53,792 | 557 |
| 12 | 932,886 | 57,150 | 543 | 57,160 | 553 |
| 13 | 932,743 | 60,423 | 541 | 60,424 | 542 |

**Q4 new-path edits**

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 930,725 | 322,089 | 525 | 322,087 | 523 |
| 2 | 930,462 | 20,230 | 515 | 20,230 | 515 |
| 3 | 931,473 | 24,419 | 530 | 24,419 | 530 |
| 4 | 931,535 | 28,396 | 531 | 28,398 | 533 |
| 5 | 932,181 | 32,320 | 542 | 32,320 | 542 |
| 6 | 932,241 | 36,082 | 546 | 36,083 | 547 |
| 7 | 932,570 | 39,953 | 549 | 39,952 | 548 |
| 8 | 932,599 | 43,452 | 551 | 43,452 | 551 |
| 9 | 932,441 | 46,858 | 549 | 46,859 | 550 |
| 10 | 932,476 | 50,280 | 536 | 50,271 | 527 |
| 11 | 932,662 | 53,797 | 562 | 53,795 | 560 |
| 12 | 932,886 | 57,175 | 568 | 57,174 | 567 |
| 13 | 932,743 | 60,448 | 566 | 60,448 | 566 |

**Q5 large file**

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 33,554,432 | 33,651,782 | 61,106 | 33,651,782 | 61,106 |
| 2 | 33,554,433 | 5,618 | 5,564 | 5,618 | 5,564 |
| 3 | 33,554,434 | 16,850 | 16,667 | 16,850 | 16,667 |
| 4 | 33,554,434 | 41,478 | 30,437 | 41,478 | 30,437 |
| 5 | 34,603,010 | 1,067,039 | 15,642 | 1,067,039 | 15,642 |
| 6 | 34,603,009 | 5,731 | 5,623 | 5,731 | 5,623 |

**Q6** (per-Commit values in the exported JSON)

| Database | Branch | Commits | Σ new_stored (B) | Min (B) | Median (B) | Max (B) | Σ new_metadata (B) | Median new_metadata (B) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | p1@lane | 20 | 68,783 | 1,541 | 2,949 | 9,875 | 49,007 | 1,126 |
| SQLite | b01.. (identical) | 3 | 3,352 | 963 | 965 | 1,424 | 3,010 | 965 |
| PostgreSQL | p1@lane | 20 | 68,767 | 1,541 | 2,949 | 9,875 | 48,991 | 1,125 |
| PostgreSQL | b01.. (identical) | 3 | 3,347 | 961 | 962 | 1,424 | 3,005 | 962 |

## Diagnostics

What the public CLI exposes per Commit is `logical`, `new_canonical`, `new_stored` and `new_metadata` (bytes). Wall time of each Commit call and the CPU of the local CLI process come from the harness ledger and are INELIGIBLE diagnostics. **UNAVAILABLE** through the public CLI: worker/daemon Commit CPU, `value_lookups`/`value_rows`, pooled decode/read-amplification counters (`chain_edges`, `physical_group_decodes`, `branch_delta_applies`, …), delta depth and PostgreSQL round trips; the product collects some of them only on the SDK trace route, which benchmarks may not use.

| Case | Database | Σ Commit wall (ms) | Median Commit wall (ms) | Max Commit wall (ms) | Median CLI-process CPU per Commit (ms) | Init wall (ms) | Verify Exec wall (ms) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Q1 | SQLite | 411.2 | 411.2 | 411.2 | 10.2 | — | 997.8 |
| Q1 | PostgreSQL | 802.6 | 802.6 | 802.6 | 11.3 | — | 9509.0 |
| Q2 | SQLite | 826.0 | 59.1 | 89.0 | 11.2 | — | 167.6 |
| Q2 | PostgreSQL | 2342.5 | 183.6 | 241.2 | 10.5 | — | 249.7 |
| Q3 | SQLite | 752.3 | 57.4 | 74.2 | 11.3 | — | 160.6 |
| Q3 | PostgreSQL | 2588.7 | 187.3 | 386.5 | 12.1 | — | 170.5 |
| Q4 | SQLite | 848.0 | 61.0 | 107.1 | 12.1 | — | 119.3 |
| Q4 | PostgreSQL | 1893.6 | 131.9 | 271.3 | 11.2 | — | 162.8 |
| Q5 | SQLite | 586.0 | 35.95 | 421.4 | 11.7 | — | 374.9 |
| Q5 | PostgreSQL | 3154.7 | 228.6 | 1749.2 | 13.1 | — | 1344.1 |
| Q6 | SQLite | 1040.0 | 42.4 | 85.3 | 12.4 | 7374.9 | 1904.8, 957.6, 1145.2, 1659.9 |
| Q6 | PostgreSQL | 3197.7 | 135.9 | 311.5 | 11.4 | 16581.0 | 7398.3, 3546.7, 3345.0, 1751.4 |

## Observations

- **The SQLite WAL is most of a small Store.** Q2–Q4 never reached the 1,000-page autocheckpoint: the main file did not grow at all (net file 0 B) and 1.7–2.3 MB sat in the WAL. After the worker's idle close every SQLite Store had 0 B of WAL and was 1.1–4.0 MB smaller (Q1 8,798,208 → 4,796,416 B; Q6 27,651,760 → 24,367,104 B). This is the effect #86 targets; until it lands, compare SQLite file and WAL separately and read the late columns as closed bytes.
- **PostgreSQL Init garbage is visible immediately and shrinks with autovacuum.** Q6 PostgreSQL was 38,158,336 B net right after the row and 31,358,976 B after 79 s idle (−6,799,360 B); the DIAGNOSTIC attribution of the repeat still showed `init_host_file` 1,474,560 B and `init_entry` 950,272 B with 0 dead tuples after autovacuum, the empty Init B-trees #87 targets.
- **Rename-over and new-path edits store 33% more payload than in-place edits** of the same content (Q3/Q4 808,429 B vs Q2 606,688 B): files below 128 KiB get no delta base on rename-over (#88). Q2's curve jumps at Commit 9 (7 KB → 68 KB) where the 512 KiB chain budget re-stores whole files at depth 8 (#89).
- **Per small file, PostgreSQL rows cost about 3× the closed SQLite file.** Q1 (2,000 files, one Commit): Store bytes not covered by packs are 1,978,911 B on PostgreSQL (989 B per file) and 664,102 B in the closed SQLite file (late net 4,796,416 − Σ new_stored 4,132,314; 332 B per file). This is the row and index overhead the gap stages (#91, #90) target.
- **Same-build repeat (campaign q85-base3, DIAGNOSTIC attribution on).** Every Store byte stayed within ±1 page per table (largest: Q6 PostgreSQL 139,264 B, Q6 SQLite 49,056 B); payload, canonical and raw were identical; `new_metadata` drifted up to 28 B (Q1 SQLite, one Commit of 2,000 files), beyond the owner's 16 B per Commit, so those repeat differences are pinned into the baseline (`repeat_abs_delta`) and widen the compare bands.

## Limits

- Counts are smaller than #85's initial table so PostgreSQL fits about 120 s on a Docker host shared with other owners' Linux builds (load average 13–21 during these runs): text 25 files × 12 edits, Q5 32 MiB, Q6 one Init, 20 edit Commits, 3 identical Branches. A first probe at the initial sizes took 314 s on PostgreSQL. Matrix walls are INELIGIBLE and moved by ±5 s between campaigns.
- Q6 verifies each head by its namespace digest plus the SHA-256 of every path the edit model touched, not a full content hash of the 65 MB tree (17 s per head on PostgreSQL).
- Verification mounts precede the final probe (same Sandbox, fresh mount), so final bytes include whatever a verification mount writes; baseline and candidates do the same.
- Commit statistics beyond bytes (worker CPU, value lookups, decode and delta-depth counters, PostgreSQL round trips) are UNAVAILABLE through the public CLI; per-Commit wall and local CLI CPU are INELIGIBLE.
- The DIAGNOSTIC per-table attribution is not part of the baseline or any gate until the owner decides #85 task 1.

## Cleanup

- Superseded attempt kept as local evidence: campaign `q85-base` (same build) failed verification on Q6 `b02`/`b03` in both backends because the harness then checked those identical heads by root identity, and their roots differ (per-Branch inode metadata, as their metadata-only `new_stored` shows). The harness now verifies every head by content (commit `275e024`); bytes of that attempt were within noise of the pinned run.
- Every row Store was released after its late probe; `finish` dropped each campaign's databases; row and campaign cleanup COMPLETE. The Docker worker, PostgreSQL server `fsopt-85-pg` and private home of q85 are released after hand-off; the image `fs-storage-quick:v1` and the extracted base tree are kept for the #86–#92 subagents.
