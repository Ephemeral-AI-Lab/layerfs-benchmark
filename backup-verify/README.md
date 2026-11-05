# backup-verify — LayerFS backups on MinIO and Cloudflare R2

Fault and recovery scenarios for `layerfs backup` against real buckets
(layerfs-project #1–#6). Every step runs the public CLI inside a Linux
container; nothing links LayerFS code.

- `run.py` — host driver: one case per invocation, own Docker volume per
  run, private key files removed at the end, verdicts and receipts under
  `receipts/<run-id>/<provider>/` (ignored).
- `cases.py` — runs inside the container (Python stdlib): fixtures, CLI
  calls with timestamped progress, peak RSS and scratch use, snapshots and
  comparisons of projects/branches/commits/trees, churn and race helpers.

## Run

```bash
# pinned Linux CLI built with --features tls, copied to bin/layerfs
python3 run.py --provider minio|r2 --case NAME --run-id ID --env-file PRIVATE.env \
  [--prefix P] [--mib N] [--phase upload|download] [--part-size 16M] [--timeout 110]
```

`PRIVATE.env` (mode 600, never committed):

- MinIO: `LAYERFS_REMOTE_ENDPOINT`, `LAYERFS_REMOTE_BUCKET`,
  `LAYERFS_REMOTE_ACCESS_KEY`, `LAYERFS_REMOTE_SECRET_KEY`,
  `MINIO_CONTAINER`, `MINIO_NETWORK`.
- R2: `LAYERFS_R2_ACCESS_KEY`, `LAYERFS_R2_SECRET_KEY`, `R2_ACCOUNT`,
  `R2_BUCKET`.

Each case finishes within the 110 s container timeout. Objects go under
`bv-<run-id>/<prefix>/`; the harness never deletes bucket objects except
MinIO incomplete uploads in `cleanup`.

**R2 budget:** before every R2 case the driver sums the bucket with
`mc du` and refuses the case when usage plus twice its largest Store plus
64 MiB would pass 5 GB, keeping the owner's account inside the free tier.

## Cases

| Case | Checks |
| --- | --- |
| `roundtrip` | fixture with history, connect/list/create/restore/disconnect, every read command, progress, identity of projects, branches, commits and tree roots |
| `isolated` | restore the roundtrip's backup into a fresh home from bucket, key and file name only; compare; commit again |
| `refusals` | wrong secret, missing bucket, part sizes, missing backup, another home's copy, a changed Store |
| `size` | one Store of `--mib`: times, peak RSS, scratch, sha256 round trip, no incomplete uploads |
| `corrupt` | truncation, one byte, altered sha256, valid-sha256 non-Store, forged manifest, missing piece, removed object: refused, destination intact, no staging |
| `kill` | SIGKILL mid-upload of a replacement and mid-download: previous copy restorable, leftovers inventoried and swept |
| `cut` | connection lost mid-upload or mid-download (MinIO killed; R2 network detached) |
| `race` | a Store of the restore's name appears during the download |
| `consistency` | commits land while the backup snapshots; the restored branch is one frontier |
| `concurrent` | two creates of one Store; a restore racing a replacement |
| `cleanup` | inventory of objects, pieces, incomplete uploads and local staging |
| `perms` | MinIO scoped users: which calls each policy allows; a revoked key; R2 NOT_RUN |
| `usage` | bucket and run-prefix bytes, incomplete uploads |

The `mc` client comes from the pinned MinIO image and runs as root so it
can write the scratch volume; `find` runs in the build image.
