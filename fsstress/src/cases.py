"""Pinned finite fsstress profile with explicit effective-work accounting."""

import hashlib
import json
import re
import shlex

CASE_IDS = ("S01",)
SOURCE_COMMIT = "edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed"
SOURCE_URL = "https://github.com/billziss-gh/secfs.test"
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
    "creat": ["EEXIST"],
    "mkdir": ["EEXIST"],
    "link": ["EEXIST"],
    "symlink": ["EEXIST"],
    "rename": ["EEXIST", "EINVAL", "ENOTEMPTY"],
    "rmdir": ["EEXIST", "ENOTEMPTY"],
    "readlink": ["EINVAL"],
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
    "-c",
)
SUMMARY = r"""import collections,errno,json,os,re,sys
allowed=json.loads(sys.argv[2])
operations=set(json.loads(sys.argv[3]))
workers={str(i):{"attempts":0,"successful":0,"skipped":0,"expected_errors":0,"unexpected_errors":0} for i in range(2)}
seen=set(); counts=collections.Counter(); errors=collections.Counter(); details=[]
io_requests={name:{"operations":0,"requested_bytes":0,"max_requested_bytes":0} for name in ("read","write")}
if open(sys.argv[5],encoding="utf-8",errors="strict").read().strip():
    raise SystemExit("fsstress reported stderr; retain the exact log")
for path in sys.argv[4:5]:
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
        if operation in io_requests:
            request=re.search(r"\[(\d+),(\d+)\]",detail)
            if request:
                length=int(request[2]); record_io=io_requests[operation]
                if not 0<length<=os.sysconf("SC_PAGE_SIZE")*32:
                    raise SystemExit("invalid source-derived fsstress I/O request length")
                record_io["operations"]+=1; record_io["requested_bytes"]+=length
                record_io["max_requested_bytes"]=max(record_io["max_requested_bytes"],length)
        nonzero=[errno.errorcode.get(value,"ERRNO_"+str(value)) for value in errnos if value]
        if not nonzero:
            record["successful"]+=1
        elif all(value in allowed.get(operation,[]) or (
            sys.platform=="darwin" and operation=="link" and value=="ENOENT"
            and re.fullmatch(r"l[0-9a-f]+",detail.split()[0].rsplit("/",1)[-1])
        ) for value in nonzero):
            record["expected_errors"]+=1
        else:
            record["unexpected_errors"]+=1
            if len(details)<8: details.append(line.strip())
        for value in nonzero: errors[operation+":"+value]+=1
result={"tool_exit_code":int(sys.argv[1]),"workers":workers,"operation_counts":dict(counts),
        "errno_counts":dict(errors),"unexpected_details":details,"io_requests":io_requests,
        "platform":sys.platform,"page_size_bytes":os.sysconf("SC_PAGE_SIZE")}
print("FSSTRESS_RESULT "+json.dumps(result,sort_keys=True,separators=(",",":")))
if any(record["attempts"]!=512 or record["successful"]==0 or record["unexpected_errors"] for record in workers.values()):
    raise SystemExit(1)
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
    flags = shlex.join(TOOL_ARGV[1:])
    body = f"""logdir=$(mktemp -d /tmp/fsstress-S01.XXXXXX) || exit 1
"${{BENCH_TOOL_ROOT:?set BENCH_TOOL_ROOT}}/bin/fsstress" {flags} >"$logdir/stdout.log" 2>"$logdir/stderr.log"
tool_rc=$?
python3 -c {shlex.quote(SUMMARY)} "$tool_rc" {shlex.quote(json.dumps(EXPECTED_ERRNOS))} {shlex.quote(json.dumps(list(WEIGHTS)))} "$logdir/stdout.log" "$logdir/stderr.log"
summary_rc=$?
if [ "$tool_rc" -ne 0 ] || [ "$summary_rc" -ne 0 ]; then
  tail -n 10 "$logdir"/*.log >&2
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
        "verifier": None,
        "provenance": {
            "upstream": SOURCE_URL,
            "source_commit": SOURCE_COMMIT,
            "source_path": "fsstress/fsstress.c",
            "source_sha256": "e2f6e7c5cce99d22117bf61b5aeb73505bd8fd114bca90f5b5a6ec91ef10b833",
            "workload_version": "fsstress-S01-v2",
            "tool_argv": list(TOOL_ARGV),
            "body_sha256": _sha(body),
            "command_sha256": _sha(body),
            "setup_sha256": _sha(""),
            "summarizer_sha256": _sha(SUMMARY),
            "operation_weights": dict(WEIGHTS),
            "expected_errno_by_operation": EXPECTED_ERRNOS,
            "darwin_symlink_link_exception": {
                "operation": "link",
                "errno": "ENOENT",
                "source_basename": "l[0-9a-f]+",
                "reason": "Apple link follows the final source symlink; upstream random target can dangle",
                "source": "https://raw.githubusercontent.com/apple-oss-distributions/xnu/main/bsd/man/man2/link.2",
            },
            "bounds": {
                "operations_per_process": 512,
                "processes": 2,
                "max_write_bytes_per_operation": "32 * runtime page size",
                "max_requested_write_bytes": "1024 * 32 * runtime page size",
                "max_logical_file_bytes": "512 * (1048576 + 32 * runtime page size)",
                "registered_pages": {"darwin": 16384, "linux": 4096},
                "max_created_entries": 1028,
            },
            "logs": "Owned Sandbox /tmp stdout/stderr; line-buffered upstream records; compact strict per-child accounting included in Exec",
            "platform_variation": "libc random() and page-size-derived lengths can differ; identical argv/counts do not claim identical byte work",
            "retain_mutations": "-c disables upstream final cleanup before LayerFS Commit",
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
            or record["successful"] == 0
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
    requests = result.get("io_requests", {})
    page_size = result.get("page_size_bytes")
    if type(page_size) is not int or page_size not in (4096, 16384):
        raise ValueError("Unregistered fsstress page-size-derived profile")
    if result.get("platform") not in ("darwin", "linux"):
        raise ValueError("Unregistered fsstress platform")
    for operation in ("read", "write"):
        request = requests.get(operation, {})
        if set(request) != {
            "operations",
            "requested_bytes",
            "max_requested_bytes",
        } or any(type(value) is not int or value < 0 for value in request.values()):
            raise ValueError("Missing/invalid actual fsstress request-size accounting")
        if (
            request["operations"] > counts.get(operation, 0)
            or request["max_requested_bytes"] > page_size * 32
        ):
            raise ValueError(
                "Fsstress request accounting exceeds source-derived bounds"
            )
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
        "platform": result["platform"],
        "page_size_bytes": page_size,
        "io_requests": requests,
        "io_request_scope": "upstream logged requested lengths, not transferred bytes",
        "intrinsic_checks": "PASS (upstream reporting; no data oracle)",
    }
