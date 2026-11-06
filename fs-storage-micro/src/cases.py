"""fs-storage-micro cases M01–M08: plans, commands, oracles and references.

The generator ``image/gen.py`` is the workload: it is baked into the Sandbox
image and every Exec re-checks its SHA-256 against this repository's copy.
"""

import hashlib
import importlib.util
import json
import re
import shlex
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
GEN_PATH = SUITE / "image" / "gen.py"
GEN_IN_IMAGE = "/opt/fs-storage-micro/gen.py"

_spec = importlib.util.spec_from_file_location("fs_storage_micro_gen", GEN_PATH)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

WORKLOAD_VERSION = gen.WORKLOAD_VERSION
CASE_IDS = tuple(sorted(gen.PLAN))
GEN_SHA256 = hashlib.sha256(GEN_PATH.read_bytes()).hexdigest()
MiB = 1 << 20

TITLES = {
    "M01": "tiny files",
    "M02": "duplicates",
    "M03": "in-place edits",
    "M04": "rename-over edits",
    "M05": "new-path edits",
    "M06": "large file",
    "M07": "compressibility",
    "M08": "SQLite churn",
}
WORKLOADS = {
    "M01": "10,000 files of 0–4,096 B (uniform, SHAKE-256 bytes) in 100 directories",
    "M02": "one 50,000,000 B tree (200 files, half synthetic text, half random), then 10 copies at new paths",
    "M03": "100 synthetic text files of 16–64 KiB; 20 Commits each replacing 1% of lines in every file",
    "M04": "same content sequence as M03",
    "M05": "same content sequence as M03; version v at fNNN.vVV.txt",
    "M06": "64 MiB random file; insert 1 B at start; insert 1 B at middle; overwrite 4 KiB at middle; append 1 MiB; delete first byte",
    "M07": "64 MiB random, 64 MiB zeros, 64 MiB synthetic text; one file per Commit",
    "M08": "SQLite database of 147,000 rows (33,542,144 B, page 4,096); 10 Commits each updating 1% of rows (same-length values); then VACUUM",
}
EXPECTED = {
    "M01": "net bytes ÷ 10,000 = overhead per small file",
    "M02": "second Commit stores only tree/metadata (≈0 payload)",
    "M03": "deltas against the previous version; the chain passes depth 16 (a fuller object re-stored)",
    "M04": "compare with M03 (rename-over also deltas against the previous version)",
    "M05": "similarity ring only; compare with M03",
    "M06": "each edit adds ≈1–2 chunks (≤64 KiB), except append (≈1 MiB)",
    "M07": "random ≈64 MiB stored raw, zeros ≈0, text at the zstd-3 ratio",
    "M08": "page-local churn reuses most chunks; VACUUM reshuffles",
}

# Final-state oracle per case: canonical manifest of the last state, from the
# reference emit in the same image (pinned before the measured run).
ORACLE = {}
# Offline references per case (bytes), pinned from references.json.
REFERENCES = {}
REFERENCES_PIN = None


def _load_pins():
    global REFERENCES_PIN
    path = SUITE / "src" / "pins.json"
    if not path.exists():
        return
    text = path.read_text()
    REFERENCES_PIN = hashlib.sha256(text.encode()).hexdigest()
    pins = json.loads(text)
    if pins.get("workload_version") != WORKLOAD_VERSION or pins.get("gen_sha256") != GEN_SHA256:
        return  # stale pins never verify a different workload
    ORACLE.update(pins.get("oracle", {}))
    REFERENCES.update(pins.get("references", {}))


_load_pins()


def step_command(case, part):
    """One bash command for the Exec: check gen.py's hash, run one part."""
    if case not in gen.PLAN or not re.fullmatch(r"[a-z-]+(:\d{2})?", part):
        raise ValueError(f"bad step {case} {part}")
    return (
        "set -euo pipefail; "
        f"printf '%s  %s\\n' {GEN_SHA256} {GEN_IN_IMAGE} | sha256sum -c --quiet; "
        + shlex.join(["python3", GEN_IN_IMAGE, "step", case, part])
    )


def verify_command():
    return (
        "set -euo pipefail; "
        f"printf '%s  %s\\n' {GEN_SHA256} {GEN_IN_IMAGE} | sha256sum -c --quiet; "
        + shlex.join(["python3", GEN_IN_IMAGE, "manifest", "."])
    )


def check_manifest(case):
    def check(result):
        try:
            observed = json.loads(result.get("stdout", "").strip().splitlines()[-1])
        except (ValueError, IndexError) as error:
            raise ValueError(f"verifier output is not a manifest: {error}") from error
        expected = ORACLE.get(case)
        if not expected:
            raise ValueError(f"no pinned oracle for {case}")
        if observed != expected:
            raise ValueError(f"final state differs: expected {expected}, observed {observed}")

    return check


def provenance(case):
    commands = [[step_command(case, part) for part in parts] for parts in gen.PLAN[case]]
    return {
        "case": case,
        "workload_version": WORKLOAD_VERSION,
        "gen_sha256": GEN_SHA256,
        "write_method": gen.WRITE_METHOD[case],
        "commits": len(gen.PLAN[case]),
        "plan": gen.PLAN[case],
        "commands_sha256": hashlib.sha256(json.dumps(commands).encode()).hexdigest(),
        "verifier_sha256": hashlib.sha256(verify_command().encode()).hexdigest(),
        "oracle": ORACLE.get(case),
        "references_pin": REFERENCES_PIN,
    }


def get_case(cell, verify=False):
    if cell not in gen.PLAN:
        raise KeyError(cell)
    return {"provenance": provenance(cell), "title": TITLES[cell]}


def steps(case, project, sandbox):
    out = [
        {"op": "sandbox", "project": project, "sandbox": sandbox},
        {"op": "mount", "sandbox": sandbox, "branch": "lane", "name": "w", "as": "w"},
    ]
    for number, parts in enumerate(gen.PLAN[case], start=1):
        for part in parts:
            out.append({"op": "exec", "ws": "w", "command": step_command(case, part), "timeout_s": 120})
        out.append({"op": "commit", "ws": "w", "timeout_s": 120, "label": f"c{number:02d}"})
    out += [{"op": "unmount", "ws": "w"}, {"op": "close", "sandbox": sandbox}]
    return out


def spec(case, backend, name, config, database_url=None):
    """storage.run_row spec for one row: one fresh Store, one project, one branch."""
    project = f"{name}/p"
    store = {"name": name, "backend": backend, "projects": [{"project": project, "source": config["empty_source"]}]}
    if backend == "postgresql":
        store["url"] = database_url
    storage_config = config.get("storage", {})
    return {
        "prefix": name,
        "machine": config["machines"]["docker"]["name"],
        "password_env": config.get("postgresql", {}).get("password_env"),
        "allocated": storage_config.get("allocated"),
        "stores": [store],
        "branches": [{"project": project, "name": "lane", "from": "main"}],
        "steps": steps(case, project, name),
        "collect": [{"project": project, "branch": "lane"}],
        "verify": [{"project": project, "branch": "lane", "command": verify_command(), "check": check_manifest(case), "timeout_s": 120}],
        "timeout_s": 60,
    }
