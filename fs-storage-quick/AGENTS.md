# fs-storage-quick agent instructions

> Status: Implemented storage workload contract (`fs-storage-quick-v1`).

Follow root [AGENTS.md](../AGENTS.md) and [shared/STORAGE.md](../shared/STORAGE.md).
This suite came from
[layerfs-project#85](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/85)
(parent #84). It is the quick before/after gate for storage optimizations: a
candidate build runs the matrix and `run.py compare` checks it against the
pinned baseline. It measures Store bytes, never speed; the full fs-storage
suites stay the release check.

## Frozen workload

- [image/gen.py](image/gen.py) (Q1–Q5) is fs-storage-micro's generator at
  smaller counts, with SHAKE-256 streams keyed by `WORKLOAD_VERSION`
  (`fs-storage-quick-v1`). [image/model.py](image/model.py) (Q6) is a verbatim
  copy of fs-storage-history's `fsh-edit-model-v1`, with seeds prefixed by the
  workload version. Both are baked into the suite image; every Exec checks the
  script's SHA-256 against the repository copy. Any change to either script,
  a count or the base tree is a new `WORKLOAD_VERSION`, image, pins and
  baseline.
- Counts (frozen after the calibration probes, see the README): Q1 2,000
  files; Q2/Q3/Q4 25 files × 12 edits (13 Commits, identical content, only the
  write method differs); Q5 32 MiB + 5 edits; Q6 2 Inits of the 65.0 MB
  DSH-157 base, 20 edit Commits, 3 identical Branches.
- [src/pins.json](src/pins.json) holds each case's final-state oracle, tied to
  both scripts' hashes ([src/pin.py](src/pin.py): Q1–Q5 in a throwaway
  container of the suite image, Q6 on the host from the base tree). Rows do
  not start without matching pins.
- Q6's base is DSH checkpoint 157 extracted with
  `fs-storage-history/src/base.py` into a private directory (never commit it);
  `run.py` re-checks its pins before a row.

## Execution

- Docker machine only; rows serial; all SQLite rows, then all PostgreSQL rows,
  so each backend's matrix wall is one interval (target ≤ 120 s per backend,
  INELIGIBLE). One fresh Store per row; one pre-created empty database per
  PostgreSQL row. One attempt per row: a registered row is never rerun; a new
  attempt is a new campaign id (new Stores and databases).
- Every command has its own deadline ≤ 120 s. A failed or uncertain Commit
  makes the row FAIL and keeps its Store (`cleanup: INCOMPLETE`); never retry,
  replay or delete runtime state by hand.
- Verification is final state only, once per Branch head: after the work's
  unmount, a fresh mount of the head in the same Sandbox runs one manifest Exec
  (Q1–Q5: full canonical manifest; Q6: every path's kind/mode/size plus the
  SHA-256 of every path the edit model touched on that Branch, because hashing
  the 65 MB base per head does not fit the budget). Verification therefore
  precedes the quiesced `final` probe, identically for baseline and candidate.
- `--late-probe-wait-s N` (outside the budget) defers every row's Store
  release (`cleanup: DEFERRED`), waits once until N s after the last row, then
  probes each Store again as `late` (SQLite after the worker's 60 s idle close,
  PostgreSQL after autovacuum had a chance) and releases it. `run.py release`
  / `finish` release any Store still deferred.
- `--attribution DIR` is a **DIAGNOSTIC, owner-decision-pending** option
  (layerfs-project#85 task 1; the repository rule bans direct Store SQL). It is
  off by default and runs only after the late probe: SQLite `dbstat` on a
  closed copy taken read-only from the worker volume; PostgreSQL catalog sizes,
  `n_dead_tup` and `last_autovacuum` in a read-only transaction on the row's
  own disposable database. Never cite it as a benchmark result.

## Compare and report

- `run.py export` writes the row summaries; the base build's export is pinned
  as `baseline/<full-sha>.json`. `run.py compare --baseline … --candidate …`
  prints Δ bytes, Δ% and a verdict per metric; the noise rule is in
  [src/results.py](src/results.py) (±1 page per Store table for Store bytes,
  ±16 B per Commit for `new_stored`/`new_metadata`, exact otherwise; each band
  widened to the |Δ| of a same-build repeat pinned into the baseline with
  `run.py add-repeat`). A new baseline (new workload version or new base
  build) is pinned with its own repeat campaign.
- Pinned baselines: `b4fa173e40…` (the #84 starting point) and
  `02133596ae…` (after the #84 Phase 1 fixes #86–#89; compare #90–#92
  candidates against it). After #86, SQLite file-only bytes are not
  comparable with the first baseline (WAL bytes moved into the file); judge
  SQLite on file+WAL and late (closed) bytes there.
- [src/report.py](src/report.py) renders one report from an export; publish it
  under `result/` and run `python3 shared/src/readme_index.py`. Ledgers,
  campaign caches and exports other than the pinned baseline stay local.
