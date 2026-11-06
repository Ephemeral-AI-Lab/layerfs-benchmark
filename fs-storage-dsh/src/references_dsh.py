#!/usr/bin/env python3
"""Pin the D10/D03 references once per workload version (offline, no LayerFS).

    references_dsh.py --refs <dir> --case D10 [--case D03]

Inputs, both produced inside the suite image from the pinned seed:

- `<dir>/states/<k>/`: materialized states (`materialize.py`);
- `<dir>/git-<case>/result.json`: the dsh-dedup Git recipe (`git_reference.py`).

Computes, with `shared/src/references.py` on the host, whole-file unique bytes,
Σ per-state `tar | zstd -3` and the approximate CDC oracle over the case's
selected states, checks the states' logical bytes against the checkpoint
manifest, and writes `<dir>/references-<case>.json` with the Git result merged
in. Prints each file's SHA-256 (the pin).
"""

import argparse
import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path[:0] = [str(SRC), str(SRC.parents[1] / "shared" / "src")]

import cases  # noqa: E402
import references  # noqa: E402


def compute(refs, case_id):
    refs = Path(refs)
    states = [refs / "states" / str(k) for k in cases.SELECTIONS[case_id]]
    result = references.compute(states, include=("whole_file_unique", "tar_zstd", "cdc_oracle"))
    git = json.loads((refs / f"git-{case_id}" / "result.json").read_text())
    if git["selection"] != cases.SELECTIONS[case_id] or git["verification"]["fsck"] != "PASS":
        raise SystemExit(f"references_dsh.py: Git reference for {case_id} does not match the selection")
    result["git_pack"] = {
        "status": "MEASURED",
        "bytes": git["pack_plus_index_bytes"],
        "pack_bytes": git["pack_bytes"],
        "idx_bytes": git["index_bytes"],
        "version": git["git_version"],
        "command": git["command"],
        "recipe": "dsh-dedup v1.0.0 (commit-tree from seed trees, repack -a -d -f -F --window=10 --depth=50 --threads=2)",
        "pinned_dsh_dedup_v1_bytes": cases.PINNED_GIT_PACK_IDX_BYTES[case_id],
    }
    # Directory sizes count regular files only; the corpus logical bytes add symlink targets.
    files_logical = result["whole_file_unique"]["logical_bytes"]
    result["case"] = case_id
    result["selection"] = cases.SELECTIONS[case_id]
    result["expected_logical_bytes"] = cases.EXPECTED_LOGICAL_BYTES[case_id]
    result["regular_file_logical_bytes"] = files_logical
    result["seed_manifest_sha256"] = cases.seed_manifest_sha256()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refs", required=True)
    parser.add_argument("--case", action="append", choices=cases.CASE_IDS, required=True)
    args = parser.parse_args(argv)
    for case_id in args.case:
        result = compute(args.refs, case_id)
        pin = references.pin(result, Path(args.refs) / f"references-{case_id}.json")
        print(json.dumps({"case": case_id, "sha256": pin, **references.reference_bytes(result)}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
