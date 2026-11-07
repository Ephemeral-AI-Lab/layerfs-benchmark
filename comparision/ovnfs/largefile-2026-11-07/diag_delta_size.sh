set -e
export OVNFS_STATE=/data/state
mkdir -p /data/src && cd /data/src
python3 - <<'PY'
import random
for mib in (2,3,4,5,6,8,12):
    open(f"r{mib:02d}.bin","wb").write(random.Random(f"diag/{mib}").randbytes(mib<<20))
r=random.Random("diag/text"); words=["alpha","beta","gamma","delta","omega","sigma","kappa","lambda"]
with open("t10.txt","w") as f:
    n=0
    while n < 10<<20:
        line=f"{n:010d} "+" ".join(r.choice(words) for _ in range(8))+f" {r.getrandbits(32):08x}\n"; f.write(line); n+=len(line)
PY
ovnfs start >/dev/null; ovnfs --json new --name main --rule 'source *' >/dev/null; ovnfs --json new --name b01 --rule 'source *' >/dev/null
cd /root/checkouts/b01
snapshot() { ovnfs --json snap b01 --wait >/dev/null; }
packs() { du -s -b --apparent-size /data/state/store/packs | cut -f1; }
loose() { find /data/state/store/objects -type f | wc -l; }
for f in r02.bin r03.bin r04.bin r05.bin r06.bin r08.bin r12.bin t10.txt; do
  p0=$(packs); l0=$(loose)
  python3 -c "import os,random;f=open('$f','r+b');s=os.path.getsize('$f');r=random.Random('edit/$f');f.seek(r.randrange(s-100));f.write(r.randbytes(100) if '$f'.endswith('.bin') else b'x'*100)"
  snapshot
  echo "$f size=$(stat -c %s $f) packs+=$(( $(packs) - p0 )) loose+=$(( $(loose) - l0 ))"
done
ovnfs stop >/dev/null
