#!/usr/bin/env python3
"""fs-storage-quick generator and final-state verifier for Q1–Q5 (stdlib only).

Runs inside the LayerFS Sandbox (cwd = Workspace root) and, for pins, in a
throwaway container of the same image. Every byte comes from SHAKE-256
streams keyed by WORKLOAD_VERSION and a label, so output is identical on any
Python 3. Generated text is SYNTHETIC (a seeded word model), not real prose.
The streams, word model and write methods are fs-storage-micro's
(``image/gen.py``, ``fs-storage-micro-v1``) at smaller counts, keyed by this
suite's own version. Q6 (history) uses ``model.py`` instead.

  gen.py step <case> <part>     apply one part of a case in the cwd
  gen.py oracle <case> <dir>    run every part in an empty dir; print the final manifest
  gen.py manifest [root]        canonical final-state manifest digest (JSON)
  gen.py namespace <paths>      Q6 head check: namespace digest + SHA-256 of the touched paths
  gen.py plan                   the per-case Commit plan (JSON)
"""

import array
import base64
import hashlib
import json
import os
import stat
import sys
import zlib

WORKLOAD_VERSION = "fs-storage-quick-v1"
MiB = 1 << 20

# Counts (frozen with WORKLOAD_VERSION after the calibration probe).
Q1_FILES = 2000  # tiny files, 0..4,096 B
Q1_PER_DIR = 100
TEXT_FILES = 25  # Q2/Q3/Q4: synthetic text files of 16..64 KiB
TEXT_EDITS = 12  # edit Commits after the create Commit
LARGE_BYTES = 32 * MiB  # Q5

# Each case is a list of Commits; each Commit lists the parts run (one Exec
# each) before it.
PLAN = {
    "Q1": [["files"]],
    "Q2": [["create"]] + [[f"edit:{v:02d}"] for v in range(1, TEXT_EDITS + 1)],
    "Q3": [["create"]] + [[f"edit:{v:02d}"] for v in range(1, TEXT_EDITS + 1)],
    "Q4": [["create"]] + [[f"edit:{v:02d}"] for v in range(1, TEXT_EDITS + 1)],
    "Q5": [["base"], ["insert-start"], ["insert-middle"], ["overwrite-middle"], ["append"], ["delete-first"]],
}
WRITE_METHOD = {
    "Q1": "new path",
    "Q2": "in-place rewrite (same inode, O_WRONLY|O_TRUNC)",
    "Q3": "write temp file then rename over the old path",
    "Q4": "new path per version, old path unlinked",
    "Q5": "in-place rewrite (same inode, O_WRONLY|O_TRUNC)",
}

# ---------------------------------------------------------------- streams


def shake(label, n):
    return hashlib.shake_256(f"{WORKLOAD_VERSION}|{label}".encode()).digest(n)


class Draws:
    """Deterministic integers from a SHAKE stream (rejection sampling)."""

    def __init__(self, label):
        self.label, self.block, self.buffer, self.pos = label, 0, b"", 0

    def u32(self):
        if self.pos + 4 > len(self.buffer):
            self.buffer = shake(f"{self.label}#{self.block}", 1 << 16)
            self.block += 1
            self.pos = 0
        value = int.from_bytes(self.buffer[self.pos:self.pos + 4], "little")
        self.pos += 4
        return value

    def below(self, n):
        limit = (1 << 32) - ((1 << 32) % n)
        while True:
            value = self.u32()
            if value < limit:
                return value % n

    def between(self, low, high):
        return low + self.below(high - low + 1)


# ------------------------------------------------------------- word model

_SYLLABLES = [c + v for c in "bcdfghjklmnprstvwz" for v in ("a", "e", "i", "o", "u", "ai", "ou")]


def _vocabulary():
    draws = Draws("vocabulary")
    words = []
    seen = set()
    while len(words) < 4096:
        word = "".join(_SYLLABLES[draws.below(len(_SYLLABLES))] for _ in range(1 + draws.below(4)))
        if word not in seen:
            seen.add(word)
            words.append(word.encode())
    weights = [1.0 / (rank + 1) for rank in range(len(words))]
    scale = 65536 / sum(weights)
    table = []
    for rank, weight in enumerate(weights):
        table.extend([rank] * max(1, round(weight * scale)))
    table = (table + list(range(len(words))))[:65536]
    return words, table


WORDS, TABLE = _vocabulary()


class Text:
    """Synthetic lines: 5–14 words, space separated, ending in ".\\n"."""

    def __init__(self, label):
        self.label, self.block = label, 0
        self.indices, self.pos = array.array("H"), 0

    def _next(self):
        if self.pos >= len(self.indices):
            raw = shake(f"{self.label}#text{self.block}", 1 << 17)
            self.block += 1
            self.indices = array.array("H")
            self.indices.frombytes(raw)
            if sys.byteorder != "little":
                self.indices.byteswap()
            self.pos = 0
        value = self.indices[self.pos]
        self.pos += 1
        return value

    def line(self):
        count = 5 + self._next() % 10
        return b" ".join(WORDS[TABLE[self._next()]] for _ in range(count)) + b".\n"

    def lines_to(self, size):
        parts, total = [], 0
        while total < size:
            line = self.line()
            parts.append(line)
            total += len(line)
        return b"".join(parts)[:size]


# ------------------------------------------------------------ writing


def mkdirs(path):
    if path and not os.path.isdir(path):
        mkdirs(os.path.dirname(path))
        os.mkdir(path)
        os.chmod(path, 0o755)


def _write_all(fd, data):
    view = memoryview(data)
    while view:
        written = os.write(fd, view[: 4 * MiB])
        view = view[written:]


def write_new(path, data):
    mkdirs(os.path.dirname(path))
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.fchmod(fd, 0o644)
        _write_all(fd, data)
    finally:
        os.close(fd)


def write_in_place(path, data):
    before = os.stat(path).st_ino
    fd = os.open(path, os.O_WRONLY | os.O_TRUNC)
    try:
        _write_all(fd, data)
    finally:
        os.close(fd)
    if os.stat(path).st_ino != before:
        raise SystemExit(f"in-place rewrite changed the inode of {path}")


def write_rename(path, data):
    temporary = path + ".tmp"
    write_new(temporary, data)
    os.rename(temporary, path)


def read(path):
    with open(path, "rb") as stream:
        return stream.read()


# --------------------------------------------------------------- cases


def q1(part):
    if part != "files":
        raise SystemExit(f"unknown Q1 part {part}")
    sizes = Draws("Q1/sizes")
    for index in range(Q1_FILES):
        size = sizes.below(4097)  # 0..4096 B
        write_new(f"d{index // Q1_PER_DIR:02d}/f{index:04d}.bin", shake(f"Q1/file{index}", size))


TEXT_PATHS = [(f"d{i // 10:02d}", f"f{i:03d}") for i in range(TEXT_FILES)]


def text_initial(index):
    draws = Draws(f"text/size{index}")
    return Text(f"text/body{index}").lines_to(draws.between(16 * 1024, 64 * 1024))


def text_edit(data, index, version):
    """Replace 1% of the complete lines (at least one) with new synthetic lines."""
    lines = data.split(b"\n")  # the last element is the partial line (or b"")
    complete = len(lines) - 1
    draws = Draws(f"text/edit{index}/v{version}")
    text = Text(f"text/new{index}/v{version}")
    count = max(1, round(complete * 0.01))
    chosen = set()
    while len(chosen) < count:
        chosen.add(draws.below(complete))
    for position in sorted(chosen):
        lines[position] = text.line()[:-1]
    return b"\n".join(lines)


def text_case(case, part):
    """Q2/Q3/Q4 write the identical content sequence; only the method differs."""
    for index, (directory, name) in enumerate(TEXT_PATHS):
        if part == "create":
            path = f"{directory}/{name}.v00.txt" if case == "Q4" else f"{directory}/{name}.txt"
            write_new(path, text_initial(index))
            continue
        version = int(part.split(":")[1])
        if case == "Q4":
            old = f"{directory}/{name}.v{version - 1:02d}.txt"
            write_new(f"{directory}/{name}.v{version:02d}.txt", text_edit(read(old), index, version))
            os.unlink(old)
        else:
            path = f"{directory}/{name}.txt"
            data = text_edit(read(path), index, version)
            (write_in_place if case == "Q2" else write_rename)(path, data)


def q5(part):
    path = "large.bin"
    if part == "base":
        write_new(path, shake("Q5/base", LARGE_BYTES))
        return
    data = read(path)
    middle = len(data) // 2
    if part == "insert-start":
        data = shake("Q5/insert-start", 1) + data
    elif part == "insert-middle":
        data = data[:middle] + shake("Q5/insert-middle", 1) + data[middle:]
    elif part == "overwrite-middle":
        data = data[:middle] + shake("Q5/overwrite-middle", 4096) + data[middle + 4096:]
    elif part == "append":
        data = data + shake("Q5/append", MiB)
    elif part == "delete-first":
        data = data[1:]
    else:
        raise SystemExit(f"unknown Q5 part {part}")
    write_in_place(path, data)


def step(case, part):
    if case == "Q1":
        q1(part)
    elif case in ("Q2", "Q3", "Q4"):
        text_case(case, part)
    elif case == "Q5":
        q5(part)
    else:
        raise SystemExit(f"unknown case {case}")


# ------------------------------------------------------------- manifest


def manifest(root="."):
    """Same canonical lines as shared/src/references.py manifest_lines."""
    entries = []
    for directory, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(dirnames + filenames):
            path = os.path.join(directory, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            info = os.lstat(path)
            mode = stat.S_IMODE(info.st_mode)
            if stat.S_ISLNK(info.st_mode):
                target = os.readlink(path).encode()
                entries.append((rel, "l", mode, len(target), hashlib.sha256(target).hexdigest()))
            elif stat.S_ISDIR(info.st_mode):
                entries.append((rel, "d", mode, 0, "-"))
            elif stat.S_ISREG(info.st_mode):
                digest = hashlib.sha256()
                with open(path, "rb") as stream:
                    for block in iter(lambda: stream.read(MiB), b""):
                        digest.update(block)
                entries.append((rel, "f", mode, info.st_size, digest.hexdigest()))
            else:
                entries.append((rel, "?", mode, 0, "-"))
    entries.sort()
    text = "".join(f"{k} {m:04o} {s} {h} {p}\n" for p, k, m, s, h in entries)
    return {
        "entries": len(entries),
        "files": sum(1 for e in entries if e[1] == "f"),
        "bytes": sum(e[3] for e in entries if e[1] == "f"),
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def namespace(paths, root="."):
    """Q6 head check (the base tree is 65 MB; hashing it all per head is too slow
    for the quick budget): every path's kind, mode and size (symlinks: target
    digest), in model.py's manifest order, plus the SHA-256 of each path in
    ``paths`` (the paths the edit model touched on that Branch)."""
    root = os.path.normpath(root)
    lines, empty_dirs, other = [], 0, 0
    for directory, dirnames, filenames in os.walk(root):
        if directory != root and not dirnames and not filenames:
            empty_dirs += 1
        for name in list(dirnames):
            if os.path.islink(os.path.join(directory, name)):
                filenames.append(name)
        dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(directory, d))]
        for name in filenames:
            full = os.path.join(directory, name)
            rel = os.path.relpath(full, root)
            info = os.lstat(full)
            if stat.S_ISLNK(info.st_mode):
                target = os.readlink(full).encode()
                lines.append((rel, f"{rel}\tlink\t0\t{len(target)}\t{hashlib.sha256(target).hexdigest()}\n"))
            elif stat.S_ISREG(info.st_mode):
                lines.append((rel, f"{rel}\tfile\t{stat.S_IMODE(info.st_mode):o}\t{info.st_size}\n"))
            else:
                other += 1
    lines.sort(key=lambda item: item[0].encode())
    touched = hashlib.sha256()
    for path in sorted(set(paths), key=str.encode):
        full = os.path.join(root, path)
        if os.path.isfile(full) and not os.path.islink(full):
            touched.update(f"{path}\t{_sha_file(full)}\n".encode())
        else:
            touched.update(f"{path}\t-\n".encode())
    return {
        "entries": len(lines),
        "bytes": sum(int(text.split("\t")[3]) for _, text in lines),
        "empty_dirs": empty_dirs,
        "other": other,
        "namespace_sha256": hashlib.sha256("".join(t for _, t in lines).encode()).hexdigest(),
        "touched": len(set(paths)),
        "touched_sha256": touched.hexdigest(),
    }


def _sha_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(MiB), b""):
            digest.update(block)
    return digest.hexdigest()


def encode_paths(paths):
    return base64.b64encode(zlib.compress(json.dumps(sorted(set(paths))).encode(), 9)).decode()


def decode_paths(text):
    return json.loads(zlib.decompress(base64.b64decode(text)))


def oracle(case, directory):
    """Run every part of ``case`` in an empty ``directory``; return its manifest."""
    os.makedirs(directory, exist_ok=True)
    if os.listdir(directory):
        raise SystemExit(f"{directory} is not empty")
    here = os.getcwd()
    os.chdir(directory)
    try:
        for parts in PLAN[case]:
            for part in parts:
                step(case, part)
        return manifest(".")
    finally:
        os.chdir(here)


def main(argv):
    if argv[:1] == ["step"] and len(argv) == 3:
        os.umask(0o022)
        step(argv[1], argv[2])
    elif argv[:1] == ["oracle"] and len(argv) == 3:
        os.umask(0o022)
        print(json.dumps(oracle(argv[1], argv[2]), sort_keys=True))
    elif argv[:1] == ["namespace"] and len(argv) == 2:
        print(json.dumps(namespace(decode_paths(argv[1])), sort_keys=True))
    elif argv[:1] == ["manifest"] and len(argv) <= 2:
        print(json.dumps(manifest(argv[1] if len(argv) == 2 else "."), sort_keys=True))
    elif argv == ["plan"]:
        print(json.dumps({"version": WORKLOAD_VERSION, "plan": PLAN, "write_method": WRITE_METHOD}, sort_keys=True))
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
