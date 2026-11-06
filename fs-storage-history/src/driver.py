"""Run one fs-storage-history row through the public LayerFS CLI.

A row is one case on Docker with one backend. It owns fresh Stores (one, or
one per project for H06). Every CLI call goes through `Custody.call`, which
writes an intent before the call and its result after, refuses to run while
an earlier call is unresolved, and classifies uncertainty the same way as
`shared/src/runner.py` `Campaign.call`. Nothing is retried or replayed; a
failed or uncertain call ends the row as FAIL and keeps its evidence.

Measurements are taken only at quiesced boundaries: no Workspace mounted and
no Sandbox open (after each Store's setup, after each project Init, after each
Branch's Sandbox is closed, and at the end of each Store).
"""

import contextlib
import hashlib
import json
import os
import re
import shlex
import time
from pathlib import Path

import cases
import measure
import model

IMAGE_MODEL = "/opt/fs-storage-history/model.py"
COMMAND_TIMEOUT_S = 110  # every command is bounded below two minutes
COMMIT_PAGE_SIZE = 100
UNCERTAIN_CODES = ("Unknown", "Unresolved", "Failed")


class Failure(Exception):
    def __init__(self, message, uncertain=False):
        super().__init__(message)
        self.uncertain = uncertain


def save(path, value):
    temporary = Path(str(path) + ".tmp")
    with temporary.open("w") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def append(path, value):
    with Path(path).open("a") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


class Custody:
    """Intent/result ledger and live-resource record for one row."""

    def __init__(self, config, output, env):
        self.config = config
        self.output = Path(output)
        self.env = env
        self.ledger = self.output / "ledger.jsonl"
        self.state_path = self.output / "custody.json"
        self.state = {"pending": None, "uncertain": False, "stores": {}, "sandboxes": {},
                      "workspaces": {}, "calls": 0}
        self.persist()

    def persist(self):
        save(self.state_path, self.state)

    def call(self, phase, argv, cli=True, timeout=COMMAND_TIMEOUT_S, output_limit=1 << 20):
        if self.state["pending"] or self.state["uncertain"]:
            raise Failure("unresolved prior operation; inspect without replay", True)
        command = [self.config["cli"], *argv] if cli else list(argv)
        self.state["pending"] = {"phase": phase, "argv": command}
        self.state["calls"] += 1
        self.persist()
        append(self.ledger, {"event": "intent", "phase": phase, "argv": command,
                             "time_ns": time.time_ns()})
        try:
            result = measure.run_command(command, measure.Deadline.after(min(timeout, 115)),
                                         env=self.env, output_limit=output_limit)
        except BaseException:
            self.state["uncertain"] = True
            self.persist()
            raise
        append(self.ledger, {"event": "result", "phase": phase, "time_ns": time.time_ns(),
                             **{k: result.get(k) for k in (
                                 "process_exit", "elapsed_ns", "stdout", "stderr",
                                 "output_truncated", "timed_out", "uncertainty", "error")}})
        self.state["pending"] = None
        uncertain = bool(result.get("uncertainty") or result.get("timed_out"))
        if result.get("process_exit") != 0:
            refusal = {}
            with contextlib.suppress(ValueError, TypeError):
                parsed = json.loads(result.get("stderr", ""))
                if isinstance(parsed, dict):
                    refusal = parsed
            code = result.get("process_exit")
            if cli:
                uncertain |= isinstance(code, int) and code < 0
                uncertain |= code == 125 and not refusal.get("code")
                uncertain |= code is None
            uncertain |= refusal.get("code") in UNCERTAIN_CODES
            self.state["uncertain"] = uncertain
            self.persist()
            detail = refusal.get("code") or (result.get("stderr") or "")[-300:]
            raise Failure(f"{phase}: exit {code} {detail}".strip(), uncertain)
        if not cli:
            self.persist()
            return result
        try:
            value = json.loads(result["stdout"])
            if not isinstance(value, dict) or result.get("output_truncated"):
                raise ValueError("expected one complete JSON object")
        except (ValueError, KeyError, TypeError) as error:
            self.state["uncertain"] = True
            self.persist()
            raise Failure(f"{phase}: malformed result: {error}", True) from error
        self._track(argv, value)
        self.persist()
        value["_elapsed_ns"] = result.get("elapsed_ns")
        if argv[:2] == ["workspace", "exec"]:
            if value.get("truncated"):
                raise Failure(f"{phase}: workload output truncated")
            if value.get("exit_code") != 0:
                raise Failure(f"{phase}: workload exit {value.get('exit_code')}: "
                              f"{(value.get('stderr') or '')[-300:]}")
        return value

    def _track(self, argv, value):
        family = argv[:2]
        if family in (["store", "create"], ["store", "connect"]):
            self.state["stores"][argv[2]] = {"backend": "sqlite" if family[1] == "create"
                                             else "postgresql", "live": True}
        elif family in (["store", "remove"], ["store", "disconnect"]):
            self.state["stores"][argv[2]]["live"] = False
        elif family == ["sandbox", "create"]:
            self.state["sandboxes"][argv[3]] = True
        elif family == ["sandbox", "close"]:
            self.state["sandboxes"][argv[2]] = False
        elif family == ["workspace", "mount"]:
            if not value.get("ws"):
                self.state["uncertain"] = True
                raise Failure("mount result has no workspace identity", True)
            self.state["workspaces"][value["ws"]] = True
        elif family == ["workspace", "unmount"]:
            self.state["workspaces"][argv[2]] = False

    def live(self, kind):
        return [name for name, value in self.state[kind].items()
                if (value.get("live") if isinstance(value, dict) else value)]


class Row:
    def __init__(self, config, case_id, backend, output, base_state, base_dir, env):
        if backend not in ("sqlite", "postgresql"):
            raise ValueError(backend)
        self.config = config
        self.case_id = case_id
        self.backend = backend
        self.output = Path(output)
        if self.output.exists():
            raise Failure("output directory exists; retained evidence is never overwritten")
        self.output.mkdir(parents=True)
        self.base_state = base_state
        self.base_dir = str(base_dir)
        self.custody = Custody(config, self.output, env)
        self.result = {
            "case": case_id,
            "backend": backend,
            "machine": "docker",
            "campaign_id": config["campaign_id"],
            "source_sha": config["source_sha"],
            "artifacts": config.get("artifacts", {}),
            "execution": "NOT_RUN",
            "verification": "NOT_RUN",
            "cleanup": "NOT_RUN",
            "performance": "INELIGIBLE",
            "stores": [],
        }

    # -- naming --------------------------------------------------------------

    def store_name(self, suffix):
        short = "sq" if self.backend == "sqlite" else "pg"
        return f"fsh-{self.config['campaign_tag']}-{self.case_id.lower()}-{short}{suffix}"

    def database_url(self, suffix):
        key = f"{self.case_id}{suffix}"
        url = self.config["postgresql"]["databases"].get(key)
        if not url:
            raise Failure(f"no pre-created PostgreSQL database for {key}")
        return url

    # -- probes --------------------------------------------------------------

    def probe(self, store, label):
        status = self.custody.call(f"probe_{label}", ["store", "status", store])
        sample = {"label": label, "state": status.get("state"), "time_ns": time.time_ns()}
        if status.get("state") != "idle":
            raise Failure(f"store not quiesced at {label}: state {status.get('state')}")
        if self.backend == "sqlite":
            file = status.get("file") or {}
            if not file.get("exists") or file.get("bytes") is None:
                raise Failure(f"store status has no file bytes at {label}")
            sample.update(file_bytes=file["bytes"], wal_bytes=file.get("wal_bytes") or 0)
            sample["store_bytes"] = sample["file_bytes"] + sample["wal_bytes"]
            sample["allocated"] = self.allocated(store, label)
        else:
            server = status.get("server") or {}
            schemas = server.get("schemas") or {}
            size = schemas.get("layerfs")
            if isinstance(size, dict):
                size = size.get("bytes", size.get("total_bytes"))
            if not isinstance(size, int):
                raise Failure(f"store status has no server.schemas.layerfs at {label}: {server}")
            sample["store_bytes"] = size
            sample["server"] = server
            sample["server_wal"] = "UNAVAILABLE"
        return sample

    def allocated(self, store, label):
        worker = self.config["docker_worker"]
        root = f"/layerfs/data/store/{store}"
        result = self.custody.call(
            f"alloc_{label}",
            ["docker", "exec", worker, "stat", "-c", "%n %s %b %B",
             f"{root}/store.sqlite", f"{root}/store.sqlite-wal"],
            cli=False, timeout=30,
        )
        files = {}
        for line in result["stdout"].splitlines():
            name, size, blocks, unit = line.rsplit(" ", 3)
            files[name.rsplit("/", 1)[-1]] = {"bytes": int(size), "allocated": int(blocks) * int(unit)}
        return {"files": files, "allocated_bytes": sum(f["allocated"] for f in files.values())}

    # -- the row -------------------------------------------------------------

    def run(self):
        started = time.monotonic_ns()
        plan = cases.build_plan(self.case_id, self.base_state)
        self.result["workload"] = cases.provenance(self.case_id, plan)
        self.result["execution"] = "ATTEMPTED"
        self.save()
        try:
            for store in plan["stores"]:
                self.run_store(store)
            self.result["execution"] = "PASS"
            self.result["verification"] = (
                "PASS" if all(b["verification"] == "PASS" for s in self.result["stores"]
                              for p in s["projects"] for b in p["branches"]) else "FAIL")
            if self.result["verification"] != "PASS":
                self.result["execution"] = "FAIL"
        except Failure as error:
            self.result["execution"] = "FAIL"
            self.result["reason"] = str(error)
            self.result["uncertain"] = error.uncertain or self.custody.state["uncertain"]
        except KeyboardInterrupt:
            self.result["execution"] = "INCOMPLETE"
            self.result["reason"] = "interrupted"
            raise
        finally:
            self.result["wall_ns_ineligible"] = time.monotonic_ns() - started
            self.cleanup()
            self.result["custody"] = self.custody.state
            self.summarize()
            self.save()
        return self.result

    def save(self):
        save(self.output / "result.json", self.result)

    def run_store(self, store_plan):
        name = self.store_name(store_plan["suffix"])
        record = {"store": name, "suffix": store_plan["suffix"], "probes": [], "projects": []}
        self.result["stores"].append(record)
        c = self.custody
        if self.backend == "sqlite":
            c.call("store_create", ["store", "create", name])
        else:
            pg = self.config["postgresql"]
            url = self.database_url(store_plan["suffix"])
            record["database"] = url
            c.call("store_connect", ["store", "connect", name, url, "--password",
                                     f"env:{pg['password_env']}", "--synchronous-commit", "off"])
        c.call("init_floor", ["project", "init", f"{name}/{cases.FLOOR_PROJECT}",
                              self.config["empty_source"]])
        if self.backend == "sqlite":
            c.call("store_push", ["store", "push", name, "docker"])
        record["floor"] = self.probe(name, "floor")
        record["probes"].append(record["floor"])
        for project in store_plan["projects"]:
            init = c.call(f"init_{project['name']}", ["project", "init",
                                                      f"{name}/{project['name']}", self.base_dir])
            sample = self.probe(name, f"init_{project['name']}")
            record["probes"].append(sample)
            record["projects"].append({"name": project["name"], "init": {
                k: init.get(k) for k in ("layer", "root", "created", "_elapsed_ns")},
                "after_init": sample["store_bytes"], "branches": []})
        record["init_floor"] = record["probes"][-1]
        self.save()
        for project, out in zip(store_plan["projects"], record["projects"]):
            for branch in project["branches"]:
                out["branches"].append(self.run_branch(name, project["name"], branch, record))
                self.save()
        for project, out in zip(store_plan["projects"], record["projects"]):
            for branch in out["branches"]:
                branch["commit_list"] = self.collect(name, project["name"], branch)
        record["final"] = self.probe(name, "final")
        record["probes"].append(record["final"])
        self.save()

    def run_branch(self, store, project, branch, record):
        c = self.custody
        out = {"name": branch["name"], "from": branch["from"], "seed": branch["seed"],
               "commits": branch["commits"], "ops_sha256": branch["ops_sha256"],
               "oracle": {k: branch["head"][k] for k in ("files", "links", "bytes", "sha256")},
               "verification": "NOT_RUN", "commit_results": []}
        fork = c.call(f"fork_{project}_{branch['name']}",
                      ["branch", "fork", f"{store}/{project}", branch["name"], branch["from"]])
        out["fork"] = {k: fork.get(k) for k in ("kind", "base", "head")}
        sandbox = f"{store}-{project}-{branch['name']}"
        c.call("sandbox_create", ["sandbox", "create", f"{store}/{project}", sandbox, "docker"])
        mount = c.call("mount", ["workspace", "mount", sandbox, branch["name"], "--name", "w"])
        ws = mount["ws"]
        for step, encoded in enumerate(branch["steps"], 1):
            applied = c.call(f"exec_{step}", ["workspace", "exec", ws, shlex.join(
                ["python3", IMAGE_MODEL, "apply", encoded])])
            counts = json.loads(applied["stdout"].strip().splitlines()[-1])["applied"]
            if sum(counts.values()) != model.OPS_PER_COMMIT:
                raise Failure(f"step {step} applied {counts}")
            commit = c.call(f"commit_{step}", ["workspace", "commit", ws])
            if commit.get("kind") != "Committed":
                raise Failure(f"step {step}: Commit answered {commit.get('kind')}", True)
            info = commit.get("commit") or {}
            out["commit_results"].append({
                **{k: info.get(k) for k in ("id", "logical", "new_canonical", "new_stored",
                                            "new_metadata")},
                "exec_ns_ineligible": applied.get("_elapsed_ns"),
                "commit_ns_ineligible": commit.get("_elapsed_ns")})
        c.call("unmount", ["workspace", "unmount", ws])
        # Final-state verification of the committed head, in a fresh mount.
        mount = c.call("verify_mount", ["workspace", "mount", sandbox, branch["name"], "--name", "v"])
        ws = mount["ws"]
        manifest = c.call("verify_exec", ["workspace", "exec", ws, shlex.join(
            ["python3", IMAGE_MODEL, "manifest"])])
        c.call("verify_unmount", ["workspace", "unmount", ws])
        c.call("sandbox_close", ["sandbox", "close", sandbox])
        actual = json.loads(manifest["stdout"])
        out["actual"] = {k: actual.get(k) for k in ("files", "links", "bytes", "sha256",
                                                     "empty_dirs", "other")}
        if (actual.get("sha256") == branch["head"]["sha256"] and actual.get("empty_dirs") == 0
                and actual.get("other") == 0):
            out["verification"] = "PASS"
        else:
            out["verification"] = "FAIL"
            out["mismatch"] = mismatch(branch["state"], branch["head"], actual)
        sample = self.probe(store, f"branch_{project}_{branch['name']}")
        record["probes"].append(sample)
        out["after_branch"] = sample["store_bytes"]
        return out

    def collect(self, store, project, branch):
        """Every Commit of the Branch from `commit list`, followed to the last page."""
        items, position, pages = [], None, 0
        while True:
            argv = ["commit", "list", f"{store}/{project}", branch["name"],
                    "--page-size", str(COMMIT_PAGE_SIZE)]
            if position is not None:
                argv += ["--page-pos", str(position)]
            page = self.custody.call(f"commit_list_{project}_{branch['name']}_{pages}", argv)
            pages += 1
            items.extend(page.get("items") or [])
            position = page.get("next_page_pos")
            if not page.get("has_more") or position is None:
                break
            if pages > 1000:
                raise Failure("commit list did not end")
        fields = ("id", "branch", "parent", "logical", "new_canonical", "new_stored",
                  "new_metadata", "time")
        return {"pages": pages, "items": [{k: item.get(k) for k in fields} for item in items]}

    def cleanup(self):
        c = self.custody
        if c.state["pending"] or c.state["uncertain"]:
            self.result["cleanup"] = "INCOMPLETE"
            self.result["cleanup_reason"] = "uncertain prior operation; release requires inspection"
            return
        try:
            for ws in c.live("workspaces"):
                c.call("cleanup_unmount", ["workspace", "unmount", ws, "--discard"])
            for sandbox in c.live("sandboxes"):
                c.call("cleanup_close", ["sandbox", "close", sandbox])
            for store in c.live("stores"):
                action = "remove" if c.state["stores"][store]["backend"] == "sqlite" else "disconnect"
                c.call(f"store_{action}", ["store", action, store])
            self.result["cleanup"] = "COMPLETE"
            if self.backend == "postgresql":
                self.result["postgresql_data"] = "RETAINED_UNTIL_INFRASTRUCTURE_FINISH"
        except Failure as error:
            self.result["cleanup"] = "INCOMPLETE" if error.uncertain else "FAIL"
            self.result["cleanup_reason"] = str(error)

    # -- accounting ------------------------------------------------------------

    def summarize(self):
        totals = {"floor": 0, "init_floor": 0, "final": 0, "net": 0, "init": 0, "growth": 0,
                  "new_stored": 0, "new_metadata": 0, "new_canonical": 0, "logical_heads": 0,
                  "commits": 0}
        complete = True
        for record in self.result["stores"]:
            if "final" not in record:
                complete = False
                continue
            floor = record["floor"]["store_bytes"]
            init_floor = record["init_floor"]["store_bytes"]
            final = record["final"]["store_bytes"]
            seen = {}
            for project in record["projects"]:
                for branch in project["branches"]:
                    own = {c["id"] for c in branch["commit_results"]}
                    listed = (branch.get("commit_list") or {}).get("items", [])
                    for item in listed:
                        seen[item["id"]] = item
                    missing = own - {i["id"] for i in listed}
                    branch["listed_commits"] = len(listed)
                    branch["missing_from_list"] = sorted(missing)
                    mine = [i for i in listed if i["id"] in own]
                    branch["sum_new_stored"] = sum(i["new_stored"] or 0 for i in mine)
                    branch["sum_new_metadata"] = sum(i["new_metadata"] or 0 for i in mine)
                    branch["head_logical"] = listed[0]["logical"] if listed else None
                    totals["logical_heads"] += branch["head_logical"] or 0
            s_stored = sum(i["new_stored"] or 0 for i in seen.values())
            s_meta = sum(i["new_metadata"] or 0 for i in seen.values())
            s_canon = sum(i["new_canonical"] or 0 for i in seen.values())
            record["accounting"] = {
                "floor": floor, "init_floor": init_floor, "final": final,
                "net": final - floor, "init": init_floor - floor, "growth": final - init_floor,
                "commits": len(seen), "sum_new_stored": s_stored, "sum_new_metadata": s_meta,
                "sum_new_canonical": s_canon,
                "unattributed": (final - floor) - (s_stored + s_meta),
                "unattributed_after_init": (final - init_floor) - (s_stored + s_meta),
            }
            for key, value in (("floor", floor), ("init_floor", init_floor), ("final", final),
                               ("net", final - floor), ("init", init_floor - floor),
                               ("growth", final - init_floor), ("new_stored", s_stored),
                               ("new_metadata", s_meta), ("new_canonical", s_canon),
                               ("commits", len(seen))):
                totals[key] += value
        totals["unattributed"] = totals["net"] - (totals["new_stored"] + totals["new_metadata"])
        totals["unattributed_after_init"] = totals["growth"] - (
            totals["new_stored"] + totals["new_metadata"])
        totals["complete"] = complete
        self.result["totals"] = totals


def mismatch(state, oracle, actual):
    """Name the oracle paths in buckets whose digests differ (at most 20)."""
    differing = [i for i, (a, b) in enumerate(zip(oracle["buckets"], actual.get("buckets") or []))
                 if a != b]
    paths = [p for p in sorted(state.entries) if model.bucket_of(p) in set(differing)]
    return {"buckets": differing[:64], "oracle_paths": paths[:20],
            "oracle_counts": {k: oracle[k] for k in ("files", "links", "bytes")},
            "actual_counts": {k: actual.get(k) for k in ("files", "links", "bytes",
                                                         "empty_dirs", "other")}}


def environment(config):
    env = dict(os.environ)
    env.update(config.get("environment", {}))
    env["LAYERFS_HOME"] = config["home"]
    env["LAYERFS_CONSTRUCTION_WORKERS"] = "1"
    return env


def docker_worker(home):
    identity = json.loads((Path(home) / "layerfs.json").read_text())["id"]
    if not re.fullmatch(r"[0-9a-f]{32}", identity):
        raise Failure("home id is not a 32-digit hex identity")
    return f"lfs-{identity[:8]}-docker"


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
