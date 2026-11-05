"""Two-worker smallfile CLI workloads, with portable hostname and seed custody."""

import hashlib
import math
import re
import shlex

CASE_IDS = ("L01", "L02", "L03", "L04", "L05")
SOURCE_SHA = "aa2519de5bf0b3b383db2c31eacbf8ac4328e19c"
SOURCE_URL = "https://github.com/distributed-system-analysis/smallfile"
SOURCE_FILE_HASHES = {
    "smallfile_cli.py": "8b0c298b814632337acb6587ac39a66325b71a74b438775b5e7630f234affdbc",
    "parse.py": "d86e065e5356a5384fa97dfe7680416875a90c2e9bf8cc319245332bdf1bb9c9",
    "smallfile.py": "c2b5fe85af1caa99fe09c75c4638ac64968e68aa6d8b02305e446b5fe35a54f4",
    "multi_thread_workload.py": "d495bb52c976f6b15a4cc1cd756e03aefcfbdd964272d27ca514001d85c44d44",
    "output_results.py": "68a4637a11454ef3a58e359cf631a2e562f131defc20bc132cc219d6cadf2071",
    "sync_files.py": "15cfa14931a574e66681938171ef112ef8a729e2eb79d7d2833a1814682a1c29",
}
OPERATIONS = dict(zip(CASE_IDS, ["create", "read", "stat", "rename", "delete"]))
# Select multiprocessing's supported POSIX fork context before upstream imports;
# source remains unchanged. The same launcher is frozen for macOS and Linux.
LAUNCHER = (
    "import multiprocessing,os,runpy,sys; "
    "multiprocessing.set_start_method('fork'); "
    "script=sys.argv.pop(1); sys.path.insert(0,os.path.dirname(script)); "
    "runpy.run_path(script,run_name='__main__')"
)
FLAGS = (
    "--as-host bench --threads 2 --files 256 --file-size 4 --record-size 4 "
    "--files-per-dir 64 --dirs-per-dir 4 --file-size-distribution fixed "
    "--same-dir N --hash-into-dirs N --stonewall N --finish Y --fsync N "
    "--verify-read Y --response-times N --incompressible N --verbose N --pause 0 "
    "--auto-pause N --cleanup-delay-usec-per-file 0"
)


def _hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _command(operation):
    return (
        'mkdir -p "$PWD/.smallfile-tmp" "$PWD/smallfile-data" && export TMPDIR="$PWD/.smallfile-tmp" && '
        f'python3 -c {shlex.quote(LAUNCHER)} "${{BENCH_TOOL_ROOT:?}}/smallfile/smallfile_cli.py" '
        f'--operation {operation} --top "$PWD/smallfile-data" {FLAGS}'
    )


def get_case(case_id, verify=False):
    if case_id not in CASE_IDS:
        raise ValueError(f"Unknown smallfile case {case_id}")
    operation = OPERATIONS[case_id]
    body = _command(operation)
    setup = "" if case_id == "L01" else _command("create")
    result = {
        "id": case_id,
        "body": body,
        "command": body,
        "exec_argv": ["/bin/bash", "-o", "pipefail", "-c", body],
        "setup": setup,
        "setup_argv": ["/bin/bash", "-o", "pipefail", "-c", setup or ":"],
        "starting_view": "empty" if not setup else "smallfile-created-512x4096",
        "environment": {"LANG": "C", "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"},
        "verifier": None,
        "required_tools": ["python3", "smallfile/smallfile_cli.py"],
        "provenance": {
            "repository": SOURCE_URL,
            "source_commit": SOURCE_SHA,
            "source_file_sha256": dict(SOURCE_FILE_HASHES),
            "source_paths": [
                "smallfile_cli.py",
                "parse.py",
                "smallfile.py",
                "multi_thread_workload.py",
                "output_results.py",
            ],
            "workload_version": "two-worker-256x4k-as-host-v1",
            "body_sha256": _hash(body),
            "setup_sha256": _hash(setup),
            "launcher_sha256": _hash(LAUNCHER),
            "operation": operation,
            "workers": 2,
            "files_per_worker": 256,
            "bytes_per_file": 4096,
            "files_per_directory": 64,
            "directories_per_directory": 4,
            "hostname": "bench",
            "multiprocessing_context": "fork",
            "fixture_payload": "upstream create_biggest_buf(False), deterministic nonzero pattern; incompressible disabled",
            "seed_custody": "upstream time/thread seed files retained under Workspace .smallfile-tmp; fixed-size/unhashed data ignores random seed",
            "upstream_internal_check": "verify-read Y",
            "sync_semantics": "payload --fsync N; intrinsic upstream sync/pickle control-file fsync retained",
        },
    }
    if verify:
        # Exact paths are defined by the pinned upstream file-name generator.
        # Check the fixed data pattern independently, without importing the tool.
        script = _verifier(operation)
        result["verifier"] = script
        result["provenance"]["verification"] = {
            "version": "fixed-pattern-512-v1",
            "sha256": _hash(script),
        }
    return result


def _verifier(operation):
    destination = "file_dstdir" if operation == "rename" else "file_srcdir"
    count = 0 if operation == "delete" else 512
    code = f"""from pathlib import Path
import re
root = Path('smallfile-data/{destination}')
files = [p for p in root.rglob('*') if p.is_file() or p.is_symlink()]
assert len(files) == {count}, len(files)
expected = {{(tid, number) for tid in ['00', '01'] for number in range(1, 257)}} if {count} else set()
seen = set()
pattern = bytes(k % 128 for k in range(1024)).replace(bytes([92]), b'!') * 5
for path in files:
    assert not path.is_symlink(), str(path)
    match = re.fullmatch(r'_bench_(00|01)_([0-9]+)_', path.name)
    assert match, str(path)
    tid, number = match[1], int(match[2])
    assert (tid, number) not in seen, str(path)
    seen.add((tid, number))
    directory = number // 64
    folder = Path(f'd_{{directory:03}}') if directory < 4 else Path('d_001/d_000')
    assert path.parent == root / 'bench' / f'thrd_{{tid}}' / folder, str(path)
    offset = ((int(tid) + 1) * number) % 1024
    assert path.read_bytes() == pattern[offset:offset + 4096], str(path)
assert seen == expected
if '{operation}' == 'rename':
    assert not any(p.is_file() or p.is_symlink() for p in Path('smallfile-data/file_srcdir').rglob('*'))
print('VERIFY PASS')
"""
    return "python3 -c " + shlex.quote(code)


def parse_result(case_id, stdout, stderr="", exit_code=0):
    if case_id not in CASE_IDS:
        raise ValueError(f"Unknown smallfile case {case_id}")
    if exit_code != 0:
        raise ValueError(f"smallfile exited {exit_code}")
    if "Exception seen" in stdout + stderr or re.search(
        r"\b(?:Traceback|ERROR:)\b", stdout + stderr
    ):
        raise ValueError("smallfile reported a worker/launcher exception")
    threads = re.search(r"^total threads = (\d+)\s*$", stdout, re.MULTILINE)
    files = re.search(r"^total files = (\d+)\s*$", stdout, re.MULTILINE)
    if not threads or int(threads[1]) != 2 or not files or int(files[1]) != 512:
        raise ValueError("smallfile did not complete two workers and 512 files")
    workers = re.findall(
        r"^host = bench,thr = (\d+),elapsed = ([^,]+),files = (\d+),records = (\d+),status = (.+)$",
        stdout,
        re.MULTILINE,
    )
    if len(workers) != 2 or {worker[0] for worker in workers} != {"00", "01"}:
        raise ValueError("missing/duplicate smallfile per-worker results")
    expected_records = 256 if OPERATIONS[case_id] in {"create", "read"} else 0
    for tid, elapsed, completed, records, status in workers:
        if (
            status.strip() != "ok"
            or int(completed) != 256
            or int(records) != expected_records
            or not math.isfinite(float(elapsed))
            or float(elapsed) <= 0
        ):
            raise ValueError(f"smallfile worker {tid} incomplete/error")
    percent = re.search(
        r"^\s*([\d.]+)% of requested files processed", stdout, re.MULTILINE
    )
    if not percent or float(percent[1]) != 100.0:
        raise ValueError("smallfile stonewalled/incomplete work")
    rate = re.search(r"^files/sec = ([\d.eE+-]+)\s*$", stdout, re.MULTILINE)
    rate_value = float(rate[1]) if rate else None
    if rate_value is not None and (not math.isfinite(rate_value) or rate_value <= 0):
        raise ValueError("invalid smallfile upstream file rate")
    if rate_value is None and "test must run longer than a millisecond" not in stdout:
        raise ValueError(
            "missing smallfile file rate without upstream short-interval explanation"
        )
    return {
        "tool": "smallfile",
        "operation": OPERATIONS[case_id],
        "workers": 2,
        "files": 512,
        "files_per_second": rate_value,
        "rate_scope": "sum of upstream per-worker file counts / each worker's elapsed interval",
        "rate_unavailable_reason": "upstream interval below one millisecond"
        if rate_value is None
        else None,
        "complete_percent": 100.0,
        "worker_results": [
            dict(zip(["thread", "elapsed_s", "files", "records", "status"], row))
            for row in workers
        ],
    }


def parse_setup_result(case_id, stdout, stderr="", exit_code=0):
    if case_id not in CASE_IDS or case_id == "L01":
        raise ValueError(f"No prepared smallfile create input for {case_id}")
    return parse_result("L01", stdout, stderr, exit_code)
