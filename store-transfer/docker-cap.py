import os
#!/usr/bin/env python3
"""LP08-FIX F1F2: the two Docker cases LP08-S2 left NOT_RUN, injected with a
tmpfs inside this home's docker worker rather than by filling a 30 GiB disk.

    R11-CAP-PRE-D    the `check` on the target's free disk refuses `Capacity`
    R11-ENOSPC-MID-D the `send` hits ENOSPC after the check passed

The first mounts a 1 GiB tmpfs where the target would write the Store, so the
target's own `statvfs` answers the free bytes. The second mounts a tmpfs big
enough for `check` to pass, then shrinks it (`remount,size=64m`) the instant
the send has written its first piece: the send then fails `ENOSPC`, which is
what LP08-S2 injected on lima and apple-container by filling their disks.

    python3 docker-cap.py cap         # R11-CAP-PRE-D
    python3 docker-cap.py enospc      # R11-ENOSPC-MID-D (after cap)
"""
import hashlib
import json
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

CLI = os.environ.get("LAYERFS_CLI", "layerfs")
HOME = Path(os.environ.get("LAYERFS_HOME", "/tmp/lp08-s2/home"))
REC = Path(os.environ.get("LP08_RECEIPTS", "./receipts/lp08-s2"))
STORE = "cap256"
MIB = 1 << 20
GIB = 1 << 30
CASES = {}


def env():
    return {**{k: v for k, v in __import__("os").environ.items()}, "LAYERFS_HOME": str(HOME)}


def cli(argv, timeout=1800):
    started = time.monotonic()
    done = subprocess.run([CLI] + argv, capture_output=True, text=True, env=env(), timeout=timeout)
    try:
        parsed = json.loads(done.stdout) if done.stdout.strip() else None
    except ValueError:
        parsed = None
    return {"argv": argv, "exit": done.returncode, "stdout": done.stdout.strip(),
            "stderr": done.stderr.strip(), "json": parsed,
            "seconds": round(time.monotonic() - started, 3)}


def refusal(result):
    for line in reversed(result["stderr"].splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if "code" in value:
                return value
    return None


def events(result):
    found = []
    for line in result["stderr"].splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                found.append(json.loads(line))
            except ValueError:
                pass
    return [e for e in found if "progress" in e]


def container():
    listed = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True,
                            check=True).stdout.split()
    for name in listed:
        if name.endswith("-docker") and HOME.exists() and name.startswith(
                "lfs-" + json.loads((HOME / "layerfs.json").read_text())["id"][:8]):
            return name
    raise SystemExit("no docker worker for this home: %s" % listed)


def guest(script, timeout=300):
    box = container()
    done = subprocess.run(["docker", "exec", box, "sh", "-c", script], capture_output=True, text=True,
                          timeout=timeout)
    return done.returncode, (done.stdout + done.stderr).strip()


def sha256_file(path):
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def store_sha(name=STORE):
    return sha256_file(HOME / "store" / name / "store.sqlite")


def status(name=STORE):
    return cli(["store", "status", name])["json"] or {}


def get(name=STORE):
    return cli(["store", "get", name])["json"] or {}


def case(cid, note=None):
    entry = CASES.setdefault(cid, {"case": cid, "checks": [], "notes": [], "commands": [], "measurements": {}})
    if note:
        entry["notes"].append(note)
    return entry


def check(cid, name, ok, evidence=""):
    CASES[cid]["checks"].append({"name": name, "ok": bool(ok), "evidence": str(evidence)[:1500]})
    print(("ok  " if ok else "FAIL"), cid, "-", name)


def mount_point(name=STORE):
    return "/layerfs/data/store/%s" % name


def mount(size, name=STORE):
    point = mount_point(name)
    return guest("mkdir -p %s && mount -t tmpfs -o size=%s tmpfs %s && df -Pk %s | tail -1"
                 % (point, size, point, point))


def unmount(name=STORE):
    point = mount_point(name)
    return guest("umount %s 2>/dev/null; rmdir %s 2>/dev/null; ls -a %s 2>&1 | head -3" % (point, point, point))


def df_available(name=STORE):
    code, out = guest("df -Pk %s | tail -1 | awk '{print $4}'" % mount_point(name))
    match = re.search(r"(\d+)", out)
    return (int(match.group(1)) * 1024) if (code == 0 and match) else None


def save():
    REC.mkdir(parents=True, exist_ok=True)
    for cid, entry in CASES.items():
        (REC / (cid + ".json")).write_text(json.dumps(entry, indent=1, ensure_ascii=False))


def cap():
    cid = "R11-CAP-PRE-D"
    case(cid, "docker: the 256 MiB Store's push is refused Capacity before any byte is sent, "
              "with the target's free disk read from a 1 GiB tmpfs where the Store would go")
    unmount()
    before = status()
    file = before.get("file") or {}
    bytes_held = (file.get("bytes") or 0) + (file.get("wal_bytes") or 0)
    sha_before = store_sha()
    code, out = mount("1g")
    check(cid, "the target's Store folder is a 1 GiB tmpfs", code == 0 and "tmpfs" in out, out[:300])
    free = df_available()
    needed = bytes_held + max(GIB, bytes_held // 10)
    pushed = cli(["store", "push", STORE, "docker", "--progress"])
    CASES[cid]["commands"].append(pushed)
    CASES[cid]["measurements"].update({"store_bytes_held": bytes_held, "needed": needed,
                                       "free": free, "df": out.strip()[:300]})
    bad = refusal(pushed) or {}
    detail = bad.get("detail") or {}
    progress = events(pushed)
    sent = [e for e in progress if (e.get("progress") or {}).get("phase") == "send"]
    check(cid, "the push is refused, exit 125 Capacity", pushed["exit"] == 125 and bad.get("code") == "Capacity",
          "exit %s %s" % (pushed["exit"], json.dumps(bad)[:400]))
    check(cid, "detail.needed is the Store's bytes plus max(1 GiB, bytes/10)", detail.get("needed") == needed,
          "%s vs %s" % (detail.get("needed"), needed))
    check(cid, "detail.free is the target's own df, byte for byte", detail.get("free") == free,
          "%s vs %s" % (detail.get("free"), free))
    check(cid, "the refusal names both numbers",
          "has %s bytes free" % detail.get("free") in (bad.get("message") or "")
          and "needs %s" % detail.get("needed") in (bad.get("message") or ""), (bad.get("message") or "")[:300])
    check(cid, "no byte was sent (no send event)", not sent, json.dumps(progress)[:300])
    code, out = guest("ls -a %s" % mount_point())
    check(cid, "the target wrote nothing there", "store.sqlite" not in out, out[:300])
    after = status()
    check(cid, "the source is untouched and idle",
          store_sha() == sha_before and (after.get("machine") == "native") and after.get("state") == "idle"
          and after.get("op") in (None, {}), json.dumps(after)[:300])
    unmount()
    save()


def enospc():
    cid = "R11-ENOSPC-MID-D"
    case(cid, "docker: the send runs into ENOSPC after check passed, deterministically, by shrinking "
              "the target's tmpfs to 64 MiB as soon as its first piece is written")
    unmount()
    before = status()
    file = before.get("file") or {}
    bytes_held = (file.get("bytes") or 0) + (file.get("wal_bytes") or 0)
    sha_before = store_sha()
    heads_before = (get().get("last_transfer") or {})
    # big enough for `check` (needs bytes + 1 GiB), small enough that the
    # shrink is the only reason the send stops
    code, out = mount("1500m")
    check(cid, "the target's Store folder is a 1500 MiB tmpfs, so check passes", code == 0, out[:300])
    armed = subprocess.Popen(
        ["docker", "exec", container(), "sh", "-c",
         "i=0; while [ $i -lt 600 ]; do if [ -s %s/store.sqlite.incoming ]; then "
         "size=$(stat -c %%s %s/store.sqlite.incoming); "
         "mount -o remount,size=64m %s && echo armed $size && exit 0; fi; "
         "i=$((i+1)); sleep 0.02; done; echo never-armed; exit 1"
         % (mount_point(), mount_point(), mount_point())],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    pushed = cli(["store", "push", STORE, "docker", "--progress"])
    armed_out = armed.communicate(timeout=120)[0] or ""
    CASES[cid]["commands"].append(pushed)
    progress = events(pushed)
    sent = [e["progress"] for e in progress if (e.get("progress") or {}).get("phase") == "send"]
    done = max([e.get("done") or 0 for e in sent], default=0)
    total = max([e.get("total") or 0 for e in sent], default=0)
    bad = refusal(pushed) or {}
    detail = bad.get("detail") or {}
    CASES[cid]["measurements"].update({"armed": armed_out.strip()[:300], "send_done": done, "send_total": total,
                                       "store_bytes_held": bytes_held})
    check(cid, "the tmpfs was shrunk at the first piece of the send", "armed" in armed_out,
          armed_out.strip()[:300])
    check(cid, "the send fails ENOSPC, a certain failure at send",
          pushed["exit"] == 125 and bad.get("code") == "Failed"
          and "No space left on device" in (bad.get("message") or "")
          and detail.get("phase") == "send", "exit %s %s" % (pushed["exit"], json.dumps(bad)[:400]))
    check(cid, "it stopped part way (done < total, and bytes had gone)", 0 < done < total,
          "%s of %s" % (done, total))
    after = status()
    check(cid, "the source's bytes and the record's owner are untouched",
          store_sha() == sha_before and after.get("machine") == "native", json.dumps(after)[:300])
    check(cid, "the target keeps the partial copy and no Store file",
          (guest("ls -a %s" % mount_point())[1].find("store.sqlite.incoming") >= 0)
          and guest("test -e %s/store.sqlite && echo yes || echo no" % mount_point())[1].strip() == "no",
          guest("ls -la %s | tail -3" % mount_point())[1][:300])
    # and the same command clears it and finishes once the disk is back
    unmount()
    again = cli(["store", "push", STORE, "docker", "--progress"])
    CASES[cid]["commands"].append(again)
    check(cid, "the same push after the disk is back succeeds", again["exit"] == 0, again["stderr"][:400])
    last = get().get("last_transfer") or {}
    code, out = guest("sha256sum /layerfs/data/store/%s/store.sqlite | awk '{print $1}'" % STORE)
    check(cid, "the copy on the target hashes to the record's sha256", out.split()[-1] == last.get("sha256"),
          "%s vs %s" % (out.strip()[-70:], last.get("sha256")))
    check(cid, "the heads are the ones before the failed send",
          (last.get("heads") or "") == (heads_before.get("heads") or "") or heads_before.get("heads") is None,
          "%s vs %s" % (last.get("heads"), heads_before.get("heads")))
    check(cid, "no stale .incoming is left", guest(
        "test -e /layerfs/data/store/%s/store.sqlite.incoming && echo yes || echo no" % STORE)[1].strip() == "no",
        guest("ls -a /layerfs/data/store/%s" % STORE)[1][:300])
    back = cli(["store", "pull", STORE])
    CASES[cid]["commands"].append(back)
    check(cid, "it comes back to native and the record names native again", back["exit"] == 0
          and status().get("machine") == "native", json.dumps(status())[:300])
    save()


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "cap"
    try:
        {"cap": cap, "enospc": enospc}[what]()
    finally:
        save()
        for cid, entry in sorted(CASES.items()):
            passed = sum(1 for c in entry["checks"] if c["ok"])
            print("%-20s %-5s %d/%d" % (cid, "PASS" if passed == len(entry["checks"]) else "FAIL",
                                        passed, len(entry["checks"])))
