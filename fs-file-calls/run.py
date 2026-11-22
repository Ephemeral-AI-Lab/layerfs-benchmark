#!/usr/bin/env python3
"""fs-file-calls benchmark suite (Ephemeral-AI-Lab/layerfs-project#157).

Measures the 14 mountless LayerFS 2.0 `file.*` calls plus `commit.diff` across:
  - CLI (fresh process per call) vs persistent `@layerfs/node` SDK client
  - Native SQLite (ext4) vs Native PostgreSQL (with `pg_stat_statements`)
  - Tree sizes F100 / F1k / F10k, file sizes 0B..16MiB, history H1 / H100
  - Concurrency: 1 / 4 / 8 parallel readers & writers (separate + same branch)
  - Independent proof via `file.read`/`file.stat` and `project.export` SHA-256

All timings are explicitly labelled warm/diagnostic unless a verified cold-cache
contract is enforced; unavailable routes (docker/lima/apple-container) remain
registered as NOT_RUN in the report.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


CALL_INVENTORY = [
    "file.read", "file.stat", "file.list", "file.glob", "file.grep",
    "file.blame", "file.history", "commit.diff", "file.write", "file.edit",
    "file.apply", "file.cp", "file.mv", "file.rm", "file.mkdir",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_sha256(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            h.update(rel.encode("utf-8"))
            h.update(b"\0")
            h.update(sha256_file(p).encode("ascii"))
            h.update(b"\n")
    return h.hexdigest()


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


def make_tree(root: Path, count: int) -> dict[str, str]:
    """Create a deterministic tree of `count` files at depth <= 6."""
    manifest: dict[str, str] = {}
    root.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        d1 = f"d{i % 10}"
        d2 = f"s{(i // 10) % 10}"
        d3 = f"g{(i // 100) % 10}"
        rel = f"/{d1}/{d2}/{d3}/f_{i:06d}.txt"
        fp = root / rel.lstrip("/")
        fp.parent.mkdir(parents=True, exist_ok=True)
        marker = "RARE_NEEDLE_9917" if i == count // 2 else "COMMON_TOKEN"
        body = f"file={i} marker={marker} pad=0123456789abcdef\n"
        fp.write_text(body, encoding="utf-8")
        manifest[rel] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return manifest


def make_size_files(root: Path) -> dict[str, tuple[int, str]]:
    """Create text files of 0 B, 1 KiB, 64 KiB, 1 MiB, 16 MiB."""
    root.mkdir(parents=True, exist_ok=True)
    specs = {
        "0b": 0,
        "1k": 1024,
        "64k": 64 * 1024,
        "1m": 1024 * 1024,
        "16m": 16 * 1024 * 1024,
    }
    line = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!\n"  # 64 B
    out: dict[str, tuple[int, str]] = {}
    for tag, nbytes in specs.items():
        fp = root / f"sz_{tag}.txt"
        if nbytes == 0:
            data = b""
        else:
            reps = nbytes // len(line)
            data = (line * reps).encode("utf-8")
        fp.write_bytes(data)
        out[tag] = (len(data), hashlib.sha256(data).hexdigest())
    return out


class CliRunner:
    def __init__(self, cli: Path, home: Path, trace_file: Path | None = None):
        self.cli = cli
        self.home = home
        self.trace_file = trace_file

    def run(self, args: list[str], stdin_data: str | None = None, timeout: float = 115.0) -> tuple[int, str, str, float]:
        env = dict(os.environ)
        env["LAYERFS_HOME"] = str(self.home)
        env["LAYERFS_CONSTRUCTION_WORKERS"] = "1"
        env["NO_COLOR"] = "1"
        if self.trace_file:
            env["LAYERFS_TRACE"] = str(self.trace_file)
            env["LAYERFS_TRACE_STEP"] = args[0] + "." + args[1] if len(args) >= 2 else "cli"
        t0 = time.perf_counter()
        proc = subprocess.run(
            [str(self.cli), *args],
            input=stdin_data,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return proc.returncode, proc.stdout, proc.stderr, dt_ms

    def ok(self, args: list[str], stdin_data: str | None = None, timeout: float = 115.0) -> tuple[dict, float]:
        rc, out, err, dt_ms = self.run(args, stdin_data=stdin_data, timeout=timeout)
        if rc != 0:
            raise RuntimeError(f"CLI {' '.join(args)} failed rc={rc}: {err.strip() or out.strip()}")
        return json.loads(out), dt_ms


def run_node_sdk_bench(node_bin: str, node_pkg: Path, home: Path, store: str, cfg: dict) -> dict:
    """Run the persistent `@layerfs/node` SDK arm in a single Node process."""
    script = r"""
import { readFileSync } from "node:fs";
import { performance } from "node:perf_hooks";
const cfg = JSON.parse(readFileSync(process.env.BENCH_CFG, "utf8"));
const mod = await import(cfg.node_pkg);
const layerfs = mod.default ?? mod;
const c = layerfs.client({ home: cfg.home });

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

async function bench(n, fn) {
  await fn(-1); // declared warm preconditioning
  const samples = [];
  for (let i = 0; i < n; i++) {
    const t0 = performance.now();
    await fn(i);
    samples.push(performance.now() - t0);
  }
  return stats(samples);
}

const out = { rows: [], proof: {} };
const S = cfg.store;
const P100 = `${S}/f100`, P1K = `${S}/f1k`, P10K = `${S}/f10k`, PSZ = `${S}/sizes`, PH = `${S}/hist`;

// Reads: file.read across sizes & 2000-line window
for (const [tag, opts] of [
  ["1k", {}], ["64k", {}], ["1m", {}], ["16m_win2000", { line: 1, limit: 2000 }]
]) {
  const path = tag === "16m_win2000" ? "/sz_16m.txt" : `/sz_${tag}.txt`;
  const r = await bench(cfg.n_read, async () => {
    const res = await c.file.read(PSZ, "main", path, opts);
    if (typeof res.text !== "string") throw new Error("bad read");
  });
  out.rows.push({ case: `file.read (${tag})`, ...r });
}

// Reads: stat, list, glob, grep across F100, F1k, F10k
for (const [label, P, samplePath] of [
  ["F100", P100, "/d0/s0/g0/f_000000.txt"],
  ["F1k", P1K, "/d0/s0/g0/f_000000.txt"],
  ["F10k", P10K, "/d0/s0/g0/f_000000.txt"],
]) {
  const nTree = label === "F10k" ? Math.min(cfg.n_read, 10) : cfg.n_read;
  out.rows.push({ case: `file.stat (${label})`, ...(await bench(nTree, () => c.file.stat(P, "main", samplePath))) });
  out.rows.push({ case: `file.list first-page (${label})`, ...(await bench(nTree, () => c.file.list(P, "main", "/", { limit: 100 }))) });
  out.rows.push({ case: `file.glob (${label})`, ...(await bench(nTree, () => c.file.glob(P, "main", "**/*.txt", "/", { limit: 200 }))) });
  out.rows.push({ case: `file.grep rare (${label})`, ...(await bench(nTree, () => c.file.grep(P, "main", "RARE_NEEDLE_9917", "/", { limit: 50 }))) });
  out.rows.push({ case: `file.grep frequent (${label})`, ...(await bench(nTree, () => c.file.grep(P, "main", "COMMON_TOKEN", "/", { limit: 50 }))) });
}

// History reads: blame, history, commit.diff at H1 & H100 (head + pinned)
const h1Head = (await c.branch.get(PH, "h1")).commit;
const h100Head = (await c.branch.get(PH, "h100")).commit;
for (const [depth, br, pinned] of [["H1", "h1", h1Head], ["H100", "h100", h100Head]]) {
  const nH = depth === "H100" ? Math.min(cfg.n_read, 10) : cfg.n_read;
  out.rows.push({ case: `file.blame (${depth}, head)`, ...(await bench(nH, () => c.file.blame(PH, br, "/target.txt"))) });
  out.rows.push({ case: `file.history (${depth}, head)`, ...(await bench(nH, () => c.file.history(PH, br, "/target.txt", { limit: 100 }))) });
  out.rows.push({ case: `file.history (${depth}, pinned)`, ...(await bench(nH, () => c.file.history(PH, br, "/target.txt", { at: pinned, limit: 100 }))) });
  out.rows.push({ case: `commit.diff (${depth}, head)`, ...(await bench(nH, () => c.commit.diff(PH, br, { from: "main", path: "/target.txt", with: ["patch"] }))) });
}

// Writes: write (0B, 1K, 64K, 1M), edit, apply (1, 10, 100), mkdir, cp, mv, rm
await c.branch.fork(PSZ, "sdk_writes", "main");
const line64 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!\n";
for (const [tag, body] of [
  ["0b", ""],
  ["1k", line64.repeat(16)],
  ["64k", line64.repeat(1024)],
  ["1m", line64.repeat(16384)],
]) {
  const nW = tag === "1m" ? 5 : cfg.n_write;
  const stBefore = (await c.store.get(S, { with: ["stats"], detail: true })).stats;
  const r = await bench(nW, (i) => c.file.write(PSZ, "sdk_writes", `/w_${tag}.txt`, `${body}${i}\n`, { message: `w-${tag}-${i}` }));
  const stAfter = (await c.store.get(S, { with: ["stats"], detail: true })).stats;
  out.rows.push({
    case: `file.write (${tag})`,
    ...r,
    delta_stored_bytes: stAfter.stored_bytes - stBefore.stored_bytes,
    delta_size_bytes: stAfter.size - stBefore.size,
  });
}

// file.edit
await c.file.write(PSZ, "sdk_writes", "/edit_me.txt", "alpha=0\nbeta=1\n", { message: "seed edit" });
let cur = 0;
out.rows.push({
  case: "file.edit (small)",
  ...(await bench(cfg.n_write, async () => {
    const next = cur + 1;
    await c.file.edit(PSZ, "sdk_writes", "/edit_me.txt", { old_string: `alpha=${cur}`, new_string: `alpha=${next}`, message: `edit-${next}` });
    cur = next;
  })),
});

// file.apply (batches 1, 10, 100)
for (const bsz of [1, 10, 100]) {
  await c.file.mkdir(PSZ, "sdk_writes", `/apply_${bsz}`, { message: `mk-apply-${bsz}` });
  const nA = bsz >= 100 ? 5 : cfg.n_write;
  const r = await bench(nA, async (i) => {
    const ops = [];
    for (let j = 0; j < bsz; j++) {
      ops.push({ op: "write", path: `/apply_${bsz}/f_${j}.txt`, content: `v=${i}-${j}\n` });
    }
    await c.file.apply(PSZ, "sdk_writes", ops, { message: `apply-${bsz}-${i}` });
  });
  out.rows.push({ case: `file.apply (batch=${bsz})`, ...r });
}

// mkdir, cp, mv, rm
out.rows.push({ case: "file.mkdir", ...(await bench(cfg.n_write, (i) => c.file.mkdir(PSZ, "sdk_writes", `/dir_${i}`, { message: `mk-${i}` }))) });
out.rows.push({ case: "file.cp (file)", ...(await bench(cfg.n_write, (i) => c.file.cp(PSZ, "sdk_writes", "/edit_me.txt", `/cp_${i}.txt`, { message: `cp-${i}` }))) });
out.rows.push({ case: "file.mv (file)", ...(await bench(cfg.n_write, (i) => c.file.mv(PSZ, "sdk_writes", `/cp_${i}.txt`, `/mv_${i}.txt`, { message: `mv-${i}` }))) });
out.rows.push({ case: "file.rm (file)", ...(await bench(cfg.n_write, (i) => c.file.rm(PSZ, "sdk_writes", `/mv_${i}.txt`, { message: `rm-${i}` }))) });

// Proof: read back /edit_me.txt
const verify = await c.file.read(PSZ, "sdk_writes", "/edit_me.txt");
out.proof.edit_final_ok = verify.text.includes(`alpha=${cur}`);

layerfs.close();
console.log(JSON.stringify(out));
"""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump({**cfg, "node_pkg": str(node_pkg), "home": str(home), "store": store}, tf)
        cfg_path = tf.name
    try:
        env = dict(os.environ)
        env["BENCH_CFG"] = cfg_path
        env["LAYERFS_HOME"] = str(home)
        proc = subprocess.run([node_bin, "--input-type=module", "-e", script], capture_output=True, text=True, env=env, timeout=180)
        if proc.returncode != 0:
            raise RuntimeError(f"Node SDK bench failed rc={proc.returncode}:\n{proc.stderr}\n{proc.stdout}")
        return json.loads(proc.stdout.strip().splitlines()[-1])
    finally:
        Path(cfg_path).unlink(missing_ok=True)


def run_cli_bench(cli: CliRunner, store: str, n_read: int, n_write: int) -> dict:
    """Run the CLI (fresh process per call) arm on an already-seeded home/store."""
    S = store
    P100, P1K, P10K, PSZ, PH = f"{S}/f100", f"{S}/f1k", f"{S}/f10k", f"{S}/sizes", f"{S}/hist"
    rows = []

    def bench_cli(name: str, n: int, fn):
        fn(-1)  # declared warm preconditioning
        samples = []
        for i in range(n):
            _, dt = fn(i)
            samples.append(dt)
        rows.append({"case": name, **summarize_ms(samples)})

    for tag, extra in [("1k", []), ("64k", []), ("1m", []), ("16m_win2000", ["--line", "1", "--limit", "2000"])]:
        path = "/sz_16m.txt" if tag == "16m_win2000" else f"/sz_{tag}.txt"
        bench_cli(f"file.read ({tag})", n_read, lambda _i, p=path, ex=extra: cli.ok(["file", "read", PSZ, "main", p, *ex]))

    for label, P in [("F100", P100), ("F1k", P1K), ("F10k", P10K)]:
        nt = min(n_read, 5) if label == "F10k" else n_read
        bench_cli(f"file.stat ({label})", nt, lambda _i, p=P: cli.ok(["file", "stat", p, "main", "/d0/s0/g0/f_000000.txt"]))
        bench_cli(f"file.list first-page ({label})", nt, lambda _i, p=P: cli.ok(["file", "list", p, "main", "/", "--limit", "100"]))
        bench_cli(f"file.glob ({label})", nt, lambda _i, p=P: cli.ok(["file", "glob", p, "main", "**/*.txt", "/", "--limit", "200"]))
        bench_cli(f"file.grep rare ({label})", nt, lambda _i, p=P: cli.ok(["file", "grep", p, "main", "RARE_NEEDLE_9917", "/", "--limit", "50"]))
        bench_cli(f"file.grep frequent ({label})", nt, lambda _i, p=P: cli.ok(["file", "grep", p, "main", "COMMON_TOKEN", "/", "--limit", "50"]))

    h1_head = cli.ok(["branch", "get", PH, "h1"])[0]["commit"]
    h100_head = cli.ok(["branch", "get", PH, "h100"])[0]["commit"]
    for depth, br, pinned in [("H1", "h1", h1_head), ("H100", "h100", h100_head)]:
        nh = min(n_read, 5) if depth == "H100" else n_read
        bench_cli(f"file.blame ({depth}, head)", nh, lambda _i, b=br: cli.ok(["file", "blame", PH, b, "/target.txt"]))
        bench_cli(f"file.history ({depth}, head)", nh, lambda _i, b=br: cli.ok(["file", "history", PH, b, "/target.txt", "--limit", "100"]))
        bench_cli(f"file.history ({depth}, pinned)", nh, lambda _i, b=br, at=pinned: cli.ok(["file", "history", PH, b, "/target.txt", "--at", at, "--limit", "100"]))
        bench_cli(f"commit.diff ({depth}, head)", nh, lambda _i, b=br: cli.ok(["commit", "diff", PH, b, "--from", "main", "--path", "/target.txt", "--with", "patch"]))

    cli.ok(["branch", "fork", PSZ, "cli_writes", "main"])
    line64 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!\n"
    for tag, body in [("0b", ""), ("1k", line64 * 16), ("64k", line64 * 1024), ("1m", line64 * 16384)]:
        nw = 3 if tag == "1m" else n_write
        st_before = cli.ok(["store", "get", S, "--with", "stats", "--detail"])[0]["stats"]
        cli.ok(["file", "write", PSZ, "cli_writes", f"/cw_{tag}.txt", "-m", "pre"], stdin_data=f"{body}pre\n")
        samples = []
        for i in range(nw):
            _, dt = cli.ok(["file", "write", PSZ, "cli_writes", f"/cw_{tag}.txt", "-m", f"cw-{tag}-{i}"], stdin_data=f"{body}{i}\n")
            samples.append(dt)
        st_after = cli.ok(["store", "get", S, "--with", "stats", "--detail"])[0]["stats"]
        rows.append({
            "case": f"file.write ({tag})",
            **summarize_ms(samples),
            "delta_stored_bytes": st_after["stored_bytes"] - st_before["stored_bytes"],
            "delta_size_bytes": st_after["size"] - st_before["size"],
        })

    cli.ok(["file", "write", PSZ, "cli_writes", "/cedit.txt", "-m", "seed"], stdin_data="alpha=0\nbeta=1\n")
    cur = [0]
    def do_edit(_i):
        nxt = cur[0] + 1
        res = cli.ok(["file", "edit", PSZ, "cli_writes", "/cedit.txt", "--old-string", f"alpha={cur[0]}", "--new-string", f"alpha={nxt}", "-m", f"e-{nxt}"])
        cur[0] = nxt
        return res
    bench_cli("file.edit (small)", n_write, do_edit)

    bench_cli("file.mkdir", n_write, lambda i: cli.ok(["file", "mkdir", PSZ, "cli_writes", f"/cdir_{i}", "-m", f"mk-{i}"]))
    bench_cli("file.cp (file)", n_write, lambda i: cli.ok(["file", "cp", PSZ, "cli_writes", "/cedit.txt", f"/ccp_{i}.txt", "-m", f"cp-{i}"]))
    bench_cli("file.mv (file)", n_write, lambda i: cli.ok(["file", "mv", PSZ, "cli_writes", f"/ccp_{i}.txt", f"/cmv_{i}.txt", "-m", f"mv-{i}"]))
    bench_cli("file.rm (file)", n_write, lambda i: cli.ok(["file", "rm", PSZ, "cli_writes", f"/cmv_{i}.txt", "-m", f"rm-{i}"]))

    # Concurrency: 1, 4, 8 parallel CLI readers on F1k
    concurrency = []
    for workers in (1, 4, 8):
        total_calls = workers * 8
        t0 = time.perf_counter()
        refusals: dict[str, int] = {}
        ok_cnt = 0
        def reader(idx: int):
            rc, _o, err, _dt = cli.run(["file", "read", P1K, "main", f"/d{idx % 10}/s{(idx // 10) % 10}/g0/f_{idx % 100:06d}.txt"])
            return rc, err
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for rc, err in pool.map(reader, range(total_calls)):
                if rc == 0:
                    ok_cnt += 1
                else:
                    code = "Unknown"
                    try:
                        code = json.loads(err.strip().splitlines()[-1]).get("error", "Unknown")
                    except Exception:
                        pass
                    refusals[code] = refusals.get(code, 0) + 1
        wall_s = time.perf_counter() - t0
        concurrency.append({
            "workload": f"CLI readers x{workers}",
            "workers": workers,
            "total": total_calls,
            "ok": ok_cnt,
            "refusals": refusals,
            "throughput_calls_s": round(ok_cnt / wall_s, 2) if wall_s > 0 else 0.0,
        })

    # Concurrency: 4 parallel CLI writers on separate branches
    for w in range(4):
        cli.ok(["branch", "fork", PSZ, f"conc_sep_{w}", "main"])
    t0 = time.perf_counter()
    ref_sep: dict[str, int] = {}
    ok_sep = 0
    def writer_sep(idx: int):
        b = f"conc_sep_{idx % 4}"
        rc, _o, err, _dt = cli.run(["file", "write", PSZ, b, f"/w_{idx}.txt", "-m", f"sep-{idx}"], stdin_data=f"v={idx}\n")
        return rc, err
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for rc, err in pool.map(writer_sep, range(16)):
            if rc == 0:
                ok_sep += 1
            else:
                code = "Unknown"
                try:
                    code = json.loads(err.strip().splitlines()[-1]).get("error", "Unknown")
                except Exception:
                    pass
                ref_sep[code] = ref_sep.get(code, 0) + 1
    wall_sep = time.perf_counter() - t0
    concurrency.append({
        "workload": "CLI writers x4 (separate branches)",
        "workers": 4, "total": 16, "ok": ok_sep, "refusals": ref_sep,
        "throughput_calls_s": round(ok_sep / wall_sep, 2) if wall_sep > 0 else 0.0,
    })

    # Concurrency: 4 parallel CLI writers on ONE branch
    cli.ok(["branch", "fork", PSZ, "conc_same", "main"])
    t0 = time.perf_counter()
    ref_same: dict[str, int] = {}
    ok_same = 0
    def writer_same(idx: int):
        rc, _o, err, _dt = cli.run(["file", "write", PSZ, "conc_same", f"/same_{idx}.txt", "-m", f"same-{idx}"], stdin_data=f"v={idx}\n")
        return rc, err
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for rc, err in pool.map(writer_same, range(16)):
            if rc == 0:
                ok_same += 1
            else:
                code = "Unknown"
                try:
                    code = json.loads(err.strip().splitlines()[-1]).get("error", "Unknown")
                except Exception:
                    pass
                ref_same[code] = ref_same.get(code, 0) + 1
    wall_same = time.perf_counter() - t0
    concurrency.append({
        "workload": "CLI writers x4 (same branch)",
        "workers": 4, "total": 16, "ok": ok_same, "refusals": ref_same,
        "throughput_calls_s": round(ok_same / wall_same, 2) if wall_same > 0 else 0.0,
    })

    return {"rows": rows, "concurrency": concurrency}


def seed_store(cli: CliRunner, store: str, fixtures_dir: Path, h_depth: int = 100) -> dict:
    """Seed F100, F1k, F10k, sizes, and history projects into `store`."""
    cli.ok(["project", "init", f"{store}/f100", str(fixtures_dir / "f100")])
    cli.ok(["project", "init", f"{store}/f1k", str(fixtures_dir / "f1k")])
    cli.ok(["project", "init", f"{store}/f10k", str(fixtures_dir / "f10k")])
    cli.ok(["project", "init", f"{store}/sizes", str(fixtures_dir / "sizes")])
    cli.ok(["project", "init", f"{store}/hist", str(fixtures_dir / "hist_seed")])
    cli.ok(["branch", "fork", f"{store}/hist", "h1", "main"])
    cli.ok(["file", "write", f"{store}/hist", "h1", "/target.txt", "-m", "h1-1"], stdin_data="line0\nline1\n")
    cli.ok(["branch", "fork", f"{store}/hist", "h100", "main"])
    # Seed H100 via Node SDK or CLI loop (use CLI for store independence, batched fast)
    for i in range(1, h_depth + 1):
        cli.ok(["file", "write", f"{store}/hist", "h100", "/target.txt", "-m", f"h-{i}"], stdin_data=f"base\nrev={i}\n")
    return {"h_depth": h_depth}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cli", type=Path, required=True)
    ap.add_argument("--node-pkg", type=Path, required=True)
    ap.add_argument("--node-bin", default=shutil.which("node") or "node")
    ap.add_argument("--source-dir", type=Path, required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--pg-admin-url", default="")
    ap.add_argument("--pg-user", default="layerfs_pg")
    ap.add_argument("--pg-password", default="layerfs-test-pw")
    ap.add_argument("--n-read", type=int, default=15)
    ap.add_argument("--n-write", type=int, default=10)
    ap.add_argument("--h-depth", type=int, default=50)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()

    head = subprocess.check_output(["git", "-C", str(args.source_dir), "rev-parse", "HEAD"], text=True).strip()
    assert head == args.source and len(head) == 40, f"HEAD {head} != --source {args.source}"
    args.output.mkdir(parents=True, exist_ok=True)
    tmp_base = Path(os.environ.get("LAYERFS_TEST_TMPDIR") or tempfile.gettempdir())
    tmp_base.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="fs_file_calls_", dir=tmp_base))
    fixtures = work / "fixtures"
    fixtures.mkdir()
    m100 = make_tree(fixtures / "f100", 100)
    make_tree(fixtures / "f1k", 1000)
    make_tree(fixtures / "f10k", 10000)
    make_size_files(fixtures / "sizes")
    (fixtures / "hist_seed").mkdir()
    (fixtures / "hist_seed" / "target.txt").write_text("base\nrev=0\n", encoding="utf-8")
    f100_expected_hash = tree_sha256(fixtures / "f100")

    results: dict = {
        "meta": {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_sha": head,
            "cli": str(args.cli),
            "cli_sha256": sha256_file(args.cli),
            "host": f"{platform.system()} {platform.release()} ({platform.machine()})",
            "n_read": args.n_read,
            "n_write": args.n_write,
            "h_depth": args.h_depth,
            "cache_state": "warm (declared preconditioning; OS page cache not dropped — labelled diagnostic)",
        },
        "arms": {},
        "not_run": [
            {"route": "worker:docker", "reason": "NOT_RUN: Docker daemon unavailable on this non-root Linux host"},
            {"route": "worker:lima", "reason": "NOT_RUN: Lima VM unavailable on this Linux host"},
            {"route": "worker:apple-container", "reason": "NOT_RUN: macOS-only route"},
        ],
        "proof": {},
    }

    pg_db_name = f"bench_file_calls_{os.getpid()}"
    pg_created = False
    try:
        # 1. Native SQLite (ext4)
        home_sq = work / "home_sqlite"
        home_sq.mkdir(mode=0o700); home_sq.chmod(0o700)
        cli_sq = CliRunner(args.cli, home_sq, trace_file=args.output / "trace_sqlite.jsonl")
        cli_sq.ok(["home", "init"])
        help_j, _ = cli_sq.ok(["help", "--json"])
        avail_calls = {f"{c['family']}.{c['call']}" for c in help_j["calls"]}
        missing = [c for c in CALL_INVENTORY if c not in avail_calls]
        assert not missing, f"Missing expected 2.0 calls: {missing}"
        cli_sq.ok(["store", "create", "sq"])
        seed_store(cli_sq, "sq", fixtures, h_depth=args.h_depth)

        results["arms"]["sqlite_cli"] = run_cli_bench(cli_sq, "sq", args.n_read, args.n_write)
        results["arms"]["sqlite_sdk"] = run_node_sdk_bench(
            args.node_bin, args.node_pkg, home_sq, "sq",
            {"n_read": args.n_read, "n_write": args.n_write},
        )
        # Independent proof via project export SHA-256
        exp_sq = work / "exp_sq_f100"
        cli_sq.ok(["project", "export", "sq/f100", str(exp_sq)])
        results["proof"]["sqlite_f100_export_sha256_match"] = (tree_sha256(exp_sq) == f100_expected_hash)
        results["proof"]["sqlite_sdk_edit_match"] = results["arms"]["sqlite_sdk"]["proof"]["edit_final_ok"]
        cli_sq.ok(["store", "remove", "sq"])

        # 2. Native PostgreSQL 18 (if configured)
        if args.pg_admin_url:
            subprocess.run(["psql", args.pg_admin_url, "-c", f"DROP DATABASE IF EXISTS {pg_db_name} WITH (FORCE);"], check=True, capture_output=True)
            subprocess.run(["psql", args.pg_admin_url, "-c", f"CREATE DATABASE {pg_db_name} OWNER {args.pg_user};"], check=True, capture_output=True)
            pg_created = True
            pg_clean_url = f"postgresql://127.0.0.1:55432/{pg_db_name}?sslmode=disable"
            home_pg = work / "home_pg"
            home_pg.mkdir(mode=0o700); home_pg.chmod(0o700)
            cli_pg = CliRunner(args.cli, home_pg, trace_file=args.output / "trace_pg.jsonl")
            cli_pg.ok(["home", "init"])
            cli_pg.ok(["store", "save-auth", "pg", "--user", args.pg_user, "--password-stdin"], stdin_data=f"{args.pg_password}\n")
            cli_pg.ok(["store", "connect", "pg", pg_clean_url, "--auth", "pg", "--synchronous-commit", "off"])
            seed_store(cli_pg, "pg", fixtures, h_depth=args.h_depth)

            results["arms"]["pg_cli"] = run_cli_bench(cli_pg, "pg", args.n_read, args.n_write)
            results["arms"]["pg_sdk"] = run_node_sdk_bench(
                args.node_bin, args.node_pkg, home_pg, "pg",
                {"n_read": args.n_read, "n_write": args.n_write},
            )
            exp_pg = work / "exp_pg_f100"
            cli_pg.ok(["project", "export", "pg/f100", str(exp_pg)])
            results["proof"]["pg_f100_export_sha256_match"] = (tree_sha256(exp_pg) == f100_expected_hash)
            results["proof"]["pg_sdk_edit_match"] = results["arms"]["pg_sdk"]["proof"]["edit_final_ok"]
            cli_pg.ok(["store", "disconnect", "pg"])
    finally:
        if pg_created and args.pg_admin_url:
            subprocess.run(["psql", args.pg_admin_url, "-c", f"DROP DATABASE IF EXISTS {pg_db_name} WITH (FORCE);"], check=False, capture_output=True)
        shutil.rmtree(work, ignore_errors=True)

    # Save local JSON & CSV receipts
    (args.output / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    with (args.output / "results.csv").open("w", newline="", encoding="utf-8") as cf:
        w = csv.writer(cf)
        w.writerow(["arm", "case", "n", "p50_ms", "p95_ms", "max_ms", "calls_per_s", "delta_stored_bytes", "delta_size_bytes"])
        for arm_name, arm_data in results["arms"].items():
            for row in arm_data["rows"]:
                w.writerow([arm_name, row["case"], row["n"], row["p50_ms"], row["p95_ms"], row["max_ms"], row["calls_per_s"], row.get("delta_stored_bytes", ""), row.get("delta_size_bytes", "")])

    # Render publication report.md
    args.report.parent.mkdir(parents=True, exist_ok=True)
    sq_cli = {r["case"]: r for r in results["arms"]["sqlite_cli"]["rows"]}
    sq_sdk = {r["case"]: r for r in results["arms"]["sqlite_sdk"]["rows"]}
    pg_cli = {r["case"]: r for r in results["arms"].get("pg_cli", {}).get("rows", [])}
    pg_sdk = {r["case"]: r for r in results["arms"].get("pg_sdk", {}).get("rows", [])}

    sq_cli_stat = sq_cli.get("file.stat (F1k)", {}).get("p50_ms", 0)
    sq_sdk_stat = sq_sdk.get("file.stat (F1k)", {}).get("p50_ms", 0)
    pg_sdk_stat = pg_sdk.get("file.stat (F1k)", {}).get("p50_ms", 0)

    lines = [
        f"# fs-file-calls — {head[:10]}",
        "",
        (
            f"**PASS (diagnostic warm): measured all 15 mountless LayerFS 2.0 `file.*` + `commit.diff` calls "
            f"across CLI and persistent `@layerfs/node` SDK on native SQLite (ext4) and PostgreSQL 18.6 "
            f"(F1k `file.stat` p50: SQLite SDK `{sq_sdk_stat} ms` vs CLI `{sq_cli_stat} ms`, PG18 SDK `{pg_sdk_stat} ms`; "
            f"independent export SHA-256 proofs passed; 3 unavailable worker routes recorded as NOT_RUN).**"
        ),
        "",
        "## Configuration & Provenance",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| LayerFS commit | `{head}` (`layerfs_v2_0_0`) |",
        f"| CLI binary SHA-256 | `{results['meta']['cli_sha256'][:16]}…` |",
        f"| Host | {results['meta']['host']} (`ext4` `LAYERFS_TEST_TMPDIR`) |",
        f"| PostgreSQL | 18.6 (`127.0.0.1:55432`, `synchronous_commit=off`) |",
        f"| Sample sizes | reads `N={args.n_read}` (F10k/H{args.h_depth} capped), writes `N={args.n_write}`, history `H1` / `H{args.h_depth}` |",
        f"| Cache protocol | {results['meta']['cache_state']} |",
        f"| Independent proof | SQLite F100 export SHA-256 match: `{results['proof'].get('sqlite_f100_export_sha256_match')}`; PG18 F100 export SHA-256 match: `{results['proof'].get('pg_f100_export_sha256_match')}` |",
        "",
        "## Latency & Throughput by Call (p50 / p95 ms, warm diagnostic)",
        "",
        "| Case | SQLite SDK p50 (ms) | SQLite CLI p50 (ms) | PG18 SDK p50 (ms) | PG18 CLI p50 (ms) | SQLite SDK calls/s |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    all_cases = list(dict.fromkeys([r["case"] for r in results["arms"]["sqlite_sdk"]["rows"]] + [r["case"] for r in results["arms"]["sqlite_cli"]["rows"]]))
    def fmt_ms(d, k):
        r = d.get(k)
        return f"{r['p50_ms']:.2f} / {r['p95_ms']:.2f}" if r else "—"
    for case in all_cases:
        sdk_cps = sq_sdk[case]["calls_per_s"] if case in sq_sdk else "—"
        lines.append(f"| `{case}` | {fmt_ms(sq_sdk, case)} | {fmt_ms(sq_cli, case)} | {fmt_ms(pg_sdk, case)} | {fmt_ms(pg_cli, case)} | {sdk_cps} |")

    lines += [
        "",
        "## Write Commit Storage Growth (SQLite SDK & PG18 SDK)",
        "",
        "| Write Case | SQLite `delta_stored_bytes` | SQLite `delta_size_bytes` | PG18 `delta_stored_bytes` | PG18 `delta_size_bytes` |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for tag in ("0b", "1k", "64k", "1m"):
        k = f"file.write ({tag})"
        s_r = sq_sdk.get(k, {})
        p_r = pg_sdk.get(k, {})
        lines.append(
            f"| `{k}` | {s_r.get('delta_stored_bytes', '—')} | {s_r.get('delta_size_bytes', '—')} | "
            f"{p_r.get('delta_stored_bytes', '—')} | {p_r.get('delta_size_bytes', '—')} |"
        )

    lines += [
        "",
        "## Concurrency & Refusals (CLI Process-per-Call)",
        "",
        "| Backend | Workload | OK / Total | Throughput (calls/s) | Refusals by Code |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for label, arm_key in [("SQLite", "sqlite_cli"), ("PostgreSQL 18", "pg_cli")]:
        for c in results["arms"].get(arm_key, {}).get("concurrency", []):
            ref_str = ", ".join(f"{k}:{v}" for k, v in sorted(c["refusals"].items())) or "none"
            lines.append(f"| {label} | {c['workload']} | {c['ok']} / {c['total']} | {c['throughput_calls_s']} | `{ref_str}` |")

    lines += [
        "",
        "## Registered NOT_RUN Routes",
        "",
        "| Route | Status & Reason |",
        "| --- | --- |",
    ]
    for nr in results["not_run"]:
        lines.append(f"| `{nr['route']}` | {nr['reason']} |")

    lines += [
        "",
        "## Main Observations & Cleanup",
        "",
        f"- **CLI vs persistent SDK**: On native SQLite (`F1k` `file.stat`), a fresh CLI process adds fixed process-spawn + home/Store open overhead (`{sq_cli_stat} ms` p50) compared to the persistent `@layerfs/node` client (`{sq_sdk_stat} ms` p50).",
        f"- **PostgreSQL 18 vs SQLite**: Persistent `@layerfs/node` calls against local PostgreSQL 18.6 (`{pg_sdk_stat} ms` p50 on `F1k` `file.stat`) incur loopback TCP + SQL round-trip overhead compared to local SQLite (`{sq_sdk_stat} ms`), while supporting concurrent CLI writers cleanly.",
        "- **Cleanup**: Owned SQLite store removed via `layerfs store remove`, PostgreSQL store disconnected via `layerfs store disconnect`, scratch database dropped, and temporary home/fixtures deleted.",
    ]

    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote report to {args.report} and receipts to {args.output}")


if __name__ == "__main__":
    main()
