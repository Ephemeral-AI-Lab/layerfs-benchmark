#!/usr/bin/env python3
"""fs-storage-micro generator and final-state verifier (stdlib only).

Runs inside the LayerFS Sandbox (cwd = Workspace root) and, for references,
in a throwaway container of the same image. Every byte comes from SHAKE-256
streams keyed by WORKLOAD_VERSION and a label, so output is identical on any
Python 3. Generated text is SYNTHETIC (a seeded word model), not real prose.

  gen.py step <case> <part>     apply one part of a case in the cwd
  gen.py emit <case> <outdir>   write the tree after each Commit to outdir/sNN
  gen.py manifest [root]        canonical final-state manifest digest (JSON)
  gen.py plan                   the per-case Commit plan (JSON)
"""

import array
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import sys

WORKLOAD_VERSION = "fs-storage-micro-v1"
MiB = 1 << 20

# Each case is a list of Commits; each Commit lists the parts run (one Exec
# each) before it. Write methods are fixed per case.
PLAN = {
    "M01": [["files"]],
    "M02": [["tree"], [f"copy:{k:02d}" for k in range(1, 11)]],
    "M03": [["create"]] + [[f"edit:{v:02d}"] for v in range(1, 21)],
    "M04": [["create"]] + [[f"edit:{v:02d}"] for v in range(1, 21)],
    "M05": [["create"]] + [[f"edit:{v:02d}"] for v in range(1, 21)],
    "M06": [["base"], ["insert-start"], ["insert-middle"], ["overwrite-middle"], ["append"], ["delete-first"]],
    "M07": [["random"], ["zeros"], ["text"]],
    "M08": [["create"]] + [[f"update:{v:02d}"] for v in range(1, 11)] + [["vacuum"]],
}
WRITE_METHOD = {
    "M01": "new path",
    "M02": "new path (copies read base/ and write new files)",
    "M03": "in-place rewrite (same inode, O_WRONLY|O_TRUNC)",
    "M04": "write temp file then rename over the old path",
    "M05": "new path per version, old path unlinked",
    "M06": "in-place rewrite (same inode, O_WRONLY|O_TRUNC)",
    "M07": "new path",
    "M08": "in-place (SQLite page writes, rollback journal)",
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
    # Zipf-like table: rank r gets weight ~ 1/(r+1); 65,536 slots.
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
        """Whole lines, then cut to exactly ``size`` bytes."""
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


def _write_all(fd, data):
    view = memoryview(data)
    while view:
        written = os.write(fd, view[: 4 * MiB])
        view = view[written:]


def read(path):
    with open(path, "rb") as stream:
        return stream.read()


# --------------------------------------------------------------- cases


def m01(part):
    sizes = Draws("M01/sizes")
    for index in range(10000):
        size = sizes.below(4097)  # 0..4096 B
        write_new(f"d{index // 100:02d}/f{index:04d}.bin", shake(f"M01/file{index}", size))


def m02_sizes():
    draws = Draws("M02/sizes")
    raw = [draws.between(1, 1000) for _ in range(200)]
    total = 50_000_000
    sizes = [r * total // sum(raw) for r in raw]
    sizes[-1] += total - sum(sizes)
    return sizes


def m02(part):
    sizes = m02_sizes()
    names = [f"d{i // 20:02d}/f{i:03d}.{'txt' if i % 2 == 0 else 'bin'}" for i in range(200)]
    if part == "tree":
        for index, (name, size) in enumerate(zip(names, sizes)):
            data = Text(f"M02/text{index}").lines_to(size) if index % 2 == 0 else shake(f"M02/bin{index}", size)
            write_new(f"base/{name}", data)
    else:
        copy = part.split(":")[1]
        for name in names:
            write_new(f"copy{copy}/{name}", read(f"base/{name}"))


TEXT100 = [(f"d{i // 10:02d}", f"f{i:03d}") for i in range(100)]


def text100_initial(index):
    draws = Draws(f"text100/size{index}")
    return Text(f"text100/body{index}").lines_to(draws.between(16 * 1024, 64 * 1024))


def text100_edit(data, index, version):
    """Replace 1% of the complete lines (at least one) with new synthetic lines."""
    lines = data.split(b"\n")  # the last element is the partial line (or b"")
    complete = len(lines) - 1
    draws = Draws(f"text100/edit{index}/v{version}")
    text = Text(f"text100/new{index}/v{version}")
    count = max(1, round(complete * 0.01))
    chosen = set()
    while len(chosen) < count:
        chosen.add(draws.below(complete))
    for position in sorted(chosen):
        lines[position] = text.line()[:-1]
    return b"\n".join(lines)


def text100(case, part):
    for index, (directory, name) in enumerate(TEXT100):
        if part == "create":
            path = f"{directory}/{name}.v00.txt" if case == "M05" else f"{directory}/{name}.txt"
            write_new(path, text100_initial(index))
            continue
        version = int(part.split(":")[1])
        if case == "M05":
            old = f"{directory}/{name}.v{version - 1:02d}.txt"
            write_new(f"{directory}/{name}.v{version:02d}.txt", text100_edit(read(old), index, version))
            os.unlink(old)
        else:
            path = f"{directory}/{name}.txt"
            data = text100_edit(read(path), index, version)
            (write_in_place if case == "M03" else write_rename)(path, data)


def m06(part):
    path = "large.bin"
    if part == "base":
        write_new(path, shake("M06/base", 64 * MiB))
        return
    data = read(path)
    middle = len(data) // 2
    if part == "insert-start":
        data = shake("M06/insert-start", 1) + data
    elif part == "insert-middle":
        data = data[:middle] + shake("M06/insert-middle", 1) + data[middle:]
    elif part == "overwrite-middle":
        data = data[:middle] + shake("M06/overwrite-middle", 4096) + data[middle + 4096:]
    elif part == "append":
        data = data + shake("M06/append", MiB)
    elif part == "delete-first":
        data = data[1:]
    else:
        raise SystemExit(f"unknown M06 part {part}")
    write_in_place(path, data)


def m07(part):
    if part == "random":
        write_new("random.bin", shake("M07/random", 64 * MiB))
    elif part == "zeros":
        write_new("zeros.bin", bytes(64 * MiB))
    elif part == "text":
        write_new("text.txt", Text("M07/text").lines_to(64 * MiB))


M08_ROWS = 147_000
M08_VALUE = 200


def m08(part):
    path = "data.db"
    if part == "create":
        connection = sqlite3.connect(path, isolation_level=None)
        connection.execute("PRAGMA page_size=4096")
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, k INTEGER NOT NULL, v TEXT NOT NULL)")
        draws, text = Draws("M08/rows"), Text("M08/rows")
        connection.execute("BEGIN")
        connection.executemany(
            "INSERT INTO t (id, k, v) VALUES (?, ?, ?)",
            ((i, draws.u32(), text.lines_to(M08_VALUE).decode()) for i in range(1, M08_ROWS + 1)),
        )
        connection.execute("COMMIT")
        connection.close()
        os.chmod(path, 0o644)
        return
    connection = sqlite3.connect(path, isolation_level=None)
    if connection.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
        raise SystemExit("unexpected journal mode")
    if part == "vacuum":
        connection.execute("VACUUM")
    else:
        version = int(part.split(":")[1])
        draws, text = Draws(f"M08/update{version}"), Text(f"M08/update{version}")
        chosen = set()
        while len(chosen) < M08_ROWS // 100:
            chosen.add(1 + draws.below(M08_ROWS))
        connection.execute("BEGIN")
        for row in sorted(chosen):
            value = text.lines_to(M08_VALUE).decode()
            connection.execute("UPDATE t SET v = ? WHERE id = ?", (value, row))
        connection.execute("COMMIT")
    connection.close()
    for leftover in (path + "-journal", path + "-wal"):
        if os.path.exists(leftover):
            raise SystemExit(f"{leftover} left behind")


def step(case, part):
    if case == "M01":
        m01(part)
    elif case == "M02":
        m02(part)
    elif case in ("M03", "M04", "M05"):
        text100(case, part)
    elif case == "M06":
        m06(part)
    elif case == "M07":
        m07(part)
    elif case == "M08":
        m08(part)
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


def emit(case, out):
    work = os.path.join(out, "work")
    os.makedirs(work)
    here = os.getcwd()
    for number, parts in enumerate(PLAN[case], start=1):
        os.chdir(work)
        for part in parts:
            step(case, part)
        os.chdir(here)
        shutil.copytree(work, os.path.join(out, f"s{number:02d}"), symlinks=True)
    shutil.rmtree(work)


def main(argv):
    if argv[:1] == ["step"] and len(argv) == 3:
        os.umask(0o022)
        step(argv[1], argv[2])
    elif argv[:1] == ["emit"] and len(argv) == 3:
        os.umask(0o022)
        emit(argv[1], argv[2])
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
