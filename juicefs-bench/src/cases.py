"""Frozen JuiceFS v1.4.2 workload and strict result validation."""
import hashlib
import math
import re

CASE_IDS = ("J01",)
IMPLEMENTED_CASES = CASE_IDS
WORKLOAD_VERSION = "juicefs-bench-v1"
TOOL_VERSION = "1.4.2"
SOURCE_COMMIT = "46af7afa9f819b8c9ddafd475fb828d22fe9dd17"
ARCHIVE_SHA256 = "19f72a30d3642a2f7971c8c4a31d2647de62f19520716e85c3a777de5f4c9036"
METRICS = (
    ("Write big file", "MiB/s", "s/file"),
    ("Read big file", "MiB/s", "s/file"),
    ("Write small file", "files/s", "ms/file"),
    ("Read small file", "files/s", "ms/file"),
    ("Stat file", "files/s", "ms/file"),
)
HEADER = "BlockSize: 1.0 MiB, BigFileSize: 1.0 GiB, SmallFileSize: 128 KiB, SmallFileCount: 100, NumThreads: 4"
BODY = """set -euo pipefail
tool=/usr/local/bin/juicefs
printf '%s  %s\\n' "${JUICEFS_SHA256:?pinned JuiceFS hash required}" "$tool" | sha256sum -c --quiet
export SKIP_DROP_CACHES=true
exec "$tool" bench . -p 4 --block-size 1 --big-file-size 1024 --small-file-size 128 --small-file-count 100
"""


def get_case(case_id, verify=False):
    if case_id not in CASE_IDS:
        raise ValueError(f"unknown JuiceFS case: {case_id}")
    if verify:
        raise ValueError("no independent verifier: JuiceFS bench deletes its files")
    return {
        "id": case_id, "body": BODY, "command": BODY, "setup": "",
        "exec_argv": ["/bin/bash", "-o", "pipefail", "-c", BODY],
        "environment": {"LANG": "C", "LC_ALL": "C", "SKIP_DROP_CACHES": "true"},
        "supported_platforms": ["linux"], "starting_view": "empty", "verifier": None,
        "performance_budget_s": 25,
        "provenance": {
            "repository": "https://github.com/juicedata/juicefs", "tag": "v1.4.2",
            "source_commit": SOURCE_COMMIT,
            "archive_sha256": ARCHIVE_SHA256, "workload_version": WORKLOAD_VERSION,
            "threads": 4, "big_file_mib": 1024, "block_mib": 1,
            "small_file_kib": 128, "small_file_count_per_thread": 100,
            "skip_drop_caches": True,
            "body_sha256": hashlib.sha256(BODY.encode()).hexdigest(),
            "command_sha256": hashlib.sha256(BODY.encode()).hexdigest(),
        },
    }


def parse_result(case_id, stdout, stderr="", exit_code=0):
    if case_id not in CASE_IDS or exit_code != 0:
        raise ValueError(f"invalid case or JuiceFS exit: {case_id}, {exit_code}")
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", stdout + "\n" + stderr)
    if "Failed to cleanup" in text or "Benchmark finished!" not in text:
        raise ValueError("benchmark did not complete and clean up successfully")
    # humanize.IBytes presentation changed across upstream versions; accept only
    # equivalent fixed values, never different sizes or worker counts.
    header = re.search(r"BlockSize: (.*), BigFileSize: (.*), SmallFileSize: (.*), SmallFileCount: (\d+), NumThreads: (\d+)", text)
    if not header or header.groups() not in {
        ("1.0 MiB", "1.0 GiB", "128 KiB", "100", "4"),
        ("1 MiB", "1 GiB", "128 KiB", "100", "4"),
    }:
        raise ValueError("missing or mismatched JuiceFS configuration header")
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if cells and cells[0] in {m[0] for m in METRICS}:
            rows.append(cells)
    if [r[0] for r in rows] != [m[0] for m in METRICS]:
        raise ValueError("missing, duplicated or reordered benchmark metrics")
    metrics = []
    for row, (name, unit, cost_unit) in zip(rows, METRICS):
        if len(row) != 3:
            raise ValueError(f"malformed metric: {name}")
        value = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?) " + re.escape(unit), row[1])
        cost = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?) " + re.escape(cost_unit), row[2])
        if not value or not cost:
            raise ValueError(f"incorrect number or unit: {name}")
        v, c = float(value[1]), float(cost[1])
        if not math.isfinite(v) or v <= 0 or not math.isfinite(c) or c < 0:
            raise ValueError(f"invalid metric value: {name}")
        metrics.append({"name": name, "value": v, "unit": unit, "cost": c, "cost_unit": cost_unit})
    return {"tool": "juicefs bench", "version": TOOL_VERSION, "metrics": metrics,
            "cache_eligibility": "INELIGIBLE", "correctness": "UNVERIFIED"}
