# fs-storage-history agent instructions

> Status: Implemented storage workload contract (`fs-storage-history-v1`).

Follow root [AGENTS.md](../AGENTS.md) and [shared/STORAGE.md](../shared/STORAGE.md).
This suite measures Store bytes for seven history shapes on Docker with
SQLite then PostgreSQL (14 rows). It came from
[layerfs-project#83](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/83)
under the parent spec #80. Storage is not timed: wall time is an INELIGIBLE
diagnostic.

## Frozen workload

- **Base tree:** DSH checkpoint 157, the last Commit of the local read-only
  seed `git-snapshots-157-v1/snapshots.git` (pack SHA-256 `27c7598c…33bc`).
  [src/base.py](src/base.py) extracts raw blobs (not `git archive`, whose
  `.gitattributes` would rewrite `*.cmd` line endings), writes files 0644 or
  0755 and checks the pins in [src/cases.py](src/cases.py): 9,404 files,
  11 symlinks, 65,020,822 B, manifest `59069f60…cd52`. Keep the extracted
  copy in a private cache; never commit or publish it.
- **Edit model:** [src/model.py](src/model.py) `fsh-edit-model-v1`. Five
  operations per Commit from a BLAKE2b counter PRNG keyed by
  `(MODEL_VERSION, seed, step)`; no `random` module, so Python 3.9–3.14 agree.
  The host plans each step against the oracle state and sends the concrete
  operations (zlib + base64) to `/opt/fs-storage-history/model.py apply`
  in the Workspace, which checks each touched file's SHA-256 first
  (a precondition, not verification). Directories left empty are removed.
- **Seeds:** `H01/p01/b01`, `H02/p01/bNN`, `H04/p01/lNN`, `H05/pNN/b01`
  (H06 reuses H05's, so both hold identical content), `H07/pNN/bNN`; every
  H03 Branch uses `H03/shared`, so all 50 apply the same Commit.
- **Counts:** the SQLite probe (H04, 50 s) confirmed the initial counts fit
  the 30-minute-per-backend target, so they were frozen unchanged. Changing a
  count, the model or the base is a new `WORKLOAD_VERSION`.

`main` cannot be mounted, so every case forks Branches from `main` (H04
forks each level from the previous level's head). Each Branch gets one
Sandbox: create, mount, one Exec + one Commit per step, unmount, a fresh
verification mount with one manifest Exec, unmount, close.

## Measurement

- One fresh Store per row (H06: 20 Stores per backend). The floor is the
  Store after `store create`/`connect` + `project init <store>/e <empty>`
  (+ `store push <store> docker` for SQLite). Base Inits follow (SQLite: on
  the Docker worker after the push), each probed: the last is the Init floor.
- Probes are quiesced only (no Workspace, no Sandbox): floor, after each
  Init, after each Branch, final. SQLite = `file.bytes + file.wal_bytes`,
  plus allocated bytes read-only in the worker volume; PostgreSQL =
  `server.schemas.layerfs`, plus the server WAL LSN from the owned server.
- The SQLite WAL stays near its 4 MiB limit after quiesce, so small Store
  deltas (per Branch) mostly measure WAL reuse. Report main-file and WAL
  parts, and use each Branch's own Σ `new_stored` from the paged
  `commit list` as the per-Branch cost.
- `new_stored` is every new pack byte of a Commit and `new_metadata` a subset
  of it: payload = stored − metadata; unattributed = growth after Init −
  Σ `new_stored` (Init storage is in no Commit).
- References come from the oracle in [src/refs.py](src/refs.py) once per
  workload version (the shared directory-based `references.compute` would
  need ~83 GB of state directories).

## Execution

Run rows serially, SQLite then PostgreSQL, one attempt each, Docker free
space ≥ 20 GiB first (a row not started for capacity is not a product
result). A failed or uncertain call ends the row FAIL and is never retried;
a failed Commit keeps its Store. Every command is bounded at 110 s. Release
each row's Stores at the end of the row, and the Docker worker, image and
PostgreSQL server/data after the last row. Publish one report with
[src/report.py](src/report.py); results, ledgers and references stay local.
