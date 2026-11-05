"""Frozen one-rank mdtest metadata diagnostics, using unmodified upstream IOR."""

import hashlib
import math
import re

CASE_IDS = ("M01", "M02")
SOURCE_SHA = "8e109900e24d45f1cd1184f108458f5fa9b4692c"
SOURCE_URL = "https://github.com/hpc/ior"
SOURCE_FILE_HASHES = {
    "src/mdtest.c": "b12579718efde10ce145495dcaba1c08aad9a740d6f516b66a1063317ed89fc2",
    "src/mdtest-main.c": "8b59f250f0edb2e91be48590efa76c90b5b6a9f63e34432bd0d10afb87d56eba",
}


def _hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def get_case(case_id, verify=False):
    if case_id not in CASE_IDS:
        raise ValueError(f"Unknown mdtest case {case_id}")
    kind = "-F" if case_id == "M01" else "-D"
    body = (
        '"${BENCH_TOOL_ROOT:?}/bin/mpirun" -np 1 "${BENCH_TOOL_ROOT}/bin/mdtest" '
        f'-a POSIX {kind} -n 512 -i 1 -C -T -r -w 0 -e 0 -z 0 -b 1 -d "$PWD/mdtest-data"'
    )
    result = {
        "id": case_id,
        "body": body,
        "command": body,
        "exec_argv": ["/bin/bash", "-o", "pipefail", "-c", body],
        "setup": "",
        "setup_argv": ["/bin/bash", "-c", ":"],
        "starting_view": "empty",
        "environment": {
            "LANG": "C",
            "LC_ALL": "C",
            "OMPI_ALLOW_RUN_AS_ROOT": "1",
            "OMPI_ALLOW_RUN_AS_ROOT_CONFIRM": "1",
        },
        "verifier": None,
        "required_tools": ["bin/mdtest", "bin/mpirun"],
        "provenance": {
            "repository": SOURCE_URL,
            "source_commit": SOURCE_SHA,
            "source_file_sha256": dict(SOURCE_FILE_HASHES),
            "source_paths": ["src/mdtest.c", "src/mdtest-main.c"],
            "workload_version": "one-rank-512-create-stat-remove-v1",
            "body_sha256": _hash(body),
            "setup_sha256": _hash(""),
            "entry_kind": "file" if case_id == "M01" else "directory",
            "ranks": 1,
            "entries": 512,
            "iterations": 1,
            "file_bytes": 0,
            "phases": ["create", "stat", "remove"],
        },
    }
    if verify:
        # mdtest removes its own test root. Empty Workspace is the surviving result.
        script = (
            'test -z "$(find . -mindepth 1 -print -quit)" && printf "VERIFY PASS\\n"'
        )
        result["verifier"] = script
        result["provenance"]["verification"] = {
            "version": "empty-after-remove-v1",
            "sha256": _hash(script),
        }
    return result


def parse_result(case_id, stdout, stderr="", exit_code=0):
    if case_id not in CASE_IDS:
        raise ValueError(f"Unknown mdtest case {case_id}")
    if exit_code != 0:
        raise ValueError(f"mdtest exited {exit_code}")
    if re.search(
        r"\b(?:ERROR|WARNING|unable to|failed to)\b", stdout + stderr, re.IGNORECASE
    ):
        raise ValueError("mdtest reported an error/warning; retain original output")
    noun = "files" if case_id == "M01" else "directories"
    if not re.search(rf"\b1 tasks, 512 {noun}\b", stdout):
        raise ValueError("missing exact one-rank/512-entry workload declaration")
    marker = "SUMMARY rate (in ops/sec): (of 1 iterations)"
    if marker not in stdout or "-- finished at" not in stdout:
        raise ValueError("missing complete single-iteration mdtest summary")
    summary = stdout.split(marker, 1)[1]
    prefix = "File" if case_id == "M01" else "Directory"
    phases = {}
    for upstream, name in [
        ("creation", "create"),
        ("stat", "stat"),
        ("removal", "remove"),
    ]:
        match = re.search(rf"^\s*{prefix} {upstream}\s+(.*)$", summary, re.MULTILINE)
        if not match:
            raise ValueError(f"missing mdtest {name} phase")
        try:
            values = [float(value) for value in match.group(1).split()]
        except ValueError as error:
            raise ValueError("malformed mdtest phase rate") from error
        if (
            len(values) != 4
            or any(not math.isfinite(value) or value < 0 for value in values)
            or values[2] <= 0
        ):
            raise ValueError("invalid mdtest phase rates")
        phases[name] = dict(zip(["max", "min", "mean", "stddev"], values))
    return {
        "tool": "mdtest",
        "ranks": 1,
        "entries": 512,
        "iterations": 1,
        "phase_rates": phases,
        "units": "ops/sec",
    }
