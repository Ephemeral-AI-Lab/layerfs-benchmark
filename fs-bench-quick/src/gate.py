#!/usr/bin/env python3
"""Docker subset regression gate: control vs treatment, paired, one row per command.

layerfs-project#98 (PostgreSQL round 2). A gate compares two sealed product
identities, `a` (control) and `b` (treatment), on the Docker machine only, over
cases C01 C04 C09 C13 C14 C16 C17 C18 and arms SQLite, PostgreSQL over the
published port and PostgreSQL co-located: 8 x 3 x 2 identities x 2 rounds = 96
rows. Every row is an ordinary `run.py prepare` + `run.py run` selection of
the unchanged fs-bench-quick runner, so receipts keep their usual format.

Each identity gets a fresh LayerFS home, a fresh XDG cache (an APFS clone of
its sealed bundle) and therefore a fresh Docker worker per gate; nothing from
an earlier gate is reused except the sealed artifacts. Each identity x round is
its own campaign (own databases). Rows run in this order: per cell, per arm
(campaign matrix order), round 1 `a` then `b`, round 2 `b` then `a`, so every
(cell, arm) pair is measured back to back and order effects alternate.

Commands (from the benchmark repository root), each its own invocation:

    gate.py setup  --gate ID --control DIR --treatment DIR   # homes, workers, databases
    gate.py next   --gate ID      # prepare + run exactly one pending row
    gate.py verdict --gate ID     # markdown summary (paired-delta rule, counts)
    gate.py finish --gate ID      # run.py finish per campaign, stop workers, drop databases

A separately labelled extra gate may declare a subset at setup (`--cells C17
--arms pg-colocated`); it runs the same paired order over that subset only.
A paired attribution gate may also select another suite's runner and the
native machine (`--suite pjdfstest --machine native --tool-root DIR`), and a
Docker worker image (`--worker-image ID`, e.g. the six-suite tool image) used
by both identities; receipts stay under results/pg-r2-gate/<gate>/.

An artifact DIR holds `layerfs`, `layerfs-daemon`, `manifest.json` (with
`source_sha`) and `xdg/layerfs/bundle/...`. `next` marks a row attempted before
it starts and never replays it; a failed or timed-out row stays failed.

Verdict rule (declared before any row): for each cell/arm/phase, paired delta
= treatment - control within a round; FLAG when the median paired delta
exceeds max(15% of the control median, 5 ms) AND both pairs are slower. This is
the #118 material-regression rule with two pairs instead of three and the
owner's 5 ms floor (under 5 ms per call is not a regression) in place of 3 ms.
The A/A reference gate (`gate-ref`, control as both identities) flagged 22 of
147 per-row metrics, so per-row flags are diagnostic; the timing verdict
is the aggregate rule (AGG_RULE) per arm and phase over all cells' pairs, and
counts stay the primary evidence.
"""

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "fs-bench-quick" / "src" / "run.py"
STATE = Path(os.environ.get("PGR2_BENCH_STATE", Path.home() / ".cache/pg-perf-r2/bench"))
RESULTS = ROOT / "fs-bench-quick" / "results" / "pg-r2-gate"
CELLS = ("C01", "C04", "C09", "C13", "C14", "C16", "C17", "C18")
ALL_CELLS = tuple(f"C{i:02d}" for i in range(1, 19))
ARMS = ("sqlite", "postgresql", "pg-colocated")
ARM_SHORT = {"postgresql": "pg", "pg-colocated": "co"}
PHASES = (
    ("create", "sandbox_create"),
    ("mount", "measured_mount"),
    ("exec", "exec"),
    ("commit", "commit"),
    ("commit2", "commit_2"),
    ("unmount", "unmount"),
)
SERVER = "pgr2b-pg"
PORT = 55442
PASSWORD_FILE = STATE / "pg" / "password"
PREPARE_TIMEOUT_S = 45
RUN_TIMEOUT_S = 65
RULE = "FLAG if median(T-C) > max(15% of control median, 5 ms) AND 2/2 pairs slower"
AGG_RULE = (
    "per arm and phase over all cells' pairs: FLAG if median relative delta > 15% AND "
    "median delta > 5 ms AND >= 3/4 of pairs slower (12/16)"
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def gate_dir(gate):
    return STATE / gate


def load(gate):
    return json.loads((gate_dir(gate) / "gate.json").read_text())


def save(gate, value):
    path = gate_dir(gate) / "gate.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, indent=1) + "\n")
    os.replace(tmp, path)


def ledger(gate, event, **fields):
    with (gate_dir(gate) / "ledger.jsonl").open("a") as stream:
        stream.write(json.dumps({"event": event, "at_utc": now(), **fields}) + "\n")


SUITE = "fs-bench-quick"
MACHINE = "docker"


def suite_cells(suite):
    """CASE_IDS of a suite's cases.py (matrix order of its runner)."""
    if suite == "fs-bench-quick":
        return ALL_CELLS
    spec = importlib.util.spec_from_file_location(f"cases_{suite}", ROOT / suite / "src" / "cases.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return tuple(module.CASE_IDS)


def run_path():
    return ROOT / SUITE / "src" / "run.py"


def arm_order(cell, arms=None):
    """The runner's matrix order with `order: alternate` (odd CASE_IDS index reversed)."""
    ordered = ARMS[::-1] if suite_cells(SUITE).index(cell) % 2 else ARMS
    return tuple(a for a in ordered if a in (arms or SELECTED_ARMS))


SELECTED_ARMS = ARMS


def scope(record):
    """Restrict reporting to a gate's declared cells and arms (an extra subset gate)."""
    global CELLS, SELECTED_ARMS, SUITE, MACHINE
    CELLS = tuple(record.get("cells", CELLS))
    SELECTED_ARMS = tuple(record.get("arms", ARMS))
    SUITE = record.get("suite", "fs-bench-quick")
    MACHINE = record.get("machine", "docker")


def plan(cells=CELLS, arms=ARMS):
    rows = []
    for cell in cells:
        for arm in arm_order(cell, arms):
            for rnd, idents in ((1, "ab"), (2, "ba")):
                rows.extend({"cell": cell, "arm": arm, "round": rnd, "ident": i} for i in idents)
    return rows


def database(gate, ident, rnd, cell, arm):
    return f"g_{gate.replace('-', '_')}_{ident}_r{rnd}_{cell.lower()}_{ARM_SHORT[arm]}"


def psql(sql):
    return subprocess.run(
        ["docker", "exec", SERVER, "psql", "-U", "postgres", "-d", "postgres", "-X", "-q",
         "-A", "-t", "-v", "ON_ERROR_STOP=1", "-c", sql],
        capture_output=True, text=True, timeout=60, check=True,
    ).stdout


def artifact(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory / "manifest.json").read_text())
    bundles = list((directory / "xdg/layerfs/bundle").glob("*/linux-*/bundle.json"))
    if len(bundles) != 1:
        raise SystemExit(f"{directory}: expected one sealed Linux bundle, found {len(bundles)}")
    found = {
        "dir": str(directory),
        "source_sha": manifest["source_sha"],
        "cli_sha256": sha(directory / "layerfs"),
        "daemon_sha256": sha(directory / "layerfs-daemon"),
        "linux_bundle_sha256": json.loads(bundles[0].read_text())["hash"],
    }
    for key in ("cli_sha256", "daemon_sha256", "linux_bundle_sha256"):
        if manifest.get(key) != found[key]:
            raise SystemExit(f"{directory}: {key} does not match its manifest (unsealed change)")
    return found


def cli_env(ident_dir):
    return dict(
        os.environ,
        LAYERFS_HOME=str(ident_dir / "home"),
        XDG_CACHE_HOME=str(ident_dir / "xdg"),
        LAYERFS_CONSTRUCTION_WORKERS="1",
    )


def machines_config(args):
    """The environment's machine table: only the gate's machine is ready."""
    machines = {
        "native": {"name": "native", "ready": MACHINE == "native"},
        "docker": {"name": "docker", "ready": MACHINE == "docker"},
        "lima": {"name": "none", "ready": False},
        "apple-container": {"name": "none", "ready": False},
    }
    if args.tool_root:
        machines[MACHINE]["platform"] = "darwin" if MACHINE == "native" else "linux"
        machines[MACHINE]["tool_environment"] = {"BENCH_TOOL_ROOT": args.tool_root}
    return machines


def setup(args):
    gate = args.gate
    root = gate_dir(gate)
    if root.exists():
        raise SystemExit(f"{root} exists; every gate needs fresh homes and workers")
    if any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in gate) or len(gate) > 12:
        raise SystemExit("gate id: up to 12 lowercase letters, digits or hyphens")
    global SUITE, MACHINE
    SUITE, MACHINE = args.suite, args.machine
    idents = {"a": artifact(args.control), "b": artifact(args.treatment)}
    cells = tuple(args.cells.split(",")) if args.cells else CELLS
    arms = tuple(args.arms.split(",")) if args.arms else ARMS
    if not set(cells) <= set(suite_cells(SUITE)) or not set(arms) <= set(ARMS):
        raise SystemExit("unknown --cells or --arms")
    if MACHINE not in ("docker", "native") or (MACHINE == "native" and "pg-colocated" in arms):
        raise SystemExit("--machine is docker or native; the co-located arm exists on Docker only")
    root.mkdir(parents=True, mode=0o700)
    colocated_ip = subprocess.run(
        ["docker", "inspect", SERVER, "--format", "{{.NetworkSettings.Networks.bridge.IPAddress}}"],
        capture_output=True, text=True, timeout=30, check=True,
    ).stdout.strip()
    harness = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain", "--", "fs-bench-quick/src", "shared/src", f"{SUITE}/src"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if dirty:
        raise SystemExit("harness source is dirty; commit it before a gate (pinned identity)")
    record = {
        "gate": gate,
        "created_utc": now(),
        "harness_commit": harness,
        "rule": RULE,
        "cells": cells,
        "arms": arms,
        "suite": SUITE,
        "machine": MACHINE,
        "tool_root": args.tool_root,
        "worker_image": args.worker_image,
        "server": {"container": SERVER, "published": f"127.0.0.1:{PORT}", "colocated": f"{colocated_ip}:5432"},
        "identities": idents,
        "label": args.label or "",
        "plan": plan(cells, arms),
        "cursor": 0,
        "workers": {},
        "databases": [],
    }
    empty = root / "empty"
    empty.mkdir(mode=0o700)
    names = []
    for ident, art in idents.items():
        d = root / ident
        (d / "home").mkdir(parents=True, mode=0o700)
        # A fresh XDG cache per identity per gate; APFS clone of the sealed bundle.
        subprocess.run(["cp", "-cR", str(Path(art["dir"]) / "xdg"), str(d / "xdg")], check=True)
        for rnd in (1, 2):
            dbs = {}
            for cell in cells:
                for arm in [a for a in ("postgresql", "pg-colocated") if a in arms]:
                    name = database(gate, ident, rnd, cell, arm)
                    names.append(name)
                    host = f"127.0.0.1:{PORT}" if arm == "postgresql" else f"{colocated_ip}:5432"
                    key = f"{cell}/{MACHINE}" if arm == "postgresql" else f"{cell}/{MACHINE}/{arm}"
                    dbs[key] = f"postgresql://bench@{host}/{name}?sslmode=disable"
            cli = str(Path(art["dir"]) / "layerfs")
            env = {
                "campaign_id": f"{gate}-{ident}-r{rnd}",
                "source_sha": art["source_sha"],
                "source_reference": f"pg-r2 gate {gate} identity {ident} ({'control' if ident == 'a' else 'treatment'}), sealed artifacts {art['dir']}",
                "harness_commit": harness,
                "cli": cli,
                "home": str(d / "home"),
                "empty_source": str(empty),
                "environment": {"XDG_CACHE_HOME": str(d / "xdg")},
                "artifacts": {k: art[k] for k in ("cli_sha256", "daemon_sha256", "linux_bundle_sha256")} | {"profile": "release"},
                "machines": machines_config(args),
                "order": "alternate",
                "compact_sources": True,
                "postgresql": {
                    "password_env": "BENCH_PG_PASSWORD",
                    "databases": dbs,
                    "colocated_machines": ["docker"],
                    "disposal_resource": f"pgr2b-{gate}-databases",
                    "observer": {
                        "admin_argv": ["docker", "exec", SERVER, "psql", "-U", "postgres", "-d", "postgres",
                                       "-X", "-q", "-A", "-t", "-F", "\u001f", "-v", "ON_ERROR_STOP=1"],
                        "log_argv": ["docker", "logs", "--since", "{since}", SERVER],
                    },
                },
                "resources": [
                    {"id": f"pgr2b-{gate}-databases", "owned": True,
                     "release_argv": [sys.executable, str(Path(__file__).resolve()), "finish", "--gate", gate],
                     "note": "the gate's exact row databases on pgr2b-pg; released by gate.py finish"},
                ] + ([{"id": f"docker-worker-{gate}-{ident}", "owned": True,
                       "release_argv": [cli, "machine", "stop", "docker"],
                       "note": f"worker of {d / 'home'}; stopped by gate.py finish"}] if MACHINE == "docker" else []),
                "shared_infrastructure": True,
                "shared_cleanup_complete": False,
                "prepare_budget_s": 25,
                "performance_budget_s": 15,
                "cleanup_budget_s": 10,
            }
            c = d / f"r{rnd}"
            c.mkdir(mode=0o700)
            (c / "environment.json").write_text(json.dumps(env, indent=2) + "\n")
    record["databases"] = names
    save(gate, record)
    ledger(gate, "declaration", rule=RULE, plan_rows=len(record["plan"]), identities=idents,
           harness_commit=harness, server=record["server"], label=record["label"])
    for name in names:
        psql(f"CREATE DATABASE {name} OWNER bench")
    ledger(gate, "databases_created", names=names)
    for ident in idents:
        d = root / ident
        started = time.monotonic()
        cli = str(Path(idents[ident]["dir"]) / "layerfs")
        if MACHINE == "native":
            # The native machine runs this identity's own macOS daemon (no worker).
            out = subprocess.run([cli, "machine", "update", "native", "--daemon",
                                  str(Path(idents[ident]["dir"]) / "layerfs-daemon")],
                                 env=cli_env(d), capture_output=True, text=True, timeout=110)
        else:
            if args.worker_image:
                image = subprocess.run([cli, "machine", "update", "docker", "--image", args.worker_image],
                                       env=cli_env(d), capture_output=True, text=True, timeout=110)
                if image.returncode != 0:
                    raise SystemExit(f"worker image for {ident} refused: {image.stderr[-500:]}")
            out = subprocess.run([cli, "machine", "start", "docker"],
                                 env=cli_env(d), capture_output=True, text=True, timeout=110)
        layerfs_id = json.loads((d / "home/layerfs.json").read_text()).get("id", "")
        worker = {"exit": out.returncode, "seconds": round(time.monotonic() - started, 1),
                  "stdout": out.stdout[-2000:], "stderr": out.stderr[-2000:],
                  "container": f"lfs-{layerfs_id[:8]}-docker", "volume": f"lfs-{layerfs_id[:8]}-docker-data"}
        record["workers"][ident] = worker
        save(gate, record)
        ledger(gate, "worker_start", ident=ident, **worker)
        print(f"worker {ident}: exit {out.returncode} in {worker['seconds']} s ({worker['container']})")
        if out.returncode != 0:
            raise SystemExit(f"worker {ident} did not start: {out.stderr[-500:]}")
    print(f"gate {gate} ({SUITE} on {MACHINE}): {len(record['plan'])} rows planned, {len(names)} databases, receipts under {RESULTS / gate}")


def receipt_path(gate, row):
    return RESULTS / gate / row["ident"] / f"r{row['round']}" / "rows" / row["cell"] / MACHINE / row["arm"]


def bounded(argv, timeout, env, log):
    try:
        out = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
        code, stdout, stderr = out.returncode, out.stdout, out.stderr
    except subprocess.TimeoutExpired as error:
        code, stdout, stderr = "timeout", error.stdout or "", error.stderr or ""
        stdout = stdout.decode() if isinstance(stdout, bytes) else stdout
        stderr = stderr.decode() if isinstance(stderr, bytes) else stderr
    log.write_text(f"argv: {argv}\nexit: {code}\n--- stdout\n{stdout}\n--- stderr\n{stderr}\n")
    return code


def next_row(args):
    # Rows are strictly serial: a second `next` while one runs is refused.
    with (gate_dir(args.gate) / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("another gate row is running; rows are serial") from None
        return one_row(args)


def one_row(args):
    gate = args.gate
    record = load(gate)
    scope(record)
    index = record["cursor"]
    if index >= len(record["plan"]):
        print("gate complete: every planned row attempted")
        return 0
    row = record["plan"][index]
    # Mark the row attempted before it starts: it is never replayed.
    record["cursor"] = index + 1
    row["attempt_utc"] = now()
    save(gate, record)
    campaign = gate_dir(gate) / row["ident"] / f"r{row['round']}"
    out = receipt_path(gate, row)
    out.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, BENCH_PG_PASSWORD=PASSWORD_FILE.read_text().strip())
    select = ["--environment", str(campaign / "environment.json"), "--cache", str(campaign / "prepared"),
              "--case", row["cell"], "--machine", MACHINE, "--backend", row["arm"]]
    logs = campaign / "logs"
    logs.mkdir(exist_ok=True)
    tag = f"{row['cell']}-{row['arm']}"
    load_before = os.getloadavg()[0]
    started = time.monotonic()
    pe = bounded([sys.executable, str(run_path()), "prepare", *select], PREPARE_TIMEOUT_S, env, logs / f"{tag}.prepare.log")
    re_ = bounded([sys.executable, str(run_path()), "run", *select, "--output", str(out)], RUN_TIMEOUT_S, env,
                  logs / f"{tag}.run.log")
    row.update(prepare_exit=pe, run_exit=re_, load_1m_before=round(load_before, 2),
               wall_s=round(time.monotonic() - started, 1))
    save(gate, record)
    ledger(gate, "row", index=index, **row)
    print(f"[{index + 1}/{len(record['plan'])}] {line(row, out / 'receipt.json')}")
    return 0


def ms(receipt, key):
    value = receipt.get("timings_ns", {}).get(key)
    return None if value is None else value / 1e6


def line(row, path):
    head = f"{row['ident']} r{row['round']} {row['cell']} {row['arm']:12}"
    try:
        r = json.loads(Path(path).read_text())
    except (OSError, ValueError) as error:
        return f"{head} NO RECEIPT ({error}) rc={row.get('prepare_exit')}/{row.get('run_exit')}"
    parts = [f"{name}={ms(r, key):.0f}" for name, key in PHASES if ms(r, key) is not None]
    counts = " ".join(
        f"{p}={v.get('statements', '?')}/{v.get('connections', '?')}"
        for p, v in r.get("pg_phases", {}).items()
        if p in dict((k, n) for n, k in PHASES) and (v.get("statements") or v.get("connections"))
    )
    stored = (r.get("commit") or {}).get("commit", {}).get("new_stored")
    return (f"{head} {r['execution']} clean={r['cleanup']} load={r.get('load_1m', 0):.1f} "
            f"{' '.join(parts)} new_stored={stored} pg[{counts}] rc={row.get('prepare_exit')}/{row.get('run_exit')} "
            f"{r.get('reason', '')[:160]}")


def collect(gate):
    record = load(gate)
    scope(record)
    rows = {}
    for row in record["plan"][: record["cursor"]]:
        path = receipt_path(gate, row) / "receipt.json"
        try:
            rows[(row["cell"], row["arm"], row["ident"], row["round"])] = json.loads(path.read_text())
        except (OSError, ValueError):
            rows[(row["cell"], row["arm"], row["ident"], row["round"])] = None
    return record, rows


def flag(control, treatment, threshold_ms=5.0, share=0.15):
    """Paired-delta rule on lists of per-round values (None = missing pair)."""
    pairs = [(c, t) for c, t in zip(control, treatment) if c is not None and t is not None]
    if len(pairs) < 2:
        return None, f"{len(pairs)}/2", "INCOMPLETE"
    deltas = [t - c for c, t in pairs]
    median_delta = statistics.median(deltas)
    slower = sum(1 for d in deltas if d > 0)
    limit = max(share * statistics.median(c for c, _ in pairs), threshold_ms)
    verdict = "FLAG" if median_delta > limit and slower == len(pairs) else "ok"
    return median_delta, f"{slower}/{len(pairs)}", verdict


def aggregate(pairs, share=0.15, threshold_ms=5.0):
    """All pairs of one arm/phase across cells: (delta ms, relative delta) tuples.

    FLAG when the median relative delta exceeds 15%, the median absolute delta
    exceeds 5 ms and at least three quarters of the pairs are slower (12 of 16
    is a one-sided sign test at about p = 0.04). Declared after the A/A
    reference gate, which showed the per-row 2-pair rule alone false-alarms.
    """
    deltas = [d for d, _ in pairs]
    rel = statistics.median(r for _, r in pairs)
    delta = statistics.median(deltas)
    slower = sum(1 for d in deltas if d > 0)
    hit = rel > share and delta > threshold_ms and 4 * slower >= 3 * len(pairs) and len(pairs) >= 4
    return delta, rel, slower, "FLAG" if hit else "ok"


def counts(receipt, phase):
    if receipt is None:
        return "—"
    value = receipt.get("pg_phases", {}).get(phase)
    if not value or value.get("statements_status") != "OBSERVED":
        return "n/a"
    return f"{value.get('statements', '?')}/{value.get('connections', '?')}"


def fmt(value):
    return "—" if value is None else f"{value:.0f}"


def row_value(r, key):
    if r is None or r.get("execution") != "PASS":
        return None
    if key is None:
        return (r.get("performance_invocation_elapsed_ns", 0) - r.get("control_overhead_ns", 0)) / 1e6
    return ms(r, key)


def flagged(rows):
    """The (cell, arm, phase) metrics the per-row 2-pair rule flags."""
    found = set()
    for cell in CELLS:
        for arm in SELECTED_ARMS:
            for name, key in (*PHASES, ("e2e", None)):
                a = [row_value(rows.get((cell, arm, "a", n)), key) for n in (1, 2)]
                b = [row_value(rows.get((cell, arm, "b", n)), key) for n in (1, 2)]
                if flag(a, b)[2] == "FLAG":
                    found.add((cell, arm, name))
    return found


def verdict(args):
    gate = args.gate
    reference = None
    if args.reference:
        ref_record, ref_rows = collect(args.reference)
        scope(ref_record)
        reference = flagged(ref_rows)
    record, rows = collect(gate)
    scope(record)
    lines = [f"# Gate `{gate}` summary", ""]
    ids = record["identities"]
    lines += [
        f"Label: {record.get('label') or '—'}. Harness `{record['harness_commit']}`. Created {record['created_utc']}.",
        "Verdict: counts first. Timing flag: the aggregate rule per arm and phase "
        f"({AGG_RULE}). Per-row rule, diagnostic only: {RULE}. Paired delta = b − a within a round; "
        "timings are diagnostic (INELIGIBLE cache state).",
        "",
        "| identity | role | source | CLI sha256 | daemon sha256 | Linux bundle | worker |",
        "|---|---|---|---|---|---|---|",
    ]
    for ident, art in ids.items():
        lines.append(
            f"| {ident} | {'control' if ident == 'a' else 'treatment'} | `{art['source_sha'][:10]}` | "
            f"`{art['cli_sha256'][:12]}` | `{art['daemon_sha256'][:12]}` | `{art['linux_bundle_sha256'][:12]}` | "
            f"`{record['workers'].get(ident, {}).get('container', '?')}` |"
        )
    attempted = record["cursor"]
    outcome = {}
    loads = []
    for key, r in rows.items():
        state = "NO_RECEIPT" if r is None else r["execution"]
        outcome[state] = outcome.get(state, 0) + 1
        if r is not None and r.get("load_1m") is not None:
            loads.append(r["load_1m"])
    lines += [
        "",
        f"Rows attempted {attempted}/{len(record['plan'])}: "
        + ", ".join(f"{k} {v}" for k, v in sorted(outcome.items()))
        + (f". 1-minute load at row start: min {min(loads):.1f}, median {statistics.median(loads):.1f}, max {max(loads):.1f}." if loads else "."),
        "",
        "## pg_stat_statements per phase (statements/connections), a r1, a r2 → b r1, b r2",
        "",
        "| cell | arm | create | mount | exec | commit | commit 2 | unmount |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for cell in CELLS:
        for arm in [a for a in ("postgresql", "pg-colocated") if a in SELECTED_ARMS]:
            cells = []
            for name, key in PHASES:
                values = [counts(rows.get((cell, arm, i, n)), key) for i in "ab" for n in (1, 2)]
                if key == "commit_2" and cell != "C13":
                    cells.append("")
                elif len(set(values)) == 1:
                    cells.append(values[0])
                else:
                    cells.append(f"{values[0]}, {values[1]} → {values[2]}, {values[3]}")
            lines.append(f"| {cell} | {arm} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## Paired timings: median a → median b ms; median paired delta (pairs slower) verdict",
        "",
        "| cell | arm | create | mount | exec | commit | commit 2 | unmount | end-to-end |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    flags = []
    for cell in CELLS:
        for arm in arm_order(cell):
            cells = []
            for name, key in (*PHASES, ("e2e", None)):
                if key == "commit_2" and cell != "C13":
                    cells.append("")
                    continue
                a = [row_value(rows.get((cell, arm, "a", n)), key) for n in (1, 2)]
                b = [row_value(rows.get((cell, arm, "b", n)), key) for n in (1, 2)]
                delta, slower, verdict_ = flag(a, b)
                med = lambda xs: statistics.median([x for x in xs if x is not None]) if any(x is not None for x in xs) else None
                cells.append(f"{fmt(med(a))} → {fmt(med(b))}; {'' if delta is None else f'{delta:+.0f}'} ({slower}) {verdict_}")
                if verdict_ == "FLAG":
                    cross = ""
                    if reference is not None:
                        also = (cell, arm, name) in reference
                        cross = f"; {'also flagged' if also else 'not flagged'} in {args.reference} (A/A)"
                    flags.append(f"{cell}/{arm}/{name}: a {[fmt(x) for x in a]} b {[fmt(x) for x in b]} median delta {delta:+.0f} ms{cross}")
            lines.append(f"| {cell} | {arm} | " + " | ".join(cells) + " |")
    lines += ["", "## Per-row flags (2-pair rule; diagnostic, high false-alarm rate)", ""]
    lines += [f"- {f}" for f in flags] or ["- none"]
    lines += [
        "",
        "## Aggregate per arm and phase (all cells' pairs)",
        "",
        f"Rule: {AGG_RULE}.",
        "",
        "| arm | phase | pairs | median paired delta ms | median relative delta | pairs slower | verdict |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for arm in SELECTED_ARMS:
        for name, key in PHASES:
            pairs = []
            for cell in CELLS:
                for n in (1, 2):
                    ra, rb = rows.get((cell, arm, "a", n)), rows.get((cell, arm, "b", n))
                    if not ra or not rb or ra.get("execution") != "PASS" or rb.get("execution") != "PASS":
                        continue
                    a, b = ms(ra, key), ms(rb, key)
                    if a is not None and b is not None and a > 0:
                        pairs.append((b - a, (b - a) / a))
            if not pairs:
                continue
            delta, rel, slower, verdict_ = aggregate(pairs)
            lines.append(
                f"| {arm} | {name} | {len(pairs)} | {delta:+.1f} | {100 * rel:+.1f}% | {slower}/{len(pairs)} | {verdict_} |"
            )
    lines += [
        "",
        "## new_stored per Commit (a r1, a r2 → b r1, b r2)",
        "",
        "| cell | arm | commit | commit 2 |",
        "|---|---|---|---|",
    ]
    for cell in CELLS:
        for arm in arm_order(cell):
            out = []
            for key in ("commit", "commit_2"):
                vals = []
                for i in "ab":
                    for n in (1, 2):
                        r = rows.get((cell, arm, i, n))
                        vals.append(str(((r or {}).get(key) or {}).get("commit", {}).get("new_stored", "—")))
                out.append(vals[0] if len(set(vals)) == 1 else f"{vals[0]}, {vals[1]} → {vals[2]}, {vals[3]}")
            lines.append(f"| {cell} | {arm} | {out[0]} | {out[1] if cell == 'C13' else ''} |")
    problems = [
        f"- {k[0]}/{k[1]} {k[2]} r{k[3]}: {'no receipt' if r is None else r['execution'] + ' ' + r.get('reason', '')[:200]}"
        for k, r in rows.items()
        if r is None or r["execution"] != "PASS" or r.get("cleanup") != "COMPLETE"
    ]
    lines += ["", "## Failed, missing or uncleaned rows", ""] + (problems or ["- none"])
    text = "\n".join(lines) + "\n"
    notes = gate_dir(gate) / "interpretation.md"  # hand-written notes survive regeneration
    if notes.exists():
        text += notes.read_text()
    target = gate_dir(gate) / "summary.md"
    target.write_text(text)
    print(text)
    return 0


def finish(args):
    """Release the gate's resources, except those holding uncertain custody.

    A row whose cleanup is not COMPLETE keeps its database and its identity's
    worker (which runs its Sandbox) for inspection; nothing is force-closed.
    """
    gate = args.gate
    record = load(gate)
    scope(record)
    if record.get("finished"):
        print("gate already finished; no release is replayed")
        return 0
    record["finished"] = now()
    save(gate, record)
    env = dict(os.environ, BENCH_PG_PASSWORD=PASSWORD_FILE.read_text().strip())
    results, kept_db, kept_ident = {}, set(), set()
    for ident, art in record["identities"].items():
        for rnd in (1, 2):
            campaign = gate_dir(gate) / ident / f"r{rnd}"
            if not (campaign / "prepared").exists():
                results[f"{ident}-r{rnd}"] = "no campaign state"
                continue
            out = subprocess.run(
                [sys.executable, str(run_path()), "finish", "--environment", str(campaign / "environment.json"),
                 "--cache", str(campaign / "prepared")],
                env=env, capture_output=True, text=True, timeout=100, cwd=ROOT,
            )
            results[f"{ident}-r{rnd}"] = out.stdout.strip()[-400:]
            state = json.loads((campaign / "prepared" / "campaign.json").read_text())
            for row in state["rows"].values():
                if row.get("cleanup") != "COMPLETE":
                    kept_ident.add(ident)
                    if row["backend"] != "sqlite":
                        kept_db.add(database(gate, ident, rnd, row["cell"], row["backend"]))
        if ident in kept_ident:
            results[f"worker-{ident}"] = {"exit": None, "retained": "uncertain row custody; inspect first"}
            continue
        if MACHINE != "docker":
            results[f"worker-{ident}"] = {"exit": 0, "note": "native: no worker"}
            continue
        stop = subprocess.run([str(Path(art["dir"]) / "layerfs"), "machine", "stop", "docker"],
                              env=cli_env(gate_dir(gate) / ident), capture_output=True, text=True, timeout=100)
        results[f"worker-{ident}"] = {"exit": stop.returncode, "stderr": stop.stderr[-500:]}
    failed = [k for k, v in results.items() if k.startswith("worker") and v["exit"] not in (0, None)]
    dropped = []
    if not failed:
        for name in record["databases"]:
            if name in kept_db:
                continue
            psql(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")
            dropped.append(name)
    results["databases_dropped"] = len(dropped)
    results["databases_retained"] = sorted(kept_db)
    record["finish_results"] = results
    save(gate, record)
    ledger(gate, "finish", **results)
    print(json.dumps(results, indent=1))
    return 0 if not (failed or kept_ident) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("setup", "next", "verdict", "finish"))
    parser.add_argument("--gate", required=True)
    parser.add_argument("--control")
    parser.add_argument("--treatment")
    parser.add_argument("--label")
    parser.add_argument("--cells", help="setup: a declared subset of cells, e.g. C17 (extra gate)")
    parser.add_argument("--arms", help="setup: a declared subset of arms, e.g. pg-colocated")
    parser.add_argument("--suite", default="fs-bench-quick", help="setup: the suite whose runner and cases run")
    parser.add_argument("--machine", default="docker", choices=("docker", "native"), help="setup: the machine")
    parser.add_argument("--tool-root", help="setup: BENCH_TOOL_ROOT for a tool suite on this machine")
    parser.add_argument("--worker-image", help="setup: Docker worker/Sandbox image for both identities")
    parser.add_argument("--reference", help="verdict: an A/A gate whose per-row flags are cross-checked")
    args = parser.parse_args(argv)
    if args.action == "setup":
        if not args.control or not args.treatment:
            parser.error("setup needs --control and --treatment")
        return setup(args)
    return {"next": next_row, "verdict": verdict, "finish": finish}[args.action](args)


if __name__ == "__main__":
    sys.exit(main() or 0)
