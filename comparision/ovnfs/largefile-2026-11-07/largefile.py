#!/usr/bin/env python3
"""Large-file, small-edit workload `fsh-ovnfs-largefile-v0` (stdlib only).

Each case is one incompressible file (seeded pseudo-random bytes, so compression
cannot hide whole-file copies) and a sequence of small edits:

    L10   10 MiB,  20 commits, overwrite 100 B in place at a seeded offset
    L100  100 MiB, 10 commits, overwrite 100 B in place at a seeded offset
    I10   10 MiB,  10 commits, insert 100 B at a seeded offset (shifts the rest)
    A5    5 MiB,   20 commits, append 16 KiB

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
    "I10": {"size": 10 * MiB, "commits": 10, "op": "insert", "bytes": 100},
    "A5": {"size": 5 * MiB, "commits": 20, "op": "append", "bytes": 16 * 1024},
}
VERSION = "fsh-ovnfs-largefile-v0"


def base_bytes(case):
    return random.Random(f"{VERSION}/{case}/base").randbytes(CASES[case]["size"])


def edit(case, k, size):
    """(offset, payload) for step k on a file of `size` bytes."""
    c = CASES[case]
    r = random.Random(f"{VERSION}/{case}/step/{k}")
    payload = r.randbytes(c["bytes"])
    if c["op"] == "append":
        return size, payload
    return r.randrange(size - c["bytes"]), payload


def apply_to_file(case, k, path):
    op = CASES[case]["op"]
    size = os.path.getsize(path)
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
    if len(argv) == 3 and argv[0] == "gen" and argv[1] in CASES:
        path = os.path.join(argv[2], f"{argv[1]}.bin")
        with open(path, "wb") as f:
            f.write(base_bytes(argv[1]))
        print(json.dumps({"case": argv[1], "path": path, "size": os.path.getsize(path)}))
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
