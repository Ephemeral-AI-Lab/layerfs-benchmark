# fs-storage-history report

**All 14 rows (7 cases × Docker × SQLite, PostgreSQL) PASS with every Branch head verified on final integration 7691ac20b0 (= 8b701f42f0 + #92 + #91 + #90, PRs pending owner merge); against the Phase 0 reference b4fa173e40, net Store bytes fell in every comparable row (SQLite −2.93 % … −17.93 %, PostgreSQL −18.03 % … −53.26 %), Σ new_metadata fell 19–41 % with payload unchanged, and PostgreSQL ÷ SQLite is now 1.07–1.10× in every case (Phase 0: 1.11–2.22×). Final cleanup COMPLETE.**

Storage is not timed; every wall time here is an INELIGIBLE diagnostic.

## Raw vs stored

**Raw** is Σ logical: the bytes of every committed snapshot, as if each were stored in full. **Stored** is the net Store bytes (SQLite: file + WAL; PostgreSQL: schema). **Raw ÷ stored** is the overall reduction, = exact dedup × delta + zstd ÷ Store overhead: **exact dedup** = raw ÷ Σ new_canonical (identical files, chunks and trees stored once); **delta + zstd** = Σ new_canonical ÷ Σ new_stored (delta encoding and compression of the new objects); **Store overhead** = stored ÷ Σ new_stored (database pages, indexes and free space around the packs; 1.35 means the Store is 35% larger than its packs). Here the base tree is imported with `project init`, which the Commit list does not cover, so only the overall reduction is shown. Raw counts every state, including the base.

| Case | Database | Raw (MB) | Stored (MB) | Raw ÷ stored (×) | Exact dedup (×) | Delta + zstd (×) | Store overhead (×) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| H01 | SQLite | 32,477.4 | 26.5 | 1225.89 | — | — | — |
| H01 | PostgreSQL | 32,477.4 | 29.1 | 1117.40 | — | — | — |
| H02 | SQLite | 16,319.9 | 25.0 | 653.82 | — | — | — |
| H02 | PostgreSQL | 16,319.9 | 27.3 | 598.61 | — | — | — |
| H03 | SQLite | 3,315.8 | 23.8 | 139.45 | — | — | — |
| H03 | PostgreSQL | 3,315.8 | 25.9 | 127.89 | — | — | — |
| H04 | SQLite | 3,315.3 | 23.8 | 139.10 | — | — | — |
| H04 | PostgreSQL | 3,315.3 | 25.7 | 128.76 | — | — | — |
| H05 | SQLite | 7,801.8 | 28.3 | 275.53 | — | — | — |
| H05 | PostgreSQL | 7,801.8 | 30.3 | 257.54 | — | — | — |
| H06 | SQLite | 7,801.8 | 471.4 | 16.55 | — | — | — |
| H06 | PostgreSQL | 7,801.8 | 509.9 | 15.30 | — | — | — |
| H07 | SQLite | 13,262.8 | 25.4 | 522.43 | — | — | — |
| H07 | PostgreSQL | 13,262.8 | 27.7 | 479.56 | — | — | — |

## Configuration

| Item | Value |
| --- | --- |
| LayerFS source | `7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3` (`layerfs_v2_0_0`) |
| CLI / daemon SHA-256 | `7f573b61995229fbbd7aeef74a6d756a8637cdd3a2effae0f5321c1863696d40` / `8b4c806d62abfe37a606cfe296e3cb001bc9c66c6615ed1808131cc0e2014409` |
| Linux bundle seal | `b7eddfc9c99da4443f933e483e97a8b2bc9d983c03a45fd20be80c5df7f685e4` (release) |
| Sandbox image | `fs-storage-history:7691ac20` = `sha256:5debc6c42e49600b7c77c8c581067636cbaf2f247838ca0880cd6258c24a2720`, FROM `sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e` |
| Edit model | `fsh-edit-model-v1`, `src/model.py` SHA-256 `f44c6b23d3035c1af97da133103b2ddf57cf37d977c09e77f11377a46aa307de` |
| Workload | `fs-storage-history-v1` |
| Machine | Docker only (built-in `docker` machine, private home, `LAYERFS_CONSTRUCTION_WORKERS=1`) |
| PostgreSQL | own container `fsopt-final-pg`, sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652 (postgres:17-bookworm), 1 CPU / 512 MiB, 127.0.0.1:55494, 1 CPU, 512 MiB, one pre-created empty database per Store, `synchronous_commit=off` |
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
| H01 | SQLite | PASS | 1/1 | COMPLETE | 1 | 1,034 | 107.1 |
| H01 | PostgreSQL | PASS | 1/1 | COMPLETE | 1 | 1,033 | 157.7 |
| H02 | SQLite | PASS | 50/50 | COMPLETE | 1 | 1,061 | 273.1 |
| H02 | PostgreSQL | PASS | 50/50 | COMPLETE | 1 | 1,060 | 431.7 |
| H03 | SQLite | PASS | 50/50 | COMPLETE | 1 | 661 | 224.0 |
| H03 | PostgreSQL | PASS | 50/50 | COMPLETE | 1 | 660 | 384.1 |
| H04 | SQLite | PASS | 10/10 | COMPLETE | 1 | 223 | 50.9 |
| H04 | PostgreSQL | PASS | 10/10 | COMPLETE | 1 | 222 | 91.2 |
| H05 | SQLite | PASS | 20/20 | COMPLETE | 1 | 488 | 164.4 |
| H05 | PostgreSQL | PASS | 20/20 | COMPLETE | 1 | 487 | 365.4 |
| H06 | SQLite | PASS | 20/20 | COMPLETE | 20 | 640 | 194.1 |
| H06 | PostgreSQL | PASS | 20/20 | COMPLETE | 20 | 620 | 587.6 |
| H07 | SQLite | PASS | 20/20 | COMPLETE | 1 | 640 | 126.6 |
| H07 | PostgreSQL | PASS | 20/20 | COMPLETE | 1 | 639 | 269.1 |

## Store bytes

| Case | Backend | Outcome | Commits | Floor (B) | Init (B) | Final (B) | Net (B) | Growth after Init (B) | Σ new_stored (B) | of which payload (B) | of which metadata (B) | Unattributed after Init and packs (B) |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H01 | SQLite | PASS | 500 | 217,088 | 23,523,328 | 26,710,016 | 26,492,928 | 2,969,600 | 1,495,019 | 516,311 | 978,708 | +1,474,581 |
| H01 | PostgreSQL | PASS | 500 | 598,016 | 25,460,736 | 29,663,232 | 29,065,216 | 3,604,480 | 1,494,984 | 516,311 | 978,673 | +2,109,496 |
| H02 | SQLite | PASS | 250 | 217,088 | 23,580,672 | 25,178,112 | 24,961,024 | 1,380,352 | 606,622 | 248,601 | 358,021 | +773,730 |
| H02 | PostgreSQL | PASS | 250 | 598,016 | 25,477,120 | 27,860,992 | 27,262,976 | 1,785,856 | 606,385 | 248,601 | 357,784 | +1,179,471 |
| H03 | SQLite | PASS | 50 | 217,088 | 23,506,944 | 23,994,368 | 23,777,280 | 270,336 | 155,997 | 350 | 155,647 | +114,339 |
| H03 | PostgreSQL | PASS | 50 | 598,016 | 25,477,120 | 26,525,696 | 25,927,680 | 450,560 | 155,994 | 350 | 155,644 | +294,566 |
| H04 | SQLite | PASS | 50 | 217,088 | 23,556,096 | 24,051,712 | 23,834,624 | 278,528 | 141,707 | 49,667 | 92,040 | +136,821 |
| H04 | PostgreSQL | PASS | 50 | 598,016 | 25,378,816 | 26,345,472 | 25,747,456 | 368,640 | 141,651 | 49,667 | 91,984 | +226,989 |
| H05 | SQLite | PASS | 100 | 217,088 | 27,758,592 | 28,532,736 | 28,315,648 | 557,056 | 252,721 | 103,988 | 148,733 | +304,335 |
| H05 | PostgreSQL | PASS | 100 | 598,016 | 29,564,928 | 30,892,032 | 30,294,016 | 729,088 | 252,763 | 103,988 | 148,775 | +476,325 |
| H06 | SQLite | PASS | 100 | 4,341,760 | 470,867,968 | 475,693,056 | 471,351,296 | 483,328 | 252,777 | 103,988 | 148,789 | +230,551 |
| H06 | PostgreSQL | PASS | 100 | 11,960,320 | 508,297,216 | 521,879,552 | 509,919,232 | 1,622,016 | 252,871 | 103,988 | 148,883 | +1,369,145 |
| H07 | SQLite | PASS | 200 | 217,088 | 24,174,592 | 25,604,096 | 25,387,008 | 1,212,416 | 543,266 | 204,239 | 339,027 | +669,150 |
| H07 | PostgreSQL | PASS | 200 | 598,016 | 26,050,560 | 28,254,208 | 27,656,192 | 1,605,632 | 543,238 | 204,239 | 338,999 | +1,062,394 |

SQLite parts (Σ over Stores). The product keeps a WAL of up to 4 MiB after quiesce, so file-only figures are shown beside file + WAL:

| Case | Init, file only (B) | Net, file only (B) | Net WAL (B) | Net, file + WAL (B) | Net allocated (B) | Growth after Init, file only (B) | File-only growth − Σ new_stored (B) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H01 | 23,523,328 | 26,492,928 | 0 | 26,492,928 | 26,497,024 | 2,969,600 | +1,474,581 |
| H02 | 23,580,672 | 24,961,024 | 0 | 24,961,024 | 24,965,120 | 1,380,352 | +773,730 |
| H03 | 23,506,944 | 23,777,280 | 0 | 23,777,280 | 23,781,376 | 270,336 | +114,339 |
| H04 | 23,556,096 | 23,834,624 | 0 | 23,834,624 | 23,838,720 | 278,528 | +136,821 |
| H05 | 27,758,592 | 28,315,648 | 0 | 28,315,648 | 28,319,744 | 557,056 | +304,335 |
| H06 | 470,867,968 | 471,351,296 | 0 | 471,351,296 | 471,363,584 | 483,328 | +230,551 |
| H07 | 24,174,592 | 25,387,008 | 0 | 25,387,008 | 25,387,008 | 1,212,416 | +669,150 |

PostgreSQL server WAL (the server is owned and serves one row at a time, but the LSN is server-wide):

| Case | Net schema bytes (B) | Server WAL floor→final (B, server-wide) |
| --- | ---: | ---: |
| H01 | 29,065,216 | 48,754,912 |
| H02 | 27,262,976 | 46,790,200 |
| H03 | 25,927,680 | 44,091,392 |
| H04 | 25,747,456 | 43,419,848 |
| H05 | 30,294,016 | 334,673,232 |
| H06 | 509,919,232 | 865,372,992 |
| H07 | 27,656,192 | 92,294,216 |

## H01 long history

Per-Commit `new_stored` and `new_metadata` (B) from the paged `commit list`, in blocks of 50 Commits (Commit 1 is the oldest):

| Commits | SQLite Σ new_stored (B) | SQLite mean new_stored (B) | SQLite max new_stored (B) | SQLite Σ new_metadata (B) | PostgreSQL Σ new_stored (B) | PostgreSQL mean new_stored (B) | PostgreSQL max new_stored (B) | PostgreSQL Σ new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1–50 | 139,344 | 2,787 | 6,563 | 90,720 | 139,283 | 2,786 | 6,558 | 90,659 |
| 51–100 | 153,139 | 3,063 | 7,130 | 98,713 | 153,125 | 3,062 | 7,132 | 98,699 |
| 101–150 | 150,446 | 3,009 | 8,342 | 102,690 | 150,352 | 3,007 | 8,325 | 102,596 |
| 151–200 | 160,529 | 3,211 | 8,633 | 96,401 | 160,651 | 3,213 | 8,633 | 96,523 |
| 201–250 | 151,987 | 3,040 | 6,457 | 100,145 | 152,057 | 3,041 | 6,449 | 100,215 |
| 251–300 | 142,970 | 2,859 | 6,308 | 98,275 | 142,996 | 2,860 | 6,303 | 98,301 |
| 301–350 | 144,039 | 2,881 | 7,783 | 94,101 | 143,939 | 2,879 | 7,797 | 94,001 |
| 351–400 | 145,860 | 2,917 | 5,730 | 98,540 | 145,815 | 2,916 | 5,731 | 98,495 |
| 401–450 | 153,087 | 3,062 | 6,583 | 100,169 | 153,228 | 3,065 | 6,595 | 100,310 |
| 451–500 | 153,618 | 3,072 | 7,677 | 98,954 | 153,538 | 3,071 | 7,613 | 98,874 |

| Backend | Growth after Init (B) | Growth per Commit (B) | new_stored per Commit (B) | payload per Commit (B) | new_metadata per Commit (B) | Head logical (B) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | 2,969,600 | 5,939 | 2,990 | 1,033 | 1,957 | 64,660,289 |
| PostgreSQL | 3,604,480 | 7,209 | 2,990 | 1,033 | 1,957 | 64,660,289 |

## H02 many branches

| Backend | Branches | Own Σ new_stored: min (B) | median (B) | mean (B) | max (B) | of which metadata, mean (B) | Store delta per Branch: min (B) | median (B) | mean (B) | max (B) | Growth after Init ÷ Branches (B) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | 50 | 8,651 | 12,046 | 12,132 | 16,108 | 7,160 | 12,288 | 28,672 | 27,607 | 49,152 | 27,607 |
| PostgreSQL | 50 | 8,649 | 12,045 | 12,128 | 16,093 | 7,156 | 8,192 | 32,768 | 35,717 | 98,304 | 35,717 |

## H03 identical branches

| Backend | Branches | Own Σ new_stored: min (B) | median (B) | mean (B) | max (B) | of which metadata, mean (B) | Store delta per Branch: min (B) | median (B) | mean (B) | max (B) | Growth after Init ÷ Branches (B) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | 50 | 3,092 | 3,104 | 3,120 | 3,894 | 3,113 | 4,096 | 4,096 | 5,407 | 16,384 | 5,407 |
| PostgreSQL | 50 | 3,103 | 3,104 | 3,120 | 3,889 | 3,113 | 0 | 8,192 | 9,011 | 57,344 | 9,011 |

## H04 nested forks

| Backend | Branches | Own Σ new_stored: min (B) | median (B) | mean (B) | max (B) | of which metadata, mean (B) | Store delta per Branch: min (B) | median (B) | mean (B) | max (B) | Growth after Init ÷ Branches (B) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | 10 | 10,316 | 14,278 | 14,171 | 18,349 | 9,204 | 20,480 | 26,624 | 27,853 | 36,864 | 27,853 |
| PostgreSQL | 10 | 10,311 | 14,258 | 14,165 | 18,338 | 9,198 | 16,384 | 32,768 | 36,864 | 90,112 | 36,864 |

| Backend | Branch | Forked from | Commits listed | Own Σ new_stored (B) | Own Σ new_metadata (B) | Store delta (B) |
| --- | --- | --- | --- | ---: | ---: | ---: |
| SQLite | l01 | main | 5 | 12,075 | 8,725 | 28,672 |
| SQLite | l02 | l01 | 10 | 14,305 | 8,735 | 20,480 |
| SQLite | l03 | l02 | 15 | 11,111 | 5,415 | 24,576 |
| SQLite | l04 | l03 | 20 | 15,925 | 10,929 | 36,864 |
| SQLite | l05 | l04 | 25 | 14,594 | 10,586 | 28,672 |
| SQLite | l06 | l05 | 30 | 14,138 | 8,476 | 36,864 |
| SQLite | l07 | l06 | 35 | 18,349 | 12,225 | 24,576 |
| SQLite | l08 | l07 | 40 | 10,316 | 5,565 | 20,480 |
| SQLite | l09 | l08 | 45 | 14,252 | 11,191 | 24,576 |
| SQLite | l10 | l09 | 50 | 16,642 | 10,193 | 32,768 |
| PostgreSQL | l01 | main | 5 | 12,065 | 8,715 | 90,112 |
| PostgreSQL | l02 | l01 | 10 | 14,278 | 8,708 | 16,384 |
| PostgreSQL | l03 | l02 | 15 | 11,101 | 5,405 | 16,384 |
| PostgreSQL | l04 | l03 | 20 | 15,927 | 10,931 | 32,768 |
| PostgreSQL | l05 | l04 | 25 | 14,603 | 10,595 | 32,768 |
| PostgreSQL | l06 | l05 | 30 | 14,148 | 8,486 | 73,728 |
| PostgreSQL | l07 | l06 | 35 | 18,338 | 12,214 | 32,768 |
| PostgreSQL | l08 | l07 | 40 | 10,311 | 5,560 | 16,384 |
| PostgreSQL | l09 | l08 | 45 | 14,239 | 11,178 | 24,576 |
| PostgreSQL | l10 | l09 | 50 | 16,641 | 10,192 | 32,768 |

## H05 and H06: projects in one Store vs separate Stores

| Case | Backend | First project Init (B) | Later Inits: min (B) | mean (B) | max (B) | Own Σ new_stored per project (B) | Net ÷ projects (B) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| H05 | SQLite | 23,568,384 | 217,088 | 220,537 | 225,280 | 12,636 | 1,415,782 |
| H05 | PostgreSQL | 25,436,160 | 204,800 | 217,304 | 303,104 | 12,638 | 1,514,701 |
| H06 | SQLite | 23,568,384 | 23,502,848 | 23,542,083 | 23,601,152 | 12,639 | 23,567,565 |
| H06 | PostgreSQL | 25,427,968 | 25,354,240 | 25,414,171 | 25,493,504 | 12,644 | 25,495,962 |

| Backend | H05 net (B) | Σ H06 net (B) | Cross-project gain Σ H06 ÷ H05 (net) | H05 Init (B) | Σ H06 Init (B) | Gain on Init | Σ H06 final ÷ H05 final |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| SQLite | 28,315,648 | 471,351,296 | 16.65 | 27,758,592 | 470,867,968 | 16.96 | 16.67 |
| PostgreSQL | 30,294,016 | 509,919,232 | 16.83 | 29,564,928 | 508,297,216 | 17.19 | 16.89 |

## H07 combined

| Backend | Branches | Own Σ new_stored: min (B) | median (B) | mean (B) | max (B) | of which metadata, mean (B) | Store delta per Branch: min (B) | median (B) | mean (B) | max (B) | Growth after Init ÷ Branches (B) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | 20 | 20,836 | 27,103 | 27,163 | 31,925 | 16,951 | 40,960 | 57,344 | 60,621 | 86,016 | 60,621 |
| PostgreSQL | 20 | 20,842 | 27,103 | 27,162 | 31,918 | 16,950 | 40,960 | 77,824 | 80,282 | 139,264 | 80,282 |

## Cost per operation kind

Least-squares fit of per-Commit bytes on the five operation counts over every Commit of H01, H02, H04, H05 and H07 (no intercept; the counts always sum to 5, so each coefficient carries a fifth of the fixed per-Commit cost). Differences between kinds are the useful part; this is a diagnostic estimate, not a measurement.

| Backend | Operation | Commits | new_stored per op (B) | payload per op (B) | new_metadata per op (B) |
| --- | --- | --- | ---: | ---: | ---: |
| SQLite | edit | 1,100 | 414 | 152 | 262 |
| SQLite | new | 1,100 | 1,360 | 897 | 463 |
| SQLite | delete | 1,100 | 1,111 | 11 | 1,100 |
| SQLite | rename | 1,100 | 464 | 8 | 456 |
| SQLite | append | 1,100 | 526 | 208 | 318 |
| PostgreSQL | edit | 1,100 | 414 | 152 | 262 |
| PostgreSQL | new | 1,100 | 1,360 | 897 | 463 |
| PostgreSQL | delete | 1,100 | 1,111 | 11 | 1,100 |
| PostgreSQL | rename | 1,100 | 464 | 8 | 456 |
| PostgreSQL | append | 1,100 | 526 | 208 | 318 |

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
| H01 | SQLite | 26,492,928 | 1225.9 | 0.336 | 0.0032 | 1.160 | 0.962 |
| H01 | PostgreSQL | 29,065,216 | 1117.4 | 0.369 | 0.0035 | 1.273 | 1.055 |
| H02 | SQLite | 24,961,024 | 653.8 | 0.350 | 0.0060 | 1.132 | 0.987 |
| H02 | PostgreSQL | 27,262,976 | 598.6 | 0.382 | 0.0065 | 1.236 | 1.078 |
| H03 | SQLite | 23,777,280 | 139.5 | 0.368 | 0.0281 | 1.114 | 1.036 |
| H03 | PostgreSQL | 25,927,680 | 127.9 | 0.401 | 0.0306 | 1.215 | 1.130 |
| H04 | SQLite | 23,834,624 | 139.1 | 0.361 | 0.0281 | 1.110 | 1.018 |
| H04 | PostgreSQL | 25,747,456 | 128.8 | 0.390 | 0.0304 | 1.199 | 1.100 |
| H05 | SQLite | 28,315,648 | 275.5 | 0.421 | 0.0142 | 1.309 | 1.188 |
| H05 | PostgreSQL | 30,294,016 | 257.5 | 0.450 | 0.0152 | 1.401 | 1.271 |
| H06 | SQLite | 471,351,296 | 16.6 | 0.364 | 0.2364 | 1.104 | 1.025 |
| H06 | PostgreSQL | 509,919,232 | 15.3 | 0.394 | 0.2557 | 1.194 | 1.109 |
| H07 | SQLite | 25,387,008 | 522.4 | 0.366 | 0.0075 | 1.158 | 1.030 |
| H07 | PostgreSQL | 27,656,192 | 479.6 | 0.399 | 0.0082 | 1.262 | 1.122 |

## Build under test

Final integration `7691ac20b0` (= `layerfs_v2_0_0` @ `8b701f42f0` + #92 + #91 + #90, PRs pending owner merge): branch `opt/84-final-int` @ `7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3`. `8b701f42f0` holds the merged Phase 1 fixes #86–#89 and follow-ups; #92 (directory/extent page deltas, pack framing v26) and #91 + #90 (gap stages 1–2, schema v2) are open PRs awaiting the owner's merge, so this is the final identity candidate. This is the #84 final validation (handoff §5). Same workload, base tree, model, references and route as Phase 0.

## Before/after against the Phase 0 reference (b4fa173e40)

Phase 0 = the 2026-11-06 reference on `b4fa173e40` ([report](../b4fa173e401fc87af6610c151225096288e4ba57/report.md)). Raw (Σ logical, every state including the base) is the same workload in both runs; see Raw vs stored above. Δ = final − Phase 0; Δ% of the Phase 0 value. Bytes are exact. H02 SQLite has no Phase 0 value (infrastructure FAIL there; its zeros were not measurements).

| Case | Database | Net Phase 0 (B) | Net final (B) | Δ net (B) | Δ net % | Σ new_stored Phase 0 (B) | Σ new_stored final (B) | Δ (B) | Δ % | Σ new_metadata Phase 0 (B) | Σ new_metadata final (B) | Δ (B) | Δ % |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H01 | SQLite | 32,280,576 | 26,492,928 | -5,787,648 | -17.93% | 1,722,017 | 1,495,019 | -226,998 | -13.18% | 1,205,706 | 978,708 | -226,998 | -18.83% |
| H01 | PostgreSQL | 36,765,696 | 29,065,216 | -7,700,480 | -20.94% | 1,721,881 | 1,494,984 | -226,897 | -13.18% | 1,205,570 | 978,673 | -226,897 | -18.82% |
| H02 | SQLite | — | 24,961,024 | — | — | — | 606,622 | — | — | — | 358,021 | — | — |
| H02 | PostgreSQL | 34,177,024 | 27,262,976 | -6,914,048 | -20.23% | 762,080 | 606,385 | -155,695 | -20.43% | 513,479 | 357,784 | -155,695 | -30.32% |
| H03 | SQLite | 28,573,696 | 23,777,280 | -4,796,416 | -16.79% | 265,828 | 155,997 | -109,831 | -41.32% | 265,478 | 155,647 | -109,831 | -41.37% |
| H03 | PostgreSQL | 31,629,312 | 25,927,680 | -5,701,632 | -18.03% | 265,825 | 155,994 | -109,831 | -41.32% | 265,475 | 155,644 | -109,831 | -41.37% |
| H04 | SQLite | 28,581,392 | 23,834,624 | -4,746,768 | -16.61% | 185,912 | 141,707 | -44,205 | -23.78% | 136,245 | 92,040 | -44,205 | -32.45% |
| H04 | PostgreSQL | 31,735,808 | 25,747,456 | -5,988,352 | -18.87% | 185,952 | 141,651 | -44,301 | -23.82% | 136,285 | 91,984 | -44,301 | -32.51% |
| H05 | SQLite | 29,171,712 | 28,315,648 | -856,064 | -2.93% | 313,452 | 252,721 | -60,731 | -19.37% | 209,464 | 148,733 | -60,731 | -28.99% |
| H05 | PostgreSQL | 64,815,104 | 30,294,016 | -34,521,088 | -53.26% | 313,478 | 252,763 | -60,715 | -19.37% | 209,490 | 148,775 | -60,715 | -28.98% |
| H06 | SQLite | 499,920,736 | 471,351,296 | -28,569,440 | -5.71% | 313,785 | 252,777 | -61,008 | -19.44% | 209,797 | 148,789 | -61,008 | -29.08% |
| H06 | PostgreSQL | 747,053,056 | 509,919,232 | -237,133,824 | -31.74% | 313,810 | 252,871 | -60,939 | -19.42% | 209,822 | 148,883 | -60,939 | -29.04% |
| H07 | SQLite | 29,933,568 | 25,387,008 | -4,546,560 | -15.19% | 696,704 | 543,266 | -153,438 | -22.02% | 492,465 | 339,027 | -153,438 | -31.16% |
| H07 | PostgreSQL | 40,747,008 | 27,656,192 | -13,090,816 | -32.13% | 696,793 | 543,238 | -153,555 | -22.04% | 492,554 | 338,999 | -153,555 | -31.18% |

| Case | PostgreSQL ÷ SQLite net, Phase 0 | PostgreSQL ÷ SQLite net, final |
| --- | ---: | ---: |
| H01 | 1.139× | 1.097× |
| H02 | — | 1.092× |
| H03 | 1.107× | 1.090× |
| H04 | 1.110× | 1.080× |
| H05 | 2.222× | 1.070× |
| H06 | 1.494× | 1.082× |
| H07 | 1.361× | 1.089× |

## Final validation: observations

- **Every comparable row is smaller; payload is identical.** Σ payload (stored − metadata) is unchanged in every row (e.g. H01 516,311 B in both runs), so the drop comes from metadata and from the Store around the packs. Σ new_metadata fell 18.8 % (H01) to 41.4 % (H03), consistent with #92's directory page deltas.
- **PostgreSQL Init no longer dominates.** The Init floor after one base import is now 25,460,736 B on PostgreSQL vs 23,523,328 B on SQLite (H01); Phase 0 had 37,928,960 B vs 24,223,744 B. H05 PostgreSQL (20 base imports into one Store) fell from 64,815,104 to 30,294,016 B (−53.26 %): its Init floor is 29,564,928 B (Phase 0 89,980,928 B, which later shrank). This is consistent with #87 (PostgreSQL Init cleanup) and #91/#90 (inode-value blocks, narrow locations).
- **Separate Stores vs one Store.** Σ H06 ÷ H05 net is 16.65× on SQLite and 16.83× on PostgreSQL (Phase 0 17.1× / 11.5×; PostgreSQL's ratio rose because H05 PostgreSQL shrank far more than H06). Σ H06 PostgreSQL fell 237,133,824 B (−31.74 %).
- **SQLite H05 −2.93 % is the smallest win.** Phase 0 probed SQLite as file + a WAL capped at 4 MiB, so its later Inits looked free (0–4,096 B each) and the cost appeared later as growth after Init (+4,866,048 B). With #86 every probe is checkpointed: later Inits cost ≈ 220 KB each and growth after Init is 557,056 B. Compare SQLite rows on net only.
- **PostgreSQL ÷ SQLite** is 1.070–1.097× in every case (Phase 0 1.107–2.222×).

## Final validation: limits

- One sample per row on Docker Desktop (arm64), shared with other #84 agents; wall times are INELIGIBLE. Every command was bounded at 110 s.
- The dedicated PostgreSQL server `fsopt-final-pg` (postgres:17-bookworm, 1 CPU, 512 MiB, 127.0.0.1:55494) served the final-validation suites one after another; during this suite it held only this suite's 26 databases (one fresh database per Store).
- Per-mechanism attribution (#86–#92) is an inference from which counters moved; this run measured the integrated build only. #92, #91 and #90 are not merged yet.
- The suite image was rebuilt from the same recipe (`fs-storage-history:7691ac20`, `sha256:5debc6c4…`, model `f44c6b23…` unchanged); references were reused from Phase 0.

## Cleanup

Each row released its Stores (SQLite `store remove`, PostgreSQL `store disconnect`). After the last row, `history_finish` released the Docker worker (`machine stop docker`), container `lfs-34565e00-docker`, volume `lfs-34565e00-docker-data`, this suite's 26 databases and the image `fs-storage-history:7691ac20` (no leftover container or volume). The dedicated server `fsopt-final-pg` and its volume were then removed (`docker stop`, `docker rm`, `docker volume rm`, each exit 0). **Final cleanup: COMPLETE.** Results, ledgers and references stay local.
