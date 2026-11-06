#!/usr/bin/env python3
"""Git pack + idx reference for one case, run once inside the suite image.

    docker run --rm --network none --user 501:501 -v <suite src>:/src:ro \
      -v <out>:/out <suite image> python3 /src/git_reference.py D10 /out/D10

The dsh-dedup v1.0.0 recipe (`.archive/dsh-dedup/reference.py`), applied to
the pinned seed: a fresh bare repository gets one linear Commit per selected
state with that state's exact root tree (`git commit-tree`, objects read from
the seed through GIT_ALTERNATE_OBJECT_DIRECTORIES only, no alternates file);
then `git repack -a -d -f -F --window=10 --depth=50 --threads=2`,
`prune-packed`, `fsck --full` and a tree-equality check. Writes result.json.
"""

import json
import os
import subprocess
import sys

import cases

SEED = "/opt/fs-storage-dsh/seed"
REPACK = ["repack", "-a", "-d", "-f", "-F", "--window=10", "--depth=50", "--threads=2"]


def main(argv):
    case_id, out = argv[1], argv[2]
    if os.path.exists(out):
        raise SystemExit(f"git_reference.py: {out} exists")
    selected = cases.SELECTIONS[case_id]
    with open(f"{SEED}/mapping.json") as stream:
        mapping = json.load(stream)
    with open(f"{SEED}/checkpoint-manifest.json") as stream:
        checkpoints = json.load(stream)["checkpoints"]
    repo = os.path.join(out, "repo.git")
    os.makedirs(out)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": out,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "fs-storage-dsh",
        "GIT_AUTHOR_EMAIL": "fs-storage-dsh@invalid",
        "GIT_COMMITTER_NAME": "fs-storage-dsh",
        "GIT_COMMITTER_EMAIL": "fs-storage-dsh@invalid",
        "GIT_AUTHOR_DATE": "1700000000 +0000",
        "GIT_COMMITTER_DATE": "1700000000 +0000",
    }
    alt = {**env, "GIT_ALTERNATE_OBJECT_DIRECTORIES": f"{SEED}/snapshots.git/objects"}

    def git(*args, environ=env):
        return subprocess.run(
            ["git", "-C", repo, *args], env=environ, check=True, capture_output=True, text=True, timeout=110
        ).stdout.strip()

    subprocess.run(["git", "init", "-q", "--bare", repo], env=env, check=True, timeout=30)
    parent = None
    for k in selected:
        tree = mapping[k - 1]["tree"]
        parent = git("commit-tree", tree, *(["-p", parent] if parent else []), "-m", f"dsh state {k}", environ=alt)
    git("update-ref", "refs/heads/main", parent)
    git(*REPACK, environ=alt)
    git("prune-packed")
    assert not os.path.exists(os.path.join(repo, "objects", "info", "alternates")), "alternates file written"
    git("fsck", "--full", "--no-dangling")
    trees = git("log", "--format=%T", "--reverse", "main").split("\n")
    assert trees == [mapping[k - 1]["tree"] for k in selected], "a Commit's tree differs from its state"
    pack_dir = os.path.join(repo, "objects", "pack")
    names = os.listdir(pack_dir)
    pack = sum(os.path.getsize(os.path.join(pack_dir, f)) for f in names if f.endswith(".pack"))
    index = sum(os.path.getsize(os.path.join(pack_dir, f)) for f in names if f.endswith(".idx"))
    counts = dict(line.split(": ", 1) for line in git("count-objects", "-v").splitlines())
    result = {
        "case": case_id,
        "states": len(selected),
        "selection": selected,
        "logical_bytes": sum(checkpoints[k - 1]["logical_bytes"] for k in selected),
        "git_version": subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.strip(),
        "command": REPACK,
        "pack_bytes": pack,
        "index_bytes": index,
        "pack_plus_index_bytes": pack + index,
        "pinned_pack_plus_index_bytes": cases.PINNED_GIT_PACK_IDX_BYTES[case_id],
        "object_count": int(counts["in-pack"]),
        "loose_objects": int(counts["count"]),
        "verification": {"fsck": "PASS", "trees_matched": len(trees), "no_alternates": True},
    }
    with open(os.path.join(out, "result.json"), "w") as stream:
        json.dump(result, stream, indent=1)
    print(json.dumps({k: result[k] for k in ("case", "states", "pack_plus_index_bytes", "pinned_pack_plus_index_bytes")}))


if __name__ == "__main__":
    main(sys.argv)
