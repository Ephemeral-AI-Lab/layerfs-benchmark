# Large-file, small-edit cases: ovnfs vs LayerFS (`fsh-ovnfs-largefile-v0`)

**On small edits to large incompressible files, LayerFS added 1–11 KB per commit while
ovnfs stored a full copy of the file every time. After 10 one-hundred-byte edits to a
100 MiB file, ovnfs held 1.15 GB and LayerFS 106.3 MB. Per commit that is 105 MB against
4.3 KB, about 24,000×; for 10 MiB files it is about 2,500×.** Appends to a 5 MiB file
cost both systems about 17 KB (the appended bytes) until ovnfs hit its delta-chain cap
and stored full copies, which left it 36× behind. All 8 case runs matched the oracle.
Timings are warm, single-sample diagnostics, and each ovnfs call includes one `docker exec`
(50–100 ms, see [the rerun's diagnostic](../rerun-2026-11-07/report.md)). Net of that
route, ovnfs's snapshots of the 10 and 100 MiB files still took longer than LayerFS's whole
Commit (12–16 ms end to end), but no clean ratio follows.

## What was run

| | ovnfs | LayerFS |
| --- | --- | --- |
| Version | `stencil-hq/ovnfs` @ `5d54cb0aec474c9aad90f43214ae4ba2bfab1d89` | `layerfs_v2_0_0` @ `751b6b83c4dd2051a112518591442e6c98808ba4`; CLI sha256 `94be23f9…3daa`, Linux bundle seal `8f8029b7…dd01` (Sandbox image `fsh-cmp-layerfs:b4fa173e`) |
| Where | daemon + FUSE in one container (`fsh-cmp-ovnfs:5d54cb0`), state on an ext4 Docker volume, no reflinks | public CLI on macOS → Docker machine worker (namespaces Sandbox), SQLite Store, Disposable profile, `LAYERFS_CONSTRUCTION_WORKERS=1` |
| Driver | [lf_ovnfs.py](lf_ovnfs.py) | [lf_layerfs.py](lf_layerfs.py) |
| Import | starting file generated inside the container, `ovnfs new --rule 'source *'` | starting file generated on the host, `project init` |
| Branch | `ovnfs new --name b01` | `branch fork` + `workspace mount` |
| Edit | `largefile.py apply` in the checkout (`docker exec`) | `workspace exec ws "python3 -c <largefile.py> apply …"` (the Sandbox image lacks the script, so it is passed inline; the tree holds only the case file) |
| Commit | `ovnfs snap b01 --wait` | `workspace commit ws` |
| Storage | `du -B1` of the state directory after each step and after `ovnfs stop` | `new_stored` per Commit, and `store status` file + WAL at import and after the Sandbox closed |
| Verify | `new --from <last snapshot>` + sha256 | fresh `workspace mount` + sha256 |

Workload: [largefile.py](largefile.py), one seeded pseudo-random (incompressible) file per
case. Host oracle `largefile.py expect`, checked first in a throwaway container: 64/64
step hashes equal. One unit per command, each call bounded at 110 s, no retries, one
sample. Host 1-minute load: ovnfs 3.7–13.8 (15:07), LayerFS 6.9–9.8 (15:12–15:14).

| Case | File | Commits | Edit per commit |
| --- | --- | ---: | --- |
| L10 | 10 MiB | 20 | overwrite 100 B in place at a seeded offset |
| L100 | 100 MiB | 10 | overwrite 100 B in place at a seeded offset |
| I10 | 10 MiB | 10 | insert 100 B at a seeded offset (shifts the rest) |
| A5 | 5 MiB | 20 | append 16 KiB |

## Results: storage (bytes)

ovnfs growth is allocated bytes from the probe after the branch opened to the final probe.
LayerFS growth is Σ `new_stored` over its Commits; the Store file grew by the page-rounded
amount shown in brackets. The WAL was 0 at both LayerFS probes.

| Case | Bytes changed | ovnfs growth | per commit | LayerFS Σ `new_stored` (file growth) | per commit | ovnfs ÷ LayerFS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| L10 | 2,000 | 209,801,216 | 10,490,061 | 76,928 (110,592) | 3,846 | 2,727× |
| L100 | 1,000 | 1,048,621,056 | 104,862,106 | 43,407 (53,248) | 4,341 | 24,158× |
| I10 | 1,000 | 104,939,520 | 10,493,952 | 42,048 (57,344) | 4,205 | 2,496× |
| A5 | 327,680 | 12,238,848 | 611,942 | 341,649 (368,640) | 17,082 | 36× |

| Case | ovnfs after import | ovnfs final | LayerFS after import | LayerFS final | final ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| L10 | 11,640,832 | 221,462,528 | 10,825,728 | 10,936,320 | 20.3× |
| L100 | 106,012,672 | 1,154,654,208 | 106,250,240 | 106,303,488 | 10.9× |
| I10 | 11,640,832 | 116,600,832 | 10,825,728 | 10,883,072 | 10.7× |
| A5 | 6,397,952 | 18,657,280 | 5,521,408 | 5,890,048 | 3.2× |

ovnfs's import includes about 1.1 MB of daemon state present before the import; the data
is incompressible, so neither system compresses it.

- **Where LayerFS's bytes went.** In L10, L100 and I10, `new_metadata` was 96–97% of
  `new_stored`: 73,868 of 76,928 B in L10. The content change itself costs about 150 B per
  edit; the rest is the per-Commit metadata pages.
- **Range per commit.** LayerFS ranged 939–10,726 B. In A5 every Commit was
  17,003–17,772 B: the 16 KiB of incompressible appended data plus about 640 B of metadata.
- **ovnfs full copies.** Per step, ovnfs stored a full uncompressed copy at every L10,
  L100 and I10 version. In A5 it stored deltas of 17 KB, then 148 KB once the file passed
  about 5.2 MiB, and full copies at steps 9 and 18 when the delta chain reached depth 8.

## Results: speed (ms, warm diagnostic)

| Case | ovnfs commit (`snap --wait`) median | LayerFS commit median | ovnfs edit step median | LayerFS edit step median | ovnfs import | LayerFS import | ovnfs full read | LayerFS full read |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L10 | 175 | 13 | 92 | 82 | 86 | 604 | 96 | 144 |
| L100 | 239 | 16 | 186 | 96 | 272 | 6,024 | 355 | 686 |
| I10 | 170 | 13 | 93 | 109 | 90 | 597 | 95 | 109 |
| A5 | 129 | 12 | 86 | 95 | 86 | 341 | 119 | 140 |

Every column measures the route as well as the system. Each ovnfs call includes one
`docker exec` from the Mac into its container. The [rerun's diagnostic](../rerun-2026-11-07/report.md)
measured that at 62–100 ms, and an in-container `ovnfs snap --wait` on the small-file tree
at 8–12 ms. Each LayerFS call includes starting the CLI and a worker round trip. No no-op
control was recorded in these runs.

- **Commit.** Subtracting 62–100 ms leaves ovnfs about 70–110 ms for L10/I10, 30–70 ms for
  A5 and 140–180 ms for L100, against LayerFS's 12–16 ms end to end. ovnfs re-reads and
  hashes the whole changed file at each snapshot, which grows with file size. LayerFS is
  likely faster on these cases, but the margin is not measured cleanly.
- **Edit step and full read.** These are within the route overhead of each other, so there
  is no ranking.
- **Import.** The routes differ. LayerFS's `project init` reads the file from the macOS host
  into the Store; ovnfs captures a file already inside its container, and generating it
  there is not timed.

### Diagnostic: where ovnfs deltas stop

A labeled diagnostic, not a case ([diag_delta_size.sh](diag_delta_size.sh)). It ran in one
ovnfs container, with one 100-byte overwrite and one snapshot per file.

| File | ovnfs stored for one 100-byte edit |
| --- | --- |
| random 2 / 3 / 4 MiB | 680 / 792 / 904 B, delta |
| random 5 MiB | 132,077 B, delta |
| random 6 MiB | 918,555 B, delta |
| random 8 / 12 MiB | full copy |
| 10 MiB text (repetitive words + hex) | 3,527 B, delta |

## Why

**ovnfs** (`store/delta.go`, `store/store.go` at `5d54cb0`):

1. A snapshot stores an edited file with `PutFileLike` against the blob at the same path in
   the parent snapshot (`checkout/hash.go:375`). The delta is zstd with the old version as a
   raw dictionary, through `klauspost/compress` v1.20.3.
2. A delta of a file over 1 MiB is kept only if it is at most 1 MiB and at most half the
   file. Otherwise the file is stored whole and uncompressed in `store/objects/`
   (`store/delta.go:174`).
3. On incompressible content over about 4 MiB, the encoder misses most matches in the
   dictionary, so the delta of a 100-byte edit comes out as large as the file. The code
   switches large bases to the better matcher so that "a small edit to a 3 MiB file" stays
   small (`store/delta.go:44-46`), but nothing covers sizes between that and the 16 MiB
   delta limit. This looks like the matcher's tables running out (inferred; the encoder
   internals were not traced). Compressible text keeps its matches.
4. When the base's chain is 8 deltas deep, the next version is stored whole
   (`deltaDepth = 8`, `store/delta.go:17,118`). Files over 16 MiB never get a delta
   (`deltaMax`, `store/delta.go:14,121`).
5. On ext4 a whole copy is a real copy. On btrfs, XFS or APFS, `PutFile` reflinks it
   (`store/store.go:424-425`), so disk use would be closer to the changed blocks; a snapshot
   still reads and hashes the whole file.

**LayerFS** (`751b6b83`): files of 128 KiB and up are split into content-defined chunks
(8/16/32 KiB min/target/max, `core/crates/layerfs-content/src/file/cdc/gear.rs`).

- **Overwrite or insert.** A 100-byte edit changes about one chunk; an insert also shifts
  bytes, but the boundaries resynchronise. The changed chunk is stored as a zstd-prefix
  delta against the old chunk, and unchanged chunks are shared by id.
- **Chain cap.** Deltas rebase onto the chain's full root at the depth cap rather than
  storing the file again.
- **Copy-up.** The Workspace overlay keeps unchanged ranges as references, so an edit
  copies nothing up.
- **What's left.** The per-Commit metadata pages (about 1–10 KB here) dominate.

## Limits

- One sample per case and arm, warm, taken minutes apart. Timings are INELIGIBLE
  diagnostics, and each arm's route (`docker exec` vs the LayerFS CLI and worker) is part
  of every timing.
- Incompressible content is the worst case for ovnfs's delta matcher and the neutral case
  for compression. Compressible large files (text, logs, CSV) do better on ovnfs, as the
  diagnostic shows.
- ovnfs ran on ext4 without reflinks. On btrfs, XFS or APFS its full copies would share
  unchanged blocks on disk.
- ovnfs per-step probes can include a layer not yet collapsed into a manifest. The final
  probe runs after `ovnfs stop`, and the loose-object counts don't depend on that.
- LayerFS reports per-Commit `new_stored`. Its Store file is probed only at import and
  after the Sandbox closed.

## Cleanup

- **ovnfs:** each case's `close` stopped the daemon and removed its container and volume
  (`fsh-lf-ov-l10`, `-l100`, `-i10`, `-a5`). The diagnostic's `fsh-lf-ov-diag` was removed.
- **LayerFS:** each case's `close` closed its Sandbox and removed its Store (`lf-<case>`).
  Then `layerfs machine stop docker`, `docker rm lfs-be8321b8-docker` and
  `docker volume rm lfs-be8321b8-docker-data`. `store list` and `sandbox list` were empty.
- **Kept:** image `fsh-cmp-ovnfs:5d54cb0`, and local campaign directories
  `~/.cache/fsh-ovnfs-lf` and `~/.cache/fsh-lf-layerfs` (CLI, bundle clone, starting files,
  raw results).

## Files

```
largefile-2026-11-07/
  report.md               this report
  largefile.py            the workload (gen / apply / expect / sha)
  lf_ovnfs.py             the ovnfs driver
  lf_layerfs.py           the LayerFS driver
  diag_delta_size.sh      the ovnfs delta-size diagnostic
  results/<arm>-<case>/   state.json, events.jsonl
```
