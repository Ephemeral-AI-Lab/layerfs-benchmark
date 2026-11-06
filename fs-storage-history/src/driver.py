"""Run one fs-storage-history row through the public LayerFS CLI.

A row is one case on Docker with one backend. It owns fresh Stores (one, or
one per project for H06). Every CLI call goes through the shared
`storage.Driver`, i.e. one bounded `runner.Campaign.call` with an intent in
the ledger first; nothing is retried or replayed. A failed or uncertain call
ends the row as FAIL; a failed Commit keeps its Store as evidence.

Each row has its own campaign cache (`<output>/campaign`), so campaign state
stays small however many Commits the row makes.

Probes are taken only at quiesced boundaries (no Workspace mounted, no
Sandbox open): the empty-Store floor, after each project Init, after each
Branch's Sandbox is closed, and at the end of each Store.
"""

import json
import shlex
import time
from pathlib import Path

import cases
import measure
import model
import storage

IMAGE_MODEL = "/opt/fs-storage-history/model.py"
COMMAND_TIMEOUT_S = 110  # every command is bounded below two minutes


def save(path, value):
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


class Row:
    def __init__(self, config, case_id, backend, output, base_state, base_dir):
        if backend not in ("sqlite", "postgresql"):
            raise ValueError(backend)
        self.config = config
        self.case_id = case_id
        self.backend = backend
        self.output = Path(output)
        if self.output.exists():
            raise storage.StorageFailure("output exists; retained evidence is never overwritten")
        self.output.mkdir(parents=True)
        self.base_state = base_state
        self.base_dir = str(base_dir)
        self.runner = storage.load_runner(cases)
        self.campaign = self.runner.Campaign(config, self.output / "campaign")
        row_id = f"{case_id}/docker/{backend}"
        self.row = self.campaign.state["rows"].setdefault(row_id, {
            "id": row_id, "cell": case_id, "machine": "docker", "backend": backend,
            "pending": None, "uncertain": False, "execution": "NOT_RUN",
            "verification": "NOT_RUN", "cleanup": "NOT_RUN", "performance": "INELIGIBLE",
        })
        self.campaign.persist()
        self.driver = storage.Driver(self.campaign, self.row, COMMAND_TIMEOUT_S)
        self.allocated = None
        if backend == "sqlite":
            self.allocated = {"volume": storage.docker_volume_for(config["home"]),
                              "image": config["artifacts"]["sandbox_image"]}
        self.result = {
            "case": case_id, "backend": backend, "machine": "docker",
            "campaign_id": config["campaign_id"], "source_sha": config["source_sha"],
            "artifacts": config.get("artifacts", {}), "policy": storage.POLICY,
            "execution": "NOT_RUN", "verification": "NOT_RUN", "cleanup": "NOT_RUN",
            "performance": "INELIGIBLE", "stores": [],
        }

    def errors(self):
        return (self.runner.Failure, storage.StorageFailure, measure.BudgetExceeded)

    # -- naming --------------------------------------------------------------

    def store_name(self, suffix):
        short = "sq" if self.backend == "sqlite" else "pg"
        return f"fsh-{self.config['campaign_tag']}-{self.case_id.lower()}-{short}{suffix}"

    # -- the row -------------------------------------------------------------

    def run(self):
        started = time.monotonic_ns()
        plan = cases.build_plan(self.case_id, self.base_state)
        self.result["workload"] = cases.provenance(self.case_id, plan)
        self.result["execution"] = self.row["execution"] = "ATTEMPTED"
        self.campaign.persist()
        self.save()
        try:
            for store in plan["stores"]:
                self.run_store(store)
            verdicts = [b["verification"] for s in self.result["stores"]
                        for p in s["projects"] for b in p["branches"]]
            self.result["verification"] = "PASS" if verdicts and all(
                v == "PASS" for v in verdicts) else "FAIL"
            self.result["execution"] = "PASS" if self.result["verification"] == "PASS" else "FAIL"
            if self.result["execution"] != "PASS":
                self.result["reason"] = "final-state verification failed"
        except self.errors() as error:
            self.result["execution"] = "FAIL"
            self.result["reason"] = str(error)
            self.result["uncertain"] = bool(getattr(error, "uncertain", False)
                                            or self.row.get("uncertain"))
        except KeyboardInterrupt:
            self.result["execution"] = "INCOMPLETE"
            self.result["reason"] = "interrupted"
            raise
        finally:
            self.result["wall_ns_ineligible"] = time.monotonic_ns() - started
            self.row["execution"] = self.result["execution"]
            self.row["verification"] = self.result["verification"]
            self.result["cleanup"] = self.driver.cleanup(release_stores=True)
            for key in ("retained_reason", "cleanup_reason", "postgresql_data"):
                if key in self.row:
                    self.result[key] = self.row[key]
            self.result["calls"] = self.row.get("sequence", 0)
            self.summarize()
            self.save()
        return self.result

    def save(self):
        save(self.output / "result.json", self.result)

    def run_store(self, store_plan):
        name = self.store_name(store_plan["suffix"])
        record = {"store": name, "suffix": store_plan["suffix"], "probes": [], "projects": []}
        self.result["stores"].append(record)
        d = self.driver
        if self.backend == "sqlite":
            d.store_create(name)
        else:
            url = self.config["postgresql"]["databases"].get(f"{self.case_id}{store_plan['suffix']}")
            if not url:
                raise storage.StorageFailure(f"no pre-created database for {name}")
            record["database"] = url
            d.store_connect(name, url, self.config["postgresql"]["password_env"])
        d.project_init(f"{name}/{cases.FLOOR_PROJECT}", self.config["empty_source"])
        if self.backend == "sqlite":
            d.store_push(name, "docker")
        record["floor"] = self.probe(name, "floor", record)
        for project in store_plan["projects"]:
            init = d.project_init(f"{name}/{project['name']}", self.base_dir)
            sample = self.probe(name, f"init_{project['name']}", record)
            record["projects"].append({
                "name": project["name"], "init_ns_ineligible": init.get("_elapsed_ns"),
                "after_init": sample["total_bytes"], "branches": []})
        record["init_floor"] = record["probes"][-1]
        self.save()
        for project, out in zip(store_plan["projects"], record["projects"]):
            for branch in project["branches"]:
                out["branches"].append(self.run_branch(name, project["name"], branch, record))
                self.save()
        for project, out in zip(store_plan["projects"], record["projects"]):
            for branch in out["branches"]:
                history = d.commits(f"{name}/{project['name']}", branch["name"])
                branch["history"] = history["commits"]
                branch["history_pages"] = history["pages"]
        record["final"] = self.probe(name, "final", record)
        self.save()

    def probe(self, store, label, record):
        sample = self.driver.probe(store, label, self.allocated)
        compact = {k: sample.get(k) for k in (
            "total_bytes", "file_bytes", "wal_bytes", "schema_bytes", "allocated_bytes",
            "allocated_status", "server_wal_lsn")}
        compact["label"] = label
        if self.backend == "postgresql":
            compact.setdefault("server_wal", "UNAVAILABLE")
        record["probes"].append(compact)
        return compact

    def run_branch(self, store, project, branch, record):
        d = self.driver
        out = {"name": branch["name"], "from": branch["from"], "seed": branch["seed"],
               "commits": branch["commits"], "ops_sha256": branch["ops_sha256"],
               "oracle": {k: branch["head"][k] for k in ("files", "links", "bytes", "sha256")},
               "verification": "NOT_RUN", "commit_results": []}
        full = f"{store}/{project}"
        fork = d.fork(full, branch["name"], branch["from"])
        out["fork"] = {k: fork.get(k) for k in ("kind", "base", "head")}
        sandbox = f"{store}-{project}-{branch['name']}"
        d.sandbox_create(full, sandbox, "docker")
        ws = d.mount(sandbox, branch["name"], "w")
        for step, encoded in enumerate(branch["steps"], 1):
            applied = d.exec(ws, shlex.join(["python3", IMAGE_MODEL, "apply", encoded]),
                             phase=f"exec_{branch['name']}_{step}")
            counts = json.loads(applied["stdout"].strip().splitlines()[-1])["applied"]
            if sum(counts.values()) != model.OPS_PER_COMMIT:
                raise storage.StorageFailure(f"step {step} applied {counts}")
            try:
                commit = d.commit(ws, label=f"{project}/{branch['name']}/{step}")
            except self.errors():
                self.row["commit_failed"] = True
                self.campaign.persist()
                raise
            info = commit.get("commit") or {}
            out["commit_results"].append({
                **{k: info.get(k) for k in ("id", "logical", "new_canonical", "new_stored",
                                            "new_metadata")},
                "applied": counts})
        d.unmount(ws)
        # Final-state verification of the committed head, once, in a fresh mount.
        ws = d.mount(sandbox, branch["name"], "v")
        manifest = d.exec(ws, shlex.join(["python3", IMAGE_MODEL, "manifest"]),
                          phase=f"verify_{branch['name']}")
        d.unmount(ws)
        d.sandbox_close(sandbox)
        actual = json.loads(manifest["stdout"])
        out["actual"] = {k: actual.get(k) for k in ("files", "links", "bytes", "sha256",
                                                     "empty_dirs", "other")}
        if (actual.get("sha256") == branch["head"]["sha256"] and actual.get("empty_dirs") == 0
                and actual.get("other") == 0):
            out["verification"] = "PASS"
        else:
            out["verification"] = "FAIL"
            out["mismatch"] = mismatch(branch["state"], branch["head"], actual)
        sample = self.probe(store, f"branch_{project}_{branch['name']}", record)
        out["after_branch"] = sample["total_bytes"]
        return out

    # -- accounting ------------------------------------------------------------

    def summarize(self):
        totals = {k: 0 for k in ("floor", "init_floor", "final", "net", "init", "growth",
                                 "sum_new_stored", "sum_new_metadata", "sum_new_canonical",
                                 "commits", "head_logical", "net_allocated")}
        complete = bool(self.result["stores"])
        for record in self.result["stores"]:
            if "final" not in record:
                complete = False
                continue
            floor = record["floor"]["total_bytes"]
            init_floor = record["init_floor"]["total_bytes"]
            final = record["final"]["total_bytes"]
            seen = {}
            previous = init_floor
            for project in record["projects"]:
                for branch in project["branches"]:
                    history = branch.get("history") or []
                    own = {c["id"] for c in branch["commit_results"]}
                    for item in history:
                        seen[item["id"]] = item
                    mine = [c for c in history if c["id"] in own]
                    branch["listed_commits"] = len(history)
                    branch["missing_from_list"] = sorted(own - {c["id"] for c in history})
                    branch["sum_new_stored"] = sum(c["new_stored"] for c in mine)
                    branch["sum_new_metadata"] = sum(c["new_metadata"] for c in mine)
                    branch["head_logical"] = history[-1]["logical"] if history else None
                    branch["marginal_bytes"] = branch["after_branch"] - previous
                    previous = branch["after_branch"]
                    totals["head_logical"] += branch["head_logical"] or 0
                branches = project["branches"]
                project["sum_new_stored"] = sum(b["sum_new_stored"] for b in branches)
                project["sum_new_metadata"] = sum(b["sum_new_metadata"] for b in branches)
            s_stored = sum(c["new_stored"] for c in seen.values())
            s_meta = sum(c["new_metadata"] for c in seen.values())
            s_canon = sum(c["new_canonical"] for c in seen.values())
            alloc = (record["final"].get("allocated_bytes"), record["floor"].get("allocated_bytes"))
            record["accounting"] = {
                "floor": floor, "init_floor": init_floor, "final": final,
                "net": final - floor, "init": init_floor - floor, "growth": final - init_floor,
                "commits": len(seen), "sum_new_stored": s_stored, "sum_new_metadata": s_meta,
                "sum_new_canonical": s_canon,
                "unattributed": (final - floor) - (s_stored + s_meta),
                "unattributed_after_init": (final - init_floor) - (s_stored + s_meta),
                "net_allocated": alloc[0] - alloc[1] if None not in alloc else None,
            }
            for key in ("floor", "init_floor", "final", "net", "init", "growth", "commits"):
                totals[key] += record["accounting"][key]
            totals["sum_new_stored"] += s_stored
            totals["sum_new_metadata"] += s_meta
            totals["sum_new_canonical"] += s_canon
            if record["accounting"]["net_allocated"] is None:
                totals["net_allocated"] = None
            elif totals["net_allocated"] is not None:
                totals["net_allocated"] += record["accounting"]["net_allocated"]
        totals["unattributed"] = totals["net"] - (totals["sum_new_stored"] + totals["sum_new_metadata"])
        totals["unattributed_after_init"] = totals["growth"] - (
            totals["sum_new_stored"] + totals["sum_new_metadata"])
        totals["complete"] = complete
        self.result["totals"] = totals


def mismatch(state, oracle, actual):
    """Name the oracle paths in buckets whose digests differ (at most 20)."""
    differing = {i for i, (a, b) in enumerate(zip(oracle["buckets"], actual.get("buckets") or []))
                 if a != b}
    paths = [p for p in sorted(state.entries) if model.bucket_of(p) in differing]
    return {"buckets": sorted(differing)[:64], "oracle_paths": paths[:20],
            "oracle_counts": {k: oracle[k] for k in ("files", "links", "bytes")},
            "actual_counts": {k: actual.get(k) for k in ("files", "links", "bytes",
                                                         "empty_dirs", "other")}}
