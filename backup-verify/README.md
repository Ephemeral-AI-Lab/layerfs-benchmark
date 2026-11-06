# backup-verify — backup and restore on MinIO and R2 under failures
> group: transfer · measures: correctness, recovery

## Basic info

| | |
| --- | --- |
| Tool | in-house: `run.py` (host driver) and `cases.py` (in-container steps, Python stdlib) |
| Drives | the public `layerfs backup` CLI (Connect), built `--features tls`, in Linux containers; nothing links LayerFS code |
| Runs on | a MinIO server and a Cloudflare R2 bucket; SQLite Disposable Stores |
| Status | active; first run 2026-11-06 (layerfs-project #1–#6) |
| Rules | the root [AGENTS.md](../AGENTS.md); one case per invocation, each within 110 s |

## Overview

Checks that a Store backed up to a bucket can always be restored intact,
and that failures never lose the last good backup or report false success.
A PASS means every check in the case held on that provider at that build;
it does not cover objects above the sizes run, LayerFS pieces, or R2 token
scoping. Times and sizes in reports are diagnostic.

| Case | Checks | Expected |
| --- | --- | --- |
| `roundtrip` | connect, list, create, restore, disconnect and every read command on a Store with history; progress | projects, branches, commits and tree roots identical |
| `isolated` | restore the roundtrip's backup into a fresh home from bucket, key and file name only; commit again | equals the source, writable |
| `refusals` | wrong secret, missing bucket, part sizes, missing backup, another home's copy, a changed Store | each refused with a clear code; nothing changed |
| `size` | one Store of `--mib`: times, peak RSS, scratch | sha256 round trip, no incomplete upload |
| `corrupt` | truncation, one byte, altered sha256, valid-sha256 non-Store, forged manifest, missing piece, removed object | refused; destination intact; no staging left |
| `kill` | SIGKILL mid-upload of a replacement and mid-download | previous copy restorable; leftovers swept by the next call |
| `cut` | connection lost mid-upload or mid-download (MinIO killed; R2 network detached) | refusal with a partial count; previous copy intact |
| `race` | a Store of the restore's name appears during the download | refused `Exists` after the download |
| `consistency` | commits land while the backup snapshots | restored branch is one frontier |
| `concurrent` | two creates of one Store; a restore racing a replacement | one create, the other `Busy`; one whole copy restored |
| `cleanup` | objects, pieces, incomplete uploads, local staging | inventoried; MinIO incomplete uploads aborted |
| `perms` | MinIO scoped users per policy; a revoked key | the calls each policy allows; revoked key refused, secret never shown; R2 NOT_RUN |
| `usage` | bucket and run-prefix bytes, incomplete uploads | report only |
| `v1-restore` (`schema_v2.py`) | a schema v1 CLI backs up a Store with history; a schema v2 CLI restores it into a fresh home | refused at the open check naming `tools/store_blocks.py migrate`; no Store, no staging; other Stores unchanged |
| `v1-migrate` (`schema_v2.py`) | `store_blocks.py migrate` of that closed v1 Store, then roundtrip and isolated checks with the v2 CLI | equals the v1 source; writable |

## Setup

1. Build the LayerFS CLI for Linux with `--features tls` and copy it to
   `bin/layerfs` (ignored).
2. For MinIO, run a MinIO container on a Docker network and create the
   bucket. For R2, create the bucket and an Object Read & Write token.
3. Write a private env file (mode 600, never committed):
   - MinIO: `LAYERFS_REMOTE_ENDPOINT`, `LAYERFS_REMOTE_BUCKET`,
     `LAYERFS_REMOTE_ACCESS_KEY`, `LAYERFS_REMOTE_SECRET_KEY`,
     `MINIO_CONTAINER`, `MINIO_NETWORK`.
   - R2: `LAYERFS_R2_ACCESS_KEY`, `LAYERFS_R2_SECRET_KEY`, `R2_ACCOUNT`,
     `R2_BUCKET`.
4. Run one case per invocation:

```bash
python3 run.py --provider minio|r2 --case NAME --run-id ID --env-file PRIVATE.env \
  [--prefix P] [--mib N] [--phase upload|download] [--part-size 16M] [--timeout 110]
```

The schema v2 cases (layerfs-project #91) take two CLIs and the v2 commit's
`tools/` and `engine/crates/layerfs-persistence/sql/` (e.g. from `git archive`),
MinIO only, `v1-restore` before `v1-migrate`:

```bash
python3 schema_v2.py --case v1-restore|v1-migrate --run-id ID --env-file PRIVATE.env \
  --cli-v1 DIR --cli-v2 DIR --tree-v2 DIR
```

Objects go under `bv-<run-id>/<prefix>/`; `isolated` defaults to the
`roundtrip` prefix. Each run gets its own Docker volume, and private key
files are removed when a case ends. Receipts and verdicts go to
`receipts/<run-id>/<provider>/` (ignored).

- **R2 budget:** before every R2 case the driver sums the bucket with
  `mc du` and refuses the case when usage plus twice its largest Store plus
  64 MiB would pass 5 GB, keeping the owner's account in the free tier.
- **Deletion:** the harness never deletes bucket objects, except MinIO
  incomplete uploads in `cleanup`.
- **Tools:** `mc` comes from the pinned MinIO image and runs as root so it
  can write the scratch volume; `find` runs in the build image.
- **Proxy:** Docker Desktop may inject an HTTP proxy into every container and
  override env-file values for it; MinIO cases clear it with explicit `-e`
  flags so `mc` and the CLI reach the MinIO container directly.

## Past runs

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-06 | `7691ac20b0` | Outcome: PASS on MinIO, 51 of 51 checks: schema v2 Stores round-trip, and a schema v1 backup is refused at open until migrated | [report](../result/2026-11-06/backup-verify/7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3/report.md) |
| 2026-11-06 | `c51d04b942` | Outcome: PASS on both providers after three product fixes | [report](../result/2026-11-06/backup-verify/c51d04b9428c4d56df690223ced1e3fe20f73dc2/report.md) |
<!-- runs:end -->
