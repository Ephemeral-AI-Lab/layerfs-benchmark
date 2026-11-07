"""Deterministic synthetic export fixtures (no user data).

    python3 fixture.py <dest> small|large    writes the fixture, prints its manifest hash
    python3 fixture.py --manifest <folder>   prints the manifest hash of a folder

small: 10,000 files of random bytes (512 B to 16 KiB, log-uniform) in 10 x 10
folders, 50 symlinks (relative, absolute, dangling), 20 empty folders, every
50th file 0755. large: one 256 MiB random file and a README. Content is
incompressible and distinct per file, so chunk dedupe saves nothing.
"""

import hashlib
import json
import math
import os
import random
import stat
import sys
from pathlib import Path

MTIME = 1_700_000_000_123_456_789


def small(root: Path) -> None:
    rng = random.Random(53)
    n = 0
    for a in range(10):
        for b in range(10):
            folder = root / f"pkg{a:02d}" / f"mod{b:02d}"
            folder.mkdir(parents=True)
            for _ in range(100):
                size = int(math.exp(rng.uniform(math.log(512), math.log(16384))))
                path = folder / f"f{n:05d}.bin"
                path.write_bytes(rng.randbytes(size))
                if n % 50 == 0:
                    path.chmod(0o755)
                n += 1
    for i in range(20):
        (root / "empty" / f"e{i:02d}").mkdir(parents=True)
    links = root / "links"
    links.mkdir()
    for i in range(50):
        target = (
            f"../pkg{i % 10:02d}/mod00/f{i * 100:05d}.bin" if i % 3 == 0
            else "/etc/hosts" if i % 3 == 1
            else f"missing-{i}"
        )
        os.symlink(target, links / f"l{i:02d}")


def large(root: Path) -> None:
    rng = random.Random(530)
    root.mkdir(parents=True, exist_ok=True)
    (root / "README").write_text("one 256 MiB random file\n")
    with open(root / "blob.bin", "wb") as out:
        for _ in range(256):
            out.write(rng.randbytes(1 << 20))


def manifest(root: Path) -> str:
    """sha256 over sorted (path, kind, mode, size, content sha256 or link target, mtime_ns)."""
    rows = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in sorted(dirnames + filenames):
            p = Path(dirpath) / name
            st = p.lstat()
            rel = str(p.relative_to(root))
            if stat.S_ISLNK(st.st_mode):
                rows.append([rel, "l", 0, 0, os.readlink(p), 0])
            elif stat.S_ISDIR(st.st_mode):
                rows.append([rel, "d", st.st_mode & 0o7777, 0, "", 0])
            else:
                h = hashlib.sha256(p.read_bytes()).hexdigest()
                rows.append([rel, "f", st.st_mode & 0o7777, st.st_size, h, st.st_mtime_ns])
    rows.sort()
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def settle(root: Path) -> None:
    """Fixed mtimes on files, then folders bottom-up, so manifests compare."""
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        for name in filenames:
            p = Path(dirpath) / name
            if not p.is_symlink():
                os.utime(p, ns=(MTIME, MTIME))


if __name__ == "__main__":
    if sys.argv[1] == "--manifest":
        print(manifest(Path(sys.argv[2])))
        sys.exit(0)
    dest, kind = Path(sys.argv[1]), sys.argv[2]
    if dest.exists():
        sys.exit(f"{dest} exists")
    dest.mkdir(parents=True)
    {"small": small, "large": large}[kind](dest)
    settle(dest)
    print(manifest(dest))
