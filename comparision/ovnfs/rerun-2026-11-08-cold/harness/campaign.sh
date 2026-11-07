#!/bin/sh
# campaign.sh: three cold samples of every case on both systems, alternating which system goes
# first, then release the LayerFS machine. Log: ~/.cache/fsh-cold/run.log.
H=$(cd "$(dirname "$0")" && pwd); C=$HOME/.cache/fsh-cold
CASES="S1 S2 S3 S4 NEW500 ADD500 RM500 DEL500 L500 L100 L10 I10 A5"
date; uptime
$H/run.sh run1 lf $CASES
$H/run.sh run2 ov $CASES
$H/run.sh run3 lf $CASES
export LAYERFS_HOME=$C/home XDG_CACHE_HOME=$C/xdg
$C/artifacts/layerfs store list; $C/artifacts/layerfs sandbox list
docker ps -a --format '{{.Names}}' | grep -E '^fsh-(cmp|lf)-ov'
ID=$(python3 -c "import json;print(json.load(open('$C/home/layerfs.json'))['id'][:8])")
$C/artifacts/layerfs machine stop docker > /dev/null && docker rm lfs-$ID-docker > /dev/null \
  && docker volume rm lfs-$ID-docker-data > /dev/null && echo "machine released"
echo "campaign done $(date)"
