#!/bin/sh
# run.sh LABEL ORDER CASE...: one cold sample of each CASE on both systems; results move to
# results/<arm>-<case>.<LABEL>. ORDER is "lf" (LayerFS first) or "ov" (ovnfs first).
# A failed unit is never retried: the case is closed and the run goes on to the next case.
H=$(cd "$(dirname "$0")" && pwd); C=$HOME/.cache/fsh-cold; cd "$H" || exit 2
export LF_CAMPAIGN=$C LF_RESULTS=$C/results LF_BASE=$C/base CMP_CAMPAIGN=$C
export LAYERFS_HOME=$C/home XDG_CACHE_HOME=$C/xdg LAYERFS_CONSTRUCTION_WORKERS=1
LABEL=$1; ORDER=$2; shift 2
case $LABEL in *[!a-z0-9]*|'') echo "bad LABEL '$LABEL'"; exit 2;; esac
case $ORDER in lf|ov) ;; *) echo "bad ORDER '$ORDER'"; exit 2;; esac
$C/artifacts/layerfs machine start docker > /dev/null || { echo "machine start failed"; exit 1; }
branches() { case $1 in S1) echo b01;; S2|S4) echo b01 b02 b03 b04 b05;; S3) echo l01 l02 l03 l04;; esac; }
one() {  # one ARM CASE
  arm=$1; case=$2
  # never touch a case that already has results: no open, no close
  [ -e $C/results/$arm-$case ] && { echo "SKIP $arm $case: results exist"; return 2; }
  [ -e $C/results/$arm-$case.$LABEL ] && { echo "SKIP $arm $case: $LABEL exists"; return 2; }
  case $case in
    S*) python3 compare.py $arm $case open > /dev/null || { echo "FAIL $arm $case open"; python3 compare.py $arm $case close > /dev/null; return 1; }
        for b in $(branches $case); do python3 compare.py $arm $case branch $b > /dev/null || { echo "FAIL $arm $case $b"; python3 compare.py $arm $case close > /dev/null; return 1; }; done
        python3 compare.py $arm $case close > /dev/null || { echo "FAIL $arm $case close"; return 1; } ;;
    *)  last=$(python3 -c "import largefile;print(largefile.CASES['$case']['commits'])")
        drv=lf_layerfs.py; [ $arm = ovnfs ] && drv=lf_ovnfs.py
        for u in "open" "steps 1 $last" "verify" "close"; do
          python3 $drv $case $u > /dev/null || { echo "FAIL $arm $case $u"; [ "$u" = close ] || python3 $drv $case close > /dev/null; return 1; }
        done ;;
  esac
}
for case in "$@"; do
  if [ $ORDER = lf ]; then arms="layerfs ovnfs"; else arms="ovnfs layerfs"; fi
  for arm in $arms; do
    one $arm $case; rc=$?
    [ $rc = 2 ] || mv $C/results/$arm-$case $C/results/$arm-$case.$LABEL
    echo "$LABEL $arm $case rc=$rc $(date +%T) load $(sysctl -n vm.loadavg | cut -d' ' -f2)"
  done
done
