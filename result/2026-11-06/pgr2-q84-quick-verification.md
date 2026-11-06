# Quick verification: PostgreSQL round 2 (#61) merged with storage efficiency (#84)

> Status: Verification outcomes. Counts and bytes are the evidence; timings are
> diagnostic and performance-ineligible (INELIGIBLE cache state).

**Outcome: PASS.** On the merged identity V every expectation of the
merge-and-quick-verification spec holds:

- **Backup:** B1–B4 pass on MinIO (51/51 checks). A schema v1 backup is refused
  by the v2 CLI at the open check, naming `tools/store_blocks.py migrate`.
  After that offline migration the Store round-trips identically.
- **Speed:** the subset passes 36/36 rows (32 + 4). PostgreSQL statement and
  connection counts equal the control C in every phase, except C16 Commit,
  which drops 251 → 224 statements. There is no aggregate flag and no
  per-row flag.
- **Storage:** all six rows (Q1/Q5/Q6 × SQLite/PostgreSQL) pass with verified
  final state, and every metric is `same` as the #84 final S.

Round 2 and the storage changes compose without changing each other's
results.

**Merged (2026-11-06).** All these merges and pushes were plain, with no
force push:

- layerfs#594 → `layerfs_v2_0_0` `0ae7a539c9`;
- layerfs#596 → `opt/91-gap-blocks` `b293887488`;
- layerfs#595 → `layerfs_v2_0_0` `e20c6a2f73` (tree `3a44cc1b94` = S);
- `pg-r2` pushed with `d0e8c13142` (merge of `e20c6a2f73`, tree `87f25ed37f`)
  and `6f09a1fdde` (the rustfmt commit, tree `dd191babb88e`);
- layerfs#597 → `layerfs_v2_0_0` `9c21b680f3`, **tree `dd191babb88e` = V's
  tree**, so the verified identity is the merged one.

## Identities

| Name | Commit | Tree | Role |
| --- | --- | --- | --- |
| V | `b092e012ddc6ca22fbd0a9076bb5aaacfaca9b0e` (local branch `q84-v`) | `dd191babb88e` | treatment: `pg-r2` `048d604dc1` + #84 final `7691ac20b0` (merge `d871d78433`, tree `87f25ed37f`) + a rustfmt-only commit |
| C | `048d604dc106e3cfafcbd031c897ba9a6fd91ed1` | — | speed control: current layerfs#597 head |
| S | `7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3` | `3a44cc1b94` | storage reference (#84 final, layerfs-benchmark#11); receipts reused, not rerun |

The tree `87f25ed37f` is the planned step-3 merge of `layerfs_v2_0_0`
(#594 + #595/#596) into `pg-r2`. The merge of `7691ac20b0` gives the same
tree, because `7691ac20b0`'s tree equals `8b701f42f0` + #594 + #595/#596. The
pushed `pg-r2` head must have tree `dd191babb88e` to carry this verification.

Sealed artifacts, built with `build-artifacts.sh` (release; macOS CLI and
daemon with PostgreSQL support; Linux bundle):

| | CLI sha256 | daemon sha256 | Linux bundle | source tree sha256 |
| --- | --- | --- | --- | --- |
| C `048d604dc1` | `a6720a15a595…` | `61e51d11a1b0…` | `d42ac7782820…` | `f5278669…` |
| V `b092e012dd` | `b170658044d8…` | `8cabd30582e2…` | `f0babddf525d…` | `ffd3bc93…` |

Conditions: Docker Desktop (arm64, 8 CPU / 8 GB), macOS host. SQLite
Disposable (WAL, synchronous=OFF); Durable NOT_RUN (disabled by owner).
PostgreSQL 17.11 with `synchronous_commit=off`. `LAYERFS_CONSTRUCTION_WORKERS=1`.
Fresh homes, workers and databases throughout; one sample per case and arm;
1-minute load recorded; no load waits and no reruns.

## Step 0: backup checks B1–B4 (MinIO only)

Run `q84s0`, MinIO `cgr.dev/chainguard/minio@sha256:4692462f…`, on a Docker
network. Two CLIs, both from sealed Linux bundles:

- v1: C `048d604dc1`, schema v1, CLI sha256 `6b07b677…`;
- v2: S `7691ac20b0`, schema v2, CLI sha256 `2bc54c72…`.

S's storage code is identical to V's: the V merge conflicted only in a test
file, and the rustfmt commit changes no tokens.

| Check | How | Checks | Outcome |
| --- | --- | ---: | --- |
| B1 | `run.py --case roundtrip`, v2 CLI | 16/16 | projects, branches, Commits (ids, roots) and trees identical; sha256 and heads equal; progress ends at bytes |
| B2 | `run.py --case isolated`, v2 CLI | 5/5 | restore into a fresh home equals the source; a new Commit succeeds |
| B3 | `schema_v2.py --case v1-restore` | 12/12 | the v1 CLI backs up a v1 Store (user_version 22); the v2 restore is refused: `Failed: the pulled Store does not open … Refused { status: "schema version 1 Store (…, before #91): convert a closed copy offline with tools/store_blocks.py migrate" }`. No Store and no `.restore-*` folder are left. An unrelated v2 Store in that home is unchanged (history and sha256), and so is the v1 source. |
| B4 | `schema_v2.py --case v1-migrate` | 18/18 | `store_blocks.py migrate` (S tree) gives user_version 22 → 42, 1 value block and 3 hint blocks; the source copy is unchanged. The v2 CLI reads the migrated Store equal to the v1 snapshot. Then B1 + B2 on it under a new prefix: the restored copy and the fresh-home restore equal the v1 source, and new Commits succeed. |

Path A (schema v2 accepted) therefore holds.

## Step 3 checks on V

| Check | Outcome |
| --- | --- |
| Conflict | Only `core/crates/layerfs-storage/tests/stored_value_reads.rs`: both sides appended a test; both kept. Tree `87f25ed37f` as predicted. |
| Build + tests | Reused from the coordinator's run on the identical tree `87f25ed37f`: 9 packages built with PostgreSQL features; 324 binaries, 323 pass. The 46 FUSE binaries ran in a privileged `/dev/fuse` container. The only failure is `filesystem_attributes` (sealed fixture absent in the container), which fails the same way on `pg-r2`. The rustfmt commit changes no tokens. |
| Clippy `-D warnings` | PASS, 0 warnings, at both `d871d78433` and `b092e012dd`. Packages: persistence, store-service, daemon and control (postgresql/machine), storage, content, workspace, history, bridge, machine. |
| `cargo +1.85.1 fmt --all -- --check` | FAIL at `87f25ed37f`: 6 files from #594 (#92), with the same drift at `c5604ef662` and `7691ac20b0`. Fixed by the rustfmt-only commit `b092e012dd` (LOC 141,111 → 141,118, +7 from line splitting). PASS after it. |

## 5.1 Speed subset: fs-bench-quick gate `q84-2` (+ extra `q84-2x`)

Harness `pg-r2-bench` @ `7b4a7b6`. Cells C09, C14, C16 and C17 × arms SQLite
and PostgreSQL (published port) × C/V × 2 paired rounds = 32 rows. Rows
32/32 PASS, cleanup COMPLETE. 1-minute load min 4.0, median 4.5, max 7.7.

**Counts, PostgreSQL arm** (statements/connections per phase; a = C, b = V):

| Cell | create | mount | exec | Commit | unmount | Expected | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C09 | 3/2 | 14/0 | 6/0 | 1/0 | 0/0 | 3/2, 14/0, 6/0, 1/0, 0/0 | PASS (from `q84-2x`) |
| C14 | 4/3 | 14/0 | 0/0 | 1/0 | 0/0 | 4/3, 14/0, 0/0, 1/0, 0/0 | PASS |
| C16 | 4/3 | 14/0 | 80/0 | 251/1, 251/1 → **224/1, 224/1** | 0/0 | V ≤ C + 2; expected ≈220–251 | PASS (−27) |
| C17 | 3/2 | 14/0 | 68/0 | 1/0 | 0/0 | 3/2, 14/0, 68/0, 1/0, 0/0 | PASS |

C16 PostgreSQL Commit, 251 → 224 statements: #91's value blocks and #90's
narrow rows take fewer statements under round 2's batched reads, as the spec
predicted. Connections are equal everywhere.

**Timings (diagnostic).** Aggregate per arm and phase over the 8 pairs: no
flag. The largest values were SQLite exec +4.7 ms (+2.6%, 5/8 slower) and
PostgreSQL create +3.1 ms (+1.1%, 4/8). PostgreSQL Commit −2.2 ms (−3.6%,
1/8 slower). Per-row 2-pair flags: none.

The two #84 flags stay clear:

- C14 PG exec: median 57 → 33 ms, delta −24 ms (0/2 slower).
- C09 PG exec: 87 → 87 ms (1/2 slower).

C16 PG Commit: 856 → 838 ms, delta −18 ms (0/2 slower). Order of magnitude
against gate-05 (`76a32a9a10`):

| Measure | gate-05 | C | V |
| --- | ---: | ---: | ---: |
| C14 PG end-to-end | ≈840 ms | 1012 ms | 679 ms |
| C09 PG exec | ≈85 ms | 87 ms | 87 ms |
| C16 PG Commit | ≈990 ms | 856 ms | 838 ms |
| C16 SQLite Commit | ≈735 ms | 701 ms | 713 ms |
| C17 PG exec | ≈390 ms | 354 ms | 366 ms |

C14 PG C r1 create (846 ms) is the first PostgreSQL row on that worker.

**Extra gate `q84-2x`.** On the recreated `pgr2b-pg`, the four C09 PostgreSQL
rows of `q84-2` (rows 5–8) ran before the `pg_stat_statements` extension
existed in the server's `postgres` database. Their counts are UNAVAILABLE in
the receipts, and the rows were not replayed. The separately labelled extra
gate `q84-2x` (C09 × PostgreSQL × C/V × 2 rounds, fresh homes and workers)
recovered them: 4/4 PASS, counts as in the table above, no flags.

new_stored per C16 Commit (bytes): PostgreSQL 186,857 / 186,872 →
186,856 / 186,863; SQLite 186,852 / 186,903 → 186,901 / 186,918.

## 5.2 Storage subset: fs-storage-quick campaign `q84-st3`

Harness: layerfs-benchmark `main` @ `50a1bd5`. Its `fs-storage-quick`,
`shared` and `fs-storage-history/src` are byte-identical to S's frozen copy,
except S's older README. Rows Q1, Q5 and Q6 × SQLite and PostgreSQL, one row
per command, then a 75 s late probe, as S. Suite image `fs-storage-quick:v1`
`sha256:fedbb407…`.

The PostgreSQL server was `q84-st-pg`: `postgres:17-bookworm` `639ab7ce…`,
1 CPU / 512 MiB, loopback, as S's `fsopt-final-pg`. All six rows PASS with
verified final state, cleanup COMPLETE. Matrix wall (INELIGIBLE): SQLite
19.2 s, PostgreSQL 30.4 s.

`run.py compare --baseline <S qfin-c1 rows.json> --candidate rows.json`:
**Regressions: none. Not comparable: none.** The only missing rows are Q2–Q4,
which were not selected (spec section 6). Every metric is `same`:

| Row | Commits | Σ new_canonical | Σ payload | Σ new_stored (S → V) | Σ new_metadata (S → V) | Net bytes (S → V, Δ) | Late net (S → V) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Q1 SQLite | 1 | 4,356,403 | 4,115,113 | 4,132,331 → 4,132,320 | 17,218 → 17,207 | 4,538,368 → 4,534,272 (−4,096) | 4,538,368 → 4,534,272 |
| Q1 PostgreSQL | 1 | 4,356,403 | 4,115,113 | 4,132,328 → 4,132,330 | 17,215 → 17,217 | 5,136,384 → 5,136,384 (0) | 5,160,960 → 5,160,960 |
| Q5 SQLite | 6 | 34,942,963 | 34,653,459 | 34,734,401 → 34,734,394 | 80,942 → 80,935 | 35,037,184 → 35,041,280 (+4,096) | 35,037,184 → 35,041,280 |
| Q5 PostgreSQL | 6 | 34,942,963 | 34,653,459 | 34,734,402 → 34,734,404 | 80,943 → 80,945 | 36,511,744 → 36,511,744 (0) | 36,528,128 → 36,528,128 |
| Q6 SQLite | 23 | 1,292,935 | 20,118 | 56,058 → 56,065 | 35,940 → 35,947 | 23,691,264 → 23,629,824 (−61,440) | 23,691,264 → 23,629,824 |
| Q6 PostgreSQL | 23 | 1,292,935 | 20,118 | 56,040 → 56,037 | 35,922 → 35,919 | 25,640,960 → 25,559,040 (−81,920) | 25,640,960 → 25,616,384 |

**Bands.** Commits, canonical and payload are exact. new_stored and
new_metadata stay within ±16 B per Commit; the largest difference is 11 B on
one Commit (Q1 SQLite). For net bytes, the schema v2 table counts were
recounted:

- SQLite: 24 tables in a CLI-created v2 Store (user_version 42), so ±98,304 B.
  The harness default of 25 tables gives ±102,400 B.
- PostgreSQL: 22 tables (19 in `schema.sql` + 3 in `acquisition.sql`), so
  ±180,224 B.

The largest net differences are −61,440 B (SQLite) and −81,920 B (PostgreSQL),
both inside either band. SQLite late WAL is 0 B on every row.

## Harness changes (this report's commit)

- `backup-verify/run.py`: Docker Desktop now injects an HTTP proxy into every
  container and overrides env-file values for it, so `mc` and the CLI reached
  the MinIO container through the proxy, which refused with 403. MinIO cases
  now clear the proxy with explicit `-e HTTP_PROXY= …` flags; R2 is unchanged.
- `backup-verify/schema_v2.py` (new): the B3 `v1-restore` and B4 `v1-migrate`
  cases. They reuse `run.py`'s `Case` with two CLIs and the v2 tree's
  `tools/store_blocks.py`.

## Incidents and abandoned selections (kept, not replayed)

- `pgr2b-pg` had been released after the #98 final run. It was recreated from
  its recorded configuration: same image digest, settings, 2 CPU / 2 GiB, port
  55442, fresh volume. The recreated server was missing two pieces of the
  original's one-off setup:
  - Role `bench`: gate `q84-1` setup failed at `CREATE DATABASE … OWNER
    bench`, with no workers or databases created. The gate was abandoned
    (`ABANDONED.txt`).
  - Extension `pg_stat_statements` in `postgres`: covered by `q84-2x` above.
- V moved from `d871d78433` to `b092e012dd` (rustfmt) before any measured row.
  The `d871d78433` artifacts are marked DISCARDED.
- Storage campaigns `q84-st1` (environment only) and `q84-st2` (databases
  only; its environment recorded the `d871d78433` CLI) were abandoned before
  any row and their databases dropped. `q84-st3` is the measured campaign.

## Not run, and why (spec section 6)

- Full 96-row gate and four-machine final: 5.1 did not flag.
- fs-storage micro/dsh/history: 5.2 shows no change from S.
- Q2–Q4: delta selection, changed only by #84 and measured there.
- C01, C04, C13 and C18: covered by C14 and C16.
- fs-bench-pro: frozen.
- R2: not needed.
- Durable: disabled by owner.

## Receipts (local, untracked)

- Speed: `fs-bench-quick/results/pg-r2-gate/q84-2/` and `…/q84-2x/`; state
  and ledgers `~/.cache/pg-perf-r2/bench/q84-2{,x}/` (`summary.md`).
- Storage: `~/.cache/pg-perf-r2/q84/st/campaigns/q84-st3/` (`environment.json`,
  `campaign/`, `rows.json`, `run.log`, `compare-S-7691ac20b0.md`).
- Backup: `backup-verify/receipts/q84s0/minio/` (`verdicts.jsonl`,
  `receipts.jsonl`, case logs).
- Product checks: Clippy `~/.cache/pg-perf-r2/q84/clippy-v{,2}.log`, fmt
  `fmt-v.log`; the coordinator's test logs on `87f25ed37f`:
  `~/.cache/pg-perf-r2/coord/x84-{tests,fuse}/`.
