# Shared shell steps for the SDK-route suites; source it from a suite's
# run.sh after setting `suite` (its folder name). Each client step runs one
# SDK client (common/client.sh) under a 115 s alarm and logs its step, times,
# exit and the 1-minute load to RUN/commands.log.
#
# Measured steps hold the measurement lock (bench_lock / bench_unlock), so
# only one suite measures at a time on this host; building, image work and
# smoke runs need no lock.
common=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
repo=$(cd "$common/../.." && pwd -P)
runtime=layerfs-352-runtime:node24
bin=$repo/core/target/fs-bench-bin
base=sha256:66aeb6bbf7fc825686a0e6d8c8486d90c99d03ce81f854008f179a23bdf4097e
base_tag=fs-bench-computer:gawk-20261020
lockdir=$repo/benchmark-results/.measure.lock

bench_load() { uptime | sed 's/.*load averages*: //' | awk '{print $1}' | tr -d ,; }

# bench_client RUN NAME SCRIPT [ARG...]: one client under the 115 s alarm.
bench_client() {
  local run=$1 name=$2 script=$3 start status=0 l0
  shift 3
  start=$(date -u +%FT%TZ)
  l0=$(bench_load)
  perl -e 'alarm 115; exec @ARGV' "$common/client.sh" "$run" "$suite" "$script" "$@" \
    >"$run/$name.out" 2>"$run/$name.err" || status=$?
  printf '%s\t%s\t%s\texit=%s\tload=%s\n' "$name" "$start" "$(date -u +%FT%TZ)" "$status" "$l0" >>"$run/commands.log"
  tail -n 5 "$run/$name.out"
  [[ $status -eq 0 ]] || { echo "$name: exit $status (see $run/$name.err)" >&2; tail -n 8 "$run/$name.err" >&2; exit "$status"; }
}

# bench_next RUN STEP -> STEP-N, the first unused name.
bench_next() {
  local n=1
  while [[ -e "$1/$2-$n.out" ]]; do n=$((n + 1)); done
  echo "$2-$n"
}

# bench_image CONTEXT_DIR TAG OUT_FILE: build the suite's Sandbox image FROM
# the pinned base tag (checked against its digest) and write image=<digest>.
# Several build commands may be needed under the 115 s ceiling; BuildKit's
# cache carries finished layers between them.
bench_image() {
  local ctx=$1 tag=$2 out=$3 digest
  [[ "$(docker image inspect "$base_tag" --format '{{.Id}}')" == "$base" ]] || { echo "lib.sh: $base_tag is not $base" >&2; exit 2; }
  perl -e 'alarm 115; exec @ARGV' docker build --load -q -t "$tag" "$ctx" >/dev/null
  digest=$(docker image inspect "$tag" --format '{{.Id}}')
  printf 'image=%s\ntag=%s\nbase=%s\n' "$digest" "$tag" "$base" >"$out"
  cat "$out"
}

# bench_setup RUN IMAGE_FILE PROJECT [NOTE]: new run folder, its two volumes,
# deploy.env and identity.txt. The caller then runs its setup client.
bench_setup() {
  local run=$1 imagefile=$2 project=$3 note=${4:-} id volume home_volume
  [[ "$run" == "$repo"/benchmark-results/"$suite"/* && ! -e "$run" ]] || { echo "lib.sh: RUN must be a new folder under $repo/benchmark-results/$suite" >&2; exit 2; }
  # shellcheck source=/dev/null
  . "$imagefile"
  id=$(basename "$run")
  volume=bench-$suite-$id home_volume=bench-$suite-$id-sdk-home
  for v in "$volume" "$home_volume"; do
    ! docker volume inspect "$v" >/dev/null 2>&1 || { echo "lib.sh: volume $v exists" >&2; exit 2; }
  done
  mkdir -p "$run"
  docker volume create "$volume" >/dev/null
  docker volume create "$home_volume" >/dev/null
  printf 'image=%q\nvolume=%q\nhome_volume=%q\nbin=%q\nruntime=%q\nproject=%q\nprefix=%q\n' \
    "$image" "$volume" "$home_volume" "$bin" "$runtime" "$project" "bench-$suite-$id-" >"$run/deploy.env"
  {
    echo "suite=$suite run=$id started=$(date -u +%FT%TZ) $note"
    echo "image=$image ($tag) base=$base runtime=$runtime@$(docker image inspect "$runtime" --format '{{.Id}}')"
    shasum -a 256 "$bin/layerfs-daemon" "$bin/layerfs.node"
    echo "source=$(git -C "$repo" rev-parse HEAD) harness_dirty_files=$(git -C "$repo" status --porcelain -- "benchmark/$suite" benchmark/common | wc -l | tr -d ' ')"
    echo "policy=wholeFileDepth 16, chunkDepth 8, metadataDepth 8; profile Disposable; LAYERFS_CONSTRUCTION_WORKERS=1; trace off"
    echo "docker=$(docker version --format '{{.Server.Version}}') $(docker info --format '{{.OperatingSystem}} {{.KernelVersion}} cpus={{.NCPU}} mem={{.MemTotal}}')"
  } >"$run/identity.txt"
}

# bench_lock RUN: take the measurement lock (one measuring suite per host).
# Exit 75 when another run holds it; the caller waits and asks again.
bench_lock() {
  local run=$1
  mkdir -p "$(dirname "$lockdir")"
  if mkdir "$lockdir" 2>/dev/null; then
    echo "$suite $run $(date -u +%FT%TZ)" >"$lockdir/owner"
    echo "lock=taken $(date -u +%FT%TZ)" >>"$run/identity.txt"
  else
    echo "lib.sh: measurement lock held by: $(cat "$lockdir/owner" 2>/dev/null)" >&2
    exit 75
  fi
}

# bench_unlock RUN: release the lock if this run holds it.
bench_unlock() {
  local run=$1
  if [[ -f "$lockdir/owner" ]] && [[ "$(awk '{print $2}' "$lockdir/owner")" == "$run" ]]; then
    rm -rf "$lockdir"
    echo "lock=released $(date -u +%FT%TZ)" >>"$run/identity.txt"
  else
    echo "lib.sh: $run does not hold the lock" >&2
  fi
}

# bench_cleanup RUN: remove the run's two volumes (after the teardown client).
bench_cleanup() {
  local run=$1
  # shellcheck source=/dev/null
  . "$run/deploy.env"
  docker volume rm "$volume" "$home_volume"
  echo "removed=$volume $home_volume at $(date -u +%FT%TZ)" >>"$run/identity.txt"
}
