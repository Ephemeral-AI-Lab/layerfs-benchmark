# fio release data

> **Status:** Current general guide.

One folder per release with fio results: fio 3.33 (Debian bookworm) runs
nine data I/O jobs, each its own invocation, through `sandbox.exec` in a
LayerFS Workspace (`layerfs`) and in the same Sandbox's own overlayfs
`/tmp` (`sandbox-disk`) as the reference. The harness is
[benchmark/fio](../../fio/README.md).

## v1.0.0

[v1.0.0](v1.0.0/): 20 s per job (`--time_based`, `--ramp_time=0`), `psync`
at iodepth 1, files laid out before the timed jobs: seq 1 GiB, rand
512 MiB, sync 64 MiB. Ratio is LayerFS bandwidth ÷ sandbox-disk bandwidth:
1.0 is the same speed, below 1.0 is slower on LayerFS, above 1.0 faster.

| Job | layerfs MB/s | sandbox-disk MB/s | layerfs IOPS | sandbox-disk IOPS | Ratio | In plain words |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| seq-write (1 MiB, end fsync) | 140.29 | 2,332.05 | 134 | 2,224 | 0.060 | LayerFS writes at about 1/17 the speed |
| seq-read (1 MiB) | 239.59 | 4,374.07 | 228 | 4,171 | 0.055 | LayerFS reads at about 1/18 the speed |
| rand-write (4 KiB) | 4.30 | 1,570.37 | 1,051 | 383,392 | 0.003 | LayerFS does about 1/365 as many writes |
| rand-read (4 KiB) | 2.54 | 11.19 | 619 | 2,733 | 0.227 | LayerFS does about 1/4.4 as many reads |
| rand-read-4j (4 KiB, 4 jobs) | 1.43 | 38.98 | 349 | 9,517 | 0.037 | LayerFS does about 1/27 as many reads |
| randrw-70-30 read | 2.98 | 4.74 | 727 | 1,156 | 0.629 | LayerFS does about 1/1.6 as many reads |
| randrw-70-30 write | 1.31 | 2.06 | 319 | 503 | 0.636 | LayerFS does about 1/1.6 as many writes |
| sync-write (4 KiB, fsync each) | 21.70 | 0.78 | 5,298 | 190 | 27.821 | LayerFS is 27.8× faster, because its fsync does not flush (see below) |
| rand-write-direct (4 KiB, O_DIRECT) | 1.85 | 20.03 | 451 | 4,890 | 0.092 | LayerFS does about 1/11 as many writes |
| rand-read-direct (4 KiB, O_DIRECT) | 40.06 | 40.04 | 9,781 | 9,774 | 1.000 | the same speed |

Completion latency p50 / p99 (µs), layerfs vs sandbox-disk: seq-write
4,489 / 39,584 vs 230 / 5,866; seq-read 2,769 / 34,341 vs 206 / 1,028;
rand-write 346 / 7,111 vs 1.5 / 6.8; rand-read 643 / 9,634 vs 161 / 3,228;
rand-read-4j 4,424 / 106,431 vs 134 / 3,752; sync-write 101 / 1,384 vs
14 / 149 (plus fsync p50 1.0 µs vs 3,719 µs); rand-write-direct 1,286 /
12,386 vs 157 / 1,417; rand-read-direct 72 / 913 vs 40 / 395.

**v1.0.0 in one line:** all 18 runs passed (fio exit 0, `error` 0,
`O_DIRECT` included) with no LayerFS-only failure. LayerFS was slower than
the container's overlayfs in every buffered data job, from 1.6× (mixed
70/30 random) to about 365× (4 KiB buffered random writes, 1,051 vs
383,392 IOPS); about 17–18× on 1 MiB sequential write and read. It matched
overlayfs on O_DIRECT random reads and was 27.8× faster on 4 KiB writes
with an fsync after each, only because a Disposable Workspace's fsync does
no disk flush. One `sandbox.commit` of the three data files (1.68 GB
logical, 1.50 GB newly stored) took 26,423.3 ms.

## How to read it

- `bw_mb_s` is decimal MB/s (fio's `bw_bytes` / 10^6). IOPS, runtime and
  bytes are fio's per direction; clat percentiles are fio's completion
  latency in µs. `randrw-70-30` has a read row and a write row.
- `sync-write` IOPS counts write+fsync pairs; `sync_p50_us` and
  `sync_p99_us` are fio's fsync latency. The Store profile is Disposable,
  whose Workspace backing is never fsynced, so the `layerfs` fsync returns
  in about 1 µs while `sandbox-disk` flushes the VM disk (about 3.7 ms).
  This row and the end fsync of `seq-write` are not durability-equivalent.
- `cache_state`: the Sandbox cannot drop caches. Buffered jobs read and
  write files their arm wrote minutes earlier: **warm own-write**, never
  cold. Residency was not checked, and it was not complete: both arms'
  files (3.2 GiB) plus LayerFS's overlay backing exceeded what stayed
  resident in the Sandbox's 5.2 GB available memory on a host running other
  containers, and the buffered 4 KiB read latencies (p50 134–643 µs) show
  most of those reads missed the page cache in both arms (going to
  the VM disk, or on `layerfs` to the daemon). O_DIRECT
  rows bypass the page cache; below it is warm/unknown.
- `load` is the host's 1-minute load when the job's client started
  (7.8–35.6 during the jobs). One sample per job and arm on a heavily
  loaded Docker Desktop host. Indicative only.

Each folder holds:

| File | What it is |
| --- | --- |
| `results.csv` | One row per job, arm and direction: `job, arm, rw, bs, numjobs, direct, sync, runtime_s, size, bw_mb_s, iops, clat_p50_us, clat_p99_us, clat_p999_us, cache_state, load`, then `ddir, bytes, clat_mean_us, sync_p50_us, sync_p99_us, ioengine, result, fio_error, exit, wall_ms` (in-Sandbox wall around fio), `exec_ms` (the exec's client-side time) and `sandbox_loadavg` (the Sandbox's `/proc/loadavg` at start) |
| `commit.csv` | The one `sandbox.commit` after the layerfs jobs: time, load, kind, ids, logical and new bytes |
| `environment.csv` | Source, binaries, images, fio version and args, files, layout, Store, host, load |
| `receipts/` | The run's receipts, unchanged: `identity.txt`, `deploy.env`, `params.env`, `commands.log`, `ledger.jsonl`, `results.jsonl`, `layout.jsonl`, `sandbox-identity.txt`, `summary.json`, `ops/*.txt` (fio's log and JSON per job and arm, each arm's layout output), and the run's `record.md` |

The CSVs are derived from the receipts by `benchmark/fio/report.py`;
everything else is copied unchanged from `benchmark-results/fio/`.

## Limits

- `psync` at iodepth 1 only: no libaio/io_uring queue depth, no mmap
  engine, no `fallocate` (LayerFS refuses it), no verify pass.
- Nothing here is a cold-read figure, and full residency was not reached,
  so the buffered read rows mix page-cache hits and lower-level reads in
  proportions the run did not measure.
- fio's buffers are pseudo-random, so the Commit's stored bytes are close
  to logical: a fair storage case for incompressible data.
- `sandbox-disk` is the container's overlayfs on the Docker Desktop VM
  disk, not a raw block device; both arms share one Sandbox and run one
  after the other.
- v1.0.0 was measured at `main` `e5c7aaae05` (the fs-bench v1.0.0 build)
  on Docker Desktop on an arm64 Mac, Disposable Store with policy 16/8/8.
