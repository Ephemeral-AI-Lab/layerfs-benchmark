#!/usr/bin/env python3
"""Seeded edit model, oracle and in-Workspace applier for fs-storage-history.

One file, two roles:

* On the host, `State` holds a tree in memory (path -> Entry) and
  `plan_step(state, seed, step)` draws one Commit's five operations from a
  portable BLAKE2b counter PRNG keyed by `(seed, step)`, applying each to the
  state as it goes. The resulting state is the oracle for the branch head.
* In the Sandbox image (`/opt/fs-storage-history/model.py`), `apply` performs
  the same concrete operations on the Workspace (the current directory) and
  `manifest` prints a small digest of the tree for final-state verification.

Write methods (part of the workload):
  edit    in place: same inode, open(O_WRONLY|O_TRUNC), rewrite
  append  in place: same inode, open(O_WRONLY|O_APPEND)
  new     new path: open(O_WRONLY|O_CREAT|O_EXCL), mode 0644
  delete  unlink(2)
  rename  rename(2) to a path that does not exist
Directories left empty by delete/rename are removed (the base, a Git tree,
has none), so the oracle is files and symlinks only.

Generated text is synthetic (a fixed 128-word vocabulary). Standard library
only; runs on Python 3.9+ with identical results (no `random` module).
"""

import base64
import bisect
import hashlib
import json
import os
import stat
import sys
import zlib

MODEL_VERSION = "fsh-edit-model-v1"
OPS_PER_COMMIT = 5
# Shares out of 100, in draw order.
OP_SHARES = (("edit", 70), ("new", 10), ("delete", 5), ("rename", 10), ("append", 5))
EDIT_LINES = (1, 5)
EDIT_ACTIONS = (("replace", 50), ("insert", 30), ("delete", 20))
NEW_FILE_BYTES = (256, 4096)
NEW_FILE_EXTENSIONS = ("md", "ts", "txt", "yaml")
APPEND_BYTES = (80, 240)
LOG_SUFFIXES = (".jsonl", ".log")
FALLBACK_LOG = "fsh-activity.log"
RENAME_SAME_DIRECTORY = 80  # percent; the rest move to a random directory
BUCKETS = 256

WORDS = tuple(
    """
    able about above across action active adapt agent align alpha amber angle
    apply arrow asset audit basis batch beacon before binary block border branch
    bridge buffer build bundle cache canvas carbon cargo center chain change
    channel check chunk circle client cloud cluster commit compact config copper
    core cursor custom cycle daemon delta depth device digest domain draft driver
    echo edge engine entry event field filter final flag folder format frame
    gamma garden gate graph group handle harbor header index input kernel ladder
    layer ledger limit linear local lumen marker matrix merge metric mirror model
    module native needle nested object offset orbit output packet parent patch
    pilot pixel plain policy portal prefix probe queue radius random record relay
    render replica result review river router sample scope shadow signal socket
    """.split()
)
assert len(WORDS) == len(set(WORDS)) == 128, len(WORDS)


# --------------------------------------------------------------------------
# Portable PRNG: BLAKE2b-64 over (key, counter); unbiased integer draws.


class Rng:
    def __init__(self, *key):
        self.key = "\x1f".join(str(part) for part in key).encode()
        self.counter = 0

    def u64(self):
        data = self.key + b"\x1e" + str(self.counter).encode()
        self.counter += 1
        return int.from_bytes(hashlib.blake2b(data, digest_size=8).digest(), "big")

    def below(self, n):
        if n <= 0:
            raise ValueError("below() needs a positive bound")
        limit = (1 << 64) - ((1 << 64) % n)
        while True:
            value = self.u64()
            if value < limit:
                return value % n

    def between(self, lo, hi):
        return lo + self.below(hi - lo + 1)

    def choice(self, items):
        return items[self.below(len(items))]

    def weighted(self, shares):
        total = sum(weight for _, weight in shares)
        value = self.below(total)
        for name, weight in shares:
            if value < weight:
                return name
            value -= weight
        raise AssertionError("unreachable")


def line(rng):
    indent = " " * (2 * rng.below(4))
    words = [rng.choice(WORDS) for _ in range(rng.between(3, 12))]
    return indent + " ".join(words) + "\n"


def text_block(rng, size):
    parts, total = [], 0
    while total < size:
        piece = line(rng)
        parts.append(piece)
        total += len(piece)
    return "".join(parts)


# --------------------------------------------------------------------------
# Host-side state (the oracle).


class Entry:
    __slots__ = ("kind", "mode", "data", "_sha", "_text")

    def __init__(self, kind, mode, data):
        if kind not in ("file", "link"):
            raise ValueError(kind)
        self.kind, self.mode, self.data = kind, mode, bytes(data)
        self._sha = None
        self._text = None

    @property
    def sha256(self):
        if self._sha is None:
            self._sha = hashlib.sha256(self.data).hexdigest()
        return self._sha

    @property
    def text(self):
        if self._text is None:
            self._text = self.kind == "file" and b"\0" not in self.data
        return self._text


def parent(path):
    return path.rsplit("/", 1)[0] if "/" in path else ""


def ancestors(path):
    out = []
    while "/" in path:
        path = parent(path)
        out.append(path)
    return out


def _remove_sorted(items, value):
    index = bisect.bisect_left(items, value)
    if index == len(items) or items[index] != value:
        raise KeyError(value)
    del items[index]


class State:
    """A tree of regular files and symlinks with sorted candidate indexes."""

    def __init__(self, entries=None):
        self.entries = {}
        self.files = []  # regular files
        self.text = []  # text regular files
        self.logs = []  # regular files ending in LOG_SUFFIXES
        self.dir_count = {"": 0}  # directory -> entries beneath it (recursive)
        self.dirs = [""]
        for path in sorted(entries or {}):
            self.add(path, entries[path])

    def copy(self):
        other = State.__new__(State)
        other.entries = dict(self.entries)
        other.files = list(self.files)
        other.text = list(self.text)
        other.logs = list(self.logs)
        other.dir_count = dict(self.dir_count)
        other.dirs = list(self.dirs)
        return other

    def add(self, path, entry):
        if not path or path.startswith("/") or path in self.entries:
            raise ValueError(f"bad or existing path {path!r}")
        if path in self.dir_count:
            raise ValueError(f"{path!r} is a directory")
        for directory in ancestors(path):
            if directory in self.entries:
                raise ValueError(f"{directory!r} is a file")
        self.entries[path] = entry
        if entry.kind == "file":
            bisect.insort(self.files, path)
            if entry.text:
                bisect.insort(self.text, path)
            if path.endswith(LOG_SUFFIXES):
                bisect.insort(self.logs, path)
        for directory in ancestors(path):
            if directory not in self.dir_count:
                self.dir_count[directory] = 0
                bisect.insort(self.dirs, directory)
            self.dir_count[directory] += 1

    def remove(self, path):
        entry = self.entries.pop(path)
        if entry.kind == "file":
            _remove_sorted(self.files, path)
            if entry.text:
                _remove_sorted(self.text, path)
            if path.endswith(LOG_SUFFIXES):
                _remove_sorted(self.logs, path)
        for directory in ancestors(path):
            self.dir_count[directory] -= 1
            if directory and self.dir_count[directory] == 0:
                del self.dir_count[directory]
                _remove_sorted(self.dirs, directory)
        return entry

    def replace(self, path, data):
        old = self.entries[path]
        new = Entry(old.kind, old.mode, data)
        if new.text != old.text:  # an edit never adds NUL; kept for safety
            self.remove(path)
            self.add(path, new)
        else:
            self.entries[path] = new
        return old, new

    # -- manifest ----------------------------------------------------------

    def manifest_lines(self):
        for path in sorted(self.entries, key=lambda p: p.encode()):
            entry = self.entries[path]
            mode = entry.mode if entry.kind == "file" else 0
            yield path, f"{path}\t{entry.kind}\t{mode:o}\t{len(entry.data)}\t{entry.sha256}\n"

    def summary(self):
        return summarize(self.manifest_lines(), empty_dirs=0, other=0)


def summarize(lines, empty_dirs, other):
    whole = hashlib.sha256()
    buckets = [hashlib.sha256() for _ in range(BUCKETS)]
    files = links = size = 0
    for path, text in lines:
        whole.update(text.encode())
        buckets[hashlib.sha256(path.encode()).digest()[0]].update(text.encode())
        kind, _, length = text.split("\t")[1:4]
        if kind == "file":
            files += 1
        else:
            links += 1
        size += int(length)
    return {
        "model": MODEL_VERSION,
        "files": files,
        "links": links,
        "bytes": size,
        "empty_dirs": empty_dirs,
        "other": other,
        "sha256": whole.hexdigest(),
        "buckets": [bucket.hexdigest()[:16] for bucket in buckets],
    }


def bucket_of(path):
    return hashlib.sha256(path.encode()).digest()[0]


# --------------------------------------------------------------------------
# Planning: one Commit's operations from (seed, step).


def plan_step(state, seed, step):
    """Draw OPS_PER_COMMIT operations, apply them to `state`, return the ops."""
    rng = Rng(MODEL_VERSION, seed, step)
    ops = []
    for index in range(OPS_PER_COMMIT):
        kind = rng.weighted(OP_SHARES)
        ops.append(_plan_one(state, rng, kind, step, index))
    return ops


def _unique(state, path):
    stem, dot, suffix = path.rpartition(".")
    if not dot or "/" in suffix:
        stem, suffix = path, ""
    candidate, counter = path, 0
    while candidate in state.entries or candidate in state.dir_count:
        counter += 1
        candidate = f"{stem}-x{counter}" + (f".{suffix}" if suffix else "")
    return candidate


def _plan_one(state, rng, kind, step, index):
    if kind == "edit" and state.text:
        path = rng.choice(state.text)
        old = state.entries[path]
        lines = old.data.splitlines(keepends=True)
        count = rng.between(*EDIT_LINES)
        action = rng.weighted(EDIT_ACTIONS) if lines else "insert"
        if action == "insert":
            start, delete = rng.below(len(lines) + 1), 0
            insert = [line(rng) for _ in range(count)]
        else:
            delete = min(count, len(lines))
            start = rng.below(len(lines) - delete + 1)
            insert = [line(rng) for _ in range(delete)] if action == "replace" else []
        op = {"op": "edit", "path": path, "pre_sha256": old.sha256, "action": action,
              "start": start, "delete": delete, "insert": insert}
        state.replace(path, apply_edit(old.data, op))
        return op
    if kind == "delete" and state.files:
        path = rng.choice(state.files)
        entry = state.remove(path)
        return {"op": "delete", "path": path, "pre_sha256": entry.sha256}
    if kind == "rename" and state.files:
        path = rng.choice(state.files)
        directory = parent(path)
        if rng.below(100) >= RENAME_SAME_DIRECTORY:
            directory = rng.choice(state.dirs)
        name = path.rsplit("/", 1)[-1]
        stem, dot, suffix = name.rpartition(".")
        if not dot or not stem:
            stem, suffix = name, ""
        renamed = f"{stem}.r{step}-{index}" + (f".{suffix}" if suffix else "")
        target = _unique(state, f"{directory}/{renamed}" if directory else renamed)
        entry = state.remove(path)
        state.add(target, entry)
        return {"op": "rename", "path": path, "to": target, "pre_sha256": entry.sha256}
    if kind == "append":
        payload = json.dumps({"step": step, "op": index,
                              "event": " ".join(rng.choice(WORDS) for _ in range(rng.between(4, 20))),
                              "value": rng.below(1 << 32)}, sort_keys=True) + "\n"
        target = rng.choice(state.logs) if state.logs else None
        if target is None:
            target = _unique(state, FALLBACK_LOG)
            state.add(target, Entry("file", 0o644, payload.encode()))
            return {"op": "append", "path": target, "create": True, "data": payload}
        old = state.entries[target]
        state.replace(target, old.data + payload.encode())
        return {"op": "append", "path": target, "create": False, "pre_sha256": old.sha256,
                "data": payload}
    # "new", and the fallback when a tree has nothing to edit/delete/rename.
    directory = rng.choice(state.dirs)
    ext = rng.choice(NEW_FILE_EXTENSIONS)
    name = f"fsh-{step:04d}-{index}.{ext}"
    target = _unique(state, f"{directory}/{name}" if directory else name)
    data = text_block(rng, rng.between(*NEW_FILE_BYTES))
    state.add(target, Entry("file", 0o644, data.encode()))
    return {"op": "new", "path": target, "data": data}


def apply_edit(data, op):
    lines = data.splitlines(keepends=True)
    start, delete = op["start"], op["delete"]
    if start + delete > len(lines):
        raise ValueError(f"edit window outside {op['path']}")
    insert = [text.encode() for text in op["insert"]]
    return b"".join(lines[:start] + insert + lines[start + delete:])


# --------------------------------------------------------------------------
# Transport of concrete ops into the Sandbox.


def encode_ops(ops):
    raw = json.dumps(ops, sort_keys=True, separators=(",", ":")).encode()
    return base64.b64encode(zlib.compress(raw, 9)).decode()


def decode_ops(text):
    return json.loads(zlib.decompress(base64.b64decode(text)))


def ops_digest(ops):
    raw = json.dumps(ops, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


# --------------------------------------------------------------------------
# Disk side (runs inside the Workspace; also used by tests on a temp dir).


def _sha_file(path):
    with open(path, "rb") as stream:
        return hashlib.sha256(stream.read()).hexdigest()


def _check(path, expected):
    if not os.path.isfile(path) or os.path.islink(path):
        raise SystemExit(f"precondition: {path} is not a regular file")
    if expected is not None and _sha_file(path) != expected:
        raise SystemExit(f"precondition: {path} content differs from the oracle")


def _prune(directory, root):
    while directory and directory != root:
        try:
            os.rmdir(directory)
        except OSError:
            return
        directory = os.path.dirname(directory)


def apply_ops(ops, root="."):
    counts = {}
    for op in ops:
        kind = op["op"]
        path = os.path.join(root, op["path"])
        if kind == "edit":
            _check(path, op["pre_sha256"])
            with open(path, "rb") as stream:
                data = stream.read()
            fd = os.open(path, os.O_WRONLY | os.O_TRUNC)
            with os.fdopen(fd, "wb") as stream:
                stream.write(apply_edit(data, op))
        elif kind == "append":
            if op.get("create"):
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
                os.fchmod(fd, 0o644)
            else:
                _check(path, op["pre_sha256"])
                fd = os.open(path, os.O_WRONLY | os.O_APPEND)
            with os.fdopen(fd, "wb") as stream:
                stream.write(op["data"].encode())
        elif kind == "new":
            os.makedirs(os.path.dirname(path) or root, exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            os.fchmod(fd, 0o644)
            with os.fdopen(fd, "wb") as stream:
                stream.write(op["data"].encode())
        elif kind == "delete":
            _check(path, op["pre_sha256"])
            os.unlink(path)
            _prune(os.path.dirname(path), os.path.normpath(root))
        elif kind == "rename":
            _check(path, op["pre_sha256"])
            target = os.path.join(root, op["to"])
            if os.path.lexists(target):
                raise SystemExit(f"precondition: {op['to']} exists")
            os.makedirs(os.path.dirname(target) or root, exist_ok=True)
            os.rename(path, target)
            _prune(os.path.dirname(path), os.path.normpath(root))
        else:
            raise SystemExit(f"unknown op {kind}")
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def disk_manifest(root="."):
    root = os.path.normpath(root)
    lines, empty_dirs, other = [], 0, 0
    for directory, dirnames, filenames in os.walk(root):
        dirnames.sort()
        if directory != root and not dirnames and not filenames:
            empty_dirs += 1
        for name in dirnames:
            full = os.path.join(directory, name)
            if os.path.islink(full):  # os.walk lists dir symlinks as dirs
                filenames.append(name)
        dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(directory, d))]
        for name in filenames:
            full = os.path.join(directory, name)
            rel = os.path.relpath(full, root)
            info = os.lstat(full)
            if stat.S_ISLNK(info.st_mode):
                data = os.readlink(full).encode()
                text = f"{rel}\tlink\t0\t{len(data)}\t{hashlib.sha256(data).hexdigest()}\n"
            elif stat.S_ISREG(info.st_mode):
                text = (f"{rel}\tfile\t{stat.S_IMODE(info.st_mode):o}\t{info.st_size}\t"
                        f"{_sha_file(full)}\n")
            else:
                other += 1
                continue
            lines.append((rel, text))
    lines.sort(key=lambda item: item[0].encode())
    return summarize(lines, empty_dirs=empty_dirs, other=other)


def main(argv):
    if len(argv) == 2 and argv[0] == "apply":
        counts = apply_ops(decode_ops(argv[1]))
        print(json.dumps({"model": MODEL_VERSION, "applied": counts}, sort_keys=True))
        return 0
    if len(argv) == 1 and argv[0] == "manifest":
        print(json.dumps(disk_manifest("."), sort_keys=True))
        return 0
    print("usage: model.py apply <ops> | model.py manifest", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
