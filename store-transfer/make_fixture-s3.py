#!/usr/bin/env python3
"""Deterministic LP08-S3 fixture: ~64 MiB of seed-derived bytes plus the LP08-S1
shape (text, empty file, 0755 script, symlinks, deep path, UTF-8 name).

    python3 make_fixture.py /abs/dir [seed]

Every byte is derived from sha256(seed||path), so the fixture is reproducible
and incompressible enough to need several 8 MiB chunks.
"""
import hashlib
import os
import sys
from pathlib import Path

SEED = 0x4C503038


def stream(seed, path, size):
    out = bytearray()
    counter = 0
    while len(out) < size:
        out += hashlib.sha256(b"%d:%s:%d" % (seed, path.encode(), counter)).digest()
        counter += 1
    return bytes(out[:size])


def main():
    root = Path(sys.argv[1])
    seed = int(sys.argv[2], 0) if len(sys.argv) > 2 else SEED
    root.mkdir(parents=True, exist_ok=True)

    def put(rel, data, mode=0o644):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(mode)

    put("src/main.rs", b"fn main() {\n    println!(\"lp08 s3\");\n}\n")
    put("src/lib.rs", b"pub fn answer() -> u32 { 42 }\n")
    put("docs/readme.md", b"# lp08 s3 fixture\n\npush and pull a sqlite Store.\n")
    put("docs/empty.txt", b"")
    put("a/b/c/d/e/f.txt", b"deep\n")
    put("中文 空格.txt", "用空格的名字\n".encode())
    put("tools/run.sh", b"#!/bin/sh\necho run\n", 0o755)
    put("data/big.bin", stream(seed, "data/big.bin", 64 << 20))
    link = root / "link"
    link.mkdir(parents=True, exist_ok=True)
    current = link / "current"
    if not current.is_symlink():
        os.symlink("../src/main.rs", current)
    print(root, sum(1 for _ in root.rglob("*")), "entries",
          (root / "data/big.bin").stat().st_size, "bytes in data/big.bin")


if __name__ == "__main__":
    main()
