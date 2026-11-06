#!/usr/bin/env python3
"""Checks the Workspace (the current directory) against state K's oracle.

    python3 /opt/fs-storage-dsh/verify.py K

The oracle is the corpus's own per-checkpoint oracle (made from the source
commit, not from the seed repository), pinned by SHA-256 at image build:
{hex path: [git mode, size, sha256]} with directories as ["40755", 0, "-"].
Every path's type, executable bit, size and SHA-256 (of the bytes, or of a
symlink's target) must match, with no path missing or extra. Ported from
dsh-dedup `sandbox/verify.py`. Prints one JSON line; exits 1 on any mismatch.
"""

import hashlib
import json
import os
import stat
import sys

ROOT = "/opt/fs-storage-dsh"


def observe(root=b"."):
    """{relative path bytes: (mode, size, sha256)} of a tree."""
    seen = {}
    prefix = len(root) + 1
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            full = os.path.join(dirpath, name)
            rel = full[prefix:]
            st = os.lstat(full)
            if stat.S_ISLNK(st.st_mode):
                target = os.readlink(full)
                seen[rel] = ("120000", len(target), hashlib.sha256(target).hexdigest())
            elif stat.S_ISDIR(st.st_mode):
                seen[rel] = ("40755", 0, "-")
            elif stat.S_ISREG(st.st_mode):
                digest = hashlib.sha256()
                size = 0
                with open(full, "rb") as stream:
                    for chunk in iter(lambda: stream.read(1 << 20), b""):
                        digest.update(chunk)
                        size += len(chunk)
                mode = "100755" if st.st_mode & 0o100 else "100644"
                seen[rel] = (mode, size, digest.hexdigest())
            else:
                seen[rel] = (f"special:{stat.S_IFMT(st.st_mode):o}", 0, "-")
    return seen


def compare(oracle, seen):
    """Sorted mismatching paths (missing, extra or different)."""
    return [p for p in sorted(set(oracle) | set(seen)) if oracle.get(p) != seen.get(p)]


def load(path):
    with open(path) as stream:
        return {bytes.fromhex(k): tuple(v) for k, v in json.load(stream).items()}


def main(argv):
    if len(argv) != 2:
        raise SystemExit("usage: verify.py K")
    state = int(argv[1])
    oracle = load(f"{ROOT}/seed/oracles/{state}.json")
    seen = observe()
    bad = compare(oracle, seen)
    files = sum(1 for v in seen.values() if v[0] in ("100644", "100755", "120000"))
    print(
        json.dumps(
            {
                "state": state,
                "entries": len(seen),
                "expected": len(oracle),
                "files": files,
                "bytes": sum(v[1] for v in seen.values()),
                "mismatches": len(bad),
                "first": [p.decode("utf-8", "replace") for p in bad[:5]],
            },
            sort_keys=True,
        )
    )
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
