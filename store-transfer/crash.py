#!/usr/bin/env python3
"""LP08-S3: layerfs-project#13 crash / ownership-recovery matrix on real machines.

Every case drives the public `layerfs` CLI against the sealed release guest
bundle (2e98e17e…) of pin 8f0ff7b2b. Interruptions are made deterministic by
freezing the CLI (SIGSTOP) the instant it writes the phase's progress event,
reading the record on disk at that instant, then SIGKILLing it (or mutating a
byte of the copy and letting it continue).

    python3 crash.py setup
    python3 crash.py route docker          # full #13 suite
    python3 crash.py route lima            # sampled: send/install/tamper/retire/readonly/reverse/remove
    python3 crash.py route ac              # sampled, same list
    python3 crash.py report
"""
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

CLI = os.environ.get("LAYERFS_CLI", "layerfs")
DAEMON = os.environ.get("LAYERFS_DAEMON", "layerfs-daemon")
BASE = Path(os.environ.get("LP08_BASE", "/tmp/lp08-s3"))
HOME = BASE / "home"
FIX = BASE / "fixture" / "p1"
REC = BASE / "receipts" / "lp08-s3"
PHASES = ["check", "snapshot", "send", "verify", "install", "record", "retire"]
MACHINE = {"docker": "docker", "lima": "lm-s3", "ac": "ac-s3"}
TAG = {"docker": "D", "lima": "L", "ac": "A"}
GUEST = {}  # route -> ("docker"|"limactl"|"container", handle)
CASES = {}
COMMANDS = []


# --------------------------------------------------------------------------- io


def env():
    return {**os.environ, "LAYERFS_HOME": str(HOME)}


def call(argv, timeout=900, progress=False):
    t0 = time.monotonic()
    process = subprocess.Popen([CLI] + argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env())
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
            text = line.decode("utf-8", "replace").strip()
            if not text:
                continue
            raw.append(text)
            if progress and text.startswith("{"):
                try:
                    events.append(json.loads(text))
                    continue
                except ValueError:
                    pass
            events.append({"raw": text})

    thread = threading.Thread(target=drain, daemon=True)
    thread.start()
    out = process.stdout.read()
    code = process.wait()
    thread.join(10)
    timer.cancel()
    try:
        parsed = json.loads(out.decode("utf-8")) if out.strip() else None
    except ValueError:
        parsed = None
    record = {
        "argv": argv,
        "exit": code,
        "seconds": round(time.monotonic() - t0, 3),
        "stdout": out.decode("utf-8", "replace").strip(),
        "stderr": "\n".join(raw),
        "json": parsed,
        "events": events,
        "timeout": expired.is_set(),
    }
    COMMANDS.append({"argv": argv, "exit": code, "seconds": record["seconds"]})
    return record


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


def case(cid, note=None):
    entry = CASES.setdefault(cid, {"case": cid, "checks": [], "notes": [], "commands": [], "evidence": {}})
    if note:
        entry["notes"].append(note)
    return entry


def check(cid, name, ok, evidence=""):
    ok = bool(ok)
    case(cid)["checks"].append({"name": name, "ok": ok, "evidence": str(evidence)[:1500]})
    return ok


def note(cid, text):
    case(cid)["notes"].append(text)


def evidence(cid, key, value):
    case(cid)["evidence"][key] = value


def ran(cid, result):
    case(cid)["commands"].append({"argv": ["layerfs"] + result["argv"], "exit": result["exit"],
                                  "seconds": result["seconds"], "stderr": result["stderr"][:600]})
    return result


def verdict(cid):
    checks = CASES[cid]["checks"]
    if not checks:
        return "NOT_RUN"
    return "PASS" if all(c["ok"] for c in checks) else "FAIL"


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def save():
    REC.mkdir(parents=True, exist_ok=True)
    for cid, entry in CASES.items():
        entry["verdict"] = verdict(cid)
        entry["at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        (REC / (cid + ".json")).write_text(json.dumps(entry, ensure_ascii=False, indent=1))
    (BASE / "receipts" / "commands.json").write_text(json.dumps(COMMANDS, indent=1))
    (BASE / "receipts" / "pin.json").write_text(json.dumps({
        "cli": CLI, "cli_sha256": sha256_file(Path(CLI)),
        "daemon": DAEMON, "daemon_sha256": sha256_file(Path(DAEMON)),
        "bundle": json.loads((Path.home() / ".cache/layerfs/bundle/2.0.0/linux-aarch64/bundle.json").read_text()),
        "home": str(HOME),
        "live": provenance(),
    }, ensure_ascii=False, indent=1))


def provenance():
    out = {}
    for name, argv in {
        "sw_vers": ["sw_vers"], "uname": ["uname", "-m"],
        "docker": ["docker", "--version"], "colima": ["colima", "version"],
        "limactl": ["limactl", "--version"], "container": ["container", "--version"],
    }.items():
        try:
            out[name] = subprocess.run(argv, capture_output=True, text=True, timeout=30).stdout.strip().splitlines()[0]
        except Exception as why:  # noqa: BLE001
            out[name] = f"unavailable: {why}"
    return out


# --------------------------------------------------------------- home records


def home_record(name):
    path = HOME / "store" / name / "record.json"
    if not path.exists():
        return None
    for _ in range(5):
        try:
            return json.loads(path.read_text())
        except ValueError:
            time.sleep(0.02)
    return None


def op_of(name):
    record = home_record(name) or {}
    return record.get("op")


def last_transfer(name):
    return (home_record(name) or {}).get("last_transfer") or {}


def machine_of(name):
    return (home_record(name) or {}).get("machine")


def observed(name):
    """The row the state table is read from: machine, op phase, uncertain."""
    record = home_record(name) or {}
    op = record.get("op") or None
    return {
        "machine": record.get("machine"),
        "op": None if not op else {
            "name": op.get("name"), "phase": op.get("phase"), "uncertain": bool(op.get("uncertain")),
            "id": op.get("id"),
        },
        "last_transfer_retired": (record.get("last_transfer") or {}).get("retired"),
    }


def row_text(row):
    op = row["op"] or {}
    return "machine=%s op=%s/%s uncertain=%s retired=%s" % (
        row["machine"], op.get("name"), op.get("phase"), op.get("uncertain"), row["last_transfer_retired"])


def store_status(name):
    return call(["store", "status", name], timeout=300)["json"]


def store_get(name):
    return call(["store", "get", name], timeout=300)["json"]


def doctor():
    return call(["doctor"], timeout=600)["json"]


def store_findings(report):
    return [f for f in ((report or {}).get("findings") or []) if (f.get("entity") or {}).get("kind") == "store"]


def store_file(name):
    return HOME / "store" / name / "store.sqlite"


def store_sha(name):
    path = store_file(name)
    return sha256_file(path) if path.exists() else None


def incoming_local(name):
    return HOME / "store" / name / "store.sqlite.incoming"


def tree(root=HOME, skip=()):
    """Every entry under the home with mode, size, mtime_ns and content hash."""
    rows = {}
    root = Path(root)
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files) + sorted(dirs):
            path = Path(base) / name
            rel = str(path.relative_to(root))
            if any(rel == s or rel.startswith(s + "/") for s in skip):
                continue
            try:
                meta = path.lstat()
            except FileNotFoundError:
                continue
            if path.is_symlink():
                rows[rel] = "L:" + os.readlink(path)
            elif path.is_dir():
                rows[rel] = "D:%o:%d" % (meta.st_mode & 0o777, meta.st_mtime_ns)
            elif meta.st_size > 8 << 20:
                rows[rel] = "F:%o:%d:%d" % (meta.st_mode & 0o777, meta.st_size, meta.st_mtime_ns)
            else:
                rows[rel] = "F:%o:%d:%d:%s" % (meta.st_mode & 0o777, meta.st_size, meta.st_mtime_ns,
                                               sha256_file(path))
    return rows


def tree_diff(before, after):
    rows = sorted(set(before.items()) ^ set(after.items()))
    return [row[0] for row in rows][:10]


# ------------------------------------------------------------------- machines


def machine_start(name):
    return call(["machine", "start", name], timeout=1200)


def home_id():
    return json.loads((HOME / "layerfs.json").read_text())["id"]


def vm_name(rid):
    """lfs-<home id[..8]>-<machine>, the name the product gives this home's VM."""
    return "lfs-%s-%s" % (home_id()[:8], MACHINE[rid])


def resolve_guest(rid):
    """This home's guest handle only: another home's workers run in parallel."""
    want = vm_name(rid)
    if rid == "docker":
        names = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True,
                               timeout=120).stdout.split()
        for name in names:
            if name == want:
                GUEST[rid] = ("docker", name)
                return GUEST[rid]
        return None
    if rid == "lima":
        listed = subprocess.run(["limactl", "list", "--json"], capture_output=True, text=True, timeout=120).stdout
        for line in listed.splitlines():
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("name") == want and entry.get("status") == "Running":
                GUEST[rid] = ("limactl", want)
                return GUEST[rid]
        return None
    listed = subprocess.run(["container", "list", "--format", "json"], capture_output=True, text=True,
                            timeout=120).stdout
    try:
        entries = json.loads(listed) if listed.strip() else []
    except ValueError:
        entries = []
    for entry in entries:
        ident = entry.get("id") or entry.get("name") or ""
        if ident == want or want in json.dumps(entry):
            GUEST[rid] = ("container", ident)
            return GUEST[rid]
    return None


def guest(rid, script, timeout=300):
    kind, handle = GUEST[rid]
    if kind == "docker":
        argv = ["docker", "exec", handle, "sh", "-c", script]
    elif kind == "limactl":
        argv = ["limactl", "shell", handle, "--", "sudo", "sh", "-c", script]
    else:
        argv = ["container", "exec", handle, "sh", "-c", script]
    done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    return done.returncode, (done.stdout + done.stderr)


def guest_store_dir(rid, name):
    rc, out = guest(rid, "ls -la /layerfs/data/store/%s 2>/dev/null" % name)
    return {"rc": rc, "listing": out.strip()}


def guest_bytes(rid, name, suffix=""):
    rc, out = guest(rid, "stat -c %%s /layerfs/data/store/%s/store.sqlite%s 2>/dev/null" % (name, suffix))
    text = out.strip().splitlines()[0] if out.strip() else ""
    return int(text) if text.isdigit() else None


def guest_sha(rid, name, suffix=""):
    rc, out = guest(rid, "sha256sum /layerfs/data/store/%s/store.sqlite%s 2>/dev/null" % (name, suffix))
    text = out.strip().split()[0] if out.strip() else ""
    return text or None


def guest_remove(rid, name):
    return guest(rid, "rm -rf /layerfs/data/store/%s" % name)


def worker_signal(rid, sig):
    """SIGSTOP or SIGKILL the guest's `layerfs worker` process (PID 1 is docker-init)."""
    kind, _ = GUEST[rid]
    find = ('for p in /proc/[0-9]*; do c=$(tr "\\0" " " < $p/cmdline 2>/dev/null); '
            'case "$c" in "/layerfs/bundle/layerfs worker"*) echo ${p#/proc/}; kill -%s ${p#/proc/}; exit 0;; esac; done; exit 3')
    if kind == "docker":
        return guest(rid, find % sig)
    return guest(rid, "pkill -%s -f '/layerfs/bundle/layerfs worker'" % sig)


def wait_guest(rid, tries=60):
    """After a machine start: wait until the guest answers a plain command."""
    for _ in range(tries):
        rc, out = guest(rid, "ls /layerfs/data/store >/dev/null 2>&1 && echo ready")
        if rc == 0 and "ready" in out:
            return True
        time.sleep(0.5)
    return False


# ------------------------------------------------------- transfer with a hook


def run_hooked(argv, name, phase, action="kill", cond=None, mutate=None, after=None, timeout=600):
    """Run a transfer, freeze it (SIGSTOP) at `phase`'s progress event, then
    either SIGKILL it or run `mutate()` while frozen and let it continue."""
    t0 = time.monotonic()
    process = subprocess.Popen([CLI] + argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env())
    events, raw = [], []
    frozen = threading.Event()
    state = {"frozen_row": None, "event": None, "mutated": None}
    finished = threading.Event()

    def monitor():
        for line in process.stderr:
            text = line.decode("utf-8", "replace").strip()
            if not text:
                continue
            raw.append(text)
            event = None
            if text.startswith("{"):
                try:
                    event = json.loads(text)
                except ValueError:
                    event = None
            events.append(event if event is not None else {"raw": text})
            progress = (event or {}).get("progress") or {}
            if (progress.get("phase") == phase and not frozen.is_set()
                    and (cond is None or cond(progress))):
                frozen.set()
                state["event"] = event
                try:
                    os.kill(process.pid, signal.SIGSTOP)
                except ProcessLookupError:
                    return
                time.sleep(0.05)
                state["frozen_row"] = observed(name)
                try:
                    if action == "kill":
                        os.kill(process.pid, signal.SIGKILL)
                    else:
                        state["mutated"] = mutate() if mutate else None
                        if after:
                            threading.Thread(target=after, daemon=True).start()
                        os.kill(process.pid, signal.SIGCONT)
                except ProcessLookupError:
                    pass
        finished.set()

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    out = process.stdout.read()
    code = process.wait()
    thread.join(20)
    try:
        parsed = json.loads(out.decode("utf-8")) if out.strip() else None
    except ValueError:
        parsed = None
    result = {
        "argv": argv, "exit": code, "seconds": round(time.monotonic() - t0, 3),
        "stdout": out.decode("utf-8", "replace").strip(), "stderr": "\n".join(raw),
        "json": parsed, "events": events,
    }
    COMMANDS.append({"argv": argv, "exit": code, "seconds": result["seconds"]})
    return result, {"frozen": frozen.is_set(), "event": state["event"],
                    "row_at_freeze": state["frozen_row"], "mutated": state["mutated"]}


# ------------------------------------------------------------------- fixtures


def new_store(rid, name, folder=FIX):
    made = call(["store", "create", name], timeout=300)
    if made["exit"] != 0:
        return made, None
    init = call(["project", "init", "%s/p1" % name, str(folder)], timeout=900)
    return made, init


def heads_check(cid, label, got, want):
    """History heads when they were readable before the injection."""
    if want is None:
        note(cid, "%s: heads were unreadable before the injection on this route, so the sha256 is the evidence"
             % label)
        return
    check(cid, label, got == want, "%s vs %s" % (got, want))


def baseline_heads(rid, cid, name):
    """A clean push+pull first: it is the only read of the history heads the CLI
    exposes before a transfer, and it proves the route works before injecting.
    A pull refused Unknown leaves an unresolved intent the documented way: the
    same `store pull` clears it, so the baseline repeats it and records how many
    attempts that took (the apple-container defect of LP08-S1)."""
    machine = MACHINE[rid]
    if rid == "ac":
        note(cid, "no baseline round trip: an apple-container pull loses the worker's answer at send "
                  "(LP08-S1's defect, reproduced below), so heads cannot be read before the injection; "
                  "the byte identity of the source copy is the evidence instead")
        return None
    a = ran(cid, call(["store", "push", name, machine], timeout=900))
    attempts = []
    for _ in range(5):
        b = ran(cid, call(["store", "pull", name], timeout=900))
        attempts.append({"exit": b["exit"], "code": (refusal(b) or {}).get("code"),
                         "stderr": b["stderr"][-200:]})
        if b["exit"] == 0:
            break
        state = (store_status(name) or {}).get("state")
        if state != "unresolved":
            break
    check(cid, "a clean round trip before the injection works",
          a["exit"] == 0 and attempts[-1]["exit"] == 0, json.dumps(attempts)[:600])
    note(cid, "baseline: push exit %s, pull attempts %s" % (a["exit"], json.dumps(attempts)[:500]))
    return (last_transfer(name) or {}).get("heads")


def ensure_machine(rid):
    name = MACHINE[rid]
    listed = call(["machine", "list"])
    names = [m.get("name") for m in ((listed["json"] or {}).get("machines") or [])]
    if name not in names and rid != "docker":
        created = call(["machine", "create", name, {"lima": "lima", "ac": "apple-container"}[rid],
                        "--cpus", "2", "--memory", "2G", "--disk", "8G"], timeout=1800)
        if created["exit"] != 0:
            raise RuntimeError("machine create %s failed: %s" % (name, created["stderr"][:400]))
    started = machine_start(name)
    if started["exit"] != 0:
        raise RuntimeError("machine start %s failed: %s" % (name, started["stderr"][:400]))
    status = call(["machine", "status", name])
    handle = resolve_guest(rid)
    if not handle:
        raise RuntimeError("no guest handle for %s" % rid)
    return status["json"], handle


def drop_store(name):
    out = call(["store", "remove", name], timeout=900)
    if out["exit"] != 0:
        shutil.rmtree(HOME / "store" / name, ignore_errors=True)
        for rid in GUEST:
            try:
                guest_remove(rid, name)
            except Exception:  # noqa: BLE001
                pass
    return out


def reset_home_store(name):
    shutil.rmtree(HOME / "store" / name, ignore_errors=True)
    for rid in list(GUEST):
        try:
            guest_remove(rid, name)
        except Exception:  # noqa: BLE001
            pass


# --------------------------------------------------------------- #13 helpers


def kill_at(rid, cid, name, direction, phase, cond=None):
    """Push or pull `name`, SIGKILL it at `phase`; record the state it left."""
    machine = MACHINE[rid]
    argv = ["store", "push", name, machine, "--progress"] if direction == "push" else \
           ["store", "pull", name, "--progress"]
    result, hook = run_hooked(argv, name, phase, "kill", cond=cond)
    ran(cid, result)
    row = observed(name)
    return result, hook, row


def tamper_at(rid, cid, name, direction, phase, mutate, cond=None, after=None):
    machine = MACHINE[rid]
    argv = ["store", "push", name, machine, "--progress"] if direction == "push" else \
           ["store", "pull", name, "--progress"]
    result, hook = run_hooked(argv, name, phase, "mutate", cond=cond, mutate=mutate, after=after)
    ran(cid, result)
    return result, hook, observed(name)


def both_copies(rid, name, direction):
    """(source exists, target exists) for the direction the transfer ran."""
    if direction == "push":
        return store_file(name).is_file(), guest_bytes(rid, name) is not None or \
               (guest_bytes(rid, name, ".incoming") or 0) > 0
    return guest_bytes(rid, name) is not None, store_file(name).is_file() or incoming_local(name).exists()


def run_label(row):
    op = row["op"] or {}
    return "machine=%s op=%s/%s uncertain=%s" % (row["machine"], op.get("name"), op.get("phase"),
                                                 op.get("uncertain"))


def recover(rid, cid, name, direction, heads_before, bytes_before, sha_before):
    """The same-direction call again: it must clear what the crash left and finish."""
    machine = MACHINE[rid]
    argv = ["store", "push", name, machine, "--progress"] if direction == "push" else \
           ["store", "pull", name, "--progress"]
    again = ran(cid, call(argv, timeout=900, progress=True))
    check(cid, "the same command again succeeds", again["exit"] == 0, again["stderr"][:400])
    row = observed(name)
    check(cid, "after recovery the record names %s" % ("native" if direction == "pull" else machine),
          row["machine"] == ("native" if direction == "pull" else machine), run_label(row))
    check(cid, "after recovery no op is left", row["op"] is None, run_label(row))
    get = store_get(name) or {}
    last = get.get("last_transfer") or {}
    check(cid, "the recovery's last_transfer is retired", last.get("retired") is True, json.dumps(last)[:400])
    heads_check(cid, "heads are unchanged across the crash and the recovery", last.get("heads"), heads_before)
    if direction == "push":
        check(cid, "the target holds the Store and its sha256 is the record's",
              guest_sha(rid, name) == last.get("sha256"), "%s vs %s" % (guest_sha(rid, name), last.get("sha256")))
        check(cid, "the native copy is retired after recovery", not store_file(name).exists(),
              str(sorted(p.name for p in (HOME / "store" / name).glob("store.sqlite*"))))
        check(cid, "no partial copy is left on the target",
              guest_bytes(rid, name, ".incoming") in (None, 0), str(guest_bytes(rid, name, ".incoming")))
    else:
        check(cid, "native holds the Store and its sha256 is the record's",
              store_sha(name) == last.get("sha256"), "%s vs %s" % (store_sha(name), last.get("sha256")))
        check(cid, "the machine's copy is retired after recovery",
              guest_bytes(rid, name) is None, str(guest_store_dir(rid, name)["listing"])[:200])
        check(cid, "no partial copy is left at native",
              not incoming_local(name).exists(), str(incoming_local(name)))
    status = store_status(name) or {}
    check(cid, "the recovered Store is idle with no op",
          status.get("state") == "idle" and status.get("op") in (None, {}), json.dumps(status)[:400])
    report = doctor()
    check(cid, "doctor is clean for the recovered Store", not store_findings(report),
          json.dumps(store_findings(report))[:500])
    return again


def table_rows(label, trigger=None):
    """The rows the state table allows for a kill that freezes at `trigger`
    (the label is the phase the case is about). The CLI writes a phase's
    progress event before it writes that phase into `op`, so a freeze at one
    phase's event may be read back as the phase before it."""
    machine = MACHINE_OF_INJECTION
    if label == "check":
        return [("native", None, False), ("native", "check", False)]
    if label in ("snapshot", "send", "verify"):
        return [("native", "check", False), ("native", "snapshot", False), ("native", "send", False),
                ("native", "verify", False)]
    if label == "install":
        # frozen at record's event: install is done (both copies), record is not written
        return [("native", "install", True), ("native", "record", True), (machine, "retire", False)]
    if label == "install-entry":
        # frozen at install's own event: the uncertain flag is not yet in the record
        return [("native", "verify", False), ("native", "install", True)]
    return [(machine, "retire", False)]


MACHINE_OF_INJECTION = ""


def phase_kill_case(rid, label, trigger=None):
    """R13-<tag>-KILL-<label>: push interrupted at a phase boundary, then recovered."""
    global MACHINE_OF_INJECTION
    trigger = trigger or label
    cid = "R13-%s-KILL-%s" % (TAG[rid], label)
    machine = MACHINE[rid]
    MACHINE_OF_INJECTION = machine
    name = "k-%s-%s" % (TAG[rid].lower(), label[:6])
    case(cid, "store push to %s, SIGKILL the CLI as its %s progress event is written (case: %s)"
         % (machine, trigger, label))
    reset_home_store(name)
    _, init = new_store(rid, name)
    check(cid, "fixture Store created", init is not None and init["exit"] == 0, (init or {}).get("stderr", "")[:300])
    heads = baseline_heads(rid, cid, name)
    before = store_status(name) or {}
    sha_before = store_sha(name)
    retired_before = last_transfer(name).get("retired")
    evidence(cid, "before", {"bytes": (before.get("file") or {}).get("bytes"), "sha256": sha_before,
                             "heads": heads, "retired": retired_before})

    cond = (lambda p: (p.get("done") or 0) > 0) if trigger == "send" else None
    result, hook, row = kill_at(rid, cid, name, "push", trigger, cond=cond)
    freeze_row = hook["row_at_freeze"]
    evidence(cid, "freeze", {"event": hook["event"], "row": freeze_row, "frozen": hook["frozen"]})
    evidence(cid, "after_kill", {"exit": result["exit"], "row": row,
                                 "stderr": result["stderr"][:600]})
    check(cid, "the CLI was frozen at the %s progress event" % trigger,
          hook["frozen"] and ((hook["event"] or {}).get("progress") or {}).get("phase") == trigger,
          json.dumps(hook["event"]))
    check(cid, "the interrupted CLI died by SIGKILL", result["exit"] == -9, "exit %s" % result["exit"])

    op = row["op"] or {}
    allowed = table_rows(label, trigger)
    hit = (row["machine"], op.get("phase"), bool(op.get("uncertain")))
    check(cid, "the state is a row the table allows for %s: %s" % (label, allowed), hit in allowed,
          run_label(row))
    check(cid, "the authority is still native or the recorded switch is the retire row (%s)" % machine,
          row["machine"] == ("native" if label != "retire" else machine), run_label(row))
    if label != "retire":
        check(cid, "the record still names the source machine (native)", row["machine"] == "native", run_label(row))
        check(cid, "the native Store copy is intact and byte-identical", store_sha(name) == sha_before,
              "%s vs %s" % (store_sha(name), sha_before))
        if op.get("uncertain"):
            status = store_status(name) or {}
            check(cid, "an uncertain intent reads as unresolved", status.get("state") == "unresolved",
                  json.dumps({"state": status.get("state"), "op": status.get("op")})[:400])
        report = doctor()
        findings = store_findings(report)
        evidence(cid, "doctor", findings)
        check(cid, "doctor reports the interrupted transfer", bool(findings) if op else not findings,
              json.dumps(findings)[:600])
        if label in ("snapshot", "send", "verify"):
            check(cid, "doctor names an incomplete partial copy on the target or a stale certain intent",
                  any("partial" in (f.get("message") or "") or "ended after a certain outcome" in (f.get("message") or "")
                      for f in findings), json.dumps(findings)[:600])
    else:
        last = last_transfer(name)
        check(cid, "an interrupted retire leaves the Store on %s with retired: false" % machine,
              row["machine"] == machine and last.get("retired") is False, json.dumps(last)[:400])
        check(cid, "the source copy is still on native, or its retire step already ran (the record still says false)",
              True, "source present=%s, retired=%s" % (store_file(name).is_file(), last.get("retired")))
        note(cid, "at the retire row the source copy was " + ("still present" if store_file(name).is_file()
              else "already deleted by the retire step") + "; the record still says retired:false")

    direction = "pull" if label == "retire" else "push"
    recover(rid, cid, name, direction, heads, (before.get("file") or {}).get("bytes"), sha_before)
    drop_store(name)


def pull_kill_case(rid, label, trigger=None):
    """R13-<tag>-KILL-<label>-PULL: the same interruption on the pull side."""
    global MACHINE_OF_INJECTION
    trigger = trigger or label
    cid = "R13-%s-KILL-%s-PULL" % (TAG[rid], label)
    machine = MACHINE[rid]
    MACHINE_OF_INJECTION = machine
    name = "kp-%s-%s" % (TAG[rid].lower(), label[:6])
    case(cid, "store pull from %s, SIGKILL the CLI as its %s progress event is written (case: %s)"
         % (machine, trigger, label))
    reset_home_store(name)
    _, init = new_store(rid, name)
    check(cid, "fixture Store created", init is not None and init["exit"] == 0, (init or {}).get("stderr", "")[:300])
    sent = ran(cid, call(["store", "push", name, machine], timeout=900))
    check(cid, "the Store is on the machine before the pull", sent["exit"] == 0, sent["stderr"][:300])
    heads = last_transfer(name).get("heads")
    remote_sha = guest_sha(rid, name)

    cond = (lambda p: (p.get("done") or 0) > 0) if trigger == "send" else None
    result, hook, row = kill_at(rid, cid, name, "pull", trigger, cond=cond)
    freeze_row = hook["row_at_freeze"]
    evidence(cid, "freeze", {"event": hook["event"], "row": freeze_row})
    evidence(cid, "after_kill", {"exit": result["exit"], "row": row, "stderr": result["stderr"][:600]})
    check(cid, "the CLI was frozen at the %s progress event" % trigger,
          hook["frozen"] and ((hook["event"] or {}).get("progress") or {}).get("phase") == trigger,
          json.dumps(hook["event"]))
    check(cid, "the interrupted CLI died by SIGKILL", result["exit"] == -9, "exit %s" % result["exit"])
    op = row["op"] or {}
    if label != "retire":
        check(cid, "the record still names the source machine %s" % machine, row["machine"] == machine, run_label(row))
        check(cid, "the machine's copy is intact and byte-identical", guest_sha(rid, name) == remote_sha,
              "%s vs %s" % (guest_sha(rid, name), remote_sha))
        if label in ("send", "verify"):
            check(cid, "native holds the partial copy as store.sqlite.incoming",
                  (incoming_local(name).stat().st_size if incoming_local(name).exists() else 0) > 0,
                  str(incoming_local(name)))
        report = doctor()
        findings = store_findings(report)
        evidence(cid, "doctor", findings)
        check(cid, "doctor reports the interrupted pull", bool(findings), json.dumps(findings)[:600])
        check(cid, "doctor's fix names `layerfs store pull %s`" % name,
              any("store pull" in (f.get("fix") or "") for f in findings), json.dumps(findings)[:600])
    recover(rid, cid, name, "pull", heads, None, None)
    drop_store(name)


def tamper_case(rid, how):
    """R13-<tag>-TAMPER-<how>: flip or truncate the target copy during verify."""
    cid = "R13-%s-TAMPER-%s" % (TAG[rid], how.upper())
    machine = MACHINE[rid]
    name = "tp-%s-%s" % (TAG[rid].lower(), how)
    case(cid, "store push to %s; at the last send event the target's .incoming is %s" % (machine, how))
    reset_home_store(name)
    _, init = new_store(rid, name)
    check(cid, "fixture Store created", init is not None and init["exit"] == 0, (init or {}).get("stderr", "")[:300])
    heads = baseline_heads(rid, cid, name)
    sha_before = store_sha(name)
    total = (store_status(name) or {}).get("file", {}).get("bytes")
    retired_before = last_transfer(name).get("retired")

    def mutate():
        if how == "flip":
            script = ("f=/layerfs/data/store/%s/store.sqlite.incoming; size=$(stat -c %%s $f); "
                      "off=$((size/2)); byte=$(od -An -tu1 -j $off -N1 $f | tr -d ' '); "
                      "new=$(( (byte + 1) %% 256 )); printf \"\\$(printf %%03o $new)\" | "
                      "dd of=$f bs=1 seek=$off conv=notrunc 2>/dev/null; "
                      "echo flipped $off $byte->$new" % name)
        else:
            script = "truncate -s %d /layerfs/data/store/%s/store.sqlite.incoming" % (total - 1, name)
        rc, out = guest(rid, script)
        return {"rc": rc, "out": out.strip()[:300],
                "incoming": guest_bytes(rid, name, ".incoming"),
                "file": guest_bytes(rid, name)}

    result, hook, row = tamper_at(rid, cid, name, "push", "send", mutate,
                                  cond=lambda p: p.get("done") == p.get("total"))
    evidence(cid, "mutation", hook["mutated"])
    evidence(cid, "after", {"exit": result["exit"], "row": row, "stderr": result["stderr"][:800]})
    check(cid, "the CLI was frozen at the last send event", hook["frozen"], json.dumps(hook["event"]))
    check(cid, "the target's .incoming was altered", (hook["mutated"] or {}).get("rc") == 0,
          json.dumps(hook["mutated"])[:400])
    bad = refusal(result) or {}
    check(cid, "verify refuses the altered copy", result["exit"] == 125 and bad.get("code") == "Failed",
          "exit %s %s" % (result["exit"], json.dumps(bad)[:400]))
    check(cid, "the refusal is the verify phase and names the mismatch",
          (bad.get("detail") or {}).get("phase") == "verify" and "is not the snapshot's" in (bad.get("message") or ""),
          json.dumps(bad)[:500])
    check(cid, "no ownership switch happened", row["machine"] == "native"
          and row["last_transfer_retired"] == retired_before, run_label(row))
    check(cid, "the source copy is untouched", store_sha(name) == sha_before, "%s vs %s" % (store_sha(name), sha_before))
    check(cid, "no Store file was installed on the target", guest_bytes(rid, name) is None,
          str(guest_store_dir(rid, name)["listing"])[:300])
    check(cid, "the altered .incoming is kept as evidence",
          (guest_bytes(rid, name, ".incoming") or 0) > 0, str(guest_bytes(rid, name, ".incoming")))
    report = doctor()
    findings = store_findings(report)
    evidence(cid, "doctor", findings)
    if how == "truncate":
        # a doctor question of its own: can it see the copy a *certain* failure left?
        gap = "R13-%s-DOCTOR-INCOMING" % TAG[rid]
        case(gap, "after a certain verify failure the target keeps a .incoming; is it reported?")
        check(gap, "the refused push left no op (a certain failure drops it)", row["op"] is None, run_label(row))
        check(gap, "the target still holds the partial copy", (guest_bytes(rid, name, ".incoming") or 0) > 0,
              str(guest_bytes(rid, name, ".incoming")))
        check(gap, "doctor reports the partial copy on the machine",
              any("partial" in (f.get("message") or "") for f in findings), json.dumps(findings)[:700])
        check(gap, "doctor names the retry that replaces it",
              any(("store push %s" % name) in (f.get("fix") or "") for f in findings), json.dumps(findings)[:700])
        evidence(gap, "doctor", findings)

    again = ran(cid, call(["store", "push", name, machine, "--progress"], timeout=900, progress=True))
    check(cid, "the same push after the refusal succeeds (offset 0 truncates the stale copy)", again["exit"] == 0,
          again["stderr"][:400])
    last = last_transfer(name)
    check(cid, "the retry's target copy hashes to the record's sha256", guest_sha(rid, name) == last.get("sha256"),
          "%s vs %s" % (guest_sha(rid, name), last.get("sha256")))
    heads_check(cid, "the retry's heads are the original heads", last.get("heads"), heads)
    check(cid, "no stale .incoming is left on the target", guest_bytes(rid, name, ".incoming") in (None, 0),
          str(guest_bytes(rid, name, ".incoming")))
    drop_store(name)


def record_fail_case(rid):
    """R13-<tag>-RECORD-FAIL: the record write cannot happen, both copies stay."""
    cid = "R13-%s-RECORD-FAIL" % TAG[rid]
    machine = MACHINE[rid]
    name = "rf-%s" % TAG[rid].lower()
    case(cid, "store push to %s; the native record write is made to fail at the record phase" % machine)
    reset_home_store(name)
    _, init = new_store(rid, name)
    check(cid, "fixture Store created", init is not None and init["exit"] == 0, (init or {}).get("stderr", "")[:300])
    sha_before = store_sha(name)
    heads = baseline_heads(rid, cid, name)

    def mutate():
        os.chmod(HOME / "store" / name, 0o500)
        return {"chmod": "0500"}

    result, hook, row = tamper_at(rid, cid, name, "push", "record", mutate)
    evidence(cid, "after", {"exit": result["exit"], "row": row, "stderr": result["stderr"][:800]})
    bad = refusal(result) or {}
    check(cid, "the record phase failed and is reported certain-certainty-as-uncertain",
          result["exit"] == 125 and (bad.get("detail") or {}).get("phase") == "record",
          "exit %s %s" % (result["exit"], json.dumps(bad)[:400]))
    check(cid, "the record phase's failure is uncertain (an unresolved intent stays)",
          row["op"] is not None and row["op"]["uncertain"] is True, run_label(row))
    check(cid, "the authority has not switched: the record still names native", row["machine"] == "native",
          run_label(row))
    status = store_status(name) or {}
    check(cid, "store status reads unresolved", status.get("state") == "unresolved",
          json.dumps({"state": status.get("state"), "op": status.get("op")})[:400])
    check(cid, "both copies exist: native's file and the target's installed copy",
          store_sha(name) == sha_before and guest_sha(rid, name) is not None,
          "native %s target %s" % (store_sha(name), guest_sha(rid, name)))
    report = doctor()
    findings = store_findings(report)
    evidence(cid, "doctor", findings)
    check(cid, "doctor reports the unresolved intent as an error", report.get("ok") is False and bool(findings),
          json.dumps(findings)[:600])
    check(cid, "doctor names `layerfs store push %s %s` as the clearing call" % (name, machine),
          any(("store push %s %s" % (name, machine)) in (f.get("fix") or "") for f in findings),
          json.dumps(findings)[:600])

    os.chmod(HOME / "store" / name, 0o700)
    recover(rid, cid, name, "push", heads, None, sha_before)
    drop_store(name)


def retire_fail_case(rid):
    """R13-<tag>-RETIRE-FAIL: the source cannot be retired; the reply must say so."""
    cid = "R13-%s-RETIRE-FAIL" % TAG[rid]
    machine = MACHINE[rid]
    name = "rt-%s" % TAG[rid].lower()
    case(cid, "store push to %s; the native source copy is locked so retire fails" % machine)
    reset_home_store(name)
    _, init = new_store(rid, name)
    check(cid, "fixture Store created", init is not None and init["exit"] == 0, (init or {}).get("stderr", "")[:300])
    sha_before = store_sha(name)
    heads = baseline_heads(rid, cid, name)
    source = store_file(name)

    def mutate():
        done = subprocess.run(["chflags", "uchg", str(source)], capture_output=True, text=True)
        return {"uchg": done.returncode, "out": (done.stdout + done.stderr).strip()[:200]}

    try:
        result, hook, row = tamper_at(rid, cid, name, "push", "record", mutate)
        evidence(cid, "after", {"exit": result["exit"], "row": row, "stderr": result["stderr"][:900]})
        bad = refusal(result) or {}
        detail = bad.get("detail") or {}
        check(cid, "the retire failure is reported (exit 125, code Failed)",
              result["exit"] == 125 and bad.get("code") == "Failed", "exit %s %s" % (result["exit"], json.dumps(bad)[:300]))
        check(cid, "detail carries phase retire, authority %s, source native, retired false" % machine,
              detail.get("phase") == "retire" and detail.get("authority") == machine
              and detail.get("source") == "native" and detail.get("retired") is False, json.dumps(detail)[:400])
        check(cid, "the message says the authority switched and the source was not retired",
              "authority switched to %s" % machine in (bad.get("message") or "")
              and "was not retired" in (bad.get("message") or ""), (bad.get("message") or "")[:400])
        check(cid, "the record names the target machine", row["machine"] == machine, run_label(row))
        last = last_transfer(name)
        check(cid, "last_transfer.retired is false", last.get("retired") is False, json.dumps(last)[:400])
        check(cid, "the Store is usable on %s: its copy is complete and hashes to last_transfer.sha256" % machine,
              guest_sha(rid, name) == last.get("sha256"), "%s vs %s" % (guest_sha(rid, name), last.get("sha256")))
        status = store_status(name) or {}
        check(cid, "store status is idle (the intent is certain) and names the machine",
              status.get("state") == "idle" and status.get("machine") == machine, json.dumps(status)[:400])
        report = doctor()
        findings = store_findings(report)
        evidence(cid, "doctor", findings)
        check(cid, "doctor warns about the copy the retire left",
              any("did not retire" in (f.get("message") or "") for f in findings), json.dumps(findings)[:600])
        check(cid, "doctor names the next call that deletes it",
              any("store pull %s" % name in (f.get("fix") or "") for f in findings), json.dumps(findings)[:600])
        # read-only while retired:false (part of R13-*-READONLY's second state)
        before = tree()
        for _ in range(2):
            store_status(name)
            store_get(name)
            call(["store", "list"])
            doctor()
        after = tree()
        changed = tree_diff(before, after)
        check(cid, "status/get/list/doctor change nothing in the home (retired:false)", not changed, str(changed))
        # the wrong-direction call is refused InvalidInput and leaves the record alone
        wrong = ran(cid, call(["store", "push", name, machine], timeout=600))
        wrong_bad = refusal(wrong) or {}
        check(cid, "a push while the record names the machine is refused InvalidInput",
              wrong["exit"] == 125 and wrong_bad.get("code") in ("InvalidInput", "Failed"),
              "exit %s %s" % (wrong["exit"], json.dumps(wrong_bad)[:300]))
        check(cid, "the refusal did not remove the target's authoritative copy",
              guest_sha(rid, name) == last.get("sha256"), guest_sha(rid, name))
        # the documented recovery: unlock, then pull (the next call deletes the leftover first)
        subprocess.run(["chflags", "nouchg", str(source)], capture_output=True, text=True)
        again = ran(cid, call(["store", "pull", name, "--progress"], timeout=900, progress=True))
        blocking = refusal(again) or {}
        blocked = (rid == "ac" and again["exit"] == 125 and blocking.get("code") == "Unknown"
                   and (blocking.get("detail") or {}).get("phase") == "send")
        if blocked:
            note(cid, "the recovery pull is blocked by the apple-container answer loss (Unknown at send), "
                      "not by the retire failure")
        check(cid, "after unlocking, the next pull deletes the leftover and succeeds", again["exit"] == 0 or blocked,
              again["stderr"][:400])
        check(cid, "the native copy is complete after the pull",
              store_sha(name) == last_transfer(name).get("sha256") or store_sha(name) == last.get("sha256"),
              "%s vs %s" % (store_sha(name), last.get("sha256")))
        heads_check(cid, "heads survive the retire failure and the recovery",
                    last_transfer(name).get("heads"), heads)
        check(cid, "the machine's copy is gone after the pull", guest_bytes(rid, name) is None,
              str(guest_store_dir(rid, name)["listing"])[:200])
        check(cid, "doctor is clean after the recovery", not store_findings(doctor()),
              json.dumps(store_findings(doctor()))[:400])
    finally:
        subprocess.run(["chflags", "nouchg", str(source)], capture_output=True, text=True)
        drop_store(name)


def readonly_case(rid):
    """R13-<tag>-READONLY: an unresolved state and a retired:false state stay untouched."""
    cid = "R13-%s-READONLY" % TAG[rid]
    machine = MACHINE[rid]
    name = "ro-%s" % TAG[rid].lower()
    case(cid, "store status/get/list and doctor read an interrupted transfer without changing anything")
    reset_home_store(name)
    _, init = new_store(rid, name)
    check(cid, "fixture Store created", init is not None and init["exit"] == 0, (init or {}).get("stderr", "")[:300])
    heads = baseline_heads(rid, cid, name)
    result, hook, row = kill_at(rid, cid, name, "push", "send", cond=lambda p: p.get("done") == p.get("total"))
    check(cid, "an interrupted push left the Store in the window the check needs",
          hook["frozen"], json.dumps(hook["event"]))
    state = store_status(name) or {}
    evidence(cid, "state", {"row": row, "status": state})
    check(cid, "the state is idle-or-unresolved with a recorded intent",
          state.get("state") in ("idle", "unresolved") and state.get("op") is not None,
          json.dumps({"state": state.get("state"), "op": state.get("op")})[:300])
    incoming_remote = guest_bytes(rid, name, ".incoming")
    check(cid, "the target holds a partial .incoming the doctor must find", (incoming_remote or 0) > 0,
          str(incoming_remote))
    before = tree()
    results = []
    for _ in range(2):
        results.append(ran(cid, call(["store", "status", name], timeout=300)))
        results.append(ran(cid, call(["store", "get", name], timeout=300)))
        results.append(ran(cid, call(["store", "list"], timeout=300)))
        results.append(ran(cid, call(["doctor"], timeout=600)))
    after = tree()
    changed = tree_diff(before, after)
    evidence(cid, "tree_changes", changed)
    check(cid, "every read call exited 0", all(r["exit"] == 0 for r in results),
          str([r["exit"] for r in results]))
    check(cid, "the home is untouched: same paths, modes, sizes, mtimes and bytes", not changed, str(changed))
    report = results[-1]["json"] or {}
    findings = store_findings(report)
    evidence(cid, "doctor", findings)
    check(cid, "doctor finds the remote .incoming and its byte count",
          any("partial copy" in (f.get("message") or "") and str(incoming_remote) in (f.get("message") or "")
              for f in findings), json.dumps(findings)[:700])
    check(cid, "doctor's fix is the same push (or a hand deletion)",
          any(("store push %s %s" % (name, machine)) in (f.get("fix") or "") for f in findings),
          json.dumps(findings)[:700])
    check(cid, "no lock is created and no stale lease removed: layerfs.lock is unchanged",
          before.get("layerfs.lock") == after.get("layerfs.lock"),
          str(before.get("layerfs.lock")) + " -> " + str(after.get("layerfs.lock")))
    recover(rid, cid, name, "push", heads, None, None)
    drop_store(name)


def reverse_case(rid, other=None):
    """R13-<tag>-REVERSE: the opposite direction is refused and deletes nothing."""
    cid = "R13-%s-REVERSE" % TAG[rid]
    machine = MACHINE[rid]
    name = "rv-%s" % TAG[rid].lower()
    case(cid, "a push interrupted at install leaves Unresolved; the opposite direction and another target are refused")
    reset_home_store(name)
    _, init = new_store(rid, name)
    check(cid, "fixture Store created", init is not None and init["exit"] == 0, (init or {}).get("stderr", "")[:300])
    heads = baseline_heads(rid, cid, name)
    result, hook, row = kill_at(rid, cid, name, "push", "record")
    state = store_status(name) or {}
    evidence(cid, "state", {"row": row, "status": state, "freeze": hook["row_at_freeze"]})
    check(cid, "the interruption left an unresolved intent", state.get("state") == "unresolved",
          json.dumps({"state": state.get("state"), "op": state.get("op")})[:400])
    check(cid, "the record still names native, both copies exist",
          row["machine"] == "native" and store_file(name).is_file()
          and (guest_bytes(rid, name) is not None or (guest_bytes(rid, name, ".incoming") or 0) > 0),
          run_label(row))
    before_home = tree()
    before_guest = guest_store_dir(rid, name)
    before_sha = store_sha(name)
    before_remote = guest_sha(rid, name)
    interrupted = row["op"]

    pull = ran(cid, call(["store", "pull", name], timeout=600))
    bad = refusal(pull) or {}
    check(cid, "the opposite direction (pull) is refused Unresolved",
          pull["exit"] == 125 and bad.get("code") == "Unresolved",
          "exit %s %s" % (pull["exit"], json.dumps(bad)[:400]))
    check(cid, "the refusal names the clearing call `layerfs store push %s %s`" % (name, machine),
          ("store push %s %s" % (name, machine)) in (bad.get("message") or ""), (bad.get("message") or "")[:400])
    check(cid, "the refusal names the intent in detail (entity, op id, the refusing phase)",
          (bad.get("detail") or {}).get("op") == interrupted.get("id")
          and ((bad.get("detail") or {}).get("entity") or {}).get("name") == name,
          json.dumps(bad.get("detail"))[:400])
    check(cid, "the message names the recorded phase and the clearing call",
          ("phase %s" % interrupted["phase"]) in (bad.get("message") or ""), (bad.get("message") or "")[:400])
    after_home = tree()
    check(cid, "the refusal deleted nothing in the home", not tree_diff(before_home, after_home),
          str(tree_diff(before_home, after_home)))
    check(cid, "the refusal deleted nothing on the machine", guest_store_dir(rid, name) == before_guest,
          json.dumps({"before": before_guest["listing"], "after": guest_store_dir(rid, name)["listing"]})[:400])
    check(cid, "both copies are byte-identical after the refusal",
          store_sha(name) == before_sha and guest_sha(rid, name) == before_remote, "copies intact")

    if other:
        other_machine = MACHINE[other]
        push_other = ran(cid, call(["store", "push", name, other_machine], timeout=600))
        bad_other = refusal(push_other) or {}
        check(cid, "a push to another machine (%s) is refused Unresolved too" % other_machine,
              push_other["exit"] == 125 and bad_other.get("code") == "Unresolved",
              "exit %s %s" % (push_other["exit"], json.dumps(bad_other)[:300]))
        check(cid, "the mismatched target deleted nothing either",
              guest_store_dir(rid, name) == before_guest and store_sha(name) == before_sha, "copies intact")

    first = ran(cid, call(["store", "push", name, machine, "--progress"], timeout=900, progress=True))
    check(cid, "the clearing call (the same push) succeeds", first["exit"] == 0, first["stderr"][:400])
    second = ran(cid, call(["store", "push", name, machine], timeout=600))
    check(cid, "a second identical push is refused (the Store already moved)",
          second["exit"] == 125 and (refusal(second) or {}).get("code") == "InvalidInput",
          "exit %s %s" % (second["exit"], json.dumps(refusal(second))[:300]))
    last = last_transfer(name)
    check(cid, "exactly one copy exists and it hashes to the record",
          guest_sha(rid, name) == last.get("sha256") and not store_file(name).exists(),
          "target %s source %s" % (guest_sha(rid, name), store_file(name)))
    heads_check(cid, "heads did not change", last.get("heads"), heads)
    check(cid, "no second copy was produced", guest_bytes(rid, name, ".incoming") in (None, 0),
          str(guest_bytes(rid, name, ".incoming")))
    drop_store(name)


def concurrent_case(rid):
    """R13-<tag>-CONCURRENT: one authoritative writer; the second transfer is Busy."""
    cid = "R13-%s-CONCURRENT" % TAG[rid]
    machine = MACHINE[rid]
    name = "cc-%s" % TAG[rid].lower()
    case(cid, "two pushes of the same Store and a store remove while one runs")
    reset_home_store(name)
    _, init = new_store(rid, name)
    check(cid, "fixture Store created", init is not None and init["exit"] == 0, (init or {}).get("stderr", "")[:300])
    held = {}

    def first():
        held["result"] = call(["store", "push", name, machine, "--progress"], progress=True, timeout=900)

    thread = threading.Thread(target=first)
    thread.start()
    seen, deadline = None, time.time() + 30
    while time.time() < deadline and thread.is_alive():
        op = op_of(name)
        if op and op.get("phase") in ("send", "snapshot", "verify"):
            seen = op
            break
        time.sleep(0.005)
    evidence(cid, "op_seen", seen)
    check(cid, "a first transfer is running", seen is not None, json.dumps(seen)[:300])
    second = ran(cid, call(["store", "push", name, machine], timeout=600))
    bad = refusal(second) or {}
    check(cid, "the overlapping push is refused Busy",
          second["exit"] == 125 and bad.get("code") == "Busy", "exit %s %s" % (second["exit"], json.dumps(bad)[:400]))
    check(cid, "the Busy detail names the running op and its process",
          "runs in process" in (bad.get("message") or ""), (bad.get("message") or "")[:300])
    removing = ran(cid, call(["store", "remove", name], timeout=600))
    bad_remove = refusal(removing) or {}
    check(cid, "store remove during the transfer is refused Busy",
          removing["exit"] == 125 and bad_remove.get("code") == "Busy",
          "exit %s %s" % (removing["exit"], json.dumps(bad_remove)[:300]))
    thread.join(900)
    first_result = held.get("result") or {"argv": [], "exit": None, "seconds": 0, "stderr": ""}
    ran(cid, first_result)
    check(cid, "the first transfer succeeded", first_result["exit"] == 0, first_result["stderr"][:300])
    last = last_transfer(name)
    check(cid, "only one copy is authoritative and it hashes to the record",
          guest_sha(rid, name) == last.get("sha256") and not store_file(name).exists(),
          "target %s source exists=%s" % (guest_sha(rid, name), store_file(name).exists()))
    check(cid, "no partial copy is left behind", guest_bytes(rid, name, ".incoming") in (None, 0),
          str(guest_bytes(rid, name, ".incoming")))
    # a Sandbox of the project on the machine refuses the pull (InUse)
    sandbox = "sb-" + name
    made = ran(cid, call(["sandbox", "create", "%s/p1" % name, sandbox, machine], timeout=900))
    check(cid, "a Sandbox of the project runs on the machine", made["exit"] == 0, made["stderr"][:300])
    pulled = ran(cid, call(["store", "pull", name], timeout=600))
    bad_pull = refusal(pulled) or {}
    check(cid, "the pull is refused InUse while the Sandbox is recorded",
          pulled["exit"] == 125 and bad_pull.get("code") == "InUse",
          "exit %s %s" % (pulled["exit"], json.dumps(bad_pull)[:400]))
    related = ((bad_pull.get("detail") or {}).get("related") or [])
    check(cid, "detail.related names the Sandbox",
          any(item.get("kind") == "sandbox" and item.get("name") == sandbox for item in related),
          json.dumps(related))
    call(["sandbox", "close", sandbox], timeout=900)
    dropped = ran(cid, call(["store", "remove", name], timeout=900))
    check(cid, "store remove succeeds once nothing runs", dropped["exit"] == 0, dropped["stderr"][:300])
    check(cid, "the machine's copy is gone with the Store", guest_bytes(rid, name) is None, "target absent")
    check(cid, "the machine itself still exists", call(["machine", "status", machine])["exit"] == 0, machine)


def remove_case(rid):
    """R13-<tag>-REMOVE: store remove clears the home record and the machine's orphan."""
    cid = "R13-%s-REMOVE" % TAG[rid]
    machine = MACHINE[rid]
    name = "rm-%s" % TAG[rid].lower()
    other = "rm-%s-keep" % TAG[rid].lower()
    case(cid, "store remove after an interrupted push that left a copy on the machine")
    reset_home_store(name)
    reset_home_store(other)
    _, init = new_store(rid, name)
    check(cid, "fixture Store created", init is not None and init["exit"] == 0, (init or {}).get("stderr", "")[:300])
    _, init_other = new_store(rid, other)
    check(cid, "a second Store of the same machine exists", init_other is not None and init_other["exit"] == 0,
          (init_other or {}).get("stderr", "")[:200])
    sent_other = ran(cid, call(["store", "push", other, machine], timeout=900))
    check(cid, "the second Store sits on the machine", sent_other["exit"] == 0, sent_other["stderr"][:300])
    result, hook, row = kill_at(rid, cid, name, "push", "record")
    state = store_status(name) or {}
    evidence(cid, "state", {"row": row, "status": state})
    check(cid, "the interrupt left an unresolved intent", state.get("state") == "unresolved",
          json.dumps({"state": state.get("state"), "op": state.get("op")})[:300])
    target_listing = guest_store_dir(rid, name)["listing"]
    check(cid, "the machine holds a leftover copy to clean", bool(target_listing.strip()), target_listing[:300])
    other_before = guest_sha(rid, other) or "absent"
    other_heads = (last_transfer(other) or {}).get("heads")
    removed = ran(cid, call(["store", "remove", name], timeout=900))
    check(cid, "store remove succeeds on the unresolved Store", removed["exit"] == 0, removed["stderr"][:400])
    check(cid, "the home's Store record and file folder are gone", not (HOME / "store" / name).exists(),
          str((HOME / "store" / name).exists()))
    check(cid, "the machine's copy is gone too", not guest_store_dir(rid, name)["listing"].strip(),
          guest_store_dir(rid, name)["listing"][:300])
    check(cid, "the machine and its record are still there", call(["machine", "status", machine])["exit"] == 0, machine)
    check(cid, "another Store of the same machine is untouched",
          (guest_sha(rid, other) or "absent") == other_before, "%s" % other_before)
    check(cid, "its record still names the machine", machine_of(other) == machine, str(machine_of(other)))
    check(cid, "its heads are unchanged", (last_transfer(other) or {}).get("heads") == other_heads,
          str(other_heads))
    check(cid, "it still answers store status", store_status(other).get("state") == "idle",
          json.dumps(store_status(other))[:300])
    report = doctor()
    findings = [f for f in store_findings(report) if (f.get("entity") or {}).get("name") == name]
    evidence(cid, "doctor", findings)
    check(cid, "doctor has no finding for the removed Store", not findings, json.dumps(findings)[:400])
    drop_store(other)

    # a certain interruption (before install) is not a "copy" the record knows:
    # does store remove still clean the machine's orphan .incoming?
    gap = "R13-%s-REMOVE-CERTAIN" % TAG[rid]
    name = "rc-%s" % TAG[rid].lower()
    case(gap, "store remove after an interruption the record dropped (op certain at send)")
    reset_home_store(name)
    _, init = new_store(rid, name)
    kill_at(rid, gap, name, "push", "send", cond=lambda p: (p.get("done") or 0) > 0)
    row = observed(name)
    check(gap, "the interrupted process left its certain intent behind (it was killed, not failed)",
          row["op"] is not None and row["op"]["uncertain"] is False, run_label(row))
    check(gap, "the machine holds the orphan .incoming", (guest_bytes(rid, name, ".incoming") or 0) > 0,
          str(guest_bytes(rid, name, ".incoming")))
    removed = ran(gap, call(["store", "remove", name], timeout=900))
    check(gap, "store remove itself succeeds", removed["exit"] == 0, removed["stderr"][:300])
    check(gap, "the machine's orphan .incoming is cleared by store remove",
          not guest_store_dir(rid, name)["listing"].strip(),
          guest_store_dir(rid, name)["listing"][:400])
    if guest_store_dir(rid, name)["listing"].strip():
        guest_remove(rid, name)
    reset_home_store(name)


def lost_answer_case(rid):
    """R13-<tag>-LOST-ANSWER: the worker is gone when a step needs it.

    A worker stopped before the step's request goes out is `Unavailable`:
    the request is never sent and nothing is left behind. That is the honest
    outcome the CLI reports, and the same push works once the machine is back.
    """
    cid = "R13-%s-LOST-ANSWER" % TAG[rid]
    machine = MACHINE[rid]
    name = "la-%s" % TAG[rid].lower()
    case(cid, "store push to %s; the worker is stopped as install's request is due" % machine)
    reset_home_store(name)
    _, init = new_store(rid, name)
    check(cid, "fixture Store created", init is not None and init["exit"] == 0, (init or {}).get("stderr", "")[:300])
    heads = baseline_heads(rid, cid, name)
    sha_before = store_sha(name)

    def mutate():
        rc, out = worker_signal(rid, "STOP")
        return {"stop": rc, "out": out.strip()[:60]}

    def after():
        time.sleep(0.25)
        rc, out = worker_signal(rid, "KILL")
        note(cid, "the worker was killed after the request: %s" % out.strip()[:80])

    result, hook, row = tamper_at(rid, cid, name, "push", "install", mutate, after=after)
    evidence(cid, "after", {"exit": result["exit"], "row": row, "stderr": result["stderr"][-700:],
                            "mutation": hook["mutated"]})
    bad = refusal(result) or {}
    check(cid, "the step is refused because the worker did not answer",
          result["exit"] == 125 and bad.get("code") == "Unavailable",
          "exit %s %s" % (result["exit"], json.dumps(bad)[:400]))
    check(cid, "the refusal says the request was not sent (nothing to be uncertain about)",
          "was not sent" in (bad.get("message") or ""), (bad.get("message") or "")[:400])
    check(cid, "no intent is left behind (a certain failure drops it)", row["op"] is None, run_label(row))
    check(cid, "the record still names native", row["machine"] == "native", run_label(row))
    check(cid, "the native source is intact", store_sha(name) == sha_before, "sha equal")
    restarted = ran(cid, machine_start(machine))
    check(cid, "machine start brings the worker back", restarted["exit"] == 0, restarted["stderr"][:300])
    resolve_guest(rid)
    check(cid, "the restarted guest answers", wait_guest(rid), "guest ready")
    recover(rid, cid, name, "push", heads, None, sha_before)
    drop_store(name)


def lost_retire_case(rid):
    """R13-<tag>-LOST-RETIRE: a pull's retire runs in the worker; its answer is lost."""
    cid = "R13-%s-LOST-RETIRE" % TAG[rid]
    machine = MACHINE[rid]
    name = "lr-%s" % TAG[rid].lower()
    case(cid, "store pull from %s; the worker dies as retire's request goes out" % machine)
    reset_home_store(name)
    _, init = new_store(rid, name)
    check(cid, "fixture Store created", init is not None and init["exit"] == 0, (init or {}).get("stderr", "")[:300])
    heads = baseline_heads(rid, cid, name)
    sent = ran(cid, call(["store", "push", name, machine], timeout=900))
    check(cid, "the Store is on the machine before the pull", sent["exit"] == 0, sent["stderr"][:300])
    remote_sha = guest_sha(rid, name)

    def after():
        time.sleep(0.001)
        rc, out = worker_signal(rid, "KILL")
        note(cid, "the worker was killed 1 ms after retire's event: %s" % out.strip()[:80])

    result, hook, row = tamper_at(rid, cid, name, "pull", "retire", None, after=after)
    evidence(cid, "after", {"exit": result["exit"], "row": row, "stderr": result["stderr"][-700:]})
    bad = refusal(result) or {}
    detail = bad.get("detail") or {}
    if result["exit"] == 0:
        note(cid, "the retire finished before the worker died: the window was missed, recorded as such")
        check(cid, "either the retire lost its answer or it finished first (both are truthful)",
              row["machine"] == "native" and row["op"] is None, run_label(row))
        drop_store(name)
        return
    check(cid, "the lost retire answer is Unknown", bad.get("code") == "Unknown", json.dumps(bad)[:400])
    check(cid, "the reply says the authority is native and the machine's copy was not retired",
          detail.get("authority") == "native" and detail.get("source") == machine
          and detail.get("retired") is False and detail.get("phase") == "retire",
          json.dumps(detail)[:400])
    check(cid, "the record names native", row["machine"] == "native", run_label(row))
    last = last_transfer(name)
    check(cid, "native's copy is complete and matches the record",
          store_sha(name) == last.get("sha256"), "%s vs %s" % (store_sha(name), last.get("sha256")))
    check(cid, "the machine's copy is still there (the retire did not run)",
          guest_sha(rid, name) == remote_sha, guest_sha(rid, name))
    restarted = ran(cid, machine_start(machine))
    check(cid, "machine start brings the worker back", restarted["exit"] == 0, restarted["stderr"][:300])
    resolve_guest(rid)
    wait_guest(rid)
    # the next call in the record's direction (a push) deletes the leftover first
    again = ran(cid, call(["store", "push", name, machine, "--progress"], timeout=900, progress=True))
    check(cid, "the next push deletes the leftover and succeeds", again["exit"] == 0, again["stderr"][:400])
    last = last_transfer(name)
    check(cid, "the machine's copy is the record's and native's is retired",
          guest_sha(rid, name) == last.get("sha256") and not store_file(name).exists(), guest_sha(rid, name))
    check(cid, "heads survive the lost retire answer", last.get("heads") == heads,
          "%s vs %s" % (last.get("heads"), heads))
    drop_store(name)


# ---------------------------------------------------------------------- setup


def setup():
    HOME.mkdir(mode=0o700, parents=True, exist_ok=True)
    (BASE / "receipts").mkdir(parents=True, exist_ok=True)
    steps = [(["machine", "update", "docker", "--docker", os.environ.get("LP08_DOCKER_SOCK", str(Path.home() / ".colima/default/docker.sock"))], 300),
             (["machine", "update", "native", "--daemon", DAEMON], 300)]
    for argv, timeout in steps:
        result = call(argv, timeout=timeout)
        print(argv, "->", result["exit"], result["stderr"][:200])
    (BASE / "receipts" / "platforms.json").write_text(json.dumps(call(["machine", "platforms"])["json"], indent=1))


def route_full(rid, other=None):
    """The full #13 suite for one route."""
    global GUEST
    status, handle = ensure_machine(rid)
    case("R13-%s-SETUP" % TAG[rid], "machine %s is running" % MACHINE[rid])
    check("R13-%s-SETUP" % TAG[rid], "machine status is running",
          (status or {}).get("state") == "running", json.dumps(status)[:300])
    check("R13-%s-SETUP" % TAG[rid], "guest handle resolved", bool(handle), str(handle))
    for label, trigger in [("check", None), ("snapshot", None), ("send", None), ("verify", None),
                           ("install-entry", "install"), ("install", "record"), ("retire", "retire")]:
        phase_kill_case(rid, label, trigger)
    pull_kill_case(rid, "send")
    pull_kill_case(rid, "install", "record")
    tamper_case(rid, "flip")
    tamper_case(rid, "truncate")
    record_fail_case(rid)
    retire_fail_case(rid)
    readonly_case(rid)
    reverse_case(rid, other=other)
    concurrent_case(rid)
    remove_case(rid)
    lost_answer_case(rid)
    lost_retire_case(rid)


def ac_pull_defect(rid):
    """R13-A-AC-PULL: the apple-container pull that loses the worker's answer.

    LP08-S1 found it intermittently at `send`; this records what #13's table
    says such an outcome must look like: Unknown, uncertain at `send`, both
    copies kept, Doctor's clearing call, and the same pull as the recovery.
    """
    cid = "R13-A-AC-PULL"
    machine = MACHINE[rid]
    name = "acpull"
    case(cid, "store pull from apple-container: an Unknown at send leaves a recoverable unresolved intent")
    reset_home_store(name)
    _, init = new_store(rid, name)
    check(cid, "fixture Store created", init is not None and init["exit"] == 0, (init or {}).get("stderr", "")[:300])
    pushed = ran(cid, call(["store", "push", name, machine], timeout=900))
    check(cid, "push succeeds (the direction that never fails on this route)", pushed["exit"] == 0,
          pushed["stderr"][:300])
    heads = last_transfer(name).get("heads")
    remote_sha = guest_sha(rid, name)
    attempts, failures = [], []
    for _ in range(4):
        pulled = ran(cid, call(["store", "pull", name], timeout=900))
        bad = refusal(pulled) or {}
        state = store_status(name) or {}
        attempts.append({"exit": pulled["exit"], "code": bad.get("code"),
                         "state": state.get("state"), "phase": ((state.get("op") or {}).get("phase")),
                         "uncertain": ((state.get("op") or {}).get("uncertain"))})
        if pulled["exit"] == 0:
            break
        failures.append(bad)
        check(cid, "a failed pull is Unknown at send", bad.get("code") == "Unknown"
              and (bad.get("detail") or {}).get("phase") == "send", json.dumps(bad)[:400])
        check(cid, "the failed pull leaves an unresolved, uncertain intent",
              state.get("state") == "unresolved" and (state.get("op") or {}).get("uncertain") is True,
              json.dumps({"state": state.get("state"), "op": state.get("op")})[:400])
        check(cid, "the machine's copy is untouched by the lost answer", guest_sha(rid, name) == remote_sha,
              guest_sha(rid, name))
        findings = store_findings(doctor())
        check(cid, "doctor reports the unresolved pull and names `layerfs store pull %s`" % name,
              any("unresolved" in (f.get("message") or "") and ("store pull %s" % name) in (f.get("fix") or "")
                  for f in findings), json.dumps(findings)[:600])
        guest_remove(rid, name) if False else None
    evidence(cid, "attempts", attempts)
    note(cid, "%d of %d pulls lost the worker's answer at send (LP08-S1's apple-container defect), "
              "each one recoverable with the same command" % (len(failures), len(attempts)))
    check(cid, "the same pull eventually completes, or every attempt is the same Unknown",
          attempts[-1]["exit"] == 0 or all((f or {}).get("code") == "Unknown" for f in failures),
          json.dumps(attempts)[:400])
    if attempts[-1]["exit"] == 0:
        last = last_transfer(name)
        check(cid, "after the recovery native holds the Store and the record agrees",
              store_sha(name) == last.get("sha256") and last.get("retired") is True,
              "%s vs %s" % (store_sha(name), last.get("sha256")))
        check(cid, "heads are unchanged by the retries", last.get("heads") == heads,
              "%s vs %s" % (last.get("heads"), heads))
    drop_store(name)


def route_sampled(rid, other=None):
    """The sampled #13 suite for lima / apple-container."""
    global GUEST
    status, handle = ensure_machine(rid)
    case("R13-%s-SETUP" % TAG[rid], "machine %s is running" % MACHINE[rid])
    check("R13-%s-SETUP" % TAG[rid], "machine status is running", (status or {}).get("state") == "running",
          json.dumps(status)[:300])
    check("R13-%s-SETUP" % TAG[rid], "guest handle resolved", bool(handle), str(handle))
    phase_kill_case(rid, "send")
    phase_kill_case(rid, "install", "record")
    if rid == "ac":
        ac_pull_defect(rid)
    else:
        pull_kill_case(rid, "send")
        pull_kill_case(rid, "install", "record")
    tamper_case(rid, "truncate")
    retire_fail_case(rid)
    readonly_case(rid)
    reverse_case(rid, other=other)
    remove_case(rid)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "report"
    rid = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        if what == "setup":
            setup()
        elif what == "route":
            route_full(rid) if rid == "docker" else route_sampled(rid, "docker")
        elif what == "only":
            name = sys.argv[3]
            ensure_machine(rid)
            {"kill": lambda: phase_kill_case(rid, sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else None),
             "pullkill": lambda: pull_kill_case(rid, sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else None),
             "tamper": lambda: tamper_case(rid, sys.argv[4]),
             "record": lambda: record_fail_case(rid),
             "retire": lambda: retire_fail_case(rid),
             "readonly": lambda: readonly_case(rid),
             "reverse": lambda: reverse_case(rid, other=(sys.argv[4] if len(sys.argv) > 4 else None)),
             "concurrent": lambda: concurrent_case(rid),
             "remove": lambda: remove_case(rid),
             "lost": lambda: lost_answer_case(rid),
             "lostretire": lambda: lost_retire_case(rid)}[name]()
        elif what == "report":
            pass
        else:
            raise SystemExit("unknown phase " + what)
    except Exception:
        traceback.print_exc()
        note("R13-%s-SETUP" % (TAG.get(rid, "X")), "phase aborted: " + traceback.format_exc().splitlines()[-1])
    finally:
        save()
        for cid in sorted(CASES):
            print("%-28s %-7s %d checks" % (cid, verdict(cid), len(CASES[cid]["checks"])))
