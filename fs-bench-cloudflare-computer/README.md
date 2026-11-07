# fs-bench-cloudflare-computer — Cloudflare's fs-bench.sh on LayerFS
> group: filesystem · measures: speed

## Basic info

| Item | Value |
| --- | --- |
| Tool | Unchanged upstream `script/fs-bench.sh` from Cloudflare Computer `de87919a4fd37242e960e13b7b3ba802d1eef0a0` (MIT) |
| Runs on | Four LayerFS machines (native, Docker, Lima, Apple Container) and two Store backends (SQLite, PostgreSQL): 1 case, 12 scenarios, 8 rows, plus one host-baseline sample per campaign taken on plain APFS outside LayerFS |
| Status | Implemented diagnostic workload; no cold-cache qualification; timings are INELIGIBLE diagnostics. Computer itself is not measured. The host baseline is host cost, not a LayerFS row |
| Frozen rules | [AGENTS.md](AGENTS.md); exact body and scenarios in [src/cases.py](src/cases.py); host recorder in [src/host.py](src/host.py); image in [TOOL.md](TOOL.md) |
| Lifecycle | [shared/src/runner.py](../shared/src/runner.py); this suite has no separate lifecycle |

## Overview

[fs-bench-quick](../fs-bench-quick/) runs the same twelve workloads with
rewritten bodies, one Sandbox per workload, and times the whole lifecycle. This
suite runs Cloudflare's own script, byte for byte, once per row in one Exec,
and reports the script's own in-mount timer for each scenario.

| Scenario | What the script times | Cache state |
| --- | --- | --- |
| create 1000 files | `echo $i > f$i` for 1–1000 | self-contained |
| stat 1000 files | create them, then `stat` each | self-contained |
| rm 1000 files | create them, then `rm f*` | self-contained |
| mkdir tree (10x10x10) | 10 × 10 directories, 10 files each | self-contained |
| find tree | build that tree, then `find . -type f \| wc -l` | self-contained |
| write 64 MiB | `dd` 64 MiB of zeros | self-contained |
| copy 64 MiB | write 64 MiB, then `cp` | self-contained |
| read 64 MiB | write 64 MiB, then `cat` it | self-contained |
| pure read 64 MiB | `cat` a 64 MiB file written just before the clock | own-write warm |
| pure copy 64 MiB | `cp` a 64 MiB file written just before the clock | own-write warm |
| overwrite 64 MiB | rewrite a 64 MiB file written just before the clock | own-write warm |
| git init + commit 100 files | `git init`, 100 files, `git add -A`, `git commit` | self-contained |

Each scenario runs once in a fresh directory that the script removes. A PASS
row means the CLI lifecycle succeeded and the script reported one sample for
all twelve. It is not content verification or a cold performance claim.

Native macOS cost is reported in two parts. One host sample per campaign runs
the same script, with the same pinned bash and PATH, on an ordinary APFS
directory outside LayerFS ([src/host.py](src/host.py)); the scenario tables then
show `host ms`, `host / Docker` and `native − host ms`, so `native − host` is
the LayerFS-attributable time. The sample is host cost, not a ninth row, and it
is taken once because the host does not depend on the database.

## Setup

Prerequisites, all described in [TOOL.md](TOOL.md):

- the suite image (Debian userland with bash 5, gawk and git, plus the frozen
  script);
- matched release CLI, native daemon and a Linux bundle sealed with that image;
- LayerFS machines: Docker on the image, Lima and Apple Container from the
  bundle's archive;
- a dedicated PostgreSQL server with one empty database per PostgreSQL row;
- for native macOS, a pinned bash 4+ and a `sha256sum -c --quiet` wrapper on
  the Exec PATH ([TOOL.md](TOOL.md#native-macos));
- for the host baseline, one empty APFS directory outside every Store, Workspace
  and campaign cache, used by the same pinned tools.

Config: copy [environments.example.json](environments.example.json), replace
placeholders and keep `"shared_infrastructure": true`, so a NOT_RUN row does
not make the runner release the machines (see [AGENTS.md](AGENTS.md)).
Export the PostgreSQL password variable named in the config, then prepare and
run one row at a time, native → Docker → Lima → Apple Container, SQLite then
PostgreSQL:

```bash
E=/private/fbcc.json C=/private/fbcc-prepared O=/retained/fbcc
python3 fs-bench-cloudflare-computer/src/run.py prepare --environment $E --cache $C \
  --case B01 --machine docker --backend sqlite
python3 fs-bench-cloudflare-computer/src/run.py run --environment $E --cache $C \
  --case B01 --machine docker --backend sqlite --output $O/docker/sqlite
```

Record the campaign's one host sample (plain APFS outside LayerFS; it refuses
the directory with a reason rather than guess):

```bash
python3 fs-bench-cloudflare-computer/src/host.py --environment $E --cache $C
```

Finish, release the shared infrastructure, then publish:

```bash
python3 fs-bench-cloudflare-computer/src/run.py finish --environment $E --cache $C
python3 fs-bench-cloudflare-computer/src/report.py --input $C --cleanup /retained/final-cleanup.json \
  --environment $E --host-baseline $C/host-baseline.json \
  --output result/YYYY-MM-DD/fs-bench-cloudflare-computer/FULL_LAYERFS_SHA/report.md
```

Each row has a 25 s budget; native macOS rows have 60 s ([AGENTS.md](AGENTS.md)).
Without `--host-baseline` the report still renders, with the host columns reading
`UNAVAILABLE`. Run the harness checks with an explicit bound:

```bash
python3 -c 'import subprocess; subprocess.run(["python3", "-m", "unittest", "discover", "-s", "fs-bench-cloudflare-computer/tests", "-v"], check=True, timeout=30)'
```

## Past runs

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-06 | `6d820c756b` | 8 of 8 rows ran all twelve scenarios (8 PASS); final cleanup COMPLETE | [report](../result/2026-11-06/fs-bench-cloudflare-computer/6d820c756b9b12541ac84af7b88467069f31bcbf/report.md) |
<!-- runs:end -->
