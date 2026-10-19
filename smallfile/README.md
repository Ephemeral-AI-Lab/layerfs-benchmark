# smallfile

> **Status:** Current general guide.

Small-file operation throughput: distributed-system-analysis/smallfile
drives many 4 KiB files through one operation at a time (create, read,
append, stat, chmod, rename, delete-renamed, mkdir, rmdir) with several
threads and reports files/s, MiB/s and the elapsed time it measured. One of
the [#365](https://github.com/Ephemeral-AI-Lab/layerfs/issues/365) suites;
it uses the shared harness in [benchmark/common](../common/README.md).

## Route and arms

Everything goes through the public JavaScript SDK. smallfile itself runs
only through `sandbox.exec`, as uid 501 in the suite's Sandbox image.

```text
setup     project.init(seed folder) → sandbox.create → branch.fork("bench", "main") → sandbox.mount
          exec: smallfile identity, kernel, both arms' filesystems; mkdir both top folders
next      per operation and arm: exec smallfile_cli.py (measured) → exec read-back (untimed)
          after the layerfs create: sandbox.commit of the Workspace, in its own client (timed)
teardown  sandbox.unmount (terminal) → sandbox.close; volumes removed
```

| Arm | smallfile `--top` | Filesystem |
| --- | --- | --- |
| `layerfs` | `<mounted Workspace>/sf` | LayerFS FUSE mount |
| `sandbox-disk` | `/tmp/sf` | the Sandbox container's overlayfs (reference) |

Plan order: `create` layerfs, `commit`, `create` sandbox-disk, then for
`read`, `append`, `stat`, `chmod`, `rename`, `delete-renamed`, `mkdir` and
`rmdir`: layerfs, then sandbox-disk. Each operation is its own
`smallfile_cli.py --operation <op>` over the same top folder, so each one
works on the files the previous one left. smallfile's output, its
`--output-json` result and its per-thread logs (`TMPDIR`) go to
`/tmp/sf-out/<arm>/<op>/` in both arms, outside the measured folder.

## Parameters

Every operation in both arms:

```text
python3 /opt/smallfile/smallfile_cli.py --top <top> --operation <op> --threads 4 \
  --files <FILES> --file-size 4 --stonewall N --finish Y --output-json <out>/result.json
```

`--stonewall N --finish Y` make every thread process all of its files, so
`pctFilesDone` is 100 and the next operation finds the complete set. The
rest are smallfile's defaults: 100 files per directory, 10 directories per
directory, record size = file size, no fsync, `--verify-read Y`, fixed
size, compressible data. `FILES` is fixed per run in `RUN/params.env` and
`identity.txt`; v1.0.0 uses 25,000 per thread (100,000 files, 390.6 MiB),
chosen from the smoke runs so the slowest LayerFS exec stays well under
100 s.

## Files

| Path | Role |
| --- | --- |
| `run.sh` | One step per command: `image`, `setup`, `start`, `next`, `teardown`, `report` |
| `sandbox/Dockerfile` | `FROM fs-bench-computer:gawk-20261020`; python3-yaml from bookworm; smallfile at `aa2519de5bf0b3b383db2c31eacbf8ac4328e19c` in `/opt/smallfile`; `/opt/smallfile-identity.txt` |
| `client/common.mjs` | Each arm's top folder, the output folder, the smallfile command |
| `client/setup.mjs` | Init, create, fork, mount (`common/session.mjs`); identity probe; both top folders |
| `client/op.mjs` | One operation in one arm: the measured smallfile exec and the read-back exec |
| `client/commit.mjs` | The one `sandbox.commit` after the layerfs create |
| `client/teardown.mjs` | Unmount and close |
| `report.py` | `results.csv`, `commit.csv` and `summary.json` from the receipts |
| `records/` | One record per measured run |

## Running

```bash
B=benchmark/smallfile
$B/run.sh image                               # once per image change
RUN=$PWD/benchmark-results/smallfile/$(date -u +%Y%m%dT%H%M%SZ)
$B/run.sh setup $RUN 25000 measured           # exit 75: lock held; wait, then $B/run.sh start $RUN measured
$B/run.sh next $RUN                           # one plan step per command; repeat until DONE
$B/run.sh teardown $RUN                       # unmount, close, volumes, lock
$B/run.sh report $RUN
```

A smoke run uses `benchmark-results/smallfile/smoke-<id>`, a small `FILES`
(1000) and `smoke` (no lock).

## Receipts

`RUN/results.jsonl` (one row per operation and arm: smallfile's exit, the
in-Sandbox wall time around smallfile alone, the Sandbox's `/proc/loadavg`,
the exec's client-side time), `RUN/ops/<op>-<arm>.txt` (smallfile's output,
its JSON result, and after a failure its per-thread log tails),
`ledger.jsonl` (setup, probe, Commit, teardown), `params.env`,
`sandbox-identity.txt`, `identity.txt`, `deploy.env`, `commands.log` (the
host's 1-minute load per client) and each step's `.out` / `.err`.

## Reading the result

- **result:** `PASS` is smallfile exit 0, status `Success` and 100 % of
  files processed; `FAIL` is anything else from smallfile; `HARNESS` means
  the exec itself failed.
- **files_per_s, mb_per_s, elapsed_s, pct_files_done** are smallfile's own
  (`filesPerSec`, `MiBps`, `elapsed`, `pctFilesDone`). `elapsed` runs from
  smallfile's starting gate to the last thread's finish; `mb_per_s` is MiB/s
  and exists only for the data operations (create, read, append).
- **wall_ms** is `date +%s%N` around the whole `smallfile_cli.py` process
  inside the Sandbox, so exec overhead is excluded but smallfile's own
  start-up (about 3.6 s of Python start, directory setup and gate polling in
  the smoke runs) is included. Compare arms on files/s.
- **load** is the host's 1-minute load when the operation's client started.
  One sample per operation and arm on a shared host; treat speed as
  indicative. Cache state: warm/unknown, not cold.
- The Commit after the layerfs create also changes what the layerfs `read`
  reads: the created files are in the committed base afterwards, not the
  Workspace's overlay.

## Known limits

- smallfile's multi-host mode, response-time statistics (numpy/scipy),
  xattr, symlink, overwrite, truncate, readdir and ls-l operations are not
  run.
- The two arms share one Sandbox and run one after the other, not
  concurrently.
- `sandbox-disk` is overlayfs in the container, not a raw block device.
