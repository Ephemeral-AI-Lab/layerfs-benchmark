# Rerun 2026-11-07: LayerFS `751b6b83` vs ovnfs `5d54cb0`

**Run on the same day at the same host load, the latest ovnfs needed 7–10% more space than
the latest LayerFS v2.0.0 for every history (25.7–26.4 MB vs 23.8–24.0 MB), and LayerFS added
11–35× fewer bytes per commit (2.1–3.3 KB vs 29–115 KB). ovnfs read the full tree about 2×
faster (1.6–2.1 s vs 3.7–4.2 s) and imported it about 14× faster. The commit, edit-step and
branch-open timings mostly measure the route into each system, not the system: timed inside
its container, an ovnfs commit took 8–12 ms, against 63–66 ms through the harness's
`docker exec`. This run does not show which system commits faster.** All 15 branch heads
matched the host oracle on both systems. Storage numbers are exact bytes. Timings are warm,
one sample per case, at host load 4–8: diagnostics, not qualified performance claims.

Both systems changed since 2026-11-06 ([../README.md](../README.md)). ovnfs gained
compressed packs and deltas, so its totals fell about 4×. LayerFS (171 commits later) now
checkpoints its WAL when a Store goes idle and stores 22–43% fewer bytes per commit. For how
the two now store data, see [design.md](design.md).

## What changed

**ovnfs** moved from `cdb3fb6b880604ba1c57c28db15304f4c5525ab3` to
`5d54cb0aec474c9aad90f43214ae4ba2bfab1d89` (main, 2026-11-07, 24 commits). The one that
matters here is `cf9fdd6` ("optimized binary storage and delta-based packing"). Per its
`docs/internals.md`:

- objects up to 1 MiB are zstd-compressed into append-only `store/packs/<n>.pack`;
  larger ones stay plain files under `store/objects/`;
- a changed file is stored as a zstd delta against the same path's blob in the parent
  snapshot when the delta is at most half its size (chains under 8);
- after hashing, a layer keeps only a manifest; its source files live in the store;
- captures are stored as compressed binary (`capture.bin`) instead of JSON.

The other 23 commits fix Windows, SMB, submodule and apply behaviour. The CLI calls the
driver uses are unchanged.

**LayerFS** `layerfs_v2_0_0` moved from `b4fa173e401fc87af6610c151225096288e4ba57` to
`751b6b83c4dd2051a112518591442e6c98808ba4` (2026-11-07, 171 commits). Relevant here:

- an idle SQLite Store checkpoints and truncates its WAL (#86), so final probes now show
  `wal_bytes` 0;
- small files get a delta base on rename-over and recreate-at-path (#88);
- read-ahead streams follow the shared cache, not the per-request client (#97);
- Docker Sandboxes now run as namespaces inside the worker container instead of one
  container each, rooted in the bundle's `sandbox-image.tar` (layerfs-project#111 D-8).

The CLI grammar for every command the driver uses is unchanged.

## Configuration

| | LayerFS | ovnfs |
| --- | --- | --- |
| Version | `layerfs_v2_0_0` @ `751b6b83c4dd2051a112518591442e6c98808ba4` | `stencil-hq/ovnfs` @ `5d54cb0aec474c9aad90f43214ae4ba2bfab1d89` (`v0.2.0`) |
| Build | release macOS CLI (`layerfs-cli`, default features), sha256 `94be23f9…3daa`; Linux bundle sealed from the same worktree with `tools/linux_bundle.py`, seal `8f8029b7…dd01`, source sha256 `d5edd698…`, toolchain 1.85.1 | `CGO_ENABLED=0 go build`, go1.27.3 linux/arm64, binary sha256 `1baff81c…0f59` ([../harness/ovnfs.Dockerfile](../harness/ovnfs.Dockerfile)) |
| Where it ran | public CLI on macOS → Docker machine: worker container with Sandboxes as namespaces inside it | daemon + FUSE in one container per case (`fsh-cmp-ovnfs:5d54cb0`, `sha256:9321fb04…1540`) |
| Sandbox / container image | the bundle's `sandbox-image.tar`, saved from `fsh-cmp-layerfs:b4fa173e` (`sha256:fd23ab06…`: the runtime image `afa1ef9c…` plus the suite's `model.py`), the same image the 11-06 Sandboxes used | runtime image `afa1ef9c…` plus fuse3, ovnfs and `model.py` |
| Persistence | SQLite Store, Disposable profile, on the worker's Docker volume; `LAYERFS_CONSTRUCTION_WORKERS=1` | state directory on an ext4 Docker volume (no reflinks) |
| Limits | none set | none set (Docker VM: 8 CPUs, 8 GB) |
| Host 1-minute load | 4.3–8.1 | 5.6–7.7 |
| Ran | 15:01–15:03 (+08) | 14:38–14:42 (+08) |

Workload, cases and operation mapping are unchanged from 11-06: label
`fsh-ovnfs-compare-v0`, the fs-storage-history base (DSH checkpoint 157, 9,415 paths,
65,020,822 B), `fsh-edit-model-v1`, the same seeds, and cases S1 (1 branch × 40 commits),
S2 (5 branches × 3), S3 (fork chain 4 deep × 3) and S4 (5 branches × the same 1 commit).
Each arm ran S4, S1, S2, S3 with one unit per command, no retries and no failed units.
The driver is [compare.py](compare.py). It differs from
[../harness/compare.py](../harness/compare.py) only in the two arms' constants (new worker
volume and ovnfs image) and in listing `store/packs`, `store/objects` and `nodes.log` in
the ovnfs probe; totals are computed as before.

## Results: storage (bytes)

LayerFS: `store status` file + WAL (equal to allocated bytes on the volume). ovnfs: `du -B1`
of the state directory after the daemon stopped (apparent size in brackets).

| Case | LayerFS 751b6b83 final | ovnfs 5d54cb0 final | ovnfs ÷ LayerFS | LayerFS 11-06 final (main file) | ovnfs 11-06 final |
| --- | ---: | ---: | ---: | ---: | ---: |
| S1 | **23,982,080** | 26,374,144 (26,215,385) | 1.10× | 28,753,400 (24,629,248) | 109,776,896 |
| S2 | **23,810,048** | 26,177,536 (26,067,792) | 1.10× | 26,821,936 (24,489,984) | 112,631,808 |
| S3 | **23,867,392** | 25,653,248 (25,576,058) | 1.07× | 26,467,880 (24,444,928) | 106,479,616 |
| S4 | **23,797,760** | 25,706,496 (25,632,795) | 1.08× | 25,104,232 (24,432,640) | 109,277,184 |

LayerFS's final WAL was 0 in every case. After importing the 65.0 MB base tree: LayerFS
751b6b83 23.75–23.79 MB, ovnfs 5d54cb0 25.09 MB (5.5% more). On 11-06 they were
24.41–24.49 MB and 98.17 MB.

History cost (logical bytes added after import):

| Case | Commits | LayerFS 751b6b83 Σ `new_stored` (metadata) | per commit | ovnfs 5d54cb0 apparent growth | per commit | ovnfs ÷ LayerFS | LayerFS 11-06 per commit | ovnfs 11-06 per commit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S1 | 40 | 108,879 (67,994) | **2,722** | 1,158,436 | 28,961 | 10.6× | 3,598 | 211,856 |
| S2 | 15 | 31,743 (19,696) | **2,116** | 1,010,808 | 67,387 | 31.8× | 2,810 | 884,738 |
| S3 | 12 | 32,939 (20,395) | **2,745** | 519,081 | 43,257 | 15.8× | 3,504 | 612,384 |
| S4 | 5 | 16,306 (15,956) | **3,261** | 575,364 | 115,073 | 35.3× | 5,679 | 2,193,641 |

LayerFS's Store file grew by 208,896 (S1), 61,440 (S2), 77,824 (S3) and 24,576 (S4)
allocated bytes; SQLite grows in 4 KiB pages and reuses free ones.

Where ovnfs's growth went (allocated bytes added after import):

| Case | `store/packs` | per commit | `bases/` | `layers/` | `nodes.log` | `uppers/` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| S1 | 995,328 | 24,883 | 81,920 | 163,840 | 28,672 | 8,192 |
| S2 | 454,656 | 30,310 | 409,600 | 61,440 | 118,784 | 40,960 |
| S3 | 303,104 | 25,259 | 81,920 | 49,152 | 94,208 | 32,768 |
| S4 | 32,768 | 6,554 | 409,600 | 20,480 | 114,688 | 40,960 |

`store/objects` held 1,052,672 B in every case: the tree's one file over 1 MiB, stored
plain and never rewritten.

## Results: speed (ms, warm diagnostic)

Today's two runs first, then 11-06 for reference (taken at load 13–27).

| Case | Run | Commit median (p90) | Edit step median (p90) | Open branch, median | Import | Full read per branch |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| S1 | LayerFS 751b6b83 | **20** (24) | 97 (104) | **29** | 5,107 | 3,792 |
| S1 | ovnfs 5d54cb0 | 66 (75) | **82** (95) | 119 | **353** | **2,087** |
| S2 | LayerFS 751b6b83 | **19** (22) | 97 (107) | **33** | 5,034 | 3,896 · 3,719 · 3,774 · 3,815 · 3,804 |
| S2 | ovnfs 5d54cb0 | 66 (73) | **81** (86) | 128 | **393** | **1,812 · 1,943 · 1,830 · 1,757 · 1,910** |
| S3 | LayerFS 751b6b83 | **21** (26) | 94 (108) | **34** | 4,984 | 4,065 · 3,780 · 3,765 · 3,970 |
| S3 | ovnfs 5d54cb0 | 66 (72) | **80** (92) | 83 (`fork`) | **370** | **1,667 · 1,623 · 1,780 · 1,869** |
| S4 | LayerFS 751b6b83 | **28** (30) | 112 (114) | **35** | 5,956 | 4,232 · 4,048 · 3,768 · 3,971 · 3,775 |
| S4 | ovnfs 5d54cb0 | 63 (71) | **86** (112) | 139 | **393** | **1,734 · 1,833 · 1,893 · 1,688 · 1,783** |
| S1–S4 | LayerFS 11-06 | 27–51 | 93–142 | 55–97 | 5,527–10,070 | 6,629–24,519 |
| S1–S4 | ovnfs 11-06 | 131–212 | 130–183 | 142–458 | 393–660 | 4,123–15,799 |

Control overhead (a no-op command through the same route, one call per case): LayerFS
`workspace exec ws true` 22–37 ms; ovnfs `docker exec … true` 51–64 ms.

**Correction (2026-11-07, after publication):** every ovnfs timing above includes one
`docker exec` from the Mac into its container, which costs about 50–100 ms by itself. LayerFS
timings include its own CLI start and worker round trip, a different and cheaper route. The
first version of this report read the commit and branch-open columns as LayerFS being
2.3–4.4× faster; the diagnostic below shows that gap is mostly the route. The import and
full-read gaps are far larger than one `docker exec` and stand.

## Observations

- **Storage: LayerFS is ahead again, by less.** ovnfs's packs took its starting tree from
  98.2 MB to 25.1 MB, and LayerFS's tree is 23.8 MB, so the old 3.8–4.4× gap is now
  7–10%. On 11-06 LayerFS's totals also carried 0.7–4.1 MB of SQLite WAL; with the idle
  checkpoint (#86) that is gone.
- **Per commit, the gap stays large.** LayerFS adds 2.1–3.3 KB per commit; ovnfs's packs
  alone grow about 25–30 KB per changed-file commit, plus layer manifests, `nodes.log`
  entries and 4 KiB file blocks. Both delta-encode now; [design.md](design.md) explains
  why the gap remains (git trees rewritten whole along each changed path, delta base only
  the same path). LayerFS's own per-commit cost fell 22–43% since 11-06.
- **Branches.** A LayerFS branch is metadata only: S4's five branches and five identical
  commits cost 16,306 B. Each `ovnfs new` adds about 82 KB in `bases/` and about 24 KB of
  `nodes.log` (about 115 KB per checkout, down from 2.1 MB). Identical content is shared
  in both.
- **Commit: no ranking from this run.** Measured end to end, LayerFS took 19–28 ms and
  ovnfs 63–66 ms, but inside its container `ovnfs snap --wait` took 8–12 ms (diagnostic
  below); the rest was `docker exec`. LayerFS's 19–28 ms also includes starting the CLI and
  a worker round trip, and its in-worker commit time was not measured. A fair comparison
  needs both timed through equal routes.
- **Branch open and edit step: also route-bound.** Opening a branch took 29–35 ms on
  LayerFS and 83–139 ms on ovnfs, and the edit step 94–112 ms vs 80–86 ms; each ovnfs figure
  includes one `docker exec`. Inside the container, ovnfs applied the same 5 edits in
  27–37 ms. ovnfs's in-container branch open and LayerFS's in-Sandbox edit time were not
  measured.
- **Full-tree read: ovnfs, about 2×.** LayerFS's reads improved from 6.6–24.5 s to
  3.7–4.2 s and no longer warm up across sibling branches (S4 on 11-06: 24.5 s falling to
  9.4 s; today flat at 3.8–4.2 s). The read walks 9,415 files one at a time, and LayerFS
  fetches each file's content in its own Store read (no prefetch across a directory). That
  is about 0.4 ms per file vs about 0.2 ms for ovnfs and 0.04 ms on plain ext4. How much of
  the improvement is code (#97) and how much is the lower host load is not separable from
  these runs.
- **Import: ovnfs, about 14×, but the routes differ.** LayerFS's `project init` reads the
  base from the macOS host through the CLI and encodes it into the Store (5.0–6.0 s);
  ovnfs captures a copy already inside its container (0.35–0.39 s), and copying it in with
  `docker cp` is not counted.

## Diagnostic: ovnfs timed inside its container

Run after publication to split the route from ovnfs's own work: a fresh throwaway container
(`fsh-cmp-ovnfs:5d54cb0`, base copied in, `ovnfs new` for `main` and `b01`), the first 15
steps of S1, timed with a Python loop inside the container (host load 5.6). Not a sample of
the benchmark; container and volume were removed afterwards.

| Call | Where timed | Calls | ms |
| --- | --- | ---: | --- |
| `docker exec <ctr> true` | from the Mac | 5 | 61.9–100.3 |
| `true` | inside | 5 | 0.4–0.6 |
| `ovnfs version` (CLI start) | inside | 5 | 2.5–3.2 |
| `ovnfs snap b01 --wait` | inside | 10 | 8.4–12.2 (median 9.9) |
| `ovnfs snap b01` (no wait) | inside | 5 | 6.1–8.4 |
| `model.py apply` (5 edits) | inside | 15 | 26.9–37.3 (median 30.5) |

`snap --wait` flushes the memory tier, writes a durable intent, renames the upper into a
layer, writes `state.json` again and waits for the background hash
(`checkout/operations.go:703-1060`).

## Limits

- The two arms are reached through different routes: ovnfs through `docker exec` (about
  50–100 ms per call), LayerFS through its CLI and worker. Small operations (commit, edit,
  branch open) are dominated by that route, so their cross-system ratios are not
  meaningful here.
- One sample per case and arm, warm caches, run a few minutes apart in one session at
  similar load (LayerFS 4.3–8.1, ovnfs 5.6–7.7). Other sessions' containers shared the
  Docker engine. No cold-cache claim; every timing is an INELIGIBLE diagnostic.
- The control routes differ (LayerFS CLI to its worker; ovnfs `docker exec`); the no-op
  controls above size that overhead, and it is not subtracted in the tables.
- LayerFS's Sandbox image comes from its sealed bundle. It was sealed with the suite's image
  (runtime + `model.py`), not the plain runtime image, so the bundle seal differs from a
  standard build of this commit; the binaries are the commit's own.
- LayerFS per-branch storage probes need a quiesced Store, so LayerFS has probes at floor,
  import and final, plus per-commit `new_stored`.
- ovnfs converts a hashed layer to a manifest after a 200 ms pause or at daemon stop; the
  final probe runs after `ovnfs stop`. ovnfs ran on ext4 without reflinks. Durability
  differs: ovnfs syncs store objects only when a pack is sealed or rewritten; LayerFS ran
  the Disposable profile.
- Comparisons with 11-06 mix code changes with a 2–3× higher host load then.
- Not covered: PostgreSQL Stores, long histories, large files, ovnfs on macOS.

## Superseded attempt (kept)

- `results/layerfs-S4.attempt1-fork-overlap`: during its `open` unit (import and Sandbox
  create, host load about 24), another session ran a throwaway Store's init, push and
  remove on the same worker. That attempt was closed, its Store removed, and S4 was rerun
  fresh. Its import probe was 23,724,032 B.

## Cleanup

- ovnfs: each `close` unit stopped the daemon and removed its container and volume
  (`fsh-cmp-ov-s1`…`s4`).
- LayerFS: the driver removed every Store (`store remove`); the Docker machine was stopped;
  its container `lfs-84acbcdb-docker` and volume `lfs-84acbcdb-docker-data` were removed,
  and so was the untagged worker image Docker loaded from the bundle (`9460a2c5…`). No
  `fsh-cmp` or `lfs-84acbcdb` containers or volumes remain.
- Kept: images `fsh-cmp-ovnfs:5d54cb0` and `fsh-cmp-layerfs:b4fa173e`; the LayerFS build
  worktree `layerfs-ovnfs-cmp` (detached at `751b6b83`) with its registration and Linux
  target/cargo volumes (`lfs-dev-layerfs-ovnfs-cmp-83def82407ae-target`, `-cargo`, about
  0.9 GB); the local campaign directories `~/.cache/fsh-ovnfs-cmp2` (ovnfs) and
  `~/.cache/fsh-ovnfs-cmp3` (LayerFS CLI and sealed bundle, 2.6 GB).

## Files

```
rerun-2026-11-07/
  report.md                  this report
  design.md                  storage and overlay design, ovnfs 5d54cb0 vs LayerFS 751b6b83
  compare.py                 the driver as run for both arms
  compare_past.py            tabulates this rerun next to ../results/ (11-06)
  snap_diag.py               the in-container ovnfs timing diagnostic
  results/
    summary-vs-past.json     per case: LayerFS and ovnfs, 11-06 and 11-07
    layerfs-<case>/, ovnfs-<case>/   state.json, events.jsonl
    layerfs-S4.attempt1-fork-overlap/
```
