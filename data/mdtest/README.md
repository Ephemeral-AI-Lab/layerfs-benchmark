# mdtest release data

> **Status:** Current general guide.

One folder per release with mdtest results: IOR's `mdtest` measures
metadata operation rates (create, stat, open/close or rename, remove) from
1 and 4 MPI processes, in a shared folder and in a folder per process, run
through `sandbox.exec` in a LayerFS Workspace (`layerfs`) and in the same
Sandbox's own overlayfs `/tmp` (`sandbox-disk`) as the reference. The
harness is [benchmark/mdtest](../../mdtest/README.md).

## v1.0.0

All 20 mdtest executions exited 0 in both arms; there is no LayerFS-only
failure. Rates are ops/s (mdtest's own `SUMMARY rate`, one iteration).
The ratio is LayerFS ÷ sandbox-disk: 0.10 means LayerFS ran at a tenth of
the container disk's rate; above 1 means LayerFS was faster.

| Case | Phase | layerfs ops/s | sandbox-disk ops/s | Ratio |
| --- | --- | ---: | ---: | ---: |
| files, 1 proc, shared (`-F`, 20,000) | creation / stat / read / removal | 6,395 / 831,980 / 18,731 / 10,134 | 67,215 / 683,128 / 499,887 / 151,006 | 0.095 / 1.22 / 0.037 / 0.067 |
| files, 1 proc, unique (`-F -u`) | creation / stat / read / removal | 6,988 / 778,330 / 10,306 / 5,620 | 59,504 / 636,861 / 425,694 / 116,710 | 0.117 / 1.22 / 0.024 / 0.048 |
| files, 4 procs, shared (`-F`, 4 × 20,000) | creation / stat / read / removal | 3,808 / 826,788 / 46,690 / 4,785 | 74,672 / 1,295,713 / 953,140 / 139,182 | 0.051 / 0.64 / 0.049 / 0.034 |
| files, 4 procs, unique (`-F -u`) | creation / stat / read / removal | 10,157 / 1,574,305 / 54,464 / 11,518 | 205,704 / 1,402,402 / 852,715 / 269,036 | 0.049 / 1.12 / 0.064 / 0.043 |
| dirs, 1 proc, shared (`-D`) | creation / stat / rename / removal | 5,302 / 833,824 / 5,509 / 6,896 | 26,140 / 710,153 / 94,639 / 106,846 | 0.203 / 1.17 / 0.058 / 0.065 |
| dirs, 1 proc, unique (`-D -u`) | creation / stat / rename / removal | 5,179 / 801,725 / 5,072 / 5,862 | 30,776 / 622,203 / 94,098 / 98,992 | 0.168 / 1.29 / 0.054 / 0.059 |
| dirs, 4 procs, shared (`-D`) | creation / stat / rename / removal | 5,795 / 2,782,130 / 5,661 / 5,322 | 19,108 / 1,150,685 / 72,920 / 71,602 | 0.303 / 2.42 / 0.078 / 0.074 |
| dirs, 4 procs, unique (`-D -u`) | creation / stat / rename / removal | 11,720 / 2,667,814 / 12,248 / 11,213 | 46,640 / 1,480,523 / 278,030 / 224,120 | 0.251 / 1.80 / 0.044 / 0.050 |
| tree, 4 procs (`-z 2 -b 4`, 4 × 10,500): dirs | creation / stat / rename / removal | 7,877 / 2,397,104 / 8,070 / 7,627 | 26,152 / 561,123 / 119,022 / 64,634 | 0.301 / 4.27 / 0.068 / 0.118 |
| tree, 4 procs: files | creation / stat / read / removal | 5,777 / 2,357,423 / 59,436 / 8,437 | 60,661 / 626,398 / 434,415 / 117,150 | 0.095 / 3.76 / 0.137 / 0.072 |

The ratios per phase, in plain words:

- **File creation:** LayerFS creates empty files at about a tenth of the
  container disk's rate with one process (0.095–0.12) and about a twentieth
  with four (0.05). Absolute: 3,800–10,200 files/s.
- **File stat:** about the same or faster on LayerFS (0.64–1.22; 3.8 in
  the tree case), because mdtest stats files it has just created and the
  kernel's FUSE attribute cache answers. Warm caches, not a cold-stat rate.
- **File read** (open and close of an empty file): the widest gap, 2–6 %
  of the disk's rate (0.024–0.064; 0.14 in the tree case).
- **File removal:** 3–7 % of the disk's rate (0.034–0.072).
- **Directory creation:** the closest write phase, a fifth to a third of
  the disk's rate (0.17–0.30).
- **Directory stat:** faster on LayerFS (1.2–4.3), the same warm-cache
  reason as file stat.
- **Directory rename:** 4–8 % of the disk's rate (0.044–0.078).
- **Directory removal:** 5–12 % (0.050–0.118).
- **Tree creation and removal** (1–21 test folders per case) take a few
  ms on LayerFS and under mdtest's 1 ms resolution on the disk, so their
  ratios (0.07–0.83 creation, 0.04–0.15 removal) are noise-level; they
  are in `results.csv`.

Four processes in **one shared folder** are slower than one process on
LayerFS for files: creation 6,395 → 3,808 files/s and removal 10,134 →
4,785. With a folder per process (`-u`) four processes do scale (10,157
and 11,518). The container disk does not drop in the shared folder.

**Commit:** after a layerfs-only `mdtest -F -C -n 20000` (20,000 empty
files), one `sandbox.commit` took **3,643.5 ms** (about 182 µs per file):
logical 60 B (only the seed README has bytes), newCanonical 2,238,515 B,
newStored 168,272 B, newMetadata 168,272 B. `mdtest -r` then removed the
files at 5,540 files/s.

## How to read it

- One sample per case and arm (`-i 1`), on a loaded Docker Desktop host
  (1-minute load 10.6–14.1). Speed is indicative. Cache state:
  warm/unknown, not cold.
- `wall_ms` is mdtest's own phase time (`SUMMARY time`, which mdtest
  labels ms/op but prints in seconds with 3 decimals) times 1000, so it
  has 1 ms resolution; short phases read 0–5 ms.
- `load` is the host's 1-minute load at the start of that case's client.

Each folder holds:

| File | What it is |
| --- | --- |
| `results.csv` | One row per case, arm and phase: `case, arm, procs, items_per_proc, unique_dir, phase, ops_per_s, wall_ms, load` (the commit pass's `-C` and `-r` cases appear as `commit-create` and `commit-remove`, layerfs only) |
| `commit.csv` | The one `sandbox.commit` after the create-only pass: files left, time, kind, ids, logical and new bytes, load |
| `environment.csv` | Source, binaries, images, upstream commit, mdtest and MPI build and args, Store, host, load |
| `receipts/` | The run's receipts, unchanged: `identity.txt`, `deploy.env`, `cases.tsv`, `commands.log`, `ledger.jsonl`, `results.jsonl`, `sandbox-identity.txt`, `summary.json` (with the ratios), `cases/*.txt` (mdtest's output per case and arm), and the run's `record.md` |

The CSVs are derived from the receipts by `benchmark/mdtest/report.py`;
everything else is copied unchanged from `benchmark-results/mdtest/`.

## Limits

- One node; MPI ranks share the Sandbox's 8 CPUs. Files are empty
  (`-w 0 -e 0`); no `-N` stride, random stat or shared-file mode.
- `sandbox-disk` is the container's overlayfs, not a raw block device.
- v1.0.0 was measured at `main` `e5c7aaae05` (the fs-bench v1.0.0 build)
  on Docker Desktop on an arm64 Mac, Disposable Store with policy 16/8/8.
