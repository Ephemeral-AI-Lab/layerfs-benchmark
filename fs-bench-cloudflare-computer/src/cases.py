"""One case: Cloudflare Computer's frozen fs-bench.sh, twelve offline scenarios.

The script runs once per row in a LayerFS Workspace through `workspace exec`,
with `MOUNT` set to the Workspace root.
"""

import hashlib
import json
import shlex

CASE_IDS = ("B01",)
IMPLEMENTED_CASES = CASE_IDS
WORKLOAD_VERSION = "fs-bench-cloudflare-computer-v1"

REPOSITORY = "https://github.com/cloudflare/computer"
SOURCE_COMMIT = "de87919a4fd37242e960e13b7b3ba802d1eef0a0"
SOURCE_TREE = "4fb409d7e1356e1098439293d77d2fdc2dbf2190"
SOURCE_BLOB = "338dd9a85dde3ac7dcc8b4873cf29be2c1eb025c"
SOURCE_PATH = "script/fs-bench.sh"
SCRIPT_SHA256 = "0e2004339a9269b88c2de451d56575957477bde16b96a10cf1837519e37230ef"

# The twelve offline scenarios, in the script's own order. git clone, npm and
# Go need the network or tools outside the image and are not selected.
SCENARIOS = (
    "create 1000 files",
    "stat 1000 files",
    "rm 1000 files",
    "mkdir tree (10x10x10)",
    "find tree",
    "write 64 MiB",
    "copy 64 MiB",
    "read 64 MiB",
    "pure read 64 MiB",
    "pure copy 64 MiB",
    "overwrite 64 MiB",
    "git init + commit 100 files",
)
# Rows timed after an untimed prep step in the same fresh directory: their
# input was written by the script just before the clock starts.
OWN_WRITE_WARM = ("pure read 64 MiB", "pure copy 64 MiB", "overwrite 64 MiB")

# Upstream defaults are WARMUP=1 and RANDOMIZE_TARGETS=1; both are overridden.
SETTINGS = {
    "BASE": "",
    "REPS": "1",
    "WARMUP": "0",
    "RANDOMIZE_TARGETS": "0",
    "SCENARIOS": ",".join(SCENARIOS),
}
ENVIRONMENT = {"LANG": "C", "LC_ALL": "C"}
SATURATED_NS = 2**31 - 1  # mawk's %d ceiling; gawk in the image avoids it


def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()


def body(mount):
    """Check the script hash, run it once, print only its JSON on stdout.

    The script's human summary and errors go to stderr for the receipt. Its
    scratch output lives in /tmp, outside the measured filesystem.
    """
    settings = " ".join(f"{k}={shlex.quote(v)}" for k, v in SETTINGS.items())
    return f"""set -o pipefail
s="${{BENCH_TOOL_ROOT:?BENCH_TOOL_ROOT must identify the pinned tools}}/fs-bench.sh"
printf '%s  %s\\n' {SCRIPT_SHA256} "$s" | sha256sum -c --quiet || {{ echo "fs-bench.sh hash mismatch" >&2; exit 97; }}
out=$(mktemp -d /tmp/fbcc.XXXXXX) || exit 98
MOUNT={mount} {settings} OUTPUT_JSON="$out/result.json" bash "$s" >"$out/stdout" 2>"$out/stderr"
rc=$?
cat "$out/stdout" "$out/stderr" >&2
[ -f "$out/result.json" ] && cat "$out/result.json"
rm -rf "$out"
exit $rc
"""


LAYERFS_BODY = body('"$PWD"')


def get_case(case_id, verify=False):
    if case_id not in CASE_IDS:
        raise ValueError(f"unknown fs-bench-cloudflare-computer case: {case_id}")
    if verify:
        raise ValueError(
            "no independent verifier: every scenario removes its own directory"
        )
    return {
        "id": case_id,
        "body": LAYERFS_BODY,
        "command": LAYERFS_BODY,
        "setup": "",
        "exec_argv": ["/bin/bash", "-o", "pipefail", "-c", LAYERFS_BODY],
        "environment": dict(ENVIRONMENT),
        "starting_view": "empty",
        "verifier": None,
        "provenance": {
            "repository": REPOSITORY,
            "source_commit": SOURCE_COMMIT,
            "source_tree": SOURCE_TREE,
            "source_blob": SOURCE_BLOB,
            "source_path": SOURCE_PATH,
            "script_sha256": SCRIPT_SHA256,
            "workload_version": WORKLOAD_VERSION,
            "scenarios": list(SCENARIOS),
            "settings": dict(SETTINGS),
            "body_sha256": sha256(LAYERFS_BODY),
            "command_sha256": sha256(LAYERFS_BODY),
        },
    }


def parse_result(case_id, stdout, stderr="", exit_code=0):
    """Accept only one complete sample of every selected scenario."""
    if case_id not in CASE_IDS:
        raise ValueError(f"unknown fs-bench-cloudflare-computer case: {case_id}")
    if exit_code != 0:
        raise ValueError(f"fs-bench.sh exited {exit_code}: {stderr[-300:]}")
    try:
        payload = json.loads(stdout)
    except (TypeError, ValueError) as error:
        raise ValueError("fs-bench.sh did not return complete JSON") from error
    config = payload.get("config") if isinstance(payload, dict) else None
    if config != {
        "reps": 1,
        "warmup": 0,
        "randomizeTargets": 0,
        "mount": config.get("mount") if isinstance(config, dict) else None,
        "base": "",
    }:
        raise ValueError("fs-bench.sh config differs from REPS=1 WARMUP=0, no BASE")
    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("fs-bench.sh results missing")  # noqa: TRY004 - parser ValueError contract
    names = [item.get("scenario") for item in results if isinstance(item, dict)]
    if names != list(SCENARIOS):
        missing = [name for name in SCENARIOS if name not in names]
        raise ValueError(f"scenario rows differ from the frozen twelve; missing {missing}")
    scenarios = []
    for item in results:
        values = [item.get(key) for key in ("meanNs", "medianNs", "p95Ns", "minNs", "maxNs")]
        # "computerd" is the frozen script's fixed label for the MOUNT target.
        if (
            item.get("target") != "computerd"
            or item.get("samples") != 1
            or any(isinstance(v, bool) or not isinstance(v, int) for v in values)
            or len(set(values)) != 1
            or values[0] <= 0
            or values[0] == SATURATED_NS  # mawk's capped value, not a time
        ):
            raise ValueError(f"invalid single sample for {item.get('scenario')}")
        scenarios.append({"scenario": item["scenario"], "ns": values[0]})
    return {
        "tool": "fs-bench.sh",
        "script_sha256": SCRIPT_SHA256,
        "mount": config["mount"],
        "scenarios": scenarios,
        "sum_ns": sum(item["ns"] for item in scenarios),
    }
