"""fs-storage-quick row lifecycle, late probe, deferred release and attribution.

Every LayerFS operation is a ``storage.Driver`` call: one bounded
``runner.Campaign.call`` with its intent in the ledger first, never retried.
A row is one fresh Store: create/connect, the empty-project floor (+ push for
SQLite), optional base Inits (each probed), forks, the case's Execs and
Commits, final-state verification of every Branch head (a fresh mount in the
same Sandbox after the work's unmount, one manifest Exec, unmount; as
fs-storage-history does), Sandbox close, a quiesced ``final`` probe, the
paged ``commit list``, then release. Verification therefore precedes the final
probe, identically for the baseline and every candidate. With ``defer_release`` the Store stays registered after
the row (``cleanup: DEFERRED``) so ``late_probe`` can measure it again after
the SQLite worker's idle close / PostgreSQL autovacuum, and is released there.
"""

import subprocess
import time
from pathlib import Path

import storage

DEFERRED = "DEFERRED"


def verify_step(driver, step):
    """Fresh mount of a committed head, one manifest Exec, unmount.

    A mismatch is recorded (``verification_failures``), not raised, so the
    row still reaches its quiesced final probe; a CLI failure raises.
    """
    row = driver.row
    if row.get("verification") in (None, "NOT_RUN"):
        row["verification"] = "ATTEMPTED"
    ws = driver.mount(step["sandbox"], step["branch"], step["name"])
    result = driver.exec(ws, step["command"], step.get("timeout_s", storage.MAX_COMMAND_S),
                         phase="verify", label=f"verify/{step['project']}@{step['branch']}")
    record = {"project": step["project"], "branch": step["branch"],
              "stdout": (result.get("stdout") or "")[-2000:], "verdict": "PASS"}
    try:
        step["check"](result)
    except ValueError as error:
        record["verdict"] = "FAIL"
        record["reason"] = str(error)[:2000]
        row.setdefault("verification_failures", []).append(f"{step['project']}@{step['branch']}")
    row.setdefault("verify_results", []).append(record)
    driver.unmount(ws)


def run_step(driver, step, workspaces, machine):
    if step["op"] == "verify":
        if step.get("enabled", True):
            verify_step(driver, step)
        return
    if step["op"] == "exec" and step.get("check"):
        result = driver.exec(workspaces[step["ws"]], step["command"], step.get("timeout_s"),
                             label=step.get("label"))
        step["check"](result)
        return
    storage.run_step(driver, step, workspaces, machine)


def collect(driver, project, branch):
    """``Driver.commits`` that also keeps the head Commit's ``root`` object id."""
    head = {}

    def page(argv):
        value = driver.call("commit_list", argv)
        items = value.get("items") or []
        if items and "root" not in head:
            head.update(root=items[0].get("root"), id=items[0].get("id"))
        return value

    history = storage.collect_commits(page, project, branch)
    history["head_root"] = head.get("root")
    driver.row.setdefault("histories", []).append(history)
    driver.campaign.persist()
    return history


def root_check(row, item):
    """A head verified by identity: same root object id as a content-verified head.

    Object ids are BLAKE3 content addresses, so an equal root is the same tree.
    The reference head must itself have passed its manifest check.
    """
    roots = {(h["project"], h["branch"]): h.get("head_root") for h in row.get("histories", [])}
    mine = roots.get((item["project"], item["branch"]))
    reference = roots.get((item["project"], item["reference"]))
    verified = any(r["project"] == item["project"] and r["branch"] == item["reference"] and r["verdict"] == "PASS"
                   for r in row.get("verify_results", []))
    record = {"project": item["project"], "branch": item["branch"], "method": f"root == {item['reference']} root",
              "root": mine, "reference_root": reference, "verdict": "PASS"}
    if not (mine and mine == reference and verified):
        record["verdict"] = "FAIL"
        row.setdefault("verification_failures", []).append(f"{item['project']}@{item['branch']}")
    row.setdefault("verify_results", []).append(record)


def run_row(campaign, row, spec, verify=True):
    """Run one quick row from ``cases.spec``; never raises for a workload failure."""
    driver = storage.Driver(campaign, row, spec.get("timeout_s", storage.DEFAULT_COMMAND_S))
    started = time.monotonic_ns()
    row["started_unix_ns"] = time.time_ns()
    row["execution"] = "ATTEMPTED"
    row["allocated"] = spec.get("allocated")
    campaign.persist()
    machine = spec["machine"]
    allocated = spec.get("allocated")
    store = spec["store"]
    name = store["name"]
    try:
        if store["backend"] == "sqlite":
            driver.store_create(name)
        else:
            driver.store_connect(name, store["url"], spec["password_env"])
        driver.project_init(spec["floor_project"]["project"], spec["floor_project"]["source"])
        if store["backend"] == "sqlite" and machine != "native":
            driver.store_push(name, machine, timeout_s=storage.MAX_COMMAND_S)
        driver.probe(name, "floor", allocated)
        for init in spec.get("inits", []):
            driver.project_init(init["project"], init["source"], timeout_s=storage.MAX_COMMAND_S)
            driver.probe(name, init["label"], allocated)
        for branch in spec.get("branches", []):
            driver.fork(branch["project"], branch["name"], branch.get("from", "main"))
        workspaces = {}
        for step in spec["steps"]:
            if step["op"] == "verify" and not verify:
                continue
            run_step(driver, step, workspaces, machine)
        driver.quiesced()
        driver.probe(name, "final", allocated)
        for item in spec.get("collect", []):
            collect(driver, item["project"], item["branch"])
        if verify:
            for item in spec.get("root_checks", []):
                root_check(row, item)
        row["execution"] = "PASS"
        if not verify:
            row["verification"] = "SKIPPED"
        elif row.get("verification_failures"):
            row["verification"] = "FAIL"
            row["reason"] = "final-state verification failed: " + ", ".join(row["verification_failures"])
        elif row.get("verify_results"):
            row["verification"] = "PASS"
            row["correctness"] = "VERIFIED"
    except Exception as error:  # noqa: BLE001 - every failure is recorded, never replayed
        row["execution"] = "FAIL"
        if row.get("verification") == "ATTEMPTED":
            row["verification"] = "FAIL"
        row["reason"] = f"{type(error).__name__}: {error}"
        row["uncertain"] = bool(row.get("uncertain") or getattr(error, "uncertain", False))
        last = (row.get("commands") or [{}])[-1].get("phase", "")
        pending = (row.get("pending") or {}).get("phase", "")
        if last.endswith("_commit") or pending.endswith("_commit"):
            row["commit_failed"] = True
    finally:
        row["wall_ns_ineligible"] = time.monotonic_ns() - started
        campaign.persist()
        defer = bool(spec.get("defer_release"))
        driver.cleanup(release_stores=not defer)
        if defer and row.get("cleanup") == "COMPLETE" and driver.live("stores"):
            row["cleanup"] = DEFERRED
            row["release"] = "DEFERRED_FOR_LATE_PROBE"
        row["finished_unix_ns"] = time.time_ns()
        campaign.persist()
    return row


def deferred_rows(campaign):
    return [row for row in campaign.state["rows"].values() if row.get("cleanup") == DEFERRED]


def release(campaign, row):
    """Release a deferred row's live Stores (one attempt each)."""
    driver = storage.Driver(campaign, row)
    try:
        for store in driver.live("stores"):
            driver.store_release(store)
        row["cleanup"] = "COMPLETE"
        row["release"] = "RELEASED_AFTER_DEFERRAL"
        if any(i.get("backend") == "postgresql" for i in row["owned"]["stores"].values()):
            row["postgresql_data"] = "RETAINED_UNTIL_INFRASTRUCTURE_FINISH"
    except Exception as error:  # noqa: BLE001 - record, never replay
        row["cleanup"] = "INCOMPLETE" if getattr(error, "uncertain", False) else "FAIL"
        row["cleanup_reason"] = str(error)
    campaign.persist()
    return row["cleanup"]


def late_probe(campaign, wait_s, attribution_dir=None, keep=False, sleep=time.sleep):
    """One wait, then re-probe every deferred row's Stores as ``late``; release.

    The wait ends ``wait_s`` after the last row finished (rows that finished
    earlier have waited longer; each row records its own idle time). With
    ``attribution_dir`` the DIAGNOSTIC per-table attribution runs before the
    release (see ``attribution``).
    """
    rows = deferred_rows(campaign)
    if not rows:
        return []
    last = max(row.get("finished_unix_ns") or 0 for row in rows)
    remaining = last / 1e9 + wait_s - time.time()
    campaign.state["late_probe"] = {"wait_s": wait_s, "slept_s": max(0.0, round(remaining, 3)),
                                    "rows": [row["id"] for row in rows]}
    campaign.persist()
    if remaining > 0:
        sleep(remaining)
    out = []
    for row in rows:
        driver = storage.Driver(campaign, row)
        record = {"probed_unix_ns": time.time_ns()}
        record["idle_s"] = round((record["probed_unix_ns"] - (row.get("finished_unix_ns") or 0)) / 1e9, 1)
        try:
            for store in driver.live("stores"):
                driver.probe(store, "late", row.get("allocated"))
            record["status"] = "MEASURED"
        except Exception as error:  # noqa: BLE001 - recorded; the row's own result stands
            record["status"] = "FAIL"
            record["reason"] = f"{type(error).__name__}: {error}"
        row["late_probe"] = record
        campaign.persist()
        if attribution_dir is not None and record["status"] == "MEASURED":
            import attribution

            row["attribution"] = attribution.collect(campaign, row, Path(attribution_dir))
            campaign.persist()
        if not keep and not row.get("pending") and not row.get("uncertain"):
            release(campaign, row)
        out.append(row)
    return out


def docker_free_bytes(image):
    """Free bytes on the Docker guest's root filesystem (read-only probe), or None."""
    try:
        got = subprocess.run(["docker", "run", "--rm", "--network", "none", "--pull", "never",
                              "--entrypoint", "df", image, "-B1", "--output=avail", "/"],
                             capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = got.stdout.split()
    return int(lines[-1]) if got.returncode == 0 and lines and lines[-1].isdigit() else None
