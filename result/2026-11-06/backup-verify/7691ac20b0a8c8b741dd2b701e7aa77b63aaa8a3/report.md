# backup-verify — schema v2 (MinIO)

> Status: Verification outcomes; times are not measured.

**Outcome: PASS on MinIO, 51 of 51 checks: schema v2 Stores round-trip, and a schema v1 backup is refused at open until migrated.**
A schema v2 CLI refuses a schema v1 backup at the open check. The refusal
names `tools/store_blocks.py migrate`, and the restore leaves nothing behind.
After that offline migration the Store round-trips identically.

This was step 0 (B1–B4) of the merge-and-quick-verification for layerfs-project
#61 and #84. The overall report is
[pgr2-q84-quick-verification](../../pgr2-q84-quick-verification.md).

## Configuration

| Item | Identity |
| --- | --- |
| v2 CLI | `7691ac20b0` (#84 final integration, schema v2), from its sealed Linux bundle; sha256 `2bc54c721e0a…` (release, `--no-default-features --features postgresql`) |
| v1 CLI | `048d604dc1` (layerfs#597 head before the merge, schema v1), from its sealed Linux bundle; sha256 `6b07b677c1f0…` |
| v2 tree for `store_blocks.py` | `git archive 7691ac20b0 tools engine/crates/layerfs-persistence/sql` |
| Harness | `run.py` with the MinIO proxy fix, and the new `schema_v2.py` |
| MinIO | `cgr.dev/chainguard/minio@sha256:4692462f35d9…`, HTTP on a Docker network, same host; run id `q84s0` |
| Store | SQLite Disposable/WAL/OFF; Durable NOT_RUN (disabled by owner) |
| Host | macOS, Docker Desktop 8 CPU / 8 GB; 1-min load 3–4 |

The storage code of `7691ac20b0` is identical to the merged
`layerfs_v2_0_0` `9c21b680f3`. The merge conflicted only in a test file, and
its one extra commit is rustfmt-only.

## Results

One sample per case.

| Check | Case | Checks | Outcome |
| --- | --- | ---: | --- |
| B1 | `roundtrip` (v2 CLI) | 16 / 0 | projects, branches, Commits (ids, roots) and trees identical; sha256 and heads equal; progress ends at bytes (229,376 B) |
| B2 | `isolated` (v2 CLI) | 5 / 0 | the restore into a fresh home equals the source; a new Commit succeeds |
| B3 | `v1-restore` | 12 / 0 | see below |
| B4 | `v1-migrate` | 18 / 0 | see below |

**B3 (`v1-restore`).**
- The v1 CLI made a Store with history (user_version 22) and backed it up.
- The v2 restore was refused with this message:
  `Failed: the pulled Store does not open: … Refused { status: "schema version 1 Store (one row per inode value and binding hint, before #91): convert a closed copy offline with tools/store_blocks.py migrate" }`.
- No Store named `shop` was made, and no `.restore-*` staging folder was left.
- An unrelated v2 Store in the same home (user_version 42) kept its history
  and its sha256, and so did the v1 source.

**B4 (`v1-migrate`).**
- `store_blocks.py migrate` turned the closed v1 copy into user_version 42,
  with 1 value block and 3 hint blocks. The source copy was unchanged.
- The v2 CLI read the migrated Store equal to the v1 snapshot.
- Roundtrip and isolated checks then ran under a new prefix. The restored
  copy and the fresh-home restore both equal the v1 source, and new Commits
  succeed on the migrated Store, the copy and the fresh-home restore.

A first attempt failed before any check ran: `mc` and the CLI reached MinIO
through Docker Desktop's injected HTTP proxy, which returned 403. The harness
now clears the proxy for MinIO containers.

Receipts (local, untracked): `backup-verify/receipts/q84s0/minio/`.
