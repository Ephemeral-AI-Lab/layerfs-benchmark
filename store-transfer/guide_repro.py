#!/usr/bin/env python3
"""LP08-S3 #10: run the guide's own bash blocks, verbatim, in a fresh home.

Every ```bash block of `GUIDE-zh.md` is executed once, in order, in one bash
session (so its exports persist), with per-block exit code, stdout and stderr
kept as a receipt. Each block is then checked against what the guide says the
output is: the guide is the specification, so a mismatch is a guide bug, not a
check to relax.

    python3 guide_repro.py            # needs the docker machine stopped or running
"""
import json
import os
import re
import subprocess
import time
from pathlib import Path

# The guide and its receipts live with this script; the rest of the run stayed in the
# paths below (LP08-S3, 2026-11-07) and has to be pointed at the current environment.
HERE = Path(__file__).resolve().parent
GUIDE = HERE / "GUIDE-zh.md"
BASE = Path(os.environ.get("LP08_BASE", "/tmp/lp08-s3"))
OUT = HERE / "receipts" / "guide"
CLI = os.environ.get("LAYERFS_CLI", "layerfs")

RESULTS = []


def blocks():
    text = GUIDE.read_text()
    return [body for body in re.findall(r"```bash\n(.*?)```", text, re.S)]


def run_all():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.out"):
        old.unlink()
    for old in OUT.glob("*.err"):
        old.unlink()
    parts = ["set +e", "export PATH=%s:$PATH" % str(Path(CLI).parent), 'OUT="%s"' % OUT]
    for index, body in enumerate(blocks()):
        parts.append("{")
        parts.append(body)
        parts.append("} >\"$OUT/%02d.out\" 2>\"$OUT/%02d.err\"" % (index, index))
        parts.append('echo "@@STEP %02d exit $?"' % index)
    script = OUT / "guide-script.sh"
    script.write_text("\n".join(parts) + "\n")
    started = time.monotonic()
    done = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=3600,
                          env={**os.environ, "LAYERFS_HOME": str(BASE / "guide-home")})
    return done, round(time.monotonic() - started, 1)


def read_block(index):
    out = (OUT / ("%02d.out" % index)).read_text() if (OUT / ("%02d.out" % index)).exists() else ""
    err = (OUT / ("%02d.err" % index)).read_text() if (OUT / ("%02d.err" % index)).exists() else ""
    return out, err


def check(index, name, ok, evidence=""):
    RESULTS.append({"block": index, "check": name, "ok": bool(ok), "evidence": str(evidence)[:1200]})
    return bool(ok)


def last_json(text):
    for line in reversed(text.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                continue
    return None


def main():
    exits = {}
    done, seconds = run_all()
    for line in done.stdout.splitlines():
        match = re.match(r"@@STEP (\d+) exit (\d+)", line.strip())
        if match:
            exits[int(match.group(1))] = int(match.group(2))
    total = len(blocks())
    for index in range(total):
        out, err = read_block(index)
        exits.setdefault(index, None)
        RESULTS.append({"block": index, "receipt": {"exit": exits[index], "seconds": None,
                                                    "stdout": out[-4000:], "stderr": err[-4000:]}})

    # ---- block by block, exactly what the guide documents -----------------
    i = 0
    out, err = read_block(i)
    check(i, "the home and fixture are printed", exits[i] == 0 and "home=" in out and "fixture=" in out, out)

    i = 1
    out, err = read_block(i)
    check(i, "layerfs is 2.0.0", "layerfs 2.0.0" in out, out[:300])
    check(i, "native/docker/apple-container are ready", out.count('"ready":true') >= 3, out[:200])
    check(i, "firecracker and ssh are refused by product policy",
          "permanently disabled by product policy" in out, "policy text present")
    check(i, "the block exits 0", exits[i] == 0, exits[i])

    i = 2
    out, err = read_block(i)
    check(i, "native is ready", '"name":"native"' in out and '"state":"ready"' in out, out[:400])
    check(i, "docker is recorded and ready", '"name":"docker"' in out and out.count('"state":"ready"') == 2,
          out[:600])
    check(i, "the block exits 0", exits[i] == 0, exits[i])

    i = 3
    out, err = read_block(i)
    check(i, "docker is running", '"state":"running"' in out, out[:400])
    check(i, "docker reports free disk", '"free_disk":' in out, out[:300])
    check(i, "the block exits 0", exits[i] == 0, exits[i])

    i = 4
    out, err = read_block(i)
    check(i, "the store is a sqlite store on native", '"kind":"sqlite"' in out and '"machine":"native"' in out, out[:600])
    check(i, "the project is created", '"project":"shop/web"' in out, out[:600])
    check(i, "status is idle with no op and no incoming copy",
          '"state":"idle"' in out and '"op":null' in out and '"incoming_bytes":0' in out, out[-600:])
    check(i, "the block exits 0", exits[i] == 0, exits[i])

    i = 5
    out, err = read_block(i)
    phases = re.findall(r'"phase":"(\w+)"', err)
    order = ["check", "snapshot", "send", "verify", "install", "record", "retire"]
    firsts = []
    for phase in order:
        firsts.append(phases.index(phase) if phase in phases else None)
    check(i, "all seven phases appear in stderr", all(p in phases for p in order), phases[:12])
    check(i, "the phases appear in order", all(p is not None for p in firsts) and firsts == sorted(firsts), firsts)
    result = None
    for line in out.strip().splitlines():
        if line.strip().startswith('{"store":"shop"'):
            result = json.loads(line)
    check(i, "push reports native->docker with the store's bytes",
          result is not None and result.get("from") == "native" and result.get("to") == "docker"
          and result.get("bytes", 0) > 60 << 20, json.dumps(result)[:400])
    check(i, "store get names docker and a retired transfer",
          '"machine":"docker"' in out and '"retired":true' in out, out[-800:])
    check(i, "the block exits 0", exits[i] == 0, exits[i])
    PUSHED = result or {}

    i = 6
    out, err = read_block(i)
    check(i, "the native store file is retired", "store.sqlite" not in out, out[:600])
    check(i, "status is idle on docker",
          '"machine":"docker"' in out and '"state":"idle"' in out, out[-500:])
    check(i, "the block exits 0", exits[i] == 0, exits[i])

    i = 7
    out, err = read_block(i)
    check(i, "the mount reports its workspace id", "ws=" in out and "sb-shop:" in out, out[:600])
    check(i, "the mounted project is readable", "lp08 s3 fixture" in out, out[:400])
    check(i, "the Sandbox is closed (no MountsActive)", "MountsActive" not in err, err[-400:])
    check(i, "the block exits 0", exits[i] == 0, exits[i])

    i = 8
    out, err = read_block(i)
    check(i, "the pull reports docker->native", '"from":"docker"' in out and '"to":"native"' in out, out[:600])
    check(i, "store get is back on native with a retired transfer",
          '"machine":"native"' in out and '"retired":true' in out, out[-800:])
    check(i, "status is idle with incoming_bytes 0",
          '"state":"idle"' in out and '"incoming_bytes":0' in out, out[-500:])
    check(i, "the block exits 0", exits[i] == 0, exits[i])
    PULLED_HEADS = None
    for line in out.splitlines():
        if '"heads":"' in line:
            found = re.search(r'"heads":"([0-9a-f]{64})"', line)
            if found:
                PULLED_HEADS = found.group(1)
    check(i, "the pull records the history heads", PULLED_HEADS is not None, str(PULLED_HEADS))
    check(i, "the fork from the mount changed the heads (so the push's differ)",
          PULLED_HEADS != PUSHED.get("heads"), "%s vs %s" % (PULLED_HEADS, PUSHED.get("heads")))

    i = 9
    out, err = read_block(i)
    check(i, "lima is created running", '"name":"lm"' in out and '"state":"running"' in out, out[:500])
    check(i, "lima reports free disk", '"free_disk":' in out, out[:300])
    check(i, "push to lima and pull back both succeed", exits[i] == 0, exits[i])
    check(i, "lima's round trip kept the heads", PULLED_HEADS in out, PULLED_HEADS)

    i = 10
    out, err = read_block(i)
    check(i, "apple-container is created running", '"name":"ac"' in out and '"state":"running"' in out, out[:600])
    check(i, "the second store is created and imported",
          '"name":"acshop"' in out and '"project":"acshop/web"' in out, out[:900])
    check(i, "push to apple-container succeeds", exits[i] == 0, err[-500:])

    i = 11
    out, err = read_block(i)
    check(i, "one pull lost the worker's answer", "lost the worker's answer" in out, out[-600:])
    check(i, "the loss is Unknown at send with the documented text",
          '"code":"Unknown"' in err and '"phase":"send"' in err and "answer was lost" in err, err[-600:])
    check(i, "status reads unresolved with an uncertain pull at send",
          '"state":"unresolved"' in out and '"name":"store.pull"' in out
          and '"phase":"send"' in out and '"uncertain":true' in out, out[-1200:])
    check(i, "the store still points at apple-container and keeps its copy",
          '"machine":"ac"' in out and '"bytes":68046848' in out.replace(" ", ""), out[-900:])
    check(i, "doctor reports it as an error and names the same pull as the fix",
          "unresolved store.pull" in out and "store pull acshop" in out, out[-1400:])
    check(i, "the block exits 0", exits[i] == 0, exits[i])

    i = 12
    out, err = read_block(i)
    refusal = last_json(err) or {}
    check(i, "the opposite direction is refused with exit 125", exits[i] == 125, exits[i])
    check(i, "the refusal is Unresolved and names the same pull as the clearing call",
          refusal.get("code") == "Unresolved" and "store pull acshop" in (refusal.get("message") or ""),
          json.dumps(refusal)[:600])

    i = 13
    out, err = read_block(i)
    check(i, "the same pull recovers", "recovered on attempt" in out, out[-400:])
    check(i, "status is idle on native", '"machine":"native"' in out and '"state":"idle"' in out, out[-500:])
    check(i, "the block exits 0", exits[i] == 0, exits[i])

    i = 14
    out, err = read_block(i)
    check(i, "store remove reports the removal", '"removed":"acshop"' in out, out[:300])
    listed = None
    for line in out.splitlines():
        if line.strip().startswith('{"stores"') or line.strip().startswith('{"items"'):
            try:
                listed = json.loads(line)
            except ValueError:
                listed = None
    names = [entry.get("name") for entry in ((listed or {}).get("stores") or (listed or {}).get("items") or [])]
    check(i, "the removed store is gone from store list", names and "acshop" not in names, names)
    check(i, "the block exits 0", exits[i] == 0, exits[i])

    i = 15
    out, err = read_block(i)
    check(i, "the kill landed while the push was sending",
          "progress events seen" in out and "store push" in out, out[:300])
    check(i, "status keeps the authority on native with a recorded intent",
          '"machine":"native"' in out and '"name":"store.push"' in out and '"op":null' not in out, out[:900])
    check(i, "the intent is certain, not uncertain", '"uncertain":false' in out, out[:700])
    check(i, "doctor names the partial copy on the machine and the push that replaces it",
          "partial copy" in out and "store push shop docker" in out, out[-1400:])
    check(i, "the block exits 0", exits[i] == 0, exits[i])

    i = 16
    out, err = read_block(i)
    check(i, "the same push recovers", exits[i] == 0, err[-400:])
    check(i, "the store is on docker with a retired transfer",
          '"machine":"docker"' in out and '"retired":true' in out, out[-800:])
    check(i, "status is idle again", '"state":"idle"' in out and '"op":null' in out, out[-400:])

    i = 17
    out, err = read_block(i)
    check(i, "the retire failure exits 125", "push exit=125" in out, out[:200])
    check(i, "the reply carries authority, source, retired:false and phase retire",
          '"code":"Failed"' in out and '"authority":"docker"' in out and '"source":"native"' in out
          and '"retired":false' in out and '"phase":"retire"' in out, out[-900:])
    check(i, "the message names the authority switch and the unretired source",
          "authority switched to docker" in out and "was not retired" in out, out[-900:])
    check(i, "store get names docker with retired:false",
          '"machine":"docker"' in out and '"retired":false' in out, out[-900:])
    check(i, "doctor warns about the copy the retire left",
          "did not retire" in out and "store pull locked" in out, out[-1000:])
    check(i, "the block exits 0", exits[i] == 0, exits[i])

    i = 18
    out, err = read_block(i)
    check(i, "the next pull deletes the leftover and succeeds", exits[i] == 0, err[-400:])
    check(i, "the store is back on native, idle", '"machine":"native"' in out and '"state":"idle"' in out,
          out[-400:])

    i = 19
    out, err = read_block(i)
    check(i, "store remove reports the removal", '"removed":"locked"' in out, out[:300])
    check(i, "the removed store is gone from store list", "locked" not in out.split('{"items"')[-1][:400],
          out[-600:])
    check(i, "doctor is clean", '"ok":true' in out and "locked" not in out.split('{"items"')[-1],
          out[-800:])
    check(i, "the block exits 0", exits[i] == 0, exits[i])

    i = 20
    out, err = read_block(i)
    listed = None
    for line in out.splitlines():
        if line.strip().startswith('{"machines"'):
            try:
                listed = json.loads(line)
            except ValueError:
                listed = None
    machine_names = [entry.get("name") for entry in ((listed or {}).get("machines") or [])]
    check(i, "the last store is removed", '"removed":"shop"' in out, out[:200])
    check(i, "only native and docker remain", machine_names == ["docker", "native"], machine_names)
    check(i, "docker is stopped", '"state":"stopped"' in out, out[-900:])
    check(i, "doctor ends clean", '"ok":true' in out, out[-400:])
    check(i, "the block exits 0", exits[i] == 0, exits[i])

    # ---- the home itself ---------------------------------------------------
    home = BASE / "guide-home"
    stores = sorted(p.name for p in (home / "store").glob("*")) if (home / "store").exists() else []
    checks = [row for row in RESULTS if "check" in row]
    passed = sum(1 for row in checks if row["ok"])
    receipt = {
        "guide": str(GUIDE),
        "home": str(home),
        "blocks": total,
        "seconds": seconds,
        "cli": CLI,
        "cli_sha256": __import__("hashlib").sha256(Path(CLI).read_bytes()).hexdigest(),
        "checks": checks,
        "passed": passed,
        "failed": len(checks) - passed,
        "exit_codes": exits,
        "leftover_store_records": stores,
        "verdict": "PASS" if passed == len(checks) else "FAIL",
    }
    (OUT / "guide-receipts.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=1))
    print(json.dumps({"blocks": total, "checks": len(checks), "passed": passed,
                      "failed": len(checks) - passed, "verdict": receipt["verdict"],
                      "seconds": seconds, "leftover": stores}, ensure_ascii=False))
    for row in checks:
        if not row["ok"]:
            print("FAIL block %d: %s | %s" % (row["block"], row["check"], row["evidence"][:300]))


if __name__ == "__main__":
    main()
