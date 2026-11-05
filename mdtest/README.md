# mdtest — create, stat and remove 512 empty files or directories
> group: filesystem · measures: speed

## Basic info

| | |
| --- | --- |
| Tool | Unmodified MPI `mdtest` from IOR, [hpc/ior `8e109900e24d45f1cd1184f108458f5fa9b4692c`](https://github.com/hpc/ior/tree/8e109900e24d45f1cd1184f108458f5fa9b4692c); native qualification used OpenMPI 5.0.11, the guest build uses Debian 12's pinned package receipt |
| Runs on | native macOS, Docker, Lima and Apple Container; SQLite and PostgreSQL Stores (16 rows) |
| Status | Current launcher profile v2, `one-rank-512-create-stat-remove-v2`; timings are INELIGIBLE diagnostics |
| Frozen rules | [AGENTS.md](AGENTS.md) and the root [SPEC.md](../SPEC.md) |
| Changes | [CHANGES.md](CHANGES.md) |

## Overview

Two small metadata diagnostics. M01 creates, stats and removes 512 empty files;
M02 does the same for directories. Each runs one MPI rank and one iteration,
with separate upstream phase rates. A PASS means the LayerFS CLI lifecycle
completed and mdtest reported all three phase rates without errors or warnings.
It is not independent committed-content proof, a cold-cache speed claim, an MPI
scaling study or a CPU-topology or binding qualification.

| Case | Workload | Expected result |
| --- | --- | --- |
| M01 | 512 empty files (`-F`): create, stat, remove; one rank, one iteration | mdtest exits 0 with create/stat/remove rates in ops/sec; Workspace empty afterwards, UpToDate Commit accepted |
| M02 | 512 directories (`-D`): create, stat, remove; one rank, one iteration | same as M01 |

Exact flags and source hashes are frozen in [src/cases.py](src/cases.py).

## Setup

**Tools.** Build mdtest from the pinned IOR source with `autoreconf -ivf`,
`./configure --without-mpiio CC=mpicc`, and `make`. Provide
`BENCH_TOOL_ROOT/bin/mdtest` and `BENCH_TOOL_ROOT/bin/mpirun`, retaining the
linked MPI runtime. Record actual versions and binary hashes with each campaign.
Build/install tools once outside measured calls. The root-capability OpenMPI
environment switches are set identically on each route; they do not grant
filesystem privileges.

**Launcher (v2).** The current MPI launcher uses
`--host localhost:1 --map-by slot --bind-to none` and
`HWLOC_COMPONENTS=no_os,stop` identically on every machine. These select a
single local scheduling slot and hwloc's generic processor-count fallback
without binding. They avoid requiring a sysfs CPU hierarchy that namespace
Sandboxes do not expose; no synthetic topology, extra rank or product
modification is used. Earlier v1 observations remain separate; see
[CHANGES.md](CHANGES.md).

**Configuration.** Use [environments.example.json](environments.example.json)
as a configuration outline. A complete configuration also needs the campaign's
product artifacts, private home and database ownership.

**Run.** `python3 mdtest/src/run.py --help` lists the shared lifecycle
commands:

```bash
python3 mdtest/src/run.py prepare --environment env.json --cache <dir> --case M01 --machine docker --backend sqlite
python3 mdtest/src/run.py run --environment env.json --cache <dir> --case M01 --machine docker --backend sqlite --output <fresh dir>
python3 mdtest/src/run.py finish --environment env.json --cache <dir>
```

Optional `--verify` checks the committed empty result; upstream phases always
run.

**Time limit.** 15 s per case, covering Create, Mount, Exec, Commit, Unmount
and Cleanup. Upstream includes an intrinsic one-second delay and MPI launch
overhead. Its phase rates cannot be substituted for full CLI wall. Reused setup
and unknown cache state produce explicitly ineligible timing diagnostics. Full
scope and cleanup requirements are in [AGENTS.md](AGENTS.md) and the root
[SPEC.md](../SPEC.md).

## Past runs

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-06 | `b919f50eaf` | Diagnostic terminal: PASS | [report](../result/2026-11-06/mdtest/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) |
<!-- runs:end -->

mdtest v1 (retired): 4 PASS, 1 FAIL, 11 NOT_RUN; superseded by the launcher v2 run above.
