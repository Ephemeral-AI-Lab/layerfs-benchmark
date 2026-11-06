"""fs-storage-history cases H01–H07: history shapes over one pinned base tree.

Every case starts from the same base (DSH checkpoint 157), imported with
`project init` into each project. Each Commit applies OPS_PER_COMMIT seeded
operations (model.py). A case is a list of Stores; a Store holds projects; a
project holds Branches in creation order, each forked from `main` or from an
earlier Branch's head. The plan (concrete ops and the oracle summary of every
Branch head) is computed on the host before a row starts.
"""

import hashlib
import json

import model

CASE_IDS = ("H01", "H02", "H03", "H04", "H05", "H06", "H07")
IMPLEMENTED_CASES = CASE_IDS
WORKLOAD_VERSION = "fs-storage-history-v1"

# Base tree: DSH checkpoint 157, the last Commit of the local seed
# deepseek-history-data/git-snapshots-157-v1/snapshots.git.
SEED_NAME = "git-snapshots-157-v1/snapshots.git"
SEED_PACK_SHA256 = "27c7598c04404730200654a1a4ad8f000d63d41da87531cc6e8f206a4e8133bc"
BASE_CHECKPOINT = 157
BASE_COMMIT = "4a096633dda569f403a6d34c61d7b206348db515"
BASE_TREE = "0175125b5dc4dd08965eb576b7c8aee28a73e0c3"
BASE_SOURCE_SHA = "b0a7d2ce3b4c19d7452e364b2d7acbfa87e707ed"
BASE_FILES = 9404  # regular files
BASE_LINKS = 11  # symlinks; 9,415 paths in all
BASE_BYTES = 65020822  # file bytes plus symlink target bytes
BASE_MANIFEST_SHA256 = "59069f602c04c92b5d3e479754dc392892bab70bdca6e8c9e18c056635f0cd52"

# Final counts (fixed by the SQLite probe before WORKLOAD_VERSION froze).
COUNTS = {
    "H01": {"commits": 500},
    "H02": {"branches": 50, "commits": 5},
    "H03": {"branches": 50, "commits": 1},
    "H04": {"depth": 10, "commits": 5},
    "H05": {"projects": 20, "commits": 5},
    "H06": {"projects": 20, "commits": 5},
    "H07": {"projects": 4, "branches": 5, "commits": 10},
}

TITLES = {
    "H01": "long history",
    "H02": "many branches",
    "H03": "identical branches",
    "H04": "nested forks",
    "H05": "projects in one Store",
    "H06": "projects in separate Stores",
    "H07": "combined",
}

SHOWS = {
    "H01": "delta chains past the depth cap; growth per Commit",
    "H02": "extra bytes per branch",
    "H03": "≈ metadata only per branch",
    "H04": "branches of branches",
    "H05": "cross-project sharing",
    "H06": "baseline: Σ H06 ÷ H05 = cross-project gain",
    "H07": "everything at once",
}

FLOOR_PROJECT = "e"  # the empty-folder project of the empty-Store floor


def _branch(name, source, commits, seed):
    return {"name": name, "from": source, "commits": commits, "seed": seed}


def shape(case_id):
    """Return [store] where store = {"suffix", "projects": [{"name", "branches"}]}."""
    if case_id not in CASE_IDS:
        raise ValueError(f"unknown fs-storage-history case: {case_id}")
    c = COUNTS[case_id]
    if case_id == "H01":
        projects = [{"name": "p01", "branches": [_branch("b01", "main", c["commits"], "H01/p01/b01")]}]
        return [{"suffix": "", "projects": projects}]
    if case_id in ("H02", "H03"):
        branches = []
        for i in range(1, c["branches"] + 1):
            seed = "H03/shared" if case_id == "H03" else f"H02/p01/b{i:02d}"
            branches.append(_branch(f"b{i:02d}", "main", c["commits"], seed))
        return [{"suffix": "", "projects": [{"name": "p01", "branches": branches}]}]
    if case_id == "H04":
        branches, source = [], "main"
        for i in range(1, c["depth"] + 1):
            branches.append(_branch(f"l{i:02d}", source, c["commits"], f"H04/p01/l{i:02d}"))
            source = f"l{i:02d}"
        return [{"suffix": "", "projects": [{"name": "p01", "branches": branches}]}]
    if case_id in ("H05", "H06"):
        # H06 uses H05's seeds, so the two cases hold identical content.
        projects = [
            {"name": f"p{i:02d}",
             "branches": [_branch("b01", "main", c["commits"], f"H05/p{i:02d}/b01")]}
            for i in range(1, c["projects"] + 1)
        ]
        if case_id == "H05":
            return [{"suffix": "", "projects": projects}]
        return [{"suffix": f"-s{i:02d}", "projects": [p]} for i, p in enumerate(projects, 1)]
    if case_id == "H07":
        projects = [
            {"name": f"p{i:02d}",
             "branches": [_branch(f"b{j:02d}", "main", c["commits"], f"H07/p{i:02d}/b{j:02d}")
                          for j in range(1, c["branches"] + 1)]}
            for i in range(1, c["projects"] + 1)
        ]
        return [{"suffix": "", "projects": projects}]
    raise AssertionError(case_id)


def commit_count(case_id):
    return sum(b["commits"] for s in shape(case_id) for p in s["projects"] for b in p["branches"])


def build_plan(case_id, base_state):
    """Concrete ops per Branch step plus each head's oracle summary.

    Returns {"stores": [{"suffix", "projects": [{"name", "branches": [
    {name, from, seed, commits, steps: [encoded ops], ops_sha256: [...],
     head: summary}]}]}], "workload_sha256": ...}. Also returns the set of
    distinct file contents ever produced (for whole-file references).
    """
    stores = []
    identity = hashlib.sha256()
    identity.update(json.dumps({"workload": WORKLOAD_VERSION, "model": model.MODEL_VERSION,
                                "base": BASE_MANIFEST_SHA256, "case": case_id,
                                "counts": COUNTS[case_id]}, sort_keys=True).encode())
    for store in shape(case_id):
        out_projects = []
        for project in store["projects"]:
            heads = {"main": base_state}
            out_branches = []
            for branch in project["branches"]:
                state = heads[branch["from"]].copy()
                steps, digests = [], []
                for step in range(1, branch["commits"] + 1):
                    ops = model.plan_step(state, branch["seed"], step)
                    steps.append(model.encode_ops(ops))
                    digests.append(model.ops_digest(ops))
                    identity.update(digests[-1].encode())
                heads[branch["name"]] = state
                out_branches.append({**branch, "steps": steps, "ops_sha256": digests,
                                     "head": state.summary(), "state": state})
            out_projects.append({"name": project["name"], "branches": out_branches})
        stores.append({"suffix": store["suffix"], "projects": out_projects})
    return {"case": case_id, "stores": stores, "workload_sha256": identity.hexdigest()}


def provenance(case_id, plan=None):
    value = {
        "workload_version": WORKLOAD_VERSION,
        "model_version": model.MODEL_VERSION,
        "case": case_id,
        "title": TITLES[case_id],
        "counts": dict(COUNTS[case_id]),
        "commits": commit_count(case_id),
        "base": {
            "checkpoint": BASE_CHECKPOINT,
            "seed": SEED_NAME,
            "seed_pack_sha256": SEED_PACK_SHA256,
            "commit": BASE_COMMIT,
            "tree": BASE_TREE,
            "files": BASE_FILES,
            "links": BASE_LINKS,
            "bytes": BASE_BYTES,
            "manifest_sha256": BASE_MANIFEST_SHA256,
        },
        "ops_per_commit": model.OPS_PER_COMMIT,
        "op_shares": dict(model.OP_SHARES),
    }
    if plan is not None:
        value["workload_sha256"] = plan["workload_sha256"]
    return value
