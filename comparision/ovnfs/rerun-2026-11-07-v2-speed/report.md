# Rerun 2026-11-07 (evening): LayerFS v2 with the exec and import speed work vs ovnfs `5d54cb0`

**With the exec and import speed work merged (`layerfs_v2_0_0` @ `c421d9db`, PR #610),
LayerFS imported the 65 MB starting tree 2.3–2.5× faster than v2 earlier the same day
(2.2–3.1 s vs 5.2–7.8 s). ovnfs still imported 6–8× faster (0.35–0.39 s). LayerFS's edit step
fell from 99–114 ms to 59–71 ms. On a 500 MiB file, LayerFS's import fell from 32.1 s to
5.0 s. Its commits took 18–33 ms against ovnfs's 0.77–1.14 s, and it stored 3–8 KB per
commit where ovnfs stored a full 525 MB copy. Cutting 500 MiB from a 1000 MiB file took
LayerFS a 22 ms commit and 8 KB, against 1.1 s and a 500 MiB copy on ovnfs. Appending 500 MiB
took LayerFS 6.9 s to commit, 5× slower than ovnfs, though it stored half as much. Creating a
brand-new 500 MiB file took LayerFS a 3.9 s commit against ovnfs's 0.84 s (both stored it
once); removing one was cheap on both (11 ms vs 75 ms, the latter mostly route). ovnfs read
files 2–6× faster.** Every branch
head matched its oracle on both systems: S1–S4, 15 heads per arm, and the 500 MiB file's
final SHA-256. Storage numbers are exact bytes. Timings are warm, with one sample per case,
at host load 4–8 (the earlier 500 MiB runs at 14–23). They are diagnostics, not qualified
performance claims.

The small-history edit, commit and branch-open timings mostly measure the route into each
system, as [the morning rerun](../rerun-2026-11-07/report.md) showed. Timed inside its
container, ovnfs applied an edit step in about 30 ms (median 30.5) and committed in 8–12 ms,
against 80–86 ms and 63–66 ms through `docker exec`. So the S1–S4 rows show LayerFS getting
faster, but they don't show which system edits or commits faster. The 500 MiB commit gap is
far larger than one `docker exec` (~50–100 ms), so it stands.

## What changed in LayerFS

`layerfs_v2_0_0` moved from `aa131e3946` (the "v2 before" arm) to
`c421d9dbafc7aa88597373449954c0cf63a6fd73`, merging
[PR #610](https://github.com/Ephemeral-AI-Lab/layerfs/pull/610) (+781 production LOC):

- **Image file times.** A namespaces Sandbox's root keeps each file's modification time when
  its image is unpacked. Python's cached bytecode then validates instead of recompiling.
  This is most of the edit-step gain: the step runs `python3 model.py apply`, and its
  imports took 63.8 ms before, 26.6 ms after.
- **Worker frames.** Bytes now travel raw next to the JSON instead of base64 (worker
  protocol 2 → 3), with a faster codec for what stays JSON.
- **Overlapped upload.** `project init` into a worker's Store sends up to 4 stage parts
  at once instead of one after another.
- **Init queue.** The queue from the chunking thread to the storing thread holds 32 batches
  (8 MiB) instead of 4. The storing thread no longer sits idle waiting for the next
  batch of chunks.
- **`LAYERFS_TRACE_STEP`.** Times each step of a worker call. It was off in these runs
  except for the 500 MiB LayerFS arms, which the harness traces.

ovnfs is unchanged. Its S1–S4 numbers are from [the morning rerun](../rerun-2026-11-07/report.md)
(14:38–14:42, load 5.6–7.7). Its 500 MiB numbers are from a run at 17:49 the same day
(load 14–15).

## Configuration

| | LayerFS merged | LayerFS before | ovnfs |
| --- | --- | --- | --- |
| Version | `c421d9db` (bundle built from `8482633f`, the same tree `585c02cc`) | `aa131e39` (500 MiB: `f6916c64`, before the import work) | `stencil-hq/ovnfs` @ `5d54cb0` |
| Build | release macOS CLI sha256 `ba600052…a522`; Linux bundle seal `a2e31861…2ab0`, toolchain 1.85.1 | release, built the same way | as in the morning rerun |
| Where it ran | public CLI on macOS → Docker machine: worker container, Sandboxes as namespaces in it | same | daemon + FUSE in one container per case |
| Sandbox image | bundle `sandbox-image.tar` saved from `fsh-cmp-layerfs:b4fa173e` (`sha256:fd23ab06…`) | same | `fsh-cmp-ovnfs:5d54cb0` |
| Persistence | SQLite Store, Disposable, on the worker's Docker volume; `LAYERFS_CONSTRUCTION_WORKERS=1` | same | state directory on an ext4 Docker volume |
| Ran (+08) | S1–S4 19:15–19:18, 500 MiB 19:18 | S1–S4 ~17:39, 500 MiB ~17:47 | S1–S4 14:38–14:42, 500 MiB ~17:49 |
| Host 1-minute load | 4.9–8.2 | S1–S4 5.5–6.5; 500 MiB 21–23 | S1–S4 5.6–7.7; 500 MiB 14–15 |

S1–S4 use the morning's driver ([../rerun-2026-11-07/compare.py](../rerun-2026-11-07/compare.py))
and the same cases, workload and operation mapping. The 500 MiB case (`L500`) uses
[harness/](harness/):
- a 500 MiB random file is imported as the base;
- then 5 commits each overwrite 100 bytes;
- then the whole file is read back and its SHA-256 checked.

ovnfs's container has no room to generate the file, so `lf_ovnfs.py` copies the
host-generated file into its volume first (`copy_base`, timed apart from the import).

## Small histories: S1–S4

Medians in ms; storage in bytes. Before = `aa131e39`, merged = `c421d9db`.

| Case | Arm | Heads | Import | Edit step | Commit | Branch open | No-op route | Full read | Stored after import | Stored at end |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S1 | ovnfs | 1/1 | 353 | 82 | 66 | 119 | 52 | 2087 | 25,088,000 | 26,374,144 |
| | LayerFS before | 1/1 | 5363 | 102 | 20 | 29 | 32 | 4233 | 23,797,760 | 24,014,848 |
| | LayerFS merged | 1/1 | **2261** | **59** | 21 | 29 | 30 | 3722 | 23,719,936 | 23,937,024 |
| S2 | ovnfs | 5/5 | 393 | 81 | 66 | 128 | 51 | 1757–1943 | 25,088,000 | 26,177,536 |
| | LayerFS before | 5/5 | 5550 | 108 | 20 | 35 | 26 | 3885–4611 | 23,793,664 | 23,855,104 |
| | LayerFS merged | 5/5 | **2335** | **62** | 21 | 42 | 29 | 3619–3929 | 23,785,472 | 23,846,912 |
| S3 | ovnfs | 4/4 | 370 | 80 | 66 | 83 | 53 | 1623–1869 | 25,088,000 | 25,653,248 |
| | LayerFS before | 4/4 | 5200 | 99 | 20 | 36 | 22 | 3480–3822 | 23,724,032 | 23,801,856 |
| | LayerFS merged | 4/4 | **2223** | **60** | 21 | 40 | 26 | 3726–4153 | 23,773,184 | 23,842,816 |
| S4 | ovnfs | 5/5 | 393 | 86 | 63 | 139 | 64 | 1688–1893 | 25,088,000 | 25,706,496 |
| | LayerFS before | 5/5 | 7800 | 114 | 31 | 37 | 46 | 3814–5328 | 23,748,608 | 23,773,184 |
| | LayerFS merged | 5/5 | **3117** | **71** | 30 | 41 | 35 | 3657–4047 | 23,728,128 | 23,752,704 |

- **Import:** 2.3–2.5× faster than before. ovnfs is still 6–8× faster. LayerFS's import
  sends the tree from the Mac to the worker over its loopback connection. Then a
  single storing thread chunks, hashes and writes it to SQLite. ovnfs copies inside its
  container.
- **Edit step:** 39–46 ms faster. The step runs `python3 model.py apply` in the Sandbox,
  and its imports no longer recompile bytecode. Inside its container ovnfs's step takes
  about 30 ms. LayerFS's 59–71 ms includes starting the CLI and a worker round trip
  (no-op 26–35 ms), so the cross-system ratio is route-bound.
- **Commit and branch open:** unchanged (the work didn't target them). Both are
  route-bound across systems, as above.
- **Storage:** unchanged. Byte differences of a few KB between runs come from the random
  workload's names and timestamps. ovnfs ends with 8–10% more bytes than LayerFS.
- **Full read:** unchanged within noise. ovnfs is about 2× faster.

## One 500 MiB file: L500

| | ovnfs | LayerFS before (`f6916c64`) | LayerFS merged |
| --- | ---: | ---: | ---: |
| Base into the system | copy into volume 5,369 ms + import 1,179 ms | import 32,052 ms | import **4,986 ms** |
| Overwrite 100 bytes (apply), ms | 407–805 | 52–62 | 50–64 |
| Commit, ms | 770–1,140 | 16–27 | 18–33 |
| Stored per commit | +524 MB (a full copy each) | 3,057–7,915 B | 3,057–7,915 B |
| Stored at end | 3,146,948,608 B | 530,423,808 B | 530,448,384 B |
| Read whole file, ms | 660 | 3,094 | 4,027 |
| Final SHA-256 | PASS | PASS | PASS |
| Host load | 14–15 | 21–23 | 5–6 |

- **Import:** 6.4× faster than before. Traced on the same build, the 5.0 s splits into
  about 2.9 s of upload and 1.8 s of the worker building the Store.
  - The upload's overlapped parts move about 180–250 MB/s in total. Each part's work in the
    worker takes ~3.5 ms, so the limit looks like Docker Desktop's port forward.
  - ovnfs's import, from a file already in its volume, took 1.2 s.
  - Getting the file into ovnfs's volume first took 5.4 s here, through `docker cp`, a
    harness choice.
- **Commit:** about 35× faster than ovnfs (medians 26 vs 950 ms), which copies the whole file each commit. LayerFS
  stores only the changed chunks. The merged run's commits were 2–13 ms slower than the
  earlier run's, from one sample each. This wasn't investigated: neither change touches
  commit.
- **Read:** ovnfs is 4.7–6.1× faster. The merged run read 0.9 s slower than the earlier
  one, again from one sample, and no change touched reads.

## Add and remove 500 MiB of a file: ADD500, DEL500

Two one-commit cases on the same bytes, run 19:25–19:28 at host load 4.5–5.8, both systems
back to back:
- **ADD500:** starts from the L500 file (500 MiB) and appends 500 MiB of new random bytes,
  so the file becomes 1000 MiB.
- **DEL500:** starts from exactly that 1000 MiB file and cuts the last 500 MiB, so the file
  is back to the L500 file.

The appended bytes come from a seeded generator in 1 MiB blocks
([harness/largefile.py](harness/largefile.py)). Both systems' final SHA-256 matched the
oracle in both cases.

| | ADD500 ovnfs | ADD500 LayerFS | DEL500 ovnfs | DEL500 LayerFS |
| --- | ---: | ---: | ---: | ---: |
| Base into the system, ms | copy 5,281 + import 1,088 | import 4,939 | copy 10,251 + import 1,989 | import 9,680 |
| Edit (append / truncate), ms | 1,767 | 1,914 | 716 | 112 |
| Commit, ms | **1,351** | 6,873 | 1,141 | **22** |
| Bytes the commit added to storage | 1,048,604,672 (a full 1000 MiB copy) | **530,214,912** (the new 500 MiB) | 524,316,672 (a full 500 MiB copy) | **8,192** |
| Stored at end | 1,574,051,840 | **1,060,585,472** | 1,574,051,840 | **1,060,646,912** |
| Read the whole final file, ms | 1,233 (1000 MiB) | 7,577 (1000 MiB) | 579 (500 MiB) | 3,113 (500 MiB) |

- **Remove 500 MiB:** LayerFS commits in 22 ms and stores 8 KB. Its new version reuses the
  chunks it already has, minus the cut tail. ovnfs takes 1.1 s and stores a full copy of the
  remaining 500 MiB.
- **Add 500 MiB:** LayerFS stores only the new 500 MiB, half of what ovnfs adds. But its
  commit is **5× slower** (6.9 s vs 1.35 s), about 76 MB/s. The trace puts all of it inside the
  Sandbox daemon's commit: the worker's routing is about 1 ms. That is much slower than
  LayerFS's own import of 500 MiB (5.0 s, of which 1.8 s builds the Store). The daemon's
  commit path has not been profiled yet.
- **Stored at end:** about 1.06 GB on LayerFS against 1.57 GB on ovnfs in both cases.
  Both still hold the starting version. ovnfs adds a whole copy of the file each commit;
  LayerFS adds only new chunks.

## Create and remove a 500 MiB file: NEW500, RM500

Two separate one-commit tests, run 19:32–19:33 at host load 5.2–8.6, both systems back to
back:
- **NEW500:** the tree holds one 1 MiB file (`keep.bin`); the commit creates a brand-new
  500 MiB file (`big.bin`).
- **RM500:** the tree holds `keep.bin` and an existing 500 MiB `big.bin`; the commit
  removes `big.bin`.

`big.bin` has the same bytes in both tests: 500 MiB from the seeded 1 MiB-block generator.
Verification compares every file in the final tree (name, size, SHA-256) against the
oracle. All four passed.

| | NEW500 ovnfs | NEW500 LayerFS | RM500 ovnfs | RM500 LayerFS |
| --- | ---: | ---: | ---: | ---: |
| Starting tree into the system, ms | copy 36 + import 81 | import 137 | copy 5,038 + import 1,061 | import 5,128 |
| Edit (write / delete the file), ms | 1,669 | 2,136 | 88 | 48 |
| Commit, ms | **841** | 3,928 | 75 | 11 |
| Bytes the commit added to storage | 524,316,672 | 530,247,680 | 24,576 | 0 (290 B of metadata, within free pages) |
| Stored at end | 526,520,320 | 531,521,536 | 526,520,320 | 531,521,536 |
| Read the final tree, ms | 576 | 2,626 | 82 | 48 |

- **Create:** both systems store the new 500 MiB once, about 525–530 MB. LayerFS's commit
  is **4.7× slower** (3.9 s vs 0.84 s). As in ADD500, the time is inside the Sandbox daemon's
  commit. Creating a new file (3.9 s) is faster than appending to an existing one (6.9 s),
  so part of the append cost seems tied to the existing file.
- **Remove:** both are cheap and store almost nothing; neither copies the remaining tree.
  LayerFS commits in 11 ms, ovnfs in 75 ms. ovnfs's figure includes its ~50–100 ms
  `docker exec` route, so this doesn't show which system removes faster.
- **Storage:** after the remove, both still hold `big.bin` in history, so the totals
  don't fall. LayerFS ends about 1% larger than ovnfs here.
- The grow/shrink pair above (ADD500/DEL500) is a different test: it changes the size of
  one existing file instead of creating or removing one.

## Observations

- The speed work helped where it aimed: imports and the Python edit step. Commit,
  branch open, storage and reads stayed where they were.
- A commit that adds a lot of new data is now LayerFS's slowest path: 3.9 s to commit a new
  500 MiB file and 6.9 s to commit 500 MiB appended to one, against 0.84 s and 1.35 s for
  ovnfs. The time is inside the Sandbox daemon's commit.
- ovnfs still leads on import (6–8× on 65 MB, ~4× on 500 MiB when its copy-in is left out)
  and on reading whole files (2–6×).
- What's left in LayerFS's import, from a profile of the storing thread before the queue
  change: SQLite writes ~0.86 s, two SHA-256 passes over each pack ~0.6 s, the zstd probe
  ~0.12 s. The upload needs a path that doesn't go through the port forward.

## Limits

- One sample per case. The arms ran at different times and host loads (above). ovnfs
  was not rerun with the merged LayerFS.
- The routes into each system differ: the LayerFS CLI to its worker, and `docker exec`
  into ovnfs. Edit, commit and branch-open ratios across systems on S1–S4 are route-bound.
- No cold-cache claim: every phase ran warm, with no cache state enforced.

## Cleanup

Every LayerFS arm released its Store, Sandbox, worker container and volume at the end.
The ovnfs arms released their containers and volumes. The two failed ovnfs L500 attempts
were cleaned up by hand: the file was too large to generate in its container, and a shell
quoting slip broke the second. The 500 MiB base file and the campaign homes stay in the
local cache.

## Files

- [results/](results/): `layerfs-{S1..S4,L500,ADD500,DEL500,NEW500,RM500}` (merged),
  `layerfs-before-{S1..S4,L500}` and `ovnfs-{L500,ADD500,DEL500,NEW500,RM500}`, each with
  `state.json` and `events.jsonl`.
- [tables.py](tables.py) prints every number above from `results/` and
  `../rerun-2026-11-07/results/ovnfs-*`.
- [harness/](harness/): `largefile.py`, `lf_layerfs.py` and `lf_ovnfs.py` for L500, ADD500,
  DEL500, NEW500 and RM500.
