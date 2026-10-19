# fsstress release data

> **Status:** Current general guide.

One folder per release with fsstress results: xfstests' `fsstress`
(xfstests-dev `22348afe338c`) runs random filesystem operations in a LayerFS
Workspace and, as the reference, on the Sandbox container's own disk, through
the public JS SDK; then the tree is committed, forked, mounted again and
compared entry by entry. The harness is
[benchmark/fsstress](../../fsstress/README.md).

| Release | Case | Arm | Procs × ops | Exit | Wall ms | Ops/s | Errors |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| [v1.0.0](v1.0.0/) | c1 (seed 365001) | sandbox-disk | 1 × 10,000 | 0 | 2,453.9 | 4,075.1 | 2,150 |
| | | layerfs | 1 × 10,000 | 0 | 3,824.9 | 2,614.5 | 3,621 |
| | c2 (seed 365002) | sandbox-disk | 4 × 10,000 | 0 | 3,962.4 | 10,094.9 | 8,443 |
| | | layerfs | 4 × 10,000 | 0 | 6,932.0 | 5,770.3 | 14,638 |

| Release | Capture entries | Bytes | Commit | logical | newStored | Manifest equal |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| v1.0.0 | 3,755 | 5,214,397,108 | 4,851.7 ms | 5,214,397,108 | 1,283,524 | yes, 0 differences |

LayerFS-only failures in v1.0.0 (operations, c1 / c2), each reproduced with
a standard tool:

| Gap | layerfs | reference | c1 / c2 |
| --- | --- | --- | ---: |
| user.* extended attributes (set/get/list/remove) | EOPNOTSUPP | supported | 516 / 2,013 |
| fallocate (mode 0, KEEP_SIZE, PUNCH_HOLE, ZERO_RANGE, COLLAPSE/INSERT_RANGE) and XFS RESVSP/UNRESVSP | EOPNOTSUPP | supported | 593 / 2,269 |
| `renameat2(RENAME_EXCHANGE)` | EINVAL | supported | 188 / 764 |
| hard link to a symlink | EPERM | supported | 31 / 128 |
| `FS_IOC_GETFLAGS`, `FS_IOC_FSGETXATTR` (ENOTTY), `FS_IOC_FIEMAP` (EOPNOTSUPP) | fail on every call | supported | 276 / 1,241 |

## How to read it

- **Wall and ops/s** are fsstress alone inside one `sandbox.exec`; ops/s is
  procs × ops ÷ wall. The arms do not do identical work: failed ops return
  early and later ops pick different files, so the wall ratio is indicative.
- **Errors** count every outcome other than success and "no object to act
  on", including root-only (`chown`, `mknod`) and XFS-only (`bulkstat`,
  `exchangerange`) failures that hit both arms.
- **op-errors.csv** has every (case, arm, op, outcome) count, successes
  (`0`) and skips (`skip`) included; `-1` is a raw return code fsstress prints
  for some ioctls. Compare the arms op by op there.
- **Capture** compares path, type, permission bits, size, SHA-256, symlink
  target, nlink and hard-link groups of every entry in the Workspace.
- Not counted against LayerFS: `deduperange` (EOPNOTSUPP on layerfs, but the
  reference deduplicated no bytes either) and failures common to both arms.

## Files

| File | What it is |
| --- | --- |
| `runs.csv` | One row per case and arm: seed, procs, ops, exit, wall_ms, ops_per_s, errors_total |
| `op-errors.csv` | Outcome counts per case, arm and op |
| `capture.csv` | The capture proof: entries, bytes, commit_ms, logical, newStored, manifest_equal, differences |
| `environment.csv` | Source, binaries, images, upstream commit, build, arguments, Store policy, route, host, load |
| `20261019T224258Z/` | The run's receipts, unchanged, and its `record.md`: fsstress logs, manifests, ledgers, `summary.json` |
| `repro-smoke-20261019T225428Z/` | The diagnostic run that reproduced each LayerFS-only failure (`repro.jsonl`) |

The CSVs are derived by `benchmark/fsstress/report.py` from the receipts;
everything else is copied unchanged from `benchmark-results/fsstress/`. The
record's relative links point into `benchmark/fsstress/records/`.

v1.0.0 was measured at `main` `e5c7aaae05` (the fs-bench v1.0.0 build) on
Docker Desktop on an arm64 Mac at 1-minute load 5.9–6.9 during the cases,
one sample per case and arm, Disposable Store with policy 16/8/8. Cache
state warm/unknown, not cold. Diagnostic host, not a qualifying result.
