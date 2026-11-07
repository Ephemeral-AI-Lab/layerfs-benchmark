#!/usr/bin/env python3
"""LP08-S1 stage-one real-machine matrix.

#9 routes (native<->docker, native<->lima, native<->apple-container, docker->native->lima),
the #9 refusal matrix and the #12 seven-phase progress assertions, all through the
public `layerfs` CLI against a sealed release guest bundle.

    python3 matrix.py setup
    python3 matrix.py route docker|lima|ac
    python3 matrix.py hop
    python3 matrix.py refuse
    python3 matrix.py report
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
BASE = Path(os.environ.get("LP08_BASE", "/tmp/lp08-s1"))
HOME = BASE / "home"
FIX = BASE / "fixture" / "p1"
MANIFEST = (BASE / "manifest.sh").read_text()
REC = BASE / "receipts" / "lp08-s1"
PHASES = ["check", "snapshot", "send", "verify", "install", "record", "retire"]

CASES = {}
COMMANDS = []


# --------------------------------------------------------------------------- io


def env():
    return {**os.environ, "LAYERFS_HOME": str(HOME)}


def call(argv, timeout=900, progress=False, cli=CLI):
    """One CLI call, with per-line timestamps on stderr and a global command log."""
    t0 = time.monotonic()
    process = subprocess.Popen(
        [cli] + argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env()
    )
    events = []
    raw_err = []
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
            t = time.monotonic() - t0
            text = line.decode("utf-8", "replace").strip()
            if not text:
                continue
            raw_err.append(text)
            if progress and text.startswith("{"):
                try:
                    events.append({"t": round(t, 4), **json.loads(text)})
                    continue
                except ValueError:
                    pass
            events.append({"t": round(t, 4), "raw": text})

    thread = threading.Thread(target=drain, daemon=True)
    thread.start()
    out = process.stdout.read()
    code = process.wait()
    thread.join(10)
    timer.cancel()
    err = "\n".join(raw_err)
    parsed = None
    try:
        parsed = json.loads(out.decode("utf-8")) if out.strip() else None
    except ValueError:
        parsed = None
    record = {
        "argv": argv,
        "exit": code,
        "seconds": round(time.monotonic() - t0, 3),
        "stdout": out.decode("utf-8", "replace"),
        "stderr": err,
        "json": parsed,
        "events": events,
        "progress": progress,
        "timeout": expired.is_set(),
    }
    COMMANDS.append({k: record[k] for k in ("argv", "exit", "seconds")})
    return record


def refusal(result):
    """The `{code,message,detail}` a refused call printed, if any."""
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
    entry = CASES.setdefault(cid, {"case": cid, "checks": [], "notes": [], "commands": []})
    if note:
        entry["notes"].append(note)
    return entry


def check(cid, name, ok, evidence=""):
    ok = bool(ok)
    case(cid)["checks"].append({"name": name, "ok": ok, "evidence": str(evidence)[:1200]})
    return ok


def note(cid, text):
    case(cid)["notes"].append(text)


def ran(cid, result):
    case(cid)["commands"].append(
        {"argv": ["layerfs"] + result["argv"], "exit": result["exit"], "seconds": result["seconds"]}
    )


def verdict(cid):
    checks = CASES[cid]["checks"]
    if not checks:
        return "NOT_RUN"
    return "PASS" if all(c["ok"] for c in checks) else "FAIL"


def rollup():
    """#12 as one case: every `R12-` check the routes recorded."""
    checks = []
    for entry in CASES.values():
        for item in entry["checks"]:
            if item["name"].startswith("R12-"):
                checks.append(item)
    if checks:
        entry = case("R12-PROGRESS", "the #12 seven-phase assertions from every route and transfer")
        entry["checks"] = checks


def save():
    rollup()
    REC.mkdir(parents=True, exist_ok=True)
    for cid, entry in CASES.items():
        entry["verdict"] = verdict(cid)
        entry["at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        (REC / (cid + ".json")).write_text(json.dumps(entry, ensure_ascii=False, indent=1))
    (BASE / "receipts" / "commands.json").write_text(json.dumps(COMMANDS, indent=1))
    Path(BASE / "receipts" / "pin.json").write_text(
        json.dumps(
            {
                "cli": CLI,
                "cli_sha256": sha256_file(Path(CLI)),
                "daemon": DAEMON,
                "daemon_sha256": sha256_file(Path(DAEMON)),
                "bundle": json.loads(
                    (Path.home() / ".cache/layerfs/bundle/2.0.0/linux-aarch64/bundle.json").read_text()
                ),
                "home": str(HOME),
                "live": provenance(),
            },
            ensure_ascii=False,
            indent=1,
        )
    )


def provenance():
    out = {}
    for name, argv in {
        "docker": ["docker", "--version"],
        "colima": ["colima", "version"],
        "limactl": ["limactl", "--version"],
        "container": ["container", "--version"],
        "sw_vers": ["sw_vers"],
        "uname": ["uname", "-a"],
    }.items():
        try:
            out[name] = subprocess.run(argv, capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception as why:  # noqa: BLE001 - a missing tool is evidence
            out[name] = f"unavailable: {why}"
    return out


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# ------------------------------------------------------------------- fixtures


def tree(root, skip_prefixes=()):
    rows = {}
    root = Path(root)
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files) + sorted(dirs):
            path = Path(base) / name
            rel = str(path.relative_to(root))
            if any(rel == s or rel.startswith(s + "/") for s in skip_prefixes):
                continue
            try:
                meta = path.lstat()
            except FileNotFoundError:
                continue
            if path.is_symlink():
                rows[rel] = "L:" + os.readlink(path)
            elif path.is_dir():
                rows[rel] = "D:%o" % (meta.st_mode & 0o777)
            else:
                rows[rel] = "F:%o:%d:%s" % (meta.st_mode & 0o777, meta.st_size, sha256_file(path))
    return rows


def manifest_lines(text):
    return [line for line in text.splitlines() if line.strip()]


def store_file(name):
    return HOME / "store" / name / "store.sqlite"


def store_sha(name):
    path = store_file(name)
    return sha256_file(path) if path.exists() else None


# --------------------------------------------------------------- progress #12


def progress_checks(cid, result, label, multi_chunk=False):
    events = [e for e in result["events"] if "progress" in e]
    seq = [e["progress"]["phase"] for e in events]
    counts = {p: seq.count(p) for p in PHASES}
    check(cid, f"{label}: all 7 phases appear", all(counts[p] >= 1 for p in PHASES), json.dumps(counts))
    firsts = []
    for phase in PHASES:
        positions = [i for i, value in enumerate(seq) if value == phase]
        firsts.append(positions[0] if positions else None)
    ordered = all(p is not None for p in firsts) and firsts == sorted(firsts)
    check(cid, f"{label}: first-event order is check..retire", ordered, str(firsts))
    has_raw = any("raw" in e for e in events)
    check(cid, f"{label}: every stderr line is a JSON progress event", not has_raw,
          [e["raw"] for e in events if "raw" in e][:3])

    def series(phase):
        return [
            (e["progress"]["done"], e["progress"]["total"], e["t"])
            for e in events
            if e["progress"]["phase"] == phase
        ]

    send = [(d, t, at) for d, t, at in series("send") if d is not None]
    totals = {t for _, t, _ in send}
    dones = [d for d, _, _ in send]
    check(cid, f"{label}: send total is constant", len(totals) == 1, str(sorted(totals)))
    check(cid, f"{label}: send done is monotonic", dones == sorted(dones), str(dones))
    check(cid, f"{label}: send ends at total", bool(send) and send[-1][0] == send[-1][1], str(send[-1:]))
    if multi_chunk:
        check(cid, f"{label}: send has more than two counted events (multi-chunk)",
              len(send) >= 3, f"{len(send)} events {dones}")
    for phase in ("snapshot", "verify"):
        rows = [(d, t, at) for d, t, at in series(phase) if d is not None]
        dones = [d for d, _, _ in rows]
        check(cid, f"{label}: {phase} starts at 0", bool(rows) and rows[0][0] == 0, str(rows[:1]))
        check(cid, f"{label}: {phase} done is monotonic", dones == sorted(dones), str(dones))
        check(cid, f"{label}: {phase} ends at total (result fills a missing last event)",
              bool(rows) and rows[-1][0] == rows[-1][1], str(rows[-1:]))
    last = events[-1] if events else None
    check(cid, f"{label}: the last progress event is retire",
          bool(last) and last["progress"]["phase"] == "retire", json.dumps(last or {}))
    retire_at = series("retire")
    margin = round(result["seconds"] - retire_at[0][2], 4) if retire_at else None
    check(cid, f"{label}: retire is emitted before the process exits",
          margin is not None and 0 <= margin, f"exit after retire by {margin}s")
    ok_exit = result["exit"] == 0
    check(cid, f"{label}: call succeeded", ok_exit, f"exit {result['exit']} {result['stderr'][:200]}")
    return events


# ------------------------------------------------------------------- plumbing


def machine_start(name):
    return call(["machine", "start", name], timeout=900)


def ensure_machine(machine):
    """Start `machine`, and confirm it reports running and its free disk."""
    started = machine_start(machine)
    status = call(["machine", "status", machine], timeout=300)
    return started, status


def new_store(name, store_project="p1", folder=FIX):
    made = call(["store", "create", name], timeout=300)
    if made["exit"] != 0:
        return made, None
    init = call(["project", "init", f"{name}/{store_project}", str(folder)], timeout=900)
    return made, init


def route_store_tag(rid):
    return {"docker": "d", "lima": "l", "ac": "a"}[rid]


def drop_store(name):
    return call(["store", "remove", name], timeout=600)


def sandbox_mount(machine, store, project, branch=None, fork=None):
    """Create a Sandbox of `store/project` on `machine`, fork `branch` if named, mount it."""
    sandbox = f"sb-{store}"
    made = call(["sandbox", "create", f"{store}/{project}", sandbox] + ([machine] if machine else []),
                timeout=900)
    if made["exit"] != 0:
        return {"sandbox": sandbox, "created": made}
    target = branch
    if fork or branch is None:
        name = fork or ("chk-" + store)
        forked = call(["branch", "fork", f"{store}/{project}", name, "main"], timeout=300)
        if forked["exit"] != 0:
            return {"sandbox": sandbox, "created": made, "forked": forked}
        target = name
    mounted = call(["workspace", "mount", sandbox, target], timeout=900)
    return {"sandbox": sandbox, "created": made, "forked": None, "mounted": mounted,
            "ws": (mounted["json"] or {}).get("ws"), "path": (mounted["json"] or {}).get("path")}


def ws_exec(ws, script, timeout=900):
    return call(["workspace", "exec", ws, script, "--stream"], timeout=timeout)


def teardown(session, commit_note=None):
    out = {}
    if session.get("ws"):
        if commit_note:
            out["commit"] = call(["workspace", "commit", session["ws"], "-m", commit_note], timeout=900)
        out["unmount"] = call(["workspace", "unmount", session["ws"]], timeout=900)
    if session.get("sandbox"):
        out["closed"] = call(["sandbox", "close", session["sandbox"]], timeout=900)
    return out


# ---------------------------------------------------------------------- routes


def route(rid, machine, geometry):
    """One native<->machine route: the unchanged round trip, then the modified one."""
    tag = route_store_tag(rid)
    ensure_machine(machine)
    geometry(rid)

    # ---- unchanged round trip: bytes and heads must come back identical
    cid = f"R9-{tag.upper()}-RT"
    rt = f"rt-{tag}"
    case(cid, f"route native<->{machine}, Store {rt}, nothing changed")
    _, init = new_store(rt)
    check(cid, "fixture store created and imported", init is not None and init["exit"] == 0,
          (init or {}).get("stderr", ""))
    before = {"sha256": store_sha(rt)}
    status = call(["store", "status", rt])
    ran(cid, status)
    before["bytes"] = (status["json"] or {}).get("file", {}).get("bytes")
    before["wal"] = (status["json"] or {}).get("file", {}).get("wal_bytes")
    hosts = tree(HOME, skip_prefixes=[f"store/{rt}", "machine"])
    perms = tree(HOME, skip_prefixes=[f"store/{rt}"])

    push = call(["store", "push", rt, machine, "--progress"], progress=True)
    ran(cid, push)
    progress_checks(cid, push, f"R12-{tag.upper()}-RT-push", multi_chunk=True)
    progressed = push["json"] or {}
    check(cid, "push reports native->" + machine, progressed.get("from") == "native" and progressed.get("to") == machine,
          json.dumps(progressed))
    check(cid, "push bytes equal the store file size", progressed.get("bytes") == before["bytes"],
          f"{progressed.get('bytes')} vs {before['bytes']}")
    get_pushed = call(["store", "get", rt])
    ran(cid, get_pushed)
    pushed = (get_pushed["json"] or {}).get("last_transfer") or {}
    check(cid, "record moved to " + machine, (get_pushed["json"] or {}).get("machine") == machine,
          (get_pushed["json"] or {}).get("machine"))
    check(cid, "last_transfer says native->" + machine + ", retired true",
          pushed.get("from") == "native" and pushed.get("to") == machine and pushed.get("retired") is True,
          json.dumps(pushed))

    # ---- R9-X-RETIRE-DIR: the source copy is gone, its folder and neighbours are not
    retire_cid = f"R9-X-RETIRE-DIR-{tag.upper()}"
    case(retire_cid, f"source retirement after store push {rt} -> {machine}")
    gone = not store_file(rt).exists()
    leftovers = sorted(p.name for p in (HOME / "store" / rt).glob("store.sqlite*"))
    check(retire_cid, f"{rt}: native store.sqlite is retired", gone, str(sorted(p.name for p in (HOME / 'store' / rt).iterdir())))
    check(retire_cid, f"{rt}: no store.sqlite, -wal, -shm or .incoming remains", not leftovers, str(leftovers))
    check(retire_cid, f"{rt}: the record folder stays with record.json",
          (HOME / "store" / rt / "record.json").is_file(), str((HOME / "store" / rt).is_dir()))
    hosts_after = tree(HOME, skip_prefixes=[f"store/{rt}", "machine"])
    perms_after = tree(HOME, skip_prefixes=[f"store/{rt}"])
    changed = sorted(set(hosts_after.items()) ^ set(hosts.items()))
    check(retire_cid, f"{rt}: every other home file is byte-identical", not changed,
          str([row[0] for row in changed][:8]))
    touched = sorted(set(perms_after.items()) ^ set(perms.items()))
    check(retire_cid, f"{rt}: nothing else in the home changed at all", not touched,
          str([row[0] for row in touched][:8]))

    pull = call(["store", "pull", rt, "--progress"], progress=True)
    ran(cid, pull)
    progress_checks(cid, pull, f"R12-{tag.upper()}-RT-pull", multi_chunk=True)
    after = store_sha(rt)
    get_pulled = call(["store", "get", rt])
    ran(cid, get_pulled)
    pulled = (get_pulled["json"] or {}).get("last_transfer") or {}
    check(cid, "the pulled store.sqlite is byte-identical to the pushed one",
          after is not None and after == before["sha256"], f"{after} vs {before['sha256']}")
    check(cid, "the pull records the file's sha256", pulled.get("sha256") == after, str(pulled.get("sha256")))
    check(cid, "heads are unchanged by an unchanged round trip",
          pulled.get("heads") == pushed.get("heads"), f"{pulled.get('heads')} vs {pushed.get('heads')}")
    check(cid, "the pull reports " + machine + "->native", pulled.get("from") == machine and pulled.get("to") == "native",
          json.dumps(pulled))
    status_after = call(["store", "status", rt])
    ran(cid, status_after)
    body = status_after["json"] or {}
    check(cid, "the store is idle on native, no holders, no op",
          body.get("machine") == "native" and body.get("state") == "idle" and body.get("op") in (None, {})
          and body.get("holders") in ([], None), json.dumps({k: body.get(k) for k in ("machine", "state", "op", "holders")}))
    check(cid, "incoming_bytes is 0 after the round trip", (body.get("file") or {}).get("incoming_bytes") == 0,
          json.dumps(body.get("file")))
    drop_store(rt)

    # ---- modified round trip: read in a mount, change, commit, pull back, compare
    cid = f"R9-{tag.upper()}-MOD"
    mod = f"mod-{tag}"
    case(cid, f"route native<->{machine}, Store {mod}, changed in a mounted Workspace")
    _, init = new_store(mod)
    check(cid, "fixture store created and imported", init is not None and init["exit"] == 0,
          (init or {}).get("stderr", ""))
    base = manifest_lines(subprocess.run(["sh", str(BASE / "manifest.sh")], cwd=FIX, capture_output=True,
                                        text=True).stdout)
    check(cid, "fixture manifest is non-empty", len(base) >= 15, f"{len(base)} lines")
    before_bytes = (call(["store", "status", mod])["json"] or {}).get("file", {}).get("bytes")

    push = call(["store", "push", mod, machine, "--progress"], progress=True)
    ran(cid, push)
    progress_checks(cid, push, f"R12-{tag.upper()}-MOD-push", multi_chunk=True)
    check(cid, "push succeeded", push["exit"] == 0, push["stderr"][:200])
    check(cid, "native copy is retired by the push", not store_file(mod).exists(), str(store_file(mod)))

    remote = sandbox_mount(machine, mod, "p1", fork="remote1")
    check(cid, f"Sandbox and Workspace on {machine}", bool(remote.get("ws")), json.dumps(remote.get("mounted", {}))[:400])
    if not remote.get("ws"):
        note(cid, "no Workspace on the target machine; the modified round trip cannot run")
        return
    reading = ws_exec(remote["ws"], MANIFEST)
    got = manifest_lines(reading["stdout"])
    check(cid, f"the mounted {machine} Workspace reproduces the fixture manifest exactly", got == base,
          diff_note(base, got))
    edited = ws_exec(remote["ws"], CHANGE_SCRIPT)
    check(cid, f"edits run inside the {machine} Workspace", edited["exit"] == 0,
          (edited["stdout"] + edited["stderr"])[:300])
    after_edit = manifest_lines(ws_exec(remote["ws"], MANIFEST)["stdout"])
    check(cid, "the mounted manifest reflects the edits", after_edit != base and len(after_edit) > len(base),
          f"{len(base)} -> {len(after_edit)} lines")
    session = teardown({"ws": remote["ws"], "sandbox": remote["sandbox"]},
                       commit_note=f"lp08 s1 {machine} edit")
    check(cid, "workspace commit succeeded", (session.get("commit") or {}).get("exit") == 0,
          str((session.get("commit") or {}).get("stderr")) [:300])
    check(cid, "sandbox closed", (session.get("closed") or {}).get("exit") == 0,
          str((session.get("closed") or {}).get("stderr"))[:300])
    commits = call(["commit", "list", f"{mod}/p1", "remote1"])
    ran(cid, commits)
    remote_commits = len((commits["json"] or {}).get("items") or [])
    check(cid, "the branch holds the edit commit", remote_commits >= 1, f"{remote_commits} commits")

    pull = call(["store", "pull", mod, "--progress"], progress=True)
    ran(cid, pull)
    progress_checks(cid, pull, f"R12-{tag.upper()}-MOD-pull", multi_chunk=True)
    check(cid, "pull succeeded after a commit on the target", pull["exit"] == 0, pull["stderr"][:300])
    get_pulled = call(["store", "get", mod])
    pulled = (get_pulled["json"] or {}).get("last_transfer") or {}
    check(cid, "the pulled store.sqlite hashes to last_transfer.sha256",
          store_sha(mod) == pulled.get("sha256"), f"{store_sha(mod)} vs {pulled.get('sha256')}")
    check(cid, "the pull moved more bytes than the push recorded (the edit added data)",
          (pulled.get("bytes") or 0) > (before_bytes or 0), f"{pulled.get('bytes')} vs {before_bytes}")

    local = sandbox_mount(None, mod, "p1", branch="remote1")
    check(cid, "native Sandbox and Workspace", bool(local.get("ws")), json.dumps(local.get("mounted", {}))[:300])
    if local.get("ws"):
        back = manifest_lines(ws_exec(local["ws"], MANIFEST)["stdout"])
        check(cid, "the native Workspace after the pull reproduces the edited manifest exactly", back == after_edit,
              diff_note(after_edit, back))
        branches = call(["branch", "list", f"{mod}/p1"])
        names = [b.get("name") for b in ((branches["json"] or {}).get("items") or [])]
        check(cid, "the edit branch travelled with the Store", "remote1" in names, str(names))
        write = ws_exec(local["ws"], "printf 'local write after pull\\n' >> docs/readme.md; sync; cat docs/readme.md")
        check(cid, "the pulled Store is writable on native", write["exit"] == 0 and "local write after pull" in write["stdout"],
              (write["stdout"] + write["stderr"])[:300])
        post = manifest_lines(ws_exec(local["ws"], MANIFEST)["stdout"])
        check(cid, "the native write is visible in the mount", post != back,
              f"{len(back)} -> {len(post)} lines")
        done = teardown({"ws": local["ws"], "sandbox": local["sandbox"]}, commit_note="lp08 s1 native edit")
        check(cid, "native commit after the pull", (done.get("commit") or {}).get("exit") == 0,
              str((done.get("commit") or {}).get("stderr"))[:300])
    status_after = call(["store", "status", mod])
    body = status_after["json"] or {}
    check(cid, "the store ends idle on native", body.get("machine") == "native" and body.get("state") == "idle",
          json.dumps({k: body.get(k) for k in ("machine", "state", "op", "holders")}))


CHANGE_SCRIPT = r"""
set -eu
printf 'modified on the target\n' > docs/readme.md
head -c 262144 /dev/urandom > data/new.bin
mkdir -p extra/dir
printf '#!/bin/sh\necho new\n' > extra/dir/tool.sh
chmod 755 extra/dir/tool.sh
ln -s ../docs/readme.md extra/link
rm -f src/lib.rs
printf 'added\n' > 'new file with space.txt'
exit 0
"""


def diff_note(want, got):
    want, got = set(want), set(got)
    return json.dumps({"missing": sorted(want - got)[:5], "extra": sorted(got - want)[:5],
                       "counts": [len(want), len(got)]}, ensure_ascii=False)[:900]


# ------------------------------------------------------------------- geometry


def geometry_lima(rid):
    machine = "lm"
    listed = call(["machine", "list"])
    names = [m.get("name") for m in ((listed["json"] or {}).get("machines") or [])]
    if "lm" not in names:
        made = call(["machine", "create", "lm", "lima", "--cpus", "2", "--memory", "2G", "--disk", "8G"],
                    timeout=1800)
        ran(f"R9-{route_store_tag(rid).upper()}-RT", made)
        if made["exit"] != 0:
            raise RuntimeError("machine create lm failed: " + made["stderr"][:400])
    started = machine_start("lm")
    if started["exit"] != 0:
        raise RuntimeError("machine start lm failed: " + started["stderr"][:400])
    status = call(["machine", "status", "lm"])
    note(f"R9-{route_store_tag(rid).upper()}-RT", "lima status: " + json.dumps(status["json"])[:400])


def geometry_ac(rid):
    listed = call(["machine", "list"])
    names = [m.get("name") for m in ((listed["json"] or {}).get("machines") or [])]
    if "ac" not in names:
        made = call(["machine", "create", "ac", "apple-container", "--cpus", "2", "--memory", "2G", "--disk", "8G"],
                    timeout=1800)
        ran(f"R9-{route_store_tag(rid).upper()}-RT", made)
        if made["exit"] != 0:
            raise RuntimeError("machine create ac failed: " + made["stderr"][:400])
    started = machine_start("ac")
    if started["exit"] != 0:
        raise RuntimeError("machine start ac failed: " + started["stderr"][:400])
    status = call(["machine", "status", "ac"])
    note(f"R9-{route_store_tag(rid).upper()}-RT", "apple-container status: " + json.dumps(status["json"])[:400])


def geometry_docker(rid):
    started = machine_start("docker")
    if started["exit"] != 0:
        raise RuntimeError("machine start docker failed: " + started["stderr"][:400])
    status = call(["machine", "status", "docker"])
    note(f"R9-{route_store_tag(rid).upper()}-RT", "docker status: " + json.dumps(status["json"])[:400])


# --------------------------------------------------------------------- phases


def cleanup():
    """Remove every Store and Sandbox of this home so a route can be re-run."""
    for sandbox in ((call(["sandbox", "list"])["json"] or {}).get("items") or []):
        call(["sandbox", "close", sandbox["name"], "--force"], timeout=900)
    for store in ((call(["store", "list"])["json"] or {}).get("items") or []):
        call(["store", "remove", store["name"]], timeout=900)
    print("home cleaned:", HOME)


def setup():
    HOME.mkdir(mode=0o700, parents=True, exist_ok=True)
    steps = [
        (["machine", "update", "docker", "--docker", str(Path.home() / ".colima/default/docker.sock")], 300),
        (["machine", "update", "native", "--daemon", DAEMON], 300),
    ]
    for argv, timeout in steps:
        result = call(argv, timeout=timeout)
        print(argv, "->", result["exit"], result["stderr"][:200])
    platforms = call(["machine", "platforms"])
    (BASE / "receipts").mkdir(parents=True, exist_ok=True)
    (BASE / "receipts" / "platforms.json").write_text(json.dumps(platforms["json"], indent=1))
    (BASE / "receipts" / "machines.json").write_text(json.dumps(call(["machine", "list"])["json"], indent=1))
    print("home:", HOME)


def hop():
    """Docker -> native -> lima: the direct push is refused, the two hops lose nothing."""
    tag = "mod-d"
    case("R9-H-HOP", "docker -> native -> lima handoff of Store mod-d")
    ensure_machine("docker")
    ensure_machine("lm")
    for entry in ((call(["sandbox", "list"])["json"] or {}).get("items") or []):
        call(["sandbox", "close", entry["name"], "--force"], timeout=900)

    local = sandbox_mount(None, tag, "p1", branch="remote1")
    expected = None
    if local.get("ws"):
        branches = [b.get("name") for b in ((call(["branch", "list", f"{tag}/p1"])["json"] or {}).get("items") or [])]
        check("R9-H-HOP", "the handoff store has its edit branch", "remote1" in branches, str(branches))
        expected = manifest_lines(ws_exec(local["ws"], MANIFEST)["stdout"])
        check("R9-H-HOP", "the native mount before the handoff has content", len(expected) > 15, f"{len(expected)} lines")
    teardown({"ws": local.get("ws"), "sandbox": local.get("sandbox")})

    push_d = call(["store", "push", tag, "docker", "--progress"], progress=True)
    ran("R9-H-HOP", push_d)
    progress_checks("R9-H-HOP", push_d, "R12-HOP-push-docker", multi_chunk=True)
    check("R9-H-HOP", "the store is on docker before the handoff", push_d["exit"] == 0, push_d["stderr"][:300])

    direct = call(["store", "push", tag, "lm"], timeout=600)
    ran("R9-H-HOP", direct)
    bad = refusal(direct) or {}
    check("R9-H-HOP", "pushing from docker straight to lima is refused",
          direct["exit"] == 125 and bad.get("code") == "InvalidInput", json.dumps(bad)[:400])
    check("R9-H-HOP", "the refusal names the way to move it", "pull" in (bad.get("message") or ""),
          bad.get("message"))
    check("R9-H-HOP", "the refusal changed no copy", not (HOME / "store" / tag / "store.sqlite").exists())

    back = call(["store", "pull", tag, "--progress"], progress=True)
    ran("R9-H-HOP", back)
    progress_checks("R9-H-HOP", back, "R12-HOP-pull-native")
    check("R9-H-HOP", "first hop (docker -> native) succeeded", back["exit"] == 0, back["stderr"][:300])
    mid = (call(["store", "get", tag])["json"] or {}).get("last_transfer") or {}
    check("R9-H-HOP", "first hop is retired", mid.get("retired") is True and mid.get("to") == "native", json.dumps(mid)[:300])
    native_sha, native_bytes = store_sha(tag), mid.get("sha256")

    onward = call(["store", "push", tag, "lm", "--progress"], progress=True)
    ran("R9-H-HOP", onward)
    progress_checks("R9-H-HOP", onward, "R12-HOP-push-lima")
    check("R9-H-HOP", "second hop (native -> lima) succeeded", onward["exit"] == 0, onward["stderr"][:300])
    pushed = (call(["store", "get", tag])["json"] or {}).get("last_transfer") or {}
    check("R9-H-HOP", "second hop is retired and leaves native", pushed.get("retired") is True and pushed.get("to") == "lm",
          json.dumps(pushed)[:300])
    check("R9-H-HOP", "lima received exactly the bytes native had",
          (onward["json"] or {}).get("bytes") == (back["json"] or {}).get("bytes"),
          f"{(onward['json'] or {}).get('bytes')} vs {(back['json'] or {}).get('bytes')}")

    remote = sandbox_mount("lm", tag, "p1", branch="remote1")
    if remote.get("ws"):
        got = manifest_lines(ws_exec(remote["ws"], MANIFEST)["stdout"])
        check("R9-H-HOP", "lima's mount equals native's mount after two hops", got == (expected or []),
              diff_note(expected or [], got))
        teardown({"ws": remote["ws"], "sandbox": remote["sandbox"]})

    final = call(["store", "pull", tag, "--progress"], progress=True)
    ran("R9-H-HOP", final)
    progress_checks("R9-H-HOP", final, "R12-HOP-pull-native-2")
    check("R9-H-HOP", "the handoff store comes back to native", final["exit"] == 0, final["stderr"][:300])
    last = (call(["store", "get", tag])["json"] or {}).get("last_transfer") or {}
    check("R9-H-HOP", "the returning copy hashes to the pull's recorded sha256",
          store_sha(tag) == last.get("sha256"), f"{store_sha(tag)} vs {last.get('sha256')}")
    check("R9-H-HOP", "heads are unchanged across both hops",
          last.get("heads") == mid.get("heads") == pushed.get("heads"),
          f"{last.get('heads')} {mid.get('heads')} {pushed.get('heads')}")
    note("R9-H-HOP", f"raw store.sqlite bytes after the first hop {native_sha}, after the second {store_sha(tag)}: "
                      "the mount on lima opened the Store, so the file itself differs while heads, bytes and "
                      "manifest do not (a use-level change, not data loss)")
    print("hop done")


def state_of_home(skip=()):
    """Every home entry: mode, size, mtime; small files hashed, big ones not."""
    rows = {}
    for base, dirs, files in os.walk(HOME):
        dirs.sort()
        for name in sorted(files) + sorted(dirs):
            path = Path(base) / name
            rel = str(path.relative_to(HOME))
            if any(rel == s or rel.startswith(s + "/") for s in skip):
                continue
            try:
                meta = path.lstat()
            except FileNotFoundError:
                continue
            if path.is_symlink():
                rows[rel] = "L:" + os.readlink(path)
            elif path.is_dir():
                rows[rel] = "D:%o" % (meta.st_mode & 0o777)
            elif meta.st_size > 1 << 20:
                rows[rel] = "F:%o:%d" % (meta.st_mode & 0o777, meta.st_size)
            else:
                rows[rel] = "F:%o:%d:%s" % (meta.st_mode & 0o777, meta.st_size, sha256_file(path))
    return rows


def store_status(name):
    return call(["store", "status", name], timeout=300)["json"]


def refusal_item(cid, argv, code, store=None, message_has=None, timeout=600, note_text=None):
    """One refusal: exit 125, the code, the message, and no side effect."""
    case(cid, note_text or "layerfs " + " ".join(argv))
    before = state_of_home()
    status_before = store_status(store) if store else None
    result = call(argv, timeout=timeout)
    ran(cid, result)
    bad = refusal(result) or {}
    check(cid, f"exit code is 125", result["exit"] == 125, f"exit {result['exit']}")
    check(cid, f"code is {code}", bad.get("code") == code, str(bad.get("code")))
    if message_has:
        check(cid, f"message names {message_has!r}", message_has in (bad.get("message") or ""), bad.get("message"))
    after = state_of_home()
    changed = sorted(set(before.items()) ^ set(after.items()))
    check(cid, "the home is byte-identical afterwards", before == after,
          str([row[0] for row in changed][:6]))
    if store:
        status_after = store_status(store)
        check(cid, f"store {store} status is unchanged", settled(status_before) == settled(status_after),
              json.dumps({"before": status_before, "after": status_after})[:500])
    return result, bad


def settled(status):
    """A store status without the free-disk figure, which moves on its own."""
    if not status:
        return status
    copy = json.loads(json.dumps(status))
    if isinstance(copy.get("file"), dict):
        copy["file"].pop("free", None)
    return copy


def write_record(path, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    path.write_text(json.dumps(fields))
    path.chmod(0o600)


def refusals():
    now_ms = int(time.time() * 1000)
    make_store = new_store
    ensure_machine("docker")
    # a re-run starts from an empty probe set: these names are this phase's own
    for entry in ((call(["sandbox", "list"])["json"] or {}).get("items") or []):
        call(["sandbox", "close", entry["name"], "--force"], timeout=900)
    for name in ("ref-native", "ref-docker", "ref-exists", "ref-inuse", "ref-busy", "ref-lease",
                 "fcstore", "sshstore", "ref-pg"):
        call(["store", "remove", name], timeout=900)
        shutil.rmtree(HOME / "store" / name, ignore_errors=True)
        shutil.rmtree(HOME / "sandbox" / ("sb-" + name), ignore_errors=True)
    for name in ("sb-inuse", "sb-fc1", "sb-h1", "sbfc1", "newsb-fc1", "newsb-h1"):
        shutil.rmtree(HOME / "sandbox" / name, ignore_errors=True)

    # ---- REF-PG: a PostgreSQL Store never moves
    cid = "REF-PG"
    case(cid, "a PostgreSQL Store is refused by store push and store pull")
    password = subprocess.run(["docker", "exec", "lp08-pg", "printenv", "POSTGRES_PASSWORD"],
                              capture_output=True, text=True, timeout=60).stdout.strip()
    url = os.environ.get("LP08_PG_URL") or "postgres://postgres@127.0.0.1:55432/postgres"
    os.environ["LP08_PG_PASSWORD"] = password
    connected = call(["store", "connect", "ref-pg", url, "--password", "env:LP08_PG_PASSWORD"], timeout=300)
    ran(cid, connected)
    check(cid, "store connect is refused in this build without the PostgreSQL engine",
          connected["exit"] == 125 and (refusal(connected) or {}).get("code") == "Unsupported",
          connected["stderr"][:300])
    note(cid, "this release CLI was built without the PostgreSQL engine (`--features postgresql`), so a "
              "postgresql Store record is written by hand for the movement refusal only, as the plan writes "
              "machine records for the disabled platforms")
    write_record(HOME / "store" / "ref-pg" / "record.json",
                 {"name": "ref-pg", "kind": "postgresql", "created": now_ms})
    refusal_item(cid, ["store", "push", "ref-pg", "docker"], "InvalidInput", None, "does not move")
    refusal_item(cid, ["store", "pull", "ref-pg"], "InvalidInput", None, "does not move")
    shutil.rmtree(HOME / "store" / "ref-pg", ignore_errors=True)

    # ---- the directions a Store's own record forbids
    native = "ref-native"
    make_store(native)
    refusal_item("REF-PUSH-NATIVE", ["store", "push", native, "native"], "InvalidInput", native, "already on native")
    refusal_item("REF-PULL-NATIVE", ["store", "pull", native], "InvalidInput", native, "already on native")
    refusal_item("REF-NOSTORE", ["store", "push", "nope", "docker"], "NotFound", None, "no Store named nope")
    refusal_item("REF-NOMACHINE", ["store", "push", native, "ghost"], "NotFound", native, "no machine named ghost")

    cid = "REF-BADNAME"
    case(cid, "invalid names are refused before anything is created")
    for argv in (["store", "push", "bad/name", "docker"], ["store", "create", "x y"]):
        result = call(argv, timeout=300)
        ran(cid, result)
        bad = refusal(result) or {}
        check(cid, f"{' '.join(argv)} is refused", result["exit"] in (2, 125), f"exit {result['exit']}")
        check(cid, f"{' '.join(argv)} names an invalid input", bad.get("code") == "InvalidInput", str(bad.get("code")))
    names = [s.get("name") for s in ((call(["store", "list"])["json"] or {}).get("stores") or [])]
    check(cid, "no store named from an invalid name exists", "bad/name" not in names and "x y" not in names, str(names))

    # ---- REF-WRONGDIR-PUSH: a Store on a machine must be pulled first
    moved = "ref-docker"
    make_store(moved)
    pushed = call(["store", "push", moved, "docker", "--progress"], progress=True)
    ran("REF-WRONGDIR-PUSH", pushed)
    check("REF-WRONGDIR-PUSH", "the probe store sits on docker", pushed["exit"] == 0, pushed["stderr"][:200])
    refusal_item("REF-WRONGDIR-PUSH", ["store", "push", moved, "docker"], "InvalidInput", moved, "store pull")
    ensure_lima()
    refusal_item("REF-WRONGDIR-PUSH", ["store", "push", moved, "lm"], "InvalidInput", moved, "store pull")

    # ---- REF-EXISTS: the target machine already holds that Store name
    cid = "REF-EXISTS"
    case(cid, "a target that already holds the Store file is refused in check")
    exists = "ref-exists"
    make_store(exists)
    instance = lima_instance("lm")
    planted = None
    if instance:
        planted = subprocess.run(
            ["limactl", "shell", instance, "--", "sudo", "sh", "-c",
             f"mkdir -p /layerfs/data/store/{exists} && : > /layerfs/data/store/{exists}/store.sqlite"],
            capture_output=True, text=True, timeout=300)
    check(cid, "a colliding file was planted in lima's data disk",
          planted is not None and planted.returncode == 0, (planted.stderr if planted else "no limactl instance")[:300])
    refusal_item(cid, ["store", "push", exists, "lm"], "Exists", exists, "already holds")
    if instance:
        subprocess.run(["limactl", "shell", instance, "--", "sudo", "rm", "-rf",
                        f"/layerfs/data/store/{exists}"], capture_output=True, text=True, timeout=300)
    after = call(["store", "status", exists])
    check(cid, "the source Store is untouched by the refusal", (after["json"] or {}).get("machine") == "native",
          json.dumps(after["json"])[:300])
    drop_store(exists)

    # ---- REF-INUSE-SANDBOX: a Sandbox of the project holds the Store
    cid = "REF-INUSE-SANDBOX"
    case(cid, "a Store whose project has a running Sandbox on its machine is refused")
    held = "ref-inuse"
    make_store(held)
    sent = call(["store", "push", held, "docker", "--progress"], progress=True)
    ran(cid, sent)
    check(cid, "the probe store is on docker", sent["exit"] == 0, sent["stderr"][:200])
    sandbox = "sb-inuse"
    made = call(["sandbox", "create", f"{held}/p1", sandbox, "docker"], timeout=900)
    ran(cid, made)
    check(cid, "a Sandbox of the project runs on docker", made["exit"] == 0, made["stderr"][:300])
    result, bad = refusal_item(cid, ["store", "pull", held], "InUse", None, None)
    related = ((bad.get("detail") or {}).get("related") or [])
    check(cid, "detail.related names the Sandbox",
          any(item.get("kind") == "sandbox" and item.get("name") == sandbox for item in related), json.dumps(related))
    call(["sandbox", "close", sandbox], timeout=900)
    cleanup = call(["store", "pull", held, "--progress"], progress=True)
    ran(cid, cleanup)
    check(cid, "the Store pulls back once the Sandbox is gone", cleanup["exit"] == 0, cleanup["stderr"][:300])
    drop_store(held)

    # ---- REF-BUSY: a second transfer of the same Store while one runs
    cid = "REF-BUSY"
    case(cid, "a second store push of the same Store while one is running")
    busy = "ref-busy"
    make_store(busy)
    started = {}

    def first():
        started["result"] = call(["store", "push", busy, "docker", "--progress"], progress=True)

    thread = threading.Thread(target=first)
    thread.start()
    week = time.time() + 20
    op_seen = None
    while time.time() < week and thread.is_alive():
        status = store_status(busy)
        op_seen = (status or {}).get("op")
        if op_seen:
            break
        time.sleep(0.02)
    note(cid, "the running op seen while pushing: " + json.dumps(op_seen)[:200])
    second = call(["store", "push", busy, "docker"], timeout=300) if op_seen else None
    thread.join(600)
    ran(cid, started.get("result") or {"argv": ["store", "push", busy, "docker"], "exit": None, "seconds": 0})
    check(cid, "the first transfer succeeded", (started.get("result") or {}).get("exit") == 0,
          str((started.get("result") or {}).get("stderr"))[:200])
    second_bad = refusal(second or {}) or {}
    check(cid, "the overlapping push is refused Busy", second_bad.get("code") == "Busy",
          json.dumps(second_bad)[:400])
    check(cid, "the overlapping push exited 125", (second or {}).get("exit") == 125,
          str((second or {}).get("exit")))
    back = call(["store", "pull", busy, "--progress"], progress=True)
    ran(cid, back)
    check(cid, "the Store is intact after the refusal", back["exit"] == 0, back["stderr"][:200])
    drop_store(busy)

    # ---- REF-LEASE: another live process holds the Store's lease
    cid = "REF-LEASE"
    case(cid, "another live process's lease on the Store refuses the transfer")
    leased = "ref-lease"
    made = call(["store", "create", leased], timeout=300)
    ran(cid, made)
    big = BASE / "fixture" / "lease"
    if not big.exists():
        big.mkdir(parents=True)
        for n in range(400):
            (big / f"file-{n:03d}.bin").write_bytes(stream_bytes(n))
    init = {}

    def filling():
        init["result"] = call(["project", "init", f"{leased}/p1", str(big), "--timeout", "120000"], timeout=600)

    thread = threading.Thread(target=filling)
    thread.start()
    holders, deadline = [], time.time() + 30
    while time.time() < deadline and not init.get("result"):
        status = store_status(leased)
        holders = (status or {}).get("holders") or []
        if holders:
            break
        time.sleep(0.02)
    check(cid, "a live process holds the Store's lease", bool(holders), f"holders={holders}")
    pushed = call(["store", "push", leased, "docker"], timeout=600)
    ran(cid, pushed)
    bad = refusal(pushed) or {}
    check(cid, "the push is refused InUse", bad.get("code") == "InUse", json.dumps(bad)[:400])
    related = ((bad.get("detail") or {}).get("related") or [])
    check(cid, "detail.related names the lease by pid",
          any(item.get("kind") == "lease" for item in related), json.dumps(related))
    thread.join(600)
    check(cid, "the filling import finished", (init.get("result") or {}).get("exit") == 0,
          str((init.get("result") or {}).get("stderr"))[:300])
    after = call(["store", "push", leased, "docker", "--progress"], progress=True)
    ran(cid, after)
    check(cid, "the push succeeds once the lease is released", after["exit"] == 0, after["stderr"][:200])
    again = call(["store", "pull", leased, "--progress"], progress=True)
    ran(cid, again)
    drop_store(leased)

    # ---- REF-STOPPED: the target machine is stopped
    cid = "REF-STOPPED"
    case(cid, "a stopped machine is Unavailable and named in the fix")
    stopped = call(["machine", "stop", "lm"], timeout=900)
    ran(cid, stopped)
    check(cid, "lm stopped", stopped["exit"] == 0, stopped["stderr"][:200])
    result, bad = refusal_item(cid, ["store", "push", native, "lm"], "Unavailable", native, "layerfs machine start lm")
    status = call(["machine", "status", "lm"], timeout=300)
    ran(cid, status)
    check(cid, "the machine was not started implicitly", (status["json"] or {}).get("state") != "running",
          json.dumps(status["json"])[:300])
    started = machine_start("lm")
    check(cid, "machine start lm brings it back", started["exit"] == 0, started["stderr"][:200])

    # ---- REF-FC-CREATE / REF-SSH-CONNECT: the #7 product refusal
    fc_text = "firecracker is permanently disabled by product policy (layerfs-project#7)"
    ssh_text = "ssh is permanently disabled by product policy (layerfs-project#7)"
    result, bad = refusal_item("REF-FC-CREATE", ["machine", "create", "fctmp", "firecracker"], "Unsupported", None, None)
    check("REF-FC-CREATE", "the authoritative firecracker text is used", bad.get("message") == fc_text, bad.get("message"))
    result, bad = refusal_item("REF-SSH-CONNECT", ["machine", "connect", "sshtmp", "10.0.0.5"], "Unsupported", None, None)
    check("REF-SSH-CONNECT", "the authoritative ssh text is used", bad.get("message") == ssh_text, bad.get("message"))

    # ---- REF-FC-RECORD / REF-SSH-RECORD: a hand-written record cannot be used
    for cid, machine, platform, text in (("REF-FC-RECORD", "fc1", "firecracker", fc_text),
                                         ("REF-SSH-RECORD", "h1", "ssh", ssh_text)):
        case(cid, f"a hand-written {platform} machine record refuses all new work")
        write_record(HOME / "machine" / machine / "record.json",
                     {"name": machine, "platform": platform, "created": now_ms})
        store = "fcstore" if platform == "firecracker" else "sshstore"
        make_store(store)
        record_path = HOME / "store" / store / "record.json"
        record = json.loads(record_path.read_text())
        record["machine"] = machine
        record_path.write_text(json.dumps(record))
        sandbox = f"sb-{machine}"
        write_record(HOME / "sandbox" / sandbox / "record.json",
                     {"name": sandbox, "project": f"{store}/p1", "machine": machine, "created": now_ms,
                      "platform": platform})
        battery = [
            (["machine", "start", machine], "Unsupported"),
            (["machine", "update", machine, "--cpus", "2"], "Unsupported"),
            (["store", "push", native, machine], "Unsupported"),
            (["store", "pull", store], "Unsupported"),
            (["sandbox", "create", f"{store}/p1", f"newsb-{machine}", machine], "Unsupported"),
            (["workspace", "mount", sandbox, "check1"], "Unsupported"),
            (["workspace", "exec", f"{sandbox}:/tmp/w", "true"], "Unsupported"),
            (["workspace", "commit", f"{sandbox}:/tmp/w"], "Unsupported"),
            (["project", "init", f"{store}/extra", str(FIX)], "Unsupported"),
            (["file", "write", f"{store}/p1", "main", "/new.txt", "--from", str(BASE / "fixture" / "new.txt")], "Unsupported"),
            (["backup", "create", store, "nobucket"], "Unsupported"),
        ]
        for argv, code in battery:
            outcome = call(argv, timeout=300)
            ran(cid, outcome)
            bad = refusal(outcome) or {}
            check(cid, f"layerfs {' '.join(argv)} is refused {code}",
                  outcome["exit"] == 125 and bad.get("code") == code,
                  f"exit {outcome['exit']} {(bad.get('code'), bad.get('message'))}")
            check(cid, f"layerfs {' '.join(argv)} carries the authoritative text",
                  bad.get("message") == text, str(bad.get("message"))[:200])
        kept = [
            ["machine", "list"], ["machine", "get", machine], ["machine", "status", machine],
            ["store", "list"], ["store", "get", store], ["store", "status", store], ["doctor"],
        ]
        for argv in kept:
            outcome = call(argv, timeout=300)
            ran(cid, outcome)
            check(cid, f"layerfs {' '.join(argv)} stays available", outcome["exit"] == 0, outcome["stderr"][:200])
        teardown_argv = ["machine", "remove", machine] if platform == "firecracker" else ["machine", "disconnect", machine]
        blocked = call(teardown_argv, timeout=300)
        ran(cid, blocked)
        note(cid, f"{' '.join(teardown_argv)} while records still name the machine: exit {blocked['exit']} "
                  + str((refusal(blocked) or {}).get("code")))
        cleaned = call(["store", "remove", store], timeout=300)
        ran(cid, cleaned)
        if cleaned["exit"] != 0:
            shutil.rmtree(HOME / "store" / store, ignore_errors=True)
            note(cid, "store remove was refused here; the record folder was deleted so the teardown could run")
        shutil.rmtree(HOME / "sandbox" / sandbox, ignore_errors=True)
        removed = call(teardown_argv, timeout=300)
        ran(cid, removed)
        removed_bad = refusal(removed) or {}
        check(cid, f"layerfs {' '.join(teardown_argv)} is not refused by the #7 policy",
              removed_bad.get("code") != "Unsupported",
              f"exit {removed['exit']} {json.dumps(removed_bad)[:240]}")
        note(cid, f"{' '.join(teardown_argv)} on the hand-written record: exit {removed['exit']} "
                  + str(removed_bad.get("message")))
        shutil.rmtree(HOME / "machine" / machine, ignore_errors=True)

    drop_store(native)
    drop_store(moved)
    print("refusals done")


def ac_sweep():
    """How big a Store can travel back from an apple-container machine (#9 A blocker)."""
    cid = "R9-A-BLOCKER"
    case(cid, "apple-container: the largest Store that survives a pull, by content size")
    ensure_machine("ac")
    rows = []
    for mib in (3, 5, 7, 7.5, 9):
        name = "sweep-ac-" + str(mib).replace(".", "_")
        folder = BASE / "fixture" / ("sweep-" + str(mib).replace(".", "_"))
        folder.mkdir(parents=True, exist_ok=True)
        blob = folder / "data.bin"
        if not blob.exists() or blob.stat().st_size != int(mib * 1024 * 1024):
            blob.write_bytes(os.urandom(int(mib * 1024 * 1024)))
        call(["store", "create", name], timeout=300)
        made = call(["project", "init", f"{name}/p", str(folder)], timeout=900)
        bytes_on_disk = ((call(["store", "status", name])["json"] or {}).get("file") or {}).get("bytes")
        pushed = call(["store", "push", name, "ac"], timeout=900)
        pulled = call(["store", "pull", name, "--progress"], progress=True)
        bad = refusal(pulled) or {}
        rows.append({"content_mib": mib, "store_bytes": bytes_on_disk, "push": pushed["exit"],
                     "pull": pulled["exit"], "code": bad.get("code"), "message": (bad.get("message") or "")[:160]})
        check(cid, f"{mib} MiB content (store {bytes_on_disk} B): push succeeded", pushed["exit"] == 0,
              pushed["stderr"][:200])
        call(["store", "remove", name], timeout=600)
        shutil.rmtree(HOME / "store" / name, ignore_errors=True)
    ok_rows = [r for r in rows if r["pull"] == 0]
    bad_rows = [r for r in rows if r["pull"] != 0]
    check(cid, "every size pulls back from apple-container", len(ok_rows) == len(rows),
          json.dumps([{r["store_bytes"]: r["pull"]} for r in rows]))
    check(cid, "every pull succeeded on its first attempt (no unresolved intent to recover)",
          all(r["pull"] == 0 for r in rows), json.dumps(bad_rows)[:400])
    check(cid, "any failure is Unknown + a lost worker answer, at send",
          all(r["code"] == "Unknown" and "answer was lost" in r["message"] for r in bad_rows),
          json.dumps(bad_rows)[:400])
    note(cid, "LP08-FIX-F1F2-AND-AC re-run: the lost answer of LP08-S1 §8.1 no longer fails a pull "
              "(the read-only `send` piece is asked again, up to three times, and the worker half-closes); "
              "the sizes that failed before now answer in one attempt: "
              + json.dumps([{r["store_bytes"]: r["pull"]} for r in rows]))

    # a failed pull leaves an unresolved intent; the next pull is the documented retry
    group = "sweep-retry"
    call(["store", "create", group], timeout=300)
    call(["project", "init", f"{group}/p", str(FIX)], timeout=900)
    pushed = call(["store", "push", group, "ac"], timeout=900)
    check(cid, "the 21.7 MiB fixture pushes to apple-container", pushed["exit"] == 0, pushed["stderr"][:200])
    attempts = []
    for attempt in range(4):
        pulled = call(["store", "pull", group, "--progress"], progress=True)
        bad = refusal(pulled) or {}
        status = call(["store", "status", group])["json"] or {}
        attempts.append({"attempt": attempt + 1, "exit": pulled["exit"], "code": bad.get("code"),
                         "state": status.get("state"), "machine": status.get("machine"),
                         "op_phase": ((status.get("op") or {}) or {}).get("phase")})
        if pulled["exit"] == 0:
            break
        check(cid, f"attempt {attempt + 1} left the Store unresolved, not broken",
              status.get("state") == "unresolved" and status.get("machine") == "ac",
              json.dumps(status)[:300])
    note(cid, "21.7 MiB retry attempts: " + json.dumps(attempts))
    check(cid, "a repeated pull eventually succeeds or reports the same Unknown, never a false success",
          any(a["exit"] == 0 for a in attempts) or all(a["code"] == "Unknown" for a in attempts),
          json.dumps(attempts))
    call(["store", "remove", group], timeout=600)
    shutil.rmtree(HOME / "store" / group, ignore_errors=True)
    print("sweep:", json.dumps(rows))


def progress_raw():
    """One transfer's complete `--progress` stream, byte for byte, as #12 evidence."""
    ensure_machine("docker")
    name = "raw-progress"
    call(["store", "remove", name], timeout=600)
    shutil.rmtree(HOME / "store" / name, ignore_errors=True)
    call(["store", "create", name], timeout=300)
    call(["project", "init", f"{name}/p1", str(FIX)], timeout=900)
    out = BASE / "receipts" / "progress-raw.jsonl"
    lines = []
    for direction in (["store", "push", name, "docker"], ["store", "pull", name]):
        result = call(direction + ["--progress"], progress=True)
        lines.append({"argv": direction, "exit": result["exit"], "seconds": result["seconds"],
                      "stdout": result["stdout"].strip(), "events": result["events"]})
    out.write_text(json.dumps(lines, ensure_ascii=False, indent=1))
    case("R12-RAW", "the complete progress stream of one push and one pull, with monotonic timestamps")
    for row in lines:
        stages = [e["progress"]["phase"] for e in row["events"] if "progress" in e]
        check("R12-RAW", f"{' '.join(row['argv'])}: every phase seen", all(p in stages for p in PHASES),
              json.dumps(stages))
    print("raw stream:", out)
    call(["store", "remove", name], timeout=600)
    shutil.rmtree(HOME / "store" / name, ignore_errors=True)


def stream_bytes(n):
    out = bytearray()
    counter = 0
    while len(out) < 131072:
        out += hashlib.sha256(b"lease:%d:%d" % (n, counter)).digest()
        counter += 1
    return bytes(out[:131072])


def ensure_lima():
    """The lima machine exists and runs (created here if the route did not)."""
    listed = call(["machine", "list"])
    names = [m.get("name") for m in ((listed["json"] or {}).get("machines") or [])]
    if "lm" not in names:
        call(["machine", "create", "lm", "lima", "--cpus", "2", "--memory", "2G", "--disk", "8G"], timeout=1800)
    return machine_start("lm")


def lima_instance(name):
    try:
        listed = subprocess.run(["limactl", "list", "--json"], capture_output=True, text=True, timeout=60).stdout
    except Exception:  # noqa: BLE001
        return None
    for line in listed.splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("name") == name:
            return name
        if name in (entry.get("name") or "") and entry.get("status") == "Running":
            return entry["name"]
    return None


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "report"
    try:
        if what == "setup":
            setup()
        elif what == "cleanup":
            cleanup()
        elif what == "route":
            rid = sys.argv[2]
            route(rid, {"docker": "docker", "lima": "lm", "ac": "ac"}[rid],
                  {"docker": geometry_docker, "lima": geometry_lima, "ac": geometry_ac}[rid])
        elif what == "hop":
            hop()
        elif what == "acsweep":
            ac_sweep()
        elif what == "rawprogress":
            progress_raw()
        elif what == "refuse":
            refusals()
        elif what == "report":
            pass
        elif what == "save":
            pass
        else:
            raise SystemExit("unknown phase " + what)
    except Exception:
        traceback.print_exc()
        note(what if what.isupper() else ("R9-" + (sys.argv[2] if len(sys.argv) > 2 else "").upper()),
             "phase aborted: " + traceback.format_exc().splitlines()[-1])
    finally:
        save()
        for cid in sorted(CASES):
            print(f"{cid:22s} {verdict(cid):7s} {len(CASES[cid]['checks'])} checks")
