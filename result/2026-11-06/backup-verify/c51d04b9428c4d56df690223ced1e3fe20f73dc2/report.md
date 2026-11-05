# backup-verify — MinIO and Cloudflare R2

> Status: Verification outcomes; timings are diagnostic and performance-ineligible.

**Outcome: PASS on both providers after three product fixes.** Every
scenario of layerfs-project #2, #4, #5 and #6 passed on MinIO and R2 at
the fixed build. Bucket-permission scoping (#3) passed on MinIO and is
NOT_RUN on R2. Three defects were found and fixed in
[PR #579](https://github.com/Ephemeral-AI-Lab/layerfs/pull/579) (below).

## Configuration

| Item | Identity |
| --- | --- |
| LayerFS | `c51d04b9428c4d56df690223ced1e3fe20f73dc2` (branch `issue5-backup-progress`, base `layerfs_v2_0_0`) |
| Failure matrix | run `20261106c` at `282ea970e840642e077aeb5856e1ecaed7272495`, CLI sha256 `93f39428b101d722fa8ef47d73509ba88a40045c7ffd6b940b08567346dc39f4` |
| Final build | run `20261106d` at `c51d04b942…`, CLI sha256 `9328119339d7cdda5f9ca58fe8abf0fb372c4f9079c1f6269500a4974ff4f835` |
| CLI | `layerfs-cli --features tls`, debug, Linux arm64 |
| Build/run image | `sha256:378b799ef43343fc64008b6a5ef456dd6bf0cb8f6ea4cec72e7b42dfc17d2cd6` |
| MinIO | `cgr.dev/chainguard/minio@sha256:4692462f35d97d7e82c30371d82f057703c5d9489bcae726010594c812f2d285`, HTTP on a Docker network, same host |
| R2 | real account, bucket `layerfs-stores`, region `auto`, over the internet from macOS Docker |
| Store | SQLite Disposable/WAL/OFF; Durable NOT_RUN (disabled by owner) |
| Host | macOS, Docker Desktop 8 CPU/8 GB; 1-min load 4–5 |

`c51d04b942` changes only the send-error path after `282ea970e8` (a 4xx
reply sent before the server stops reading the body). The cases that path
touches (`perms`, `roundtrip`, upload `cut`) were run again at
`c51d04b942`; the other matrix rows stand at `282ea970e8`.

## Results

Checks passed / failed per case. One sample per case.

| Case | MinIO | R2 | Covers |
| --- | ---: | ---: | --- |
| roundtrip | 16 / 0 | 16 / 0 | #2 every CLI call, history identity, progress |
| isolated | 5 / 0 | 5 / 0 | #2, #6 restore into a fresh home |
| refusals | 16 / 0 | 17 / 0 | #2 refusal codes (R2 adds the 5 GiB part refusal) |
| size (5 sizes / 3 sizes) | 30 / 0 | 18 / 0 | #4 |
| corrupt | 31 / 0 | 31 / 0 | #6 corruption, #5 failure after the transfer |
| kill (upload, download) | 11 / 0 | 11 / 0 | #6 |
| cut (upload, download) | 17 / 0 | 17 / 0 | #5, #6 |
| race | 4 / 0 | 4 / 0 | #5, #6 install race |
| consistency | 6 / 0 | 6 / 0 | #6 snapshot under 148 concurrent commits |
| concurrent | 7 / 0 | 7 / 0 | #6 |
| cleanup | 2 / 0 | inventory | #6 |
| perms | 27 / 0 | NOT_RUN | #3 |
| at `c51d04b942`: perms, roundtrip, upload cut | 51 / 0 | 24 / 0 | |

Failed checks recorded on the way and kept in the receipts: in `20261106c`
the first MinIO `isolated` ran under its own empty prefix (harness default;
4 failures, rerun under the roundtrip prefix passed), and the first
`perms` crashed in the harness after its checks (rerun passed). The
exploratory run `20261106b` found the defects below and three harness
faults (an `mc` that could not write the scratch volume, so no damage was
applied; no `find`/`grep` in the `mc` image; MinIO listing incomplete
uploads only by exact key).

### Sizes

Times are seconds of one CLI call, including snapshot and hash for create.
RSS is peak resident KiB; scratch is peak extra bytes on the home's volume.

| Provider | Store bytes | Part | Create s | Restore s | Create RSS | Restore RSS | Create scratch | Restore scratch |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MinIO | 1,277,952 | 5M | 0.104 | 0.052 | 22,484 | 1,192* | 1,290,240 | 0* |
| MinIO | 6,582,272 | 5M | 0.307 | 0.103 | 23,836 | 14,680 | 13,213,696 | 4,308,992 |
| MinIO | 68,063,232 | 5M | 2.275 | 0.688 | 24,048 | 14,680 | 131,104,768 | 67,747,840 |
| MinIO | 271,626,240 | 16M | 7.965 | 2.425 | 24,040 | 14,680 | 543,432,704 | 270,385,152 |
| MinIO | 1,085,669,376 | 64M | 31.361 | 9.775 | 24,072 | 18,744 | 2,171,383,808 | 1,085,689,856 |
| R2 | 1,277,952 | 5M | 1.652 | 1.644 | 26,936 | 19,408 | 1,290,240 | 1,306,624 |
| R2 | 6,582,272 | 5M | 3.692 | 1.576 | 28,340 | 19,408 | 6,643,712 | 5,206,016 |
| R2 | 68,063,232 | 5M | 18.774 | 2.859 | 28,484 | 23,796 | 68,124,672 | 68,112,384 |

\* sampled at 50 ms; the call ended before a sample.

Memory stays flat with size. Create needs 1–2× the Store in scratch.
Every size round-tripped its sha256 and left no incomplete upload. R2 was
capped at 64 MiB by the owner's 5 GB budget; the largest object
(4.995 TiB R2, 48.83 TiB MinIO) and pieces were not run.

### Failure matrix

| Phase | Fault | MinIO | R2 |
| --- | --- | --- | --- |
| create, upload | CLI killed | previous copy restorable; one incomplete upload; `<store>.backup` left, removed by the next create | same |
| create, upload | connection lost | `Failed` in 0.3 s; previous copy intact; incomplete upload left (abort failed) | `Failed` (part lost, abort lost) in 61–62 s; same state |
| restore, download | CLI killed | no Store; `.restore-*` left, removed by the next restore | same |
| restore, download | connection lost | `Failed` in 0.3 s; no Store; staging removed | `Failed` in 62.6 s; same |
| restore, verify | valid sha256, not a Store | every byte moved, refused at `verify`, exit 125 | same |
| restore, install | Store of that name appears | `Exists` after the download | same |
| restore | 7 kinds of damage | all refused, destination intact, no staging | same |
| create ×2 | same Store, same home | one succeeds, the other `Busy` | same |
| create + restore | replacement racing a restore | restore gets one whole copy (sha256-verified) | same |
| create | commits during the snapshot | restored branch is one frontier (counter = commit count) | same |

R2 cuts take up to the 60 s request timeout to notice a dropped network.
MinIO dropped an older incomplete upload when the same key was overwritten;
R2 aborts incomplete uploads after 7 days. LayerFS never aborts others'
uploads and never deletes bucket objects.

### Permissions (MinIO)

| Policy | connect | list | restore | create, replace |
| --- | --- | --- | --- | --- |
| ListBucket, GetObject | yes | yes | yes | `Failed: HTTP 403 AccessDenied` |
| + PutObject, AbortMultipartUpload, ListMultipartUploadParts | yes | yes | yes | yes |
| + DeleteObject | yes | yes | yes | yes |

A disabled key: `Failed: remote refused: HTTP 403 InvalidAccessKeyId`; the
secret appears in no output or log. Scoped users were removed afterwards.

## Defects found and fixed

| Commit | Defect | Found by |
| --- | --- | --- |
| `9767c5f335` | a trickling send held a request without bound; a lost completion whose abort also failed reported parts left instead of an uncertain object; MinIO's largest object and R2's part limit were wrong | #4, #6 |
| `282ea970e8` | two creates of one Store could replace the staged snapshot under each other, risking mixed bytes over the last good backup; a killed restore leaked its partial download | `concurrent`, `kill` |
| `c51d04b942` | a key without write access made create report `Unknown` (may have landed) instead of a 403 refusal | `perms` |

Each fix has a test that fails without it.

## Limits

- One sample per case; times are diagnostic (warm caches, shared host,
  debug build). No throughput claim.
- R2 permission scoping, R2 jurisdictions, HTTPS MinIO, pieces and
  TiB-scale objects: NOT_RUN.
- Two homes writing the same file at once are not serialized (no bucket
  compare-and-swap); documented in the guide.
- CI on PR #579 reports 5 test failures that also fail on other branches of
  the same base (sandbox, workspace names, machine start, SQLite
  publication); not caused by this change.

## Cleanup

MinIO incomplete uploads under `bv-20261106c/` were aborted by `cleanup`.
Test objects remain under `bv-*` and `issue5-*`/`issue6-*` prefixes in
both buckets: R2 bucket total 722 MB at the end (budget 5 GB); remove
those prefixes with the provider's tools. Local receipts stay in the
ignored `backup-verify/receipts/`. Private key files, the MinIO container,
its network and the run volumes were removed after the run.
