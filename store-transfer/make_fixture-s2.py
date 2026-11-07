#!/usr/bin/env python3
"""The #11 fixtures: a 256 MiB and a 512 MiB Store's worth of input, from a fixed seed.

Content is a blake2b counter stream keyed by the file's path, so it is
incompressible (a Store keeps its content near the input's size: the smoke
run measured 17,186,816 B for 16 MiB of input) and recomputable from the
seed alone. `python3 make_fixture.py <root>` writes `<root>/p1`, `<root>/p2`
under `s256/` and `s512/`, plus `fixtures.json` with per-file sha256.
"""
import hashlib
import json
import os
import stat
import sys
import time
from pathlib import Path

SEED = b"\x4c\x50\x38\x53"  # "LP8S"
BLOCK = 32
CHUNK = 8 << 20


def stream(name: str, size: int) -> bytes:
    key = hashlib.sha256(SEED + name.encode()).digest()
    out = bytearray()
    counter = 0
    while len(out) < size:
        out += hashlib.blake2b(key + counter.to_bytes(8, "little"), digest_size=BLOCK).digest()
        counter += 1
    return bytes(out[:size])


def write(path: Path, data: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    os.chmod(path, mode)


def project(root: Path, blobs: int) -> None:
    for n in range(blobs):
        name = f"data/blob-{n:02d}.bin"
        write(root / name, stream(name, CHUNK))


def textual(root: Path) -> None:
    """The metadata a manifest check needs: modes, a symlink, a UTF-8 name, a deep path."""
    write(root / "README.md", b"# lp08-s2 fixture\n\nfixed seed, incompressible blobs\n")
    write(root / "src/main.rs", b"fn main() {\n    println!(\"lp08-s2\");\n}\n")
    write(root / "tools/run.sh", b"#!/bin/sh\necho lp08-s2\n", 0o755)
    write(root / "a/b/c/d/e/f.txt", b"deep\n")
    write(root / "\u4e2d\u6587 \u7a7a\u683c.txt", "utf-8 name with a space\n".encode())
    link = root / "link" / "current"
    link.parent.mkdir(parents=True, exist_ok=True)
    if not link.exists():
        link.symlink_to("../src/main.rs")


def manifest(root: Path) -> dict:
    rows = {}
    for path in sorted(root.rglob("*")):
        rel = str(path.relative_to(root))
        if path.is_symlink():
            rows[rel] = {"kind": "link", "target": os.readlink(path)}
        elif path.is_dir():
            rows[rel] = {"kind": "dir"}
        else:
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(block)
            rows[rel] = {"kind": "file", "mode": oct(stat.S_IMODE(path.stat().st_mode)),
                         "bytes": path.stat().st_size, "sha256": digest.hexdigest()}
    return rows


def main() -> int:
    base = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/lp08-s2/fixture")
    jobs = [
        ("s256", 32),   # 256 MiB of data + text -> a Store of about 259 MiB
        ("s512", 64),   # 512 MiB of data -> a Store of about 518 MiB
        ("quiet", 2),   # 16 MiB: the #12 quiet and small-Store case
    ]
    out = {"seed": SEED.hex(), "block": BLOCK, "chunk": CHUNK, "fixtures": {}}
    for name, blobs in jobs:
        root = base / name
        started = time.time()
        project(root / "p1", blobs)
        textual(root / "p1")
        (root / "p2/docs").mkdir(parents=True, exist_ok=True)
        write(root / "p2/docs/readme.md", b"# small project\n")
        write(root / "p2/notes.txt", b"notes\n")
        total = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
        out["fixtures"][name] = {
            "root": str(root),
            "bytes": total,
            "seconds": round(time.time() - started, 2),
            "files": manifest(root),
        }
        print(name, total, "bytes", round(time.time() - started, 2), "s")
    (base / "fixtures.json").write_text(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
