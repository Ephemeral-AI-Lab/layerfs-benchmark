#!/usr/bin/env python3
"""Record one host baseline: the frozen script on plain APFS, outside LayerFS.

The host baseline is not a LayerFS row. It runs the same `cases.py` body, with
the same pinned bash, `sha256sum` wrapper and PATH as the native rows, on an
ordinary APFS directory that no Store or Workspace owns, and records the
script's own twelve scenario times once per campaign. The report subtracts it
from the native column to show LayerFS-attributable time.

Run it once per campaign, after the campaign config exists and before or after
the rows (the rows never read it):

    python3 fs-bench-cloudflare-computer/src/host.py --environment $E --cache $C

It writes `<cache>/host-baseline.json` and exits 0 only when the twelve
scenarios parsed. A directory that is not proven plain APFS outside LayerFS is
NOT_RUN with a reason, never a guessed number.
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cases  # noqa: E402 - the suite's frozen workload

RECORD = "host-baseline"
TIMEOUT_S = 120  # the whole script on plain APFS is ~15 s; no longer than 120 s
NETWORK_FILESYSTEMS = ("nfs", "afpfs", "smbfs", "autofs", "webdav")
LOCAL_FILESYSTEMS = ("apfs",)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def tool_environment(config):
    """The native rows' tool environment, or the host_baseline override."""
    block = config.get("host_baseline") or {}
    if block.get("tool_environment"):
        return dict(block["tool_environment"])
    return dict(((config.get("machines") or {}).get("native") or {}).get("tool_environment") or {})


def filesystem(directory):
    """Ask `mount` what backs this directory; never take the caller's word."""
    target = Path(str(directory)).expanduser().resolve()
    listing = subprocess.run(
        ["mount"], capture_output=True, text=True, check=False, timeout=30,
    )
    best = {"type": "", "source": "", "mountpoint": "", "mount_exit": listing.returncode}
    for line in listing.stdout.splitlines():
        source, separator, rest = line.partition(" on ")
        if not separator:
            continue
        mountpoint, opened, tail = rest.partition(" (")
        if not opened:
            continue
        kind = tail.split(",")[0].strip()
        covered = mountpoint == "/" or str(target) == mountpoint or str(target).startswith(mountpoint.rstrip("/") + "/")
        if covered and len(mountpoint) >= len(best["mountpoint"]):
            best = {
                "type": kind,
                "source": source,
                "mountpoint": mountpoint,
                "mount_exit": listing.returncode,
            }
    return best


def layerfs_paths(config, cache):
    """Directories this campaign owns; a host sample must sit outside all of them."""
    owned = [config.get("home"), config.get("empty_source"), cache]
    owned += [config["environment"].get("XDG_CACHE_HOME")] if config.get("environment") else []
    for machine in (config.get("machines") or {}).values():
        owned.append(machine.get("store"))
        owned.append(machine.get("home"))
    return [Path(str(item)).expanduser().resolve() for item in owned if item]


def preflight(directory, config, cache):
    """Prove the target is plain APFS outside LayerFS, or say why it is not."""
    target = Path(str(directory)).expanduser()
    if platform.system() != "Darwin":
        return {"ok": False, "reason": f"APFS check needs macOS, not {platform.system()}"}
    if not target.is_dir():
        return {"ok": False, "reason": f"{target} is not an existing directory"}
    target = target.resolve()
    for owned in layerfs_paths(config, cache):
        if target == owned or owned in target.parents:
            return {
                "ok": False,
                "reason": f"{target} is inside {owned}, which this campaign's LayerFS owns",
            }
    facts = filesystem(target)
    source = facts["source"]
    if source.startswith(("127.0.0.1:", "localhost:")):
        return {
            "ok": False,
            "reason": f"{target} comes from {source}, a LayerFS NFS mount, not local APFS",
            "details": facts,
        }
    if facts["type"] in NETWORK_FILESYSTEMS or ":" in source or source.startswith("//"):
        return {
            "ok": False,
            "reason": f"{target} is mounted from {source or 'a network source'} ({facts['type']}), not local APFS",
            "details": facts,
        }
    if facts["type"] not in LOCAL_FILESYSTEMS:
        return {
            "ok": False,
            "reason": f"{target} is {facts['type'] or 'unknown'}, not apfs",
            "details": facts,
        }
    return {"ok": True, "reason": "", "details": {**facts, "target": str(target)}}


def run_body(directory, environment):
    """Run the native rows' byte-identical body, with the same bash and PATH."""
    argv = ["/bin/bash", "-o", "pipefail", "-c", cases.LAYERFS_BODY]
    env = dict(os.environ, **cases.ENVIRONMENT, **environment)
    started = time.monotonic_ns()
    try:
        done = subprocess.run(
            argv, cwd=str(directory), env=env, capture_output=True, text=True,
            timeout=TIMEOUT_S, check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "exit_code": None,
            "stdout": "",
            "stderr": f"fs-bench.sh did not finish within {TIMEOUT_S} s",
            "elapsed_ns": time.monotonic_ns() - started,
        }
    return {
        "exit_code": done.returncode,
        "stdout": done.stdout,
        "stderr": done.stderr,
        "elapsed_ns": time.monotonic_ns() - started,
    }

def record(config, cache, directory=None):
    """Measure one host sample and return the receipt for host-baseline.json."""
    cache = Path(cache)
    environment = tool_environment(config)
    block = config.get("host_baseline") or {}
    target = directory or block.get("directory") or ""
    body_sha256_placeholder = cases.sha256(cases.LAYERFS_BODY)
    receipt = {
        "record": RECORD,
        "source_sha": config.get("source_sha"),
        "campaign_id": config.get("campaign_id"),
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
        "directory": str(Path(str(target)).expanduser()) if target else "",
        "filesystem": "",
        "tool_environment": dict(environment),
        "script_sha256": "",
        "body_sha256": body_sha256_placeholder,
        "settings": dict(cases.SETTINGS),
        "scenarios": [],
        "sum_ns": None,
        "one_sample": True,
        "status": "NOT_RUN",
        "reason": "",
        "elapsed_ns": None,
    }
    if not target:
        receipt["reason"] = "no host_baseline.directory in the config and no --directory given"
        return receipt
    facts = preflight(target, config, cache)
    receipt["filesystem"] = "apfs, not NFS" if facts["ok"] else ""
    receipt["preflight"] = facts.get("details", {})
    if not facts["ok"]:
        receipt["reason"] = facts["reason"]
        return receipt
    receipt["directory"] = facts["details"]["target"]
    tools = Path(environment.get("BENCH_TOOL_ROOT", ""))
    script = tools / "fs-bench.sh"
    if not script.is_file():
        receipt["reason"] = f"{script} is missing; set BENCH_TOOL_ROOT to the pinned tools"
        return receipt
    receipt["script_sha256"] = sha256_file(script)
    if receipt["script_sha256"] != cases.SCRIPT_SHA256:
        receipt["reason"] = f"{script} is not the frozen script ({receipt['script_sha256']})"
        return receipt
    bash = shutil.which("bash", path=environment.get("PATH") or os.environ.get("PATH"))
    if bash:
        receipt["tool_environment"]["bash"] = bash
        receipt["tool_environment"]["bash_sha256"] = sha256_file(bash)
    else:
        receipt["reason"] = "no bash on the configured PATH"
        return receipt
    run = run_body(receipt["directory"], environment)
    receipt["elapsed_ns"] = run["elapsed_ns"]
    try:
        metrics = cases.parse_result("B01", run["stdout"], run["stderr"], run["exit_code"])
    except ValueError as error:
        receipt["status"] = "FAIL"
        receipt["reason"] = str(error)[:500]
        return receipt
    receipt["scenarios"] = metrics["scenarios"]
    receipt["sum_ns"] = metrics["sum_ns"]
    receipt["status"] = "PASS"
    return receipt


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def load(path, source_sha):
    """Read a recorded sample for the report; never invent one.

    Returns `{"available": bool, "reason": str, ...}`. Anything short of a PASS
    sample with all twelve scenarios at the report's product commit is
    unavailable, and the reason travels with it.
    """
    try:
        value = json.loads(Path(path).read_text())
    except (OSError, TypeError, ValueError) as error:
        return {"available": False, "path": str(path), "reason": f"host baseline unreadable: {error}"}
    if not isinstance(value, dict) or value.get("record") != RECORD:
        return {"available": False, "path": str(path), "reason": "not a host-baseline record"}
    if value.get("status") != "PASS":
        return {
            "available": False,
            "path": str(path),
            "campaign_id": value.get("campaign_id"),
            "reason": f"host sample was {value.get('status')}: {value.get('reason') or 'no reason'}",
        }
    if value.get("source_sha") != source_sha:
        return {
            "available": False,
            "path": str(path),
            "campaign_id": value.get("campaign_id"),
            "reason": (
                f"host sample measured LayerFS `{value.get('source_sha')}`, "
                f"not `{source_sha}`"
            ),
        }
    scenarios = value.get("scenarios")
    if not isinstance(scenarios, list) or [item.get("scenario") for item in scenarios] != list(cases.SCENARIOS):
        return {
            "available": False,
            "path": str(path),
            "campaign_id": value.get("campaign_id"),
            "reason": "host sample does not have the frozen twelve scenarios",
        }
    times = {item["scenario"]: item["ns"] for item in scenarios}
    if any(
        isinstance(ns, bool) or not isinstance(ns, int) or ns <= 0 or ns == cases.SATURATED_NS
        for ns in times.values()
    ):
        return {
            "available": False,
            "path": str(path),
            "campaign_id": value.get("campaign_id"),
            "reason": "host sample has an invalid scenario time",
        }
    return {
        "available": True,
        "path": str(path),
        "campaign_id": value.get("campaign_id"),
        "measured_at": value.get("measured_at"),
        "directory": value.get("directory"),
        "filesystem": value.get("filesystem"),
        "platform": value.get("platform"),
        "tool_environment": value.get("tool_environment") or {},
        "scenarios": times,
        "sum_ns": value.get("sum_ns") or sum(times.values()),
        "reason": "",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", type=Path, required=True, help="campaign config")
    parser.add_argument("--cache", type=Path, required=True, help="campaign cache directory")
    parser.add_argument("--directory", type=Path, help="override host_baseline.directory")
    parser.add_argument("--force", action="store_true", help="replace an earlier sample")
    args = parser.parse_args()
    config = json.loads(args.environment.read_text())
    output = args.cache / "host-baseline.json"
    if output.exists() and not args.force:
        parser.error(f"{output} already exists; one host sample per campaign")
    receipt = record(config, args.cache, args.directory)
    save(output, receipt)
    print(output)
    if receipt["status"] != "PASS":
        print(f"host baseline {receipt['status']}: {receipt['reason']}", file=sys.stderr)
        return 1
    print(f"host baseline PASS: {len(receipt['scenarios'])} scenarios, {receipt['sum_ns'] / 1_000_000:,.1f} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
