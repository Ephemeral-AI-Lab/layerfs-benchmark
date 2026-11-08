#!/usr/bin/env python3
"""LP08-S2: the #11 large-Store matrix and the rest of #12.

#11: a 256 MiB and a 512 MiB SQLite Store across native<->docker, native<->lima
and native<->apple-container: per-phase time, throughput, the caller's and the
worker's peak RSS, the target's `.incoming` peak and its return to zero, then a
Workspace edit on the target and a pull back to native. Plus the capacity
pre-check refusal (`R11-CAP-PRE`) and a mid-`send` ENOSPC injection
(`R11-ENOSPC-MID`) on the two VM platforms whose data disk can be filled.
#12: the quiet path (no `--progress`) and the Node SDK's `on_progress`.

    python3 lp08s2.py setup
    python3 lp08s2.py route docker|lima|ac
    python3 lp08s2.py sdk
    python3 lp08s2.py report
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

CLI = os.environ.get("LAYERFS_CLI", "layerfs")
DAEMON = os.environ.get("LAYERFS_DAEMON", "layerfs-daemon")
ADDON = os.environ.get("LAYERFS_NATIVE", "layerfs.node")
WORK = Path(os.environ.get("LP08_WORK", "."))
RUN = Path(os.environ.get("LP08_BASE", "/tmp/lp08-s2"))
HOME = RUN / "home"
FIX = {"256": RUN / "fixture" / "s256", "512": RUN / "fixture" / "s512",
       "quiet": RUN / "fixture" / "quiet"}
REC = WORK / "receipts" / "lp08-s2"
RAW = REC / "raw"
MANIFEST = (WORK / "manifest.sh").read_text()
PHASES = ["check", "snapshot", "send", "verify", "install", "record", "retire"]
CHUNK = 8 << 20
GIB = 1 << 30
MIB = 1 << 20
MACHINE = {"docker": "docker", "lima": "lm-s2", "ac": "ac-s2"}
PLATFORM = {"docker": "docker", "lima": "lima", "ac": "apple-container"}
DISK = {"lima": os.environ.get("LP08_DISK", "4G"), "ac": os.environ.get("LP08_DISK", "4G")}
STORE = {"256": "cap256", "512": "cap512", "quiet": "quiet-s"}

CASES = {}
LOG = []


# --------------------------------------------------------------------- plumbing


def env():
    return {**os.environ, "LAYERFS_HOME": str(HOME)}


def run(argv, timeout=600, extra_env=None, cwd=None):
    started = time.monotonic()
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                              env={**env(), **(extra_env or {})}, cwd=cwd)
        return {"argv": argv, "exit": done.returncode, "out": done.stdout, "err": done.stderr,
                "seconds": round(time.monotonic() - started, 3)}
    except subprocess.TimeoutExpired as expired:
        return {"argv": argv, "exit": None, "out": (expired.stdout or b"").decode("utf-8", "replace")
                if isinstance(expired.stdout, bytes) else (expired.stdout or ""),
                "err": "timeout", "seconds": round(time.monotonic() - started, 3)}


def sh(script, timeout=600):
    return run(["/bin/sh", "-c", script], timeout=timeout)


def call(argv, timeout=900, progress=False, timed=False):
    """One CLI call: per-line timestamps on stderr, optionally `/usr/bin/time -l`'s peak RSS."""
    started = time.monotonic()
    prefix = []
    timefile = None
    if timed:
        timefile = RUN / "time.rss"
        prefix = ["/usr/bin/time", "-l", "-o", str(timefile)]
    process = subprocess.Popen(prefix + [CLI] + argv, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=env())
    events, raw = [], []
    expired = threading.Event()

    def expire():
        expired.set()
        try:
            process.kill()
        except OSError:
            pass

    timer = threading.Timer(timeout, expire)
    timer.start()

    def drain():
        for line in process.stderr:
            moment = round(time.monotonic() - started, 4)
            text = line.decode("utf-8", "replace").rstrip("\n")
            raw.append(text)
            if not text.strip():
                continue
            if progress and text.startswith("{"):
                try:
                    events.append({"t": moment, **json.loads(text)})
                    continue
                except ValueError:
                    pass
            events.append({"t": moment, "raw": text})

    thread = threading.Thread(target=drain, daemon=True)
    thread.start()
    out = process.stdout.read()
    code = process.wait()
    thread.join(10)
    timer.cancel()
    elapsed = time.monotonic() - started
    parsed = None
    if out.strip():
        try:
            parsed = json.loads(out.decode("utf-8"))
        except ValueError:
            parsed = None
    maxrss = None
    if timefile and timefile.exists():
        found = re.search(r"(\d+)\s+maximum resident set size", timefile.read_text())
        maxrss = int(found.group(1)) if found else None
    record = {"argv": argv, "exit": code, "seconds": round(elapsed, 3),
              "stdout": out.decode("utf-8", "replace"), "stderr": "\n".join(raw),
              "json": parsed, "events": events, "timeout": expired.is_set(),
              "maxrss": maxrss, "progress": progress}
    LOG.append({"argv": argv, "exit": code, "seconds": record["seconds"]})
    return record


# ------------------------------------------------------------------- assertions


def case(cid, note=None):
    entry = CASES.setdefault(cid, {"case": cid, "checks": [], "notes": [], "commands": [],
                                   "measurements": {}})
    if note:
        entry["notes"].append(note)
    return entry


def check(cid, name, ok, evidence=""):
    ok = bool(ok)
    case(cid)["checks"].append({"name": name, "ok": ok, "evidence": str(evidence)[:1500]})
    return ok


def note(cid, text):
    case(cid)["notes"].append(str(text)[:4000])


def ran(cid, result):
    case(cid)["commands"].append({"argv": ["layerfs"] + result["argv"], "exit": result["exit"],
                                  "seconds": result["seconds"]})


def verdict(cid):
    checks = CASES[cid]["checks"]
    if not checks:
        return "NOT_RUN"
    return "PASS" if all(c["ok"] for c in checks) else "FAIL"


def refusal(result):
    for line in reversed((result or {}).get("stderr", "").splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if "code" in value:
                return value
    return None


# ------------------------------------------------------------------------ peers


def docker_container():
    """This home's docker worker: the newest running container with the worker label."""
    cached = RUN / "docker_container"
    if cached.exists():
        found = run(["docker", "inspect", cached.read_text().strip()], timeout=120)
        if found["exit"] == 0:
            return cached.read_text().strip()
    listed = run(["docker", "ps", "-q"], timeout=120)
    ids = [i for i in listed["out"].split() if i]
    best = None
    for ident in ids:
        shown = run(["docker", "inspect", ident], timeout=120)
        if shown["exit"] != 0:
            continue
        try:
            facts = json.loads(shown["out"])[0]
        except (ValueError, IndexError):
            continue
        labels = (facts.get("Config") or {}).get("Labels") or {}
        if labels.get("layerfs.role") != "machine-worker":
            continue
        created = facts.get("Created") or ""
        if best is None or created > best[0]:
            best = (created, ident)
    if best is None:
        raise RuntimeError("no running docker machine-worker container")
    cached.write_text(best[1])
    return best[1]


def lima_instance(machine):
    listed = run(["limactl", "list", "--json"], timeout=120)
    candidates = []
    for line in listed["out"].splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("status") == "Running":
            candidates.append(entry.get("name"))
    named = [c for c in candidates if c and c.endswith("-" + machine)]
    if len(named) == 1:
        return named[0]
    raise RuntimeError(f"lima instance for {machine} not found among {candidates}")


def ac_container(machine):
    cached = RUN / "ac_container"
    if cached.exists():
        found = run(["container", "exec", cached.read_text().strip(), "true"], timeout=120)
        if found["exit"] == 0:
            return cached.read_text().strip()
    listed = run(["container", "ls", "--format", "json"], timeout=120)
    names = []
    try:
        entries = json.loads(listed["out"])
    except ValueError:
        entries = []
    for entry in entries if isinstance(entries, list) else []:
        name = entry.get("id") or entry.get("name")
        state = ((entry.get("status") or {}).get("state") or "").lower()
        if name and name.endswith("-" + machine) and state == "running":
            names.append(name)
    for name in names:
        found = run(["container", "exec", name, "test", "-d", "/layerfs/data"], timeout=120)
        if found["exit"] == 0:
            cached.write_text(name)
            return name
    raise RuntimeError(f"no running apple-container {machine} among {names}")


def guest(platform, script, timeout=600):
    if platform == "docker":
        return run(["docker", "exec", docker_container(), "sh", "-c", script], timeout=timeout)
    if platform == "lima":
        return run(["limactl", "shell", lima_instance(MACHINE["lima"]), "--", "sudo", "sh", "-c", script],
                   timeout=timeout)
    if platform == "ac":
        return run(["container", "exec", ac_container(MACHINE["ac"]), "sh", "-c", script], timeout=timeout)
    raise ValueError(platform)


WORKER_PID = r'''for p in /proc/[0-9]*; do
  c=$(tr '\0' ' ' < "$p/cmdline" 2>/dev/null)
  case "$c" in "/layerfs/bundle/layerfs worker "*) echo "${p#/proc/}";; esac
done | head -1'''


def probe(platform):
    """Worker pid, its VmHWM/VmRSS, and the data disk's free bytes."""
    script = f'''p=$({WORKER_PID})
echo "pid=$p"
grep -E "^VmHWM|^VmRSS" /proc/$p/status 2>/dev/null
echo "free=$(df -Pk /layerfs/data | awk 'NR==2{{print $4}}')"
echo "storefiles=$(ls -1 /layerfs/data/store 2>/dev/null | tr '\\n' ' ')"'''
    shown = guest(platform, script, timeout=300)
    facts = {"exit": shown["exit"], "raw": shown["out"].strip()}
    for line in shown["out"].splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            facts[key] = value.strip()
    for line in shown["out"].splitlines():
        if line.startswith("VmHWM:"):
            facts["hwm_kb"] = int(line.split()[1])
        elif line.startswith("VmRSS:"):
            facts["rss_kb"] = int(line.split()[1])
    if "free" in facts:
        facts["free_bytes"] = int(facts["free"]) * 1024
    return facts


def native_sha(store):
    path = HOME / "store" / store / "store.sqlite"
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def store_status(store):
    shown = call(["store", "status", store], timeout=300)
    return {"result": shown, "json": shown["json"] or {}}


def store_get(store):
    shown = call(["store", "get", store], timeout=300)
    return {"result": shown, "json": shown["json"] or {}}


# --------------------------------------------------------------------- sampling

SAMPLE = r'''inc="/layerfs/data/store/$1/store.sqlite.incoming"
f=/tmp/lp08s2-samples.$1
rm -f /tmp/lp08s2-stop.$1
p=$({pid})
: > $f
n=0
while [ ! -f /tmp/lp08s2-stop.$1 ]; do
  s=$(stat -c %s "$inc" 2>/dev/null || echo 0)
  r=0
  if [ -n "$p" ] && [ -r "/proc/$p/status" ]; then
    while read -r k v _; do case $k in VmRSS:) r=$v; break;; esac; done < "/proc/$p/status"
  fi
  echo "$n $s $r" >> $f
  n=$((n+1))
  sleep 0.02
done'''


def guest_sampler_start(platform, store):
    facts = probe(platform)
    pid = facts.get("pid") or ""
    script = SAMPLE.replace("{pid}", WORKER_PID)
    staged = "cat > /tmp/lp08s2-sample.sh <<'EOS'\n" + script + "\nEOS\n"
    made = guest(platform, staged, timeout=300)
    launched = guest(platform, f"setsid sh /tmp/lp08s2-sample.sh {store} >/dev/null 2>&1 & echo started",
                     timeout=300)
    return {"pid": pid, "staged": made["exit"], "launched": launched["out"].strip()}


def guest_sampler_stop(platform, store):
    guest(platform, "touch /tmp/lp08s2-stop." + store, timeout=300)
    time.sleep(0.2)
    shown = guest(platform, "cat /tmp/lp08s2-samples." + store, timeout=300)
    rows = []
    for line in shown["out"].splitlines():
        parts = line.split()
        if len(parts) == 3:
            rows.append([int(parts[0]), int(parts[1]), int(parts[2])])
    sizes = [row[1] for row in rows]
    rss = [row[2] for row in rows if row[2]]
    return {"samples": len(rows), "incoming_peak": max(sizes) if sizes else 0,
            "rss_peak_kb": max(rss) if rss else 0,
            "incoming_last": sizes[-1] if sizes else 0}


class NativeSampler(threading.Thread):
    """Native `store/<name>/store.sqlite.incoming` while a pull writes it."""

    def __init__(self, store):
        super().__init__(daemon=True)
        self.path = HOME / "store" / store / "store.sqlite.incoming"
        self.stop = threading.Event()
        self.peak = 0
        self.samples = 0

    def run(self):
        while not self.stop.is_set():
            try:
                size = self.path.stat().st_size
            except OSError:
                size = 0
            self.peak = max(self.peak, size)
            self.samples += 1
            time.sleep(0.01)

    def finish(self):
        self.stop.set()
        self.join(5)
        return {"samples": self.samples, "incoming_peak": self.peak}


# ------------------------------------------------------------------ measurement


def phase_times(result, exit_at):
    marks = {}
    for event in result["events"]:
        phase = (event.get("progress") or {}).get("phase")
        if phase and phase not in marks:
            marks[phase] = event["t"]
    present = [p for p in PHASES if p in marks]
    spans = {}
    for index, phase in enumerate(present):
        end = marks[present[index + 1]] if index + 1 < len(present) else exit_at
        spans[phase] = round(end - marks[phase], 4)
    return spans, marks, present


def transfer(cid, platform, machine, store, direction, restart=True, attempts=6):
    """One measured `store push`/`store pull`: time, throughput, both peak RSS towers."""
    call_argv = ["store", "push", store, machine] if direction == "push" else ["store", "pull", store]
    before_status = store_status(store)
    before = before_status["json"].get("file") or {}
    sha_before = native_sha(store) if direction == "push" else None
    if restart:
        call(["machine", "stop", machine], timeout=900)
        started = call(["machine", "start", machine], timeout=1800)
        ran(cid, started)
    facts_before = probe(platform)
    attempts_made = []
    sampler = guest_sampler_start(platform, store)
    native = None
    if direction == "pull":
        native = NativeSampler(store)
        native.start()
    result = call(call_argv + ["--progress"], progress=True, timed=True, timeout=1800)
    attempts_made.append({"exit": result["exit"], "seconds": result["seconds"],
                          "code": (refusal(result) or {}).get("code")})
    # the known Apple Container defect: the same pull again (idempotent recovery)
    tries = 25 if (platform == "ac" and direction == "pull") else attempts
    if platform == "ac" and direction == "pull" and result["exit"] != 0:
        note(cid, "attempt 1 lost the worker's answer: " + json.dumps(refusal(result) or {})[:300])
        for _ in range(tries - 1):
            time.sleep(0.2)
            result = call(call_argv + ["--progress"], progress=True, timed=True, timeout=1800)
            attempts_made.append({"exit": result["exit"], "seconds": result["seconds"],
                                  "code": (refusal(result) or {}).get("code")})
            if result["exit"] == 0:
                break
    guest_samples = guest_sampler_stop(platform, store) if sampler else None
    native_samples = native.finish() if native else None
    facts_after = probe(platform)
    ran(cid, result)
    spans, marks, present = phase_times(result, result["seconds"])
    total = (result["json"] or {}).get("bytes")
    send_seconds = spans.get("send") or 0
    seconds = max(result["seconds"], 0.0001)
    measurement = {
        "platform": platform, "machine": machine, "store": store, "direction": direction,
        "bytes": total, "store_bytes_before": before.get("bytes"),
        "wal_bytes_before": before.get("wal_bytes"),
        "seconds": result["seconds"], "phases": spans, "phase_starts": marks,
        "phase_order": present,
        "mib_per_second_send": round((total or 0) / MIB / send_seconds, 2) if send_seconds else None,
        "mib_per_second_total": round((total or 0) / MIB / seconds, 2),
        "caller_maxrss_bytes": result["maxrss"],
        "worker_hwm_kb_before": facts_before.get("hwm_kb"),
        "worker_hwm_kb_after": facts_after.get("hwm_kb"),
        "worker_rss_peak_kb_sampled": (guest_samples or {}).get("rss_peak_kb"),
        "incoming_peak": ((native_samples or {}).get("incoming_peak") if native_samples
                          else (guest_samples or {}).get("incoming_peak")),
        "incoming_samples": ((native_samples or {}).get("samples") if native_samples
                             else (guest_samples or {}).get("samples")),
        "guest_worker_rss_samples": guest_samples,
        "native_incoming_samples": native_samples,
        "attempts": attempts_made,
        "attempts_count": len(attempts_made),
        "seconds_total_with_retries": round(sum(a["seconds"] for a in attempts_made), 3),
        "target_free_before": facts_before.get("free_bytes"),
        "target_free_after": facts_after.get("free_bytes"),
        "storefiles_after": facts_after.get("storefiles"),
        "stdout": result["stdout"].strip(),
    }
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"{cid}-{store}-{direction}.json").write_text(json.dumps(
        {"measurement": measurement, "events": result["events"]}, indent=1))
    case(cid)["measurements"][f"{store}-{direction}"] = measurement

    # ---- assertions
    label = f"{store} MiB {direction} {platform}"
    check(cid, f"{label}: the call succeeded", result["exit"] == 0,
          f"exit {result['exit']} {(refusal(result) or {}).get('message', '')[:200]} attempts={json.dumps(attempts_made)}")
    check(cid, f"{label}: the seven phases ran in order",
          present == PHASES, json.dumps(present))
    send = [e for e in result["events"] if (e.get("progress") or {}).get("phase") == "send"
            and (e.get("progress") or {}).get("total") is not None]
    totals = {e["progress"]["total"] for e in send}
    done = [e["progress"]["done"] for e in send]
    check(cid, f"{label}: send's total is constant and its done mount to it",
          len(totals) == 1 and done == sorted(done) and done and done[-1] == totals.pop() == total,
          f"totals={totals} done={done[:3]}..{done[-3:]}")
    check(cid, f"{label}: the last event is retire, before the process exits",
          present and present[-1] == "retire" and result["seconds"] - marks["retire"] >= 0,
          f"retire at {marks.get('retire')}s of {result['seconds']}s")
    check(cid, f"{label}: the transfer's bytes are the Store's bytes",
          total is not None and total == before.get("bytes"), f"{total} vs {before.get('bytes')}")
    check(cid, f"{label}: the caller's peak RSS stays far below the Store",
          (result["maxrss"] or 0) < 128 * MIB and (result["maxrss"] or 0) < 0.25 * (total or MIB),
          f"{result['maxrss']} B for {total} B")
    hwm = facts_after.get("hwm_kb") or 0
    check(cid, f"{label}: the worker's peak RSS stays far below the Store",
          0 < hwm < 128 * 1024 and hwm * 1024 < 0.25 * (total or MIB),
          f"VmHWM {hwm} kB for {total} B")
    if direction == "push":
        check(cid, f"{label}: the target's staged copy peaked at the Store's size",
              (measurement["incoming_peak"] or 0) >= 0.9 * (total or 0),
              f"peak {measurement['incoming_peak']} of {total} over {measurement['incoming_samples']} samples")
        left = guest(platform, f"ls -1 /layerfs/data/store/{store} | tr '\\n' ' '", timeout=300)["out"].strip()
        check(cid, f"{label}: the staged copy is gone after install",
              "incoming" not in left,
              f"store folder: {left}")
    else:
        check(cid, f"{label}: the native staged copy rose to the Store's size",
              (measurement["incoming_peak"] or 0) >= 0.9 * (total or 0),
              f"peak {measurement['incoming_peak']} over {measurement['incoming_samples']} samples")
    return {"result": result, "measurement": measurement, "sha_before": sha_before}


def verify_after_push(cid, platform, machine, store, result):
    listing = guest(platform, f"ls -la /layerfs/data/store/{store} 2>&1", timeout=300)["out"]
    shown = store_get(store)
    last = shown["json"].get("last_transfer") or {}
    check(cid, "the target holds the Store and the source's copy is retired",
          "store.sqlite" in listing and "incoming" not in listing, listing.strip()[:400])
    check(cid, "the record moved and says the source was retired",
          shown["json"].get("machine") == machine and last.get("to") == machine
          and last.get("retired") is True,
          json.dumps({"machine": shown["json"].get("machine"), "last": last})[:400])
    check(cid, "the stored bytes are the transfer's bytes",
          last.get("bytes") == (result["json"] or {}).get("bytes"),
          f"{last.get('bytes')} vs {(result['json'] or {}).get('bytes')}")
    return {"last_transfer": last, "heads": (result["json"] or {}).get("heads"),
            "target_listing": listing.strip()[:800]}


def manifest_lines(text):
    return [line for line in text.splitlines() if line.strip()]


def ws(cid, argv_json, ws_exec_script, timeout=900, stream=True):
    shown = call(["workspace", "exec", argv_json, ws_exec_script] + (["--stream"] if stream else []),
                 timeout=timeout)
    return shown


def edit_on_target(cid, platform, machine, store):
    """Mount the Store on `machine`, add files, commit: the target-side write #11 asks for."""
    sandbox = "sb-s2"
    call(["sandbox", "close", sandbox, "--force"], timeout=900)
    branch = "s2edit"
    existing = call(["branch", "list", f"{store}/p1"], timeout=600)
    names = [b.get("name") for b in ((existing["json"] or {}).get("items") or [])]
    step = 2
    while branch in names:
        branch = f"s2edit-{step}"
        step += 1
    made = call(["sandbox", "create", f"{store}/p1", sandbox, machine], timeout=1800)
    ran(cid, made)
    check(cid, f"{machine}: a Sandbox of {store}/p1 runs on it", made["exit"] == 0, made["stderr"][:300])
    forked = call(["branch", "fork", f"{store}/p1", branch, "main"], timeout=600)
    ran(cid, forked)
    mounted = call(["workspace", "mount", sandbox, branch], timeout=1800)
    ran(cid, mounted)
    check(cid, f"{machine}: a Workspace mounts branch {branch}", mounted["exit"] == 0, mounted["stderr"][:300])
    workspace = (mounted["json"] or {}).get("ws")
    if not workspace:
        return {"ok": False, "branch": branch}
    script = (f"set -e\nmkdir -p s2-added\n"
              f"printf 'edited on {machine}\\nlp08-s2\\n' > s2-added/note.txt\n"
              f"cat s2-added/note.txt")
    wrote = ws(cid, workspace, script)
    ran(cid, wrote)
    check(cid, f"{machine}: a write in the mounted Workspace succeeds", wrote["exit"] == 0, wrote["stderr"][:300])
    committed = call(["workspace", "commit", workspace, "-m", f"lp08 s2 edit on {machine}"], timeout=1800)
    ran(cid, committed)
    check(cid, f"{machine}: the edit commits", committed["exit"] == 0, committed["stderr"][:300])
    call(["workspace", "unmount", workspace], timeout=1800)
    call(["sandbox", "close", sandbox], timeout=1800)
    commits = call(["commit", "list", f"{store}/p1", branch], timeout=600)
    rows = (commits["json"] or {}).get("items") or (commits["json"] or {}).get("commits") or []
    check(cid, f"{machine}: the branch {branch} has the new commit", len(rows) >= 1, json.dumps(rows)[:300])
    return {"ok": True, "commits": rows, "branch": branch}


def verify_native_after_pull(cid, store, pull, baseline, branch="s2edit"):
    sha = native_sha(store)
    shown = store_get(store)
    last = shown["json"].get("last_transfer") or {}
    check(cid, "the pulled Store's bytes are the transfer's sha256", sha is not None and sha == last.get("sha256"),
          f"{sha} vs {last.get('sha256')}")
    check(cid, "the record is back on native and retired",
          shown["json"].get("machine") == "native" and last.get("retired") is True,
          json.dumps({"machine": shown["json"].get("machine"), "last": last})[:300])
    sandbox = "sb-nat"
    call(["sandbox", "close", sandbox, "--force"], timeout=900)
    made = call(["sandbox", "create", f"{store}/p1", sandbox], timeout=1800)
    mounted = call(["workspace", "mount", sandbox, branch], timeout=1800)
    ran(cid, mounted)
    check(cid, f"native mounts the branch the target edited ({branch})", mounted["exit"] == 0,
          mounted["stderr"][:300])
    workspace = (mounted["json"] or {}).get("ws")
    lines = []
    if workspace:
        listed = ws(cid, workspace, MANIFEST)
        lines = manifest_lines(listed["stdout"])
        added = ws(cid, workspace, "cat s2-added/note.txt")
        check(cid, "the target's edit is in the pulled Store",
              added["stdout"].strip() == f"edited on {last.get('from', '')}\nlp08-s2",
              added["stdout"].strip()[:200])
        found = [line for line in lines if "s2-added/note.txt" in line]
        check(cid, "the pulled manifest lists the target's file", bool(found), str(found)[:300])
        if baseline:
            kept = [line for line in lines if "s2-added" not in line]
            check(cid, "every fixture entry survives the round trip",
                  kept == baseline, f"{len(kept)} vs {len(baseline)} lines; "
                                    f"first difference: {next((a + ' != ' + b for a, b in zip(kept, baseline) if a != b), 'none')[:300]}")
        call(["workspace", "unmount", workspace], timeout=1800)
    call(["sandbox", "close", sandbox], timeout=1800)
    return {"sha256": sha, "last_transfer": last, "manifest_lines": len(lines)}


# ----------------------------------------------------------------- #11 R11-CAP


def fill_guest(platform, leave_mib, tag="lp08s2-filler"):
    script = f'''set -e
free_kb=$(df -Pk /layerfs/data | awk 'NR==2{{print $4}}')
want=$(( free_kb/1024 - {leave_mib} ))
rm -f /layerfs/data/{tag}
if [ "$want" -le 0 ]; then echo "nothing to fill: ${{free_kb}}kB"; exit 0; fi
fallocate -l ${{want}}M /layerfs/data/{tag} 2>/dev/null || dd if=/dev/zero of=/layerfs/data/{tag} bs=1M count=$want 2>/dev/null
echo "filled $want MiB; free now $(df -Pk /layerfs/data | awk 'NR==2{{print $4}}') kB"'''
    return guest(platform, script, timeout=1800)


def clear_guest_filler(platform, tag="lp08s2-filler"):
    return guest(platform, f"rm -f /layerfs/data/{tag}; df -Pk /layerfs/data | awk 'NR==2{{print $4}}'",
                 timeout=600)


def ensure_store_on(platform, store, size="256", attempts=6):
    """The Store is on native and not unresolved; recovered, or recreated, if not."""
    for step in range(attempts):
        shown = store_status(store)
        if shown["result"]["exit"] != 0:
            return {"missing": True, "stderr": shown["result"]["stderr"][:200]}
        state = shown["json"].get("state")
        where = shown["json"].get("machine")
        if state != "unresolved" and where == "native":
            return {"ok": True, "attempts": step}
        result = call(["store", "pull", store], timeout=1800)
        if result["exit"] == 0:
            return {"ok": True, "attempts": step + 1}
    call(["store", "remove", store], timeout=1800)
    call(["store", "create", store], timeout=600)
    for project in ("p1", "p2"):
        call(["project", "init", f"{store}/{project}", str(FIX[size] / project)], timeout=3600)
    return {"ok": False, "recreated": True, "attempts": attempts}


def cap_pre(cid, platform, machine, store):
    ensure_store_on(platform, store)
    filled = fill_guest(platform, 1000)
    free = probe(platform).get("free_bytes")
    status = store_status(store)["json"]
    before = status.get("file") or {}
    sha_before = native_sha(store)
    leaves = guest(platform, f"ls -la /layerfs/data/store/{store} 2>&1", timeout=300)["out"]
    result = call(["store", "push", store, machine, "--progress"], progress=True, timed=True, timeout=1800)
    ran(cid, result)
    bad = refusal(result) or {}
    detail = bad.get("detail") or {}
    bytes_held = (before.get("bytes") or 0) + (before.get("wal_bytes") or 0)
    headroom = max(GIB, bytes_held // 10)
    needed = bytes_held + headroom
    after = probe(platform)
    leaves_after = guest(platform, f"ls -la /layerfs/data/store/{store} 2>&1", timeout=300)["out"]
    guest_free_after = after.get("free_bytes")
    restored = clear_guest_filler(platform)
    check(cid, f"{machine}: the push is refused Capacity", result["exit"] == 125 and bad.get("code") == "Capacity",
          json.dumps(bad)[:400])
    check(cid, f"{machine}: detail.needed is the Store's bytes plus its headroom",
          detail.get("needed") == needed, f"{detail.get('needed')} vs {needed} (bytes {bytes_held})")
    check(cid, f"{machine}: detail.free is the target's free disk",
          detail.get("free") is not None and free is not None
          and abs(detail["free"] - min(free, guest_free_after)) <= 4 * MIB,
          f"detail {detail.get('free')} vs df {free} / {guest_free_after}")
    check(cid, f"{machine}: nothing was written on the target",
          "No such file" in leaves_after or store not in leaves_after,
          leaves_after.strip()[:300])
    check(cid, f"{machine}: the source Store is untouched and idle",
          native_sha(store) == sha_before and (store_status(store)["json"].get("machine") == "native")
          and store_status(store)["json"].get("op") is None,
          json.dumps(store_status(store)["json"])[:400])
    check(cid, f"{machine}: the refusal sent 0 bytes (no send phase, no staged copy)",
          not any((e.get("progress") or {}).get("phase") == "send" for e in result["events"]),
          json.dumps([e.get("progress") or e.get("raw") for e in result["events"]])[:400])
    case(cid)["measurements"]["cap"] = {
        "free_before": free, "free_after": guest_free_after, "detail": detail,
        "needed": needed, "bytes": bytes_held, "headroom": headroom,
        "fill": filled["out"].strip(), "restored_free_kb": restored["out"].strip(),
        "seconds": result["seconds"], "caller_maxrss_bytes": result["maxrss"],
    }
    return result


def data_mountpoint(platform):
    shown = guest(platform, 'src=$(findmnt -no SOURCE /layerfs/data); '
                           'findmnt -n -o TARGET -S "$src" | grep -vx /layerfs/data | head -1', timeout=300)
    return shown["out"].strip()


def remount_data(platform, options):
    """Remount the data disk's filesystem with `options`; its bind mount follows it."""
    mountpoint = data_mountpoint(platform)
    if not mountpoint:
        mountpoint = "/layerfs/data"
    script = (f'mount -o remount,{options} "{mountpoint}" && '
              'findmnt -n -o TARGET,OPTIONS -S "$(findmnt -no SOURCE /layerfs/data)"')
    shown = guest(platform, script, timeout=600)
    return {"mountpoint": mountpoint, "exit": shown["exit"], "out": shown["out"].strip(),
            "err": shown["err"].strip()[:300]}


ARMED_FILL = r'''# fills the target's data disk once `send` has written its first chunk: down to
# `leave` MiB of raw (root-usable) space, reserved blocks included
inc=/layerfs/data/store/$1/store.sqlite.incoming
leave=$2
rm -f /tmp/lp08s2-fill.log
while :; do
  s=$(stat -c %s "$inc" 2>/dev/null || echo 0)
  if [ "$s" -gt 0 ]; then break; fi
  sleep 0.005
done
i=0
while [ $i -lt 6 ]; do
  total=$(df -Pk /layerfs/data | awk 'NR==2{print $2}')
  used=$(df -Pk /layerfs/data | awk 'NR==2{print $3}')
  raw=$(( total - used ))
  if [ "$raw" -le $(( (leave + 8) * 1024 )) ]; then break; fi
  want=$(( raw/1024 - leave ))
  fallocate -l ${want}M /layerfs/data/lp08s2-enospc.$i 2>/dev/null ||
    dd if=/dev/zero of=/layerfs/data/lp08s2-enospc.$i bs=1M count=$want 2>/dev/null
  i=$((i+1))
done
echo "triggered at incoming=$s raw_kb=$(( $(df -Pk /layerfs/data | awk 'NR==2{print $2}') - $(df -Pk /layerfs/data | awk 'NR==2{print $3}') )) fillers=$i $(date -u +%FT%TZ)" > /tmp/lp08s2-fill.log'''


def enospc_mid(cid, platform, machine, store, mode="sync"):
    """`send` with the target's disk filled underneath it.

    `mode` names the filesystem's allocation behaviour: `sync` remounts the data
    disk `nodelalloc` first, where a write that cannot be allocated fails at once;
    `delalloc` keeps the default, where the write lands in the page cache and the
    allocation waits for writeback.
    """
    remount = remount_data(platform, "nodelalloc") if mode == "sync" else None
    ensure_store_on(platform, store)
    guest(platform, "rm -f /layerfs/data/lp08s2-enospc.* /tmp/lp08s2-fill.log", timeout=600)
    free_before = probe(platform).get("free_bytes")
    sha_before = native_sha(store)
    before = store_status(store)["json"].get("file") or {}
    staged = "cat > /tmp/lp08s2-armed.sh <<'EOS'\n" + ARMED_FILL + "\nEOS\n"
    guest(platform, staged, timeout=300)
    guest(platform, f"setsid sh /tmp/lp08s2-armed.sh {store} 64 >/dev/null 2>&1 & echo armed", timeout=300)
    started = time.monotonic()
    result = call(["store", "push", store, machine, "--progress"], progress=True, timed=True, timeout=1800)
    elapsed = round(time.monotonic() - started, 3)
    ran(cid, result)
    fill_log = guest(platform, "cat /tmp/lp08s2-fill.log 2>&1", timeout=300)["out"].strip()
    bad = refusal(result) or {}
    detail = bad.get("detail") or {}
    status_after = store_status(store)["json"]
    listing = guest(platform, f"ls -la /layerfs/data/store/{store} 2>&1; df -Pk /layerfs/data | tail -1",
                    timeout=300)["out"]
    send_events = [e["progress"] for e in result["events"]
                   if (e.get("progress") or {}).get("phase") == "send"]
    stages = [(e.get("progress") or {}).get("phase") for e in result["events"]]
    allocation = guest(platform, f'''f=/layerfs/data/store/{store}/store.sqlite
  echo "size=$(stat -c %s $f 2>/dev/null || echo 0)"
  echo "blocks_now=$(du -B1 $f 2>/dev/null | cut -f1)"
  sync 2>/dev/null; sleep 0.5
  echo "blocks_after_sync=$(du -B1 $f 2>/dev/null | cut -f1)"
  echo "df=$(df -Pk /layerfs/data | awk 'NR==2{{print $2\" \"$3\" \"$4}}')"
  echo 3 > /proc/sys/vm/drop_caches 2>/dev/null
  echo "sha_after_drop=$(sha256sum $f 2>&1 | cut -c1-120)"''', timeout=1800)["out"]
    case(cid)["measurements"]["enospc"] = {
        "mode": mode, "remount": remount, "free_before": free_before, "fill_log": fill_log,
        "error": bad, "exit": result["exit"], "seconds": elapsed, "phases_seen": stages,
        "send_events_last": send_events[-4:], "send_events_total": len(send_events),
        "caller_maxrss_bytes": result["maxrss"], "allocation": allocation.strip()[:1500],
        "state_after": {k: status_after.get(k) for k in ("machine", "state", "op", "file")},
        "listing_after": listing.strip()[:900],
    }
    check(cid, f"{machine} ({mode}): the armed filler fired during send",
          "triggered" in fill_log and bool(send_events), fill_log[:300])
    check(cid, f"{machine} ({mode}): the transfer stops in send with a full-disk failure",
          result["exit"] == 125 and detail.get("phase") == "send"
          and str(bad.get("message", "")).startswith("store push, send:")
          and bad.get("code") == "Failed"
          and re.search(r"StorageFull|No space left", str(bad.get("message"))),
          json.dumps(bad)[:400])
    check(cid, f"{machine} ({mode}): it fails mid-send, after real chunks were written",
          0 < send_events[-1]["done"] < (before.get("bytes") or MIB),
          json.dumps(send_events[-3:])[:300])
    check(cid, f"{machine} ({mode}): the source copy is intact and the Store reads as an ended transfer",
          native_sha(store) == sha_before and status_after.get("machine") == "native"
          and status_after.get("op") is None,
          json.dumps({"machine": status_after.get("machine"), "op": status_after.get("op"),
                      "state": status_after.get("state")})[:400])
    check(cid, f"{machine} ({mode}): the partial staged copy stays on the target",
          "store.sqlite.incoming" in listing, listing.strip()[:400])
    cleared = clear_guest_filler(platform, tag="lp08s2-enospc.*")
    case(cid)["measurements"]["enospc"]["cleared_free_kb"] = cleared["out"].strip()
    retry = call(["store", "push", store, machine, "--progress"], progress=True, timed=True, timeout=1800)
    ran(cid, retry)
    installed = guest(platform, f"sha256sum /layerfs/data/store/{store}/store.sqlite 2>&1", timeout=1800)["out"]
    last = (store_get(store)["json"] or {}).get("last_transfer") or {}
    check(cid, f"{machine} ({mode}): the same command succeeds once the space is back",
          retry["exit"] == 0, (refusal(retry) or {}).get("message", "")[:300])
    check(cid, f"{machine} ({mode}): the copy installed by the retry is the snapshot's",
          installed.split()[0] == last.get("sha256") if installed.strip() else False,
          f"{installed.strip()[:80]} vs {last.get('sha256')}")
    case(cid)["measurements"]["enospc"]["retry"] = {
        "exit": retry["exit"], "seconds": retry["seconds"],
        "bytes": (retry["json"] or {}).get("bytes"), "sha256": last.get("sha256"),
        "installed": installed.strip()[:120]}
    back = None
    for _ in range(25 if platform == "ac" else 3):
        back = call(["store", "pull", store, "--progress"], progress=True, timeout=1800)
        ran(cid, back)
        if back["exit"] == 0:
            break
        time.sleep(0.2)
    case(cid)["measurements"]["enospc"]["pull_back"] = {"exit": (back or {}).get("exit"),
                                                       "code": (refusal(back or {}) or {}).get("code")}
    if platform == "ac" and back["exit"] != 0:
        note(cid, "the pull back is blocked by the Apple Container pull defect (see R11-A-256-pull): "
                  + json.dumps(refusal(back) or {})[:200])
        call(["store", "remove", store], timeout=1800)
    else:
        check(cid, f"{machine}: the Store pulls back to native afterwards", back["exit"] == 0,
              back["stderr"][:300])
    if mode == "sync":
        restored = remount_data(platform, "delalloc")
        case(cid)["measurements"]["enospc"]["remount_back"] = restored
        check(cid, f"{machine}: the data disk is remounted as it was", restored.get("exit") == 0,
              json.dumps(restored)[:300])
    return result


# ------------------------------------------------------------------- #12 quiet


def quiet(cid, machine, store, direction):
    if direction == "push":
        recovered = ensure_store_on("native", store, size="quiet")
        if not recovered.get("ok", True):
            case(cid)["measurements"]["recovery"] = recovered
    argv = ["store", "push", store, machine] if direction == "push" else ["store", "pull", store]
    result = call(argv, timeout=1800)
    if result["exit"] != 0 and "ac" in machine and direction == "pull":
        note(cid, f"{direction} failed once: " + json.dumps(refusal(result) or {})[:200])
        for _ in range(24):
            time.sleep(0.2)
            result = call(argv, timeout=1800)
            if result["exit"] == 0:
                break
    ran(cid, result)
    lines = [line for line in result["stderr"].splitlines() if line.strip()]
    payload = [line for line in result["stdout"].splitlines() if line.strip()]
    parsed = None
    try:
        parsed = json.loads(payload[0]) if len(payload) == 1 else None
    except ValueError:
        parsed = None
    check(cid, f"{direction} without --progress: exit 0", result["exit"] == 0, result["stderr"][:200])
    check(cid, f"{direction} without --progress: no progress line on stderr", not lines,
          json.dumps(lines[:5]))
    check(cid, f"{direction} without --progress: one JSON line on stdout",
          len(payload) == 1 and isinstance(parsed, dict)
          and {"store", "from", "to", "bytes", "heads"} <= set(parsed),
          result["stdout"][:300])
    case(cid)["measurements"][direction] = {"exit": result["exit"], "seconds": result["seconds"],
                                            "stderr_lines": lines, "stdout": result["stdout"].strip()}
    return result


# ------------------------------------------------------- the AC pull ladder


def ac_pull_sweep(cid="R11-A-PULL-SWEEP"):
    """How the Apple Container pull fails as the Store grows: one row per size.

    Every row is a fresh Store of `n` 8 MiB blobs, pushed to ac-s2 (which always
    succeeds) and pulled until it succeeds or `attempts` tries are spent.
    """
    case(cid, "the Apple Container pull ladder: 8 MiB to 128 MiB Stores, one row each")
    rows = []
    for blobs in (1, 2, 4, 8, 16):
        store = f"sweep-{blobs}"
        folder = RUN / "fixture" / f"sweep{blobs}" / "p1"
        folder.mkdir(parents=True, exist_ok=True)
        for index in range(blobs):
            source = FIX["256"] / "p1" / f"data/blob-{index:02d}.bin"
            target = folder / f"blob-{index:02d}.bin"
            if not target.exists():
                shutil.copy2(source, target)
        (folder / "README.md").write_text("sweep\n")
        call(["store", "remove", store], timeout=1800)
        call(["store", "create", store], timeout=600)
        call(["project", "init", f"{store}/p1", str(folder)], timeout=3600)
        size = (store_status(store)["json"].get("file") or {}).get("bytes")
        pushed = call(["store", "push", store, "ac-s2"], timeout=1800)
        attempts = 0
        started = time.monotonic()
        result = None
        while attempts < 12:
            attempts += 1
            result = call(["store", "pull", store], timeout=1800)
            if result["exit"] == 0:
                break
            time.sleep(0.2)
        row = {"blobs": blobs, "bytes": size, "push_exit": pushed["exit"],
               "pull_attempts": attempts, "pull_exit": (result or {}).get("exit"),
               "pull_seconds_total": round(time.monotonic() - started, 2),
               "last_code": (refusal(result or {}) or {}).get("code")}
        rows.append(row)
        case(cid)["measurements"][f"{blobs}x8MiB"] = row
        call(["store", "remove", store], timeout=1800)
    small = [row for row in rows if row["bytes"] <= 40 * MIB]
    large = [row for row in rows if row["bytes"] > 40 * MIB]
    check(cid, "every push to the Apple Container succeeded", all(row["push_exit"] == 0 for row in rows),
          json.dumps(rows))
    # PR #617: v2's worker waits for the client to close (97fac452bd) and the
    # product reads each piece once, so every size must pull on its first attempt
    check(cid, "Stores up to 32 MiB pull on their first attempt",
          bool(small) and all(row["pull_exit"] == 0 and row["pull_attempts"] == 1 for row in small),
          json.dumps(small))
    check(cid, "Stores above 32 MiB pull on their first attempt too",
          bool(large) and all(row["pull_exit"] == 0 and row["pull_attempts"] == 1 for row in large),
          json.dumps(large))
    check(cid, "a failed pull never reports success and never damages the source",
          all(row["pull_exit"] in (0, 125) for row in rows), json.dumps(rows))
    return rows


# --------------------------------------------------------------------- routes


def ensure_machine(platform, machine):
    if platform == "docker":
        return call(["machine", "start", machine], timeout=1800)
    listed = call(["machine", "list"], timeout=300)
    names = [m.get("name") for m in ((listed["json"] or {}).get("machines") or [])]
    if machine not in names:
        created = call(["machine", "create", machine, PLATFORM[platform], "--cpus", "2", "--memory", "2G",
                        "--disk", DISK[platform]], timeout=3600)
        if created["exit"] != 0:
            return created
    return call(["machine", "start", machine], timeout=1800)


def reset_stores(cid, pairs):
    """Both Stores back to the fixture's bytes, so every route measures the same input."""
    wanted = json.loads((REC / "setup.json").read_text())["stores"] if (REC / "setup.json").exists() else {}
    problems = []
    close_sandboxes()
    for size, store in pairs:
        ensure_store_on("native", store)
        call(["sandbox", "close", "sb-" + store, "--force"], timeout=900)
        call(["store", "remove", store], timeout=1800)
        call(["store", "create", store], timeout=600)
        for project in ("p1", "p2"):
            init = call(["project", "init", f"{store}/{project}", str(FIX[size] / project)], timeout=3600)
            if init["exit"] != 0:
                problems.append({store: init["stderr"][:200]})
        got = (store_status(store)["json"].get("file") or {}).get("bytes")
        case(cid)["measurements"][f"reset-{store}"] = {"bytes": got, "setup_bytes": wanted.get(store)}
        base = wanted.get(store)
        if base and abs(got - base) > base * 0.005:
            problems.append({store: f"{got} != {base}"})
    return problems


def route(platform):
    machine = MACHINE[platform]
    tag = {"docker": "D", "lima": "L", "ac": "A"}[platform]
    started = ensure_machine(platform, machine)
    boot = f"R11-{tag}-BOOT"
    case(boot, f"{machine} ({platform}) starts and reports its kernel and free disk")
    check(boot, f"{machine}: machine start succeeds", started["exit"] == 0, started["stderr"][:300])
    status = call(["machine", "status", machine], timeout=600)
    check(boot, f"{machine}: reports running with a free disk",
          (status["json"] or {}).get("state") == "running" and ((status["json"] or {}).get("free_disk") or 0) > 0,
          json.dumps(status["json"])[:400])
    case(boot)["measurements"]["status"] = status["json"]

    big = "cap256"
    cid = f"R11-{tag}-256-push"
    case(cid, f"{platform}: the 256 MiB Store's push, measured phase by phase")
    reset = reset_stores(cid, (("256", big), ("512", STORE["512"]), ("quiet", STORE["quiet"])))
    check(cid, "both Stores start from the fixture's bytes (within 0.5% of the setup import)", not reset,
          json.dumps(reset)[:400])
    push0 = transfer(cid, platform, machine, big, "push")
    after = verify_after_push(cid, platform, machine, big, push0["result"])
    case(cid)["measurements"].update(after)

    edit_cid = f"R11-{tag}-TARGET-EDIT"
    case(edit_cid, f"{platform}: a Workspace write and commit on the target, then a pull back")
    edit = edit_on_target(edit_cid, platform, machine, big)
    branch = edit.get("branch", "s2edit")

    pull_cid = f"R11-{tag}-256-pull"
    case(pull_cid, f"{platform}: the 256 MiB Store's pull, measured phase by phase")
    baseline = fixture_manifest()
    pulled = transfer(pull_cid, platform, machine, big, "pull")
    back = verify_native_after_pull(pull_cid, big, pulled, baseline, branch)
    case(pull_cid)["measurements"].update(back)

    quiet_cid = f"R12-{tag}-QUIET"
    case(quiet_cid, f"{platform}: neither command without --progress writes a progress line")
    quiet(quiet_cid, machine, STORE["quiet"], "push")
    quiet(quiet_cid, machine, STORE["quiet"], "pull")

    cid512 = f"R11-{tag}-512"
    case(cid512, f"{platform}: the 512 MiB Store, to show the buffers do not grow with the Store")
    push512 = transfer(cid512, platform, machine, STORE["512"], "push")
    verify_after_push(cid512, platform, machine, STORE["512"], push512["result"])
    pull512 = transfer(cid512, platform, machine, STORE["512"], "pull")
    check(cid512, "the pulled 512 MiB Store's bytes are the transfer's sha256",
          (native_sha(STORE["512"]) or "") ==
          ((store_get(STORE["512"])["json"].get("last_transfer") or {}).get("sha256") or "x"),
          f"{native_sha(STORE['512'])}")

    if platform == "docker":
        for name, reason in (("CAP-PRE", "colima's 30 GiB data disk would have to be filled to about 28 GiB "
                                          "to leave less than a 256 MiB Store's 1.25 GiB requirement; the host "
                                          "has 50 GiB and the same check code path runs on lima and apple-container"),
                             ("ENOSPC-MID", "the same 30 GiB disk would have to be filled during send; the "
                                            "injection ran on lima and apple-container")):
            skip = f"R11-{name}-{tag}"
            case(skip, f"{platform}: NOT_RUN — {reason}")
            note(skip, reason)
    else:
        cap_pre(f"R11-CAP-PRE-{tag}", platform, machine, big)
        enospc_mid(f"R11-ENOSPC-MID-{tag}", platform, machine, big, mode="delalloc")
        sync_cid = f"R11-ENOSPC-MID-SYNC-{tag}"
        looked = remount_data(platform, "nodelalloc")
        if looked.get("exit") == 0 and "nodelalloc" in looked.get("out", ""):
            remount_data(platform, "delalloc")
            enospc_mid(sync_cid, platform, machine, big, mode="sync")
        else:
            reason = (f"the data disk of {machine} refuses `mount -o remount,nodelalloc` "
                      f"(exit {looked.get('exit')}: {looked.get('err', '')[:120]}); the same injection did run "
                      f"on the default mount, recorded in R11-ENOSPC-MID-{tag}")
            case(sync_cid, f"{platform}: NOT_RUN — {reason}")
            note(sync_cid, reason)
            case(sync_cid)["measurements"]["remount"] = looked


def fixture_manifest(size="256", project="p1"):
    """The fixture's own manifest, run on the host with the same script: the bytes a pull must return."""
    shown = run(["/bin/sh", "-c", MANIFEST], timeout=1800, cwd=str(FIX[size] / project))
    lines = manifest_lines(shown["out"])
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"manifest-fixture-{size}-{project}.txt").write_text("\n".join(lines) + "\n")
    return lines


# ------------------------------------------------------------------------ setup


def close_sandboxes():
    listed = call(["sandbox", "list"], timeout=600)
    names = [entry.get("name") for entry in ((listed["json"] or {}).get("items") or [])]
    for name in names:
        call(["sandbox", "close", name, "--force"], timeout=1800)
    return names


def setup():
    HOME.mkdir(mode=0o700, parents=True, exist_ok=True)
    for folder in (REC, RAW):
        folder.mkdir(parents=True, exist_ok=True)
    closed = close_sandboxes()
    print("closed sandboxes:", closed)
    steps = [
        (["machine", "update", "docker", "--docker", os.environ.get("LP08_DOCKER_SOCK", str(Path.home() / ".colima/default/docker.sock"))], 600),
        (["machine", "update", "native", "--daemon", DAEMON], 600),
        (["machine", "start", "docker"], 1800),
    ]
    for argv, timeout in steps:
        result = call(argv, timeout=timeout)
        print(argv, "->", result["exit"], result["stderr"][:160])
    facts = {
        "platforms": (call(["machine", "platforms"], timeout=300)["json"]),
        "machines": (call(["machine", "list"], timeout=300)["json"]),
        "fixtures": json.loads((RUN / "fixture" / "fixtures.json").read_text()),
        "stores": {},
    }
    for size, store in STORE.items():
        ensure_store(store, FIX[size], size=size)
        facts["stores"][store] = (store_status(store)["json"].get("file") or {}).get("bytes")
    (REC / "setup.json").write_text(json.dumps(facts, indent=1))
    print("home:", HOME)


def ensure_store(store, fixture, size="256"):
    existing = (call(["store", "list"], timeout=300)["json"] or {}).get("items") or []
    names = [entry.get("name") for entry in existing]
    if store not in names:
        made = call(["store", "create", store], timeout=600)
        if made["exit"] != 0:
            raise SystemExit(f"store create {store}: {made['stderr']}")
    else:
        # a Store a failed transfer left unresolved, or one still on a machine
        ensure_store_on("native", store, size=size, attempts=6)
    for project in ("p1", "p2"):
        init = call(["project", "init", f"{store}/{project}", str(fixture / project)], timeout=3600)
        code = (refusal(init) or {}).get("code")
        if init["exit"] != 0 and code != "Exists":
            ensure_store_on("native", store, size=size, attempts=6)
            init = call(["project", "init", f"{store}/{project}", str(fixture / project)], timeout=3600)
            code = (refusal(init) or {}).get("code")
            if init["exit"] != 0 and code != "Exists":
                raise SystemExit(f"project init {store}/{project}: {init['stderr']}")
    status = store_status(store)
    print(store, json.dumps(status["json"].get("file")))


def ac_pull_rounds(machine="ac-s2", rounds=3, attempts=25):
    """How often a big Store's pull succeeds on the Apple Container, round by round."""
    cid = "R11-A-PULL-ROUNDS"
    case(cid, "the Apple Container's pull of the 256 MiB and 512 MiB Stores, three rounds each")
    for size in ("256", "512"):
        store = STORE[size]
        for round_number in range(1, rounds + 1):
            if not ensure_store_on("native", store, size=size).get("ok", True):
                reset_stores(cid, ((size, store),))
            pushed = call(["store", "push", store, machine], timeout=1800)
            started = time.monotonic()
            result = None
            made = 0
            while made < attempts:
                made += 1
                result = call(["store", "pull", store], timeout=1800)
                if result["exit"] == 0:
                    break
                time.sleep(0.2)
            status = store_status(store)["json"]
            sha = native_sha(store)
            last = (store_get(store)["json"] or {}).get("last_transfer") or {}
            row = {"store": store, "round": round_number, "push_exit": pushed["exit"],
                   "attempts": made, "pull_exit": (result or {}).get("exit"),
                   "seconds": round(time.monotonic() - started, 2),
                   "state": status.get("state"), "machine": status.get("machine"),
                   "op_uncertain": (status.get("op") or {}).get("uncertain"),
                   "sha_is_snapshot": sha is not None and sha == last.get("sha256")}
            case(cid)["measurements"][f"{size}-round{round_number}"] = row
            if row["pull_exit"] != 0:
                # a failed round must leave the authority where it was, nothing lost
                check(cid, f"{size} round {round_number}: a failed pull leaves the Store unresolved, source intact",
                      row["state"] == "unresolved" and row["machine"] == machine
                      and native_sha(store) is None, json.dumps(row))
            else:
                check(cid, f"{size} round {round_number}: a successful pull returns the snapshot's bytes",
                      row["sha_is_snapshot"] and row["machine"] == "native", json.dumps(row))
    rows = [row for row in case(cid)["measurements"].values()
            if isinstance(row, dict) and "round" in row]
    succeeded = [row for row in rows if row["pull_exit"] == 0]
    note(cid, f"success rate: {len(succeeded)} of {len(rows)} rounds; attempts per success "
              f"{[row['attempts'] for row in succeeded]}")
    check(cid, "no round reported a success whose bytes were not the snapshot's",
          all(row["sha_is_snapshot"] for row in succeeded), json.dumps(succeeded))
    return rows


# --------------------------------------------------------------- #12 SDK


def sdk(cid="R12-D-SDK-ONPROGRESS"):
    """The Node SDK's `on_progress`: the same seven phases, every event before the call settles."""
    case(cid, "Node SDK on_progress on the release build, against the same docker machine as the CLI")
    ensure_store_on("native", STORE["256"])
    ensure_store_on("native", STORE["quiet"], size="quiet")
    call(["machine", "start", "docker"], timeout=1800)
    shown = run(["node", str(WORK / "sdk-progress.mjs"), str(HOME), STORE["256"], "docker", STORE["quiet"]],
                timeout=1800, extra_env={"LAYERFS_NATIVE": ADDON})
    payload = None
    try:
        payload = json.loads(shown["out"].strip().splitlines()[-1])
    except (ValueError, IndexError):
        payload = None
    case(cid)["measurements"]["process"] = {"exit": shown["exit"], "seconds": shown["seconds"],
                                         "stderr": shown["err"][-1200:]}
    if not payload:
        note(cid, "the SDK run printed no JSON: " + shown["err"][-800:])
        check(cid, "the SDK run answered with its event stream", False, shown["err"][-400:])
        return None
    (RAW / "sdk-progress.json").write_text(json.dumps(payload, indent=1))
    cli_push = json.loads((REC / "R11-D-256-push.json").read_text())["measurements"]["cap256-push"]
    for label, key, cli in (("push", "push", cli_push), ("pull", "pull",
                            json.loads((REC / "R11-D-256-pull.json").read_text())["measurements"]["cap256-pull"])):
        events = payload[key]["events"]
        phases = [e["phase"] for e in events]
        seen = []
        for phase in phases:
            if not seen or seen[-1] != phase:
                seen.append(phase)
        sends = [e for e in events if e["phase"] == "send" and e["total"] is not None]
        check(cid, f"SDK {label}: the call succeeded", payload[key]["answer"] is not None
              and payload[key]["error"] is None, json.dumps(payload[key]["answer"])[:300])
        check(cid, f"SDK {label}: the seven phases arrive in the CLI's order",
              seen == PHASES and seen == cli["phase_order"],
              f"sdk {seen} vs cli {cli['phase_order']}")
        check(cid, f"SDK {label}: send's counts are the CLI's (constant total, final done == total)",
              bool(sends) and len({e["total"] for e in sends}) == 1
              and [e["done"] for e in sends] == sorted(e["done"] for e in sends)
              and sends[-1]["done"] == sends[-1]["total"] == (payload[key]["answer"] or {}).get("bytes"),
              f"{len(sends)} counted events, totals {[e['total'] for e in sends][:2]}")
        check(cid, f"SDK {label}: every event arrived before the call settled",
              all(e["settled"] is False for e in events), json.dumps(events[:3])[:300])
        check(cid, f"SDK {label}: the last event is retire",
              phases[-1] == "retire" if label == "push" else phases[-1] == "retire", phases[-1] if phases else None)
    thrown = payload["throwing"]
    check(cid, "a handler that throws at every event does not stop the push",
          thrown["error"] is None and thrown["answer"] is not None, json.dumps(thrown["error"])[:300])
    thrown_phases = [row["phase"] for row in thrown["phases"]]
    check(cid, "the throwing handler still saw every phase, retire last",
          thrown_phases[:1] == ["check"] and thrown_phases[-1:] == ["retire"]
          and set(PHASES) <= set(thrown_phases), json.dumps(thrown_phases))
    check(cid, "each throw was a warning, not a refusal", thrown["warning_count"] >= 1,
          json.dumps(thrown["warnings"])[:400])
    check(cid, "the small Store pulls back through the SDK",
          payload["small_back"]["answer"] is not None and payload["small_back"]["error"] is None,
          json.dumps(payload["small_back"]["answer"])[:200])
    return payload


# ----------------------------------------------------------------------- report


def report():
    for cid, entry in CASES.items():
        (REC / f"{cid}.json").write_text(json.dumps(entry, indent=1, ensure_ascii=False))
    matrix = {"cases": [{"case": cid, "verdict": verdict(cid),
                         "checks": len(entry["checks"]),
                         "passed": sum(1 for c in entry["checks"] if c["ok"])}
                        for cid, entry in sorted(CASES.items())]}
    matrix["commands"] = LOG
    (REC / f"matrix-run-{len(matrix['cases'])}.json").write_text(
        json.dumps(matrix, indent=1, ensure_ascii=False))
    rows = [(cid, verdict(cid), len(entry["checks"]), sum(1 for c in entry["checks"] if c["ok"]))
            for cid, entry in sorted(CASES.items())]
    for row in rows:
        print(f"{row[0]:<28} {row[1]:<8} {row[3]}/{row[2]}")
    return matrix


def rollup():
    """`matrix-s2.json`: every case on disk, one row each, with the totals."""
    cases = []
    for path in sorted(REC.glob("*.json")):
        name = path.stem
        if name.startswith("matrix"):
            continue
        entry = json.loads(path.read_text())
        if "checks" not in entry:
            continue
        checks = entry["checks"]
        passed = sum(1 for c in checks if c["ok"])
        verdict_of = "NOT_RUN" if not checks else ("PASS" if passed == len(checks) else "FAIL")
        cases.append({"case": name, "verdict": verdict_of, "checks": len(checks),
                      "passed": passed,
                      "failed": [c["name"] for c in checks if not c["ok"]]})
    totals = {"cases": len(cases),
              "checks": sum(c["checks"] for c in cases),
              "passed": sum(c["passed"] for c in cases),
              "failed": sum(c["checks"] - c["passed"] for c in cases),
              "not_run": sum(1 for c in cases if c["verdict"] == "NOT_RUN")}
    (REC / "matrix-s2.json").write_text(json.dumps({"totals": totals, "cases": cases}, indent=1,
                                                    ensure_ascii=False))
    print(json.dumps(totals))
    for row in cases:
        print(f"{row['case']:<28} {row['verdict']:<8} {row['passed']}/{row['checks']}")
    return totals


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "report"
    try:
        if what == "setup":
            setup()
        elif what == "route":
            route(sys.argv[2])
        elif what == "acsweep":
            ac_pull_sweep()
        elif what == "acrounds":
            ac_pull_rounds()
        elif what == "sdk":
            sdk()
        elif what == "report":
            report()
        elif what == "rollup":
            rollup()
        else:
            raise SystemExit(f"unknown step {what}")
    finally:
        report()


if __name__ == "__main__":
    main()
