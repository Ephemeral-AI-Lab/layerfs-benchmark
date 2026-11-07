#!/usr/bin/env python3
"""Large-file, small-edit workload `fsh-ovnfs-largefile-v0` (stdlib only).

Each case is one incompressible file (seeded pseudo-random bytes, so compression
cannot hide whole-file copies) and a sequence of small edits:

    L10   10 MiB,  20 commits, overwrite 100 B in place at a seeded offset
    L100  100 MiB, 10 commits, overwrite 100 B in place at a seeded offset
    I10   10 MiB,  10 commits, insert 100 B at a seeded offset (shifts the rest)
    A5    5 MiB,   20 commits, append 16 KiB
    ADD500  500 MiB (the L500 file), 1 commit, append 500 MiB of new bytes
    DEL500  1000 MiB (ADD500's result), 1 commit, cut the last 500 MiB (back to L500)
    NEW500  tree of keep.bin (1 MiB), 1 commit, create a brand-new 500 MiB big.bin
    RM500   tree of keep.bin and an existing 500 MiB big.bin, 1 commit, remove big.bin

NEW500 and RM500 are tree cases: `gen` writes the starting tree into DIR, `apply`
works in DIR, and `expect` gives every file's size and sha256 per step.

    largefile.py gen CASE DIR       write the starting file DIR/<case>.bin
    largefile.py apply CASE K DIR   apply edit K (1-based) to DIR/<case>.bin
    largefile.py expect CASE        print the sha256 after every step, as JSON
    largefile.py sha DIR            print {name: sha256} for every file in DIR

The same commands run unchanged inside an ovnfs checkout or a LayerFS Workspace.
"""

import hashlib
import json
import os
import random
import sys

MiB = 1 << 20
CASES = {
    "L10": {"size": 10 * MiB, "commits": 20, "op": "overwrite", "bytes": 100},
    "L100": {"size": 100 * MiB, "commits": 10, "op": "overwrite", "bytes": 100},
    "L500": {"size": 500 * MiB, "commits": 5, "op": "overwrite", "bytes": 100},
    "I10": {"size": 10 * MiB, "commits": 10, "op": "insert", "bytes": 100},
    "A5": {"size": 5 * MiB, "commits": 20, "op": "append", "bytes": 16 * 1024},
    "ADD500": {"size": 500 * MiB, "commits": 1, "op": "grow", "bytes": 500 * MiB},
    "DEL500": {"size": 1000 * MiB, "commits": 1, "op": "shrink", "bytes": 500 * MiB},
    "NEW500": {"size": MiB, "commits": 1, "op": "create", "bytes": 500 * MiB, "tree": True},
    "RM500": {"size": 501 * MiB, "commits": 1, "op": "delete", "bytes": 500 * MiB, "tree": True},
}
BIG, KEEP = "big.bin", "keep.bin"
GROWTH = 500 * MiB
VERSION = "fsh-ovnfs-largefile-v0"


def base_bytes(case):
    return random.Random(f"{VERSION}/{case}/base").randbytes(CASES[case]["size"])


def growth_blocks():
    """The 500 MiB ADD500 appends, in seeded 1 MiB blocks: Python 3.11 (the
    containers' Python) cannot make 500 MiB in one randbytes call."""
    r = random.Random(f"{VERSION}/grow500")
    for _ in range(GROWTH // MiB):
        yield r.randbytes(MiB)


def base_blocks(case):
    """The starting file: ADD500 starts from the L500 file, DEL500 from ADD500's result."""
    if case in ("ADD500", "DEL500"):
        yield base_bytes("L500")
        if case == "DEL500":
            yield from growth_blocks()
    else:
        yield base_bytes(case)


def edit(case, k, size):
    """(offset, payload) for step k on a file of `size` bytes."""
    c = CASES[case]
    r = random.Random(f"{VERSION}/{case}/step/{k}")
    payload = r.randbytes(c["bytes"])
    if c["op"] == "append":
        return size, payload
    return r.randrange(size - c["bytes"]), payload


def keep_bytes():
    return random.Random(f"{VERSION}/keep").randbytes(MiB)


def base_tree(case):
    """{name: block iterator} of a tree case's starting tree."""
    tree = {KEEP: iter([keep_bytes()])}
    if case == "RM500":
        tree[BIG] = growth_blocks()
    return tree


def digest(blocks):
    h, n = hashlib.sha256(), 0
    for block in blocks:
        h.update(block)
        n += len(block)
    return {"size": n, "sha256": h.hexdigest()}


def expect_tree(case):
    keep = digest([keep_bytes()])
    small = {KEEP: keep}
    large = {KEEP: keep, BIG: digest(growth_blocks())}
    first, last = (small, large) if case == "NEW500" else (large, small)
    return [{"step": 0, "files": first}, {"step": 1, "files": last}]


def apply_to_tree(case, k, root):
    op = CASES[case]["op"]
    path = os.path.join(root, BIG)
    if op == "create":
        with open(path, "xb") as f:
            for block in growth_blocks():
                f.write(block)
    else:
        os.remove(path)
    return {"case": case, "step": k, "op": op, "path": BIG, "bytes": GROWTH}


def apply_to_file(case, k, path):
    op = CASES[case]["op"]
    size = os.path.getsize(path)
    if op == "grow":
        with open(path, "ab") as f:
            for block in growth_blocks():
                f.write(block)
        return {"case": case, "step": k, "op": op, "offset": size, "bytes": GROWTH}
    if op == "shrink":
        os.truncate(path, size - GROWTH)
        return {"case": case, "step": k, "op": op, "offset": size - GROWTH, "bytes": GROWTH}
    offset, payload = edit(case, k, size)
    if op == "overwrite":
        with open(path, "r+b") as f:
            f.seek(offset)
            f.write(payload)
    elif op == "append":
        with open(path, "ab") as f:
            f.write(payload)
    else:  # insert: rewrite the file in place with the shifted tail
        with open(path, "r+b") as f:
            f.seek(offset)
            tail = f.read()
            f.seek(offset)
            f.write(payload + tail)
    return {"case": case, "step": k, "op": op, "offset": offset, "bytes": len(payload)}


def apply_to_bytes(case, k, data):
    op = CASES[case]["op"]
    offset, payload = edit(case, k, len(data))
    if op == "overwrite":
        return data[:offset] + payload + data[offset + len(payload):]
    if op == "append":
        return data + payload
    return data[:offset] + payload + data[offset:]


def expect(case):
    if CASES[case].get("tree"):
        return expect_tree(case)
    if CASES[case]["op"] in ("grow", "shrink"):
        small = hashlib.sha256(base_bytes("L500"))
        large = small.copy()
        for block in growth_blocks():
            large.update(block)
        small = {"size": 500 * MiB, "sha256": small.hexdigest()}
        large = {"size": 1000 * MiB, "sha256": large.hexdigest()}
        first, last = (small, large) if case == "ADD500" else (large, small)
        return [{"step": 0, **first}, {"step": 1, **last}]
    data = base_bytes(case)
    out = [{"step": 0, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}]
    for k in range(1, CASES[case]["commits"] + 1):
        data = apply_to_bytes(case, k, data)
        out.append({"step": k, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return out


def sha_dir(root):
    out = {}
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if os.path.isfile(p) and not os.path.islink(p):
            h = hashlib.sha256()
            with open(p, "rb") as f:
                for block in iter(lambda: f.read(MiB), b""):
                    h.update(block)
            out[name] = {"size": os.path.getsize(p), "sha256": h.hexdigest()}
    return out


def main(argv):
    if len(argv) == 3 and argv[0] == "gen" and CASES.get(argv[1], {}).get("tree"):
        for name, blocks in base_tree(argv[1]).items():
            with open(os.path.join(argv[2], name), "wb") as f:
                for block in blocks:
                    f.write(block)
        print(json.dumps(sha_dir(argv[2])))
    elif len(argv) == 3 and argv[0] == "gen" and argv[1] in CASES:
        path = os.path.join(argv[2], f"{argv[1]}.bin")
        with open(path, "wb") as f:
            for block in base_blocks(argv[1]):
                f.write(block)
        print(json.dumps({"case": argv[1], "path": path, "size": os.path.getsize(path)}))
    elif len(argv) == 4 and argv[0] == "apply" and CASES.get(argv[1], {}).get("tree"):
        print(json.dumps(apply_to_tree(argv[1], int(argv[2]), argv[3])))
    elif len(argv) == 4 and argv[0] == "apply" and argv[1] in CASES:
        print(json.dumps(apply_to_file(argv[1], int(argv[2]), os.path.join(argv[3], f"{argv[1]}.bin"))))
    elif len(argv) == 2 and argv[0] == "expect" and argv[1] in CASES:
        print(json.dumps(expect(argv[1])))
    elif len(argv) == 2 and argv[0] == "sha":
        print(json.dumps(sha_dir(argv[1])))
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
