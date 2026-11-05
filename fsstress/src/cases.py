"""Pinned finite fsstress profile with explicit effective-work accounting."""

import hashlib
import json
import re
import shlex

CASE_IDS = ("S01",)
SOURCE_COMMIT = "31f7192f90a89a6f808a37c3a3cd30491bd50eba"
SOURCE_URL = "https://git.kernel.org/pub/scm/fs/xfs/xfstests-dev.git"
WEIGHTS = {
    "creat": 4,
    "mkdir": 2,
    "stat": 4,
    "rename": 2,
    "unlink": 2,
    "rmdir": 1,
    "link": 1,
    "symlink": 1,
    "readlink": 1,
    "read": 2,
    "write": 2,
    "truncate": 1,
}
EXPECTED_ERRNOS = {
    "creat": [17],
    "mkdir": [17],
    "link": [17],
    "symlink": [17],
    "rename": [17, 22, 39],
    "rmdir": [17, 39],
    "readlink": [22],
}
TOOL_ARGV = (
    "fsstress",
    "-d",
    "stress.data",
    "-p",
    "2",
    "-n",
    "512",
    "-l",
    "1",
    "-s",
    "1",
    "-z",
    *(word for name, weight in WEIGHTS.items() for word in ("-f", f"{name}={weight}")),
    "-v",
    "-V",
    "-o",
    "${BENCH_LOG_DIR}/fsstress.log",
)
SUMMARY = r"""import collections,json,re,sys
allowed=json.loads(sys.argv[2])
operations=set(json.loads(sys.argv[3]))
workers={str(i):{"attempts":0,"successful":0,"skipped":0,"expected_errors":0,"unexpected_errors":0} for i in range(2)}
seen=set(); counts=collections.Counter(); errors=collections.Counter(); details=[]
for path in sys.argv[4:]:
    for line in open(path,encoding="utf-8",errors="strict"):
        found=re.match(r"^([01])/(\d+): ([a-z]+)(?:\([^)]*\))? (.*)$",line.rstrip())
        if not found:
            if line.strip():
                raise SystemExit("unrecognized fsstress output: "+line[:160])
            continue
        worker,number,operation,detail=found.groups(); number=int(number)
        if operation not in operations:
            raise SystemExit("undeclared fsstress operation: "+operation)
        if detail.startswith(("add id=","del entry:","source entry:","target entry:")):
            continue
        key=(worker,number)
        if key in seen or not 0<=number<512:
            raise SystemExit("duplicate/out-of-range fsstress operation")
        seen.add(key); record=workers[worker]; record["attempts"]+=1; counts[operation]+=1
        if detail.startswith("- ") and ("no " in detail or "zero size" in detail):
            record["skipped"]+=1
            continue
        found=re.search(r" (\d+)$",detail)
        if not found:
            raise SystemExit("unrecognized fsstress outcome: "+line[:160])
        errnos=[int(found[1])]
        if operation=="creat" and " x:" in detail:
            found=re.search(r" x:\d+ (\d+) (\d+)$",detail)
            if not found:
                raise SystemExit("unrecognized creat result")
            errnos=[int(found[1]),int(found[2])]
        nonzero=[value for value in errnos if value]
        if not nonzero:
            record["successful"]+=1
        elif all(value in allowed.get(operation,[]) for value in nonzero):
            record["expected_errors"]+=1
        else:
            record["unexpected_errors"]+=1
            if len(details)<8: details.append(line.strip())
        for value in nonzero: errors[operation+":"+str(value)]+=1
result={"tool_exit_code":int(sys.argv[1]),"workers":workers,"operation_counts":dict(counts),
        "errno_counts":dict(errors),"unexpected_details":details}
print("FSSTRESS_RESULT "+json.dumps(result,sort_keys=True,separators=(",",":")))
"""


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def get_case(case_id, verify=False):
    if case_id not in CASE_IDS:
        raise ValueError(f"Unknown fsstress case: {case_id}")
    if verify:
        raise NotImplementedError(
            "Independent committed-result fsstress proof is unavailable; intrinsic reporting remains enabled"
        )
    flags = shlex.join(TOOL_ARGV[1:-2])
    body = f"""logdir=$(mktemp -d /tmp/fsstress-S01.XXXXXX) || exit 1
"${{BENCH_TOOL_ROOT:?set BENCH_TOOL_ROOT}}/bin/fsstress" {flags} -o "$logdir/fsstress.log"
tool_rc=$?
python3 -c {shlex.quote(SUMMARY)} "$tool_rc" {shlex.quote(json.dumps(EXPECTED_ERRNOS))} {shlex.quote(json.dumps(list(WEIGHTS)))} "$logdir/fsstress.log.0" "$logdir/fsstress.log.1"
summary_rc=$?
if [ "$tool_rc" -ne 0 ] || [ "$summary_rc" -ne 0 ]; then
  tail -n 10 "$logdir"/fsstress.log* >&2
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
        "supported_platforms": ["linux"],
        "unavailable_reason": "Pinned upstream requires Linux headers; native macOS is unsupported without porting",
        "verifier": None,
        "provenance": {
            "upstream": SOURCE_URL,
            "source_commit": SOURCE_COMMIT,
            "source_path": "ltp/fsstress.c",
            "source_sha256": "2af909ea454d1b0b122891d045ca270b6d4ad9c047b765fc5ee8dc58032521a3",
            "workload_version": "fsstress-S01-v1",
            "tool_argv": list(TOOL_ARGV),
            "body_sha256": _sha(body),
            "command_sha256": _sha(body),
            "setup_sha256": _sha(""),
            "summarizer_sha256": _sha(SUMMARY),
            "operation_weights": dict(WEIGHTS),
            "expected_errno_by_operation": EXPECTED_ERRNOS,
            "bounds": {
                "operations_per_process": 512,
                "processes": 2,
                "max_write_bytes_per_operation": 131072,
                "max_requested_write_bytes": 134217728,
                "max_logical_file_bytes": 603979776,
                "max_created_entries": 1028,
            },
            "logs": "Owned Sandbox /tmp; compact summary included in Exec, logs excluded from LayerFS Commit",
        },
    }


def parse_result(case_id, stdout, stderr="", exit_code=0):
    if case_id not in CASE_IDS or exit_code != 0:
        raise ValueError(
            f"fsstress failed: case={case_id}, exit={exit_code}, stderr={stderr[:500]}"
        )
    lines = re.findall(r"^FSSTRESS_RESULT (.+)$", stdout, re.MULTILINE)
    if len(lines) != 1:
        raise ValueError("Exactly one complete fsstress summary is required")
    result = json.loads(lines[0])
    if result.get("tool_exit_code") != 0 or set(result.get("workers", {})) != {
        "0",
        "1",
    }:
        raise ValueError("Both fsstress workers must report completion")
    totals = {
        name: 0
        for name in (
            "attempts",
            "successful",
            "skipped",
            "expected_errors",
            "unexpected_errors",
        )
    }
    for record in result["workers"].values():
        if any(
            type(record.get(name)) is not int or record[name] < 0 for name in totals
        ):
            raise ValueError("Invalid fsstress accounting")
        if (
            record["attempts"] != 512
            or sum(record[name] for name in totals if name != "attempts") != 512
        ):
            raise ValueError(
                "Incomplete fsstress worker; parent exit alone is insufficient"
            )
        for name in totals:
            totals[name] += record[name]
    if totals["successful"] == 0 or totals["unexpected_errors"]:
        raise ValueError(
            "fsstress has zero effective work or unexpected operation errors: "
            + str(result.get("unexpected_details", []))
        )
    counts = result.get("operation_counts", {})
    if (
        set(counts) - set(WEIGHTS)
        or any(type(value) is not int or value < 0 for value in counts.values())
        or sum(counts.values()) != 1024
    ):
        raise ValueError("Incomplete fsstress operation histogram")
    return {
        "operations_requested": 1024,
        "operations_completed": totals["attempts"],
        "operations_effective": totals["successful"],
        "operations_skipped": totals["skipped"],
        "operations_expected_errors": totals["expected_errors"],
        "operations_unexpected_errors": 0,
        "operation_counts": counts,
        "errno_counts": result.get("errno_counts", {}),
        "workers": result["workers"],
        "intrinsic_checks": "PASS (upstream reporting; no data oracle)",
    }
