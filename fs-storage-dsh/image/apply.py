#!/usr/bin/env python3
"""Moves the Workspace (the current directory) from seed state FROM to TO.

    python3 /opt/fs-storage-dsh/apply.py FROM TO

States are 1..157 of the pinned seed (state 0 is the empty tree). Both trees
are read from the seed repository inside the image with `git ls-tree` and the
blobs with one `git cat-file --batch`; nothing is read from the host.

Write method (part of the workload; ported from dsh-dedup `sandbox/apply.py`):

- a path that stays a regular file and changes content is rewritten in place:
  the same inode, opened ``O_WRONLY|O_TRUNC`` and written whole; a mode-only
  change is a chmod;
- a removed path, or one whose type changes (file <-> symlink), is unlinked;
- new paths are created (``O_CREAT|O_EXCL``, mode 0644 or 0755);
- a symlink whose target changes is unlinked and recreated;
- directories left empty are removed (Git trees have none).

Prints one JSON line of counts; exits non-zero on any error.
"""

import json
import os
import shutil
import subprocess
import sys

ROOT = "/opt/fs-storage-dsh"
REPO = f"{ROOT}/seed/snapshots.git"
MAPPING = f"{ROOT}/seed/mapping.json"
LINK, FILE = "link", "file"
MODES = {"100644": FILE, "100755": FILE, "120000": LINK}


def kind(mode):
    return MODES[mode]


def git(*args, **kwargs):
    return subprocess.run(
        ["git", "-c", f"safe.directory={REPO}", f"--git-dir={REPO}", *args],
        check=True,
        **kwargs,
    )


def tree_of(state):
    """The pinned root tree of state 1..157 from the seed mapping."""
    with open(MAPPING) as stream:
        mapping = json.load(stream)
    entry = mapping[state - 1]
    if entry["index"] != state:
        raise SystemExit(f"apply.py: mapping row {state} is index {entry['index']}")
    return entry["tree"]


def entries(state):
    """{path bytes: (mode, blob id)} of one state; state 0 is empty."""
    if state == 0:
        return {}
    out = git("ls-tree", "-r", "-z", "--full-tree", tree_of(state), capture_output=True).stdout
    rows = {}
    for record in out.split(b"\0"):
        if not record:
            continue
        meta, path = record.split(b"\t", 1)
        mode, typ, oid = meta.decode().split(" ")
        if typ != "blob" or mode not in MODES:
            raise SystemExit(f"apply.py: unsupported entry {mode} {typ} {path!r}")
        rows[path] = (mode, oid)
    return rows


class Blobs:
    """Streams blob contents through one `git cat-file --batch` process."""

    def __init__(self):
        self.process = subprocess.Popen(
            ["git", "-c", f"safe.directory={REPO}", f"--git-dir={REPO}", "cat-file", "--batch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

    def read(self, oid):
        self.process.stdin.write(oid.encode() + b"\n")
        self.process.stdin.flush()
        header = self.process.stdout.readline().split()
        if len(header) != 3 or header[0].decode() != oid or header[1] != b"blob":
            raise SystemExit(f"apply.py: cat-file answered {header!r} for {oid}")
        size = int(header[2])
        data = self.process.stdout.read(size)
        if len(data) != size or self.process.stdout.read(1) != b"\n":
            raise SystemExit(f"apply.py: short read of {oid}")
        return data

    def close(self):
        self.process.stdin.close()
        if self.process.wait() != 0:
            raise SystemExit("apply.py: cat-file failed")


def apply(old, new, read, root=b"."):
    """Move `root` from manifest `old` to `new`; returns counts.

    `old`/`new` map relative path bytes to (mode, blob id); `read(blob id)`
    returns the content bytes. Pure apart from the filesystem under `root`.
    """
    counts = {
        "removed": 0,
        "created": 0,
        "created_bytes": 0,
        "overwritten": 0,
        "overwritten_bytes": 0,
        "relinked": 0,
        "chmod": 0,
        "dirs_removed": 0,
    }

    def at(path):
        return os.path.join(root, path)

    for path, (mode, _) in sorted(old.items()):
        if path not in new or kind(new[path][0]) != kind(mode):
            os.unlink(at(path))
            counts["removed"] += 1

    for path, (mode, oid) in sorted(new.items()):
        before = old.get(path)
        if before == (mode, oid):
            continue
        parent = os.path.dirname(path)
        if parent:
            # A path that was a file and is now a directory was unlinked above.
            os.makedirs(at(parent), mode=0o755, exist_ok=True)
        full = at(path)
        if os.path.isdir(full) and not os.path.islink(full):
            shutil.rmtree(full)  # a directory replaced by a file or link
        if kind(mode) == LINK:
            data = read(oid)
            if before is not None and kind(before[0]) == LINK:
                os.unlink(full)
                counts["relinked"] += 1
            else:
                counts["created"] += 1
            os.symlink(data, full)
            continue
        perm = 0o755 if mode == "100755" else 0o644
        if before is not None and kind(before[0]) == FILE:
            if before[1] != oid:
                data = read(oid)
                fd = os.open(full, os.O_WRONLY | os.O_TRUNC)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                counts["overwritten"] += 1
                counts["overwritten_bytes"] += len(data)
            if before[0] != mode:
                os.chmod(full, perm)
                counts["chmod"] += 1
        else:
            data = read(oid)
            fd = os.open(full, os.O_WRONLY | os.O_CREAT | os.O_EXCL, perm)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
            os.chmod(full, perm)
            counts["created"] += 1
            counts["created_bytes"] += len(data)

    for dirpath, _, _ in os.walk(root, topdown=False):
        if dirpath != root and not os.listdir(dirpath):
            os.rmdir(dirpath)
            counts["dirs_removed"] += 1
    return counts


def main(argv):
    if len(argv) != 3:
        raise SystemExit("usage: apply.py FROM TO")
    before, after = int(argv[1]), int(argv[2])
    if not (0 <= before < after <= 157):
        raise SystemExit("apply.py: need 0 <= FROM < TO <= 157")
    old, new = entries(before), entries(after)
    blobs = Blobs()
    counts = apply(old, new, blobs.read)
    blobs.close()
    print(json.dumps({"from": before, "to": after, "entries": len(new), **counts}, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv)
