#!/usr/bin/env python3
"""Build the deterministic #9 fixture: multi-directory project with a multi-chunk
file, a symlink, an executable bit, an empty file and a UTF-8 name with a space."""
import hashlib
import os
import shutil
import sys
from pathlib import Path

SEED = 0x4C503038
BIG = 20 * 1024 * 1024  # > CHUNK (8 MiB) so `send` needs several chunks


def stream(path: str) -> bytes:
    """Deterministic bytes for a fixture path: sha256(seed || path) keyed stream."""
    out = bytearray()
    counter = 0
    while len(out) < BIG:
        out += hashlib.sha256(b"%d:%s:%d" % (SEED, path.encode(), counter)).digest()
        counter += 1
    return bytes(out[:BIG])


def main(root: Path) -> None:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    (root / "src").mkdir()
    (root / "src" / "main.rs").write_text("fn main() {\n    println!(\"lp08\");\n}\n")
    (root / "src" / "lib.rs").write_text("pub const NAME: &str = \"lp08\";\n")
    (root / "docs").mkdir()
    (root / "docs" / "readme.md").write_text("# lp08 fixture\n\nsmall text file\n")
    (root / "docs" / "empty.txt").write_bytes(b"")
    (root / "data").mkdir()
    (root / "data" / "big.bin").write_bytes(stream("data/big.bin"))
    (root / "tools").mkdir()
    (root / "tools" / "run.sh").write_text("#!/bin/sh\necho ran\n")
    os.chmod(root / "tools" / "run.sh", 0o755)
    (root / "link").mkdir()
    os.symlink("../src/main.rs", root / "link" / "current")
    deep = root / "a" / "b" / "c" / "d" / "e"
    deep.mkdir(parents=True)
    (deep / "f.txt").write_text("deep file\n")
    (root / "中文 空格.txt").write_text("utf-8 name with a space\n")
    print(f"fixture at {root}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "fixture/p1"))
