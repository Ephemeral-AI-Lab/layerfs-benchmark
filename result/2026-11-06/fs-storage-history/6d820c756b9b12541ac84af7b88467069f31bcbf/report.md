# fs-storage-history report

**All 14 rows (7 cases × Docker × SQLite, PostgreSQL) PASS with every Branch head verified (171 heads per backend); 50 identical Branches cost ≈ 5.3 KB of metadata each, 20 projects in separate Stores need 17.1× (SQLite) / 11.2× (PostgreSQL) the net bytes of one shared Store, and 500 Commits add a flat ≈ 3.4 KB of packs each; final cleanup COMPLETE.**

Storage is not timed; every wall time here is an INELIGIBLE diagnostic. H02 on
PostgreSQL ran twice: the first attempt was interrupted by the owner's Docker
Desktop restart (infrastructure, not a product result) and is kept as a
superseded attempt; the counted row is the rerun on a fresh database and Store.

Harness: `fs-storage-history` at `5ba00b6` (driver, cases, model) with the shared
`storage.Driver` from `fs-storage-shared` (`a95af3d`; the `98d2622` summary
update was merged during the SQLite rows and does not change the Driver or the
`commit list` collector). Report and accounting code were finished afterwards.

## Raw vs stored

**Raw** is Σ logical: the bytes of every committed snapshot, as if each were stored in full. **Stored** is the net Store bytes (SQLite: file + WAL; PostgreSQL: schema). **Raw ÷ stored** is the overall reduction, = exact dedup × delta + zstd ÷ Store overhead: **exact dedup** = raw ÷ Σ new_canonical (identical files, chunks and trees stored once); **delta + zstd** = Σ new_canonical ÷ Σ new_stored (delta encoding and compression of the new objects); **Store overhead** = stored ÷ Σ new_stored (database pages, indexes and free space around the packs; 1.35 means the Store is 35% larger than its packs). Here the base tree is imported with `project init`, which the Commit list does not cover, so only the overall reduction is shown. Raw counts every state, including the base.

| Case | Database | Raw (MB) | Stored (MB) | Raw ÷ stored (×) | Exact dedup (×) | Delta + zstd (×) | Store overhead (×) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| H01 | SQLite | 32,477.4 | 32.3 | 1006.61 | — | — | — |
| H01 | PostgreSQL | 32,477.4 | 36.7 | 883.76 | — | — | — |
| H02 | SQLite | 16,319.9 | 30.2 | 540.25 | — | — | — |
| H02 | PostgreSQL | 16,319.9 | 34.2 | 477.17 | — | — | — |
| H03 | SQLite | 3,315.8 | 28.6 | 115.98 | — | — | — |
| H03 | PostgreSQL | 3,315.8 | 31.6 | 104.94 | — | — | — |
| H04 | SQLite | 3,315.3 | 28.6 | 115.84 | — | — | — |
| H04 | PostgreSQL | 3,315.3 | 31.8 | 104.14 | — | — | — |
| H05 | SQLite | 7,801.8 | 29.3 | 266.59 | — | — | — |
| H05 | PostgreSQL | 7,801.8 | 67.1 | 116.27 | — | — | — |
| H06 | SQLite | 7,801.8 | 500.1 | 15.60 | — | — | — |
| H06 | PostgreSQL | 7,801.8 | 749.9 | 10.40 | — | — | — |
| H07 | SQLite | 13,262.8 | 30.0 | 442.65 | — | — | — |
| H07 | PostgreSQL | 13,262.8 | 40.7 | 325.56 | — | — | — |

## Configuration

| Item | Value |
| --- | --- |
| LayerFS source | `6d820c756b9b12541ac84af7b88467069f31bcbf` (`layerfs_v2_0_0`) |
| CLI / daemon SHA-256 | `da25a81bdc692b9a2989650a35716648ab3a64f360281edaff51f870b322e57f` / `b0b961bf004bef7bb0e53724ad5a4a4155e731128093cddfb0a0d3bdd8ff803f` |
| Linux bundle seal | `05891b572d5bcad989f7f05821a856e2ea9cf540186fb18f813ccacbd4cbb0e3` (release) |
| Sandbox image | `fs-storage-history:6d820c75` = `sha256:0627c7f8ffa5747ace659229afa5e87ef7cc4a8f76c8118853472de6ff55a7d1`, FROM `sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e` |
| Edit model | `fsh-edit-model-v1`, `src/model.py` SHA-256 `f44c6b23d3035c1af97da133103b2ddf57cf37d977c09e77f11377a46aa307de` |
| Workload | `fs-storage-history-v1` |
| Machine | Docker only (built-in `docker` machine, private home, `LAYERFS_CONSTRUCTION_WORKERS=1`) |
| PostgreSQL | own container `fsh-pg`, sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652 (postgres:17-bookworm), 1 CPU, 512 MiB, one pre-created empty database per Store, `synchronous_commit=off` |
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
| H01 | SQLite | PASS | 1/1 | COMPLETE | 1 | 1,034 | 96.3 |
| H01 | PostgreSQL | PASS | 1/1 | COMPLETE | 1 | 1,033 | 161.6 |
| H02 | SQLite | PASS | 50/50 | COMPLETE | 1 | 1,061 | 476.5 |
| H02 | PostgreSQL | PASS | 50/50 | COMPLETE | 1 | 1,060 | 495.0 |
| H03 | SQLite | PASS | 50/50 | COMPLETE | 1 | 661 | 311.1 |
| H03 | PostgreSQL | PASS | 50/50 | COMPLETE | 1 | 660 | 550.2 |
| H04 | SQLite | PASS | 10/10 | COMPLETE | 1 | 223 | 64.5 |
| H04 | PostgreSQL | PASS | 10/10 | COMPLETE | 1 | 222 | 126.8 |
| H05 | SQLite | PASS | 20/20 | COMPLETE | 1 | 488 | 181.5 |
| H05 | PostgreSQL | PASS | 20/20 | COMPLETE | 1 | 487 | 373.6 |
| H06 | SQLite | PASS | 20/20 | COMPLETE | 20 | 640 | 189.7 |
| H06 | PostgreSQL | PASS | 20/20 | COMPLETE | 20 | 620 | 440.6 |
| H07 | SQLite | PASS | 20/20 | COMPLETE | 1 | 640 | 128.0 |
| H07 | PostgreSQL | PASS | 20/20 | COMPLETE | 1 | 639 | 290.8 |

Superseded attempts (kept as local evidence; see Observations):

| Case | Backend | Attempt | Execution | Cleanup | Reason |
| --- | --- | --- | --- | --- | --- |
| H02 | PostgreSQL | H02-postgresql | FAIL | INCOMPLETE | 00543_verify_b27: CLI/process exit 125 |

## Store bytes

| Case | Backend | Outcome | Commits | Floor (B) | Init (B) | Final (B) | Net (B) | Growth after Init (B) | Σ new_stored (B) | of which payload (B) | of which metadata (B) | Unattributed after Init and packs (B) |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H01 | SQLite | PASS | 500 | 212,992 | 24,248,320 | 32,477,184 | 32,264,192 | 8,015,872 | 1,721,854 | 516,311 | 1,205,543 | +6,294,018 |
| H01 | PostgreSQL | PASS | 500 | 753,664 | 37,879,808 | 37,502,976 | 36,749,312 | -1,130,496 | 1,721,638 | 516,311 | 1,205,327 | -2,852,134 |
| H02 | SQLite | PASS | 250 | 212,992 | 24,174,592 | 30,420,992 | 30,208,000 | 6,033,408 | 762,125 | 248,601 | 513,524 | +5,271,283 |
| H02 | PostgreSQL | PASS | 250 | 753,664 | 37,871,616 | 34,955,264 | 34,201,600 | -3,670,016 | 762,213 | 248,601 | 513,612 | -4,432,229 |
| H03 | SQLite | PASS | 50 | 212,992 | 24,186,880 | 28,802,744 | 28,589,752 | 4,402,872 | 265,814 | 350 | 265,464 | +4,137,058 |
| H03 | PostgreSQL | PASS | 50 | 753,664 | 30,932,992 | 32,350,208 | 31,596,544 | 663,552 | 265,834 | 350 | 265,484 | +397,718 |
| H04 | SQLite | PASS | 50 | 212,992 | 24,182,784 | 28,831,744 | 28,618,752 | 4,435,968 | 185,861 | 49,667 | 136,194 | +4,250,107 |
| H04 | PostgreSQL | PASS | 50 | 753,664 | 37,953,536 | 32,587,776 | 31,834,112 | -6,119,424 | 185,950 | 49,667 | 136,283 | -6,305,374 |
| H05 | SQLite | PASS | 100 | 212,992 | 24,272,896 | 29,478,584 | 29,265,592 | 4,992,696 | 313,458 | 103,988 | 209,470 | +4,679,238 |
| H05 | PostgreSQL | PASS | 100 | 753,664 | 85,811,200 | 67,854,336 | 67,100,672 | -18,710,528 | 313,461 | 103,988 | 209,473 | -19,023,989 |
| H06 | SQLite | PASS | 100 | 4,259,840 | 483,930,112 | 504,369,832 | 500,109,992 | 16,179,880 | 313,825 | 103,988 | 209,837 | +15,866,055 |
| H06 | PostgreSQL | PASS | 100 | 15,073,280 | 747,364,352 | 764,928,000 | 749,854,720 | 2,490,368 | 313,818 | 103,988 | 209,830 | +2,176,550 |
| H07 | SQLite | PASS | 200 | 212,992 | 24,231,936 | 30,175,232 | 29,962,240 | 5,730,304 | 696,721 | 204,239 | 492,482 | +5,033,583 |
| H07 | PostgreSQL | PASS | 200 | 753,664 | 64,380,928 | 41,492,480 | 40,738,816 | -23,642,112 | 696,599 | 204,239 | 492,360 | -24,338,711 |

SQLite parts (Σ over Stores). The product keeps a WAL of up to 4 MiB after quiesce, so file-only figures are shown beside file + WAL:

| Case | Init, file only (B) | Net, file only (B) | Net WAL (B) | Net, file + WAL (B) | Net allocated (B) | Growth after Init, file only (B) | File-only growth − Σ new_stored (B) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H01 | 24,248,320 | 28,069,888 | 4,194,304 | 32,264,192 | 32,264,192 | 3,821,568 | +2,099,714 |
| H02 | 24,174,592 | 26,013,696 | 4,194,304 | 30,208,000 | 30,212,096 | 1,839,104 | +1,076,979 |
| H03 | 24,186,880 | 24,432,640 | 4,157,112 | 28,589,752 | 28,594,176 | 245,760 | -20,054 |
| H04 | 24,182,784 | 24,424,448 | 4,194,304 | 28,618,752 | 28,618,752 | 241,664 | +55,803 |
| H05 | 24,272,896 | 25,108,480 | 4,157,112 | 29,265,592 | 29,270,016 | 835,584 | +522,126 |
| H06 | 483,930,112 | 483,930,112 | 16,179,880 | 500,109,992 | 500,174,848 | 0 | -313,825 |
| H07 | 24,231,936 | 25,767,936 | 4,194,304 | 29,962,240 | 29,966,336 | 1,536,000 | +839,279 |

PostgreSQL server WAL (the server is owned and serves one row at a time, but the LSN is server-wide):

| Case | Net schema bytes (B) | Server WAL floor→final (B, server-wide) |
| --- | ---: | ---: |
| H01 | 36,749,312 | 58,257,784 |
| H02 | 34,201,600 | 55,880,944 |
| H03 | 31,596,544 | 51,537,824 |
| H04 | 31,834,112 | 50,580,784 |
| H05 | 67,100,672 | 345,962,552 |
| H06 | 749,854,720 | 1,001,723,472 |
| H07 | 40,738,816 | 112,716,560 |

## H01 long history

Per-Commit `new_stored` and `new_metadata` (B) from the paged `commit list`, in blocks of 50 Commits (Commit 1 is the oldest):

| Commits | SQLite Σ new_stored (B) | SQLite mean new_stored (B) | SQLite max new_stored (B) | SQLite Σ new_metadata (B) | PostgreSQL Σ new_stored (B) | PostgreSQL mean new_stored (B) | PostgreSQL max new_stored (B) | PostgreSQL Σ new_metadata (B) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1–50 | 180,498 | 3,610 | 8,223 | 131,874 | 180,369 | 3,607 | 8,226 | 131,745 |
| 51–100 | 179,374 | 3,587 | 9,965 | 124,948 | 179,464 | 3,589 | 9,910 | 125,038 |
| 101–150 | 165,869 | 3,317 | 8,946 | 118,113 | 165,892 | 3,318 | 8,968 | 118,136 |
| 151–200 | 184,944 | 3,699 | 8,969 | 120,816 | 184,938 | 3,699 | 8,967 | 120,810 |
| 201–250 | 173,282 | 3,466 | 12,021 | 121,440 | 173,220 | 3,464 | 12,051 | 121,378 |
| 251–300 | 154,019 | 3,080 | 10,164 | 109,324 | 154,054 | 3,081 | 10,167 | 109,359 |
| 301–350 | 171,228 | 3,425 | 8,049 | 121,290 | 171,328 | 3,427 | 8,047 | 121,390 |
| 351–400 | 174,167 | 3,483 | 7,858 | 126,847 | 174,119 | 3,482 | 7,857 | 126,799 |
| 401–450 | 170,140 | 3,403 | 6,826 | 117,222 | 169,986 | 3,400 | 6,834 | 117,068 |
| 451–500 | 168,333 | 3,367 | 7,887 | 113,669 | 168,268 | 3,365 | 7,894 | 113,604 |

| Backend | Growth after Init (B) | Growth per Commit (B) | new_stored per Commit (B) | payload per Commit (B) | new_metadata per Commit (B) | Head logical (B) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | 8,015,872 | 16,032 | 3,444 | 1,033 | 2,411 | 64,660,289 |
| PostgreSQL | -1,130,496 | -2,261 | 3,443 | 1,033 | 2,411 | 64,660,289 |

## H02 many branches

| Backend | Branches | Own Σ new_stored: min (B) | median (B) | mean (B) | max (B) | of which metadata, mean (B) | Store delta per Branch: min (B) | median (B) | mean (B) | max (B) | Growth after Init ÷ Branches (B) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | 50 | 8,931 | 14,615 | 15,242 | 22,849 | 10,270 | 0 | 0 | 120,668 | 836,360 | 120,668 |
| PostgreSQL | 50 | 8,905 | 14,626 | 15,244 | 22,839 | 10,272 | -6,774,784 | 57,344 | -73,400 | 131,072 | -73,400 |

## H03 identical branches

| Backend | Branches | Own Σ new_stored: min (B) | median (B) | mean (B) | max (B) | of which metadata, mean (B) | Store delta per Branch: min (B) | median (B) | mean (B) | max (B) | Growth after Init ÷ Branches (B) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | 50 | 5,127 | 5,279 | 5,316 | 7,281 | 5,309 | 0 | 121,540 | 88,057 | 344,640 | 88,057 |
| PostgreSQL | 50 | 5,128 | 5,279 | 5,317 | 7,283 | 5,310 | 0 | 8,192 | 13,271 | 73,728 | 13,271 |

## H04 nested forks

| Backend | Branches | Own Σ new_stored: min (B) | median (B) | mean (B) | max (B) | of which metadata, mean (B) | Store delta per Branch: min (B) | median (B) | mean (B) | max (B) | Growth after Init ÷ Branches (B) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | 10 | 10,669 | 18,245 | 18,586 | 24,964 | 13,619 | 0 | 567,908 | 443,597 | 873,440 | 443,597 |
| PostgreSQL | 10 | 10,654 | 18,252 | 18,595 | 24,995 | 13,628 | -6,782,976 | 65,536 | -611,942 | 131,072 | -611,942 |

| Backend | Branch | Forked from | Commits listed | Own Σ new_stored (B) | Own Σ new_metadata (B) | Store delta (B) |
| --- | --- | --- | --- | ---: | ---: | ---: |
| SQLite | l01 | main | 5 | 18,138 | 14,788 | 803,432 |
| SQLite | l02 | l01 | 10 | 18,353 | 12,783 | 799,280 |
| SQLite | l03 | l02 | 15 | 14,568 | 8,872 | 741,600 |
| SQLite | l04 | l03 | 20 | 22,097 | 17,101 | 873,440 |
| SQLite | l05 | l04 | 25 | 18,361 | 14,353 | 824,000 |
| SQLite | l06 | l05 | 30 | 24,964 | 19,302 | 394,216 |
| SQLite | l07 | l06 | 35 | 16,759 | 10,635 | 0 |
| SQLite | l08 | l07 | 40 | 17,624 | 12,873 | 0 |
| SQLite | l09 | l08 | 45 | 10,669 | 7,608 | 0 |
| SQLite | l10 | l09 | 50 | 24,328 | 17,879 | 0 |
| PostgreSQL | l01 | main | 5 | 18,137 | 14,787 | 131,072 |
| PostgreSQL | l02 | l01 | 10 | 18,454 | 12,884 | 65,536 |
| PostgreSQL | l03 | l02 | 15 | 14,569 | 8,873 | 40,960 |
| PostgreSQL | l04 | l03 | 20 | 22,091 | 17,095 | 65,536 |
| PostgreSQL | l05 | l04 | 25 | 18,368 | 14,360 | -6,782,976 |
| PostgreSQL | l06 | l05 | 30 | 24,995 | 19,333 | 114,688 |
| PostgreSQL | l07 | l06 | 35 | 16,752 | 10,628 | 65,536 |
| PostgreSQL | l08 | l07 | 40 | 17,607 | 12,856 | 65,536 |
| PostgreSQL | l09 | l08 | 45 | 10,654 | 7,593 | 49,152 |
| PostgreSQL | l10 | l09 | 50 | 24,323 | 17,874 | 65,536 |

## H05 and H06: projects in one Store vs separate Stores

| Case | Backend | First project Init (B) | Later Inits: min (B) | mean (B) | max (B) | Own Σ new_stored per project (B) | Net ÷ projects (B) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| H05 | SQLite | 24,268,800 | 0 | 216 | 4,096 | 15,673 | 1,463,280 |
| H05 | PostgreSQL | 31,080,448 | -43,884,544 | 2,880,566 | 9,232,384 | 15,673 | 3,355,034 |
| H06 | SQLite | 24,227,840 | 24,137,728 | 24,194,856 | 24,256,512 | 15,691 | 25,005,500 |
| H06 | PostgreSQL | 30,965,760 | 36,929,536 | 37,705,189 | 37,969,920 | 15,691 | 37,492,736 |

| Backend | H05 net (B) | Σ H06 net (B) | Cross-project gain Σ H06 ÷ H05 (net) | H05 Init (B) | Σ H06 Init (B) | Gain on Init | Σ H06 final ÷ H05 final |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| SQLite | 29,265,592 | 500,109,992 | 17.09 | 24,272,896 | 483,930,112 | 19.94 | 17.11 |
| PostgreSQL | 67,100,672 | 749,854,720 | 11.18 | 85,811,200 | 747,364,352 | 8.71 | 11.27 |

## H07 combined

| Backend | Branches | Own Σ new_stored: min (B) | median (B) | mean (B) | max (B) | of which metadata, mean (B) | Store delta per Branch: min (B) | median (B) | mean (B) | max (B) | Growth after Init ÷ Branches (B) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | 20 | 25,463 | 34,258 | 34,836 | 44,229 | 24,624 | 0 | 0 | 286,515 | 1,577,992 | 286,515 |
| PostgreSQL | 20 | 25,466 | 34,245 | 34,830 | 44,251 | 24,618 | -26,255,360 | 131,072 | -1,182,106 | 212,992 | -1,182,106 |

## Cost per operation kind

Least-squares fit of per-Commit bytes on the five operation counts over every Commit of H01, H02, H04, H05 and H07 (no intercept; the counts always sum to 5, so each coefficient carries a fifth of the fixed per-Commit cost). Differences between kinds are the useful part; this is a diagnostic estimate, not a measurement.

| Backend | Operation | Commits | new_stored per op (B) | payload per op (B) | new_metadata per op (B) |
| --- | --- | --- | ---: | ---: | ---: |
| SQLite | edit | 1,100 | 438 | 152 | 285 |
| SQLite | new | 1,100 | 1,369 | 897 | 472 |
| SQLite | delete | 1,100 | 2,197 | 11 | 2,186 |
| SQLite | rename | 1,100 | 858 | 8 | 850 |
| SQLite | append | 1,100 | 561 | 208 | 352 |
| PostgreSQL | edit | 1,100 | 438 | 152 | 285 |
| PostgreSQL | new | 1,100 | 1,368 | 897 | 471 |
| PostgreSQL | delete | 1,100 | 2,198 | 11 | 2,187 |
| PostgreSQL | rename | 1,100 | 858 | 8 | 850 |
| PostgreSQL | append | 1,100 | 560 | 208 | 352 |

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
| H01 | SQLite | 32,264,192 | 1006.6 | 0.409 | 0.0039 | 1.413 | 1.171 |
| H01 | PostgreSQL | 36,749,312 | 883.8 | 0.466 | 0.0044 | 1.609 | 1.334 |
| H02 | SQLite | 30,208,000 | 540.3 | 0.423 | 0.0072 | 1.370 | 1.194 |
| H02 | PostgreSQL | 34,201,600 | 477.2 | 0.479 | 0.0082 | 1.551 | 1.352 |
| H03 | SQLite | 28,589,752 | 116.0 | 0.442 | 0.0337 | 1.339 | 1.246 |
| H03 | PostgreSQL | 31,596,544 | 104.9 | 0.489 | 0.0373 | 1.480 | 1.377 |
| H04 | SQLite | 28,618,752 | 115.8 | 0.434 | 0.0338 | 1.333 | 1.223 |
| H04 | PostgreSQL | 31,834,112 | 104.1 | 0.482 | 0.0376 | 1.483 | 1.360 |
| H05 | SQLite | 29,265,592 | 266.6 | 0.435 | 0.0147 | 1.353 | 1.228 |
| H05 | PostgreSQL | 67,100,672 | 116.3 | 0.998 | 0.0336 | 3.102 | 2.815 |
| H06 | SQLite | 500,109,992 | 15.6 | 0.386 | 0.2508 | 1.171 | 1.088 |
| H06 | PostgreSQL | 749,854,720 | 10.4 | 0.579 | 0.3760 | 1.756 | 1.631 |
| H07 | SQLite | 29,962,240 | 442.7 | 0.432 | 0.0088 | 1.367 | 1.216 |
| H07 | PostgreSQL | 40,738,816 | 325.6 | 0.587 | 0.0120 | 1.859 | 1.653 |

## Observations

- **Identical Branches are metadata only.** In H03 every Branch applies the same
  Commit. The first Branch stores 7,281 B (350 B of payload, 6,931 B metadata);
  each of the other 49 stores 5,279 B, all metadata. Σ payload over 50 Branches is
  350 B on both backends.
- **Distinct Branches cost their edits.** H02 (5 Commits per Branch): own Σ
  `new_stored` 8.9–22.8 KB per Branch, mean 15.2 KB; H07 (10 Commits): mean
  34.8 KB. H04 fork depth does not change the cost: levels 1–10 store 10.7–25.0 KB
  each with no trend, and a level's `commit list` shows its ancestors' Commits.
- **Long history stays flat.** H01's per-Commit `new_stored` averages 3,080–3,699 B
  in every block of 50 Commits, with no step past the delta depth cap of 16
  (≈ 1.0 KB payload + 2.4 KB metadata per Commit). The two backends agree within
  a few bytes per Commit.
- **Cross-project sharing.** Later base Inits into the H05 Store add 0–4,096 B
  (SQLite) each: the second to twentieth copies of the 65 MB base are deduplicated
  completely. Σ H06 ÷ H05 = **17.09×** net on SQLite (19.94× on Init alone) and
  **11.18×** on PostgreSQL. The PostgreSQL ratio is depressed by Init bloat (below).
- **Init floor.** One base Init stores 24.2 MB on SQLite (2.68× smaller than the
  65.0 MB tree) and 31–38 MB of schema on PostgreSQL. Net SQLite Store bytes are
  1.33–1.41× the Git pack + idx reference and 1.17–1.25× the approximate CDC oracle
  for the same states (H06: 1.17× and 1.09×).
- **Operation mix.** A least-squares fit over 1,100 SQLite Commits gives about
  440 B per in-place edit, 1.4 KB per new file, 560 B per append, 860 B per rename
  and 2.2 KB per delete (the last two almost all metadata). Renames store no
  payload: content moves unchanged and is reused, unlike the rename-over edits of
  fs-storage-micro M04, which write new content. The fit is diagnostic only.
- **SQLite WAL.** After quiesce the product keeps a `-wal` of 4,157,112–4,194,304 B
  per Store (its 4 MiB journal limit), so per-Branch Store deltas mostly show WAL
  reuse (median 0 B in H02/H07). In H01, H02, H05 and H07 main-file growth after
  Init exceeds Σ `new_stored` by 0.5–2.1 MB (pages, indexes and free space); in H03
  and H04 the two agree within 56 KB, and the H06 Stores' small histories never
  left the WAL (main-file growth 0 B).
- **PostgreSQL schema bytes depend on autovacuum.** Base Init leaves reclaimable
  space that autovacuum truncates later, so `server.schemas.layerfs` *falls*
  after Init in H01, H02, H04, H05 and H07 (H05: −18.7 MB after 100 Commits that
  added 313 KB of packs; one later Init probe in H05 even read 43.9 MB smaller
  than the one before). Quiesced schema bytes are therefore a snapshot of
  autovacuum timing, not a stable size; Commit accounting (`new_stored`) is
  unaffected. The suite does not run VACUUM, which would be Store-database
  administration.
- **Determinism (H04 SQLite, run twice on the same product).** Not byte-identical:
  Init floor −28,672 B (7 pages), final main file −20,480 B, WAL +37,192 B,
  net +16,712 B (0.06%), Σ `new_stored` +32 B and Σ `new_metadata` +32 B over 50
  Commits; Σ `new_canonical` identical. PostgreSQL was not repeated.

## Limits

- Docker only; no native, Lima or Apple Container rows.
- Counts were fixed by a 50 s SQLite probe (H04) and kept as specified. SQLite
  took 24.1 min for the seven rows and PostgreSQL 40.6 min (INELIGIBLE wall),
  over the 30-minute target; most of it is per-Branch Sandbox lifecycle and the
  one verification Exec per Branch, not Commits. Counts were not scaled because
  both backends must share one workload version.
- Init storage is in no Commit, so attribution starts at the Init floor. The
  spec formula net − (Σ new_stored + Σ new_metadata) double-counts metadata
  (`new_metadata` ⊂ `new_stored`); the report uses growth − Σ `new_stored`.
- PostgreSQL server WAL is server-wide (one owned server, one row at a time,
  includes Init and other databases' idle activity).
- References are computed from the in-memory oracle by `src/refs.py`, not by the
  directory-based shared helper; Σ `tar | zstd -3` uses Python `compression.zstd`
  level 3; the CDC oracle is approximate (different gear table).
- Text is synthetic (fixed 128-word vocabulary); the base is real code and docs.
- Per-Branch Store deltas are dominated by the SQLite WAL and PostgreSQL
  autovacuum; use each Branch's own Σ `new_stored` as its cost.

## Cleanup

Every row released its Stores (SQLite `store remove`, PostgreSQL `store
disconnect`) and reported cleanup COMPLETE. The superseded H02 PostgreSQL
attempt's dead Sandbox record was closed (`was_gone: true`) and its Store
disconnected after its status was recorded (33,579,008 B schema); the
interrupted Exec was not replayed. Then the Docker worker was stopped and its
container and data volume removed, the `fsh-pg` server, its container and data
volume (all 27 databases) were removed, and the suite image
`fs-storage-history:6d820c75` was deleted: no owned container or volume
remains, and Docker free space rose by 2,283,814,912 B. Kept locally (ignored,
unpublished): the private home, row results and ledgers, references JSON, the
extracted base tree and the pinned CLI/daemon copies (158 MB in all). Host free
space was checked before and after (no cleanup required).
