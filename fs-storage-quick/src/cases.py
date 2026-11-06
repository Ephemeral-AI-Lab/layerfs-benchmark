"""fs-storage-quick cases Q1–Q6: plans, commands, oracles and row specs.

Q1–Q5 run ``image/gen.py`` (fs-storage-micro's generator at smaller counts,
keyed by ``fs-storage-quick-v1``); Q6 runs ``image/model.py`` (a copy of
fs-storage-history's ``fsh-edit-model-v1``) over the pinned DSH checkpoint-157
base tree. Both scripts are baked into the suite image and every Exec
re-checks their SHA-256 against this repository's copy.
"""

import hashlib
import importlib.util
import json
import re
import shlex
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
IMAGE = SUITE / "image"
GEN_PATH = IMAGE / "gen.py"
MODEL_PATH = IMAGE / "model.py"
GEN_IN_IMAGE = "/opt/fs-storage-quick/gen.py"
MODEL_IN_IMAGE = "/opt/fs-storage-quick/model.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = _load("fs_storage_quick_gen", GEN_PATH)
model = _load("fs_storage_quick_model", MODEL_PATH)

WORKLOAD_VERSION = gen.WORKLOAD_VERSION
CASE_IDS = ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6")
GEN_SHA256 = hashlib.sha256(GEN_PATH.read_bytes()).hexdigest()
MODEL_SHA256 = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()

# Q6 counts (frozen with WORKLOAD_VERSION after the calibration probe).
Q6_INITS = 1  # projects p1[, p2 …], each `project init` of the base tree
Q6_EDIT_COMMITS = 20  # edit Commits on p1/lane
Q6_IDENTICAL = 3  # Branches b01.. from the last project's main, each the same single Commit
Q6_LANE_SEED = f"{WORKLOAD_VERSION}/Q6/p1/lane"
Q6_SHARED_SEED = f"{WORKLOAD_VERSION}/Q6/shared"

# Base tree: DSH checkpoint 157 (same pins as fs-storage-history-v1).
BASE_CHECKPOINT = 157
BASE_SEED = "git-snapshots-157-v1/snapshots.git"
BASE_FILES = 9404
BASE_LINKS = 11
BASE_BYTES = 65020822  # file bytes plus symlink target bytes
BASE_MANIFEST_SHA256 = "59069f602c04c92b5d3e479754dc392892bab70bdca6e8c9e18c056635f0cd52"

TITLES = {
    "Q1": "tiny files",
    "Q2": "in-place edits",
    "Q3": "rename-over edits",
    "Q4": "new-path edits",
    "Q5": "large file",
    "Q6": "history",
}
WORKLOADS = {
    "Q1": f"{gen.Q1_FILES:,} files of 0–4,096 B in {gen.Q1_FILES // gen.Q1_PER_DIR} directories, 1 Commit",
    "Q2": f"{gen.TEXT_FILES} synthetic text files of 16–64 KiB, then {gen.TEXT_EDITS} Commits each replacing 1% of lines in every file (in place)",
    "Q3": "the Q2 content sequence, written as temp file + rename over the old path",
    "Q4": "the Q2 content sequence, each version at a new path (fNNN.vVV.txt), old path unlinked",
    "Q5": "32 MiB random file; insert 1 B at start; insert 1 B at middle; overwrite 4 KiB at middle; append 1 MiB; delete first byte",
    "Q6": (f"{Q6_INITS} × `project init` of the 65.0 MB DSH-157 base; {Q6_EDIT_COMMITS} edit Commits on lane "
           f"(5 seeded operations each); {Q6_IDENTICAL} Branches from main with the same single Commit"),
}
EXERCISES = {
    "Q1": "per-file rows: inode_value, object_location, file_digest; PostgreSQL row/index overhead",
    "Q2": "chain budget / chain-root re-base",
    "Q3": "small-file delta base on rename-over",
    "Q4": "similarity ring",
    "Q5": "extent / directory page metadata",
    "Q6": "Init staging cleanup, per-Commit rows and metadata, Branch cost",
}
WRITE_METHOD = dict(gen.WRITE_METHOD, Q6="model ops: in-place edit/append, new path, unlink, rename")

# Final-state oracles (pins.json), tied to the generator and model hashes.
ORACLE = {}
PINS = {}
PINS_SHA256 = None


def _load_pins():
    global PINS_SHA256
    path = SUITE / "src" / "pins.json"
    if not path.exists():
        return
    text = path.read_text()
    pins = json.loads(text)
    if (pins.get("workload_version") != WORKLOAD_VERSION or pins.get("gen_sha256") != GEN_SHA256
            or pins.get("model_sha256") != MODEL_SHA256):
        return  # stale pins never verify a different workload
    PINS_SHA256 = hashlib.sha256(text.encode()).hexdigest()
    PINS.update(pins)
    ORACLE.update(pins.get("oracle", {}))


_load_pins()


def commits(case):
    if case == "Q6":
        return Q6_EDIT_COMMITS + Q6_IDENTICAL
    return len(gen.PLAN[case])


# ------------------------------------------------------------------ commands


def _check_script(sha, path):
    return f"printf '%s  %s\\n' {sha} {path} | sha256sum -c --quiet; "


def step_command(case, part):
    """One bash command for the Exec: check gen.py's hash, run one part."""
    if case not in gen.PLAN or not re.fullmatch(r"[a-z-]+(:\d{2})?", part):
        raise ValueError(f"bad step {case} {part}")
    return ("set -euo pipefail; " + _check_script(GEN_SHA256, GEN_IN_IMAGE)
            + shlex.join(["python3", GEN_IN_IMAGE, "step", case, part]))


def verify_command():
    return ("set -euo pipefail; " + _check_script(GEN_SHA256, GEN_IN_IMAGE)
            + shlex.join(["python3", GEN_IN_IMAGE, "manifest", "."]))


def apply_command(encoded):
    return ("set -euo pipefail; " + _check_script(MODEL_SHA256, MODEL_IN_IMAGE)
            + shlex.join(["python3", MODEL_IN_IMAGE, "apply", encoded]))


def namespace_command(paths):
    return ("set -euo pipefail; " + _check_script(GEN_SHA256, GEN_IN_IMAGE)
            + shlex.join(["python3", GEN_IN_IMAGE, "namespace", gen.encode_paths(paths)]))


def touched_paths(ops_list):
    """Every path an op wrote, removed or renamed (source and target)."""
    paths = set()
    for ops in ops_list:
        for op in ops:
            paths.add(op["path"])
            if op.get("to"):
                paths.add(op["to"])
    return sorted(paths, key=str.encode)


def namespace_oracle(state, paths):
    """Host side of ``gen.py namespace``: the same digests from the model State."""
    lines = []
    for path in sorted(state.entries, key=str.encode):
        entry = state.entries[path]
        if entry.kind == "link":
            lines.append(f"{path}\tlink\t0\t{len(entry.data)}\t{entry.sha256}\n")
        else:
            lines.append(f"{path}\tfile\t{entry.mode:o}\t{len(entry.data)}\n")
    touched = hashlib.sha256()
    for path in sorted(set(paths), key=str.encode):
        entry = state.entries.get(path)
        touched.update(f"{path}\t{entry.sha256 if entry is not None and entry.kind == 'file' else '-'}\n".encode())
    return {
        "entries": len(lines),
        "bytes": sum(len(e.data) for e in state.entries.values()),
        "empty_dirs": 0,
        "other": 0,
        "namespace_sha256": hashlib.sha256("".join(lines).encode()).hexdigest(),
        "touched": len(set(paths)),
        "touched_sha256": touched.hexdigest(),
    }


def _last_json(result):
    try:
        return json.loads(result.get("stdout", "").strip().splitlines()[-1])
    except (ValueError, IndexError) as error:
        raise ValueError(f"verifier output is not JSON: {error}") from error


def check_manifest(case):
    def check(result):
        observed = _last_json(result)
        expected = ORACLE.get(case)
        if not expected:
            raise ValueError(f"no pinned oracle for {case}")
        if observed != expected:
            raise ValueError(f"final state differs: expected {expected}, observed {observed}")

    return check


def check_namespace(expected):
    """Q6 head check: namespace digest, touched-path digest, no empty dirs or other types."""
    def check(result):
        observed = _last_json(result)
        if observed != expected:
            raise ValueError(f"final state differs: expected {expected}, observed {observed}")

    return check


def apply_check(result):
    counts = _last_json(result).get("applied") or {}
    if sum(counts.values()) != model.OPS_PER_COMMIT:
        raise ValueError(f"model applied {counts}, expected {model.OPS_PER_COMMIT} operations")


# ------------------------------------------------------------------ Q6 plan


def q6_plan(base_state):
    """Concrete ops for p1/lane and the shared p2 Commit, plus head oracles."""
    lane = base_state.copy()
    steps, digests, lane_ops = [], [], []
    for step in range(1, Q6_EDIT_COMMITS + 1):
        ops = model.plan_step(lane, Q6_LANE_SEED, step)
        lane_ops.append(ops)
        steps.append(model.encode_ops(ops))
        digests.append(model.ops_digest(ops))
    shared = base_state.copy()
    shared_ops = model.plan_step(shared, Q6_SHARED_SEED, 1)
    lane_touched, shared_touched = touched_paths(lane_ops), touched_paths([shared_ops])
    identity = hashlib.sha256(json.dumps({
        "workload": WORKLOAD_VERSION, "model": model.MODEL_VERSION, "base": BASE_MANIFEST_SHA256,
        "lane": digests, "shared": model.ops_digest(shared_ops),
        "counts": [Q6_INITS, Q6_EDIT_COMMITS, Q6_IDENTICAL],
    }, sort_keys=True).encode()).hexdigest()

    def head(state):
        summary = state.summary()
        summary.pop("buckets")
        return summary

    return {
        "lane_steps": steps,
        "lane_head": head(lane),
        "lane_touched": lane_touched,
        "lane_check": namespace_oracle(lane, lane_touched),
        "shared_step": model.encode_ops(shared_ops),
        "shared_head": head(shared),
        "shared_touched": shared_touched,
        "shared_check": namespace_oracle(shared, shared_touched),
        "base_logical": sum(len(e.data) for e in base_state.entries.values() if e.kind == "file"),
        "workload_sha256": identity,
    }


def check_base(summary):
    expected = {"files": BASE_FILES, "links": BASE_LINKS, "bytes": BASE_BYTES, "sha256": BASE_MANIFEST_SHA256}
    actual = {key: summary.get(key) for key in expected}
    if actual != expected:
        raise ValueError(f"base tree differs from the pins: {actual} != {expected}")


def load_base(root):
    """Read the extracted base tree into a model State and check its pins."""
    import os

    root = Path(root)
    entries = {}
    for directory, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            full = Path(directory) / name
            rel = full.relative_to(root).as_posix()
            if full.is_symlink():
                entries[rel] = model.Entry("link", 0, os.readlink(full).encode())
            elif full.is_file():
                entries[rel] = model.Entry("file", full.stat().st_mode & 0o7777, full.read_bytes())
    state = model.State(entries)
    check_base(state.summary())
    return state


# ------------------------------------------------------------------ provenance


def provenance(case, q6=None):
    value = {
        "case": case,
        "title": TITLES[case],
        "workload_version": WORKLOAD_VERSION,
        "gen_sha256": GEN_SHA256,
        "model_sha256": MODEL_SHA256,
        "pins_sha256": PINS_SHA256,
        "write_method": WRITE_METHOD[case],
        "commits": commits(case),
        "oracle": ORACLE.get(case),
    }
    if case == "Q6":
        value.update(model_version=model.MODEL_VERSION, inits=Q6_INITS, edit_commits=Q6_EDIT_COMMITS,
                     identical_branches=Q6_IDENTICAL,
                     base={"checkpoint": BASE_CHECKPOINT, "seed": BASE_SEED, "files": BASE_FILES,
                           "links": BASE_LINKS, "bytes": BASE_BYTES, "manifest_sha256": BASE_MANIFEST_SHA256})
        if q6:
            value["workload_sha256"] = q6["workload_sha256"]
    else:
        plan = [[step_command(case, part) for part in parts] for parts in gen.PLAN[case]]
        value["plan"] = gen.PLAN[case]
        value["commands_sha256"] = hashlib.sha256(json.dumps(plan).encode()).hexdigest()
    return value


def get_case(cell, verify=False):
    if cell not in CASE_IDS:
        raise KeyError(cell)
    return {"provenance": provenance(cell), "title": TITLES[cell]}


# ------------------------------------------------------------------ row specs


def _gen_steps(case, project, sandbox):
    out = [
        {"op": "sandbox", "project": project, "sandbox": sandbox},
        {"op": "mount", "sandbox": sandbox, "branch": "lane", "name": "w", "as": "w"},
    ]
    for number, parts in enumerate(gen.PLAN[case], start=1):
        for part in parts:
            out.append({"op": "exec", "ws": "w", "command": step_command(case, part), "timeout_s": 120,
                        "label": f"c{number:02d}/{part}"})
        out.append({"op": "commit", "ws": "w", "timeout_s": 120, "label": f"c{number:02d}"})
    out += [
        {"op": "unmount", "ws": "w"},
        {"op": "verify", "sandbox": sandbox, "project": project, "branch": "lane", "name": "v",
         "command": verify_command(), "check": check_manifest(case)},
        {"op": "close", "sandbox": sandbox},
    ]
    return out


def q6_projects(name):
    return [f"{name}/p{i}" for i in range(1, Q6_INITS + 1)]


def _q6_steps(name, plan):
    projects = q6_projects(name)
    p1, last = projects[0], projects[-1]
    a, b = f"{name}-a", f"{name}-b"
    out = [
        {"op": "sandbox", "project": p1, "sandbox": a},
        {"op": "mount", "sandbox": a, "branch": "lane", "name": "w", "as": "w"},
    ]
    for step, encoded in enumerate(plan["lane_steps"], start=1):
        out.append({"op": "exec", "ws": "w", "command": apply_command(encoded), "timeout_s": 120,
                    "label": f"lane/{step:02d}", "check": apply_check})
        out.append({"op": "commit", "ws": "w", "timeout_s": 120, "label": f"lane/{step:02d}"})
    out += [
        {"op": "unmount", "ws": "w"},
        {"op": "verify", "sandbox": a, "project": p1, "branch": "lane", "name": "v",
         "command": namespace_command(plan["lane_touched"]), "check": check_namespace(plan["lane_check"])},
    ]
    if last != p1:
        out += [{"op": "close", "sandbox": a}, {"op": "sandbox", "project": last, "sandbox": b}]
    else:
        b = a
    for index in range(1, Q6_IDENTICAL + 1):
        branch = f"b{index:02d}"
        out += [
            {"op": "mount", "sandbox": b, "branch": branch, "name": f"w{index:02d}", "as": branch},
            {"op": "exec", "ws": branch, "command": apply_command(plan["shared_step"]), "timeout_s": 120,
             "label": f"{branch}/01", "check": apply_check},
            {"op": "commit", "ws": branch, "timeout_s": 120, "label": f"{branch}/01"},
            {"op": "unmount", "ws": branch},
        ]
    # b01 is verified by content; b02.. by root identity with b01 (root_checks, after `commit list`).
    out.append({"op": "verify", "sandbox": b, "project": last, "branch": "b01", "name": "v01",
                "command": namespace_command(plan["shared_touched"]), "check": check_namespace(plan["shared_check"])})
    out.append({"op": "close", "sandbox": b})
    return out


def spec(case, backend, name, config, database_url=None, q6=None):
    """One row: a fresh Store, the empty-Store floor, the case's work, checks."""
    storage_config = config.get("storage", {})
    common = {
        "prefix": name,
        "machine": config["machines"]["docker"]["name"],
        "password_env": config.get("postgresql", {}).get("password_env"),
        "allocated": storage_config.get("allocated"),
        "store": {"name": name, "backend": backend, "url": database_url},
        "timeout_s": 60,
    }
    if case != "Q6":
        project = f"{name}/p"
        return {
            **common,
            "floor_project": {"project": project, "source": config["empty_source"]},
            "inits": [],
            "branches": [{"project": project, "name": "lane", "from": "main"}],
            "steps": _gen_steps(case, project, name),
            "collect": [{"project": project, "branch": "lane"}],
        }
    if q6 is None:
        raise ValueError("Q6 needs its plan (q6_plan of the base tree)")
    projects = q6_projects(name)
    p1, last = projects[0], projects[-1]
    identical = [f"b{i:02d}" for i in range(1, Q6_IDENTICAL + 1)]
    return {
        **common,
        "floor_project": {"project": f"{name}/e", "source": config["empty_source"]},
        "inits": [{"project": p, "source": config["base_dir"], "label": f"init_{p.rsplit('/', 1)[1]}"}
                  for p in projects],
        "branches": [{"project": p1, "name": "lane", "from": "main"}]
        + [{"project": last, "name": b, "from": "main"} for b in identical],
        "steps": _q6_steps(name, q6),
        "collect": [{"project": p1, "branch": "lane"}] + [{"project": last, "branch": b} for b in identical],
        "root_checks": [{"project": last, "branch": b, "reference": "b01"} for b in identical[1:]],
        "init_logical": q6["base_logical"] * Q6_INITS,
    }
