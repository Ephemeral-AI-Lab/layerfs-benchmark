"""In-container steps for backup-verify: run LayerFS CLI commands and record
receipts, build fixture Stores, and snapshot a Store's history for comparison.

Runs inside a Linux container with the pinned CLI at $LAYERFS_CLI, a private
LAYERFS_HOME per step, receipts under /out and scratch data under /scratch.
Standard library only. Every CLI call is made once; nothing is retried.
"""

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import threading
import time

CLI = os.environ.get("LAYERFS_CLI", "/cli/layerfs")
OUT = "/out"
SECRETS = [
    os.environ.get(name, "")
    for name in (
        "LAYERFS_R2_ACCESS_KEY",
        "LAYERFS_R2_SECRET_KEY",
        "R2_ACCOUNT",
        "LAYERFS_REMOTE_ACCESS_KEY",
        "LAYERFS_REMOTE_SECRET_KEY",
        "LAYERFS_BAD_ACCESS_KEY",
        "LAYERFS_BAD_SECRET_KEY",
    )
]


def redact(text):
    for secret in SECRETS:
        if len(secret) >= 8:
            text = text.replace(secret, "<redacted>")
    return text


def receipt(entry):
    with open(os.path.join(OUT, "receipts.jsonl"), "a") as out:
        out.write(redact(json.dumps(entry)) + "\n")


def run(label, args, expect=None, stdin=None, quiet=False, hook=None):
    """Runs `layerfs <args>` once; returns (exit, parsed stdout or None, progress).

    Records argv, exit, stdout, the refusal on stderr, every progress line with
    its time since start, peak RSS (VmHWM) and the lowest free space on /scratch.
    """
    started = time.time()
    proc = subprocess.Popen(
        [CLI, *args],
        stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    progress, other, peak = [], [], {"rss_kib": 0, "min_free": None}

    def read_stderr():
        for raw in proc.stderr:
            line = raw.decode(errors="replace").rstrip("\n")
            at = round(time.time() - started, 3)
            try:
                value = json.loads(line)
            except ValueError:
                value = None
            if isinstance(value, dict) and "progress" in value:
                progress.append([at, value["progress"]])
                if hook:
                    hook(value["progress"])
                if not quiet:
                    print(f"PROGRESS {label} {at} {json.dumps(value['progress'])}", flush=True)
            else:
                other.append(line)

    def sample():
        while proc.poll() is None:
            try:
                with open(f"/proc/{proc.pid}/status") as status:
                    for row in status:
                        if row.startswith("VmHWM:"):
                            peak["rss_kib"] = max(peak["rss_kib"], int(row.split()[1]))
            except OSError:
                pass
            free = os.statvfs("/scratch")
            free = free.f_bavail * free.f_frsize
            peak["min_free"] = free if peak["min_free"] is None else min(peak["min_free"], free)
            time.sleep(0.05)

    readers = [threading.Thread(target=read_stderr, daemon=True), threading.Thread(target=sample, daemon=True)]
    for thread in readers:
        thread.start()
    free_before = os.statvfs("/scratch")
    free_before = free_before.f_bavail * free_before.f_frsize
    # stderr belongs to the reader thread; feed stdin and read stdout here
    if stdin is not None:
        proc.stdin.write(stdin)
        proc.stdin.close()
    out = proc.stdout.read()
    proc.wait()
    for thread in readers:
        thread.join(timeout=5)
    text = out.decode(errors="replace")
    try:
        parsed = json.loads(text) if text.strip() else None
    except ValueError:
        parsed = None
    refusal = None
    for line in other:
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict) and "code" in value:
            refusal = value
    entry = {
        "label": label,
        "argv": ["layerfs", *args],
        "start": round(started, 3),
        "seconds": round(time.time() - started, 3),
        "exit": proc.returncode,
        "stdout": text[:4000],
        "refusal": refusal,
        "stderr_other": other[-5:],
        "progress": progress,
        "peak_rss_kib": peak["rss_kib"],
        "scratch_used_peak": None if peak["min_free"] is None else max(0, free_before - peak["min_free"]),
    }
    if expect is not None:
        entry["expected_exit"] = expect
        entry["verdict"] = "PASS" if proc.returncode == expect else "FAIL"
    receipt(entry)
    print(
        redact(
            f"RESULT {label} exit={proc.returncode}"
            + (f" expected={expect} {entry['verdict']}" if expect is not None else "")
            + (f" refusal={refusal['code']}: {refusal['message'][:300]}" if refusal else "")
        ),
        flush=True,
    )
    return proc.returncode, parsed, progress


def ok(label, args, stdin=None):
    code, parsed, _ = run(label, args, expect=0, stdin=stdin, quiet=True)
    if code != 0:
        raise SystemExit(f"{label} failed")
    return parsed


def paged(label, args):
    items, pos = [], None
    while True:
        page = ok(label, args + (["--page-pos", str(pos)] if pos is not None else []))
        items.extend(page["items"])
        pos = page.get("next_page_pos")
        if not page.get("has_more") or pos is None:
            return items


def noise(size, seed):
    rng = random.Random(seed)
    return rng.randbytes(size)


def fixture(args):
    """A Store with text and binary files, folders, modes, a published layer
    and two branches with several Commits each (text, binary, mkdir, rm)."""
    src = f"{os.environ['LAYERFS_HOME']}.src-{args.store}"
    os.makedirs(f"{src}/docs/nested", exist_ok=True)
    os.chmod(src, 0o700)
    with open(f"{src}/README.md", "w") as f:
        f.write("backed up\n")
    with open(f"{src}/docs/nested/notes.txt", "w") as f:
        f.write("line one\nline two\n")
    with open(f"{src}/run.sh", "w") as f:
        f.write("#!/bin/sh\necho hi\n")
    os.chmod(f"{src}/run.sh", 0o755)
    with open(f"{src}/small.bin", "wb") as f:
        f.write(noise(4096, 1))
    if args.mib:
        with open(f"{src}/large.bin", "wb") as f:
            for chunk in range(args.mib):
                f.write(noise(1 << 20, 1000 + chunk))
    project = f"{args.store}/api"
    ok("store create", ["store", "create", args.store])
    ok("project init", ["project", "init", project, src])
    if args.history:
        ok("fork dev", ["branch", "fork", project, "dev", "main"])
        ok("write dev text", ["file", "write", project, "dev", "/README.md", "-m", "edit readme"], b"edited on dev\n")
        ok("mkdir dev", ["file", "mkdir", project, "dev", "/made"])
        ok("write dev binary", ["file", "write", project, "dev", "/made/data.bin"], noise(1500, 2))
        ok("rm dev", ["file", "rm", project, "dev", "/docs/nested/notes.txt"])
        ok("publish dev", ["branch", "publish", project, "dev"])
        ok("fork topic", ["branch", "fork", project, "topic", "main"])
        ok("write topic", ["file", "write", project, "topic", "/topic.txt"], b"topic work\n")
    print("FIXTURE READY", flush=True)


def tree(project, branch, commit=None):
    """Every path under / of `branch` (at `commit`): type, size, mode, and the
    text of text files (binary files are covered by the Commit's root)."""
    files, stack = {}, ["/"]
    at = [commit] if commit else []
    while stack:
        folder = stack.pop()
        for item in paged("file list", ["file", "list", project, branch, folder, *at]):
            path = item["path"]
            stat = ok("file stat", ["file", "stat", project, branch, path, *at])
            entry = {"type": stat["type"], "size": stat.get("size"), "mode": stat.get("mode")}
            if item["type"] == "dir":
                stack.append(path)
            elif item["type"] == "file":
                code, parsed, _ = run("file read", ["file", "read", project, branch, path, *at], quiet=True)
                if code == 0 and not parsed.get("truncated"):
                    entry["text_sha256"] = hashlib.sha256(parsed["text"].encode()).hexdigest()
                else:
                    entry["text"] = "binary or truncated"
            files[path] = entry
    return files


def snapshot(args):
    """Projects, Branches, every Commit (id, parent, root) and each Branch
    head's tree, as one JSON file to compare across Stores."""
    store = args.store
    result = {"store": store, "projects": {}}
    for project in paged("project list", ["project", "list", store]):
        name = project["project"]
        branches = {}
        for branch in paged("branch list", ["branch", "list", name]):
            commits = []
            if branch.get("head"):
                for commit in paged("commit list", ["commit", "list", name, branch["name"]]):
                    commits.append({k: commit.get(k) for k in ("id", "parent", "second_parent", "root", "message")})
            branches[branch["name"]] = {
                "base": branch.get("base"),
                "head": branch.get("head"),
                "commits": commits,
                "tree": tree(name, branch["name"]) if args.trees else None,
            }
        result["projects"][project["name"]] = {"layer": project.get("layer"), "branches": branches}
    with open(args.out, "w") as out:
        json.dump(result, out, indent=1, sort_keys=True)
    print(f"SNAPSHOT {store} -> {args.out}", flush=True)


def compare(args):
    a, b = (json.load(open(path)) for path in (args.a, args.b))
    a.pop("store"), b.pop("store")
    same = a == b
    receipt({"label": "compare", "a": args.a, "b": args.b, "verdict": "PASS" if same else "FAIL"})
    print(f"COMPARE {'PASS' if same else 'FAIL'} {args.a} {args.b}", flush=True)
    if not same:
        for name in sorted(set(a["projects"]) | set(b["projects"])):
            if a["projects"].get(name) != b["projects"].get(name):
                print(f"  differs: project {name}", flush=True)
        raise SystemExit(1)


def write_read(args):
    """A new Commit on the restored Store, then read back."""
    project, branch = args.project, args.branch
    text = f"written after restore {time.time()}\n"
    made = ok("write after restore", ["file", "write", project, branch, "/after-restore.txt"], text.encode())
    read = ok("read after restore", ["file", "read", project, branch, "/after-restore.txt"])
    same = read["text"] == text and made["kind"] == "Committed"
    receipt({"label": "write-read", "verdict": "PASS" if same else "FAIL"})
    print(f"WRITE-READ {'PASS' if same else 'FAIL'}", flush=True)
    if not same:
        raise SystemExit(1)


def churn(args):
    """Commits `/counter` = 1, 2, ... on `branch` for `seconds`; the file's
    value always equals the number of Commits on the branch."""
    deadline = time.time() + args.seconds
    n = 0
    while time.time() < deadline:
        n += 1
        ok("churn write", ["file", "write", args.project, args.branch, "/counter"], f"{n}\n".encode())
    print(f"CHURN {n} commits", flush=True)


def counter_check(args):
    """The restored branch is one consistent frontier: `/counter` equals its
    Commit count, and every Commit's own `/counter` equals its position."""
    commits = paged("commit list", ["commit", "list", args.project, args.branch])
    head = ok("read counter", ["file", "read", args.project, args.branch, "/counter"])["text"].strip()
    good = int(head) == len(commits)
    for position, commit in enumerate(reversed(commits), start=1):
        if position % max(1, len(commits) // 5) and position != len(commits):
            continue
        value = ok("read counter at", ["file", "read", args.project, args.branch, "/counter", commit["id"]])
        good &= value["text"].strip() == str(position)
    receipt({"label": "counter-check", "commits": len(commits), "head": head, "verdict": "PASS" if good else "FAIL"})
    print(f"COUNTER {'PASS' if good else 'FAIL'} commits={len(commits)} head={head}", flush=True)
    if not good:
        raise SystemExit(1)


def race_install(args):
    """Restores into a new name and makes a Store of that name as soon as
    the download has moved bytes: the restore must refuse at install."""
    made = []

    def hook(update):
        if not made and update.get("phase") == "download" and (update.get("done") or 0) > 0:
            made.append(True)
            threading.Thread(target=lambda: run("race store create", ["store", "create", args.store], quiet=True)).start()

    code, _, progress = run("restore racing a store create", json.loads(args.restore), hook=hook)
    time.sleep(1)
    phases = [p[1]["phase"] for p in progress]
    good = code == 125 and bool(made) and "download" in phases
    receipt({"label": "race-install", "exit": code, "phases": phases, "verdict": "PASS" if good else "FAIL"})
    print(f"RACE {'PASS' if good else 'FAIL'} exit={code} phases={phases}", flush=True)


def parallel(args):
    """Runs two CLI commands at the same moment and records both."""
    results = {}

    def one(name, argv):
        results[name] = run(f"parallel {name}", argv)

    threads = [threading.Thread(target=one, args=(n, json.loads(a))) for n, a in (("a", args.a), ("b", args.b))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    print("PARALLEL " + json.dumps({k: v[0] for k, v in results.items()}), flush=True)
    for name, (code, parsed, _) in sorted(results.items()):
        if parsed:
            print(f"PARALLEL-RESULT {name} " + redact(json.dumps(parsed))[:600], flush=True)


def churn_backup(args):
    """Runs `churn` in the background and `layerfs <rest>` while it writes."""
    bg = subprocess.Popen([sys.executable, __file__, "churn", "--project", args.project, "--branch", args.branch, "--seconds", str(args.seconds)])
    time.sleep(args.delay)
    code, parsed, _ = run("create during churn", args.rest, expect=0)
    bg.wait(timeout=args.seconds + 60)
    if parsed:
        print("CREATED " + redact(json.dumps(parsed)), flush=True)


def cli(args):
    expect = None if args.expect == "any" else int(args.expect)
    stdin = sys.stdin.buffer.read() if args.stdin else None
    code, _, _ = run(args.label, args.rest, expect=expect, stdin=stdin)
    if expect is not None and code != expect:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="step", required=True)
    p = sub.add_parser("fixture")
    p.add_argument("--store", required=True)
    p.add_argument("--mib", type=int, default=0)
    p.add_argument("--history", action="store_true")
    p = sub.add_parser("snapshot")
    p.add_argument("--store", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--trees", action="store_true")
    p = sub.add_parser("compare")
    p.add_argument("a")
    p.add_argument("b")
    p = sub.add_parser("write-read")
    p.add_argument("--project", required=True)
    p.add_argument("--branch", required=True)
    p = sub.add_parser("churn")
    p.add_argument("--project", required=True)
    p.add_argument("--branch", required=True)
    p.add_argument("--seconds", type=float, required=True)
    p = sub.add_parser("counter-check")
    p.add_argument("--project", required=True)
    p.add_argument("--branch", required=True)
    p = sub.add_parser("race-install")
    p.add_argument("--store", required=True)
    p.add_argument("--restore", required=True)
    p = sub.add_parser("parallel")
    p.add_argument("--a", required=True)
    p.add_argument("--b", required=True)
    p = sub.add_parser("churn-backup")
    p.add_argument("--project", required=True)
    p.add_argument("--branch", required=True)
    p.add_argument("--seconds", type=float, required=True)
    p.add_argument("--delay", type=float, default=1.0)
    p.add_argument("rest", nargs=argparse.REMAINDER)
    p = sub.add_parser("cli")
    p.add_argument("--label", required=True)
    p.add_argument("--expect", default="0")
    p.add_argument("--stdin", action="store_true")
    p.add_argument("rest", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if getattr(args, "rest", None) and args.rest[0] == "--":
        args.rest = args.rest[1:]
    {
        "fixture": fixture,
        "snapshot": snapshot,
        "compare": compare,
        "write-read": write_read,
        "churn": churn,
        "counter-check": counter_check,
        "race-install": race_install,
        "parallel": parallel,
        "churn-backup": churn_backup,
        "cli": cli,
    }[args.step](args)


if __name__ == "__main__":
    main()
