#!/usr/bin/env bash
# fio, one step per command. Each client step runs one SDK client
# (common/client.sh) under the 115 s alarm and logs its step, times, exit and
# the 1-minute load to RUN/commands.log (common/lib.sh).
#
#   run.sh image                         build bench-fio:<date>; benchmark-results/fio/image.txt
#   run.sh setup RUN RUNTIME SEQ RAND SYNC MODE
#                                        volumes, identity, RUN/params.env (RUNTIME s per job; file
#                                        sizes as fio --size, e.g. 1g 512m 64m), then start
#   run.sh start RUN MODE                MODE measured takes the measurement lock (exit 75 while another
#                                        run holds it: wait, then start again), smoke does not; Init,
#                                        create, fork, mount
#   run.sh next RUN                      the next step of the plan below (repeat until DONE)
#   run.sh teardown RUN                  unmount, close, remove the volumes, release the lock
#   run.sh report RUN [OUT]              results.csv, commit.csv and summary.json (report.py)
#
# RUN is a new folder benchmark-results/fio/<UTC yyyymmddTHHMMSSZ> (smoke
# runs: smoke-<id>). The plan lays out each arm's data files (untimed), runs
# each fio job in the layerfs arm, then sandbox-disk, and ends with one
# sandbox.commit of the layerfs Workspace in its own client.
set -euo pipefail
suite=fio
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
# shellcheck source=../common/lib.sh
. "$here/../common/lib.sh"
imagefile=$repo/benchmark-results/fio/image.txt
plan=(layout:layerfs layout:sandbox-disk)
for job in seq-write seq-read rand-write rand-read rand-read-4j randrw-70-30 sync-write rand-write-direct rand-read-direct; do
  plan+=("$job:layerfs" "$job:sandbox-disk")
done
plan+=(commit)
step=${1:-}
shift || true

case "$step" in
image)
  mkdir -p "$(dirname "$imagefile")"
  bench_image "$here/sandbox" "bench-fio:$(date -u +%Y%m%d)" "$imagefile"
  docker run --rm --entrypoint cat "$(sed -n 's/^image=//p' "$imagefile")" /opt/fio-identity.txt >>"$imagefile"
  ;;
setup)
  run=$1 secs=$2 seq=$3 rand=$4 sync=$5 mode=$6
  [[ "$mode" == measured || "$mode" == smoke ]] || { echo "run.sh: MODE is measured or smoke" >&2; exit 2; }
  [[ "$secs" =~ ^[1-9][0-9]*$ ]] || { echo "run.sh: RUNTIME is a positive integer" >&2; exit 2; }
  for s in "$seq" "$rand" "$sync"; do [[ "$s" =~ ^[1-9][0-9]*[kmg]$ ]] || { echo "run.sh: sizes look like 512m" >&2; exit 2; }; done
  bench_setup "$run" "$imagefile" fio "mode=$mode runtime=$secs seq=$seq rand=$rand sync=$sync"
  grep -E '^(fio_version|fio_package|libaio)=' "$imagefile" | sed 's/^/image_/' >>"$run/identity.txt"
  printf 'runtime=%s\nseq_size=%s\nrand_size=%s\nsync_size=%s\n' "$secs" "$seq" "$rand" "$sync" >"$run/params.env"
  mkdir "$run/seed"
  echo "LayerFS fio benchmark Workspace; fio works under fio/." >"$run/seed/README"
  exec "$0" start "$run" "$mode"
  ;;
start)
  run=$1 mode=$2
  [[ "$mode" == smoke ]] || bench_lock "$run"
  bench_client "$run" setup setup.mjs "$run/seed"
  ;;
next)
  run=$1
  for s in "${plan[@]}"; do
    case "$s" in
    commit)
      grep -qs '"step":"commit"' "$run/ledger.jsonl" && continue
      bench_client "$run" commit commit.mjs
      ;;
    layout:*)
      grep -qs "\"arm\":\"${s#*:}\"" "$run/layout.jsonl" && continue
      bench_client "$run" "layout-${s#*:}" layout.mjs "${s#*:}"
      ;;
    *)
      grep -qs "\"case\":\"${s/:/-}\"" "$run/results.jsonl" && continue
      bench_client "$run" "$(bench_next "$run" "job-${s/:/-}")" job.mjs "${s%%:*}" "${s#*:}"
      ;;
    esac
    exit 0
  done
  echo DONE
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
  sed -n '2,20p' "$0" >&2
  exit 2
  ;;
esac
