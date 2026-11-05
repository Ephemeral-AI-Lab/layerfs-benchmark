"""One finite, unmodified upstream fsx treatment and its intrinsic result."""

import hashlib
import json
import re
import shlex

CASE_IDS = ("X01",)
SOURCE_COMMIT = "edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed"
SOURCE_URL = "https://github.com/billziss-gh/secfs.test"
TOOL_ARGV = (
    "fsx",
    "-S",
    "1",
    "-N",
    "1000",
    "-F",
    "8388608",
    "-o",
    "65536",
    "-R",
    "-W",
    "-v",
    "-P",
    "${BENCH_LOG_DIR}",
    "fsx.data",
)
SUMMARY = r"""import collections,json,re,sys
text=open(sys.argv[2],encoding="utf-8",errors="strict").read()
completed=re.findall(r"^All operations - (\d+) - completed A-OK!$",text,re.M)
records=re.findall(r"^(\d+): (.*)$",text,re.M)
skips=re.findall(r"^skipping (zero size (?:read|write)|seek/read past end of file)$",text,re.M)
counts=collections.Counter()
seen=set()
for number,detail in records:
    number=int(number)
    if number in seen or not 1<=number<=1000:
        raise SystemExit("duplicate/out-of-range fsx record")
    seen.add(number)
    operation=detail.split()[0]
    if operation not in {"READ","WRITE","TRUNCATE"}:
        raise SystemExit("undeclared fsx operation: "+operation)
    counts[operation]+=1
counts["SKIPPED"]=len(skips)
result={"tool_exit_code":int(sys.argv[1]),"completed":int(completed[0]) if len(completed)==1 else None,
        "records":len(records)+len(skips),"operation_counts":dict(counts),"intrinsic_checks":"fsx-size-and-read-consistency"}
print("FSX_RESULT "+json.dumps(result,sort_keys=True,separators=(",",":")))
"""


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def get_case(case_id, verify=False):
    if case_id not in CASE_IDS:
        raise ValueError(f"Unknown fsx case: {case_id}")
    if verify:
        raise NotImplementedError(
            "Independent committed-result fsx proof is unavailable; intrinsic checks remain enabled"
        )
    flags = shlex.join(TOOL_ARGV[1:-3])
    body = f"""logdir=$(mktemp -d /tmp/fsx-X01.XXXXXX) || exit 1
"${{BENCH_TOOL_ROOT:?set BENCH_TOOL_ROOT}}/bin/fsx" {flags} -P "$logdir" fsx.data >"$logdir/stdout"
tool_rc=$?
python3 -c {shlex.quote(SUMMARY)} "$tool_rc" "$logdir/stdout"
summary_rc=$?
if [ "$tool_rc" -ne 0 ] || [ "$summary_rc" -ne 0 ]; then
  tail -n 20 "$logdir/stdout" >&2
  exit 1
fi
rm -rf -- "$logdir"
"""
    return {
        "id": case_id,
        "body": body,
        "command": body,
        "exec_argv": ["/bin/bash", "-o", "pipefail", "-c", body],
        "setup": "",
        "starting_view": "empty",
        "environment": {"LANG": "C", "LC_ALL": "C"},
        "supported_platforms": ["darwin", "linux"],
        "required_tools": ["bin/fsx", "python3"],
        "verifier": None,
        "provenance": {
            "upstream": SOURCE_URL,
            "source_commit": SOURCE_COMMIT,
            "source_path": "fstools/src/fsx/fsx.c",
            "source_sha256": "94119d806ffe04ae96e5f90fbef78b41ae8303139a4f82212d699bdc2ed27d81",
            "workload_version": "fsx-X01-v2-secfs-portable",
            "supersedes": {
                "workload_version": "fsx-X01-v1",
                "source_commit": "31f7192f90a89a6f808a37c3a3cd30491bd50eba",
                "reason": "Owner-authorized unchanged portable upstream; previous Linux-only receipts retained",
            },
            "tool_argv": list(TOOL_ARGV),
            "body_sha256": _sha(body),
            "command_sha256": _sha(body),
            "setup_sha256": _sha(""),
            "summarizer_sha256": _sha(SUMMARY),
            "selection": "ordinary read/write/truncate; mapped I/O disabled, intrinsic size/read checks enabled",
            "data_element_bytes": 4,
            "logs": "Owned Sandbox /tmp; summary included in Exec, logs excluded from LayerFS Commit",
        },
    }


def parse_result(case_id, stdout, stderr="", exit_code=0):
    if case_id not in CASE_IDS or exit_code != 0:
        raise ValueError(
            f"fsx failed: case={case_id}, exit={exit_code}, stderr={stderr[:500]}"
        )
    lines = re.findall(r"^FSX_RESULT (.+)$", stdout, re.MULTILINE)
    if len(lines) != 1:
        raise ValueError("Exactly one complete fsx summary is required")
    result = json.loads(lines[0])
    if (
        result.get("tool_exit_code") != 0
        or result.get("completed") != 1000
        or result.get("records") != 1000
    ):
        raise ValueError("fsx did not complete its declared 1,000 operation slots")
    counts = result.get("operation_counts", {})
    if set(counts) - {"READ", "WRITE", "TRUNCATE", "SKIPPED"}:
        raise ValueError("Unexpected fsx operation")
    if (
        any(type(value) is not int or value < 0 for value in counts.values())
        or sum(counts.values()) != 1000
    ):
        raise ValueError("Invalid fsx effective operation accounting")
    effective = sum(counts.get(name, 0) for name in ("READ", "WRITE", "TRUNCATE"))
    if effective == 0:
        raise ValueError("fsx completed no effective filesystem operations")
    return {
        "operations_requested": 1000,
        "operations_completed": 1000,
        "operations_effective": effective,
        "operations_skipped": counts.get("SKIPPED", 0),
        "operation_counts": counts,
        "intrinsic_checks": "PASS",
    }
