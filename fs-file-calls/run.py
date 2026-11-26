#!/usr/bin/env python3
"""fs-file-calls benchmark suite (Ephemeral-AI-Lab/layerfs-project#157).

Measures the 14 mountless LayerFS 2.0 `file.*` calls plus `commit.diff` across:
  - CLI (fresh process per call) vs persistent `@layerfs/node` SDK client
  - Native SQLite (ext4) vs Native PostgreSQL (with `pg_stat_statements`)
  - Trees F100 / F1k / F10k / F100k (`--trees`), file sizes 0B..16MiB (+ optional
    big write payload), history depths H1 / H<d> (`--h-depths`)
  - Concurrency: 1 / 4 / 8 parallel readers & writers (separate + same branch)
  - Independent proof: every read result is checked against the fixture manifest
    (`proof.manifest`); the manifest hash is re-checked after the write rows.

Every case is one row. A refused call becomes a REFUSED row carrying the
refusal code; a call over the 120 s cap becomes a FAIL row; the run continues.
Cold-cache rows are registered and gated by `shared/src/measure.py:assess_cache`
(INELIGIBLE); no row is ever labelled cold. All timings are warm/diagnostic.
Unavailable routes (docker/lima/apple-container) stay registered as NOT_RUN.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import itertools
import json
import math
import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared" / "src"))
from measure import assess_cache  # noqa: E402  (shared/src/measure.py:181)


CALL_INVENTORY = [
    "file.read", "file.stat", "file.list", "file.glob", "file.grep",
    "file.blame", "file.history", "commit.diff", "file.write", "file.edit",
    "file.apply", "file.cp", "file.mv", "file.rm", "file.mkdir",
]

CAP_S = 120
MIN_FREE_GB = 25
TREE_SIZES = {"F100": 100, "F1k": 1000, "F10k": 10000, "F100k": 100000}
BIG_TREES = ("F10k", "F100k")
SIZE_SPECS = {"0b": 0, "1k": 1024, "64k": 64 * 1024, "1m": 1024 * 1024, "16m": 16 * 1024 * 1024}
LINE64 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!\n"  # 64 B
LINES_PER_MIB = 16384
SAMPLE_PATH = "/d0/s0/g0/f_000000.txt"
RARE, COMMON = "RARE_NEEDLE_9917", "COMMON_TOKEN"

TRACE_SRC = (
    "control/crates/layerfs-home/src/trace.rs:24-37 (steps are written only when LAYERFS_TRACE and "
    "LAYERFS_TRACE_STEP are both set; the native route writes `step: dispatch` events only, observed in T1)"
)
LIMIT_SOURCES = {
    "file.write content": [
        "core/crates/layerfs-storage/src/store/policy.rs:57 (TRANSACTION_CANONICAL_BYTES_LIMIT 4 MiB-1, metadata bytes of one transaction)",
        "core/crates/layerfs-storage/src/store/policy.rs:60 (PUBLICATION_BYTES_MAX 16 MiB-1, one publication batch; larger content is published in several batches)",
        "no explicit file-content size limit found in the call path; the ladder records what the product did",
    ],
    "file.apply": [
        "core/crates/layerfs-storage/src/store/policy.rs:55 (TRANSACTION_ROW_LIMIT = 8,191 rows)",
        "engine/crates/layerfs-persistence/src/history/fused.rs:106 (past it the Commit leaves the fused path: Fused::Overflow, not a refusal)",
    ],
    "commit.diff": [
        "engine/crates/layerfs-store-service/src/history/listing.rs:29,44-45 (MAX_LIMIT 1,000; `limit` outside 1..1000 is InvalidInput)",
        "engine/crates/layerfs-store-service/src/history/lookup.rs:57,229 (where a diff would answer Capacity)",
    ],
    "file.read": [
        "control/crates/layerfs-store/src/calls/file/read.rs:16,66-70 (MAX_LINES 2,000; `limit` outside 1..2000 is InvalidInput)",
        "engine/crates/layerfs-store-service/src/read/window.rs:11-12 (BYTES 48 KiB, LINES 2,000)",
        "engine/crates/layerfs-store-service/src/read/read_reply.rs:16,35 (a reply past the 48 KiB window is cut: next_line / line_truncated)",
    ],
}


# ---------------------------------------------------------------- hashing / stats

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fixture_manifest(root: Path) -> tuple[str, dict[str, tuple[int, str]]]:
    """sha256 over sorted `path \\0 size \\0 content-sha256` lines, plus the entries."""
    entries: dict[str, tuple[int, str]] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            entries["/" + p.relative_to(root).as_posix()] = (p.stat().st_size, sha256_file(p))
    h = hashlib.sha256()
    for rel in sorted(entries):
        size, digest = entries[rel]
        h.update(f"{rel}\0{size}\0{digest}\n".encode("utf-8"))
    return h.hexdigest(), entries


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] + (s[c] - s[f]) * (k - f)


def summarize_ms(samples_ms: list[float]) -> dict:
    total_s = sum(samples_ms) / 1000.0
    return {
        "n": len(samples_ms),
        "p50_ms": round(pct(samples_ms, 50), 3),
        "p95_ms": round(pct(samples_ms, 95), 3),
        "max_ms": round(max(samples_ms) if samples_ms else 0.0, 3),
        "calls_per_s": round(len(samples_ms) / total_s, 2) if total_s > 0 else 0.0,
    }


def free_gb(path: Path) -> float:
    return shutil.disk_usage(path).free / 2**30


# ---------------------------------------------------------------- fixtures

def make_tree(root: Path, count: int) -> None:
    """Create a deterministic tree of `count` files at depth <= 6 (here 4)."""
    root.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        rel = tree_path(i)
        fp = root / rel.lstrip("/")
        fp.parent.mkdir(parents=True, exist_ok=True)
        marker = RARE if i == count // 2 else COMMON
        fp.write_text(f"file={i} marker={marker} pad=0123456789abcdef\n", encoding="utf-8")


def tree_path(i: int) -> str:
    return f"/d{i % 10}/s{(i // 10) % 10}/g{(i // 100) % 10}/f_{i:06d}.txt"


def make_size_files(root: Path) -> None:
    """Create text files of 0 B, 1 KiB, 64 KiB, 1 MiB, 16 MiB."""
    root.mkdir(parents=True, exist_ok=True)
    for tag, nbytes in SIZE_SPECS.items():
        (root / f"sz_{tag}.txt").write_bytes((LINE64 * (nbytes // len(LINE64))).encode("utf-8"))


def register_fixture(root: Path) -> dict:
    digest, entries = fixture_manifest(root)
    return {
        "root": root, "sha": digest, "entries": entries,
        "files": len(entries), "bytes": sum(s for s, _ in entries.values()),
    }


def build_proofs(fx: dict, h_depths: list[int]) -> dict:
    """case name -> (fixture label, description, check(result) -> bool); shared by both front ends."""
    proofs: dict = {}
    sizes_root = fx["sizes"]["root"]
    cache: dict[str, str] = {}

    def text_of(rel: str) -> str:
        if rel not in cache:
            cache[rel] = (sizes_root / rel.lstrip("/")).read_text(encoding="utf-8")
        return cache[rel]

    for tag in ("1k", "64k", "1m", "16m_win2000"):
        rel = "/sz_16m.txt" if tag == "16m_win2000" else f"/sz_{tag}.txt"
        proofs[f"file.read ({tag})"] = (
            "sizes", f"reply text is a prefix of fixture {rel}",
            lambda d, rel=rel: isinstance(d.get("text"), str) and text_of(rel).startswith(d["text"]),
        )
    def tree_proofs(label: str, entries: dict) -> None:  # a function, so each tree binds its own values
        n = len(entries)
        top = {p.split("/")[1] for p in entries}
        rare_rel = tree_path(n // 2)
        proofs[f"file.stat ({label})"] = (
            label, f"size equals manifest size of {SAMPLE_PATH}",
            lambda d: d.get("size") == entries[SAMPLE_PATH][0])
        proofs[f"file.list first-page ({label})"] = (
            label, "items are the manifest's top-level directories, count min(100, entries)",
            lambda d: len(d["items"]) == min(100, len(top)) and all(i["path"].strip("/") in top for i in d["items"]))
        proofs[f"file.glob ({label})"] = (
            label, "items are manifest paths, count min(200, files)",
            lambda d: len(d["items"]) == min(200, n) and all(p in entries for p in d["items"]))
        proofs[f"file.grep rare ({label})"] = (
            label, f"exactly the manifest file {rare_rel} matches",
            lambda d: len(d["items"]) == 1 and d["items"][0]["path"] == rare_rel and RARE in d["items"][0]["text"])
        proofs[f"file.grep frequent ({label})"] = (
            label, "50 manifest paths whose line holds the token (or files-1 if fewer)",
            lambda d: len(d["items"]) == min(50, n - 1)
            and all(i["path"] in entries and COMMON in i["text"] for i in d["items"]))

    for label, f in fx.items():
        if label in TREE_SIZES:
            tree_proofs(label, f["entries"])
    for d_ in h_depths:
        last = "h1-1" if d_ == 1 else f"h-{d_}"
        want = min(100, d_ + 1)
        # a page ends early at its byte budget (listing.rs PAGE_BYTES) with next_cursor, so fewer rows need a cursor
        hist = lambda d, last=last, want=want: (
            d["items"][0]["message"] == last
            and (len(d["items"]) == want or (0 < len(d["items"]) < want and d.get("next_cursor") is not None)))
        desc = f"newest commit `{last}`; {want} commits, or a shorter page that carries next_cursor"
        proofs[f"file.history (H{d_}, head)"] = ("hist", desc, hist)
        proofs[f"file.history (H{d_}, pinned)"] = ("hist", desc, hist)
        proofs[f"file.blame (H{d_}, head)"] = (
            "hist", "ranges cover the 2-line target.txt", lambda d: d["ranges"][-1]["end"] == 2)
        proofs[f"commit.diff (H{d_}, head)"] = (
            "hist", "diff vs main is exactly /target.txt modified",
            lambda d: [(i["path"], i["change"]) for i in d["items"]] == [("/target.txt", "modified")])
    return proofs


# ---------------------------------------------------------------- CLI process layer

class CaseAbort(RuntimeError):
    """A call that did not succeed: becomes one row, never aborts the run."""

    def __init__(self, status: str, code: str | None = None, message: str = "", cap_s: int | None = None):
        super().__init__(f"{status} {code or ''} {message}".strip())
        self.status, self.code, self.message, self.cap_s = status, code, message, cap_s

    def row(self, case: str, kind: str = "read") -> dict:
        r: dict = {"case": case, "kind": kind, "status": self.status, "n": 0}
        if self.code:
            r["code"] = self.code
        if self.cap_s:
            r["cap_s"] = self.cap_s
        if self.message:
            r["message"] = self.message[:300]
        return r


def refusal_code(stderr: str, stdout: str) -> tuple[str, str]:
    for text in (stderr, stdout):
        for line in reversed(text.strip().splitlines()):
            try:
                j = json.loads(line)
            except ValueError:
                continue
            if isinstance(j, dict) and "error" in j:
                return str(j["error"]), str(j.get("message", ""))[:200]
    return "Unknown", (stderr or stdout).strip()[:200]


def timed_process(argv: list[str], env: dict, cap_s: float) -> dict:
    """Run once under a wall cap; wall time, CPU and max RSS from os.wait4 rusage
    (units as shared/src/measure.py:171-177)."""
    out = {"rc": None, "stdout": "", "stderr": "", "ms": None, "cpu_ms": None,
           "max_rss_bytes": None, "timed_out": False, "error": None}
    t0 = time.perf_counter()
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=env, start_new_session=True)
    except OSError as error:
        out["error"] = str(error)
        return out
    bufs: dict[str, bytes] = {}

    def drain(name: str, stream) -> None:
        bufs[name] = stream.read()

    readers = [threading.Thread(target=drain, args=(n, getattr(proc, n)), daemon=True) for n in ("stdout", "stderr")]
    for t in readers:
        t.start()
    fired = threading.Event()

    def expire() -> None:
        fired.set()
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass

    timer = threading.Timer(cap_s, expire)
    timer.start()
    try:
        _pid, status, usage = os.wait4(proc.pid, 0)
    finally:
        timer.cancel()
    out["ms"] = (time.perf_counter() - t0) * 1000.0
    proc.returncode = os.waitstatus_to_exitcode(status)
    for t in readers:
        t.join(timeout=5)
    proc.stdout.close()
    proc.stderr.close()
    out["rc"] = proc.returncode
    out["timed_out"] = fired.is_set() and proc.returncode == -signal.SIGKILL
    out["stdout"] = bufs.get("stdout", b"").decode("utf-8", errors="replace")
    out["stderr"] = bufs.get("stderr", b"").decode("utf-8", errors="replace")
    out["cpu_ms"] = (usage.ru_utime + usage.ru_stime) * 1000.0
    out["max_rss_bytes"] = int(usage.ru_maxrss) * (1 if sys.platform == "darwin" else 1024)
    return out


def read_trace(path: Path, offset: int) -> dict[str, int]:
    """Microseconds per step name from the trace lines appended after `offset`."""
    try:
        with path.open("rb") as f:
            f.seek(offset)
            data = f.read()
    except FileNotFoundError:
        return {}
    steps: dict[str, int] = {}
    for line in data.decode("utf-8", errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("event") == "step" and "step" in ev and "us" in ev:
            steps[ev["step"]] = steps.get(ev["step"], 0) + int(ev["us"])
    return steps


class CliRunner:
    def __init__(self, cli: Path, home: Path, trace_file: Path | None = None):
        self.cli = cli
        self.home = home
        self.trace_file = trace_file
        self.content_dir = home.with_name(home.name + "_content")
        self.content_dir.mkdir(parents=True, exist_ok=True)
        self._seq = itertools.count()
        if trace_file:
            trace_file.unlink(missing_ok=True)

    def env(self) -> dict:
        env = dict(os.environ)
        env["LAYERFS_HOME"] = str(self.home)
        env["LAYERFS_CONSTRUCTION_WORKERS"] = "1"
        env["NO_COLOR"] = "1"
        if self.trace_file:
            env["LAYERFS_TRACE"] = str(self.trace_file)
            env["LAYERFS_TRACE_STEP"] = "1"  # any non-empty value (trace.rs:29)
        return env

    def run_stdin(self, args: list[str], stdin_data: str, timeout: float = CAP_S) -> tuple[int, str, str]:
        """Setup-only call that needs stdin (`--password-stdin`); never a measured row."""
        proc = subprocess.run([str(self.cli), *args], input=stdin_data, capture_output=True, text=True,
                              env=self.env(), timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr

    def raw(self, args: list[str], content: str | None = None, cap_s: float = CAP_S, trace: bool = True) -> dict:
        """One call, never raises. Content goes through `--from <file>` (staged before the clock starts)."""
        argv = [str(self.cli), *args]
        staged = None
        if content is not None:
            staged = self.content_dir / f"c{next(self._seq)}.txt"
            staged.write_text(content, encoding="utf-8")
            argv += ["--from", str(staged)]
        offset = self.trace_file.stat().st_size if (trace and self.trace_file and self.trace_file.exists()) else 0
        res = timed_process(argv, self.env(), cap_s)
        if staged:
            staged.unlink(missing_ok=True)
        res["steps_us"] = read_trace(self.trace_file, offset) if (trace and self.trace_file) else {}
        return res

    def call(self, args: list[str], content: str | None = None, cap_s: float = CAP_S) -> dict:
        r = self.raw(args, content=content, cap_s=cap_s)
        label = " ".join(args[:2])
        if r["timed_out"]:
            raise CaseAbort("FAIL", message=f"{label}: over the {cap_s} s cap; local process killed, remote effect unknown", cap_s=int(cap_s))
        if r["rc"] is None:
            raise CaseAbort("FAIL", message=f"{label}: {r['error']}")
        if r["rc"] < 0:
            raise CaseAbort("FAIL", code=f"signal {-r['rc']}", message=f"{label}: killed by signal")
        if r["rc"] != 0:
            code, msg = refusal_code(r["stderr"], r["stdout"])
            raise CaseAbort("REFUSED", code=code, message=f"{label}: {msg}")
        try:
            r["data"] = json.loads(r["stdout"])
        except ValueError as error:
            raise CaseAbort("FAIL", message=f"{label}: unparsable output: {error}")
        return r

    def ok(self, args: list[str], content: str | None = None) -> tuple[dict, float]:
        r = self.call(args, content=content)
        return r["data"], r["ms"]


def attribution(calls: list[dict]) -> dict:
    per: dict[str, list[float]] = {}
    for c in calls:
        for name, us in c.get("steps_us", {}).items():
            per.setdefault(name, []).append(us / 1000.0)
    p50 = {k: round(pct(v, 50), 3) for k, v in sorted(per.items())}
    return {
        "dispatch_ms_p50": p50.get("dispatch"),
        "steps_p50_ms": p50,
        "unavailable": {s: "UNAVAILABLE on the native route" for s in ("route", "connect", "request") if s not in p50},
        "source": TRACE_SRC,
    }


def summarize_calls(calls: list[dict]) -> dict:
    row = summarize_ms([c["ms"] for c in calls])
    row["cpu_ms_p50"] = round(pct([c["cpu_ms"] for c in calls], 50), 3)
    row["max_rss_bytes"] = max((c["max_rss_bytes"] or 0) for c in calls) if calls else 0
    row["attribution"] = attribution(calls)
    row["dispatch_ms_p50"] = row["attribution"]["dispatch_ms_p50"]
    return row


# ---------------------------------------------------------------- PostgreSQL helpers (code only; untested without a server)

PG_TOP_SQL = (
    "select calls, round(total_exec_time::numeric, 3), rows, "
    "left(regexp_replace(query, '\\s+', ' ', 'g'), 120) from pg_stat_statements "
    "where dbid = (select oid from pg_database where datname = '{db}') "
    "order by total_exec_time desc limit 5"
)
PG_SETTINGS = ("shared_buffers", "synchronous_commit", "shared_preload_libraries", "max_connections",
               "wal_level", "fsync", "full_page_writes", "effective_cache_size")


def psql(url: str, sql: str) -> str:
    return subprocess.run(["psql", url, "-qAt", "-F", "|", "-c", sql], capture_output=True, text=True,
                          timeout=60, check=True).stdout


class PgStat:
    def __init__(self, admin_url: str, db: str):
        self.url, self.db = admin_url, db

    def reset(self) -> None:
        psql(self.url, "select pg_stat_statements_reset()")

    def top(self, n: int) -> list[dict]:
        out = []
        for line in psql(self.url, PG_TOP_SQL.format(db=self.db)).strip().splitlines():
            calls, total, rows, *query = line.split("|")
            out.append({"calls": int(calls), "total_ms_per_case_call": round(float(total) / n, 3),
                        "rows_per_case_call": round(int(rows) / n, 3), "query": "|".join(query)})
        return out


def pg_identity(admin_url: str) -> dict:
    version = psql(admin_url, "show server_version").strip()
    names = ",".join(f"'{s}'" for s in PG_SETTINGS)
    settings = dict(l.split("|", 1) for l in psql(admin_url, f"select name, setting from pg_settings where name in ({names})").strip().splitlines())
    ext = psql(admin_url, "select count(*) from pg_extension where extname = 'pg_stat_statements'").strip() == "1"
    return {"version": version, "settings": settings, "pg_stat_statements": ext,
            "store_connect": {"synchronous_commit": "off"}}


# ---------------------------------------------------------------- Node SDK arm

def run_node_sdk_bench(node_bin: str, node_pkg: Path, home: Path, store: str, cfg: dict, timeout_s: float) -> dict:
    """Run the persistent `@layerfs/node` SDK arm in a single Node process (rows stream out as JSON lines)."""
    script = r"""
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { performance } from "node:perf_hooks";
const cfg = JSON.parse(readFileSync(process.env.BENCH_CFG, "utf8"));
const mod = await import(cfg.node_pkg);
const layerfs = mod.default ?? mod;
const c = layerfs.client({ home: cfg.home });
const CAP_MS = cfg.cap_s * 1000;
class CapError extends Error {}

function stats(ms) {
  const s = [...ms].sort((a, b) => a - b);
  const p = (q) => {
    const k = (s.length - 1) * (q / 100);
    const f = Math.floor(k), u = Math.ceil(k);
    return f === u ? s[k] : s[f] + (s[u] - s[f]) * (k - f);
  };
  const tot = ms.reduce((a, b) => a + b, 0) / 1000;
  return {
    n: ms.length,
    p50_ms: Number(p(50).toFixed(3)),
    p95_ms: Number(p(95).toFixed(3)),
    max_ms: Number((s[s.length - 1] ?? 0).toFixed(3)),
    calls_per_s: tot > 0 ? Number((ms.length / tot).toFixed(2)) : 0,
  };
}

function psql(sql) {
  return execFileSync("psql", [cfg.pg_admin_url, "-qAt", "-F", "|", "-c", sql], { encoding: "utf8", timeout: 60000 });
}
function pgReset() { if (cfg.pg_admin_url) psql("select pg_stat_statements_reset()"); }
function pgTop(n) {
  if (!cfg.pg_admin_url) return undefined;
  return psql(cfg.pg_top_sql).trim().split("\n").filter(Boolean).map((l) => {
    const [calls, total, rows, ...q] = l.split("|");
    return { calls: Number(calls), total_ms_per_case_call: Number((Number(total) / n).toFixed(3)), rows_per_case_call: Number((Number(rows) / n).toFixed(3)), query: q.join("|") };
  });
}

// Times n calls after one declared warm-up call; CPU and memory are process deltas around the timed loop.
async function bench(n, fn) {
  const w0 = performance.now();
  await fn(-1);
  if (performance.now() - w0 > CAP_MS) throw new CapError(`warm-up call over the ${cfg.cap_s} s cap`);
  pgReset();
  const cpu0 = process.cpuUsage(), mem0 = process.memoryUsage();
  const samples = [];
  let last;
  for (let i = 0; i < n; i++) {
    const t0 = performance.now();
    last = await fn(i);
    const dt = performance.now() - t0;
    samples.push(dt);
    if (dt > CAP_MS) throw new CapError(`call ${i} took ${dt.toFixed(0)} ms, over the ${cfg.cap_s} s cap`);
  }
  const cpu = process.cpuUsage(cpu0), mem = process.memoryUsage();
  const r = {
    ...stats(samples),
    cpu_ms_per_call: Number((((cpu.user + cpu.system) / 1000) / Math.max(n, 1)).toFixed(3)),
    rss_delta_bytes: mem.rss - mem0.rss,
    heap_used_delta_bytes: mem.heapUsed - mem0.heapUsed,
    max_rss_kib: process.resourceUsage().maxRSS,
    _sample: last,
  };
  const pg = pgTop(n);
  if (pg) r.pg_statements = pg;
  return r;
}

const out = { proof: {} };
function emit(r) { console.log(JSON.stringify({ row: r })); }
function failure(e) {
  if (e instanceof CapError) return { status: "FAIL", cap_s: cfg.cap_s, message: e.message };
  if (e?.constructor?.name === "LayerFSError") return { status: "REFUSED", code: e.code, message: String(e.message).slice(0, 200) };
  return { status: "FAIL", message: String(e?.message ?? e).slice(0, 200) };
}
async function runCase(name, kind, thunk) {
  try { emit({ case: name, kind, status: "OK", ...(await thunk()) }); }
  catch (e) { emit({ case: name, kind, n: 0, ...failure(e) }); }
}
async function once(fn) {
  const t0 = performance.now();
  const value = await fn();
  const dt = performance.now() - t0;
  if (dt > CAP_MS) throw new CapError(`call took ${dt.toFixed(0)} ms, over the ${cfg.cap_s} s cap`);
  return [dt, value];
}

const S = cfg.store;
const PSZ = `${S}/sizes`, PH = `${S}/hist`;
const line64 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!\n";

// Reads: file.read across sizes & 2000-line window
for (const [tag, opts] of [["1k", {}], ["64k", {}], ["1m", {}], ["16m_win2000", { line: 1, limit: 2000 }]]) {
  const path = tag === "16m_win2000" ? "/sz_16m.txt" : `/sz_${tag}.txt`;
  await runCase(`file.read (${tag})`, "read", () => bench(cfg.n_read, async () => {
    const res = await c.file.read(PSZ, "main", path, opts);
    if (typeof res.text !== "string") throw new Error("bad read");
    return res;
  }));
}

// Reads: stat, list, glob, grep across the trees
for (const label of cfg.trees) {
  const P = `${S}/${label.toLowerCase()}`;
  const nTree = cfg.big_trees.includes(label) ? Math.min(cfg.n_read, 10) : cfg.n_read;
  await runCase(`file.stat (${label})`, "read", () => bench(nTree, () => c.file.stat(P, "main", cfg.sample_path)));
  await runCase(`file.list first-page (${label})`, "read", () => bench(nTree, () => c.file.list(P, "main", "/", { limit: 100 })));
  await runCase(`file.glob (${label})`, "read", () => bench(nTree, () => c.file.glob(P, "main", "**/*.txt", "/", { limit: 200 })));
  await runCase(`file.grep rare (${label})`, "read", () => bench(nTree, () => c.file.grep(P, "main", cfg.rare, "/", { limit: 50 })));
  await runCase(`file.grep frequent (${label})`, "read", () => bench(nTree, () => c.file.grep(P, "main", cfg.common, "/", { limit: 50 })));
}

// History reads: blame, history, commit.diff at each seeded depth; branch h<d> holds d Commits
for (const d of cfg.h_depths) {
  const br = `h${d}`, depth = `H${d}`;
  const nH = d > 1 ? Math.min(cfg.n_read, 10) : cfg.n_read;
  await runCase(`file.blame (${depth}, head)`, "read", () => bench(nH, () => c.file.blame(PH, br, "/target.txt")));
  await runCase(`file.history (${depth}, head)`, "read", () => bench(nH, () => c.file.history(PH, br, "/target.txt", { limit: 100 })));
  await runCase(`file.history (${depth}, pinned)`, "read", async () => {
    const pinned = (await c.branch.get(PH, br)).commit;
    return bench(nH, () => c.file.history(PH, br, "/target.txt", { at: pinned, limit: 100 }));
  });
  await runCase(`commit.diff (${depth}, head)`, "read", () => bench(nH, () => c.commit.diff(PH, br, { from: "main", path: "/target.txt", with: ["patch"] })));
}

// Writes on a branch forked from the seeded one: write, edit, apply (1, 10, 100), mkdir, cp, mv, rm
let forked = true;
try { await c.branch.fork(PSZ, "sdk_writes", "main"); }
catch (e) { forked = false; emit({ case: "branch.fork (sdk_writes)", kind: "setup", n: 0, ...failure(e) }); }
if (forked) {
  const writes = [["0b", ""], ["1k", line64.repeat(16)], ["64k", line64.repeat(1024)], ["1m", line64.repeat(16384)]];
  if (cfg.big_write_mib > 0) writes.push([`${cfg.big_write_mib}m`, line64.repeat(cfg.big_write_mib * 16384)]);
  for (const [tag, body] of writes) {
    const nW = tag === "1m" ? 5 : (tag === `${cfg.big_write_mib}m` ? Math.min(cfg.n_write, 3) : cfg.n_write);
    await runCase(`file.write (${tag})`, "write", async () => {
      const stBefore = (await c.store.get(S, { with: ["stats"], detail: true })).stats;
      const r = await bench(nW, (i) => c.file.write(PSZ, "sdk_writes", `/w_${tag}.txt`, `${body}${i}\n`, { message: `w-${tag}-${i}` }));
      const stAfter = (await c.store.get(S, { with: ["stats"], detail: true })).stats;
      return { ...r, delta_stored_bytes: stAfter.stored_bytes - stBefore.stored_bytes, delta_size_bytes: stAfter.size - stBefore.size };
    });
  }

  let cur = 0;
  await runCase("file.edit (small)", "write", async () => {
    await c.file.write(PSZ, "sdk_writes", "/edit_me.txt", "alpha=0\nbeta=1\n", { message: "seed edit" });
    return bench(cfg.n_write, async () => {
      const next = cur + 1;
      await c.file.edit(PSZ, "sdk_writes", "/edit_me.txt", { old_string: `alpha=${cur}`, new_string: `alpha=${next}`, message: `edit-${next}` });
      cur = next;
    });
  });

  for (const bsz of [1, 10, 100]) {
    await runCase(`file.apply (batch=${bsz})`, "write", async () => {
      await c.file.mkdir(PSZ, "sdk_writes", `/apply_${bsz}`, { message: `mk-apply-${bsz}` });
      return bench(bsz >= 100 ? 5 : cfg.n_write, async (i) => {
        const ops = [];
        for (let j = 0; j < bsz; j++) ops.push({ op: "write", path: `/apply_${bsz}/f_${j}.txt`, content: `v=${i}-${j}\n` });
        await c.file.apply(PSZ, "sdk_writes", ops, { message: `apply-${bsz}-${i}` });
      });
    });
  }

  await runCase("file.mkdir", "write", () => bench(cfg.n_write, (i) => c.file.mkdir(PSZ, "sdk_writes", `/dir_${i}`, { message: `mk-${i}` })));
  await runCase("file.cp (file)", "write", () => bench(cfg.n_write, (i) => c.file.cp(PSZ, "sdk_writes", "/edit_me.txt", `/cp_${i}.txt`, { message: `cp-${i}` })));
  await runCase("file.mv (file)", "write", () => bench(cfg.n_write, (i) => c.file.mv(PSZ, "sdk_writes", `/cp_${i}.txt`, `/mv_${i}.txt`, { message: `mv-${i}` })));
  await runCase("file.rm (file)", "write", () => bench(cfg.n_write, (i) => c.file.rm(PSZ, "sdk_writes", `/mv_${i}.txt`, { message: `rm-${i}` })));

  try {
    const verify = await c.file.read(PSZ, "sdk_writes", "/edit_me.txt");
    out.proof.edit_final_ok = verify.text.includes(`alpha=${cur}`);
  } catch (e) { out.proof.edit_final_ok = false; }
}

// Limits as rows (one probe, one row, with its code when refused)
const single = (dt) => stats([dt]);
let limitsBranch = true;
try { await c.branch.fork(PSZ, "sdk_limits", "main"); }
catch (e) { limitsBranch = false; emit({ case: "branch.fork (sdk_limits)", kind: "setup", n: 0, ...failure(e) }); }
if (limitsBranch) {
  for (const mib of cfg.write_ladder_mib) {
    await runCase(`limit: file.write content ${mib} MiB`, "limit", async () => {
      const body = line64.repeat(mib * 16384) + "\n";
      const [dt] = await once(() => c.file.write(PSZ, "sdk_limits", `/lim_${mib}m.txt`, body, { message: `lim-${mib}` }));
      return { ...single(dt), limit: { content_bytes: Buffer.byteLength(body) } };
    });
  }
  let lastApply = null;
  for (const rows of cfg.apply_rows) {
    await runCase(`limit: file.apply ${rows} rows`, "limit", async () => {
      const br = `sdk_apply_${rows}`;
      await c.branch.fork(PSZ, br, "main");
      const ops = [];
      for (let j = 0; j < rows; j++) ops.push({ op: "write", path: `/f${String(j).padStart(5, "0")}.txt`, content: `v=${j}\n` });
      const [dt] = await once(() => c.file.apply(PSZ, br, ops, { message: `apply-${rows}` }));
      lastApply = { br, rows };
      return { ...single(dt), limit: { rows } };
    });
  }
  for (const limit of [1000, 1001]) {
    await runCase(`limit: commit.diff page limit ${limit}`, "limit", async () => {
      if (!lastApply) throw new Error("no apply branch to diff (every apply probe failed)");
      const [dt, res] = await once(() => c.commit.diff(PSZ, lastApply.br, { from: "main", with: ["patch"], limit }));
      return { ...single(dt), limit: { changed_paths: lastApply.rows, page_limit: limit, items: res.items.length, has_next: res.next_cursor != null } };
    });
  }
}
for (const limit of [2000, 2001]) {
  await runCase(`limit: file.read window ${limit} lines`, "limit", async () => {
    const [dt, res] = await once(() => c.file.read(PSZ, "main", "/sz_16m.txt", { line: 1, limit }));
    return { ...single(dt), limit: { lines_asked: limit, reply_bytes: Buffer.byteLength(JSON.stringify(res)), text_bytes: Buffer.byteLength(res.text), has_next_line: res.next_line != null } };
  });
}

layerfs.close();
console.log(JSON.stringify(out));
"""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump({**cfg, "node_pkg": str(node_pkg), "home": str(home), "store": store}, tf)
        cfg_path = tf.name
    rows: list[dict] = []
    proof: dict = {}
    note = None
    try:
        env = dict(os.environ)
        env["BENCH_CFG"] = cfg_path
        env["LAYERFS_HOME"] = str(home)
        try:
            proc = subprocess.run([node_bin, "--input-type=module", "-e", script], capture_output=True, text=True,
                                  env=env, timeout=timeout_s)
            stdout, stderr, rc = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as error:
            raw = error.stdout or ""
            stdout = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            stderr, rc = "", None
            note = {"status": "FAIL", "cap_s": int(timeout_s), "message": f"Node arm over its {int(timeout_s)} s process cap; remaining cases not run"}
        for line in stdout.splitlines():
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if "row" in obj:
                rows.append(obj["row"])
            elif "proof" in obj:
                proof = obj["proof"]
        if rc not in (0, None):
            note = {"status": "FAIL", "message": f"Node arm exited rc={rc}: {stderr.strip()[-300:]}"}
    finally:
        Path(cfg_path).unlink(missing_ok=True)
    if note:
        rows.append({"case": "node arm (remaining cases)", "kind": "setup", "n": 0, **note})
    return {"rows": rows, "proof": proof}


# ---------------------------------------------------------------- CLI arm

def guarded(rows: list[dict], case: str, kind: str, thunk) -> None:
    """Append the row `thunk` builds, or the row of the CaseAbort it raises."""
    try:
        rows.append({"case": case, "kind": kind, "status": "OK", **thunk()})
    except CaseAbort as abort:
        rows.append(abort.row(case, kind))


def run_cli_bench(cli: CliRunner, store: str, ctx, seed: dict, pg: PgStat | None) -> dict:
    """Run the CLI (fresh process per call) arm on an already-seeded home/store."""
    S, n_read, n_write = store, ctx.args.n_read, ctx.args.n_write
    PSZ, PH = f"{S}/sizes", f"{S}/hist"
    rows: list[dict] = list(seed["rows"])

    def bench_cli(name: str, n: int, fn) -> None:
        def thunk() -> dict:
            fn(-1)  # declared warm preconditioning
            if pg:
                pg.reset()
            calls, ok_n = [], 0
            proof = ctx.proofs.get(name)
            for i in range(n):
                c = fn(i)
                calls.append(c)
                ok_n += bool(proof and proof[2](c["data"]))
            row = summarize_calls(calls)
            if proof:
                row["proof"] = {"manifest": {
                    "fixture": proof[0], "manifest_sha256": ctx.fx[proof[0]]["sha"],
                    "check": proof[1], "checked": n, "matched": ok_n, "match": ok_n == n}}
            if pg:
                row["pg_statements"] = pg.top(max(n, 1))
            return row
        guarded(rows, name, "read" if name in ctx.proofs else "write", thunk)

    for tag, extra in [("1k", []), ("64k", []), ("1m", []), ("16m_win2000", ["--line", "1", "--limit", "2000"])]:
        path = "/sz_16m.txt" if tag == "16m_win2000" else f"/sz_{tag}.txt"
        bench_cli(f"file.read ({tag})", n_read, lambda _i, p=path, ex=extra: cli.call(["file", "read", PSZ, "main", p, *ex]))

    for label in seed["trees"]:
        P = f"{S}/{label.lower()}"
        nt = min(n_read, 5) if label in BIG_TREES else n_read
        bench_cli(f"file.stat ({label})", nt, lambda _i, p=P: cli.call(["file", "stat", p, "main", SAMPLE_PATH]))
        bench_cli(f"file.list first-page ({label})", nt, lambda _i, p=P: cli.call(["file", "list", p, "main", "/", "--limit", "100"]))
        bench_cli(f"file.glob ({label})", nt, lambda _i, p=P: cli.call(["file", "glob", p, "main", "**/*.txt", "/", "--limit", "200"]))
        bench_cli(f"file.grep rare ({label})", nt, lambda _i, p=P: cli.call(["file", "grep", p, "main", RARE, "/", "--limit", "50"]))
        bench_cli(f"file.grep frequent ({label})", nt, lambda _i, p=P: cli.call(["file", "grep", p, "main", COMMON, "/", "--limit", "50"]))

    for d in seed["h_depths"]:
        br, depth = f"h{d}", f"H{d}"
        nh = min(n_read, 5) if d > 1 else n_read
        bench_cli(f"file.blame ({depth}, head)", nh, lambda _i, b=br: cli.call(["file", "blame", PH, b, "/target.txt"]))
        bench_cli(f"file.history ({depth}, head)", nh, lambda _i, b=br: cli.call(["file", "history", PH, b, "/target.txt", "--limit", "100"]))
        try:
            pinned = cli.ok(["branch", "get", PH, br])[0]["commit"]
            bench_cli(f"file.history ({depth}, pinned)", nh, lambda _i, b=br, at=pinned: cli.call(["file", "history", PH, b, "/target.txt", "--at", at, "--limit", "100"]))
        except CaseAbort as abort:
            rows.append(abort.row(f"file.history ({depth}, pinned)"))
        bench_cli(f"commit.diff ({depth}, head)", nh, lambda _i, b=br: cli.call(["commit", "diff", PH, b, "--from", "main", "--path", "/target.txt", "--with", "patch"]))

    # Writing rows run on a branch forked from the seeded one, never on the read fixtures.
    try:
        cli.ok(["branch", "fork", PSZ, "cli_writes", "main"])
        writes_ready = True
    except CaseAbort as abort:
        rows.append({**abort.row("branch.fork (cli_writes)"), "kind": "setup"})
        writes_ready = False
    if writes_ready:
        writes = [("0b", ""), ("1k", LINE64 * 16), ("64k", LINE64 * 1024), ("1m", LINE64 * LINES_PER_MIB)]
        if ctx.args.big_write_mib > 0:
            if ctx.guard(ctx.args.big_write_mib * 4):
                writes.append((f"{ctx.args.big_write_mib}m", LINE64 * (ctx.args.big_write_mib * LINES_PER_MIB)))
            else:
                rows.append(ctx.guard_row(f"file.write ({ctx.args.big_write_mib}m)"))
        for tag, body in writes:
            nw = 3 if tag == "1m" else (min(n_write, 3) if tag not in ("0b", "1k", "64k") else n_write)

            def write_thunk(tag=tag, body=body, nw=nw) -> dict:
                st_before = cli.ok(["store", "get", S, "--with", "stats", "--detail"])[0]["stats"]
                cli.ok(["file", "write", PSZ, "cli_writes", f"/cw_{tag}.txt", "-m", "pre"], content=f"{body}pre\n")
                calls = [cli.call(["file", "write", PSZ, "cli_writes", f"/cw_{tag}.txt", "-m", f"cw-{tag}-{i}"], content=f"{body}{i}\n") for i in range(nw)]
                st_after = cli.ok(["store", "get", S, "--with", "stats", "--detail"])[0]["stats"]
                return {**summarize_calls(calls),
                        "delta_stored_bytes": st_after["stored_bytes"] - st_before["stored_bytes"],
                        "delta_size_bytes": st_after["size"] - st_before["size"]}
            guarded(rows, f"file.write ({tag})", "write", write_thunk)

        cur = [0]

        def do_edit(_i):
            nxt = cur[0] + 1
            res = cli.call(["file", "edit", PSZ, "cli_writes", "/cedit.txt", "--old-string", f"alpha={cur[0]}", "--new-string", f"alpha={nxt}", "-m", f"e-{nxt}"])
            cur[0] = nxt
            return res

        def edit_thunk() -> dict:
            cli.ok(["file", "write", PSZ, "cli_writes", "/cedit.txt", "-m", "seed"], content="alpha=0\nbeta=1\n")
            calls = [do_edit(i) for i in range(n_write)]
            return summarize_calls(calls)
        guarded(rows, "file.edit (small)", "write", edit_thunk)

        for name, mk in [
            ("file.mkdir", lambda i: ["file", "mkdir", PSZ, "cli_writes", f"/cdir_{i}", "-m", f"mk-{i}"]),
            ("file.cp (file)", lambda i: ["file", "cp", PSZ, "cli_writes", "/cedit.txt", f"/ccp_{i}.txt", "-m", f"cp-{i}"]),
            ("file.mv (file)", lambda i: ["file", "mv", PSZ, "cli_writes", f"/ccp_{i}.txt", f"/cmv_{i}.txt", "-m", f"mv-{i}"]),
            ("file.rm (file)", lambda i: ["file", "rm", PSZ, "cli_writes", f"/cmv_{i}.txt", "-m", f"rm-{i}"]),
        ]:
            def op_thunk(mk=mk) -> dict:
                cli.call(mk(-1))  # declared warm preconditioning
                return summarize_calls([cli.call(mk(i)) for i in range(n_write)])
            guarded(rows, name, "write", op_thunk)

    rows.extend(run_cli_limits(cli, S, ctx))
    return {"rows": rows, "concurrency": run_cli_concurrency(cli, S, PSZ, seed)}


def run_cli_limits(cli: CliRunner, S: str, ctx) -> list[dict]:
    """T3: limits as rows. Every probe is one row with its status and code."""
    PSZ = f"{S}/sizes"
    rows: list[dict] = []
    try:
        cli.ok(["branch", "fork", PSZ, "cli_limits", "main"])
    except CaseAbort as abort:
        return [{**abort.row("branch.fork (cli_limits)"), "kind": "setup"}]
    for mib in ctx.write_ladder_mib:
        name = f"limit: file.write content {mib} MiB"
        if not ctx.guard(mib * 3):
            rows.append(ctx.guard_row(name, "limit"))
            continue

        def thunk(mib=mib) -> dict:
            body = LINE64 * (mib * LINES_PER_MIB) + "\n"
            r = cli.call(["file", "write", PSZ, "cli_limits", f"/lim_{mib}m.txt", "-m", f"lim-{mib}"], content=body)
            return {**summarize_calls([r]), "limit": {"content_bytes": len(body)}}
        guarded(rows, name, "limit", thunk)
    last_apply = None
    for count in ctx.apply_rows:
        def apply_thunk(count=count) -> dict:
            nonlocal last_apply
            br = f"cli_apply_{count}"
            cli.ok(["branch", "fork", PSZ, br, "main"])
            ops = json.dumps([{"op": "write", "path": f"/f{j:05d}.txt", "content": f"v={j}\n"} for j in range(count)])
            r = cli.call(["file", "apply", PSZ, br, "-m", f"apply-{count}"], content=ops)
            last_apply = (br, count)
            return {**summarize_calls([r]), "limit": {"rows": count}}
        guarded(rows, f"limit: file.apply {count} rows", "limit", apply_thunk)
    for limit in (1000, 1001):
        def diff_thunk(limit=limit) -> dict:
            if not last_apply:
                raise CaseAbort("NOT_RUN", message="no apply branch to diff (every apply probe failed)")
            r = cli.call(["commit", "diff", PSZ, last_apply[0], "--from", "main", "--with", "patch", "--limit", str(limit)])
            return {**summarize_calls([r]), "limit": {
                "changed_paths": last_apply[1], "page_limit": limit,
                "items": len(r["data"]["items"]), "has_next": r["data"].get("next_cursor") is not None}}
        guarded(rows, f"limit: commit.diff page limit {limit}", "limit", diff_thunk)
    for limit in (2000, 2001):
        def read_thunk(limit=limit) -> dict:
            r = cli.call(["file", "read", PSZ, "main", "/sz_16m.txt", "--line", "1", "--limit", str(limit)])
            return {**summarize_calls([r]), "limit": {
                "lines_asked": limit, "reply_bytes": len(r["stdout"].encode("utf-8")),
                "text_bytes": len(r["data"].get("text", "").encode("utf-8")),
                "has_next_line": r["data"].get("next_line") is not None}}
        guarded(rows, f"limit: file.read window {limit} lines", "limit", read_thunk)
    return rows


def conc_run(workload: str, workers: int, total: int, work) -> dict:
    t0 = time.perf_counter()
    ok_cnt = 0
    refusals: dict[str, int] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for r in pool.map(work, range(total)):
            if r["rc"] == 0:
                ok_cnt += 1
            else:
                code = "Timeout" if r["timed_out"] else refusal_code(r["stderr"], r["stdout"])[0]
                refusals[code] = refusals.get(code, 0) + 1
    wall_s = time.perf_counter() - t0
    return {"workload": workload, "workers": workers, "total": total, "ok": ok_cnt, "refusals": refusals,
            "throughput_calls_s": round(ok_cnt / wall_s, 2) if wall_s > 0 else 0.0}


def run_cli_concurrency(cli: CliRunner, S: str, PSZ: str, seed: dict) -> list[dict]:
    out: list[dict] = []
    P = f"{S}/f1k" if "F1k" in seed["trees"] else None
    if P:
        for workers in (1, 4, 8):
            out.append(conc_run(f"CLI readers x{workers}", workers, workers * 8, lambda idx: cli.raw(
                ["file", "read", P, "main", tree_path(idx % 100)], trace=False)))
    try:
        for w in range(4):
            cli.ok(["branch", "fork", PSZ, f"conc_sep_{w}", "main"])
        cli.ok(["branch", "fork", PSZ, "conc_same", "main"])
    except CaseAbort as abort:
        out.append({"workload": "CLI writers (branch setup)", "workers": 0, "total": 0, "ok": 0,
                    "refusals": {abort.code or abort.status: 1}, "throughput_calls_s": 0.0})
        return out
    out.append(conc_run("CLI writers x4 (separate branches)", 4, 16, lambda idx: cli.raw(
        ["file", "write", PSZ, f"conc_sep_{idx % 4}", f"/w_{idx}.txt", "-m", f"sep-{idx}"], content=f"v={idx}\n", trace=False)))
    out.append(conc_run("CLI writers x4 (same branch)", 4, 16, lambda idx: cli.raw(
        ["file", "write", PSZ, "conc_same", f"/same_{idx}.txt", "-m", f"same-{idx}"], content=f"v={idx}\n", trace=False)))
    return out


def seed_store(cli: CliRunner, store: str, ctx) -> dict:
    """Seed the requested trees, sizes and history projects into `store`; each tree init is a row."""
    rows: list[dict] = list(ctx.pre_rows)
    trees: list[str] = []
    for label in ctx.trees:
        case = f"project.init ({label})"
        if not ctx.guard(1):
            rows.append(ctx.guard_row(case, "setup"))
            continue
        try:
            r = cli.call(["project", "init", f"{store}/{label.lower()}", str(ctx.fx[label]["root"])])
            rows.append({"case": case, "kind": "setup", "status": "OK", **summarize_calls([r])})
            trees.append(label)
        except CaseAbort as abort:
            rows.append(abort.row(case, "setup"))
    cli.ok(["project", "init", f"{store}/sizes", str(ctx.fx["sizes"]["root"])])
    cli.ok(["project", "init", f"{store}/hist", str(ctx.fx["hist"]["root"])])
    depths: list[int] = []
    for d in ctx.h_depths:
        case = f"history seed (H{d})"
        try:
            if d == 1:
                cli.ok(["branch", "fork", f"{store}/hist", "h1", "main"])
                cli.ok(["file", "write", f"{store}/hist", "h1", "/target.txt", "-m", "h1-1"], content="line0\nline1\n")
            else:
                cli.ok(["branch", "fork", f"{store}/hist", f"h{d}", "main"])
                for i in range(1, d + 1):
                    cli.ok(["file", "write", f"{store}/hist", f"h{d}", "/target.txt", "-m", f"h-{i}"], content=f"base\nrev={i}\n")
            depths.append(d)
        except CaseAbort as abort:
            rows.append(abort.row(case, "setup"))
    return {"rows": rows, "trees": trees, "h_depths": depths}


def verify_fixtures(cli: CliRunner, store: str, ctx, work: Path, tag: str, trees: list[str]) -> dict:
    """Export each seeded read fixture (main) after the write rows and compare its manifest hash."""
    out: dict = {}
    labels = [(t, t.lower()) for t in trees] + [("sizes", "sizes"), ("hist", "hist")]
    for label, proj in labels:
        dest = work / f"exp_{tag}_{proj}"
        try:
            cli.call(["project", "export", f"{store}/{proj}", str(dest)])
            after, _ = fixture_manifest(dest)
            out[label] = {"expected": ctx.fx[label]["sha"], "after_writes": after, "match": after == ctx.fx[label]["sha"]}
        except CaseAbort as abort:
            out[label] = {"expected": ctx.fx[label]["sha"], "after_writes": None, "match": None, "note": str(abort)[:200]}
        finally:
            shutil.rmtree(dest, ignore_errors=True)
    return out


# ---------------------------------------------------------------- identity / finalize

def host_identity() -> dict:
    cpu, ram = platform.processor() or platform.machine(), None
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal"):
                ram = round(int(line.split()[1]) / 1024 / 1024, 1)
                break
    except OSError:
        pass
    return {"cpu": cpu, "cpus": os.cpu_count(), "ram_gib": ram, "kernel": platform.release(), "os": platform.system(),
            "arch": platform.machine()}


def finalize_arm(arm: dict, ident: dict, backend: str, front_end: str) -> None:
    """Stamp identity, normalise Node rows, run Node-side manifest proofs, register INELIGIBLE cold rows."""
    ident = {**ident, "backend": backend, "front_end": front_end}
    proofs = arm.pop("_proofs", {})
    out: list[dict] = []
    for row in arm["rows"]:
        sample = row.pop("_sample", None)
        row.setdefault("kind", "read" if row["case"] in proofs else "write")
        row.setdefault("cache_state", "warm (declared preconditioning)")
        if row["case"].startswith("limit: "):
            row["source"] = LIMIT_SOURCES[lim_key(row["case"])]
        if front_end == "sdk" and row["case"] in proofs and row.get("status") == "OK":
            fixture, desc, check = proofs[row["case"]]
            matched = 1 if (sample is not None and check(sample)) else 0
            row["proof"] = {"manifest": {"fixture": fixture, "manifest_sha256": arm["_fx"][fixture]["sha"],
                                         "check": desc + " (last sample)", "checked": 1, "matched": matched,
                                         "match": matched == 1}}
        row["identity"] = ident
        out.append(row)
    cold: list[dict] = []
    for row in out:
        if row.get("kind") != "read":
            continue
        a = assess_cache(None, row["case"], "native", backend)
        cold.append({
            "case": f"{row['case']} [cold]", "kind": "cold", "status": a["status"], "n": 0,
            "requested_cache": "cold", "cache_state": "no cold claim: INELIGIBLE",
            "required_domains": a["required_domains"], "reason": " ".join(a["reasons"]),
            "assessment": a, "identity": ident})
    arm["rows"] = out + cold
    for c in arm.get("concurrency", []):
        c["identity"] = ident
    arm.pop("_fx", None)


def lim_key(case: str) -> str:
    for key in ("file.write", "file.apply", "commit.diff", "file.read"):
        if f"limit: {key}" in case:
            return key if key != "file.write" else "file.write content"
    raise KeyError(case)


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cli", type=Path, required=True, help="path to the layerfs CLI binary")
    ap.add_argument("--node-pkg", type=Path, required=True, help="the package ENTRY FILE (api/node/src/index.js), not its directory")
    ap.add_argument("--node-bin", default=shutil.which("node") or "node")
    ap.add_argument("--source-dir", type=Path, required=True)
    ap.add_argument("--source", required=True, help="the FULL 40-hex commit; must equal HEAD of --source-dir")
    ap.add_argument("--pg-admin-url", default="")
    ap.add_argument("--pg-user", default="layerfs_pg")
    ap.add_argument("--pg-password", default="layerfs-test-pw")
    ap.add_argument("--n-read", type=int, default=15)
    ap.add_argument("--n-write", type=int, default=10)
    ap.add_argument("--h-depth", type=int, default=50, help="single history depth (used when --h-depths is empty)")
    ap.add_argument("--h-depths", default="", help="comma list of history depths, e.g. 10,100,1000 (H1 always runs)")
    ap.add_argument("--trees", default="F100,F1k,F10k", help="comma list from F100,F1k,F10k,F100k")
    ap.add_argument("--big-write-mib", type=int, default=0, help="add a file.write case of this many MiB (e.g. 64); 0 = off")
    ap.add_argument("--write-ladder-mib", default="16,64,256", help="file.write content sizes probed as limit rows")
    ap.add_argument("--apply-rows", default="1000,8191,8192", help="file.apply row counts probed as limit rows")
    ap.add_argument("--node-arm-timeout", type=float, default=1800, help="wall cap of one Node SDK arm process, seconds")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()

    trees = [t for t in args.trees.split(",") if t]
    bad = [t for t in trees if t not in TREE_SIZES]
    assert not bad, f"unknown --trees {bad}; choose from {list(TREE_SIZES)}"
    h_depths = sorted({1, *(int(x) for x in args.h_depths.split(",") if x)} if args.h_depths else {1, args.h_depth})
    write_ladder = [int(x) for x in args.write_ladder_mib.split(",") if x]
    apply_rows = [int(x) for x in args.apply_rows.split(",") if x]

    head = subprocess.check_output(["git", "-C", str(args.source_dir), "rev-parse", "HEAD"], text=True).strip()
    assert head == args.source and len(head) == 40, f"HEAD {head} != --source {args.source} (give the full 40-hex commit)"
    assert args.node_pkg.is_file(), f"--node-pkg must be the package entry file, got {args.node_pkg}"
    args.output.mkdir(parents=True, exist_ok=True)
    tmp_base = Path(os.environ.get("LAYERFS_TEST_TMPDIR") or tempfile.gettempdir())
    tmp_base.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="fs_file_calls_", dir=tmp_base))
    free_start = round(free_gb(work), 1)

    def guard(need_gb: float) -> bool:
        return free_gb(work) - need_gb >= MIN_FREE_GB

    def guard_row(case: str, kind: str = "write") -> dict:
        return {"case": case, "kind": kind, "status": "NOT_RUN", "n": 0,
                "message": f"disk guard: {free_gb(work):.1f} GB free, less than {MIN_FREE_GB} GB would remain"}

    pre_rows: list[dict] = []
    fixtures = work / "fixtures"
    fixtures.mkdir()
    fx: dict = {}
    built_trees: list[str] = []
    for label in trees:
        if label in BIG_TREES and not guard(3):
            pre_rows.append(guard_row(f"fixture {label}", "setup"))
            continue
        make_tree(fixtures / label.lower(), TREE_SIZES[label])
        fx[label] = register_fixture(fixtures / label.lower())
        built_trees.append(label)
    make_size_files(fixtures / "sizes")
    fx["sizes"] = register_fixture(fixtures / "sizes")
    (fixtures / "hist_seed").mkdir()
    (fixtures / "hist_seed" / "target.txt").write_text("base\nrev=0\n", encoding="utf-8")
    fx["hist"] = register_fixture(fixtures / "hist_seed")
    proofs = build_proofs(fx, h_depths)

    cli_sha = sha256_file(args.cli)
    addon = Path(os.environ.get("LAYERFS_NATIVE") or args.node_pkg.parent.parent / "layerfs.node")
    base_ident = {
        "source_commit": head, "cli_sha256": cli_sha,
        "addon_sha256": sha256_file(addon) if addon.is_file() else "UNAVAILABLE: addon file not found",
        "addon_path": str(addon), "host": host_identity(), "route": "native",
    }
    ctx = SimpleNamespace(args=args, fx=fx, proofs=proofs, trees=built_trees, h_depths=h_depths, pre_rows=pre_rows,
                          write_ladder_mib=write_ladder, apply_rows=apply_rows, guard=guard, guard_row=guard_row)

    results: dict = {
        "meta": {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_sha": head, "cli": str(args.cli), "cli_sha256": cli_sha,
            "addon_sha256": base_ident["addon_sha256"],
            "host": f"{platform.system()} {platform.release()} ({platform.machine()})",
            "n_read": args.n_read, "n_write": args.n_write, "h_depth": h_depths[-1], "h_depths": h_depths,
            "trees": built_trees, "big_write_mib": args.big_write_mib, "cap_s": CAP_S,
            "disk_free_gb_start": free_start,
            "cache_state": "warm (declared preconditioning; OS page cache not dropped — labelled diagnostic)",
        },
        "fixtures": {k: {"manifest_sha256": v["sha"], "files": v["files"], "bytes": v["bytes"]} for k, v in fx.items()},
        "arms": {},
        "not_run": [
            {"route": "worker:docker", "reason": "NOT_RUN: Docker daemon unavailable on this non-root Linux host"},
            {"route": "worker:lima", "reason": "NOT_RUN: Lima VM unavailable on this Linux host"},
            {"route": "worker:apple-container", "reason": "NOT_RUN: macOS-only route"},
        ],
        "proof": {},
        "failed_arms": {},
    }

    def run_arm(tag: str, backend: str, cli: CliRunner, store: str, home: Path, pg: PgStat | None, pg_cfg: dict, ident: dict) -> None:
        seed = seed_store(cli, store, ctx)
        cli_arm = run_cli_bench(cli, store, ctx, seed, pg)
        node_cfg = {
            "n_read": args.n_read, "n_write": args.n_write, "cap_s": CAP_S, "trees": seed["trees"],
            "big_trees": list(BIG_TREES), "h_depths": seed["h_depths"], "big_write_mib": args.big_write_mib,
            "write_ladder_mib": write_ladder, "apply_rows": apply_rows, "sample_path": SAMPLE_PATH,
            "rare": RARE, "common": COMMON, **pg_cfg,
        }
        sdk_arm = run_node_sdk_bench(args.node_bin, args.node_pkg, home, store, node_cfg, args.node_arm_timeout)
        sdk_arm["rows"] = list(ctx.pre_rows) + sdk_arm["rows"]
        sdk_arm["concurrency"] = []
        for arm in (cli_arm, sdk_arm):
            arm["_proofs"], arm["_fx"] = proofs, fx
        finalize_arm(cli_arm, ident, backend, "cli")
        finalize_arm(sdk_arm, ident, backend, "sdk")
        results["arms"][f"{tag}_cli"] = cli_arm
        results["arms"][f"{tag}_sdk"] = sdk_arm
        verified = verify_fixtures(cli, store, ctx, work, tag, seed["trees"])
        results["proof"][f"{tag}_manifest_unchanged_after_writes"] = verified
        if "F100" in verified:
            results["proof"][f"{tag}_f100_export_sha256_match"] = verified["F100"]["match"]
        results["proof"][f"{tag}_sdk_edit_match"] = sdk_arm["proof"].get("edit_final_ok", False)

    pg_db_name = f"bench_file_calls_{os.getpid()}"
    pg_created = False
    try:
        # 1. Native SQLite (ext4)
        home_sq = work / "home_sqlite"
        home_sq.mkdir(mode=0o700)
        home_sq.chmod(0o700)
        cli_sq = CliRunner(args.cli, home_sq, trace_file=args.output / "trace_sqlite.jsonl")
        cli_sq.ok(["home", "init"])
        help_j, _ = cli_sq.ok(["help", "--json"])
        avail_calls = {f"{c['family']}.{c['call']}" for c in help_j["calls"]}
        missing = [c for c in CALL_INVENTORY if c not in avail_calls]
        assert not missing, f"Missing expected 2.0 calls: {missing}"
        cli_sq.ok(["store", "create", "sq"])
        run_arm("sqlite", "sqlite", cli_sq, "sq", home_sq, None, {}, base_ident)
        cli_sq.ok(["store", "remove", "sq"])

        # 2. Native PostgreSQL 18 (code path validated later; skipped without --pg-admin-url)
        if args.pg_admin_url:
            try:
                pg_ident = pg_identity(args.pg_admin_url)
                psql(args.pg_admin_url, f"DROP DATABASE IF EXISTS {pg_db_name} WITH (FORCE);")
                psql(args.pg_admin_url, f"CREATE DATABASE {pg_db_name} OWNER {args.pg_user};")
                pg_created = True
                pg_clean_url = f"postgresql://127.0.0.1:55432/{pg_db_name}?sslmode=disable"
                home_pg = work / "home_pg"
                home_pg.mkdir(mode=0o700)
                home_pg.chmod(0o700)
                cli_pg = CliRunner(args.cli, home_pg, trace_file=args.output / "trace_pg.jsonl")
                cli_pg.ok(["home", "init"])
                rc, _o, err = cli_pg.run_stdin(["store", "save-auth", "pg", "--user", args.pg_user, "--password-stdin"], f"{args.pg_password}\n")
                assert rc == 0, f"save-auth failed: {err.strip()}"
                cli_pg.ok(["store", "connect", "pg", pg_clean_url, "--auth", "pg", "--synchronous-commit", "off"])
                pg_cfg = {"pg_admin_url": args.pg_admin_url, "pg_top_sql": PG_TOP_SQL.format(db=pg_db_name)}
                run_arm("pg", "postgresql", cli_pg, "pg", home_pg, PgStat(args.pg_admin_url, pg_db_name), pg_cfg,
                        {**base_ident, "pg": pg_ident})
                cli_pg.ok(["store", "disconnect", "pg"])
            except Exception as error:  # keep the SQLite results; the PG arm is recorded as failed
                results["failed_arms"]["pg"] = f"{type(error).__name__}: {error}"
                print(f"PG arm failed: {error}", file=sys.stderr)
        else:
            results["not_run"].append({"route": "native:postgresql", "reason": "NOT_RUN: --pg-admin-url not given"})
    finally:
        if pg_created and args.pg_admin_url:
            subprocess.run(["psql", args.pg_admin_url, "-c", f"DROP DATABASE IF EXISTS {pg_db_name} WITH (FORCE);"], check=False, capture_output=True)
        results["meta"]["disk_free_gb_end"] = round(free_gb(work), 1)
        shutil.rmtree(work, ignore_errors=True)

    results["identity"] = base_ident
    if "pg_cli" in results["arms"]:
        results["identity"]["pg"] = results["arms"]["pg_cli"]["rows"][0]["identity"].get("pg")

    # Local JSON & CSV receipts (ignored by git; AGENTS.md:64-65)
    (args.output / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    with (args.output / "results.csv").open("w", newline="", encoding="utf-8") as cf:
        w = csv.writer(cf)
        w.writerow(["arm", "case", "kind", "status", "code", "n", "p50_ms", "p95_ms", "max_ms", "calls_per_s",
                    "cpu_ms", "max_rss_bytes", "dispatch_ms_p50", "delta_stored_bytes", "delta_size_bytes"])
        for arm_name, arm_data in results["arms"].items():
            for r in arm_data["rows"]:
                w.writerow([arm_name, r["case"], r.get("kind", ""), r.get("status", ""), r.get("code", ""), r.get("n", ""),
                            r.get("p50_ms", ""), r.get("p95_ms", ""), r.get("max_ms", ""), r.get("calls_per_s", ""),
                            r.get("cpu_ms_p50", r.get("cpu_ms_per_call", "")), r.get("max_rss_bytes", r.get("max_rss_kib", "")),
                            r.get("dispatch_ms_p50", ""), r.get("delta_stored_bytes", ""), r.get("delta_size_bytes", "")])

    write_report(results, args, head)
    print(f"Wrote report to {args.report} and receipts to {args.output}")


# ---------------------------------------------------------------- report

def cell(r: dict | None) -> str:
    if not r:
        return "—"
    st = r.get("status", "OK")
    if st != "OK":
        extra = r.get("code") or (f"cap {r['cap_s']} s" if r.get("cap_s") else "")
        return f"{st} {extra}".strip()
    return f"{r['p50_ms']:.2f} / {r['p95_ms']:.2f}"


def write_report(results: dict, args, head: str) -> None:
    args.report.parent.mkdir(parents=True, exist_ok=True)
    arms = results["arms"]
    ident = results["identity"]
    by = {name: {r["case"]: r for r in a["rows"]} for name, a in arms.items()}
    pg_ran = "pg_cli" in arms
    ran = ["native SQLite (ext4)"] + ([f"PostgreSQL {ident['pg']['version']}"] if pg_ran else [])
    warm = [r for a in arms.values() for r in a["rows"] if r.get("kind") in ("read", "write", "limit", "setup")]
    counts: dict[str, int] = {}
    for r in warm:
        counts[r.get("status", "OK")] = counts.get(r.get("status", "OK"), 0) + 1
    cold_n = sum(1 for a in arms.values() for r in a["rows"] if r.get("kind") == "cold")
    fails = counts.get("FAIL", 0)
    stat_case = "file.stat (F1k)"
    stat_bits = []
    for name, label in (("sqlite_sdk", "SQLite SDK"), ("sqlite_cli", "SQLite CLI"), ("pg_sdk", "PG SDK"), ("pg_cli", "PG CLI")):
        r = by.get(name, {}).get(stat_case)
        if r and r.get("status") == "OK":
            stat_bits.append(f"{label} `{r['p50_ms']} ms`")
    proofs_ok = all(v is not False for k, v in results["proof"].items() if k.endswith("_match"))
    headline = (
        f"**{'PASS' if not fails else 'PARTIAL'} (diagnostic warm): measured the mountless LayerFS 2.0 `file.*` + `commit.diff` calls "
        f"across CLI and persistent `@layerfs/node` SDK on {' and '.join(ran)}"
        + (f" ({stat_case} p50: {', '.join(stat_bits)})" if stat_bits else "")
        + f"; rows by status: {', '.join(f'{k} {v}' for k, v in sorted(counts.items()))}; "
        f"{cold_n} cold rows registered as INELIGIBLE (no cold claim); "
        f"fixture and export proofs {'passed' if proofs_ok else 'FAILED'}; "
        f"{len(results['not_run'])} unavailable routes recorded as NOT_RUN.**"
    )
    host = ident["host"]
    lines = [
        f"# fs-file-calls — {head[:10]}", "", headline, "",
        "## Configuration & Provenance", "",
        "| Field | Value |", "| --- | --- |",
        f"| LayerFS commit | `{head}` |",
        f"| CLI binary SHA-256 | `{ident['cli_sha256']}` |",
        f"| Node addon SHA-256 | `{ident['addon_sha256']}` |",
        f"| Host | {host['cpu']}, {host['cpus']} CPUs, {host['ram_gib']} GiB RAM, kernel {host['kernel']} |",
        f"| Machine route | `{ident['route']}` (`LAYERFS_TEST_TMPDIR` on ext4); Node SDK arm is a persistent-client exception to \"public CLI for every operation\" |",
    ]
    if pg_ran:
        pg = ident["pg"]
        lines.append(f"| PostgreSQL | {pg['version']}, pg_stat_statements: {pg['pg_stat_statements']}, store `synchronous_commit=off`; settings `{json.dumps(pg['settings'])}` |")
    else:
        lines.append("| PostgreSQL | NOT_RUN (`--pg-admin-url` not given) |")
    m = results["meta"]
    lines += [
        f"| Sample sizes | reads `N={m['n_read']}` (F10k/F100k/deeper history capped), writes `N={m['n_write']}`, trees {', '.join(m['trees'])}, history {', '.join('H' + str(d) for d in m['h_depths'])} |",
        f"| Per-call cap | {m['cap_s']} s; a call over it is a FAIL row and the run continues |",
        f"| Disk free (GB) | start {m['disk_free_gb_start']}, end {m.get('disk_free_gb_end')} (stop below {MIN_FREE_GB}) |",
        f"| Cache protocol | {m['cache_state']} |",
        "| Local receipts | `results.json` / `results.csv` under `--output`, not committed (AGENTS.md:64-65) |",
        "", "## Fixtures (manifest = sha256 over sorted path, size, content sha256)", "",
        "| Fixture | Files | Bytes | Manifest SHA-256 | Unchanged after write rows |", "| --- | ---: | ---: | --- | --- |",
    ]
    for label, f in results["fixtures"].items():
        after = []
        for tag in ("sqlite", "pg"):
            v = results["proof"].get(f"{tag}_manifest_unchanged_after_writes", {}).get(label)
            if v is not None:
                after.append(f"{tag}: {v['match']}")
        lines.append(f"| {label} | {f['files']} | {f['bytes']} | `{f['manifest_sha256'][:16]}…` | {', '.join(after) or '—'} |")

    cols = [(n, t) for n, t in (("sqlite_sdk", "SQLite SDK"), ("sqlite_cli", "SQLite CLI"), ("pg_sdk", "PG SDK"), ("pg_cli", "PG CLI")) if n in arms]
    lines += ["", "## Latency by Call (p50 / p95 ms, warm diagnostic)", "",
              "| Case | " + " | ".join(f"{t} p50 / p95" for _, t in cols) + " |", "| --- | " + " | ".join("---:" for _ in cols) + " |"]
    cases = list(dict.fromkeys(r["case"] for a in arms.values() for r in a["rows"] if r.get("kind") in ("read", "write")))
    for case in cases:
        lines.append(f"| `{case}` | " + " | ".join(cell(by[n].get(case)) for n, _ in cols) + " |")

    lines += ["", "## Resources and native dispatch (CLI: per-call rusage; SDK: process deltas per call)", "",
              "| Case | CLI CPU ms p50 | CLI max RSS MiB | CLI dispatch ms p50 | SDK CPU ms/call | SDK RSS delta MiB |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for case in cases:
        c, s = by["sqlite_cli"].get(case, {}), by["sqlite_sdk"].get(case, {})
        if c.get("status") != "OK" and s.get("status") != "OK":
            continue
        mib = lambda v: f"{v / 1048576:.1f}" if isinstance(v, (int, float)) else "—"
        lines.append(f"| `{case}` | {c.get('cpu_ms_p50', '—')} | {mib(c.get('max_rss_bytes'))} | {c.get('dispatch_ms_p50', '—') if c.get('dispatch_ms_p50') is not None else 'UNAVAILABLE'} | {s.get('cpu_ms_per_call', '—')} | {mib(s.get('rss_delta_bytes'))} |")
    lines += ["", f"Step attribution: native rows carry the `dispatch` step only; `route`, `connect`, `request` are UNAVAILABLE on native. Source: {TRACE_SRC}.",
              "The step table for worker rows needs the worker route (T6)."]

    lines += ["", "## Write Commit Storage Growth", "",
              "| Write Case | " + " | ".join(f"{t} `delta_stored_bytes` / `delta_size_bytes`" for n, t in cols if n.endswith("_sdk") or n.endswith("_cli")) + " |",
              "| --- | " + " | ".join("---" for _ in cols) + " |"]
    for case in [c for c in cases if c.startswith("file.write (")]:
        lines.append(f"| `{case}` | " + " | ".join(
            f"{by[n].get(case, {}).get('delta_stored_bytes', '—')} / {by[n].get(case, {}).get('delta_size_bytes', '—')}" for n, _ in cols) + " |")

    lines += ["", "## Limits (one row per probe; cites the source that sets the limit)", "",
              "| Probe | Arm | Status | Code | ms | Detail | Source |", "| --- | --- | --- | --- | ---: | --- | --- |"]
    for name, a in arms.items():
        for r in a["rows"]:
            if r.get("kind") == "limit":
                lines.append(f"| `{r['case']}` | {name} | {r['status']} | {r.get('code', '')} | {r.get('p50_ms', '—')} | `{json.dumps(r.get('limit', {}))}` {r.get('message', '')[:100]} | {'; '.join(r.get('source', [])[:2])} |")

    lines += ["", "## Cold rows", "",
              "Cold rows are registered per read case and gated by `shared/src/measure.py:181 assess_cache`; none is measured, none is labelled cold (`shared/AGENTS.md:7`).", "",
              "| Arm | Cold rows | Status | Required domains | Reason |", "| --- | ---: | --- | --- | --- |"]
    for name, a in arms.items():
        cr = [r for r in a["rows"] if r.get("kind") == "cold"]
        if cr:
            lines.append(f"| {name} | {len(cr)} | {cr[0]['status']} | {', '.join(cr[0]['required_domains'])} | {cr[0]['reason']} |")

    bad = [(n, r) for n, a in arms.items() for r in a["rows"] if r.get("status") not in ("OK", "INELIGIBLE") and r.get("kind") != "limit"]
    lines += ["", "## Rows that are not OK (REFUSED / FAIL / NOT_RUN)", ""]
    if bad:
        lines += ["| Arm | Case | Status | Code / cap | Message |", "| --- | --- | --- | --- | --- |"]
        for n, r in bad:
            lines.append(f"| {n} | `{r['case']}` | {r['status']} | {r.get('code') or r.get('cap_s') or ''} | {r.get('message', '')[:160]} |")
    else:
        lines.append("none")

    lines += ["", "## Concurrency & Refusals (CLI Process-per-Call)", "",
              "| Backend | Workload | OK / Total | Throughput (calls/s) | Refusals by Code |", "| --- | --- | ---: | ---: | --- |"]
    for label, key in (("SQLite", "sqlite_cli"), ("PostgreSQL", "pg_cli")):
        for c in arms.get(key, {}).get("concurrency", []):
            ref = ", ".join(f"{k}:{v}" for k, v in sorted(c["refusals"].items())) or "none"
            lines.append(f"| {label} | {c['workload']} | {c['ok']} / {c['total']} | {c['throughput_calls_s']} | `{ref}` |")

    lines += ["", "## Registered NOT_RUN Routes", "", "| Route | Status & Reason |", "| --- | --- |"]
    lines += [f"| `{nr['route']}` | {nr['reason']} |" for nr in results["not_run"]]
    if results["failed_arms"]:
        lines += ["", "## Failed arms", ""] + [f"- `{k}`: {v}" for k, v in results["failed_arms"].items()]

    sq_cli, sq_sdk = by["sqlite_cli"].get(stat_case), by["sqlite_sdk"].get(stat_case)
    lines += ["", "## Main Observations & Cleanup", ""]
    if sq_cli and sq_sdk and sq_cli.get("status") == "OK" and sq_sdk.get("status") == "OK":
        lines.append(f"- **CLI vs persistent SDK**: on SQLite `{stat_case}` a fresh CLI process takes `{sq_cli['p50_ms']} ms` p50 against `{sq_sdk['p50_ms']} ms` for the persistent client.")
    if pg_ran and by["pg_sdk"].get(stat_case, {}).get("status") == "OK" and sq_sdk and sq_sdk.get("status") == "OK":
        lines.append(f"- **PostgreSQL vs SQLite**: persistent client `{stat_case}` `{by['pg_sdk'][stat_case]['p50_ms']} ms` (PostgreSQL) against `{sq_sdk['p50_ms']} ms` (SQLite).")
    lines.append("- **Cleanup**: owned SQLite store removed via `layerfs store remove`" + (", PostgreSQL store disconnected via `layerfs store disconnect`, scratch database dropped" if pg_ran else "") + ", temporary home/fixtures deleted.")
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
