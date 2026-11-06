# fs-storage-micro agent instructions

> Status: Implemented storage workload contract (`fs-storage-micro-v1`).

Follow root [AGENTS.md](../AGENTS.md) and [shared/STORAGE.md](../shared/STORAGE.md).
This suite came from
[layerfs-project#81](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/81)
(parent #80). It measures Store bytes, never speed.

## Frozen workload

- [image/gen.py](image/gen.py) is the workload: SHAKE-256 streams keyed by
  `WORKLOAD_VERSION` give every byte, size and choice, so output is identical
  on any Python 3. Any change to it is a new `WORKLOAD_VERSION`, new image and
  new pins. Every Exec checks gen.py's SHA-256 against the repository copy.
- `PLAN` (per case: Commits, and the parts run as one Exec each before a
  Commit) and `WRITE_METHOD` are part of the workload. M03, M04 and M05 write
  the identical content sequence; only the write method (and M05's names)
  differ.
- M08 bytes depend on the SQLite library, so pins and oracles are emitted in
  a throwaway container of the suite image (`pin.py --docker-image`), never on
  host Python.
- [src/pins.json](src/pins.json) holds the final-state oracle (canonical
  manifest digest) and the offline references for each case, tied to
  gen.py's hash. Rows are NOT_RUN without matching pins. The full reference
  JSON stays in the private work directory.

## Execution

- Docker machine only; SQLite then PostgreSQL per case; rows serial. One
  fresh Store per row (and one pre-created empty database per PostgreSQL
  row). One attempt per row: a registered row is never rerun; a second sample
  is an explicit `--repeat N` row on its own Store.
- Each command has its own deadline of at most 120 s (Exec and Commit 120 s,
  others 60 s). No overall row budget, because storage is not timed; wall time
  is recorded only as an INELIGIBLE diagnostic.
- A failed or uncertain Commit makes the row FAIL and keeps its Store
  (`cleanup: INCOMPLETE`). Never retry, replay or delete runtime state by hand.
- Verification is final state only: after the quiesced probe, a fresh Sandbox
  mounts `lane` and `gen.py manifest .` must equal the pinned oracle.
- Repeat one smoke case once (`--repeat 2`) and report whether Store bytes and
  per-Commit counters are identical.

## Report

[src/report.py](src/report.py) renders lifecycle, Store bytes (floor, final,
net, SQLite file/WAL/allocated parts), per-Commit attribution, references and
ratios, then one section per case with expected vs actual and the per-Commit
`new_stored`/`new_metadata` curve for SQLite and PostgreSQL side by side.
Hand-written observations, limits and cleanup come from `--notes`. Publish one
report under `result/` and run `python3 shared/src/readme_index.py`; ledgers,
receipts and reference JSON stay local.
