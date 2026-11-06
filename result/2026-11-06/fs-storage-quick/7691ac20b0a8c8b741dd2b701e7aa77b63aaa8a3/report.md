# fs-storage-quick — 7691ac20b0

**12 of 12 fs-storage-quick rows PASS with verified final state on final integration 7691ac20b0 (= 8b701f42f0 + #92 + #91 + #90, PRs pending owner merge); against the Phase 0 baseline b4fa173e40 every row is smaller or within noise on SQLite file+WAL, SQLite late and PostgreSQL schema bytes (Q1 SQLite 8,798,208 → 4,538,368 B, Q6 PostgreSQL 38,158,336 → 25,640,960 B), and against the Phase 2 baseline 02133596ae there are no regressions; cleanup COMPLETE.**

Store bytes for six quick storage workloads on LayerFS 2.0 (Docker machine, SQLite and PostgreSQL Stores), measured at a quiesced boundary through the public CLI. This subset is the before/after gate of the #84 storage optimizations (`run.py compare` against this baseline); the full fs-storage suites remain the release check. Bytes are exact integers. MB = 10⁶ B; MiB = 2²⁰ B = 1,048,576 B. Wall times are INELIGIBLE diagnostics, never speed claims.

## Raw vs stored

**Raw** is Σ logical: the bytes of every committed snapshot, as if each were stored in full. **Stored** is the net Store bytes (SQLite: file + WAL; PostgreSQL: schema). **Raw ÷ stored** is the overall reduction, = exact dedup × delta + zstd ÷ Store overhead: **exact dedup** = raw ÷ Σ new_canonical (identical files, chunks and trees stored once); **delta + zstd** = Σ new_canonical ÷ Σ new_stored (delta encoding and compression of the new objects); **Store overhead** = stored ÷ Σ new_stored (database pages, indexes and free space around the packs; 1.35 means the Store is 35% larger than its packs). Q6 imports its base with `project init`, which no Commit covers, so only the overall reduction is shown for it; its raw counts every Commit state plus the Init state.

| Case | Database | Raw (MB) | Stored (MB) | Raw ÷ stored (×) | Exact dedup (×) | Delta + zstd (×) | Store overhead (×) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Q1 | SQLite | 4.1 | 4.5 | 0.90 | 0.94 | 1.05 | 1.10 |
| Q1 | PostgreSQL | 4.1 | 5.1 | 0.80 | 0.94 | 1.05 | 1.24 |
| Q2 | SQLite | 12.1 | 0.5 | 24.45 | 1.00 | 27.51 | 1.12 |
| Q2 | PostgreSQL | 12.1 | 0.7 | 17.61 | 1.00 | 27.51 | 1.56 |
| Q3 | SQLite | 12.1 | 0.5 | 24.05 | 1.00 | 27.43 | 1.14 |
| Q3 | PostgreSQL | 12.1 | 0.7 | 17.20 | 1.00 | 27.43 | 1.59 |
| Q4 | SQLite | 12.1 | 0.6 | 21.91 | 1.00 | 26.66 | 1.21 |
| Q4 | PostgreSQL | 12.1 | 0.8 | 15.57 | 1.00 | 26.65 | 1.71 |
| Q5 | SQLite | 203.4 | 35.0 | 5.81 | 5.82 | 1.01 | 1.01 |
| Q5 | PostgreSQL | 203.4 | 36.5 | 5.57 | 5.82 | 1.01 | 1.05 |
| Q6 | SQLite | 1,560.5 | 23.7 | 65.87 | — | — | — |
| Q6 | PostgreSQL | 1,560.5 | 25.6 | 60.86 | — | — | — |

## Configuration

| Item | Value |
| --- | --- |
| LayerFS source | `7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3` |
| CLI / daemon (macOS, release) | `7f573b61995229fbbd7aeef74a6d756a8637cdd3a2effae0f5321c1863696d40` / `8b4c806d62abfe37a606cfe296e3cb001bc9c66c6615ed1808131cc0e2014409` |
| Linux bundle seal | `b7eddfc9c99da4443f933e483e97a8b2bc9d983c03a45fd20be80c5df7f685e4` |
| Sandbox image | `sha256:fedbb4077dc7cba7771ff10fd0ee2db8ec063a7cea657559819cdcbb4bfb5db5 (fs-storage-quick:v1)` (FROM runtime `sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e`) |
| Workload | `fs-storage-quick-v1`; gen.py `8ddd0ab6c6d6fc0984890b174c9f7dab085eca10167c1660a96757248e590a8d`; model.py `f44c6b23d3035c1af97da133103b2ddf57cf37d977c09e77f11377a46aa307de` |
| Pins | `src/pins.json` SHA-256 `0d40f379bb114eab63ea4b907fe623d5dab4940ba32c12cebf17b7c8e765b66e` |
| Harness | layerfs-benchmark `None` (suite dirty: None), sources `4d3c787dc77fe5659e20d466c28cb1b7434746bf6ae44afcbb0e13e2e5471d9f` |
| Machine | Docker (`docker`), private `LAYERFS_HOME`, `LAYERFS_CONSTRUCTION_WORKERS=1`; rows serial, all SQLite then all PostgreSQL |
| Store bytes | SQLite: `store status` `file.bytes` (file) + `file.wal_bytes` (WAL); WAL frames = (WAL − 32) ÷ 4,120. PostgreSQL: `server.schemas.layerfs` |
| Floor | the row's own Store after create/connect + `project init` of an empty folder (+ `store push` for SQLite) |
| Late probe | one wait of 75.0 s after the last row (slept 74.973 s), then `store status` of 12 retained Stores, then release |

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
| Q1 | SQLite | PASS | PASS | COMPLETE | 1 | 2.7 |  |
| Q1 | PostgreSQL | PASS | PASS | COMPLETE | 1 | 6.3 |  |
| Q2 | SQLite | PASS | PASS | COMPLETE | 13 | 3.6 |  |
| Q2 | PostgreSQL | PASS | PASS | COMPLETE | 13 | 6.9 |  |
| Q3 | SQLite | PASS | PASS | COMPLETE | 13 | 4.1 |  |
| Q3 | PostgreSQL | PASS | PASS | COMPLETE | 13 | 7.1 |  |
| Q4 | SQLite | PASS | PASS | COMPLETE | 13 | 4.1 |  |
| Q4 | PostgreSQL | PASS | PASS | COMPLETE | 13 | 7.2 |  |
| Q5 | SQLite | PASS | PASS | COMPLETE | 6 | 3.5 |  |
| Q5 | PostgreSQL | PASS | PASS | COMPLETE | 6 | 6.4 |  |
| Q6 | SQLite | PASS | PASS | COMPLETE | 23 | 17.0 |  |
| Q6 | PostgreSQL | PASS | PASS | COMPLETE | 23 | 29.9 |  |

| Database | Rows | Matrix wall, first row start → last row end (s, INELIGIBLE) | Σ row wall (s, INELIGIBLE) |
| --- | --- | ---: | ---: |
| SQLite | 6 | 35.1 | 35.0 |
| PostgreSQL | 6 | 64.0 | 63.8 |

## Store bytes

SQLite file and WAL are separate: a quiesced Store keeps up to 4 MiB of WAL (`journal_size_limit`). The late probe re-reads every Store after one wait (SQLite after the worker's 60 s idle close; PostgreSQL after autovacuum had a chance).

| Case | Database | Floor (B) | Final (B) | Net (B) | Net (MB) | Net file (B) | Final WAL (B) | Final WAL frames | Late net (B) | Late net file (B) | Late WAL (B) | Late idle (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| Q1 | SQLite | 217,088 | 4,755,456 | 4,538,368 | 4.538 | 4,538,368 | 0 | 0 | 4,538,368 | 4,538,368 | 0 | 171.5 |
| Q1 | PostgreSQL | 598,016 | 5,734,400 | 5,136,384 | 5.136 | — | — | — | 5,160,960 | — | — | 133.9 |
| Q2 | SQLite | 217,088 | 712,704 | 495,616 | 0.496 | 495,616 | 0 | 0 | 495,616 | 495,616 | 0 | 168.1 |
| Q2 | PostgreSQL | 598,016 | 1,286,144 | 688,128 | 0.688 | — | — | — | 688,128 | — | — | 127.4 |
| Q3 | SQLite | 217,088 | 720,896 | 503,808 | 0.504 | 503,808 | 0 | 0 | 503,808 | 503,808 | 0 | 164.2 |
| Q3 | PostgreSQL | 598,016 | 1,302,528 | 704,512 | 0.705 | — | — | — | 704,512 | — | — | 120.6 |
| Q4 | SQLite | 217,088 | 770,048 | 552,960 | 0.553 | 552,960 | 0 | 0 | 552,960 | 552,960 | 0 | 160.2 |
| Q4 | PostgreSQL | 598,016 | 1,376,256 | 778,240 | 0.778 | — | — | — | 778,240 | — | — | 114.2 |
| Q5 | SQLite | 217,088 | 35,254,272 | 35,037,184 | 35.037 | 35,037,184 | 0 | 0 | 35,037,184 | 35,037,184 | 0 | 156.8 |
| Q5 | PostgreSQL | 598,016 | 37,109,760 | 36,511,744 | 36.512 | — | — | — | 36,528,128 | — | — | 108.3 |
| Q6 | SQLite | 217,088 | 23,908,352 | 23,691,264 | 23.691 | 23,691,264 | 0 | 0 | 23,691,264 | 23,691,264 | 0 | 140.0 |
| Q6 | PostgreSQL | 598,016 | 26,238,976 | 25,640,960 | 25.641 | — | — | — | 25,640,960 | — | — | 78.8 |

## Q6 Init floors

| Case | Database | Probe | Store (B) | Δ previous probe (B) | WAL (B) |
| --- | --- | --- | ---: | ---: | ---: |
| Q6 | SQLite | init_p1 | 23,789,568 | +23,572,480 | 0 |
| Q6 | SQLite | final (after Commits) | 23,908,352 | +118,784 | 0 |
| Q6 | PostgreSQL | init_p1 | 26,017,792 | +25,419,776 | — |
| Q6 | PostgreSQL | final (after Commits) | 26,238,976 | +221,184 | — |

## Per-Commit attribution

In LayerFS 2.0 `new_stored` counts all new pack bytes and `new_metadata` is its metadata-domain subset, so payload = stored − metadata; **net − Σ new_stored** is what no Commit's packs account for (database pages, indexes, free space, the SQLite WAL, and for Q6 the base Init).

| Case | Database | Commits | Raw = Σ logical (+ Init) (B) | Σ new_canonical (B) | Σ new_stored (B) | Σ payload (B) | Σ new_metadata (B) | Net (B) | Net − Σ new_stored (B) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Q1 | SQLite | 1 | 4,103,985 | 4,356,403 | 4,132,331 | 4,115,113 | 17,218 | 4,538,368 | +406,037 |
| Q1 | PostgreSQL | 1 | 4,103,985 | 4,356,403 | 4,132,328 | 4,115,113 | 17,215 | 5,136,384 | +1,004,056 |
| Q2 | SQLite | 13 | 12,116,994 | 12,157,920 | 442,016 | 436,551 | 5,465 | 495,616 | +53,600 |
| Q2 | PostgreSQL | 13 | 12,116,994 | 12,157,920 | 442,009 | 436,551 | 5,458 | 688,128 | +246,119 |
| Q3 | SQLite | 13 | 12,116,994 | 12,164,904 | 443,520 | 436,551 | 6,969 | 503,808 | +60,288 |
| Q3 | PostgreSQL | 13 | 12,116,994 | 12,164,904 | 443,505 | 436,551 | 6,954 | 704,512 | +261,007 |
| Q4 | SQLite | 13 | 12,116,994 | 12,166,204 | 456,424 | 449,377 | 7,047 | 552,960 | +96,536 |
| Q4 | PostgreSQL | 13 | 12,116,994 | 12,166,204 | 456,441 | 449,377 | 7,064 | 778,240 | +321,799 |
| Q5 | SQLite | 6 | 203,423,752 | 34,942,963 | 34,734,401 | 34,653,459 | 80,942 | 35,037,184 | +302,783 |
| Q5 | PostgreSQL | 6 | 203,423,752 | 34,942,963 | 34,734,402 | 34,653,459 | 80,943 | 36,511,744 | +1,777,342 |
| Q6 | SQLite | 23 | 1,560,458,138 | 1,292,935 | 56,058 | 20,118 | 35,940 | 23,691,264 | +23,635,206 |
| Q6 | PostgreSQL | 23 | 1,560,458,138 | 1,292,935 | 56,040 | 20,118 | 35,922 | 25,640,960 | +25,584,920 |

## Per-Commit curves

**Q1 tiny files**

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 4,103,985 | 4,132,331 | 17,218 | 4,132,328 | 17,215 |

**Q2 in-place edits**

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 930,725 | 322,083 | 519 | 322,081 | 517 |
| 2 | 930,462 | 7,078 | 412 | 7,079 | 413 |
| 3 | 931,473 | 7,291 | 411 | 7,291 | 411 |
| 4 | 931,535 | 7,375 | 411 | 7,374 | 410 |
| 5 | 932,181 | 7,384 | 410 | 7,380 | 406 |
| 6 | 932,241 | 7,190 | 412 | 7,190 | 412 |
| 7 | 932,570 | 7,385 | 412 | 7,386 | 413 |
| 8 | 932,599 | 7,262 | 410 | 7,263 | 411 |
| 9 | 932,441 | 12,533 | 411 | 12,534 | 412 |
| 10 | 932,476 | 9,020 | 395 | 9,023 | 398 |
| 11 | 932,662 | 14,445 | 418 | 14,442 | 415 |
| 12 | 932,886 | 23,832 | 423 | 23,828 | 419 |
| 13 | 932,743 | 9,138 | 421 | 9,138 | 421 |

**Q3 rename-over edits**

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 930,725 | 322,083 | 519 | 322,083 | 519 |
| 2 | 930,462 | 7,189 | 523 | 7,191 | 525 |
| 3 | 931,473 | 7,410 | 530 | 7,409 | 529 |
| 4 | 931,535 | 7,498 | 534 | 7,493 | 529 |
| 5 | 932,181 | 7,509 | 535 | 7,505 | 531 |
| 6 | 932,241 | 7,317 | 539 | 7,312 | 534 |
| 7 | 932,570 | 7,511 | 538 | 7,511 | 538 |
| 8 | 932,599 | 7,393 | 541 | 7,392 | 540 |
| 9 | 932,441 | 12,660 | 538 | 12,658 | 536 |
| 10 | 932,476 | 9,154 | 529 | 9,157 | 532 |
| 11 | 932,662 | 14,580 | 553 | 14,580 | 553 |
| 12 | 932,886 | 23,956 | 547 | 23,956 | 547 |
| 13 | 932,743 | 9,260 | 543 | 9,258 | 541 |

**Q4 new-path edits**

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 930,725 | 322,089 | 525 | 322,087 | 523 |
| 2 | 930,462 | 19,981 | 515 | 19,981 | 515 |
| 3 | 931,473 | 7,403 | 523 | 7,410 | 530 |
| 4 | 931,535 | 7,494 | 530 | 7,495 | 531 |
| 5 | 932,181 | 7,513 | 539 | 7,517 | 543 |
| 6 | 932,241 | 7,326 | 548 | 7,326 | 548 |
| 7 | 932,570 | 7,524 | 551 | 7,520 | 547 |
| 8 | 932,599 | 7,401 | 549 | 7,402 | 550 |
| 9 | 932,441 | 12,667 | 545 | 12,670 | 548 |
| 10 | 932,476 | 9,158 | 533 | 9,157 | 532 |
| 11 | 932,662 | 14,591 | 564 | 14,592 | 565 |
| 12 | 932,886 | 11,103 | 563 | 11,108 | 568 |
| 13 | 932,743 | 22,174 | 562 | 22,176 | 564 |

**Q5 large file**

| Commit | Logical (B) | SQLite new_stored (B) | SQLite new_metadata (B) | PostgreSQL new_stored (B) | PostgreSQL new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 33,554,432 | 33,651,782 | 61,106 | 33,651,782 | 61,106 |
| 2 | 33,554,433 | 884 | 830 | 884 | 830 |
| 3 | 33,554,434 | 6,712 | 6,529 | 6,713 | 6,530 |
| 4 | 33,554,434 | 19,356 | 8,315 | 19,354 | 8,313 |
| 5 | 34,603,010 | 1,054,485 | 3,088 | 1,054,486 | 3,089 |
| 6 | 34,603,009 | 1,182 | 1,074 | 1,183 | 1,075 |

**Q6** (per-Commit values in the exported JSON)

| Database | Branch | Commits | Σ new_stored (B) | Min (B) | Median (B) | Max (B) | Σ new_metadata (B) | Median new_metadata (B) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | p1@lane | 20 | 52,726 | 1,553 | 2,273 | 6,144 | 32,950 | 1,193 |
| SQLite | b01.. (identical) | 3 | 3,332 | 960 | 963 | 1,409 | 2,990 | 963 |
| PostgreSQL | p1@lane | 20 | 52,710 | 1,549 | 2,271 | 6,141 | 32,934 | 1,193 |
| PostgreSQL | b01.. (identical) | 3 | 3,330 | 961 | 961 | 1,408 | 2,988 | 961 |

## Diagnostics

What the public CLI exposes per Commit is `logical`, `new_canonical`, `new_stored` and `new_metadata` (bytes). Wall time of each Commit call and the CPU of the local CLI process come from the harness ledger and are INELIGIBLE diagnostics. **UNAVAILABLE** through the public CLI: worker/daemon Commit CPU, `value_lookups`/`value_rows`, pooled decode/read-amplification counters (`chain_edges`, `physical_group_decodes`, `branch_delta_applies`, …), delta depth and PostgreSQL round trips; the product collects some of them only on the SDK trace route, which benchmarks may not use.

| Case | Database | Σ Commit wall (ms) | Median Commit wall (ms) | Max Commit wall (ms) | Median CLI-process CPU per Commit (ms) | Init wall (ms) | Verify Exec wall (ms) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Q1 | SQLite | 242.1 | 242.1 | 242.1 | 8.8 | — | 618.3 |
| Q1 | PostgreSQL | 381.9 | 381.9 | 381.9 | 9.1 | — | 2158.5 |
| Q2 | SQLite | 482.8 | 37.7 | 41.2 | 8.4 | — | 107.6 |
| Q2 | PostgreSQL | 1348.2 | 89.3 | 285.7 | 8.7 | — | 174.6 |
| Q3 | SQLite | 459.5 | 35.6 | 39.6 | 8.4 | — | 78.1 |
| Q3 | PostgreSQL | 1336.3 | 94.0 | 235.2 | 8.6 | — | 148.6 |
| Q4 | SQLite | 477.5 | 36.8 | 44.7 | 8.2 | — | 85.7 |
| Q4 | PostgreSQL | 1244.8 | 88.4 | 175.5 | 8.7 | — | 135.2 |
| Q5 | SQLite | 364.6 | 28.2 | 219.9 | 8.5 | — | 202.1 |
| Q5 | PostgreSQL | 1017.0 | 60.25 | 685.0 | 8.2 | — | 883.9 |
| Q6 | SQLite | 495.8 | 21.0 | 30.2 | 7.9 | 5672.5 | 1426.5, 793.7, 879.0, 861.1 |
| Q6 | PostgreSQL | 2155.5 | 83.2 | 337.4 | 8.5 | 11603.5 | 3681.7, 781.4, 695.7, 808.7 |

## Build under test

Final integration `7691ac20b0` (= `layerfs_v2_0_0` @ `8b701f42f0` + #92 + #91 + #90, PRs pending owner merge): branch `opt/84-final-int` @ `7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3`. `8b701f42f0` already holds the merged Phase 1 fixes #86–#89 and their follow-ups (#592 ring admission, #593 one-shot WAL close). The three Phase 2 PRs (#92 directory/extent page deltas, pack framing v26; #91 + #90 gap stages 1–2, PostgreSQL/SQLite schema v2) are not merged yet, so this is the final identity candidate, not a merged head.

## Before/after against the Phase 0 baseline (b4fa173e40)

Pinned baseline `fs-storage-quick/baseline/b4fa173e401fc87af6610c151225096288e4ba57.json` (the #84 starting point, [report](../b4fa173e401fc87af6610c151225096288e4ba57/report.md)). Net = final − floor (SQLite file + WAL; PostgreSQL schema); late = the same Store after the 75 s late probe (SQLite closed and checkpointed). Δ = final − Phase 0; Δ% of the Phase 0 value. Bytes are exact.

| Case | Database | Raw (B) | Net Phase 0 (B) | Net final (B) | Δ (B) | Δ % | Late net Phase 0 (B) | Late net final (B) | Δ (B) | Δ % | Σ new_stored Phase 0 (B) | Σ new_stored final (B) | Δ (B) | Δ % |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Q1 | SQLite | 4,103,985 | 8,798,208 | 4,538,368 | -4,259,840 | -48.42% | 4,796,416 | 4,538,368 | -258,048 | -5.38% | 4,132,314 | 4,132,331 | +17 | +0.00% |
| Q1 | PostgreSQL | 4,103,985 | 6,111,232 | 5,136,384 | -974,848 | -15.95% | 6,160,384 | 5,160,960 | -999,424 | -16.22% | 4,132,321 | 4,132,328 | +7 | +0.00% |
| Q2 | SQLite | 12,116,994 | 1,726,312 | 495,616 | -1,230,696 | -71.29% | 675,840 | 495,616 | -180,224 | -26.67% | 612,161 | 442,016 | -170,145 | -27.79% |
| Q2 | PostgreSQL | 12,116,994 | 942,080 | 688,128 | -253,952 | -26.96% | 942,080 | 688,128 | -253,952 | -26.96% | 612,151 | 442,009 | -170,142 | -27.79% |
| Q3 | SQLite | 12,116,994 | 2,253,672 | 503,808 | -1,749,864 | -77.65% | 917,504 | 503,808 | -413,696 | -45.09% | 815,382 | 443,520 | -371,862 | -45.61% |
| Q3 | PostgreSQL | 12,116,994 | 1,343,488 | 704,512 | -638,976 | -47.56% | 1,343,488 | 704,512 | -638,976 | -47.56% | 815,394 | 443,505 | -371,889 | -45.61% |
| Q4 | SQLite | 12,116,994 | 2,261,912 | 552,960 | -1,708,952 | -75.55% | 917,504 | 552,960 | -364,544 | -39.73% | 815,499 | 456,424 | -359,075 | -44.03% |
| Q4 | PostgreSQL | 12,116,994 | 1,343,488 | 778,240 | -565,248 | -42.07% | 1,343,488 | 778,240 | -565,248 | -42.07% | 815,488 | 456,441 | -359,047 | -44.03% |
| Q5 | SQLite | 203,423,752 | 37,605,376 | 35,037,184 | -2,568,192 | -6.83% | 35,098,624 | 35,037,184 | -61,440 | -0.18% | 34,788,498 | 34,734,401 | -54,097 | -0.16% |
| Q5 | PostgreSQL | 203,423,752 | 36,691,968 | 36,511,744 | -180,224 | -0.49% | 36,708,352 | 36,528,128 | -180,224 | -0.49% | 34,788,498 | 34,734,402 | -54,096 | -0.16% |
| Q6 | SQLite | 1,560,458,138 | 27,651,760 | 23,691,264 | -3,960,496 | -14.32% | 24,367,104 | 23,691,264 | -675,840 | -2.77% | 72,135 | 56,058 | -16,077 | -22.29% |
| Q6 | PostgreSQL | 1,560,458,138 | 38,158,336 | 25,640,960 | -12,517,376 | -32.80% | 31,358,976 | 25,640,960 | -5,718,016 | -18.23% | 72,114 | 56,040 | -16,074 | -22.29% |

| Case | PostgreSQL ÷ SQLite net, Phase 0 | final | PostgreSQL ÷ SQLite late net, Phase 0 | final |
| --- | ---: | ---: | ---: | ---: |
| Q1 | 0.695× | 1.132× | 1.284× | 1.137× |
| Q2 | 0.546× | 1.388× | 1.394× | 1.388× |
| Q3 | 0.596× | 1.398× | 1.464× | 1.398× |
| Q4 | 0.594× | 1.407× | 1.464× | 1.407× |
| Q5 | 0.976× | 1.042× | 1.046× | 1.043× |
| Q6 | 1.380× | 1.082× | 1.287× | 1.082× |

`run.py compare` against this baseline: **every SQLite file+WAL and late metric and every PostgreSQL schema metric is `lower` or `same`; no payload, canonical, raw or Commit-count difference.** It also lists four `HIGHER` verdicts on SQLite *file-only* net (Q2 +495,616 B, Q3 +503,808 B, Q4 +552,960 B, Q5 +1,626,112 B): after #86 the WAL is checkpointed into the main file at quiesce, so file-only bytes are not comparable with this pre-#86 baseline (the suite's AGENTS.md says to judge SQLite on file+WAL and late bytes there). On those, the same rows are −71.3 % / −77.7 % / −75.6 % / −6.8 % (file+WAL) and −26.7 % / −45.1 % / −39.7 % / −0.2 % (late).

## Before/after against the Phase 2 baseline (02133596ae)

Pinned baseline `fs-storage-quick/baseline/02133596ae95caecd5763b810d0ad3c43087caaa.json` (after #86–#89). `run.py compare`: **no regressions, nothing not comparable, no missing rows.**

| Case | Database | Raw (B) | Net Phase 2 base (B) | Net final (B) | Δ (B) | Δ % | Late net Phase 2 base (B) | Late net final (B) | Δ (B) | Δ % | Σ new_stored Phase 2 base (B) | Σ new_stored final (B) | Δ (B) | Δ % |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Q1 | SQLite | 4,103,985 | 4,796,416 | 4,538,368 | -258,048 | -5.38% | 4,796,416 | 4,538,368 | -258,048 | -5.38% | 4,132,324 | 4,132,331 | +7 | +0.00% |
| Q1 | PostgreSQL | 4,103,985 | 6,119,424 | 5,136,384 | -983,040 | -16.06% | 6,168,576 | 5,160,960 | -1,007,616 | -16.33% | 4,132,330 | 4,132,328 | -2 | -0.00% |
| Q2 | SQLite | 12,116,994 | 503,808 | 495,616 | -8,192 | -1.63% | 503,808 | 495,616 | -8,192 | -1.63% | 442,030 | 442,016 | -14 | -0.00% |
| Q2 | PostgreSQL | 12,116,994 | 761,856 | 688,128 | -73,728 | -9.68% | 761,856 | 688,128 | -73,728 | -9.68% | 442,003 | 442,009 | +6 | +0.00% |
| Q3 | SQLite | 12,116,994 | 548,864 | 503,808 | -45,056 | -8.21% | 548,864 | 503,808 | -45,056 | -8.21% | 443,504 | 443,520 | +16 | +0.00% |
| Q3 | PostgreSQL | 12,116,994 | 942,080 | 704,512 | -237,568 | -25.22% | 942,080 | 704,512 | -237,568 | -25.22% | 443,507 | 443,505 | -2 | -0.00% |
| Q4 | SQLite | 12,116,994 | 917,504 | 552,960 | -364,544 | -39.73% | 917,504 | 552,960 | -364,544 | -39.73% | 815,494 | 456,424 | -359,070 | -44.03% |
| Q4 | PostgreSQL | 12,116,994 | 1,343,488 | 778,240 | -565,248 | -42.07% | 1,343,488 | 778,240 | -565,248 | -42.07% | 815,481 | 456,441 | -359,040 | -44.03% |
| Q5 | SQLite | 203,423,752 | 35,098,624 | 35,037,184 | -61,440 | -0.18% | 35,098,624 | 35,037,184 | -61,440 | -0.18% | 34,788,498 | 34,734,401 | -54,097 | -0.16% |
| Q5 | PostgreSQL | 203,423,752 | 36,724,736 | 36,511,744 | -212,992 | -0.58% | 36,724,736 | 36,528,128 | -196,608 | -0.54% | 34,788,498 | 34,734,402 | -54,096 | -0.16% |
| Q6 | SQLite | 1,560,458,138 | 24,399,872 | 23,691,264 | -708,608 | -2.90% | 24,399,872 | 23,691,264 | -708,608 | -2.90% | 62,030 | 56,058 | -5,972 | -9.63% |
| Q6 | PostgreSQL | 1,560,458,138 | 28,999,680 | 25,640,960 | -3,358,720 | -11.58% | 28,999,680 | 25,640,960 | -3,358,720 | -11.58% | 62,042 | 56,040 | -6,002 | -9.67% |

| Case | PostgreSQL ÷ SQLite net, Phase 2 base | final | PostgreSQL ÷ SQLite late net, Phase 2 base | final |
| --- | ---: | ---: | ---: | ---: |
| Q1 | 1.276× | 1.132× | 1.286× | 1.137× |
| Q2 | 1.512× | 1.388× | 1.512× | 1.388× |
| Q3 | 1.716× | 1.398× | 1.716× | 1.398× |
| Q4 | 1.464× | 1.407× | 1.464× | 1.407× |
| Q5 | 1.046× | 1.042× | 1.046× | 1.043× |
| Q6 | 1.189× | 1.082× | 1.189× | 1.082× |

## Observations

- **Against Phase 0, every row is smaller or within noise on both backends**, on SQLite file + WAL, SQLite late (closed) bytes and PostgreSQL schema bytes; only Q5 (late SQLite −61,440 B, PostgreSQL −180,224 B) stays inside the noise band. Largest: Q3 SQLite −77.65 % net (−45.09 % late), Q4 PostgreSQL −42.07 %, Q6 PostgreSQL −32.80 % net (−18.23 % late). Q5 (one 32 MiB file + 5 edits) is dominated by its payload, which is unchanged.
- **Against the Phase 2 baseline (after #86–#89), the Phase 2 PRs add:** Q1 PostgreSQL −16.06 % (inode-value blocks and narrow locations, #91/#90), Q6 PostgreSQL −11.58 % and SQLite −2.90 %, Q4 −39.7 % SQLite / −42.1 % PostgreSQL (Σ payload −44.4 %; the #88 Q4 ring admission landed in `8b701f42f0` after this baseline was pinned), Q5 Σ new_metadata −40.06 % (#92 extent page deltas); Q2/Q3/Q5 SQLite are within noise.
- **PostgreSQL ÷ SQLite (closed bytes)** moved from 1.28× to 1.14× on Q1 and from 1.29× to 1.08× on Q6; on Q2–Q4 it stays about 1.4× (a few hundred KB of schema pages on sub-MB Stores).

## Limits

- One campaign (no same-session repeat); the noise bands come from each baseline's pinned same-build repeat. Docker Desktop (arm64) was shared with other #84 agents. Wall times are INELIGIBLE.
- #92, #91 and #90 are open PRs; this is the final identity candidate, not the merged head.

## Cleanup

`--late-probe-wait-s 75` kept the 12 Stores, probed them once more and released them (SQLite `store remove`, PostgreSQL `store disconnect`); `run.py finish` dropped the six campaign databases `qfinc1_q1 … _q6` on the dedicated server `fsopt-final-pg`. Cleanup COMPLETE. The shared image `fs-storage-quick:v1` and base tree `base-157` are kept by their owner (q85). The Docker worker was reused by the next final-validation suite and released by it; the dedicated server was released after the last suite.
