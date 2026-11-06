#!/usr/bin/env python3
"""Compute and pin offline references and final-state oracles (no LayerFS).

  pin.py --work DIR [--docker-image ID] [--case M0x ...] [--keep]

Emits every state of each case with ``image/gen.py emit`` (inside a throwaway
``docker run --rm --network none`` of the suite image when ``--docker-image``
is given, so SQLite bytes match the Sandbox; otherwise with host Python),
computes ``shared/src/references.py`` references, writes the full result to
``DIR/references.json`` (local evidence, not committed) and the compact pins
to ``src/pins.json``. Snapshots are deleted unless ``--keep``.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "shared" / "src"))
sys.path.insert(0, str(HERE))
import cases  # noqa: E402
import references  # noqa: E402


def emit(case, out, image):
    if image:
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["docker", "run", "--rm", "--network", "none", "--pull", "never",
             "--user", "0:0", "-v", f"{out.parent}:/out", "--entrypoint", "python3", image,
             cases.GEN_IN_IMAGE, "emit", case, f"/out/{out.name}"],
            check=True, timeout=600,
        )
    else:
        subprocess.run([sys.executable, str(cases.GEN_PATH), "emit", case, str(out)], check=True, timeout=600)
    return sorted(p for p in out.iterdir() if p.name.startswith("s"))


def extra(case, snapshots):
    """Case-specific context numbers (per-file zstd-3 for M07 and M06 states)."""
    zstd = references._zstd3()[0]
    if zstd is None:
        return {}
    if case == "M07":
        last = snapshots[-1]
        return {f"zstd3_{p.name}": zstd(p.read_bytes()) for p in sorted(last.iterdir())}
    if case == "M08":
        return {f"zstd3_state{n + 1:02d}": zstd((s / "data.db").read_bytes()) for n, s in enumerate(snapshots)}
    return {}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--work", required=True)
    parser.add_argument("--docker-image")
    parser.add_argument("--case", action="append", choices=cases.CASE_IDS)
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args(argv)
    work = Path(args.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    full_path = work / "references.json"
    full = json.loads(full_path.read_text()) if full_path.exists() else {}
    if full.get("gen_sha256") not in (None, cases.GEN_SHA256):
        full = {}
    full.update(workload_version=cases.WORKLOAD_VERSION, gen_sha256=cases.GEN_SHA256)
    full.setdefault("cases", {})
    for case in args.case or cases.CASE_IDS:
        started = time.monotonic()
        out = work / "emit" / case
        if out.exists():
            shutil.rmtree(out)
        snapshots = emit(case, out, args.docker_image)
        result = references.compute(snapshots)
        result["extra"] = extra(case, snapshots)
        result["emit"] = {"route": "docker" if args.docker_image else "host", "image": args.docker_image}
        result["elapsed_s_ineligible"] = round(time.monotonic() - started, 1)
        full["cases"][case] = result
        references.pin(full, full_path)
        print(case, json.dumps(references.reference_bytes(result)), result["manifests"][-1]["sha256"], flush=True)
        if not args.keep:
            shutil.rmtree(out)
    full_sha = references.pin(full, full_path)
    pins = {
        "workload_version": cases.WORKLOAD_VERSION,
        "gen_sha256": cases.GEN_SHA256,
        "references_json_sha256": full_sha,
        "emit": {case: full["cases"][case]["emit"] for case in sorted(full["cases"])},
        "oracle": {case: full["cases"][case]["manifests"][-1] for case in sorted(full["cases"])},
        "input_sha256": {case: full["cases"][case]["input_sha256"] for case in sorted(full["cases"])},
        "references": {
            case: {**references.reference_bytes(full["cases"][case]),
                   "logical_bytes": full["cases"][case]["whole_file_unique"]["logical_bytes"],
                   "cdc_unique_raw_bytes": full["cases"][case]["cdc_oracle"]["unique_raw_bytes"],
                   **full["cases"][case].get("extra", {})}
            for case in sorted(full["cases"])
        },
        "tools": next(iter(full["cases"].values()))["tools"] if full["cases"] else {},
    }
    (HERE / "pins.json").write_text(json.dumps(pins, indent=1, sort_keys=True) + "\n")
    print("pins.json", hashlib.sha256((HERE / "pins.json").read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
