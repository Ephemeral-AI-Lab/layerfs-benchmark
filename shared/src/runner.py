#!/usr/bin/env python3
"""Small, serial CLI-only benchmark lifecycle; configuration is explicit JSON.

Required configuration: campaign_id, source_sha, cli, home, empty_source,
machines (mapping native/docker/lima/apple-container to {name, ready}), artifacts.
PostgreSQL rows additionally use postgresql.databases['C01/native'] and
postgresql.password_env. Databases must be independently provisioned beforehand.
Infrastructure allocations are exact records in resources: {id, owned: true,
release_argv: [...], released: false}; borrowed resources are never removed.
"""

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import shlex
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import cases
import measure

MACHINES = ("native", "docker", "lima", "apple-container")
BACKENDS = ("sqlite", "postgresql")
# Optional declared route arm: PostgreSQL on the daemon's own Docker network.
COLOCATED = "pg-colocated"
ARMS = (*BACKENDS, COLOCATED)
CELLS = getattr(cases, "CASE_IDS", tuple(f"C{i:02d}" for i in range(1, 13)))
HARNESS_FILES = ("run.py", "cases.py", "runner.py", "measure.py")
OBSERVER_DATABASE = re.compile(r"[a-z0-9_]{1,63}")
LOG_LINE = re.compile(r"\[(\d+)\] db=(\S+) LOG:\s+(.*)$")


class Failure(Exception):
    def __init__(self, message, uncertain=False):
        super().__init__(message)
        self.uncertain = uncertain


def kind(backend):
    """The Store backend of a selected arm; route arms keep their backend."""
    return "sqlite" if backend == "sqlite" else "postgresql"


def selections(
    cells=CELLS, machines=MACHINES, backends=ARMS, colocated=(), alternate=False
):
    """Matrix order: cell, machine, then arm.

    `colocated` names machines that also register the co-located PostgreSQL
    arm. `alternate` reverses the arm order on every second cell (C02, C04, ...)
    so first-touch effects do not always land on the same backend.
    """
    rows = []
    for index, cell in enumerate(CELLS):
        if cell not in cells:
            continue
        for machine in MACHINES:
            if machine not in machines:
                continue
            arms = BACKENDS + ((COLOCATED,) if machine in colocated else ())
            if alternate and index % 2:
                arms = arms[::-1]
            rows.extend(
                {
                    "cell": cell,
                    "machine": machine,
                    "backend": backend,
                    "id": f"{cell}/{machine}/{backend}",
                }
                for backend in arms
                if backend in backends
            )
    return rows


def matrix_options(config):
    return {
        "colocated": tuple(
            config.get("postgresql", {}).get("colocated_machines", ())
        ),
        "alternate": config.get("order") == "alternate",
    }


def database_key(row):
    key = f"{row['cell']}/{row['machine']}"
    return key if row["backend"] == "postgresql" else f"{key}/{row['backend']}"


def connection_counts(text, row_id, database):
    """Attribute logged connections to the phase between this row's markers.

    Each boundary call logs `pg62-boundary row=<id> next=<phase>`; a logged
    `connection authorized` for the row's database counts toward the phase
    that marker opened, with the client address from its `connection received`.
    """
    hosts, phase, counts = {}, None, {}
    for line in text.splitlines():
        match = LOG_LINE.search(line)
        if not match:
            continue
        pid, message = match.group(1), match.group(3)
        if message.startswith("connection received: host="):
            hosts[pid] = message.split("host=", 1)[1].split()[0]
        elif message.startswith("pg62-boundary "):
            fields = dict(
                item.split("=", 1) for item in message.split()[1:] if "=" in item
            )
            if fields.get("row") == row_id:
                phase = None if fields.get("next") == "end" else fields.get("next")
        elif message.startswith("connection authorized:") and phase:
            fields = dict(
                item.split("=", 1) for item in message.split()[2:] if "=" in item
            )
            if fields.get("database") == database:
                entry = counts.setdefault(phase, {"connections": 0, "sources": {}})
                entry["connections"] += 1
                source = hosts.get(pid, "unknown")
                entry["sources"][source] = entry["sources"].get(source, 0) + 1
    return counts


def digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def harness_sources():
    suite = Path(__file__).resolve().parent
    shared = suite.parents[1] / "shared" / "src"
    return {
        "run.py": suite / "run.py",
        "cases.py": suite / "cases.py",
        "runner.py": shared / "runner.py",
        "measure.py": shared / "measure.py",
    }


def harness_hashes():
    return {name: digest(path) for name, path in harness_sources().items()}


def snapshot_harness(output):
    destination = Path(output) / "harness"
    destination.mkdir()
    hashes = {}
    for name, path in harness_sources().items():
        source = path.read_bytes()
        with (destination / name).open("wb") as stream:
            stream.write(source)
            stream.flush()
            os.fsync(stream.fileno())
        hashes[name] = hashlib.sha256(source).hexdigest()
    return hashes


def compact_snapshot(cache, output):
    hashes = harness_hashes()
    identity = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    root = cache / "sources" / identity
    if not root.exists():
        root.mkdir(parents=True)
        snapshot_harness(root)
    if {name: digest(root / "harness" / name) for name in hashes} != hashes:
        raise Failure("retained source snapshot identity mismatch")
    (Path(output) / "harness").symlink_to(root / "harness", target_is_directory=True)
    return hashes


def workspace_command(argv, environment):
    prefix = " ".join(
        f"{key}={shlex.quote(value)}" for key, value in environment.items()
    )
    return ("export " + prefix + "; " if prefix else "") + shlex.join(argv)


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def append(path, value):
    with path.open("a") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


class Campaign:
    def __init__(self, config, cache):
        self.config = config
        self.cache = Path(cache).resolve()
        self.cache.mkdir(parents=True, exist_ok=True)
        self.path = self.cache / "campaign.json"
        self.log = self.cache / "ledger.jsonl"
        self.identity = hashlib.sha256(
            json.dumps(config, sort_keys=True).encode()
        ).hexdigest()
        if self.path.exists():
            self.state = json.loads(self.path.read_text())
            if self.state["config_sha256"] != self.identity:
                raise Failure("configuration identity changed; prepare a new campaign")
        else:
            self.state = {
                "campaign_id": config["campaign_id"],
                "source_sha": config["source_sha"],
                "config_sha256": self.identity,
                "matrix": selections(**matrix_options(config)),
                "rows": {},
                "resources": config.get("resources", []),
                "cleanup": "NOT_RUN",
            }
            self.persist()
        self.env = dict(
            os.environ, LAYERFS_HOME=config["home"], LAYERFS_CONSTRUCTION_WORKERS="1"
        )
        self.env.update(config.get("environment", {}))
        self.env["LAYERFS_HOME"] = config["home"]
        self.env["LAYERFS_CONSTRUCTION_WORKERS"] = "1"
        self.secrets = [
            os.environ[key]
            for key in config.get("secret_env", [])
            if os.environ.get(key)
        ]
        password_env = config.get("postgresql", {}).get("password_env")
        if password_env and os.environ.get(password_env):
            self.secrets.append(os.environ[password_env])

    def persist(self):
        save(self.path, self.state)

    def event(self, kind, **fields):
        append(
            self.log, {"event": kind, "time_ns": time.time_ns(), **self.redact(fields)}
        )

    def redact(self, value):
        if isinstance(value, str):
            for secret in self.secrets:
                value = value.replace(secret, "<redacted>")
            return value
        if isinstance(value, list):
            return [self.redact(item) for item in value]
        if isinstance(value, dict):
            return {key: self.redact(item) for key, item in value.items()}
        return value

    def call(self, row, phase, argv, deadline, cli=True):
        if row.get("pending"):
            raise Failure("unresolved prior operation; inspect without replay", True)
        command = [self.config["cli"], *argv] if cli else argv
        row["pending"] = {"phase": phase, "argv": self.redact(command)}
        self.persist()
        self.event("intent", row=row["id"], phase=phase, argv=command)
        try:
            deadline.remaining()
        except measure.BudgetExceeded:
            row["pending"] = None
            self.persist()
            raise
        try:
            result = measure.run_command(command, deadline, env=self.env)
        except BaseException:
            row["uncertain"] = True
            self.persist()
            raise
        self.event("result", row=row["id"], phase=phase, **result)
        row.setdefault("commands", []).append({"phase": phase, **self.redact(result)})
        row.setdefault("timings_ns", {})[phase] = result.get("elapsed_ns")
        row["pending"] = None
        uncertain = bool(result.get("uncertainty") or result.get("timed_out"))
        if result.get("process_exit") != 0:
            refusal = {}
            with contextlib.suppress(ValueError, TypeError):
                parsed_refusal = json.loads(result.get("stderr", ""))
                if isinstance(parsed_refusal, dict):
                    refusal = parsed_refusal
            process_exit = result.get("process_exit")
            if cli:
                uncertain |= isinstance(process_exit, int) and process_exit < 0
                uncertain |= process_exit == 125 and not refusal.get("code")
            uncertain |= refusal.get("code") in ("Unknown", "Unresolved")
            # An exchange failure can follow publication; retain its custody.
            uncertain |= refusal.get("code") == "Failed"
            row["uncertain"] = uncertain
            self.persist()
            raise Failure(
                f"{phase}: CLI/process exit {result.get('process_exit')}", uncertain
            )
        if not cli:
            self.persist()
            return result
        try:
            value = json.loads(result["stdout"])
            if not isinstance(value, dict) or result.get("output_truncated"):
                raise ValueError("expected complete JSON object")
        except (ValueError, KeyError, TypeError) as error:
            row["uncertain"] = True
            self.persist()
            raise Failure(
                f"{phase}: malformed/missing result: {error}", True
            ) from error
        # Persist allocation/release identity atomically with settling the intent.
        if argv[:2] in (["store", "create"], ["store", "connect"]):
            row["store_live"] = True
            if argv[:2] == ["store", "connect"]:
                row["database_allocation"] = argv[3]
        elif argv[:2] == ["sandbox", "create"]:
            row["sandbox_live"] = True
        elif argv[:2] == ["workspace", "mount"]:
            if not value.get("ws"):
                row["uncertain"] = True
                self.persist()
                raise Failure("mount result has no workspace identity", True)
            row["workspace"] = value["ws"]
        elif argv[:2] == ["workspace", "unmount"]:
            row["workspace"] = None
        elif argv[:2] == ["sandbox", "close"]:
            row["sandbox_live"] = False
        elif argv[:2] in (["store", "remove"], ["store", "disconnect"]):
            row["store_live"] = False
        self.persist()
        if argv[:2] == ["workspace", "exec"] and value.get("truncated"):
            raise Failure(f"{phase}: workload output is truncated")
        if argv[:2] == ["workspace", "exec"] and value.get("exit_code") != 0:
            raise Failure(f"{phase}: workload exit {value.get('exit_code')}")
        return value

    def row(self, selection):
        key = selection["id"]
        if key not in self.state["rows"]:
            slug = re.sub(r"[^A-Za-z0-9_-]", "-", key).lower()
            name = f"q-{self.config['campaign_id']}-{slug}"
            self.state["rows"][key] = {
                **selection,
                "store": name,
                "sandbox": name,
                "workspace": None,
                "store_live": False,
                "sandbox_live": False,
                "uncertain": False,
                "preparation": "NOT_RUN",
                "execution": "NOT_RUN",
                "cleanup": "NOT_RUN",
                "verification": "SKIPPED",
                "correctness": "UNVERIFIED",
                "performance": "INELIGIBLE",
                "pending": None,
            }
            self.persist()
        return self.state["rows"][key]

    def prerequisite(self, row):
        cli = Path(self.config["cli"])
        if not cli.is_file() or not os.access(cli, os.X_OK):
            return "pinned release CLI is unavailable"
        expected = self.config.get("artifacts", {}).get("cli_sha256")
        if not expected or digest(cli) != expected:
            return "CLI artifact hash missing or mismatched"
        machine = self.config.get("machines", {}).get(row["machine"], {})
        if not machine.get("ready"):
            return f"{row['machine']} machine is not registered ready"
        if not Path(self.config["empty_source"]).is_dir():
            return "empty source fixture is unavailable"
        if any(Path(self.config["empty_source"]).iterdir()):
            return "empty source fixture is not empty"
        if kind(row["backend"]) == "postgresql":
            pg = self.config.get("postgresql", {})
            url = pg.get("databases", {}).get(database_key(row))
            if not url:
                return "independently provisioned PostgreSQL database missing"
            parsed = urlsplit(url)
            password_query = any(
                "password" in key.lower()
                for key, _ in parse_qsl(parsed.query, keep_blank_values=True)
            )
            if parsed.password is not None or password_query:
                return "PostgreSQL URL must omit passwords and password query settings"
            if not pg.get("password_env") or not os.environ.get(pg["password_env"]):
                return "PostgreSQL credential environment reference unavailable"
            disposal_id = pg.get("disposal_resource")
            if not any(
                resource.get("id") == disposal_id
                and resource.get("owned")
                and resource.get("release_argv")
                for resource in self.state["resources"]
            ):
                return "PostgreSQL data disposal resource is unregistered"
        return None

    def prepare(self, selection):
        row = self.row(selection)
        if row["preparation"] != "NOT_RUN":
            raise Failure(f"{row['id']}: preparation already attempted; no replay")
        try:
            case = cases.get_case(row["cell"])
        except (KeyError, ValueError, NotImplementedError) as error:
            row["reason"] = str(error)
            self.persist()
            return row
        machine = self.config.get("machines", {}).get(row["machine"], {})
        reason = machine.get("unavailable_reason") or self.prerequisite(row)
        if (
            case.get("supported_platforms")
            and machine.get("platform") not in case["supported_platforms"]
        ):
            reason = f"upstream tool does not support {machine.get('platform')}; supported: {case['supported_platforms']}"
        if case.get("requires_root") and not machine.get("root_capable", False):
            reason = "upstream requires root; selected execution route is not root"
        if reason:
            row["reason"] = reason
            self.event("not_run", row=row["id"], reason=reason)
            self.persist()
            return row
        row["prepare_harness_sha256"] = harness_hashes()
        row["preparation"] = "ATTEMPTED"
        row["workload"] = case["provenance"]
        self.persist()
        started = time.monotonic_ns()
        deadline = measure.Deadline.after(self.config.get("prepare_budget_s", 25))
        try:
            store = row["store"]
            if row["backend"] == "sqlite":
                self.call(row, "store_create", ["store", "create", store], deadline)
            else:
                pg = self.config["postgresql"]
                url = pg["databases"][database_key(row)]
                self.call(
                    row,
                    "store_connect",
                    [
                        "store",
                        "connect",
                        store,
                        url,
                        "--password",
                        f"env:{pg['password_env']}",
                        "--synchronous-commit",
                        "off",
                    ],
                    deadline,
                )
                row["database_allocation"] = url
            row["store_live"] = True
            self.persist()
            self.call(
                row,
                "project_init",
                ["project", "init", store + "/p", self.config["empty_source"]],
                deadline,
            )
            self.call(
                row,
                "branch_fork",
                ["branch", "fork", store + "/p", "lane", "main"],
                deadline,
            )
            if row["backend"] == "sqlite" and row["machine"] != "native":
                self.call(
                    row,
                    "store_push",
                    ["store", "push", store, self.machine_name(row)],
                    deadline,
                )
            if case.get("setup"):
                self.prepare_base(row, case, deadline)
            row["preparation"] = "READY"
        except (Failure, measure.BudgetExceeded) as error:
            row["preparation"] = "FAIL"
            row["reason"] = str(error)
            row["uncertain"] |= getattr(error, "uncertain", False)
            self.cleanup(row)
        finally:
            row["prepare_elapsed_ns"] = time.monotonic_ns() - started
            self.persist()
        return row

    def tool_environment(self, row, case):
        return {
            **case.get("environment", {}),
            **self.config["machines"][row["machine"]].get("tool_environment", {}),
        }

    def prepare_base(self, row, case, deadline):
        started = time.monotonic_ns()
        row["base_fixture"] = {"status": "ATTEMPTED", "machine": row["machine"]}
        self.persist()
        self.call(
            row,
            "setup_sandbox_create",
            [
                "sandbox",
                "create",
                row["store"] + "/p",
                row["sandbox"],
                self.machine_name(row),
            ],
            deadline,
        )
        self.mount(row, "setup", deadline)
        command = workspace_command(
            case["setup_argv"], self.tool_environment(row, case)
        )
        setup_result = self.call(
            row,
            "setup_exec",
            ["workspace", "exec", row["workspace"], command],
            deadline,
        )
        if hasattr(cases, "parse_setup_result"):
            try:
                row["setup_tool_metrics"] = cases.parse_setup_result(
                    row["cell"],
                    setup_result.get("stdout", ""),
                    setup_result.get("stderr", ""),
                    setup_result.get("exit_code"),
                )
            except ValueError as error:
                raise Failure(f"setup tool result: {error}") from error
        commit = self.call(
            row, "setup_commit", ["workspace", "commit", row["workspace"]], deadline
        )
        if commit.get("kind") != "Committed":
            raise Failure("base preparation requires a known Committed result")
        row["base_fixture"]["commit"] = commit
        self.persist()
        self.call(
            row, "setup_unmount", ["workspace", "unmount", row["workspace"]], deadline
        )
        self.call(
            row, "setup_sandbox_close", ["sandbox", "close", row["sandbox"]], deadline
        )
        row["base_fixture"].update(
            status="READY", elapsed_ns=time.monotonic_ns() - started
        )
        self.persist()

    def machine_name(self, row):
        return self.config["machines"][row["machine"]].get("name", row["machine"])

    def cache_boundary(self, row, phase, deadline):
        controls = (
            self.config.get("machines", {}).get(row["machine"], {}).get("cache", {})
        )
        selected = controls.get(row["backend"], {}).get(phase, {})
        for index, argv in enumerate(selected.get("commands", [])):
            self.call(row, f"cache_{phase}_{index}", argv, deadline, cli=False)
        evidence = selected.get("evidence", {})
        verdict = measure.assess_cache(
            evidence, phase, row["machine"], kind(row["backend"])
        )
        row.setdefault("cache", {})[phase] = verdict
        self.persist()

    def observer_database(self, row):
        if kind(row["backend"]) != "postgresql":
            return None
        url = self.config["postgresql"]["databases"][database_key(row)]
        name = urlsplit(url).path.lstrip("/")
        if not OBSERVER_DATABASE.fullmatch(name):
            raise Failure("observed database name must be lowercase [a-z0-9_]")
        return name

    def boundary(self, row, next_phase, deadline):
        """Close the observed phase and open the next one (None: end).

        One administrative psql call on the dedicated server: snapshot this
        row's database in pg_stat_statements, reset it, and log a marker that
        attributes later connections. SQLite rows make the same call with the
        marker only, so both backends see the same gaps between phases. The
        call is control overhead, never a phase timing; its failure leaves the
        phase's counts unavailable and does not touch LayerFS custody.
        """
        observer = self.config.get("postgresql", {}).get("observer")
        if not observer:
            return
        database = self.observer_database(row)
        previous = row.get("observed_phase")
        scope = (
            "FROM pg_stat_statements s JOIN pg_database d ON d.oid = s.dbid "
            f"WHERE d.datname = '{database}'"
        )
        sql = []
        if database and previous:
            sql += [
                "SELECT 'total', coalesce(sum(calls), 0), count(*), "
                "coalesce(round(sum(total_exec_time)::numeric, 3), 0), "
                f"coalesce(sum(rows), 0) {scope}",
                "SELECT 'top', calls, round(total_exec_time::numeric, 3), rows, "
                "left(regexp_replace(query, '\\s+', ' ', 'g'), 160) "
                f"{scope} ORDER BY calls DESC, query LIMIT 25",
            ]
        if database and next_phase:
            sql.append(
                "SELECT 'reset', pg_stat_statements_reset(0, "
                f"(SELECT oid FROM pg_database WHERE datname = '{database}'), 0)"
            )
        marker = next_phase or "end"
        sql.append(
            f"DO $$BEGIN RAISE LOG 'pg62-boundary row={row['id']} next={marker}'; END$$"
        )
        argv = [*observer["admin_argv"], *[part for text in sql for part in ("-c", text)]]
        result = measure.run_command(argv, deadline, env=self.env, output_limit=262144)
        row["control_overhead_ns"] = row.get("control_overhead_ns", 0) + (
            result.get("elapsed_ns") or 0
        )
        row.setdefault("boundaries", []).append(
            {
                "next": marker,
                "elapsed_ns": result.get("elapsed_ns"),
                "process_exit": result.get("process_exit"),
            }
        )
        if previous and database:
            stats = row.setdefault("pg_phases", {}).setdefault(previous, {})
            if result.get("process_exit") != 0 or result.get("output_truncated"):
                stats["statements_status"] = "UNAVAILABLE"
                stats["observer_error"] = self.redact(result.get("stderr", ""))[:2000]
            else:
                top = []
                for line in result.get("stdout", "").splitlines():
                    fields = line.split("\x1f")
                    if fields[0] == "total" and len(fields) == 5:
                        stats.update(
                            statements=int(fields[1]),
                            distinct_statements=int(fields[2]),
                            statement_exec_ms=float(fields[3]),
                            statement_rows=int(fields[4]),
                        )
                    elif fields[0] == "top" and len(fields) == 5:
                        top.append(
                            {
                                "calls": int(fields[1]),
                                "exec_ms": float(fields[2]),
                                "rows": int(fields[3]),
                                "query": fields[4],
                            }
                        )
                stats["top"] = top
                stats["statements_status"] = (
                    "OBSERVED" if "statements" in stats else "UNAVAILABLE"
                )
        row["observed_phase"] = next_phase
        self.persist()

    def collect_connections(self, row, since_s):
        observer = self.config.get("postgresql", {}).get("observer")
        database = observer and self.observer_database(row)
        if not database:
            return
        argv = [
            str(since_s) if part == "{since}" else part
            for part in observer["log_argv"]
        ]
        result = measure.run_command(
            argv, measure.Deadline.after(10), env=self.env, output_limit=4194304
        )
        row["control_overhead_ns"] = row.get("control_overhead_ns", 0) + (
            result.get("elapsed_ns") or 0
        )
        if result.get("process_exit") != 0 or result.get("output_truncated"):
            row["connections_status"] = "UNAVAILABLE"
            self.persist()
            return
        counts = connection_counts(
            result.get("stdout", "") + "\n" + result.get("stderr", ""),
            row["id"],
            database,
        )
        phases = row.setdefault("pg_phases", {})
        for phase in phases:
            phases[phase].update(counts.get(phase, {"connections": 0, "sources": {}}))
        for phase, value in counts.items():
            phases.setdefault(phase, {}).update(value)
        row["connections_status"] = "OBSERVED"
        self.persist()

    def guarded(self, row, action, *args):
        """Observation after measurement must not block case cleanup."""
        try:
            action(*args)
        except (Failure, measure.BudgetExceeded, OSError, ValueError) as error:
            row.setdefault("observer_failures", []).append(str(error))
            self.persist()

    def mount(self, row, name, deadline):
        result = self.call(
            row,
            f"{name}_mount",
            ["workspace", "mount", row["sandbox"], "lane", "--name", name],
            deadline,
        )
        if not result.get("ws"):
            row["uncertain"] = True
            raise Failure("mount result has no workspace identity", True)
        row["workspace"] = result["ws"]
        self.persist()

    def execute(self, selection, output, verify=False):
        row = self.row(selection)
        if row["execution"] != "NOT_RUN":
            raise Failure(f"{row['id']}: attempt already registered; no resampling")
        matrix_index = next(
            index
            for index, item in enumerate(self.state["matrix"])
            if item["id"] == row["id"]
        )
        prior = self.state.get("attempt_sequence", [])
        if prior and matrix_index < prior[-1]["matrix_index"]:
            raise Failure(
                "configuration is earlier than the campaign cursor; preserve cell/machine/database order"
            )
        output = Path(output)
        if output.exists():
            raise Failure(
                "output directory already exists; retained evidence cannot be overwritten"
            )
        output.mkdir(parents=True)
        row["output"] = str(output.resolve())
        row["harness_sha256"] = (
            compact_snapshot(self.cache, output)
            if self.config.get("compact_sources")
            else snapshot_harness(output)
        )
        row["matrix_index"] = matrix_index
        self.state.setdefault("attempt_sequence", []).append(
            {
                "row": row["id"],
                "matrix_index": matrix_index,
                "harness_sha256": row["harness_sha256"],
                "registered_ns": time.time_ns(),
            }
        )
        self.persist()
        self.event(
            "selection_registered",
            row=row["id"],
            matrix_index=matrix_index,
            harness_sha256=row["harness_sha256"],
        )
        if row["preparation"] != "READY":
            row["reason"] = row.get("reason", "prepared input unavailable")
            self.cleanup(row)
            self.receipt(row)
            return row
        case = cases.get_case(row["cell"], verify=verify)
        workload_identity = {
            key: value
            for key, value in case["provenance"].items()
            if key != "verification"
        }
        if workload_identity != row["workload"]:
            raise Failure("prepared workload identity changed")
        if verify:
            row["verification_provenance"] = case["provenance"].get("verification")
        row["execution"] = "ATTEMPTED"
        row["preparation"] = "CONSUMED"
        row["verification"] = "NOT_RUN" if verify else "SKIPPED"
        self.persist()
        self.event("attempt", row=row["id"], verify=verify)
        started = time.monotonic_ns()
        since_s = int(time.time()) - 1
        row["load_1m"] = os.getloadavg()[0]
        proof_started = None
        budget = case.get(
            "performance_budget_s", self.config.get("performance_budget_s", 15)
        )
        # An owner-approved exception may raise one machine's budget past 25 s,
        # never past the 2-minute command ceiling. Record it on the row.
        exception = self.config.get("budget_exceptions", {}).get(row["machine"])
        ceiling = 25
        if exception:
            if not exception.get("approved_by") or not exception.get("reason"):
                raise Failure("budget exception needs approved_by and reason")
            ceiling = min(exception.get("max_s", 25), 110)
            budget = exception.get("max_s", budget)
            row["budget_exception"] = exception
        if not 0 < budget <= ceiling:
            raise Failure(f"performance budget must be positive and at most {ceiling} seconds")
        row["performance_budget_s"] = budget
        deadline = measure.Deadline.after(budget)
        try:
            self.boundary(row, "sandbox_create", deadline)
            self.call(
                row,
                "sandbox_create",
                [
                    "sandbox",
                    "create",
                    row["store"] + "/p",
                    row["sandbox"],
                    self.machine_name(row),
                ],
                deadline,
            )
            row["sandbox_live"] = True
            self.persist()
            self.boundary(row, "measured_mount", deadline)
            self.cache_boundary(row, "mount", deadline)
            self.mount(row, "measured", deadline)
            self.boundary(row, "exec", deadline)
            self.cache_boundary(row, "exec", deadline)
            command = workspace_command(
                case["exec_argv"], self.tool_environment(row, case)
            )
            tool_result = self.call(
                row, "exec", ["workspace", "exec", row["workspace"], command], deadline
            )
            if hasattr(cases, "parse_result"):
                try:
                    row["tool_metrics"] = cases.parse_result(
                        row["cell"],
                        tool_result.get("stdout", ""),
                        tool_result.get("stderr", ""),
                        tool_result.get("exit_code"),
                    )
                except ValueError as error:
                    raise Failure(f"tool result: {error}") from error
            self.boundary(row, "commit", deadline)
            self.cache_boundary(row, "commit", deadline)
            commit = self.call(
                row, "commit", ["workspace", "commit", row["workspace"]], deadline
            )
            if commit.get("kind") not in ("Committed", "UpToDate"):
                raise Failure("unexpected Commit result", True)
            row["commit"] = commit
            if case.get("followup_argv"):
                # A small second change and Commit on the same Workspace.
                self.boundary(row, "followup_exec", deadline)
                followup = workspace_command(
                    case["followup_argv"], self.tool_environment(row, case)
                )
                self.call(
                    row,
                    "followup_exec",
                    ["workspace", "exec", row["workspace"], followup],
                    deadline,
                )
                self.boundary(row, "commit_2", deadline)
                second = self.call(
                    row, "commit_2", ["workspace", "commit", row["workspace"]], deadline
                )
                if second.get("kind") not in ("Committed", "UpToDate"):
                    raise Failure("unexpected second Commit result", True)
                row["commit_2"] = second
            self.boundary(row, "unmount", deadline)
            self.call(
                row, "unmount", ["workspace", "unmount", row["workspace"]], deadline
            )
            row["workspace"] = None
            row["execution"] = "PASS"
            # The optional proof has a separately bounded deadline after performance.
            row["performance_operations_elapsed_ns"] = time.monotonic_ns() - started
            if verify:
                proof_started = time.monotonic_ns()
                proof_deadline = measure.Deadline.after(9.9)
                self.mount(row, "verification", proof_deadline)
                verifier = case["verifier"]
                if isinstance(verifier, dict):
                    verifier = verifier["command"]
                verifier_command = shlex.join(
                    ["/bin/bash", "-o", "pipefail", "-c", verifier]
                )
                self.call(
                    row,
                    "verify",
                    ["workspace", "exec", row["workspace"], verifier_command],
                    proof_deadline,
                )
                self.call(
                    row,
                    "verify_unmount",
                    ["workspace", "unmount", row["workspace"]],
                    proof_deadline,
                )
                row["workspace"] = None
                row["verification"] = "PASS"
                row["correctness"] = "VERIFIED"
                row["verification_elapsed_ns"] = time.monotonic_ns() - proof_started
            cache = row.get("cache", {})
            eligible = set(cache) == {"mount", "exec", "commit"} and all(
                v.get("eligibility", v.get("status")) == "ELIGIBLE"
                for v in cache.values()
            )
            row["performance"] = "ELIGIBLE" if eligible else "INELIGIBLE"
        except (Failure, measure.BudgetExceeded) as error:
            if row["execution"] == "PASS" and verify:
                row["verification"] = "FAIL"
            else:
                row["execution"] = "FAIL"
            row["reason"] = str(error)
            row["uncertain"] |= getattr(error, "uncertain", False)
        except (KeyboardInterrupt, SystemExit):
            row["execution"] = "INCOMPLETE"
            row["uncertain"] |= bool(row.get("pending"))
            raise
        finally:
            if proof_started is not None and "verification_elapsed_ns" not in row:
                row["verification_elapsed_ns"] = time.monotonic_ns() - proof_started
            proof_ns = row.get("verification_elapsed_ns", 0)
            # Pause only the performance budget for the separately bounded proof.
            cleanup_deadline = measure.Deadline(deadline.end_ns + proof_ns)
            observed = self.config.get("postgresql", {}).get("observer")
            if observed:
                self.guarded(
                    row, self.boundary, row, "cleanup", measure.Deadline.after(10)
                )
            self.cleanup(row, deadline=cleanup_deadline)
            if observed:
                self.guarded(row, self.boundary, row, None, measure.Deadline.after(10))
                self.guarded(row, self.collect_connections, row, since_s)
            row["harness_elapsed_ns"] = time.monotonic_ns() - started
            row["performance_invocation_elapsed_ns"] = (
                row["harness_elapsed_ns"] - proof_ns
            )
            if row["performance_invocation_elapsed_ns"] > budget * 1_000_000_000:
                row["performance_budget_exceeded"] = True
                row["performance"] = "INELIGIBLE"
                row["execution"] = "FAIL"
                row.setdefault(
                    "reason",
                    "complete performance invocation exceeded its declared budget",
                )
            self.persist()
            self.receipt(row)
        return row

    def receipt(self, row):
        if row.get("output"):
            receipt = {
                **row,
                "campaign_id": self.state["campaign_id"],
                "source_sha": self.state["source_sha"],
                "config_sha256": self.identity,
                "artifacts": self.config.get("artifacts", {}),
                "command_wall_ns": None,
                "command_wall_unavailable_reason": "no validated in-Sandbox monotonic timer registered",
            }
            save(Path(row["output"]) / "receipt.json", self.redact(receipt))

    def cleanup(self, row, deadline=None):
        if row.get("pending") or row.get("uncertain"):
            row["cleanup"] = "INCOMPLETE"
            row["retained_reason"] = (
                "uncertain prior operation; release requires inspection"
            )
            self.persist()
            return
        if row.get("cleanup") in ("FAIL", "INCOMPLETE", "COMPLETE"):
            return  # A second command is not permission to replay a failed release.
        if deadline is not None:
            try:
                deadline.remaining()
            except measure.BudgetExceeded:
                row["performance_budget_exceeded"] = True
                row["execution"] = "FAIL"
                deadline = None
        deadline = deadline or measure.Deadline.after(
            self.config.get("cleanup_budget_s", 10)
        )
        started = time.monotonic_ns()
        try:
            if row.get("workspace"):
                self.call(
                    row,
                    "cleanup_unmount",
                    ["workspace", "unmount", row["workspace"], "--discard"],
                    deadline,
                )
                row["workspace"] = None
                self.persist()
            if row.get("sandbox_live"):
                self.call(
                    row, "sandbox_close", ["sandbox", "close", row["sandbox"]], deadline
                )
                row["sandbox_live"] = False
                self.persist()
            if row.get("store_live"):
                action = "remove" if row["backend"] == "sqlite" else "disconnect"
                self.call(
                    row, "store_" + action, ["store", action, row["store"]], deadline
                )
                row["store_live"] = False
                self.persist()
            row["cleanup"] = "COMPLETE"
            if kind(row["backend"]) == "postgresql" and row.get("database_allocation"):
                row["postgresql_data"] = "RETAINED_UNTIL_INFRASTRUCTURE_FINISH"
        except (Failure, measure.BudgetExceeded) as error:
            row["cleanup"] = (
                "INCOMPLETE" if getattr(error, "uncertain", False) else "FAIL"
            )
            row["cleanup_reason"] = str(error)
        finally:
            row["cleanup_elapsed_ns"] = time.monotonic_ns() - started
            self.persist()

    def finish(self):
        before = os.statvfs(self.cache)
        for row in self.state["rows"].values():
            self.cleanup(row)
            self.receipt(row)
        retained = [
            row["id"]
            for row in self.state["rows"].values()
            if row["cleanup"] != "COMPLETE"
        ]
        resource_failure = bool(
            self.config.get("shared_infrastructure")
            and not self.config.get("shared_cleanup_complete", False)
        )
        release_blocker = "retained row custody" if retained else None
        for resource in self.state["resources"]:
            if self.config.get("shared_infrastructure"):
                continue
            if not resource.get("owned") or resource.get("released"):
                continue
            if release_blocker:
                resource.setdefault("disposition", "RETAINED")
                resource["retained_reason"] = release_blocker
                resource_failure = True
                continue
            if resource.get("attempted"):
                if resource.get("disposition") in (None, "ATTEMPTED"):
                    resource["disposition"] = "INCOMPLETE"
                resource["retained_reason"] = "prior release attempt is not replayed"
                release_blocker = f"unreleased resource {resource['id']}"
                resource_failure = True
                continue
            argv = resource.get("release_argv")
            if not argv:
                resource["disposition"] = "NO_RELEASE_COMMAND"
                release_blocker = f"unreleased resource {resource['id']}"
                resource_failure = True
                continue
            resource["attempted"] = True
            resource["disposition"] = "ATTEMPTED"
            self.persist()
            self.event(
                "infrastructure_release_intent", resource=resource["id"], argv=argv
            )
            try:
                result = measure.run_command(
                    argv, measure.Deadline.after(25), env=self.env
                )
            except measure.BudgetExceeded as error:
                result = {
                    "process_exit": None,
                    "uncertainty": False,
                    "not_started": True,
                    "error": str(error),
                }
            except BaseException as error:  # noqa: BLE001 -- preserve custody on any provider interruption
                # A killed or interrupted caller cannot prove provider effects stopped.
                result = {
                    "process_exit": None,
                    "uncertainty": True,
                    "error": f"{type(error).__name__}: {error}",
                }
            self.event(
                "infrastructure_release_result", resource=resource["id"], **result
            )
            resource["released"] = result.get("process_exit") == 0 and not result.get(
                "uncertainty"
            )
            resource["disposition"] = (
                "RELEASED"
                if resource["released"]
                else "INCOMPLETE"
                if result.get("uncertainty")
                else "FAIL"
            )
            resource_failure |= not resource["released"]
            if not resource["released"]:
                release_blocker = f"unreleased resource {resource['id']}"
            self.persist()
        pg_live = [
            row for row in self.state["rows"].values() if row.get("database_allocation")
        ]
        disposal_id = self.config.get("postgresql", {}).get("disposal_resource")
        pg_released = any(
            r["id"] == disposal_id and r.get("released")
            for r in self.state["resources"]
        )
        if self.config.get("shared_infrastructure"):
            pg_released = self.config.get("shared_cleanup_complete", False)
        if pg_live and not pg_released:
            resource_failure = True
        for row in pg_live:
            row["postgresql_data"] = "RELEASED" if pg_released else "RETAINED"
            self.receipt(row)
        after = os.statvfs(self.cache)
        known_failure = any(
            row["cleanup"] == "FAIL" for row in self.state["rows"].values()
        ) or any(
            resource.get("disposition") == "FAIL"
            for resource in self.state["resources"]
        )
        self.state["cleanup"] = (
            "FAIL"
            if known_failure
            else "INCOMPLETE"
            if retained or resource_failure
            else "COMPLETE"
        )
        receipt = {
            "cleanup": self.state["cleanup"],
            "retained_rows": retained,
            "resources": self.state["resources"],
            "available_bytes_delta": after.f_bavail * after.f_frsize
            - before.f_bavail * before.f_frsize,
        }
        self.event("finish", **receipt)
        self.persist()
        save(self.cache / "cleanup.json", self.redact(receipt))
        return receipt


@contextlib.contextmanager
def campaign_lock(cache):
    directory = Path(cache)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise Failure("campaign already has an active owner") from error
        yield


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run", "finish"))
    parser.add_argument("--environment", required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--case", choices=CELLS, action="append")
    parser.add_argument("--machine", choices=MACHINES, action="append")
    parser.add_argument("--backend", choices=ARMS, action="append")
    parser.add_argument("--matrix", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    campaign = None
    try:
        config = json.loads(Path(args.environment).read_text())
        if not re.fullmatch(r"[a-z0-9-]{1,24}", config["campaign_id"]):
            raise Failure(
                "campaign_id must contain 1–24 lowercase letters, digits or hyphens"
            )
        if not re.fullmatch(r"[a-f0-9]{40}", config["source_sha"]):
            raise Failure("source_sha must be a full commit identity")
        if not Path(config["home"]).is_absolute():
            raise Failure("LayerFS home must be absolute")
        selected = selections(
            args.case or CELLS,
            args.machine or MACHINES,
            args.backend or ARMS,
            **matrix_options(config),
        )
        if args.action != "finish" and not args.matrix and len(selected) != 1:
            raise Failure("select one --case/--machine/--backend or use --matrix")
        if args.action == "run" and not args.output:
            raise Failure("run requires fresh --output")
        with campaign_lock(args.cache):
            campaign = Campaign(config, args.cache)
            if args.action == "finish":
                result = campaign.finish()
                print(json.dumps(result))
                return 0 if result["cleanup"] == "COMPLETE" else 1
            outcomes = []
            for selection in selected:
                if args.action == "prepare":
                    row = campaign.prepare(selection)
                else:
                    destination = Path(args.output)
                    if args.matrix:
                        destination = destination / selection["id"]
                    row = campaign.execute(selection, destination, args.verify)
                outcomes.append(row)
                print(
                    json.dumps(
                        {
                            key: row[key]
                            for key in ("id", "preparation", "execution", "cleanup")
                        }
                    ),
                    flush=True,
                )
                if row.get("uncertain"):
                    break
            failed = any(
                row["preparation"] not in ("READY", "CONSUMED")
                or (
                    args.action == "run"
                    and (
                        row["execution"] != "PASS"
                        or row["cleanup"] != "COMPLETE"
                        or row["verification"] == "FAIL"
                        or (args.verify and row["verification"] != "PASS")
                    )
                )
                for row in outcomes
            )
            if failed or (args.action == "run" and args.matrix):
                campaign.finish()
            return (
                1
                if failed or campaign.state["cleanup"] in ("FAIL", "INCOMPLETE")
                else 0
            )
    except (Failure, OSError, ValueError, KeyError, KeyboardInterrupt) as error:
        if campaign is not None:
            campaign.event("terminal_failure", reason=str(error))
            campaign.finish()
        print(str(error) or "interrupted", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
