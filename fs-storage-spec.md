# fs-storage — storage-efficiency benchmarks for LayerFS

> Status: Implemented 2026-11-06 (34 of 34 rows PASS). Tracked by
> `Ephemeral-AI-Lab/layerfs-project#80`. The suite folders' own `AGENTS.md`
> and `README.md` files define the frozen workloads. This file is the
> design record.

Three CLI-only suites measure **how many bytes a LayerFS Store holds** for a
known workload. They do not measure speed. Build and run them in this order:

1. **fs-storage-micro**: one storage mechanism per case, generated data.
2. **fs-storage-dsh**: real repository history (the DeepSeek-harness checkpoints) at stride 10 and stride 3.
3. **fs-storage-history**: history shape (long history, many branches, nested forks, cross-project) built by a seeded edit model.

## Why

LayerFS v2.0.0 stores content with:

- **CAS**: BLAKE3 object IDs. Exact reuse covers chunks, whole files and trees across the whole Store, including across projects.
- **CDC**: GEAR at 8/16/32 KiB, for files of 128 KiB and up. Smaller files are one whole-file object.
- **Delta encoding**: zstd prefix deltas with a depth cap of 16 for whole files, 8 for chunks and 8 for metadata. The base is the previous version for in-place or rename-over edits; otherwise an 8,192-slot similarity ring is used.
- **Compression**: per-object zstd level 3.
- **Storage layout**: append-only immutable packs stored as rows in the Store database.

No current suite measures Store bytes; every existing report marks storage
UNAVAILABLE. The archived `dsh-dedup` harness (SDK route) did measure them,
but a stride-1 run took about 16 minutes, and over half of that was
per-state and per-Commit re-verification rather than storage work.

## Matrix

Storage is not timed, so only Docker is used. Native, Lima and Apple
Container add rows without adding information about bytes.

| Suite | Cases | Data | Docker + SQLite | Docker + PostgreSQL | Rows |
| --- | --- | --- | --- | --- | ---: |
| fs-storage-micro | M01–M08 | Generated from fixed seeds | ✓ | ✓ | 16 |
| fs-storage-dsh | D10, D03 | DeepSeek-harness checkpoint seed | ✓ | ✓ | 4 |
| fs-storage-history | H01–H07 | Seeded edit model on a base tree | ✓ | ✓ | 14 |
| **Total** | **17** | | | | **34** |

## Shared measurement

**Quiesced boundary.** Measure after every Workspace is unmounted and every
Sandbox is closed, so no daemon holds the Store open.

**Primary metric: Store bytes.**

- **SQLite:** `layerfs store status <store>` → `file.bytes` (st_size) plus
  `file.wal_bytes`. Also record allocated bytes (`st_blocks × 512`) of the
  Store file inside the Docker worker volume, read-only, with Docker tooling.
- **PostgreSQL:** `layerfs store status <store>` →
  `server.schemas.layerfs` (sum of `pg_total_relation_size`, including
  TOAST and indexes). Use one pre-created empty database per row. Server WAL
  is reported separately, or as UNAVAILABLE.

**Net Store bytes** = Store bytes − empty-Store floor. The floor is measured
on the same backend after `store create`/`store connect` plus `project init`
of an empty folder (and `store push` to Docker for SQLite).

**Per-Commit accounting.** `layerfs commit list <project> <branch>`, followed
to the last page (the old harness lost 5 of 52 Commits by not paging). For
each Commit record `logical`, `new_canonical`, `new_stored` and
`new_metadata`. Report:

- the curve of `new_stored` per Commit;
- Σ`new_stored` and Σ`new_metadata`;
- **unattributed bytes** = net Store bytes − Σ`new_stored`. `new_stored` already counts all new pack bytes, and `new_metadata` is a subset of it; payload = `new_stored` − `new_metadata`.
- For SQLite, report net with and without the `-wal` file. A quiesced Store keeps up to 4 MiB of WAL (`journal_size_limit`).

**Ratios:**

- logical ÷ net Store bytes;
- net Store bytes ÷ each reference;
- net Store bytes ÷ ideal unique bytes (space amplification).

**References.** Computed outside LayerFS once per workload version, pinned
with hashes, and not rerun on every row:

- **Whole-file unique bytes:** the sum of distinct file contents.
- **Σ per-snapshot `tar | zstd -3`:** compression with no dedup.
- **Git pack + idx:** a fresh bare repo with one Commit per state, then `git repack -a -d -f --window=10 --depth=50`.
- **Approximate CDC oracle:** FastCDC 8/16/32 KiB, unique chunks, each compressed with zstd -3. Labelled approximate, because the GEAR table differs.

**Units.** Exact integer bytes. MB = 10⁶ B, MiB = 2²⁰ B, always labelled.

**Time.** Wall time per row is recorded as an INELIGIBLE diagnostic only. No
speed claims.

## Shared rules

- Public `layerfs` CLI only, with an absolute path. Pin the `layerfs_v2_0_0` source SHA and the matched CLI, daemon and Linux bundle.
- Private `LAYERFS_HOME` and `LAYERFS_CONSTRUCTION_WORKERS=1`. Invoke with argument arrays, and check both the CLI exit and the Exec `exit_code`.
- No SDK, no direct Store SQL, no manual deletion of runtime state, and no automatic retry or replay.
- **One fresh Store per row.** `project remove` frees nothing and 2.0 has no GC.
- **Failed or uncertain Commits.** A failed or uncertain Commit can leave orphan packs. The row is FAIL and kept.
- **Write method is part of the workload.** Every case declares how it writes, because bytes depend on it. The methods are:
  - in-place rewrite (same inode, `O_WRONLY|O_TRUNC`);
  - write-then-rename;
  - new path.
- **Storage policy is fixed in 2.0** (128 KiB cutoff, depths 16/8/8, compile-time CDC and zstd). Record it; do not vary it.
- **Determinism.**
  - Inputs come from fixed seeds or pinned files, and input manifest hashes are recorded.
  - On the same product identity, a case must give the same Store bytes.
  - Check this once on one smoke case per suite and report any variance.
- **Verification is final state only.** For each row, check each branch head once: path, type, mode, size and SHA-256 against the oracle, with no missing or extra paths. Do not verify every state or every Commit.
- **Bounded commands.** Every command has an explicit timeout of 120 s or less. Long histories run as many bounded CLI calls.
- **Reports.** One report per suite at `result/YYYY-MM-DD/<suite>/<full-layerfs-sha>/report.md`.
  - Group tables by case, with SQLite then PostgreSQL.
  - Use separate named columns with units.
  - Run `python3 shared/src/readme_index.py` afterwards.
  - Logs, receipts and exports stay local and ignored.
- **Suite folders.** Each suite gets its own folder with `README.md` (`> group: filesystem · measures: storage`), `AGENTS.md`, `environments.example.json`, `src/` and `tests/`.

## fs-storage-micro

**Starting view:** an empty project. The generator runs inside the Sandbox
from a fixed seed. Generated text uses a seeded word model and is labelled
synthetic. The expected results are what the design should produce. A case
passes when it runs and verifies; the bytes are reported against the expected
result, not gated by it.

| Case | Workload | Write method | Commits | Expected result |
| --- | --- | --- | ---: | --- |
| M01 tiny files | 10,000 files of 0–4,096 B in 100 directories | New paths | 1 | Net bytes ÷ 10,000 = overhead per small file |
| M02 duplicates | One 50 MB generated tree, then 10 copies at new paths | New paths | 2 | Second Commit stores only tree/metadata (≈0 payload) |
| M03 in-place edits | 100 text files of 16–64 KiB, 20 Commits each changing 1% of lines | In-place `O_TRUNC` | 21 | Deltas against the previous version; chain passes depth 16 |
| M04 rename-over edits | Same as M03 | Write temp + rename | 21 | Compare with M03 |
| M05 new-path edits | Same as M03, each version at a new path, old removed | New path + unlink | 21 | Similarity ring only; compare with M03 |
| M06 large file | 64 MiB seeded random file, then insert 1 B at start, insert 1 B at middle, overwrite 4 KiB at middle, append 1 MiB, delete first byte | In-place `O_TRUNC` | 6 | Each edit adds ≈1–2 chunks (≤64 KiB), except append (≈1 MiB) |
| M07 compressibility | 64 MiB random, 64 MiB zeros, 64 MiB generated text, one file per Commit | New paths | 3 | Random ≈64 MiB stored raw, zeros ≈0, text at the zstd-3 ratio |
| M08 SQLite churn | 32 MiB SQLite database, 10 Commits each updating 1% of rows, then `VACUUM` | In-place (SQLite writes) | 12 | Page-local churn reuses most chunks; `VACUUM` reshuffles |

## fs-storage-dsh

**Corpus:** the DeepSeek-harness history, 157 checkpoints (every 100th of
15,632 Commits plus the last), 4,936,693,030 logical bytes. It is BSD-3-Clause
or MIT depending on checkpoint.

**Seed:** `deepseek-history-data/git-snapshots-157-v1/snapshots.git`, a
54 MB bare repo with the 157 trees as linear Commits. It is copied into the
Sandbox image (under 0.1 GB). The old harness baked a 1 GB `corpus.tar` with
all 157 states.

**Starting view:** an empty project. Each state is applied by `apply.py` inside
the Workspace:

- changed regular files are rewritten in place (same inode, `O_TRUNC`);
- removed paths and type changes are unlinked;
- new paths are created;
- empty directories are removed.

Then the state is committed.

| Case | States | Selection | Logical bytes | Git pack + idx (pinned in dsh-dedup v1.0.0) |
| --- | ---: | --- | ---: | ---: |
| D10 | 17 | `sorted(set(range(1,158,10)) \| {157})` | 561,010,345 | 41,797,536 |
| D03 | 53 | `range(1,158,3)` | 1,676,767,835 | 48,169,384 |

The Git references are recomputed once to confirm them. Earlier LayerFS
results came through the SDK route with a different policy history: 53,125,120
and 69,455,872 B allocated in dsh-dedup v1.0.0. They are shown only as
context, not as a comparable baseline. Stride 1 (157 states) is not in the
regular set.

**Dropped from dsh-dedup:**

- per-state live verification;
- fork, mount and verify for every Commit;
- the 80 s segment and 115 s alarm machinery;
- apply and Commit timers;
- one Docker client container per step.

## fs-storage-history

**Base tree:** see the decision below. The default is DSH checkpoint 157
(9,415 files, 65.0 MB). It is imported with `project init`, so the base's
storage reflects the Init route and is reported separately as the
Init floor.

**Edit model** (seeded and deterministic from `(seed, step)`). Each Commit applies
5 operations drawn from:

| Share | Operation |
| ---: | --- |
| 70% | Small in-place text edit (1–5 lines) |
| 10% | New file |
| 5% | Delete |
| 10% | Rename |
| 5% | Append to a log file |

| Case | Shape | Commits | What it shows |
| --- | --- | ---: | --- |
| H01 long history | 1 project, 1 branch × 500 Commits | 500 | Delta chains past the depth cap; growth per Commit |
| H02 many branches | 50 branches from base, 5 Commits each, distinct seeds | 250 | Extra bytes per branch |
| H03 identical branches | 50 branches from base, the same single edit | 50 | Should be ≈ metadata only per branch |
| H04 nested forks | Fork chain 10 deep, 5 Commits per level | 50 | Branches of branches |
| H05 projects in one Store | 20 projects from the same base, 5 Commits each, distinct seeds | 100 | Cross-project sharing |
| H06 projects in separate Stores | Same 20 projects, one Store each | 100 | Baseline: Σ H06 ÷ H05 = cross-project gain |
| H07 combined | 4 projects × 5 branches × 10 Commits in one Store | 200 | Everything at once |

The counts are initial. A probe run fixes them before the workload version is
frozen, with a target of 30 minutes or less per backend.

## Findings from the first run (2026-11-06)

- **Packs and git.** `new_stored` includes `new_metadata`, so unattributed bytes = net − Σ`new_stored`. Packs match the git pack to within 0.99–1.08×. The rest of the Store is database overhead: about 27% on SQLite and about 42% on PostgreSQL.
- **SQLite WAL.** A quiesced SQLite Store keeps up to 4 MiB of WAL, which may still hold frames that haven't been checkpointed. Report both the file-only and the file + WAL values.
- **PostgreSQL schema size depends on autovacuum timing.** Space freed after Init is truncated later. Growth after Init can therefore be negative.
- **Determinism.** Repeats are close but not always byte-identical: a few SQLite pages, and a few bytes of `new_metadata` per Commit.
- **`workspace mount` refuses `main`.** Every case forks working Branches from it.
- **Rename-over for files under 128 KiB gets no delta base** (the `normalize.rs` size filter). It costs about the same as writing a new path. In-place whole-file chains are limited by the 512 KiB canonical chain budget before depth 16 (files of about 64 KiB reach depth 6–7).
- **`LAYERFS_HOME` must be mode 0700.**

## Out of scope and known gaps

- **Space reclamation.** 2.0 has no GC or branch/project removal that frees bytes (layerfs-project#41). Add removal and reclaim cases after #51 and #52.
- **No CLI call reports Store-wide totals.** The internal `get_storage` returns logical, stored and metadata totals. A payload / metadata / "other" breakdown needs either that exposed in the CLI, or an owner-approved offline read of a Store copy. Until then, report only CLI values and file/schema sizes.
- **No stride 1 in the regular set.**
- **No other machines.** Add them only if a byte difference between machines is suspected.

## Decisions to confirm

The default is listed first.

1. **Runner:** the shared `shared/src/runner.py` Campaign for custody, plus a storage case driver and its own `report.py`. The alternative is a standalone runner in the `backup-verify` style.
2. **DSH seed hosting:** a local pinned copy first. Later, publish a trees-only seed with a neutral name (the name is trademarked) and no author emails, as a Hugging Face dataset pinned by revision or a GitHub release asset. Do not use GitHub LFS.
3. **fs-storage-history base tree:** DSH checkpoint 157. Alternatives are a pinned public repository (e.g. cpython at a fixed SHA) or a generated tree.
4. **Offline Store breakdown:** not done unless the owner approves.
