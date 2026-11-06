# fs-bench-cloudflare-computer agent instructions

> Status: Implemented diagnostic workload contract; no cold-cache qualification.

Follow root [AGENTS.md](../AGENTS.md). This suite runs Cloudflare Computer's
frozen `script/fs-bench.sh` on LayerFS through the public CLI. It owns one case,
B01, with twelve scenarios inside it, and eight rows: native, Docker, Lima and
Apple Container, each with SQLite then PostgreSQL. It came from
[layerfs-project#72](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/72).
**Computer itself is not part of this suite** (owner, 2026-11-06): only the
script is used; no Computer arm, image or daemon. The retired
`.archive/fs-bench/` stays frozen.

## Frozen workload

[image/fs-bench.sh](image/fs-bench.sh) is byte-identical to Computer
`de87919a4fd37242e960e13b7b3ba802d1eef0a0` `script/fs-bench.sh` (blob
`338dd9a85dde…`, SHA-256 `0e2004339a92…37230ef`, MIT). Never edit it. The
exact command body, settings and scenario list are in [src/cases.py](src/cases.py),
workload `fs-bench-cloudflare-computer-v1`:

- `REPS=1 WARMUP=0 RANDOMIZE_TARGETS=0`, no `BASE`. Upstream defaults are
  `WARMUP=1` and randomized targets; both are overridden. No best-of, no warmup.
- `SCENARIOS` selects the twelve offline scenarios, in script order. git clone,
  npm and Go are excluded.
- The body checks the script's SHA-256, runs it once on the Workspace root
  (`MOUNT="$PWD"`) as the Sandbox identity, writes the script's JSON to stdout
  and its summary to stderr, and keeps scratch files in `/tmp`.

The script times each scenario itself with `date +%s%N` inside the mount and
exits 0 even when a scenario fails. `parse_result` is therefore the check: one
sample for each of the twelve scenarios, single-sample statistics equal, no
value at mawk's 2³¹−1 ceiling. Anything else is FAIL.

## Machines and execution

The Linux machines use one Sandbox image: the LayerFS runtime image (Debian 12,
bash 5, GNU coreutils, git) plus gawk and the frozen script
([image/Dockerfile](image/Dockerfile)). See [TOOL.md](TOOL.md).

Native macOS has bash 3.2, which the script cannot run (`declare -A`), and its
`sha256sum` has no `--quiet`. Native rows put a pinned bash 5.2.37 and a small
`sha256sum -c --quiet` wrapper first on the Exec PATH through the machine's
`tool_environment` ([TOOL.md](TOOL.md)); the workload command and the script
stay byte-identical to the Linux rows. Without them, native rows are NOT_RUN.
Native rows run close to the 25 s budget (macOS launches one process per file
in the 1,000-step loops on an NFS mount); a row over it is FAIL, never retried.

Use the shared runner ([src/run.py](src/run.py)) unchanged: create, mount, one
Exec, LayerFS Commit, unmount, close, Store remove or disconnect. The script
removes its own directories, so Commit is normally `UpToDate`. Keep rows serial
in native, Docker, Lima, Apple Container order, SQLite then PostgreSQL; one
attempt per row; no build, provisioning or cache reset overlaps a row.

Set `"shared_infrastructure": true` in the campaign config. The runner calls
`finish` after any prepare that is not READY, including a NOT_RUN native row;
without that flag it releases every registered machine and server mid-campaign.
Release shared infrastructure yourself after the last row.

## Budgets, results and limits

The whole script runs in one Exec, so each row has a declared 25 s performance
budget (the shared runner's maximum) and a 25 s setup budget. A row over budget
is FAIL. No command runs longer than two minutes.

Report a lifecycle table for the eight rows, then one scenario table per
database with Docker as the baseline column and `machine / Docker` ratios.
`pure read`, `pure copy` and `overwrite` are own-write warm; the 64 MiB rows
write zeros. No cache is proven cold: every time and ratio is an INELIGIBLE
diagnostic. There is no independent verifier (each scenario deletes its
output), so `--verify` is refused. Publish one report with
[src/report.py](src/report.py); raw receipts stay local.
