#!/usr/bin/env bash
# smallfile, one step per command. Each client step runs one SDK client
# (common/client.sh) under the 115 s alarm and logs its step, times, exit and
# the 1-minute load to RUN/commands.log (common/lib.sh).
#
#   run.sh image                    build bench-smallfile:<date>; benchmark-results/smallfile/image.txt
#   run.sh setup RUN FILES MODE     volumes, identity, RUN/params.env (FILES per thread), then start
#   run.sh start RUN MODE           MODE measured takes the measurement lock (exit 75 while another run
#                                   holds it: wait, then start again), smoke does not; Init, create,
#                                   fork, mount
#   run.sh next RUN                 the next step of the plan below (repeat until DONE)
#   run.sh teardown RUN             unmount, close, remove the volumes, release the lock
#   run.sh report RUN [OUT]         results.csv, commit.csv and summary.json (report.py)
#
# RUN is a new folder benchmark-results/smallfile/<UTC yyyymmddTHHMMSSZ>
# (smoke runs: smoke-<id>). The plan runs each smallfile operation in the
# layerfs arm, then sandbox-disk, over the same top folder per arm; one
# sandbox.commit follows the layerfs create, in its own client.
set -euo pipefail
suite=smallfile
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
# shellcheck source=../common/lib.sh
. "$here/../common/lib.sh"
imagefile=$repo/benchmark-results/smallfile/image.txt
plan=(create:layerfs commit create:sandbox-disk)
for op in read append stat chmod rename delete-renamed mkdir rmdir; do plan+=("$op:layerfs" "$op:sandbox-disk"); done
step=${1:-}
shift || true

case "$step" in
image)
  mkdir -p "$(dirname "$imagefile")"
  bench_image "$here/sandbox" "bench-smallfile:$(date -u +%Y%m%d)" "$imagefile"
  docker run --rm --entrypoint cat "$(sed -n 's/^image=//p' "$imagefile")" /opt/smallfile-identity.txt >>"$imagefile"
  ;;
setup)
  run=$1 files=$2 mode=$3
  [[ "$mode" == measured || "$mode" == smoke ]] || { echo "run.sh: MODE is measured or smoke" >&2; exit 2; }
  [[ "$files" =~ ^[1-9][0-9]*$ ]] || { echo "run.sh: FILES is a positive integer" >&2; exit 2; }
  bench_setup "$run" "$imagefile" smallfile "mode=$mode files_per_thread=$files"
  grep -E '^(smallfile_commit|smallfile_version|python|pyyaml)=' "$imagefile" | sed 's/^/image_/' >>"$run/identity.txt"
  printf 'threads=4\nfiles=%s\nfile_size_kb=4\n' "$files" >"$run/params.env"
  mkdir "$run/seed"
  echo "LayerFS smallfile benchmark Workspace; smallfile works under sf/." >"$run/seed/README"
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
    if [[ "$s" == commit ]]; then
      grep -qs '"step":"commit"' "$run/ledger.jsonl" && continue
      bench_client "$run" commit commit.mjs
    else
      grep -qs "\"case\":\"${s/:/-}\"" "$run/results.jsonl" && continue
      # shellcheck source=/dev/null
      . "$run/params.env"
      bench_client "$run" "$(bench_next "$run" "op-${s/:/-}")" op.mjs "${s%%:*}" "${s#*:}" "$threads" "$files" "$file_size_kb"
    fi
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
  sed -n '2,19p' "$0" >&2
  exit 2
  ;;
esac
