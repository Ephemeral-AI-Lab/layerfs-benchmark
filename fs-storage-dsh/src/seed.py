#!/usr/bin/env python3
"""Stage the suite image's build context from the pinned seed (setup only).

    seed.py stage --data <deepseek-history-data> --out <new folder>

Copies every pinned seed file (cases.SEED_FILES) from the read-only data folder,
checks size and SHA-256, adds apply.py / verify.py and the Dockerfile, and
writes `opt/pins.sha256`, which the image build checks again. The output
belongs outside Git (e.g. ~/.cache/fs-storage-dsh/context-<id>); the seed is
never published. No git command runs on the host.
"""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import cases

SUITE = Path(__file__).resolve().parents[1]
SCRIPTS = ("apply.py", "verify.py")


def digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def stage(data, out):
    data, out = Path(data), Path(out)
    if out.exists():
        raise SystemExit(f"seed.py: {out} exists")
    opt = out / "opt"
    pins = []
    for relative, (size, sha) in sorted(cases.SEED_FILES.items()):
        source = data / cases.seed_source(relative)
        if source.stat().st_size != size or digest(source) != sha:
            raise SystemExit(f"seed.py: {source} differs from its pin")
        destination = opt / "seed" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        pins.append(f"{sha}  seed/{relative}")
    for name in SCRIPTS:
        shutil.copyfile(SUITE / "image" / name, opt / name)
        pins.append(f"{digest(opt / name)}  {name}")
    (opt / "pins.sha256").write_text("".join(line + "\n" for line in pins))
    shutil.copyfile(SUITE / "image" / "Dockerfile", out / "Dockerfile")
    record = {
        "seed_manifest_sha256": cases.seed_manifest_sha256(),
        "pins_sha256": digest(opt / "pins.sha256"),
        "scripts": {name: digest(opt / name) for name in SCRIPTS},
        "dockerfile_sha256": digest(out / "Dockerfile"),
    }
    (out / "stage.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("stage",))
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(stage(args.data, args.out), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
