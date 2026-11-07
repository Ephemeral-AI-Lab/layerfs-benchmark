# Rerun 2026-11-08: LayerFS `b9c4adcb` vs ovnfs `5d54cb0`

**On one 500 MiB file, LayerFS `layerfs_v2_0_0` @ `b9c4adcb`:**
- commits an append in 1.40 s (ovnfs 1.35 s);
- commits a brand-new file in 1.82 s (ovnfs 0.84 s);
- commits a 100-byte edit in 15–19 ms (ovnfs 0.77–1.14 s);
- commits cutting 500 MiB off the file in 18 ms (ovnfs 1.14 s).

Each LayerFS commit stores only the chunks that changed: 0–33 KB for edits, cuts and removals. Each ovnfs commit that changes the file stores a full copy of it.

On the small histories S1–S4, LayerFS needs 8–10% fewer bytes than ovnfs. ovnfs imports 6–8× faster and reads whole trees or files 2–5× faster.

Every head on both systems matched its oracle. Storage numbers are exact bytes. Timings are warm, one sample per case unless stated, and are diagnostics, not qualified performance claims.

The small-history edit, commit and branch-open timings mostly measure the route into each system. Inside its container, ovnfs applies an edit step in about 30 ms and commits in 8–12 ms ([morning rerun](../rerun-2026-11-07/report.md)). So those rows don't show which system edits or commits faster on small histories. The large-file commit differences are far larger than one `docker exec` (~50–100 ms) and stand.

## Configuration

| | LayerFS | ovnfs |
| --- | --- | --- |
| Version | `layerfs_v2_0_0` @ `b9c4adcb04f3445d1488698d4956f2010798a6d9` ([PR #612](https://github.com/Ephemeral-AI-Lab/layerfs/pull/612)); bundle built from `bd21785a1f`, the same tree | `stencil-hq/ovnfs` @ `5d54cb0aec474c9aad90f43214ae4ba2bfab1d89` |
| Where it ran | public CLI on macOS → Docker machine: worker container, Sandboxes as namespaces in it | daemon + FUSE in one container per case (`fsh-cmp-ovnfs:5d54cb0`) |
| Persistence | SQLite Store, Disposable, on the worker's Docker volume; `LAYERFS_CONSTRUCTION_WORKERS=1` | state directory on an ext4 Docker volume |
| Ran (+08) | 500 MiB cases 2026-11-07 21:05–21:12; S1–S4 2026-11-08 01:24–01:26 | S1–S4 2026-11-07 14:38–14:42; L500 17:49; ADD500/DEL500 19:27; NEW500/RM500 19:33 |
| Host 1-minute load | 5.2–8.2 | S1–S4 5.6–7.7; L500 14–15; others 4.7–8.6 |

The ovnfs runs are reused from the [morning rerun](../rerun-2026-11-07/report.md) and [the evening one](../rerun-2026-11-07-v2-speed/report.md), which have the same ovnfs build and host. ovnfs was not rerun for this LayerFS build. The drivers and workloads are unchanged:
- S1–S4: [../rerun-2026-11-07/compare.py](../rerun-2026-11-07/compare.py);
- the 500 MiB cases: [../rerun-2026-11-07-v2-speed/harness/](../rerun-2026-11-07-v2-speed/harness/).

## One 500 MiB file

Every case writes or changes 500 MiB of seeded random (incompressible) data, then commits once. L500 is the exception: it has five commits of a 100-byte overwrite.

| Case | What the commit records |
| --- | --- |
| NEW500 | a tree holding a 1 MiB file, plus a brand-new 500 MiB file |
| ADD500 | the 500 MiB L500 file with 500 MiB appended (so it becomes 1000 MiB) |
| RM500 | removing an existing 500 MiB file from the tree |
| DEL500 | cutting the last 500 MiB off a 1000 MiB file |
| L500 | five commits, each overwriting 100 bytes of the 500 MiB file |

**Commit time.** NEW500 and ADD500 are 3 LayerFS runs each, shown as median (range).

| Case | ovnfs | LayerFS |
| --- | ---: | ---: |
| NEW500 | **841 ms** | 1,820 ms (1,207–2,943) |
| ADD500 | **1,351 ms** | 1,404 ms (1,377–1,441) |
| RM500 | 75 ms | **11 ms** |
| DEL500 | 1,141 ms | **18 ms** |
| L500, each of 5 commits | 770–1,140 ms | **15–19 ms** |

**Storage and data movement.**

| Case | Stored by the commit(s): ovnfs | Stored by the commit(s): LayerFS | Stored at end: ovnfs | Stored at end: LayerFS | Base into the system: ovnfs (copy + import) | Base into the system: LayerFS (import) | Read final file: ovnfs | Read final file: LayerFS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| NEW500 | 524,316,672 | 530,235,392 | 526,520,320 | 531,509,248 | 36 + 81 ms | 48 ms | **576 ms** | 2,794 ms |
| ADD500 | 1,048,604,672 | **530,190,336** | 1,574,051,840 | **1,060,556,800** | 5,281 + 1,088 ms | 4,200 ms | **1,233 ms** | 5,507 ms |
| RM500 | 24,576 | 0 | 526,520,320 | 531,492,864 | 5,038 + 1,061 ms | 4,294 ms | 82 ms | 56 ms |
| DEL500 | 524,316,672 | **8,192** | 1,574,051,840 | **1,060,630,528** | 10,251 + 1,989 ms | 8,318 ms | **579 ms** | 2,877 ms |
| L500 (5 commits) | 2,621,501,440 | **32,768** | 3,146,948,608 | **530,423,808** | 5,369 + 1,179 ms | 4,355 ms | **660 ms** | 3,058 ms |

Storage values are bytes. "Stored by the commit(s)" is the Store size at the end minus its size after import. For LayerFS NEW500 and ADD500, storage and data-movement figures come from the median run.

- **Creating a new file:** both systems store it once. ovnfs commits about 2× faster. The LayerFS NEW500 runs varied from 1.2 to 2.9 s; the slowest was the first case after the machine started.
- **Appending:** commit times are about even. LayerFS stores only the new 500 MiB; ovnfs stores a new 1000 MiB copy.
- **Edits and cuts:** LayerFS commits in 11–19 ms and stores at most a few pages. ovnfs copies the remaining file on every commit: 524 MB for DEL500, 524 MB per L500 commit.
- **Getting the base in:** ovnfs's import from a file already in its volume takes 1.1–2.0 s. Copying the file into its container first (a harness choice, `docker cp`) took 5.0–10.3 s. LayerFS's import sends the file from the Mac to the worker and stores it in 4.2–8.3 s.
- **Reads:** ovnfs reads the final file 2.2–5.0× faster. The exception is RM500, which only reads the small remaining file.

## Small histories: S1–S4

Times are medians in ms; storage is in bytes.

| Case | Arm | Heads | Import | Edit step | Commit | Branch open | No-op route | Full read | Stored at end |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S1 | ovnfs | 1/1 | **353** | 82 | 66 | 119 | 52 | **2,087** | 26,374,144 |
| | LayerFS | 1/1 | 2,254 | 58 | 20 | 31 | 27 | 4,154 | **24,043,520** |
| S2 | ovnfs | 5/5 | **393** | 81 | 66 | 128 | 51 | **1,757–1,943** | 26,177,536 |
| | LayerFS | 5/5 | 2,256 | 64 | 20 | 38 | 26 | 3,629–4,544 | **23,879,680** |
| S3 | ovnfs | 4/4 | **370** | 80 | 66 | 83 | 53 | **1,623–1,869** | 25,653,248 |
| | LayerFS | 4/4 | 2,191 | 66 | 23 | 38 | 27 | 3,777–4,363 | **23,834,624** |
| S4 | ovnfs | 5/5 | **393** | 86 | 63 | 139 | 64 | **1,688–1,893** | 25,706,496 |
| | LayerFS | 5/5 | 3,157 | 76 | 33 | 41 | 42 | 3,945–4,367 | **23,773,184** |

- **Storage:** ovnfs ends with 7.6–9.7% more bytes than LayerFS.
- **Import:** ovnfs is 5.6–8.0× faster. LayerFS sends the tree from the Mac to its worker over a loopback connection; ovnfs copies inside its container.
- **Full read:** ovnfs is about 2.0–2.4× faster.
- **Edit step, commit, branch open, no-op route:** these columns are route-bound, as explained above, so none is bolded.

## Limits

- One sample per case, except LayerFS NEW500 and ADD500 (3 each). The two systems ran at different times. ovnfs's L500 ran at host load 14–15, against 7–8 for LayerFS's.
- The routes into each system differ: the LayerFS CLI to its worker, and `docker exec` into ovnfs.
- No cold-cache claim: every phase ran warm, with no cache state enforced.

## Cleanup

Every LayerFS arm released its Store, Sandbox, worker container and volume. The ovnfs arms released theirs in the earlier runs. The 500 MiB base files and campaign homes stay in the local cache.

## Files

- [results/](results/): LayerFS `layerfs-{S1..S4,RM500,DEL500,L500}` and `layerfs-{NEW500,ADD500}.run{1,2,3}`, each with `state.json` and `events.jsonl`.
- [tables.py](tables.py): prints every number above. It reads these results plus ovnfs's from `../rerun-2026-11-07/results` and `../rerun-2026-11-07-v2-speed/results`.
