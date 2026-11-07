# fs-bench-pro — cold project export from each machine into a host folder
> group: filesystem · measures: speed, correctness

## Basic info

| | |
| --- | --- |
| Tool | In-house: Python standard library in [src/](src/), plus a small static C tool for cold-cache control in [tools/](tools/); every LayerFS step uses the public CLI |
| Product | LayerFS 2.0 with `project.export` ([layerfs-project#53](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/53)), pinned per campaign |
| Machines | macOS host: native, Docker, Lima, Apple Container |
| Store backends | SQLite (Disposable) |
| Families | `export` (E01, E02); more families are added as their own case groups |
| Status | Current general guide. New suite (2026-11-08); the earlier fs-bench-pro is archived in `.archive/` and stays frozen |
| Frozen rules | [AGENTS.md](AGENTS.md) (cases, cold control, verdicts, cleanup); root [CLI and cache rules](../AGENTS.md) |

Agents must read the root [CLI and cache rules](../AGENTS.md) and the
[suite instructions](AGENTS.md) before preparing or running selections.

The suite root holds documentation and the configuration example. Python
implementation lives in `src/`, focused checks in `tests/`, and the guest
cache tool's source in `tools/`. [cases.py](src/cases.py) pins the cases and
the expected trees.

## Overview

fs-bench-pro measures one product operation per family from a declared,
enforced cold state, with an independent content check. The `export` family
times `layerfs project export <store>/<project> <host folder> --progress`:
the Store lives on one machine and the exported tree must land, complete and
exact, in a fresh folder on the macOS host.

| Case | Work | Fixture |
| --- | --- | --- |
| E01 | Export 10,000 small files (46.5 MB), 50 symlinks, 132 folders | `small` |
| E02 | Export one 256 MiB file and a README | `large` |

Fixtures come from [fixture.py](src/fixture.py): deterministic, incompressible
and distinct per file, so chunk dedupe saves nothing. Their manifest hashes
(path, kind, mode, size, content hash or link target, mtime) are pinned in
[cases.py](src/cases.py).

One `run` is one sample of one case on one machine:

1. **Cold control (untimed).** Guests: `resident --evict` syncs and drops the
   Store's own files from the guest page cache, then `resident` counts the
   pages still resident (mincore). Native: the home lives on an owned APFS disk
   image, which is detached and re-attached; mincore then counts the Store's
   resident pages. Any resident page, or a failed control, makes the row
   INELIGIBLE.
2. **Timed export.** One CLI process; each progress line is stamped as it
   arrives. The export wall time is the case time.
3. **Verification (untimed).** The CLI's counts must match the fixture, and the
   manifest of the exported folder must equal the pinned hash. No staging
   folder may be left behind.
4. **Release.** The exported folder is removed; the receipt is written to
   `results/<run-id>/receipt.json` (ignored, local).

Verdicts: **QUALIFIED** (execution and verification PASS, cold shown, export
within budget), **OVER_BUDGET**, **INELIGIBLE** (cold not shown) or **FAIL**.

## Setup

### Prerequisites

- A LayerFS CLI and Linux bundle built from one clean source snapshot, with
  `project export` (`<cli> help project export`).
- Ready machines for the guests you select, created through the CLI
  (`layerfs machine …`), each with its own SQLite Store.
- An owned APFS sparse disk image mounted where the private `LAYERFS_HOME`
  lives, so native cold control never touches a shared volume:

  ```bash
  hdiutil create -size 20g -type SPARSE -fs APFS -volname lfs-bench native.sparseimage
  hdiutil attach -nobrowse -mountpoint vol native.sparseimage
  ```

- The guest tool, built once for the guests' architecture:

  ```bash
  docker run --rm -v "$PWD/tools:/w" -w /w gcc gcc -O2 -static -o resident-linux-aarch64 resident.c
  ```

- The fixtures: `python3 src/fixture.py <fixtures>/small small` and
  `python3 src/fixture.py <fixtures>/large large`; each prints its manifest,
  which must equal the pinned one.

### Config file

Copy [environments.example.json](environments.example.json) to
`environments.local.json` (ignored) and fill in absolute paths, the guest exec
prefixes and the campaign's identities. `XDG_CACHE_HOME` points at a private
cache so the bundle never mixes with another session's.

### One selection

```bash
python3 src/run.py setup --env environments.local.json
python3 src/run.py run --env environments.local.json --case E01 --machine lima
python3 src/report.py <run-id>...
python3 src/run.py cleanup --env environments.local.json
```

`setup` creates one Store per machine with both fixtures, pushes guest Stores
and installs the guest tool. `cleanup` removes those Stores; machines, the disk
image and fixtures are released by the caller.

### Time limits

The timed export has the 15 s default budget; verification has 10 s. No case
has a declared exception. The cold control's cost (up to 12 s for a disk-image
detach) is enforcement overhead, recorded as `cold.control_s` and never case
time.

### Focused checks

```bash
python3 -m unittest discover -s tests -v
```

## Past runs

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-08 | `97fac452bd` | All 8 export samples QUALIFIED: every machine exported both fixtures into a host folder with exact content, from a cold Store, within budget | [report](../result/2026-11-08/fs-bench-pro/97fac452bd4c1f834bdc2df005cf01caf8b415d0/report.md) |
| 2026-11-08 | `4cd63f16dd` | Export works from all four machines into a host folder: 7 of 8 samples completed with exact content (6 QUALIFIED, native E01 OVER_BUDGET under the first harness rule); Apple Container E01 FAILED mid-stream | [report](../result/2026-11-08/fs-bench-pro/4cd63f16ddbea5791c88fe34be369de27bcfff81/report.md) |
<!-- runs:end -->
