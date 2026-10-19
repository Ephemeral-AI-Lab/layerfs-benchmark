# smallfile release data

> **Status:** Current general guide.

One folder per release with smallfile results: distributed-system-analysis
smallfile runs one operation at a time over many 4 KiB files with 4
threads, through `sandbox.exec` in a LayerFS Workspace (`layerfs`) and in
the same Sandbox's own overlayfs `/tmp` (`sandbox-disk`) as the reference.
The harness is [benchmark/smallfile](../../smallfile/README.md).

## v1.0.0

[v1.0.0](v1.0.0/): 4 threads × 25,000 files × 4 KiB = 100,000 files per
arm. files/s is smallfile's own figure. Ratio is LayerFS files/s ÷
sandbox-disk files/s: 1.0 would be the same speed, below 1.0 is slower on
LayerFS.

| Operation | layerfs files/s | sandbox-disk files/s | Ratio | LayerFS takes |
| --- | ---: | ---: | ---: | --- |
| create | 6,394 | 171,026 | 0.037 | 26.7× as long |
| read | 40,835 | 356,019 | 0.115 | 8.7× as long |
| append | 10,387 | 317,168 | 0.033 | 30.5× as long |
| stat | 51,150 | 946,583 | 0.054 | 18.5× as long |
| chmod | 40,326 | 625,310 | 0.064 | 15.5× as long |
| rename | 5,620 | 111,491 | 0.050 | 19.8× as long |
| delete-renamed | 7,762 | 230,063 | 0.034 | 29.6× as long |
| mkdir | 11,584 | 51,075 | 0.227 | 4.4× as long |
| rmdir | 12,938 | 69,543 | 0.186 | 5.4× as long |

**v1.0.0 in one line:** all 18 runs passed (smallfile exit 0, status
`Success`, 100 % of files processed) with no LayerFS-only failure, and
LayerFS was slower than the container's overlayfs in every operation, by
4.4× (mkdir) to 30.5× (append). The data-writing and namespace-changing
operations (create, append, rename, delete-renamed) are the slowest on
LayerFS at about 5,600–10,400 files/s; stat, chmod and
read run at about 40,000–51,000 files/s. One `sandbox.commit` of the
100,000 created files took 10,721.1 ms (about 107 µs per file).

## How to read it

- files/s, MiB/s, elapsed and `pct_files_done` are smallfile's own
  `--output-json` figures. Its elapsed time runs from its starting gate to
  the last thread's finish.
- `wall_ms` is `date +%s%N` around the whole `smallfile_cli.py` process
  inside the Sandbox. It excludes the `sandbox.exec` overhead but includes
  about 3.6 s of smallfile start-up per run, so the wall-time ratio
  understates the difference; use files/s to compare arms.
- `PASS` means smallfile exit 0, status `Success` and 100 % of files
  processed (`--stonewall N --finish Y` make every thread finish its files).
- Several `sandbox-disk` operations took only 0.1–0.6 s of smallfile time,
  so their files/s carry more timing noise than the LayerFS figures.
- The layerfs `read` ran after the Commit, so it read files from the
  committed base rather than the Workspace overlay.
- One sample per operation and arm on a loaded Docker Desktop host
  (1-minute load 6.6–10.3 during the operations). Indicative only. Cache
  state: warm/unknown, not cold.

Each folder holds:

| File | What it is |
| --- | --- |
| `results.csv` | One row per operation and arm: `op, arm, threads, files_per_thread, file_size_kb, files_per_s, mb_per_s, elapsed_s, pct_files_done, wall_ms, load`, then `result, status, files, exit, exec_ms` (the exec's client-side time) and `sandbox_loadavg` (the Sandbox's `/proc/loadavg` at start). `load` is the host's 1-minute load when the client started; `mb_per_s` is MiB/s and exists only for create, read and append |
| `commit.csv` | The one `sandbox.commit` after the layerfs create: files, time, load, kind, ids, logical and new bytes |
| `environment.csv` | Source, binaries, images, upstream commit, smallfile args, Store, host, load |
| `receipts/` | The run's receipts, unchanged: `identity.txt`, `deploy.env`, `params.env`, `commands.log`, `ledger.jsonl`, `results.jsonl`, `sandbox-identity.txt`, `summary.json`, `ops/*.txt` (smallfile's output and JSON result per operation and arm), and the run's `record.md` |

The CSVs are derived from the receipts by `benchmark/smallfile/report.py`;
everything else is copied unchanged from `benchmark-results/smallfile/`.

## Limits

- Only create, read, append, stat, chmod, rename, delete-renamed, mkdir and
  rmdir were run; smallfile's xattr, symlink, overwrite, truncate, readdir
  and ls-l operations and its multi-host mode were not.
- smallfile's default file content is highly repetitive, so the Commit's
  stored bytes (973,607 B for 409,600,076 logical) are not a storage result.
- `sandbox-disk` is the container's overlayfs on the Docker Desktop VM
  disk, not a raw block device; both arms share one Sandbox and run one
  after the other.
- v1.0.0 was measured at `main` `e5c7aaae05` (the fs-bench v1.0.0 build)
  on Docker Desktop on an arm64 Mac, Disposable Store with policy 16/8/8.
