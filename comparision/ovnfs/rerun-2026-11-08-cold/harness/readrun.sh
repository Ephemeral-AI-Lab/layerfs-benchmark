#!/bin/sh
# readrun.sh LABEL READS CASE...: each read CASE on both systems (alternating which goes first per
# case), READS cold reads each; results move to results/<arm>-<case>.<LABEL>. Failed units are
# never retried: the case is closed and the run moves on. Releases the LayerFS machine at the end.
H=$(cd "$(dirname "$0")" && pwd); C=$HOME/.cache/fsh-cold; cd "$H" || exit 2
export CMP_CAMPAIGN=$C LAYERFS_HOME=$C/home XDG_CACHE_HOME=$C/xdg LAYERFS_CONSTRUCTION_WORKERS=1
LABEL=$1; READS=$2; shift 2
case $LABEL in *[!a-z0-9]*|'') echo "bad LABEL"; exit 2;; esac
case $READS in [1-9]) ;; *) echo "bad READS"; exit 2;; esac
$C/artifacts/layerfs machine start docker > /dev/null || { echo "machine start failed"; exit 1; }
i=0
for case in "$@"; do
  i=$((i + 1)); if [ $((i % 2)) = 1 ]; then arms="layerfs ovnfs"; else arms="ovnfs layerfs"; fi
  for arm in $arms; do
    if [ -e $C/results/$arm-$case ] || [ -e $C/results/$arm-$case.$LABEL ]; then echo "SKIP $arm $case: results exist"; continue; fi
    rc=0
    python3 readcase.py $arm $case open > /dev/null || rc=1
    k=1; while [ $rc = 0 ] && [ $k -le $READS ]; do python3 readcase.py $arm $case read $k > /dev/null || rc=1; k=$((k + 1)); done
    python3 readcase.py $arm $case close > /dev/null || { [ -e $C/results/$arm-$case/state.json ] && grep -q "\"released\": true" $C/results/$arm-$case/state.json || echo "CLOSE FAIL $arm $case"; rc=1; }
    mv $C/results/$arm-$case $C/results/$arm-$case.$LABEL
    echo "$LABEL $arm $case rc=$rc $(date +%T) load $(sysctl -n vm.loadavg | cut -d' ' -f2)"
  done
done
ID=$(python3 -c "import json;print(json.load(open('$C/home/layerfs.json'))['id'][:8])")
$C/artifacts/layerfs store list; $C/artifacts/layerfs sandbox list
docker ps -a --format '{{.Names}}' | grep -E '^fsh-rd-ov'
$C/artifacts/layerfs machine stop docker > /dev/null && docker rm lfs-$ID-docker > /dev/null \
  && docker volume rm lfs-$ID-docker-data > /dev/null && echo "machine released"
echo "read run done $(date)"
