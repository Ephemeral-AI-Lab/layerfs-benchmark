#!/usr/bin/env python3
"""Store-byte measurement and a multi-Commit driver for storage suites.

Storage suites measure how many bytes a LayerFS Store holds; they never time.
Everything here goes through the public CLI via ``runner.Campaign.call``
custody: intent first, one attempt, no retry, CLI exit and Exec ``exit_code``
both checked. Every command gets its own deadline of at most 120 s.

See ``shared/STORAGE.md`` for the API and the measurement contract.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qsl, urlsplit

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
import measure  # noqa: E402

MAX_COMMAND_S = 120
DEFAULT_COMMAND_S = 60
# measure.run_command keeps 64 KiB of stdout; one commit-list item is ~0.6 KB.
DEFAULT_PAGE_SIZE = 40
POLICY = {
    "cas": "BLAKE3 object ids; exact reuse across the whole Store",
    "cdc": "GEAR 8/16/32 KiB (min/avg/max) for files of 128 KiB and up",
    "whole_file_cutoff_bytes": 131072,
    "delta_depth_cap": {"whole_file": 16, "chunk": 8, "metadata": 8},
    "compression": "per-object zstd level 3",
    "layout": "append-only immutable packs stored as Store database rows",
    "note": "fixed at compile time in LayerFS 2.0; recorded, never varied",
}


class StorageFailure(Exception):
    def __init__(self, message, uncertain=False):
        super().__init__(message)
        self.uncertain = uncertain


# --------------------------------------------------------------------------
# Loading the shared runner without a suite ``cases`` module on sys.path.


def load_runner(cases_module):
    """Load shared/src/runner.py with ``cases_module`` as its ``cases`` import."""
    spec = importlib.util.spec_from_file_location("storage_runner", SRC / "runner.py")
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {"cases": cases_module}):
        spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# Pure helpers: parsing and arithmetic. No product calls.


def docker_volume_for(home, machine="docker"):
    """The Docker machine's data volume, ``lfs-<home id[:8]>-<machine>-data``."""
    identity = json.loads((Path(home) / "layerfs.json").read_text())["id"]
    return f"lfs-{identity[:8]}-{machine}-data"


def allocated_argv(volume, image, store):
    """Read-only ``find`` of the SQLite Store files inside the worker volume.

    Prints ``<name> <st_size> <st_blocks>`` (512-byte blocks) for
    ``store.sqlite`` and its ``-wal``/``-shm`` siblings.
    """
    return [
        "docker", "run", "--rm", "--network", "none", "--pull", "never",
        "-v", f"{volume}:/d:ro", "--entrypoint", "find", image,
        f"/d/store/{store}", "-maxdepth", "1", "-name", "store.sqlite*",
        "-printf", "%f %s %b\\n",
    ]


def parse_allocated(stdout):
    files = {}
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) != 3:
            continue
        name, size, blocks = parts[0], int(parts[1]), int(parts[2])
        files[name] = {"size": size, "allocated": blocks * 512}
    if "store.sqlite" not in files:
        raise StorageFailure("allocated probe did not find store.sqlite")
    return files


def parse_status(value, allocated_files=None):
    """Normalize ``layerfs store status`` JSON to one byte record.

    SQLite: ``file.bytes`` (st_size) and ``file.wal_bytes``; ``total_bytes`` is
    their sum. PostgreSQL: ``server.schemas.layerfs`` (sum of
    ``pg_total_relation_size`` incl. TOAST and indexes) is ``total_bytes``.
    """
    kind = value.get("kind")
    record = {
        "backend": kind,
        "state": value.get("state"),
        "holders": value.get("holders"),
        "file_bytes": None,
        "wal_bytes": None,
        "schema_bytes": None,
        "allocated_bytes": None,
        "allocated_status": "UNAVAILABLE",
        "total_bytes": None,
        "raw": value,
    }
    if kind == "sqlite":
        file = value.get("file") or {}
        if not file.get("exists") or not isinstance(file.get("bytes"), int):
            raise StorageFailure("store status has no SQLite file bytes")
        record["file_bytes"] = file["bytes"]
        record["wal_bytes"] = int(file.get("wal_bytes") or 0)
        record["total_bytes"] = record["file_bytes"] + record["wal_bytes"]
        if allocated_files is not None:
            record["allocated_files"] = allocated_files
            record["allocated_bytes"] = sum(
                allocated_files[name]["allocated"]
                for name in ("store.sqlite", "store.sqlite-wal")
                if name in allocated_files
            )
            record["allocated_status"] = "MEASURED"
    elif kind == "postgresql":
        server = value.get("server") or {}
        schema = (server.get("schemas") or {}).get("layerfs")
        if not server.get("reachable") or not isinstance(schema, int):
            raise StorageFailure("store status has no PostgreSQL schema bytes")
        record["schema_bytes"] = schema
        record["total_bytes"] = schema
        record["allocated_status"] = "NOT_APPLICABLE"
    else:
        raise StorageFailure(f"unknown Store kind {kind!r}")
    return record


def pg_lsn_bytes(text):
    """``16/B374D848`` → absolute WAL byte position."""
    high, low = text.strip().split("/")
    return (int(high, 16) << 32) + int(low, 16)


COMMIT_FIELDS = ("logical", "new_canonical", "new_stored", "new_metadata")


def commit_record(item):
    record = {"id": item["id"], "parent": item.get("parent")}
    for field in COMMIT_FIELDS:
        value = item.get(field)
        if not isinstance(value, int):
            raise StorageFailure(f"Commit {item.get('id')} has no integer {field}")
        record[field] = value
    for field in ("branch", "via", "time", "second_parent"):
        record[field] = item.get(field)
    return record


def collect_commits(list_page, project, branch, page_size=DEFAULT_PAGE_SIZE):
    """Follow ``commit list`` to its last page; return Commits oldest first.

    ``list_page(argv)`` returns the parsed JSON object of one CLI call. The
    newest-first first-parent chain must be continuous (each item's parent is
    the next item), ids unique and paging must advance, or this fails rather
    than silently losing Commits.
    """
    items, position, pages = [], None, 0
    while True:
        argv = ["commit", "list", project, branch, "--page-size", str(page_size)]
        if position is not None:
            argv += ["--page-pos", str(position)]
        page = list_page(argv)
        pages += 1
        batch = page.get("items")
        if not isinstance(batch, list):
            raise StorageFailure("commit list returned no items list")
        items.extend(batch)
        if not page.get("has_more"):
            break
        following = page.get("next_page_pos")
        if following is None or (position is not None and following <= position):
            raise StorageFailure("commit list paging did not advance")
        if not batch:
            raise StorageFailure("commit list reported more items after an empty page")
        position = following
    ids = [item.get("id") for item in items]
    if len(set(ids)) != len(ids):
        raise StorageFailure("commit list returned a Commit twice")
    for newer, older in zip(items, items[1:]):
        if newer.get("parent") != older.get("id"):
            raise StorageFailure(
                f"commit list chain broken at {newer.get('id')}: parent "
                f"{newer.get('parent')} != {older.get('id')}"
            )
    records = [commit_record(item) for item in reversed(items)]
    return {"project": project, "branch": branch, "pages": pages, "commits": records}


def total(probes):
    """Sum a list of byte records field by field (None if any is None)."""
    fields = ("file_bytes", "wal_bytes", "schema_bytes", "allocated_bytes", "total_bytes")
    out = {}
    for field in fields:
        values = [probe.get(field) for probe in probes]
        out[field] = None if any(v is None for v in values) else sum(values)
    return out


def summarize(final, floor, histories, references=None, ideal_unique=None):
    """Net bytes, per-Commit sums, unattributed bytes and ratios.

    ``final``/``floor``: byte records (or lists of them, summed). ``histories``:
    ``collect_commits`` results; a Commit listed on several branches counts
    once. ``references``: name → bytes. Ratios are None when undefined.
    """
    final = total(final) if isinstance(final, list) else final
    floor = total(floor) if isinstance(floor, list) else floor
    seen, commits = set(), []
    for history in histories:
        for commit in history["commits"]:
            if commit["id"] not in seen:
                seen.add(commit["id"])
                commits.append(commit)

    def diff(field):
        a, b = final.get(field), floor.get(field)
        return a - b if isinstance(a, int) and isinstance(b, int) else None

    net = diff("total_bytes")
    stored = sum(c["new_stored"] for c in commits)
    metadata = sum(c["new_metadata"] for c in commits)
    logical_sum = sum(c["logical"] for c in commits)

    def per(a, b):
        return a / b if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b > 0 else None

    out = {
        "final_bytes": final.get("total_bytes"),
        "floor_bytes": floor.get("total_bytes"),
        "net_bytes": net,
        "net_file_bytes": diff("file_bytes"),
        "net_wal_bytes": diff("wal_bytes"),
        "net_allocated_bytes": diff("allocated_bytes"),
        "commits": len(commits),
        "sum_logical": logical_sum,
        "final_logical": {
            f"{h['project']}@{h['branch']}": (h["commits"][-1]["logical"] if h["commits"] else 0)
            for h in histories
        },
        "sum_new_canonical": sum(c["new_canonical"] for c in commits),
        "sum_new_stored": stored,
        "sum_new_metadata": metadata,
        "unattributed_bytes": net - (stored + metadata) if net is not None else None,
        "logical_per_net": per(logical_sum, net),
        "net_per_reference": {
            name: per(net, value) for name, value in (references or {}).items()
        },
        "space_amplification": per(net, ideal_unique),
    }
    return out


def safe_database_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ("postgres", "postgresql"):
        return False
    if parsed.password is not None:
        return False
    return not any(
        "password" in key.lower() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)
    )


# --------------------------------------------------------------------------
# The multi-Commit driver: bounded CLI calls under runner.Campaign custody.


class Driver:
    """One storage row's CLI calls, resources and byte probes.

    ``campaign`` is a ``runner.Campaign`` (or anything with its ``call``,
    ``persist`` and ``config``); ``row`` is that row's dict in campaign state.
    The row records every Store, Sandbox and Workspace it owns, so cleanup can
    release exactly those and nothing else.
    """

    def __init__(self, campaign, row, default_timeout_s=DEFAULT_COMMAND_S):
        if not 0 < default_timeout_s <= MAX_COMMAND_S:
            raise ValueError("command timeout must be in (0, 120] seconds")
        self.campaign = campaign
        self.row = row
        self.default_timeout_s = default_timeout_s
        row.setdefault("sequence", 0)
        row.setdefault("owned", {"stores": {}, "sandboxes": {}, "workspaces": {}})
        row.setdefault("probes", {})
        row.setdefault("commit_results", [])

    # -- custody --------------------------------------------------------
    def call(self, phase, argv, timeout_s=None, cli=True, keep_output=2000):
        timeout_s = timeout_s or self.default_timeout_s
        if not 0 < timeout_s <= MAX_COMMAND_S:
            raise ValueError("command timeout must be in (0, 120] seconds")
        self.row["sequence"] += 1
        label = f"{self.row['sequence']:05d}_{phase}"
        try:
            value = self.campaign.call(
                self.row, label, list(argv), measure.Deadline.after(timeout_s), cli=cli
            )
        finally:
            # The ledger keeps full output; keep campaign state compact.
            commands = self.row.get("commands") or []
            if commands and keep_output is not None:
                for key in ("stdout", "stderr"):
                    text = commands[-1].get(key)
                    if isinstance(text, str) and len(text) > keep_output:
                        commands[-1][key] = text[:keep_output] + "…<trimmed; see ledger>"
            self.campaign.persist()
        return value

    def _own(self, kind, key, value):
        self.row["owned"][kind][key] = value
        self.campaign.persist()

    # -- lifecycle ------------------------------------------------------
    def store_create(self, store):
        self.call("store_create", ["store", "create", store])
        self._own("stores", store, {"backend": "sqlite", "live": True})

    def store_connect(self, store, url, password_env, synchronous_commit="off"):
        if not safe_database_url(url):
            raise StorageFailure("PostgreSQL URL must omit passwords and password settings")
        argv = ["store", "connect", store, url, "--password", f"env:{password_env}"]
        if synchronous_commit:
            argv += ["--synchronous-commit", synchronous_commit]
        self.call("store_connect", argv)
        self._own("stores", store, {"backend": "postgresql", "live": True, "database": url})

    def project_init(self, project, source, timeout_s=None):
        return self.call("project_init", ["project", "init", project, str(source)], timeout_s)

    def store_push(self, store, machine, timeout_s=None):
        return self.call("store_push", ["store", "push", store, machine], timeout_s)

    def fork(self, project, name, from_branch, from_commit=None):
        argv = ["branch", "fork", project, name, from_branch]
        if from_commit:
            argv.append(from_commit)
        return self.call("branch_fork", argv)

    def sandbox_create(self, project, sandbox, machine, timeout_s=None):
        self.call("sandbox_create", ["sandbox", "create", project, sandbox, machine], timeout_s)
        self._own("sandboxes", sandbox, {"live": True, "project": project})

    def mount(self, sandbox, branch, name, timeout_s=None):
        value = self.call(
            "mount", ["workspace", "mount", sandbox, branch, "--name", name], timeout_s
        )
        ws = value.get("ws")
        if not ws:
            self.row["uncertain"] = True
            raise StorageFailure("mount result has no workspace identity", True)
        self._own("workspaces", ws, {"live": True, "branch": branch, "sandbox": sandbox})
        return ws

    def exec(self, ws, command, timeout_s=None, phase="exec"):
        return self.call(phase, ["workspace", "exec", ws, command], timeout_s)

    def commit(self, ws, timeout_s=None, allow_up_to_date=False, label=None):
        value = self.call("commit", ["workspace", "commit", ws], timeout_s)
        kind = value.get("kind")
        accepted = ("Committed", "UpToDate") if allow_up_to_date else ("Committed",)
        if kind not in accepted:
            self.row["uncertain"] = kind != "UpToDate"
            raise StorageFailure(f"unexpected Commit result {kind!r}", kind != "UpToDate")
        commit = value.get("commit") or {}
        self.row["commit_results"].append(
            {
                "label": label,
                "ws": ws,
                "kind": kind,
                "id": commit.get("id") or value.get("head"),
                **{field: commit.get(field) for field in COMMIT_FIELDS},
            }
        )
        self.campaign.persist()
        return value

    def unmount(self, ws, discard=False, timeout_s=None):
        argv = ["workspace", "unmount", ws] + (["--discard"] if discard else [])
        self.call("unmount", argv, timeout_s)
        self.row["owned"]["workspaces"][ws]["live"] = False
        self.campaign.persist()

    def sandbox_close(self, sandbox, timeout_s=None):
        self.call("sandbox_close", ["sandbox", "close", sandbox], timeout_s)
        self.row["owned"]["sandboxes"][sandbox]["live"] = False
        self.campaign.persist()

    def store_release(self, store):
        info = self.row["owned"]["stores"][store]
        action = "remove" if info["backend"] == "sqlite" else "disconnect"
        self.call(f"store_{action}", ["store", action, store])
        info["live"] = False
        self.campaign.persist()

    def live(self, kind):
        return [key for key, info in self.row["owned"][kind].items() if info.get("live")]

    # -- measurement ----------------------------------------------------
    def quiesced(self):
        open_ws, open_sb = self.live("workspaces"), self.live("sandboxes")
        if open_ws or open_sb:
            raise StorageFailure(
                f"not quiesced: workspaces {open_ws}, sandboxes {open_sb} still open"
            )

    def probe(self, store, label, allocated=None):
        """Byte record for ``store`` at a quiesced boundary; saved as ``label``.

        ``allocated``: ``{"volume", "image"}`` to read SQLite allocated bytes in
        the Docker worker volume read-only, or None (UNAVAILABLE).
        """
        self.quiesced()
        status = self.call(f"probe_{label}", ["store", "status", store])
        files = None
        if status.get("kind") == "sqlite" and allocated and status.get("machine") != "native":
            result = self.call(
                f"probe_{label}_allocated",
                allocated_argv(allocated["volume"], allocated["image"], store),
                cli=False,
            )
            files = parse_allocated(result.get("stdout", ""))
        if status.get("state") not in ("idle", None) or status.get("holders"):
            raise StorageFailure(f"Store {store} is not idle: {status.get('state')}")
        record = parse_status(status, files)
        record["store"] = store
        wal = self.campaign.config.get("storage", {}).get("server_wal_argv")
        if record["backend"] == "postgresql" and wal:
            lsn = self.call(f"probe_{label}_server_wal", wal, cli=False)
            record["server_wal_lsn"] = lsn.get("stdout", "").strip()
        self.row["probes"].setdefault(label, {})[store] = record
        self.campaign.persist()
        return record

    def commits(self, project, branch, page_size=DEFAULT_PAGE_SIZE):
        history = collect_commits(
            lambda argv: self.call("commit_list", argv), project, branch, page_size
        )
        self.row.setdefault("histories", []).append(history)
        self.campaign.persist()
        return history

    # -- cleanup --------------------------------------------------------
    def cleanup(self, release_stores=True):
        """Release this row's live Workspaces, Sandboxes and (optionally) Stores.

        Never runs after an uncertain operation or a failed Commit: those rows
        keep their Store as evidence (``retained_reason``).
        """
        row = self.row
        if row.get("pending") or row.get("uncertain"):
            row["cleanup"] = "INCOMPLETE"
            row["retained_reason"] = "uncertain prior operation; release requires inspection"
            self.campaign.persist()
            return row["cleanup"]
        try:
            for ws in self.live("workspaces"):
                self.unmount(ws, discard=True)
            for sandbox in self.live("sandboxes"):
                self.sandbox_close(sandbox)
            if row.get("commit_failed"):
                row["cleanup"] = "INCOMPLETE"
                row["retained_reason"] = "failed Commit may leave orphan packs; Store kept"
            else:
                if release_stores:
                    for store in self.live("stores"):
                        self.store_release(store)
                row["cleanup"] = "COMPLETE"
                if any(
                    info.get("backend") == "postgresql"
                    for info in row["owned"]["stores"].values()
                ):
                    row["postgresql_data"] = "RETAINED_UNTIL_INFRASTRUCTURE_FINISH"
        except Exception as error:  # noqa: BLE001 - record, never replay
            row["cleanup"] = "INCOMPLETE" if getattr(error, "uncertain", False) else "FAIL"
            row["cleanup_reason"] = str(error)
        self.campaign.persist()
        return row["cleanup"]


# --------------------------------------------------------------------------
# A standard storage row: fresh Store(s), floor, steps, quiesce, measure,
# verify, release.


def run_row(campaign, row, spec, verify=True):
    """Run one storage row from a declarative ``spec`` (see STORAGE.md).

    spec = {
      "stores": [{"name", "backend": "sqlite"|"postgresql", "url"?,
                  "projects": [{"project": "<store>/<name>", "source": dir}]}],
      "machine": "docker",
      "branches": [{"project", "name", "from": "main", "commit"?}],
      "steps": [{"op": "sandbox"|"mount"|"exec"|"commit"|"unmount"|"close"|"fork", ...}],
      "collect": [{"project", "branch"}],
      "verify": [{"project", "branch", "command", "check": callable(result)->None}],
      "allocated": {"volume", "image"} | None,
      "password_env": "...",
    }
    Returns the row; the row's ``storage`` field holds the summary inputs.
    """
    driver = Driver(campaign, row, spec.get("timeout_s", DEFAULT_COMMAND_S))
    started = time.monotonic_ns()
    row["execution"] = "ATTEMPTED"
    campaign.persist()
    machine = spec["machine"]
    allocated = spec.get("allocated")
    try:
        # Fresh Stores and the empty-Store floor (create/connect + init + push).
        for store in spec["stores"]:
            if store["backend"] == "sqlite":
                driver.store_create(store["name"])
            else:
                driver.store_connect(store["name"], store["url"], spec["password_env"])
            for project in store["projects"]:
                driver.project_init(project["project"], project["source"])
            if store["backend"] == "sqlite" and machine != "native":
                driver.store_push(store["name"], machine, timeout_s=MAX_COMMAND_S)
            driver.probe(store["name"], "floor", allocated)
        for branch in spec.get("branches", []):
            driver.fork(branch["project"], branch["name"], branch.get("from", "main"), branch.get("commit"))
        workspaces = {}
        for step in spec["steps"]:
            run_step(driver, step, workspaces, machine)
        driver.quiesced()
        for store in spec["stores"]:
            driver.probe(store["name"], "final", allocated)
        for item in spec.get("collect", []):
            driver.commits(item["project"], item["branch"])
        row["execution"] = "PASS"
        if verify and spec.get("verify"):
            row["verification"] = "ATTEMPTED"
            campaign.persist()
            for index, item in enumerate(spec["verify"]):
                sandbox = f"{spec['prefix']}-v{index}"
                driver.sandbox_create(item["project"], sandbox, machine)
                ws = driver.mount(sandbox, item["branch"], f"verify{index}")
                result = driver.exec(ws, item["command"], item.get("timeout_s", MAX_COMMAND_S), phase="verify")
                row.setdefault("verify_results", []).append(
                    {"branch": item["branch"], "stdout": result.get("stdout", "")[:4000]}
                )
                item["check"](result)
                driver.unmount(ws)
                driver.sandbox_close(sandbox)
            for store in spec["stores"]:
                driver.probe(store["name"], "post_verify", allocated)
            row["verification"] = "PASS"
            row["correctness"] = "VERIFIED"
        elif not verify:
            row["verification"] = "SKIPPED"
    except Exception as error:  # noqa: BLE001 - every failure is recorded, never replayed
        if row["execution"] == "PASS":
            row["verification"] = "FAIL"
        else:
            row["execution"] = "FAIL"
        row["reason"] = f"{type(error).__name__}: {error}"
        row["uncertain"] = bool(row.get("uncertain") or getattr(error, "uncertain", False))
        last = (row.get("commands") or [{}])[-1].get("phase", "")
        pending = (row.get("pending") or {}).get("phase", "")
        if last.endswith("_commit") or pending.endswith("_commit"):
            row["commit_failed"] = True
    finally:
        row["wall_ns_ineligible"] = time.monotonic_ns() - started
        campaign.persist()
        driver.cleanup(release_stores=spec.get("release_stores", True))
    return row


def run_step(driver, step, workspaces, machine):
    op = step["op"]
    timeout = step.get("timeout_s")
    if op == "fork":
        driver.fork(step["project"], step["name"], step.get("from", "main"), step.get("commit"))
    elif op == "sandbox":
        driver.sandbox_create(step["project"], step["sandbox"], step.get("machine", machine), timeout)
    elif op == "mount":
        workspaces[step["as"]] = driver.mount(step["sandbox"], step["branch"], step["name"], timeout)
    elif op == "exec":
        driver.exec(workspaces[step["ws"]], step["command"], timeout)
    elif op == "commit":
        driver.commit(workspaces[step["ws"]], timeout, step.get("allow_up_to_date", False), step.get("label"))
    elif op == "unmount":
        driver.unmount(workspaces.pop(step["ws"]), timeout_s=timeout)
    elif op == "close":
        driver.sandbox_close(step["sandbox"], timeout)
    else:
        raise ValueError(f"unknown storage step {op!r}")


def row_summary(row, references=None, ideal_unique=None):
    """``summarize`` from a finished row's probes and histories."""
    probes = row.get("probes", {})
    if "final" not in probes or "floor" not in probes:
        return None
    return summarize(
        list(probes["final"].values()),
        list(probes["floor"].values()),
        row.get("histories", []),
        references,
        ideal_unique,
    )


__all__ = [
    "POLICY", "StorageFailure", "Driver", "load_runner", "docker_volume_for",
    "allocated_argv", "parse_allocated", "parse_status", "pg_lsn_bytes",
    "collect_commits", "commit_record", "total", "summarize", "safe_database_url",
    "run_row", "run_step", "row_summary",
]
