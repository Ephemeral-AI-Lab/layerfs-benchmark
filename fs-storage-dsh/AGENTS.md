# fs-storage-dsh agent instructions

> Status: Implemented storage workload `fs-storage-dsh-v1`; bytes only, no timing claims.

Follow root [AGENTS.md](../AGENTS.md) and [shared/STORAGE.md](../shared/STORAGE.md).
This suite replays the DeepSeek-harness checkpoint history through Workspace
Commits and weighs the Store. It came from
[layerfs-project#82](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/82)
(parent #80) and replaces the archived `.archive/dsh-dedup` SDK harness, which
stays frozen. Its storage numbers are context only (different route and
policy history).

## Frozen workload

- **Seed.** `deepseek-history-data/git-snapshots-157-v1/snapshots.git` (157
  trees as linear Commits; pack SHA-256 `27c7598c…8133bc`), its
  `mapping.json`, the corpus `checkpoint-manifest.json` and the corpus's own
  state-157 oracle, each pinned by size and SHA-256 in
  [src/cases.py](src/cases.py) (`SEED_FILES`, identity
  `seed_manifest_sha256()`). A local pinned copy only; never publish it, and
  never name a published dataset "DeepSeek Harness".
- **Cases.** D10 = `sorted(set(range(1,158,10)) | {157})` (17 states),
  D03 = `range(1,158,3)` (53 states). Both end at state 157.
- **Route.** Empty project → one Sandbox and Workspace on branch `lane` → per
  state one Exec `python3 /opt/fs-storage-dsh/apply.py <prev> <k>` (prev 0 =
  empty) and one Commit, which must be `Committed` → unmount, close → probe →
  paged `commit list` → `verify.py 157` once in a fresh Sandbox. No per-state
  verify, no per-Commit fork, no segments, alarms or timers, no SDK.
- **Write method** (part of the workload): changed regular files are rewritten
  in place (same inode, `O_WRONLY|O_TRUNC`); removed paths and file↔symlink
  changes are unlinked; new paths `O_CREAT|O_EXCL`; symlink retarget =
  unlink + symlink; mode-only change = chmod; emptied directories removed.
- **Policy.** LayerFS 2.0's fixed storage policy is recorded, never varied.

Changing the seed, selections, scripts or route is a new workload version.

## Execution

Use [src/run.py](src/run.py) only: rows run serially, D10 then D03, SQLite
then PostgreSQL, one attempt each. One fresh Store per row (SQLite: `store
create` + `project init` of an empty folder + `store push docker`; PostgreSQL:
`store connect` to a pre-created empty database). Every CLI call has its own
deadline (`command_timeout_s`, at most 120 s). A failed or uncertain Commit
makes the row FAIL and keeps its Store; nothing is retried. A Docker capacity
problem is an infrastructure blocker, not a product FAIL.

Docker only: native, Lima and Apple Container add rows but no byte
information. Determinism is checked once by repeating D10 SQLite in a separate
campaign on the same product identity.

## References

Computed once per workload version outside LayerFS and pinned by the JSON's
SHA-256 (the report lists them):

1. `src/materialize.py` (inside the suite image) writes the selected states
   with the image's own `apply.py` and checks state 157 against its oracle.
2. `src/git_reference.py` (inside the suite image) recomputes the Git pack +
   idx with the dsh-dedup v1.0.0 recipe from the seed trees. `--threads=2`
   makes it vary by a few kB between runs; the pins are confirmed within that.
3. `src/references_dsh.py` (host) runs `shared/src/references.py` for
   whole-file unique, Σ `tar | zstd -3` and the approximate CDC oracle, and
   merges the Git result.

## Report

Publish one report with [src/report.py](src/report.py): configuration and
identities, per-case Store tables (SQLite then PostgreSQL), attribution,
references and ratios, a `new_stored` curve summary, determinism, observations
against dsh-dedup (context only), limits and cleanup. Receipts, ledgers and
reference JSON stay local under `~/.cache/fs-storage-dsh/`.
