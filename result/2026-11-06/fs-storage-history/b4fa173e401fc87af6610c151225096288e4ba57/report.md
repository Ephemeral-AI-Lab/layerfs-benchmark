# fs-storage-history report

**13 of 14 rows PASS with every Branch head verified (171 heads on PostgreSQL; 168 on SQLite, including the 47 H02 heads committed before the failure). H02 SQLite is an infrastructure FAIL: the Docker Desktop disk filled up, and the row was not rerun. Against 6d820c756b, Commit pack bytes moved by at most 243 B per row; Store bytes moved by −2.8 MB … +32,768 B, mostly in PostgreSQL Init. Final cleanup COMPLETE for this suite's resources.**

Storage is not timed; every wall time here is an INELIGIBLE diagnostic. This is the post-#581 reference for layerfs-project#84 on `layerfs_v2_0_0` @ `b4fa173e40`, with the same workload, base tree, model, references and route as the 2026-11-06 run on `6d820c756b`.

## Raw vs stored

**Raw** is Σ logical: the bytes of every committed snapshot, as if each were stored in full. **Stored** is the net Store bytes (SQLite: file + WAL; PostgreSQL: schema). **Raw ÷ stored** is the overall reduction, = exact dedup × delta + zstd ÷ Store overhead: **exact dedup** = raw ÷ Σ new_canonical (identical files, chunks and trees stored once); **delta + zstd** = Σ new_canonical ÷ Σ new_stored (delta encoding and compression of the new objects); **Store overhead** = stored ÷ Σ new_stored (database pages, indexes and free space around the packs; 1.35 means the Store is 35% larger than its packs). Here the base tree is imported with `project init`, which the Commit list does not cover, so only the overall reduction is shown. Raw counts every state, including the base.

| Case | Database | Raw (MB) | Stored (MB) | Raw ÷ stored (×) | Exact dedup (×) | Delta + zstd (×) | Store overhead (×) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| H01 | SQLite | 32,477.4 | 32.3 | 1006.10 | — | — | — |
| H01 | PostgreSQL | 32,477.4 | 36.8 | 883.36 | — | — | — |
| H02 | SQLite | 16,319.9 | 0.0 | — | — | — | — |
| H02 | PostgreSQL | 16,319.9 | 34.2 | 477.51 | — | — | — |
| H03 | SQLite | 3,315.8 | 28.6 | 116.04 | — | — | — |
| H03 | PostgreSQL | 3,315.8 | 31.6 | 104.83 | — | — | — |
| H04 | SQLite | 3,315.3 | 28.6 | 116.00 | — | — | — |
| H04 | PostgreSQL | 3,315.3 | 31.7 | 104.47 | — | — | — |
| H05 | SQLite | 7,801.8 | 29.2 | 267.45 | — | — | — |
| H05 | PostgreSQL | 7,801.8 | 64.8 | 120.37 | — | — | — |
| H06 | SQLite | 7,801.8 | 499.9 | 15.61 | — | — | — |
| H06 | PostgreSQL | 7,801.8 | 747.1 | 10.44 | — | — | — |
| H07 | SQLite | 13,262.8 | 29.9 | 443.08 | — | — | — |
| H07 | PostgreSQL | 13,262.8 | 40.7 | 325.49 | — | — | — |

## Configuration

| Item | Value |
| --- | --- |
| LayerFS source | `b4fa173e401fc87af6610c151225096288e4ba57` (`layerfs_v2_0_0`) |
| CLI / daemon SHA-256 | `69d320f8f9fe86bf78ac18ab7c1a9c0e44c933b2c2493763bd2282e1dff9a348` / `e04a45593a206338696fd7748f205a272f46ebb754e4b49c40aeb0953ce70000` |
| Linux bundle seal | `a8c8daf34097cc61e21ac07b6f5de32b76a7c4a485601ee7c8d6668a2c612d37` (release) |
| Sandbox image | `fs-storage-history:b4fa173e` = `sha256:2081a1489e35d68a528ba0074f59996611dd56d688e6511d3fd1c6bf120774ec`, FROM `sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e` |
| Edit model | `fsh-edit-model-v1`, `src/model.py` SHA-256 `f44c6b23d3035c1af97da133103b2ddf57cf37d977c09e77f11377a46aa307de` |
| Workload | `fs-storage-history-v1` |
| Machine | Docker only (built-in `docker` machine, private home, `LAYERFS_CONSTRUCTION_WORKERS=1`) |
| PostgreSQL | own container `fsopt-ref-pg`, sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652 (postgres:17-bookworm), 1 CPU, 512 MiB, one pre-created empty database per Store, `synchronous_commit=off` |
| Base tree | DSH checkpoint 157: commit `4a096633dda569f403a6d34c61d7b206348db515`, tree `0175125b5dc4dd08965eb576b7c8aee28a73e0c3`, 9,404 files + 11 symlinks, 65,020,822 B; manifest `59069f602c04c92b5d3e479754dc392892bab70bdca6e8c9e18c056635f0cd52`; seed pack `27c7598c04404730200654a1a4ad8f000d63d41da87531cc6e8f206a4e8133bc` |
| Storage policy | cas: BLAKE3 object ids; exact reuse across the whole Store; cdc: GEAR 8/16/32 KiB (min/avg/max) for files of 128 KiB and up; whole_file_cutoff_bytes: 131072; delta_depth_cap: {'whole_file': 16, 'chunk': 8, 'metadata': 8}; compression: per-object zstd level 3; layout: append-only immutable packs stored as Store database rows |

Each Commit applies five operations drawn from `(seed, step)` with a BLAKE2b counter PRNG: 70% small text edit of 1–5 lines (in place, same inode, `O_WRONLY|O_TRUNC`), 10% new 256–4,096 B synthetic text file (new path), 5% delete (unlink), 10% rename (`rename(2)`, 80% same directory), 5% append of one 80–240 B line to a `*.jsonl`/`*.log` file (in place, `O_APPEND`). Every project imports the base with `project init`; Branches are forked with `branch fork` and committed through one Sandbox each (`workspace exec` + `workspace commit` per step). Each Branch head is verified once, in a fresh mount, against the oracle digest (path, type, mode, size, SHA-256; no missing, extra or empty-directory paths).

| Case | Shape | Stores | Projects | Branches | Commits | What it shows |
| --- | --- | --- | --- | --- | --- | --- |
| H01 | long history | 1 | 1 | 1 | 500 | delta chains past the depth cap; growth per Commit |
| H02 | many branches | 1 | 1 | 50 | 250 | extra bytes per branch |
| H03 | identical branches | 1 | 1 | 50 | 50 | ≈ metadata only per branch |
| H04 | nested forks | 1 | 1 | 10 | 50 | branches of branches |
| H05 | projects in one Store | 1 | 20 | 20 | 100 | cross-project sharing |
| H06 | projects in separate Stores | 20 | 20 | 20 | 100 | baseline: Σ H06 ÷ H05 = cross-project gain |
| H07 | combined | 1 | 4 | 20 | 200 | everything at once |

Workload digests: H01 `72080f20f7f5d7eb…`, H02 `41e734b243420e7e…`, H03 `71e9adb3014c62b9…`, H04 `f3da08b003fc4b1b…`, H05 `63f5b2ecfed8f510…`, H06 `120517cdfb8fb7b0…`, H07 `5230deeaa74da012…`

Bytes are exact integers. MB = 10⁶ B; MiB = 2²⁰ B = 1,048,576 B. Wall times are INELIGIBLE diagnostics, never speed claims.

**Floor** = Store bytes after `store create`/`connect` + `project init` of an empty folder (+ `store push` for SQLite). **Init** = after every base `project init` − floor (the Init floor). **Net** = final − floor. **Growth after Init** = final − Init floor. SQLite bytes are `file.bytes + file.wal_bytes`; PostgreSQL bytes are `server.schemas.layerfs`. In LayerFS 2.0 `new_stored` counts every new pack byte of a Commit and `new_metadata` is a subset of it, so payload = new_stored − new_metadata and **unattributed after Init and packs** = growth − Σ new_stored over distinct Commits (database pages, indexes, free space and WAL). The spec's net − (Σ new_stored + Σ new_metadata) counts metadata twice and is not used.

## Lifecycle

| Case | Backend | Execution | Heads verified | Cleanup | Stores | CLI/Docker calls | Row wall (s, INELIGIBLE) |
| --- | --- | --- | --- | --- | --- | --- | ---: |
| H01 | SQLite | PASS | 1/1 | COMPLETE | 1 | 1,034 | 194.2 |
| H01 | PostgreSQL | PASS | 1/1 | COMPLETE | 1 | 1,033 | 191.9 |
| H02 | SQLite | FAIL | 47/47 | INCOMPLETE | 1 | 955 | 591.3 |
| H02 | PostgreSQL | PASS | 50/50 | COMPLETE | 1 | 1,060 | 515.5 |
| H03 | SQLite | PASS | 50/50 | COMPLETE | 1 | 661 | 612.6 |
| H03 | PostgreSQL | PASS | 50/50 | COMPLETE | 1 | 660 | 445.7 |
| H04 | SQLite | PASS | 10/10 | COMPLETE | 1 | 223 | 90.1 |
| H04 | PostgreSQL | PASS | 10/10 | COMPLETE | 1 | 222 | 107.0 |
| H05 | SQLite | PASS | 20/20 | COMPLETE | 1 | 488 | 335.3 |
| H05 | PostgreSQL | PASS | 20/20 | COMPLETE | 1 | 487 | 361.9 |
| H06 | SQLite | PASS | 20/20 | COMPLETE | 20 | 640 | 263.4 |
| H06 | PostgreSQL | PASS | 20/20 | COMPLETE | 20 | 620 | 430.6 |
| H07 | SQLite | PASS | 20/20 | COMPLETE | 1 | 640 | 170.9 |
| H07 | PostgreSQL | PASS | 20/20 | COMPLETE | 1 | 639 | 267.4 |

## Store bytes

| Case | Backend | Outcome | Commits | Floor (B) | Init (B) | Final (B) | Net (B) | Growth after Init (B) | Σ new_stored (B) | of which payload (B) | of which metadata (B) | Unattributed after Init and packs (B) |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H01 | SQLite | PASS | 500 | 212,992 | 24,223,744 | 32,493,568 | 32,280,576 | 8,056,832 | 1,722,017 | 516,311 | 1,205,706 | +6,334,815 |
| H01 | PostgreSQL | PASS | 500 | 753,664 | 37,928,960 | 37,519,360 | 36,765,696 | -1,163,264 | 1,721,881 | 516,311 | 1,205,570 | -2,885,145 |
| H02 | SQLite | FAIL | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | +0 |
| H02 | PostgreSQL | PASS | 250 | 753,664 | 30,982,144 | 34,930,688 | 34,177,024 | 3,194,880 | 762,080 | 248,601 | 513,479 | +2,432,800 |
| H03 | SQLite | PASS | 50 | 212,992 | 24,145,920 | 28,786,688 | 28,573,696 | 4,427,776 | 265,828 | 350 | 265,478 | +4,161,948 |
| H03 | PostgreSQL | PASS | 50 | 753,664 | 37,937,152 | 32,382,976 | 31,629,312 | -6,307,840 | 265,825 | 350 | 265,475 | -6,573,665 |
| H04 | SQLite | PASS | 50 | 212,992 | 24,231,936 | 28,794,384 | 28,581,392 | 4,349,456 | 185,912 | 49,667 | 136,245 | +4,163,544 |
| H04 | PostgreSQL | PASS | 50 | 753,664 | 30,957,568 | 32,489,472 | 31,735,808 | 778,240 | 185,952 | 49,667 | 136,285 | +592,288 |
| H05 | SQLite | PASS | 100 | 212,992 | 24,305,664 | 29,384,704 | 29,171,712 | 4,866,048 | 313,452 | 103,988 | 209,464 | +4,552,596 |
| H05 | PostgreSQL | PASS | 100 | 753,664 | 89,980,928 | 65,568,768 | 64,815,104 | -25,165,824 | 313,478 | 103,988 | 209,490 | -25,479,302 |
| H06 | SQLite | PASS | 100 | 4,259,840 | 483,885,056 | 504,180,576 | 499,920,736 | 16,035,680 | 313,785 | 103,988 | 209,797 | +15,721,895 |
| H06 | PostgreSQL | PASS | 100 | 15,073,280 | 744,570,880 | 762,126,336 | 747,053,056 | 2,482,176 | 313,810 | 103,988 | 209,822 | +2,168,366 |
| H07 | SQLite | PASS | 200 | 212,992 | 24,219,648 | 30,146,560 | 29,933,568 | 5,713,920 | 696,704 | 204,239 | 492,465 | +5,017,216 |
| H07 | PostgreSQL | PASS | 200 | 753,664 | 64,364,544 | 41,500,672 | 40,747,008 | -23,617,536 | 696,793 | 204,239 | 492,554 | -24,314,329 |

SQLite parts (Σ over Stores). The product keeps a WAL of up to 4 MiB after quiesce, so file-only figures are shown beside file + WAL:

| Case | Init, file only (B) | Net, file only (B) | Net WAL (B) | Net, file + WAL (B) | Net allocated (B) | Growth after Init, file only (B) | File-only growth − Σ new_stored (B) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H01 | 24,223,744 | 28,086,272 | 4,194,304 | 32,280,576 | 32,284,672 | 3,862,528 | +2,140,511 |
| H03 | 24,145,920 | 24,379,392 | 4,194,304 | 28,573,696 | 28,581,888 | 233,472 | -32,356 |
| H04 | 24,231,936 | 24,453,120 | 4,128,272 | 28,581,392 | 28,581,888 | 221,184 | +35,272 |
| H05 | 24,305,664 | 24,977,408 | 4,194,304 | 29,171,712 | 29,179,904 | 671,744 | +358,292 |
| H06 | 483,885,056 | 483,885,056 | 16,035,680 | 499,920,736 | 499,986,432 | 0 | -313,785 |
| H07 | 24,219,648 | 25,739,264 | 4,194,304 | 29,933,568 | 29,937,664 | 1,519,616 | +822,912 |

PostgreSQL server WAL (the server is owned and serves one row at a time, but the LSN is server-wide):

| Case | Net schema bytes (B) | Server WAL floor→final (B, server-wide) |
| --- | ---: | ---: |
| H01 | 36,765,696 | 60,008,464 |
| H02 | 34,177,024 | 56,185,720 |
| H03 | 31,629,312 | 53,028,976 |
| H04 | 31,735,808 | 50,539,816 |
| H05 | 64,815,104 | 357,257,112 |
| H06 | 747,053,056 | 1,004,350,856 |
| H07 | 40,747,008 | 109,928,224 |

## H01 long history

Per-Commit `new_stored` and `new_metadata` (B) from the paged `commit list`, in blocks of 50 Commits (Commit 1 is the oldest):

| Commits | SQLite Σ new_stored (B) | SQLite mean new_stored (B) | SQLite max new_stored (B) | SQLite Σ new_metadata (B) | PostgreSQL Σ new_stored (B) | PostgreSQL mean new_stored (B) | PostgreSQL max new_stored (B) | PostgreSQL Σ new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1–50 | 180,630 | 3,613 | 8,185 | 132,006 | 180,566 | 3,611 | 8,221 | 131,942 |
| 51–100 | 179,549 | 3,591 | 9,974 | 125,123 | 179,433 | 3,589 | 9,965 | 125,007 |
| 101–150 | 165,779 | 3,316 | 8,970 | 118,023 | 165,875 | 3,318 | 8,970 | 118,119 |
| 151–200 | 184,963 | 3,699 | 8,969 | 120,835 | 184,875 | 3,698 | 8,965 | 120,747 |
| 201–250 | 173,324 | 3,466 | 12,047 | 121,482 | 173,214 | 3,464 | 12,006 | 121,372 |
| 251–300 | 154,025 | 3,080 | 10,163 | 109,330 | 154,088 | 3,082 | 10,200 | 109,393 |
| 301–350 | 171,239 | 3,425 | 8,032 | 121,301 | 171,321 | 3,426 | 8,048 | 121,383 |
| 351–400 | 174,140 | 3,483 | 7,863 | 126,820 | 174,103 | 3,482 | 7,840 | 126,783 |
| 401–450 | 169,919 | 3,398 | 6,823 | 117,001 | 170,123 | 3,402 | 6,836 | 117,205 |
| 451–500 | 168,449 | 3,369 | 7,895 | 113,785 | 168,283 | 3,366 | 7,892 | 113,619 |

| Backend | Growth after Init (B) | Growth per Commit (B) | new_stored per Commit (B) | payload per Commit (B) | new_metadata per Commit (B) | Head logical (B) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | 8,056,832 | 16,114 | 3,444 | 1,033 | 2,411 | 64,660,289 |
| PostgreSQL | -1,163,264 | -2,327 | 3,444 | 1,033 | 2,411 | 64,660,289 |

## H02 many branches

| Backend | Branches | Own Σ new_stored: min (B) | median (B) | mean (B) | max (B) | of which metadata, mean (B) | Store delta per Branch: min (B) | median (B) | mean (B) | max (B) | Growth after Init ÷ Branches (B) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | — | — | — | — | — | — | — | — | — | — | — |
| PostgreSQL | 50 | 8,927 | 14,617 | 15,242 | 22,844 | 10,270 | 16,384 | 57,344 | 63,898 | 122,880 | 63,898 |

## H03 identical branches

| Backend | Branches | Own Σ new_stored: min (B) | median (B) | mean (B) | max (B) | of which metadata, mean (B) | Store delta per Branch: min (B) | median (B) | mean (B) | max (B) | Growth after Init ÷ Branches (B) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | 50 | 5,127 | 5,279 | 5,317 | 7,281 | 5,310 | 0 | 121,540 | 88,556 | 336,584 | 88,556 |
| PostgreSQL | 50 | 5,127 | 5,279 | 5,316 | 7,283 | 5,310 | -6,946,816 | 8,192 | -126,157 | 73,728 | -126,157 |

## H04 nested forks

| Backend | Branches | Own Σ new_stored: min (B) | median (B) | mean (B) | max (B) | of which metadata, mean (B) | Store delta per Branch: min (B) | median (B) | mean (B) | max (B) | Growth after Init ÷ Branches (B) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | 10 | 10,661 | 18,252 | 18,591 | 24,912 | 13,624 | 0 | 383,160 | 434,946 | 1,094,624 | 434,946 |
| PostgreSQL | 10 | 10,661 | 18,231 | 18,595 | 24,986 | 13,628 | 32,768 | 69,632 | 77,824 | 147,456 | 77,824 |

| Backend | Branch | Forked from | Commits listed | Own Σ new_stored (B) | Own Σ new_metadata (B) | Store delta (B) |
| --- | --- | --- | --- | ---: | ---: | ---: |
| SQLite | l01 | main | 5 | 18,135 | 14,785 | 824,032 |
| SQLite | l02 | l01 | 10 | 18,458 | 12,888 | 807,520 |
| SQLite | l03 | l02 | 15 | 14,559 | 8,863 | 766,320 |
| SQLite | l04 | l03 | 20 | 22,098 | 17,102 | 856,960 |
| SQLite | l05 | l04 | 25 | 18,370 | 14,362 | 1,094,624 |
| SQLite | l06 | l05 | 30 | 24,912 | 19,250 | 0 |
| SQLite | l07 | l06 | 35 | 16,766 | 10,642 | 0 |
| SQLite | l08 | l07 | 40 | 17,621 | 12,870 | 0 |
| SQLite | l09 | l08 | 45 | 10,661 | 7,600 | 0 |
| SQLite | l10 | l09 | 50 | 24,332 | 17,883 | 0 |
| PostgreSQL | l01 | main | 5 | 18,135 | 14,785 | 147,456 |
| PostgreSQL | l02 | l01 | 10 | 18,459 | 12,889 | 32,768 |
| PostgreSQL | l03 | l02 | 15 | 14,569 | 8,873 | 49,152 |
| PostgreSQL | l04 | l03 | 20 | 22,123 | 17,127 | 81,920 |
| PostgreSQL | l05 | l04 | 25 | 18,328 | 14,320 | 57,344 |
| PostgreSQL | l06 | l05 | 30 | 24,986 | 19,324 | 114,688 |
| PostgreSQL | l07 | l06 | 35 | 16,760 | 10,636 | 106,496 |
| PostgreSQL | l08 | l07 | 40 | 17,612 | 12,861 | 57,344 |
| PostgreSQL | l09 | l08 | 45 | 10,661 | 7,600 | 40,960 |
| PostgreSQL | l10 | l09 | 50 | 24,319 | 17,870 | 90,112 |

## H05 and H06: projects in one Store vs separate Stores

| Case | Backend | First project Init (B) | Later Inits: min (B) | mean (B) | max (B) | Own Σ new_stored per project (B) | Net ÷ projects (B) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| H05 | SQLite | 24,301,568 | 0 | 216 | 4,096 | 15,673 | 1,458,586 |
| H05 | PostgreSQL | 31,014,912 | -43,843,584 | 3,103,475 | 9,207,808 | 15,674 | 3,240,755 |
| H06 | SQLite | 24,289,280 | 24,137,728 | 24,189,251 | 24,272,896 | 15,689 | 24,996,037 |
| H06 | PostgreSQL | 30,900,224 | 36,847,616 | 37,561,613 | 38,002,688 | 15,690 | 37,352,653 |

| Backend | H05 net (B) | Σ H06 net (B) | Cross-project gain Σ H06 ÷ H05 (net) | H05 Init (B) | Σ H06 Init (B) | Gain on Init | Σ H06 final ÷ H05 final |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| SQLite | 29,171,712 | 499,920,736 | 17.14 | 24,305,664 | 483,885,056 | 19.91 | 17.16 |
| PostgreSQL | 64,815,104 | 747,053,056 | 11.53 | 89,980,928 | 744,570,880 | 8.27 | 11.62 |

## H07 combined

| Backend | Branches | Own Σ new_stored: min (B) | median (B) | mean (B) | max (B) | of which metadata, mean (B) | Store delta per Branch: min (B) | median (B) | mean (B) | max (B) | Growth after Init ÷ Branches (B) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | 20 | 25,448 | 34,256 | 34,835 | 44,232 | 24,623 | 0 | 0 | 285,696 | 1,610,952 | 285,696 |
| PostgreSQL | 20 | 25,451 | 34,245 | 34,840 | 44,219 | 24,628 | -26,198,016 | 131,072 | -1,180,877 | 204,800 | -1,180,877 |

## Cost per operation kind

Least-squares fit of per-Commit bytes on the five operation counts over every Commit of H01, H02, H04, H05 and H07 (no intercept; the counts always sum to 5, so each coefficient carries a fifth of the fixed per-Commit cost). Differences between kinds are the useful part; this is a diagnostic estimate, not a measurement.

| Backend | Operation | Commits | new_stored per op (B) | payload per op (B) | new_metadata per op (B) |
| --- | --- | --- | ---: | ---: | ---: |
| SQLite | edit | 850 | 464 | 151 | 312 |
| SQLite | new | 850 | 1,422 | 902 | 520 |
| SQLite | delete | 850 | 1,928 | 14 | 1,914 |
| SQLite | rename | 850 | 871 | 2 | 869 |
| SQLite | append | 850 | 601 | 217 | 384 |
| PostgreSQL | edit | 1,100 | 438 | 152 | 285 |
| PostgreSQL | new | 1,100 | 1,369 | 897 | 472 |
| PostgreSQL | delete | 1,100 | 2,197 | 11 | 2,186 |
| PostgreSQL | rename | 1,100 | 858 | 8 | 850 |
| PostgreSQL | append | 1,100 | 561 | 208 | 352 |

## References

Computed once offline from the oracle states ([src/refs.py](../../../../fs-storage-history/src/refs.py)); input digest `19628673fe7f69908d648af33a97f9e26b2987500498d37a5f5c5147324ef5a1`. H06 references are Σ over its 20 separate Stores/repositories. The CDC oracle is approximate (different gear table).

| Case | States | Σ logical (B) | Whole-file unique (B) | Σ tar \| zstd -3 (B) | Git pack + idx (B) | CDC oracle, approx. (B) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| H01 | 501 | 32,477,401,214 | 78,830,497 | 8,347,296,522 | 22,834,511 | 27,552,946 |
| H02 | 251 | 16,319,910,680 | 71,379,465 | 4,171,211,194 | 22,051,139 | 25,291,294 |
| H03 | 51 | 3,315,780,923 | 64,667,219 | 847,422,088 | 21,343,854 | 22,951,661 |
| H04 | 51 | 3,315,339,018 | 65,978,293 | 847,717,951 | 21,473,220 | 23,405,873 |
| H05 | 120 | 7,801,840,603 | 67,268,453 | 1,994,127,816 | 21,629,571 | 23,834,741 |
| H06 | 120 | 7,801,840,603 | 1,295,605,685 | 1,994,127,816 | 427,060,953 | 459,806,841 |
| H07 | 204 | 13,262,830,459 | 69,385,229 | 3,390,155,386 | 21,915,708 | 24,647,736 |

| Case | Backend | Net (B) | Σ logical ÷ net | Net ÷ whole-file unique | Net ÷ Σ tar\|zstd | Net ÷ Git pack | Net ÷ CDC oracle |
| --- | --- | ---: | ---: | --- | --- | --- | --- |
| H01 | SQLite | 32,280,576 | 1006.1 | 0.409 | 0.0039 | 1.414 | 1.172 |
| H01 | PostgreSQL | 36,765,696 | 883.4 | 0.466 | 0.0044 | 1.610 | 1.334 |
| H02 | PostgreSQL | 34,177,024 | 477.5 | 0.479 | 0.0082 | 1.550 | 1.351 |
| H03 | SQLite | 28,573,696 | 116.0 | 0.442 | 0.0337 | 1.339 | 1.245 |
| H03 | PostgreSQL | 31,629,312 | 104.8 | 0.489 | 0.0373 | 1.482 | 1.378 |
| H04 | SQLite | 28,581,392 | 116.0 | 0.433 | 0.0337 | 1.331 | 1.221 |
| H04 | PostgreSQL | 31,735,808 | 104.5 | 0.481 | 0.0374 | 1.478 | 1.356 |
| H05 | SQLite | 29,171,712 | 267.4 | 0.434 | 0.0146 | 1.349 | 1.224 |
| H05 | PostgreSQL | 64,815,104 | 120.4 | 0.964 | 0.0325 | 2.997 | 2.719 |
| H06 | SQLite | 499,920,736 | 15.6 | 0.386 | 0.2507 | 1.171 | 1.087 |
| H06 | PostgreSQL | 747,053,056 | 10.4 | 0.577 | 0.3746 | 1.749 | 1.625 |
| H07 | SQLite | 29,933,568 | 443.1 | 0.431 | 0.0088 | 1.366 | 1.214 |
| H07 | PostgreSQL | 40,747,008 | 325.5 | 0.587 | 0.0120 | 1.859 | 1.653 |

## Before/after vs 6d820c756b

Compared with the 6d820c756b report ([report](../../fs-storage-history/6d820c756b9b12541ac84af7b88467069f31bcbf/report.md)). Δ = base − 6d820c756b; Δ% is of the 6d820c756b value. Bytes are exact.

| Case | Database | Net 6d820c756b (B) | Net base (B) | Δ net (B) | Δ net % | Σ new_stored 6d820c756b (B) | Σ new_stored base (B) | Δ (B) | Δ % | Σ new_metadata 6d820c756b (B) | Σ new_metadata base (B) | Δ (B) | Δ % |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H01 | SQLite | 32,264,192 | 32,280,576 | +16,384 | +0.05% | 1,721,854 | 1,722,017 | +163 | +0.01% | 1,205,543 | 1,205,706 | +163 | +0.01% |
| H01 | PostgreSQL | 36,749,312 | 36,765,696 | +16,384 | +0.04% | 1,721,638 | 1,721,881 | +243 | +0.01% | 1,205,327 | 1,205,570 | +243 | +0.02% |
| H02 | SQLite | 30,208,000 | — (FAIL) | — | — | 762,125 | — | — | — | 513,524 | — | — | — |
| H02 | PostgreSQL | 34,201,600 | 34,177,024 | -24,576 | -0.07% | 762,213 | 762,080 | -133 | -0.02% | 513,612 | 513,479 | -133 | -0.03% |
| H03 | SQLite | 28,589,752 | 28,573,696 | -16,056 | -0.06% | 265,814 | 265,828 | +14 | +0.01% | 265,464 | 265,478 | +14 | +0.01% |
| H03 | PostgreSQL | 31,596,544 | 31,629,312 | +32,768 | +0.10% | 265,834 | 265,825 | -9 | -0.00% | 265,484 | 265,475 | -9 | -0.00% |
| H04 | SQLite | 28,618,752 | 28,581,392 | -37,360 | -0.13% | 185,861 | 185,912 | +51 | +0.03% | 136,194 | 136,245 | +51 | +0.04% |
| H04 | PostgreSQL | 31,834,112 | 31,735,808 | -98,304 | -0.31% | 185,950 | 185,952 | +2 | +0.00% | 136,283 | 136,285 | +2 | +0.00% |
| H05 | SQLite | 29,265,592 | 29,171,712 | -93,880 | -0.32% | 313,458 | 313,452 | -6 | -0.00% | 209,470 | 209,464 | -6 | -0.00% |
| H05 | PostgreSQL | 67,100,672 | 64,815,104 | -2,285,568 | -3.41% | 313,461 | 313,478 | +17 | +0.01% | 209,473 | 209,490 | +17 | +0.01% |
| H06 | SQLite | 500,109,992 | 499,920,736 | -189,256 | -0.04% | 313,825 | 313,785 | -40 | -0.01% | 209,837 | 209,797 | -40 | -0.02% |
| H06 | PostgreSQL | 749,854,720 | 747,053,056 | -2,801,664 | -0.37% | 313,818 | 313,810 | -8 | -0.00% | 209,830 | 209,822 | -8 | -0.00% |
| H07 | SQLite | 29,962,240 | 29,933,568 | -28,672 | -0.10% | 696,721 | 696,704 | -17 | -0.00% | 492,482 | 492,465 | -17 | -0.00% |
| H07 | PostgreSQL | 40,738,816 | 40,747,008 | +8,192 | +0.02% | 696,599 | 696,793 | +194 | +0.03% | 492,360 | 492,554 | +194 | +0.04% |

- **Commit packs are unchanged within metadata drift.** Per row, Σ new_stored moves by −133 … +243 B, and all of it is new_metadata; payload is identical.
- **PostgreSQL Init changed.** H05 PostgreSQL net is −2,285,568 B (−3.41%). Its Init floor (20 base imports) is +4,169,728 B larger, and the later shrink below the Init floor is deeper (growth −25,165,824 B vs −18,710,528 B), which is consistent with Init working-table space being returned after the Inits (#87's area). H06 PostgreSQL net is −2,801,664 B, almost all Init (−2,793,472 B over 20 Stores, ≈ −139.7 KB per Store); its growth after Init moved by only −8,192 B.
- **SQLite rows move by ≤0.32% net** (−93,880 B on H05, mostly growth after Init); counters are unchanged.

## H02 SQLite: infrastructure FAIL (not rerun)

During Branch 48 of 50, a `workspace commit` was refused with `{"code":"Capacity","message":"physical Store I/O: pack persistence: Refused { status: \"Capacity\" }"}` (CLI exit 125). At that moment the shared Docker Desktop disk had 0 B free, filled by another owner's build-target volumes; the next row's pre-check measured 0 B and did not start. This is not a product result. Per the suite rules, the row stays FAIL: its Store `fsh-ref-h02-sq` was kept, its `store status` (26,390,528 B, idle), Store record, branch list, ledger and result were copied to local evidence, and the row was not rerun. The other 13 rows ran after Docker capacity came back (136 GB free at restart, checked before every row). The Store bytes and totals tables show H02 SQLite as zeros because the row never reached a final probe; those zeros are not measurements.

## Observations

- **The 6d820c756b history findings carry over unchanged.** The Commit packs per shape are byte-identical except for ≤243 B of metadata. H03's identical Branches still cost ≈5.3 KB of metadata each, and H01's 500 Commits add a flat ≈3.4 KB of packs each.
- **Separate Stores vs one Store.** H06 ÷ H05 net is 499,920,736 / 29,171,712 = 17.1× on SQLite and 747,053,056 / 64,815,104 = 11.5× on PostgreSQL (11.2× on 6d820c756b, because H05 PostgreSQL shrank).
- **Database overhead dominates the per-Store cost**, the target of the #84 gap stages: the PostgreSQL Init floor of a single base import is ≈37.9 MB against ≈24.2 MB on SQLite (H01).

## Limits

- One sample per row on Docker Desktop (arm64), shared with other #84 subagents' builds; wall times are INELIGIBLE. Every command was bounded at 110 s.
- **Deviation:** PostgreSQL server `fsopt-ref-pg` (postgres:17-bookworm, 1 CPU, 512 MiB, 127.0.0.1:55484) was not dedicated to this suite. It also held the idle, retained fs-storage-dsh failed-row database `fsr_d03_docker`. Every Store still had its own fresh empty database, and schema bytes are per database. The server-wide WAL LSN deltas include that idle database, so they stay diagnostic only.
- The SQLite WAL stays near 4 MiB after quiesce; file-only parts are listed separately.
- The suite image was rebuilt from the same recipe (`fs-storage-history:b4fa173e`, `sha256:2081a148…`, model `f44c6b23…` unchanged); references were reused from 6d820c756b (input digest `19628673…`).
- The PostgreSQL Init explanation is an inference from probe bytes, not a per-table attribution.

## Cleanup

Each PASS row released its Stores (SQLite `store remove`, PostgreSQL `store disconnect`). After the last row, `history_finish` released the Docker worker (`machine stop docker`), the worker container `lfs-263153b4-docker`, the worker volume `lfs-263153b4-docker-data` (which held the H02 SQLite evidence Store, after its evidence was copied locally), this suite's 26 databases, and the image `fs-storage-history:b4fa173e`. `history_finish` left only `fsopt-ref-pg` and its volume, which still held the dsh evidence database. On the lead's decision, that Store was then disconnected through the CLI and the server and its volume were removed (`docker stop`, `docker rm`, `docker volume rm`, each exit 0). The private home still lists `fsh-ref-h02-sq` as a `down` record: `store remove` needs a running machine, and its data volume is gone. No container, volume or database remains. **Final cleanup: COMPLETE.** Ledgers, results and references stay local.
