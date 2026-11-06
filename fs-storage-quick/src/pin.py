#!/usr/bin/env python3
"""Pin the final-state oracles (no LayerFS).

  pin.py --docker-image ID --base DIR [--work DIR]

Q1–Q5: ``gen.py oracle <case>`` runs every part in an empty directory inside a
throwaway ``docker run --rm --network none`` of the suite image (the same
Python and filesystem semantics as the Sandbox) and prints the canonical
manifest of the final state. Q6: the edit model planned on the host over the
pinned base tree gives the p1/lane head and the shared p2 head. Writes
``src/pins.json`` tied to gen.py's and model.py's SHA-256.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cases  # noqa: E402


def oracle(case, image):
    got = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--pull", "never", "--user", "0:0",
         "--entrypoint", "python3", image, cases.GEN_IN_IMAGE, "oracle", case, f"/tmp/oracle-{case}"],
        check=True, capture_output=True, text=True, timeout=300,
    )
    return json.loads(got.stdout.strip().splitlines()[-1])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--docker-image", required=True)
    parser.add_argument("--base", required=True)
    args = parser.parse_args(argv)
    check = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--pull", "never", "--entrypoint", "sha256sum",
         args.docker_image, cases.GEN_IN_IMAGE, cases.MODEL_IN_IMAGE],
        check=True, capture_output=True, text=True, timeout=60).stdout.split()
    if check[0] != cases.GEN_SHA256 or check[2] != cases.MODEL_SHA256:
        raise SystemExit("image scripts differ from the repository copies; rebuild the image")
    pins = {
        "workload_version": cases.WORKLOAD_VERSION,
        "gen_sha256": cases.GEN_SHA256,
        "model_sha256": cases.MODEL_SHA256,
        "image": args.docker_image,
        "oracle": {},
    }
    for case in cases.CASE_IDS[:-1]:
        pins["oracle"][case] = oracle(case, args.docker_image)
        print(case, json.dumps(pins["oracle"][case]), flush=True)
    plan = cases.q6_plan(cases.load_base(args.base))
    pins["q6"] = {
        "base_manifest_sha256": cases.BASE_MANIFEST_SHA256,
        "base_logical": plan["base_logical"],
        "workload_sha256": plan["workload_sha256"],
        "lane_head": plan["lane_head"],
        "shared_head": plan["shared_head"],
        "lane_check": plan["lane_check"],
        "shared_check": plan["shared_check"],
    }
    pins["oracle"]["Q6"] = {"lane": plan["lane_head"]["sha256"], "identical": plan["shared_head"]["sha256"]}
    print("Q6", json.dumps(pins["q6"]), flush=True)
    (HERE / "pins.json").write_text(json.dumps(pins, indent=1, sort_keys=True) + "\n")
    print("pins.json", hashlib.sha256((HERE / "pins.json").read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
