"""fs-storage-dsh: the DeepSeek-harness checkpoint history at stride 10 and 3.

Workload `fs-storage-dsh-v1`. Starting view: an empty project. For each
selected state k (after the previous selected state p, or 0 first) one Exec
runs `apply.py p k` in the Workspace, then one Workspace Commit. After the last
state one Exec runs `verify.py <last>` against the pinned corpus oracle.
"""

import hashlib
import json
import shlex

CASE_IDS = ("D10", "D03")
IMPLEMENTED_CASES = CASE_IDS
WORKLOAD_VERSION = "fs-storage-dsh-v1"
TOOL_ROOT = "/opt/fs-storage-dsh"
STATES = 157

SELECTIONS = {
    "D10": sorted(set(range(1, STATES + 1, 10)) | {STATES}),
    "D03": list(range(1, STATES + 1, 3)),
}
# Σ checkpoint-manifest logical_bytes over the selection (file bytes plus
# symlink target bytes), and the dsh-dedup v1.0.0 Git pack + idx pins.
EXPECTED_LOGICAL_BYTES = {"D10": 561_010_345, "D03": 1_676_767_835}
PINNED_GIT_PACK_IDX_BYTES = {"D10": 41_797_536, "D03": 48_169_384}
# Context only (dsh-dedup v1.0.0, SDK route, different policy history).
DSH_DEDUP_V1_ALLOCATED_BYTES = {"D10": 53_125_120, "D03": 69_455_872}

WRITE_METHOD = (
    "in-place O_WRONLY|O_TRUNC rewrite of changed regular files (same inode); "
    "unlink for removed paths and file<->symlink type changes; O_CREAT|O_EXCL "
    "for new paths; symlink retarget = unlink + symlink; chmod for mode-only "
    "changes; emptied directories removed"
)
STORAGE_POLICY = (
    "LayerFS 2.0 fixed policy: CDC GEAR 8/16/32 KiB for files >= 128 KiB, "
    "whole-file objects below; zstd prefix deltas depth 16 (whole file) / 8 "
    "(chunk) / 8 (metadata); per-object zstd level 3; append-only packs"
)

# Pinned seed: deepseek-history-data/git-snapshots-157-v1 (157 trees as
# linear Commits) plus the corpus checkpoint manifest and the final-state
# oracle (both cases end at state 157). Paths are relative to the image's /opt/fs-storage-dsh/seed.
# Values: (size bytes, SHA-256).
SEED_FILES = {
    "snapshots.git/HEAD": (21, "28d25bf82af4c0e2b72f50959b2beb859e3e60b9630a5e8c603dad4ddb2b6e80"),
    "snapshots.git/config": (279, "310b9bdd241d65b393dae1c8f060468c3bfa4c77345939b04b3bfae7d34cdd63"),
    "snapshots.git/info/refs": (57, "4eb4ac0f8273a203ce85457a6964af8c4c09540c79693a57458e646e87ecc1c1"),
    "snapshots.git/objects/info/packs": (54, "69c3075c007b09dc148903a347fd95d31fac8bbbfc59e4b0e257f04f8489c535"),
    "snapshots.git/objects/pack/pack-610e32a558f31eb4a3a39f9b3385b25619f028b5.bitmap": (
        656_002,
        "2f7343e895f2c93c2b661cd7280fcbfc7b0840dd29a79b4b6e709a2118a9dcc5",
    ),
    "snapshots.git/objects/pack/pack-610e32a558f31eb4a3a39f9b3385b25619f028b5.idx": (
        3_083_340,
        "9e01310817261ca989b30185398c179717c82da794bd9b92ec755b56fcf51fd6",
    ),
    "snapshots.git/objects/pack/pack-610e32a558f31eb4a3a39f9b3385b25619f028b5.pack": (
        51_989_900,
        "27c7598c04404730200654a1a4ad8f000d63d41da87531cc6e8f206a4e8133bc",
    ),
    "snapshots.git/objects/pack/pack-610e32a558f31eb4a3a39f9b3385b25619f028b5.rev": (
        440_376,
        "07d380b06d6403459c43836994139afd53f8a75de3ea753a4e59c0ad68ec0910",
    ),
    "snapshots.git/refs/heads/main": (41, "6bf22426c24bcc8994a38fe048c28f8c807468cd2b95174ab5065ddc236d9281"),
    "mapping.json": (32_237, "54bbdc3a73eecc7c8e362b9cc245064508d5556235259d4182fb79570ffc1c59"),
    "checkpoint-manifest.json": (50_193, "03f21acfb415907f521217e7a972ed512265c8d0c2da0f8034e2ff3014334271"),
    "oracles/157.json": (2_285_860, "10e705a338baa86a1656c4b462aa27e9a3f6381d74b4f0fd31bd82c80d295e3c"),
}
# Where each seed file comes from under the deepseek-history-data root.
ORACLE_SOURCES = {
    157: "b0a7d2ce3b4c19d7452e364b2d7acbfa87e707ed",
}
# Recorded, not copied into the image.
SEED_COMPANIONS = {
    "results.json": (3_053, "63bf99c044d9fdb7f9319c12b9f00faa83e92d14e3c360f8cb2992d7845d304a"),
    "snapshot-object-ids.txt": (4_506_884, "02837ecda1a336cbb6b466b1793f46e4d79bc891c9ef985c9e7f8a6c18425fe1"),
}
SEED_HEAD = "main"
FINAL_TREES = {
    157: "0175125b5dc4dd08965eb576b7c8aee28a73e0c3",
}


def seed_source(relative):
    """Path of a pinned seed file relative to deepseek-history-data."""
    if relative.startswith("oracles/"):
        state = int(relative.split("/")[1].split(".")[0])
        return f"oracles/{ORACLE_SOURCES[state]}.json"
    if relative == "checkpoint-manifest.json":
        return relative
    return "git-snapshots-157-v1/" + relative


def seed_manifest_sha256():
    """One identity for the pinned seed file set."""
    text = "".join(f"{sha}  {size}  {path}\n" for path, (size, sha) in sorted(SEED_FILES.items()))
    return hashlib.sha256(text.encode()).hexdigest()


def apply_command(before, after):
    return shlex.join(["python3", f"{TOOL_ROOT}/apply.py", str(before), str(after)])


def verify_command(state):
    return shlex.join(["python3", f"{TOOL_ROOT}/verify.py", str(state)])


def steps(case_id):
    """[(previous state, state)] for each Exec + Commit of the case."""
    selected = SELECTIONS[case_id]
    return list(zip([0, *selected[:-1]], selected))


def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()


def get_case(case_id, verify=False):
    if case_id not in CASE_IDS:
        raise ValueError(f"unknown fs-storage-dsh case: {case_id}")
    selected = SELECTIONS[case_id]
    commands = [apply_command(a, b) for a, b in steps(case_id)]
    final = verify_command(selected[-1])
    return {
        "id": case_id,
        "starting_view": "empty",
        "states": list(selected),
        "steps": steps(case_id),
        "final_state": selected[-1],
        "final_tree": FINAL_TREES[selected[-1]],
        "commands": commands,
        "verify_command": final,
        "provenance": {
            "workload_version": WORKLOAD_VERSION,
            "selection": list(selected),
            "expected_logical_bytes": EXPECTED_LOGICAL_BYTES[case_id],
            "write_method": WRITE_METHOD,
            "storage_policy": STORAGE_POLICY,
            "seed_manifest_sha256": seed_manifest_sha256(),
            "commands_sha256": sha256(json.dumps(commands)),
            "verify_command": final,
        },
    }


def parse_apply(stdout, before, after):
    """Validate apply.py's one JSON line."""
    try:
        value = json.loads(stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as error:
        raise ValueError(f"apply.py {before}->{after}: no JSON result") from error
    if value.get("from") != before or value.get("to") != after:
        raise ValueError(f"apply.py answered {value.get('from')}->{value.get('to')}")
    return value


def parse_verify(stdout, state):
    try:
        value = json.loads(stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as error:
        raise ValueError("verify.py: no JSON result") from error
    if value.get("state") != state or value.get("mismatches") != 0 or value.get("entries") != value.get("expected"):
        raise ValueError(f"verify.py: {value}")
    return value
