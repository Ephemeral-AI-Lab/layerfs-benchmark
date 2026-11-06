#!/usr/bin/env python3
"""Materialize selected seed states as plain directories, inside the suite image.

    docker run --rm --network none --user 501:501 -v <suite src>:/src:ro \
      -v <out>:/out <suite image> python3 /src/materialize.py /out D10 D03

Walks the union of the cases' selections in order with the image's own
apply.py (the workload's write rule) in one scratch tree, and copies each
selected state to OUT/states/<k>/. The final states are checked against their
pinned corpus oracles with verify.py. The directories feed the host-side
references (whole-file unique, tar|zstd -3, CDC oracle); they are not product
input and are deleted after the references are pinned.
"""

import json
import os
import shutil
import subprocess
import sys

import cases

TOOL = cases.TOOL_ROOT


def main(argv):
    out, case_ids = argv[1], argv[2:]
    union = sorted({k for case_id in case_ids for k in cases.SELECTIONS[case_id]})
    finals = {cases.SELECTIONS[case_id][-1] for case_id in case_ids}
    scratch = os.path.join(out, "scratch")
    os.makedirs(scratch)
    os.makedirs(os.path.join(out, "states"), exist_ok=True)
    previous = 0
    for k in union:
        subprocess.run(["python3", f"{TOOL}/apply.py", str(previous), str(k)], cwd=scratch, check=True,
                       stdout=subprocess.DEVNULL, timeout=110)
        shutil.copytree(scratch, os.path.join(out, "states", str(k)), symlinks=True)
        previous = k
    checks = {}
    for k in sorted(finals):
        done = subprocess.run(["python3", f"{TOOL}/verify.py", str(k)], cwd=os.path.join(out, "states", str(k)),
                              capture_output=True, text=True, timeout=110)
        checks[k] = json.loads(done.stdout)
        if done.returncode:
            raise SystemExit(f"materialize.py: state {k} fails its oracle: {checks[k]}")
    shutil.rmtree(scratch)
    print(json.dumps({"states": union, "verified": checks}))


if __name__ == "__main__":
    main(sys.argv)
