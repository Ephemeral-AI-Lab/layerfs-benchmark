# mdtest

> **Status:** Current general guide.

Metadata operation rates: IOR's `mdtest` creates, stats, reads (opens and
closes) and removes files, or creates, stats, renames and removes
directories, from one or several MPI processes, and prints each phase's
rate and time. One of the
[#365](https://github.com/Ephemeral-AI-Lab/layerfs/issues/365) suites; it
uses the shared harness in [benchmark/common](../common/README.md).

## Route and arms

Everything goes through the public JavaScript SDK. mdtest itself runs only
through `sandbox.exec`, as uid 501 in the suite's Sandbox image.

```text
setup     project.init(seed folder) → sandbox.create → branch.fork("bench", "main") → sandbox.mount
          exec: mdtest and MPI identity, kernel, both arms' filesystems; mkdir both md folders
next      per case and arm: one exec of mpirun … mdtest (measured by mdtest), its output printed back
commit    layerfs only: exec mdtest -C (create only) → sandbox.commit (timed, own client) → exec mdtest -r
teardown  sandbox.unmount (terminal) → sandbox.close; volumes removed; lock released
```

| Arm | Folder | Filesystem |
| --- | --- | --- |
| `layerfs` | `<mounted Workspace>/md/<case>/` | LayerFS FUSE mount |
| `sandbox-disk` | `/tmp/md/<case>/` | the Sandbox container's overlayfs (reference) |

Both arms run the same command in the same Sandbox, one after the other.
A measured run takes the measurement lock right after `bench_setup`,
before the setup client mounts the Workspace, so no measured op runs
without it and no Workspace waits for it.

## Cases

Every case runs
`mpirun --oversubscribe --bind-to none -np <procs> mdtest -P -i 1 -n <items> <args> -d <arm base>/<case>`.
`-n` is items per process; `-P` prints both the rate and the time table;
`-i 1` is one iteration (one sample). `-w` and `-e` stay 0, so files are
empty and the file read phase is an open and close.

| Case | Procs | Items per proc | Args | Phases |
| --- | ---: | ---: | --- | --- |
| `files-1p-shared` | 1 | 20,000 | `-F` | file creation, stat, read, removal; tree creation, removal |
| `files-1p-unique` | 1 | 20,000 | `-F -u` | same, one working folder per process |
| `files-4p-shared` | 4 | 20,000 | `-F` | same, four processes in one folder |
| `files-4p-unique` | 4 | 20,000 | `-F -u` | same, a folder per process |
| `dirs-1p-shared` … `dirs-4p-unique` | 1 / 4 | 20,000 | `-D` (`-u`) | directory creation, stat, rename, removal; tree creation, removal |
| `tree-4p-shared` | 4 | 10,500 | `-z 2 -b 4` | files and directories over a depth-2, branch-4 tree (21 folders, 500 items each per process) |
| `commit` row | 1 | 20,000 | `-F` | the commit pass: `-C`, then `sandbox.commit`, then `-r` (layerfs only) |

Item counts come from the smoke run: 4 × 20,000 in one shared folder took
about 35 s on `layerfs`, the longest exec, well under the 115 s alarm.

MPI is Debian bookworm's Open MPI 4.1.4. As uid 501 in the Sandbox,
`--oversubscribe` (and `--bind-to none`, to leave CPU placement to the
container) is all `mpirun` needs; it starts local ranks without ssh.

## Files

| Path | Role |
| --- | --- |
| `run.sh` | One step per command: `image`, `setup`, `start`, `next`, `commit`, `teardown`, `report` |
| `cases.tsv` | Measured plan (case, procs, items per process, mdtest args); the `commit` row sets the commit pass |
| `cases-smoke.tsv` | Smoke plan (200 items per process) |
| `sandbox/Dockerfile` | `FROM fs-bench-computer:gawk-20261020`; Open MPI from bookworm; hpc/ior at `f1172addabada77d13cf37773d1ffdb202b4fc4a`, `./bootstrap`, `./configure`, `make -j2`; `/usr/local/bin/mdtest` and `/opt/mdtest-identity.txt` |
| `client/setup.mjs` | Init, create, fork, mount (`common/session.mjs`); identity probe; both arms' folders |
| `client/case.mjs` | One case in one arm: the mdtest exec, its output kept |
| `client/commit.mjs` | The `sandbox.commit` between the `-C` and `-r` passes |
| `client/teardown.mjs` | Unmount and close |
| `report.py` | `results.csv`, `commit.csv` and `summary.json` (with layerfs ÷ sandbox-disk ratios) from the receipts |
| `records/` | One record per measured run |

## Running

```bash
B=benchmark/mdtest
$B/run.sh image                               # once per image change
RUN=$PWD/benchmark-results/mdtest/$(date -u +%Y%m%dT%H%M%SZ)
$B/run.sh setup $RUN $B/cases.tsv measured    # exit 75: lock held; wait, then $B/run.sh start $RUN measured
$B/run.sh next $RUN                           # one case and arm per command; repeat until DONE
$B/run.sh commit $RUN                         # mdtest -C, sandbox.commit, mdtest -r
$B/run.sh teardown $RUN                       # unmount, close, volumes, lock
$B/run.sh report $RUN
```

A smoke run uses `benchmark-results/mdtest/smoke-<id>`, `cases-smoke.tsv`
and `smoke` (no lock).

## Receipts

`RUN/results.jsonl` (one row per case and arm: the mpirun command,
mdtest's exit, the in-Sandbox wall time around mpirun, the Sandbox's
1-minute load, the exec's client-side time), `RUN/cases/<case>-<arm>.txt`
(mdtest's whole output), `ledger.jsonl` (setup, probe, Commit, teardown),
`sandbox-identity.txt`, `identity.txt`, `deploy.env`, `cases.tsv`,
`commands.log` (host 1-minute load per client), and each step's
`.out` / `.err`.

## Reading the result

- **ops_per_s** is the Mean column of mdtest's `SUMMARY rate` table; with
  `-i 1` it is the one sample. **wall_ms** is the `SUMMARY time` table
  times 1000: mdtest labels that table `ms/op` but prints each phase's
  seconds with 3 decimals, so wall_ms has 1 ms resolution and very short
  phases (stat, tree creation and removal) read 0–5 ms.
- **load** is the host's 1-minute load at the client's start
  (`commands.log`). One sample per case and arm on a loaded Docker Desktop
  host; speed is indicative.
- mdtest stats what it has just created, so stat rates come from warm
  caches (the FUSE attribute cache on `layerfs`). Cache state:
  warm/unknown, not cold.

## Known limits

- One node; MPI ranks share the Sandbox's 8 CPUs. No `-N` stride, random
  stat (`-R`), shared-file (`-S`) or written/read bytes (`-w`, `-e`).
- The two arms share one Sandbox and run sequentially, not concurrently.
- `sandbox-disk` is overlayfs in the container, not a raw block device.
