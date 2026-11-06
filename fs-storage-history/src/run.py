#!/usr/bin/env python3
"""fs-storage-history entrypoint.

    run.py plan
    run.py row --environment E --case H01 --backend sqlite --output DIR

`plan` prints each case's Commit count and workload digest (needs FSH_BASE or
the config's base_dir). `row` runs one case on Docker with one backend, once;
it refuses an output directory that exists. Rows run serially, SQLite then
PostgreSQL. Infrastructure (docker worker, PostgreSQL server and databases)
is provisioned and released outside this script and recorded in the config.
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
sys.path.insert(1, str(SRC.parents[1] / "shared" / "src"))

import base  # noqa: E402
import cases  # noqa: E402
import driver  # noqa: E402
import measure  # noqa: E402


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def docker_free_bytes(image):
    """Free bytes on the Docker guest's root filesystem (read-only probe)."""
    got = measure.run_command(["docker", "run", "--rm", "--network", "none", "--pull", "never",
                               "--entrypoint", "df", image, "-B1", "--output=avail", "/"],
                              measure.Deadline.after(60))
    lines = got["stdout"].split()
    return int(lines[-1]) if got["process_exit"] == 0 and lines and lines[-1].isdigit() else None


def preflight(config):
    """Check pinned identities before a row; return (base_state, problems)."""
    problems = []
    cli = Path(config["cli"])
    if not cli.is_absolute() or not cli.is_file():
        problems.append("pinned CLI missing or not absolute")
    elif sha256(cli) != config["artifacts"]["cli_sha256"]:
        problems.append("CLI hash differs from artifacts.cli_sha256")
    empty = Path(config["empty_source"])
    if not empty.is_dir() or any(empty.iterdir()):
        problems.append("empty source missing or not empty")
    model_sha = sha256(SRC / "model.py")
    if model_sha != config["artifacts"].get("model_sha256"):
        problems.append("model.py differs from the image's recorded model_sha256")
    state = base.load_tree(config["base_dir"])
    try:
        base.check_pins(state.summary())
    except SystemExit as error:
        problems.append(str(error))
    env = dict(os.environ, **config.get("environment", {}), LAYERFS_HOME=config["home"],
               LAYERFS_CONSTRUCTION_WORKERS="1")
    got = measure.run_command([config["cli"], "machine", "get", "docker"],
                              measure.Deadline.after(30), env=env)
    try:
        machine = json.loads(got["stdout"])
        if machine.get("image") != config["artifacts"]["sandbox_image"]:
            problems.append("docker machine image differs from artifacts.sandbox_image")
        if machine.get("state") != "running":
            problems.append(f"docker machine is {machine.get('state')}")
    except ValueError:
        problems.append("machine get docker gave no JSON")
    free = docker_free_bytes(config["artifacts"]["sandbox_image"])
    minimum = config.get("docker_min_free_bytes", 20 * 2**30)
    if free is None or free < minimum:
        problems.append(f"Docker guest free space {free} B is below {minimum} B; not started "
                        "(capacity, not a product result)")
    return state, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "row"))
    parser.add_argument("--environment")
    parser.add_argument("--case", choices=cases.CASE_IDS)
    parser.add_argument("--backend", choices=("sqlite", "postgresql"))
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    if args.action == "plan":
        root = os.environ.get("FSH_BASE")
        if args.environment:
            root = json.loads(Path(args.environment).read_text())["base_dir"]
        state = base.load_tree(root)
        base.check_pins(state.summary())
        for case_id in cases.CASE_IDS:
            plan = cases.build_plan(case_id, state)
            print(json.dumps({"case": case_id, "commits": cases.commit_count(case_id),
                              "stores": len(plan["stores"]),
                              "workload_sha256": plan["workload_sha256"]}))
        return 0
    if not (args.environment and args.case and args.backend and args.output):
        parser.error("row needs --environment, --case, --backend and --output")
    config = json.loads(Path(args.environment).read_text())
    state, problems = preflight(config)
    if problems:
        print(json.dumps({"case": args.case, "backend": args.backend, "execution": "NOT_RUN",
                          "reasons": problems}))
        return 1
    row = driver.Row(config, args.case, args.backend, args.output, state, config["base_dir"])
    result = row.run()
    print(json.dumps({k: result.get(k) for k in (
        "case", "backend", "execution", "verification", "cleanup", "reason")}))
    print(json.dumps(result.get("totals")))
    return 0 if result["execution"] == "PASS" and result["cleanup"] == "COMPLETE" else 1


if __name__ == "__main__":
    sys.exit(main())
