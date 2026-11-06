#!/usr/bin/env python3
"""Extract and pin the base tree: DSH checkpoint 157 from the local seed.

    python3 base.py --seed <snapshots.git> --dest <dir>

The seed is a read-only bare Git repository; the base is its last Commit
(`BASE_COMMIT`, tree `BASE_TREE`). Files are written 0644 or 0755 (Git's
modes), directories 0755, symlinks as links. The extracted copy lives in a
private cache, never in Git or a report. Prints the pinned manifest summary
and refuses a tree that differs from the pins in cases.py.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cases  # noqa: E402
import model  # noqa: E402


def read_seed(seed):
    """Return {path: Entry} for BASE_COMMIT from the bare seed repository."""
    tree = subprocess.run(
        ["git", "--git-dir", str(seed), "rev-parse", cases.BASE_COMMIT + "^{tree}"],
        check=True, capture_output=True, text=True, timeout=60,
    ).stdout.strip()
    if tree != cases.BASE_TREE:
        raise SystemExit(f"seed tree {tree} differs from the pinned {cases.BASE_TREE}")
    # Raw blobs, not `git archive`: the tree's .gitattributes would convert
    # line endings (*.cmd) on export.
    listing = subprocess.run(
        ["git", "--git-dir", str(seed), "ls-tree", "-r", "-z", "--full-tree", cases.BASE_COMMIT],
        check=True, capture_output=True, timeout=60,
    ).stdout
    rows = []
    for record in listing.split(b"\0"):
        if not record:
            continue
        meta, path = record.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        if kind != "blob" or mode not in ("100644", "100755", "120000"):
            raise SystemExit(f"unexpected tree entry {mode} {kind} {path!r}")
        rows.append((mode, oid, path.decode()))
    batch = subprocess.run(
        ["git", "--git-dir", str(seed), "cat-file", "--batch"],
        input="".join(oid + "\n" for _, oid, _ in rows).encode(),
        check=True, capture_output=True, timeout=120,
    ).stdout
    entries, offset = {}, 0
    for mode, oid, path in rows:
        header_end = batch.index(b"\n", offset)
        got, kind, size = batch[offset:header_end].decode().split()
        if got != oid or kind != "blob":
            raise SystemExit(f"cat-file answered {got} {kind} for {oid}")
        data = batch[header_end + 1:header_end + 1 + int(size)]
        offset = header_end + 2 + int(size)
        if mode == "120000":
            entries[path] = model.Entry("link", 0, data)
        else:
            entries[path] = model.Entry("file", 0o755 if mode == "100755" else 0o644, data)
    return entries


def write_tree(entries, dest):
    dest = Path(dest)
    if dest.exists():
        raise SystemExit(f"{dest} exists; extract into a fresh directory")
    dest.mkdir(parents=True, mode=0o755)
    for path in sorted(entries):
        entry = entries[path]
        full = dest / path
        full.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        if entry.kind == "link":
            os.symlink(entry.data.decode(), full)
        else:
            fd = os.open(full, os.O_WRONLY | os.O_CREAT | os.O_EXCL, entry.mode)
            with os.fdopen(fd, "wb") as stream:
                stream.write(entry.data)
            os.chmod(full, entry.mode)
    for directory, _, _ in os.walk(dest):
        os.chmod(directory, 0o755)


def load_tree(root):
    """Read an extracted base back into a State (host oracle input)."""
    root = Path(root)
    entries = {}
    for directory, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            full = Path(directory) / name
            rel = full.relative_to(root).as_posix()
            if full.is_symlink():
                entries[rel] = model.Entry("link", 0, os.readlink(full).encode())
            elif full.is_file():
                entries[rel] = model.Entry("file", full.stat().st_mode & 0o7777, full.read_bytes())
    return model.State(entries)


def check_pins(summary):
    expected = {
        "files": cases.BASE_FILES,
        "links": cases.BASE_LINKS,
        "bytes": cases.BASE_BYTES,
        "sha256": cases.BASE_MANIFEST_SHA256,
    }
    actual = {key: summary[key] for key in expected}
    if actual != expected:
        raise SystemExit(f"base tree differs from the pins: {actual} != {expected}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--dest", required=True)
    parser.add_argument("--unpinned", action="store_true", help="print, do not check pins")
    args = parser.parse_args(argv)
    entries = read_seed(args.seed)
    summary = model.State(entries).summary()
    if not args.unpinned:
        check_pins(summary)
    write_tree(entries, args.dest)
    reread = load_tree(args.dest).summary()
    if reread["sha256"] != summary["sha256"]:
        raise SystemExit("extracted tree differs from the seed manifest")
    summary.pop("buckets")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
