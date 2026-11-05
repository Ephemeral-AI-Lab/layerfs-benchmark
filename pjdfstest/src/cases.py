"""Unprivileged fixed upstream TAP selections; every assertion remains enabled."""

import hashlib
import re

CASE_IDS = ("P01", "P02", "P03", "P04")
SOURCE_SHA = "85a8aea9e685999ef0540392fd80535f873d7ff7"
SOURCE_URL = "https://github.com/pjd/pjdfstest"
SOURCE_FILE_HASHES = {
    "pjdfstest.c": "a6c354f2c42015a1d2d538ea4276091278a1e4955bb6a10d0ec9b9838f24a23e",
    "tests/open/04.t": "a4553cbafb239bc76adf176c1beb89b3e46b794116b8718ec00fb02b328c0b6a",
    "tests/rename/18.t": "3013e55c7547efd9ab9caf98d0df8a18bf804f5e40ccd4bbff9111f660d9d3d6",
    "tests/chmod/02.t": "dd0c9370bd26607984640fc78f0a0cc835dd9a0b93bae4f1d882c62fa8063601",
    "tests/symlink/00.t": "abad2f9fb84cc558995794280aeac868e7be4bf9fbc94b5b51cb991bb6bee24a",
    "tests/misc.sh": "de3752eb5e02034395d4cc8a0d4053190bf28ae083205f98e34438380e7fb5d1",
    "tests/conf": "2c9cdeaa47344b15d6d6690fe2b0b45719b85f75f72d976046d23fc141b57b23",
}
SCRIPTS = {
    "P01": "open/04.t",
    "P02": "rename/18.t",
    "P03": "chmod/02.t",
    "P04": "symlink/00.t",
}
PLANS = {"P01": 4, "P02": 6, "P03": 5, "P04": 14}


def _hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def get_case(case_id, verify=False):
    if case_id not in CASE_IDS:
        raise ValueError(f"Unknown pjdfstest case {case_id}")
    body = (
        'uid=$(id -u) && gid=$(id -g) && test "$uid" -gt 0 && test "$gid" -gt 0 && '
        'printf "PJDFSTEST_IDENTITY uid=%s gid=%s\\n" "$uid" "$gid" && '
        f'prove -rv "${{BENCH_TOOL_ROOT:?}}/pjdfstest/tests/{SCRIPTS[case_id]}"'
    )
    result = {
        "id": case_id,
        "body": body,
        "command": body,
        "exec_argv": ["/bin/bash", "-o", "pipefail", "-c", body],
        "setup": "",
        "starting_view": "empty",
        "environment": {"LANG": "C", "LC_ALL": "C"},
        "verifier": None,
        "requires_root": False,
        "requires_nonroot": True,
        "required_tools": ["pjdfstest/pjdfstest", "prove", "openssl", "perl"],
        "provenance": {
            "repository": SOURCE_URL,
            "source_commit": SOURCE_SHA,
            "source_file_sha256": dict(SOURCE_FILE_HASHES),
            "scripts": ["tests/" + SCRIPTS[case_id]],
            "workload_version": "fixed-posix-tap-unprivileged-subset-v2",
            "body_sha256": _hash(body),
            "setup_sha256": _hash(""),
            "expected_assertions_darwin_linux": PLANS[case_id],
            "root_required": False,
            "privilege_profile": "selected-upstream-scripts-unprivileged-v2",
            "identity_contract": {
                "effective_uid": ">0",
                "effective_gid": ">0",
                "switching": "none; inherited ordinary command identity",
                "evidence": "one PJDFSTEST_IDENTITY marker from id -u/id -g, parsed into tool_metrics",
                "helper_defaults": "uid=-1 and gids=NULL; selected scripts pass no -u/-g",
            },
            "full_upstream_root_suite": "outside selected subset",
            "script_selection": "Small fixed selections; no FIFO/device nodes or ownership changes",
        },
    }
    if verify:
        script = (
            'test -z "$(find . -mindepth 1 -print -quit)" && printf "VERIFY PASS\\n"'
        )
        result["verifier"] = script
        result["provenance"]["verification"] = {
            "version": "empty-after-script-v1",
            "sha256": _hash(script),
        }
    return result


def parse_result(case_id, stdout, stderr="", exit_code=0):
    if case_id not in CASE_IDS:
        raise ValueError(f"Unknown pjdfstest case {case_id}")
    if exit_code != 0:
        raise ValueError(f"pjdfstest/prove exited {exit_code}; preserve all TAP output")
    identities = re.findall(
        r"^PJDFSTEST_IDENTITY uid=([0-9]+) gid=([0-9]+)$", stdout, re.MULTILINE
    )
    if len(identities) != 1 or any(int(value) <= 0 for value in identities[0]):
        raise ValueError("missing/ambiguous ordinary effective UID/GID evidence")
    effective_uid, effective_gid = (int(value) for value in identities[0])
    if "Bail out!" in stdout or "Result: PASS" not in stdout:
        raise ValueError("missing successful complete TAP harness result")
    plans = re.findall(
        r"^1\.\.(\d+)(?:\s+#\s*(.*))?\s*$", stdout, re.MULTILINE | re.IGNORECASE
    )
    if len(plans) != 1 or int(plans[0][0]) != PLANS[case_id]:
        raise ValueError("missing/mismatched frozen TAP plan")
    counts = {"pass": 0, "fail": 0, "skip": 0, "todo": 0}
    numbers = []
    for match in re.finditer(r"^(not )?ok\s+(\d+)([^\n]*)$", stdout, re.MULTILINE):
        numbers.append(int(match[2]))
        suffix = match[3]
        if re.search(r"#\s*SKIP\b", suffix, re.IGNORECASE):
            counts["skip"] += 1
        elif re.search(r"#\s*TODO\b", suffix, re.IGNORECASE):
            counts["todo"] += 1
        elif match[1]:
            counts["fail"] += 1
        else:
            counts["pass"] += 1
    if numbers != list(range(1, PLANS[case_id] + 1)):
        raise ValueError("missing/duplicate/out-of-order TAP assertions")
    if counts["fail"] or not counts["pass"]:
        raise ValueError(f"failed or all-skipped/TODO selection: {counts}")
    return {
        "tool": "pjdfstest",
        "execution_identity": {
            "effective_uid": effective_uid,
            "effective_gid": effective_gid,
            "switched": False,
        },
        "scripts": [SCRIPTS[case_id]],
        "assertions": sum(counts.values()),
        "tap": counts,
        **counts,
        "upstream_result": "PASS",
    }
