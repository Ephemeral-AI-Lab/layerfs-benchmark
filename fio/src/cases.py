"""Four finite buffered-I/O jobs pinned to unchanged upstream fio 3.40."""

import hashlib
import json
import math
import shlex

CASE_IDS = ("F01", "F02", "F03", "F04")
IMPLEMENTED_CASES = CASE_IDS
SOURCE_COMMIT = "ff930c4653ae3952d6b09ab3ec89671aeabf2cbe"
SOURCE_TAG = "fio-3.40"
TOOL_VERSION = "fio-3.40"
WORKLOAD_VERSION = "fio-buffered-single-pass-v1"
ENVIRONMENT = {"LANG": "C", "LC_ALL": "C"}
TOOL = '"${BENCH_TOOL_ROOT:?BENCH_TOOL_ROOT must identify the pinned tools}/fio"'
PROFILES = {
    "F01": ("write", 64 * 1024 * 1024, 1024 * 1024),
    "F02": ("read", 64 * 1024 * 1024, 1024 * 1024),
    "F03": ("randwrite", 8 * 1024 * 1024, 4096),
    "F04": ("randread", 8 * 1024 * 1024, 4096),
}


def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()


def arguments(name, rw, size, block):
    """No allocation/sync additions, implicit read preparation or warm-up."""
    return [
        "--output-format=json",
        "--eta=never",
        f"--name={name}",
        "--filename=fio.data",
        f"--rw={rw}",
        f"--bs={block}",
        f"--size={size}",
        f"--io_size={size}",
        "--ioengine=sync",
        "--iodepth=1",
        "--numjobs=1",
        "--thread=1",
        "--direct=0",
        "--loops=1",
        "--time_based=0",
        "--ramp_time=0",
        "--pre_read=0",
        "--fallocate=none",
        "--create_on_open=1",
        "--create_fsync=0",
        f"--allow_file_create={0 if 'read' in rw else 1}",
        "--fsync=0",
        "--fdatasync=0",
        "--end_fsync=0",
        "--fsync_on_close=0",
        "--invalidate=0",
        "--unlink=0",
        "--randrepeat=1",
        "--randseed=1",
        "--random_generator=tausworthe64",
        "--softrandommap=0",
        "--buffer_pattern=0x5a",
        "--scramble_buffers=0",
        "--refill_buffers=0",
        "--clocksource=clock_gettime",
    ]


def invocation(name, rw, size, block):
    return TOOL + " " + shlex.join(arguments(name, rw, size, block))


def get_case(case_id, verify=False):
    if case_id not in PROFILES:
        raise ValueError(f"unknown fio case: {case_id}")
    rw, size, block = PROFILES[case_id]
    command = invocation(case_id, rw, size, block)
    # Read fixtures use the same pinned tool and pattern, before measurement.
    setup = invocation(case_id + "-setup", "write", size, block) if "read" in rw else ""
    result = {
        "id": case_id,
        "body": command,
        "command": command,
        "setup": setup,
        "exec_argv": ["/bin/bash", "-o", "pipefail", "-c", command],
        "environment": dict(ENVIRONMENT),
        "starting_view": "committed-base" if setup else "empty",
        "verifier": None,
        "provenance": {
            "repository": "https://github.com/axboe/fio",
            "source_commit": SOURCE_COMMIT,
            "source_tag": SOURCE_TAG,
            "source_path": "HOWTO.rst;options.c;filesetup.c",
            "workload_version": WORKLOAD_VERSION,
            "body_sha256": sha256(command),
            "command_sha256": sha256(command),
            "setup_sha256": sha256(setup),
            "profile": {
                "rw": rw,
                "size_bytes": size,
                "block_bytes": block,
                "io_bytes": size,
                "jobs": 1,
                "iodepth": 1,
                "seed": 1,
                "engine": "sync",
                "buffered": True,
                "buffer_pattern": "0x5a",
                "random_map": "upstream default enabled; softrandommap=0",
            },
        },
    }
    if setup:
        result["setup_command"] = setup
        result["setup_argv"] = ["/bin/bash", "-o", "pipefail", "-c", setup]
        result["provenance"]["setup_command_sha256"] = sha256(setup)
        result["provenance"]["setup_profile"] = {
            "rw": "write",
            "size_bytes": size,
            "block_bytes": block,
            "pattern": "nonzero repeated byte 0x5a",
        }
    if verify:
        # One streaming pass checks every byte; no Python/tool dependency in guest.
        result["verifier"] = f"""export LANG=C LC_ALL=C
set -o pipefail
fail() {{ echo "VERIFY FAIL $*"; exit 1; }}
shopt -s nullglob dotglob
entries=(*)
[ "${{#entries[@]}}" -eq 1 ] || fail "entry count"
[ -f fio.data ] && [ ! -L fio.data ] || fail "regular file"
[ "$(wc -c < fio.data | tr -d ' ')" = {size} ] || fail "file size"
[ "$(tr -d '\\132' < fio.data | wc -c | tr -d ' ')" = 0 ] || fail "nonzero pattern"
echo "VERIFY OK"
"""
        result["provenance"]["verification"] = {
            "version": "full-0x5a-v1",
            "sha256": sha256(result["verifier"]),
        }
    return result


def _number(value, name, *, positive=False):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(f"fio {name} missing or nonfinite")
    if value < 0 or (positive and value <= 0):
        raise ValueError(f"fio {name} has invalid value")
    return value


def parse_result(case_id, stdout, stderr="", exit_code=0):
    """Reject tool errors and zero/partial work; preserve upstream units."""
    if case_id not in PROFILES:
        raise ValueError(f"unknown fio case: {case_id}")
    if exit_code != 0:
        raise ValueError(f"fio exited {exit_code}: {stderr[:200]}")
    try:
        payload = json.loads(stdout)
    except (TypeError, ValueError) as error:
        raise ValueError("fio did not return complete JSON") from error
    if not isinstance(payload, dict) or payload.get("fio version") != TOOL_VERSION:
        raise ValueError("fio result does not match the pinned tool version")
    jobs = payload.get("jobs")
    if not isinstance(jobs, list) or len(jobs) != 1 or not isinstance(jobs[0], dict):
        raise ValueError("fio result must contain exactly one job")
    job = jobs[0]
    if job.get("jobname") != case_id or job.get("error") != 0:
        raise ValueError("fio job name or error outcome is invalid")
    rw, size, block = PROFILES[case_id]
    direction = "read" if "read" in rw else "write"
    other = "write" if direction == "read" else "read"
    io = job.get(direction)
    if not isinstance(io, dict):
        raise ValueError("fio direction metrics missing")  # noqa: TRY004 - malformed external data uses the parser ValueError contract
    if io.get("io_bytes") != size or io.get("total_ios") != size // block:
        raise ValueError("fio completed byte/I/O count differs from the frozen pass")
    if io.get("short_ios") != 0 or io.get("drop_ios") != 0:
        raise ValueError("fio reported short or dropped I/O")
    opposite = job.get(other)
    if not isinstance(opposite, dict) or opposite.get("io_bytes") != 0:
        raise ValueError("fio performed unexpected I/O in the opposite direction")
    options = job.get("job options", {})
    expected_options = {
        "rw": rw,
        "size": str(size),
        "io_size": str(size),
        "bs": str(block),
        "ioengine": "sync",
        "numjobs": "1",
        "iodepth": "1",
        "direct": "0",
    }
    if not isinstance(options, dict) or any(
        options.get(name) != expected for name, expected in expected_options.items()
    ):
        raise ValueError("fio effective job options differ from the frozen profile")
    latency = io.get("clat_ns")
    if not isinstance(latency, dict):
        raise ValueError("fio completion latency metrics missing")  # noqa: TRY004 - malformed external data uses the parser ValueError contract
    return {
        "tool": "fio",
        "version": TOOL_VERSION,
        "direction": direction,
        "io_bytes": size,
        "total_ios": size // block,
        "block_bytes": block,
        "runtime_ms": _number(io.get("runtime"), "runtime_ms"),
        "bandwidth_bytes_per_second": _number(
            io.get("bw_bytes"), "bw_bytes", positive=True
        ),
        "iops": _number(io.get("iops"), "iops", positive=True),
        "completion_latency_ns": {
            name: _number(latency.get(name), f"clat_ns.{name}")
            for name in ("min", "max", "mean", "stddev")
        },
        "tool_error": 0,
        "completed_pass": True,
    }
