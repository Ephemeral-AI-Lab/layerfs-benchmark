#!/usr/bin/env bash
# mdtest, one step per command. Each client step runs one SDK client
# (common/client.sh) under the 115 s alarm and logs its step, times, exit and
# the 1-minute load to RUN/commands.log (common/lib.sh).
#
#   run.sh image                    build bench-mdtest:<date>; benchmark-results/mdtest/image.txt
#   run.sh setup RUN CASES MODE     volumes, identity, CASES copied to RUN/cases.tsv, then start
#   run.sh start RUN MODE           MODE measured takes the measurement lock (exit 75 while another run
#                                   holds it: wait, then start again), smoke does not; Init, create,
#                                   fork, mount
#   run.sh next RUN                 the next case and arm from RUN/cases.tsv (repeat until DONE)
#   run.sh commit RUN               the commit pass, layerfs only: mdtest -C, sandbox.commit, mdtest -r
#   run.sh teardown RUN             unmount, close, remove the volumes, release the lock
#   run.sh report RUN [OUT]         results.csv, commit.csv and summary.json (report.py)
#
# RUN is a new folder benchmark-results/mdtest/<UTC yyyymmddTHHMMSSZ> (smoke
# runs: smoke-<id>). CASES is cases.tsv (measured) or cases-smoke.tsv. Each
# row is one mdtest case run in the layerfs arm, then sandbox-disk; the row
# named `commit` gives the commit pass's procs, items and mode flag.
set -euo pipefail
suite=mdtest
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
# shellcheck source=../common/lib.sh
. "$here/../common/lib.sh"
imagefile=$repo/benchmark-results/mdtest/image.txt
step=${1:-}
shift || true

# row RUN CASE -> "PROCS ITEMS ARGS..." of that cases.tsv row.
row() { awk -F'\t' -v c="$2" '$1 == c { print $2, $3, $4 }' "$1/cases.tsv"; }

case "$step" in
image)
  mkdir -p "$(dirname "$imagefile")"
  bench_image "$here/sandbox" "bench-mdtest:$(date -u +%Y%m%d)" "$imagefile"
  docker run --rm --entrypoint cat "$(sed -n 's/^image=//p' "$imagefile")" /opt/mdtest-identity.txt >>"$imagefile"
  ;;
setup)
  run=$1 cases=$2 mode=$3
  [[ "$mode" == measured || "$mode" == smoke ]] || { echo "run.sh: MODE is measured or smoke" >&2; exit 2; }
  bench_setup "$run" "$imagefile" mdtest "mode=$mode cases=$(basename "$cases")"
  grep -E '^(ior_commit|mdtest_sha256|mdtest_version|mpi|gcc)=' "$imagefile" | sed 's/^/image_/' >>"$run/identity.txt"
  cp "$cases" "$run/cases.tsv"
  mkdir "$run/seed"
  echo "LayerFS mdtest benchmark Workspace; mdtest works under md/." >"$run/seed/README"
  exec "$0" start "$run" "$mode"
  ;;
start)
  run=$1 mode=$2
  [[ "$mode" == smoke ]] || bench_lock "$run"
  bench_client "$run" setup setup.mjs "$run/seed"
  ;;
next)
  run=$1
  # The first (row, arm) without a results.jsonl line: CASE ARM PROCS ITEMS ARGS.
  pick=$(python3 - "$run" <<'PY'
import json, os, sys
run = sys.argv[1]
done = set()
if os.path.exists(f"{run}/results.jsonl"):
    done = {(r["case"], r["arm"]) for r in map(json.loads, filter(str.strip, open(f"{run}/results.jsonl")))}
for line in open(f"{run}/cases.tsv"):
    if not line.strip() or line.startswith("#"):
        continue
    case, procs, items, args = (line.rstrip("\n").split("\t") + [""])[:4]
    if case == "commit":
        continue
    for arm in ("layerfs", "sandbox-disk"):
        if (case, arm) not in done:
            print(case, arm, procs, items, args)
            sys.exit(0)
PY
)
  if [[ -z "$pick" ]]; then echo DONE; exit 0; fi
  read -r -a argv <<<"$pick"
  bench_client "$run" "$(bench_next "$run" "case-${argv[0]}-${argv[1]}")" case.mjs "${argv[@]}"
  ;;
commit)
  run=$1
  read -r procs items flags <<<"$(row "$run" commit)"
  [[ -n "$items" ]] || { echo "run.sh: $run/cases.tsv has no commit row" >&2; exit 2; }
  bench_client "$run" commit-create case.mjs commit-create layerfs "$procs" "$items" "$flags" -C
  bench_client "$run" commit commit.mjs
  bench_client "$run" commit-remove case.mjs commit-remove layerfs "$procs" "$items" "$flags" -r
  ;;
teardown)
  run=$1
  bench_client "$run" teardown teardown.mjs
  bench_cleanup "$run"
  if grep -q '^lock=taken' "$run/identity.txt"; then bench_unlock "$run"; fi
  ;;
report)
  python3 "$here/report.py" "$@"
  ;;
*)
  sed -n '2,19p' "$0" >&2
  exit 2
  ;;
esac
