"""Record one bounded public CLI operation; never replay an uncertain action."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def logical_snapshot(home):
    """Only management records/leases; never descend into mounted runtime trees."""
    home = Path(home)
    if not home.exists():
        return {"absent": True}
    result = {}
    def selected(path):
        if path.is_file():
            result[str(path.relative_to(home))] = {"sha256": digest(path), "mode": path.stat().st_mode & 0o777}
    for name in ["layerfs.json", "layerfs.lock"]:
        selected(home / name)
    for kind in ["machine", "store", "sandbox", "backup"]:
        base = home / kind
        if not base.is_dir():
            continue
        for entity in base.iterdir():
            if not entity.is_dir() or entity.name.startswith("."):
                continue
            for name in ["record.json", "worker.json", "control.json"]:
                selected(entity / name)
            if kind == "store":
                for lease in (entity / "open").glob("*"):
                    selected(lease)
                for project in (entity / "project").glob("*"):
                    for record in project.glob("*.json"):
                        selected(record)
            if kind == "sandbox":
                for record in (entity / "workspace").glob("*.json"):
                    selected(record)
                for record in (entity / "workspace").glob("*/exec/*.json"):
                    selected(record)
    return result


def invoke(config, command, output, case, expected=(), no_mutation=False, timeout=100, complete=None):
    if not command or command[0] not in {"doctor", "machine", "store", "project", "sandbox", "workspace", "branch", "backup", "help"}:
        raise ValueError("only public LayerFS command families are allowed")
    if not 0 < timeout <= (100 if command[0] == "doctor" else 300):
        raise ValueError("Doctor is bounded100s; fixture setup at most300s")
    destination = Path(output)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / (case + ".json")
    if target.exists():
        raise FileExistsError("preserve previous receipt; select a new case ID")
    cli = Path(config["cli"]).resolve()
    env = dict(os.environ)
    env.update(config.get("environment", {}))
    env["LAYERFS_HOME"] = config["home"]
    env["LAYERFS_CONSTRUCTION_WORKERS"] = "1"
    if config.get("bundle"):
        env["LAYERFS_BUNDLE"] = config["bundle"]
    secrets = [str(value) for key, value in config.get("environment", {}).items()
               if any(word in key.upper() for word in ["SECRET", "PASSWORD", "ACCESS_KEY"])]
    source = config["source"]
    commit = subprocess.check_output(["git", "-C", source, "rev-parse", "HEAD"], text=True).strip()
    patch = subprocess.check_output(["git", "-C", source, "diff", "--binary", "HEAD"])
    cli_before = digest(cli)
    before = logical_snapshot(config["home"])
    started = time.monotonic()
    timed_out = False
    try:
        result = subprocess.run([str(cli), *command], env=env, text=True, capture_output=True, timeout=timeout)
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as error:
        timed_out = True
        def decoded(value):
            return value.decode(errors="replace") if isinstance(value, bytes) else (value or "")
        code, stdout = None, decoded(error.stdout)
        stderr = decoded(error.stderr) + "\nowned CLI exceeded invocation deadline; operation was not replayed"
    after = logical_snapshot(config["home"])
    elapsed = time.monotonic() - started
    leaks = [value for value in secrets if value and (value in stdout or value in stderr)]
    for value in secrets:
        if value:
            stdout, stderr = stdout.replace(value, "[redacted]"), stderr.replace(value, "[redacted]")
    try:
        data = json.loads(stdout)
    except (ValueError, TypeError):
        data = None
    failures = []
    if code != 0:
        failures.append("CLI did not return0")
    if leaks:
        failures.append("credential appeared in raw output (redacted in retained evidence)")
    if no_mutation and before != after:
        failures.append("logical home/file inventory changed")
    if digest(cli) != cli_before:
        failures.append("CLI artifact changed during invocation; result is not pinned")
    checks = {row["id"]: row for row in (data or {}).get("checks", [])}
    for requirement in expected:
        check, outcome = requirement.rsplit("=", 1)
        if checks.get(check, {}).get("outcome") != outcome:
            failures.append("unexpected check outcome: " + requirement)
    permitted_failures = {item.rsplit("=", 1)[0] for item in expected if item.endswith("=fail")}
    for row in (data or {}).get("checks", []):
        if row.get("outcome") == "fail" and row.get("severity") == "error" and row.get("id") not in permitted_failures:
            failures.append("unexpected confirmed failure: " + row.get("id", "unknown"))
    if complete is not None and (data or {}).get("complete") is not complete:
        failures.append("unexpected complete coverage flag")
    receipt = {"case": case, "source": commit, "source_patch_sha256": hashlib.sha256(patch).hexdigest(), "source_dirty": bool(patch),
               "cli_sha256": cli_before, "command": command, "exit": code, "timeout_s": timeout,
               "elapsed_s": elapsed, "timed_out": timed_out, "expect": list(expected), "expected_complete": complete, "no_mutation": no_mutation,
               "logical_unchanged": before == after, "logical_changes": sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key)), "verdict": "FAIL" if failures else "PASS", "failures": failures,
               "stdout": data if data is not None else stdout, "stderr": stderr}
    target.write_text(json.dumps(receipt, indent=2))
    print(json.dumps({key: receipt[key] for key in ["case", "verdict", "exit", "elapsed_s", "failures"]}))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--expect", action="append", default=[])
    parser.add_argument("--no-mutation", action="store_true")
    parser.add_argument("--complete", choices=["true","false"])
    parser.add_argument("--timeout", type=int, default=100)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    receipt = invoke(json.loads(Path(args.environment).read_text()), command, args.output, args.case,
                     args.expect, args.no_mutation, args.timeout, None if args.complete is None else args.complete=="true")
    return 0 if receipt["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
