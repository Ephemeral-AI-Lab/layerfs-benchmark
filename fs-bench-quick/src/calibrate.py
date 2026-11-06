#!/usr/bin/env python3
"""Calibrate PostgreSQL round trips per route, from the host and from guests.

`host --route NAME` runs pgrtt.py in this process's host against a declared
host route. `guest --machine M` creates one Sandbox of a fresh SQLite Store on
M through the public CLI and runs pgrtt.py inside its Workspace once per route
the configuration declares for M (the address that machine's daemon dials).
The client uses a trust-authenticated calibration role, so no secret enters an
Exec command. Calibration is never a case: it runs outside every measured row.

Configuration (`calibration` in the environment file):
  {"user": "calib", "database": "calib", "iterations": 200, "connects": 20,
   "host_routes": {"host/published": {"host": "127.0.0.1", "port": 55432}},
   "guest_routes": {"docker": {"postgresql": {"host": ..., "port": ...}}},
   "scram": {"user": "bench", "password_env": "BENCH_PG_PASSWORD"}}
"""

import argparse
import base64
import importlib.util
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
CLIENT = SOURCE / "pgrtt.py"


def load_runner():
    sys.path.insert(0, str(SOURCE))
    spec = importlib.util.spec_from_file_location("quick_run", SOURCE / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def client_args(settings, route, user=None, password_env=None):
    args = [
        "--host",
        route["host"],
        "--port",
        str(route["port"]),
        "--user",
        user or settings["user"],
        "--database",
        settings["database"],
        "--iterations",
        str(settings.get("iterations", 200)),
        "--connects",
        str(settings.get("connects", 20)),
    ]
    return args + (["--password-env", password_env] if password_env else [])


def guest_command(settings, route):
    """One bash command that runs the embedded client with python3."""
    code = (
        "import base64;exec(compile(base64.b64decode("
        + repr(base64.b64encode(CLIENT.read_bytes()).decode())
        + '),"pgrtt","exec"))'
    )
    return shlex.join(["python3", "-c", code, *client_args(settings, route)])


def host(settings, name):
    route = settings["host_routes"][name]
    runs = {"trust": client_args(settings, route)}
    scram = settings.get("scram")
    if scram:
        runs["scram"] = client_args(
            settings, route, scram["user"], scram["password_env"]
        )
    results = {}
    for label, args in runs.items():
        completed = subprocess.run(
            [sys.executable, str(CLIENT), *args],
            capture_output=True,
            text=True,
            timeout=60,
        )
        results[label] = (
            json.loads(completed.stdout)
            if completed.returncode == 0
            else {"error": completed.stderr[-2000:], "exit": completed.returncode}
        )
    return {"location": "host", "route": name, "target": route, "results": results}


def guest(run, config, cache, machine):
    settings = config["calibration"]
    routes = settings["guest_routes"][machine]
    campaign = run.Campaign(config, Path(cache) / "calibration")
    row = campaign.row(
        {
            "cell": "RTT",
            "machine": machine,
            "backend": "sqlite",
            "id": f"RTT/{machine}/sqlite",
        }
    )
    if row["preparation"] != "NOT_RUN":
        raise run.Failure("calibration for this machine already attempted; no replay")
    row["preparation"] = "ATTEMPTED"
    campaign.persist()
    deadline = run.measure.Deadline.after(90)
    store = row["store"]
    output = {"location": "guest", "machine": machine, "results": {}}
    try:
        campaign.call(row, "store_create", ["store", "create", store], deadline)
        row["store_live"] = True
        campaign.call(
            row,
            "project_init",
            ["project", "init", store + "/p", config["empty_source"]],
            deadline,
        )
        campaign.call(
            row, "branch_fork", ["branch", "fork", store + "/p", "lane", "main"], deadline
        )
        if machine != "native":
            campaign.call(
                row,
                "store_push",
                ["store", "push", store, campaign.machine_name(row)],
                deadline,
            )
        campaign.call(
            row,
            "sandbox_create",
            [
                "sandbox",
                "create",
                store + "/p",
                row["sandbox"],
                campaign.machine_name(row),
            ],
            deadline,
        )
        row["sandbox_live"] = True
        campaign.mount(row, "rtt", deadline)
        for arm, route in routes.items():
            value = campaign.call(
                row,
                f"rtt_{arm}",
                ["workspace", "exec", row["workspace"], guest_command(settings, route)],
                deadline,
            )
            output["results"][arm] = {
                "target": route,
                "measurement": json.loads(value["stdout"]),
            }
        campaign.call(
            row, "unmount", ["workspace", "unmount", row["workspace"]], deadline
        )
        row["workspace"] = None
        row["execution"] = "PASS"
    except (run.Failure, run.measure.BudgetExceeded, ValueError) as error:
        row["execution"] = "FAIL"
        row["reason"] = str(error)
        row["uncertain"] |= getattr(error, "uncertain", False)
    finally:
        campaign.cleanup(row)
        campaign.persist()
    output.update(
        execution=row["execution"],
        cleanup=row["cleanup"],
        reason=row.get("reason"),
        commands=row.get("commands", []),
    )
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("where", choices=("host", "guest"))
    parser.add_argument("--environment", required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--route")
    parser.add_argument("--machine")
    args = parser.parse_args(argv)
    config = json.loads(Path(args.environment).read_text())
    if args.output.exists():
        parser.error("output exists; calibration receipts are append-only")
    started = time.time_ns()
    if args.where == "host":
        result = host(config["calibration"], args.route)
    else:
        run = load_runner()
        with run.campaign_lock(Path(args.cache) / "calibration"):
            result = guest(run, config, args.cache, args.machine)
    result.update(
        started_unix_ns=started,
        finished_unix_ns=time.time_ns(),
        load_1m=__import__("os").getloadavg()[0],
        campaign_id=config["campaign_id"],
        source_sha=config["source_sha"],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    failed = result.get("execution", "PASS") != "PASS" or result.get(
        "cleanup", "COMPLETE"
    ) != "COMPLETE"
    print(json.dumps({"output": str(args.output), "failed": failed}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
