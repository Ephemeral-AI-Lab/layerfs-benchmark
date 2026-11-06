#!/usr/bin/env python3
"""Offline references for fs-storage-history, computed from the in-memory oracle.

    python3 refs.py --base <extracted base> --output refs.json [--case H01 ...]

`shared/src/references.compute` needs one directory per state; here a case
has up to 501 states of 65 MB each, so the same references are computed from
the oracle `State` objects instead, per Store (H06: Σ over its 20 Stores):

* whole_file_unique: Σ distinct regular-file contents over every state
  (each project's base plus every Commit state).
* tar_zstd: Σ per-state deterministic PAX tar (sorted, mtime/uid 0, the
  shared `references.deterministic_tar` conventions) compressed with zstd
  level 3 (Python `compression.zstd`). One state per Init and per Commit.
* git_pack: one fresh bare repository per Store via `git fast-import`: per
  project a root Commit of the base, then one Commit per state on a Git
  branch per LayerFS Branch (forks start from their parent's head); then
  `git repack -a -d -f --window=10 --depth=50` with `pack.threads=1`.
* cdc_oracle (approximate): shared `references.cdc_boundaries` (gear, 8/16/32
  KiB, files ≥ 128 KiB chunked) over distinct contents, Σ min(raw, zstd-3).

Pinned by `input_sha256` (the case workload digests) in the output JSON.
"""

import argparse
import hashlib
import io
import json
import multiprocessing
import os
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
sys.path.insert(1, str(SRC.parents[1] / "shared" / "src"))

import base  # noqa: E402
import cases  # noqa: E402
import model  # noqa: E402
import references  # noqa: E402

TIMEOUT_S = 120


def zstd3(data):
    from compression import zstd  # Python 3.14+

    return len(zstd.compress(data, level=3))


def state_tar(entries):
    """Deterministic PAX tar of a state (files, links and their directories)."""
    buffer = io.BytesIO()
    dirs = set()
    for path in entries:
        dirs.update(model.ancestors(path))
    dirs.discard("")
    items = sorted([(d, None) for d in dirs] + [(p, entries[p]) for p in entries])
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for path, entry in items:
            info = tarfile.TarInfo(path)
            info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "", ""
            if entry is None:
                info.type, info.mode = tarfile.DIRTYPE, 0o755
                archive.addfile(info)
            elif entry.kind == "link":
                info.type, info.mode, info.linkname = tarfile.SYMTYPE, 0o777, entry.data.decode()
                archive.addfile(info)
            else:
                info.mode, info.size = entry.mode, len(entry.data)
                archive.addfile(info, io.BytesIO(entry.data))
    return buffer.getvalue()


def _tar_zstd_size(entries):
    return zstd3(state_tar(entries))


class Collector:
    """Visits every state of one Store and feeds the references."""

    def __init__(self, pool):
        self.pool = pool
        self.unique = {}  # sha256 -> bytes of regular-file contents
        self.contents = {}  # sha256 -> data (for CDC)
        self.logical = 0
        self.states = 0
        self.tar_jobs = []
        self.stream = io.BytesIO()  # git fast-import stream
        self.marks = {}  # sha256 -> mark
        self.next_mark = 1
        self.commit_time = 1767225600  # 2026-01-01T00:00:00Z
        self.heads = {}  # Git ref -> commit mark

    def visit(self, entries):
        self.states += 1
        for entry in entries.values():
            if entry.kind == "file":
                self.logical += len(entry.data)
                if entry.sha256 not in self.unique:
                    self.unique[entry.sha256] = len(entry.data)
                    self.contents[entry.sha256] = entry.data
        self.tar_jobs.append(self.pool.apply_async(_tar_zstd_size, (dict(entries),)))

    def blob(self, entry):
        key = hashlib.sha256(b"%d:" % (entry.kind == "link") + entry.data).hexdigest()
        if key not in self.marks:
            self.marks[key] = self.next_mark
            self.next_mark += 1
            self.stream.write(b"blob\nmark :%d\ndata %d\n" % (self.marks[key], len(entry.data)))
            self.stream.write(entry.data + b"\n")
        return self.marks[key]

    def git_commit(self, ref, parent_ref, entries, paths, message):
        changes = []
        for path in sorted(paths):
            entry = entries.get(path)
            if entry is None:
                changes.append(b"D %s\n" % path.encode())
            else:
                mode = b"120000" if entry.kind == "link" else (
                    b"100755" if entry.mode & 0o111 else b"100644")
                changes.append(b"M %s :%d %s\n" % (mode, self.blob(entry), path.encode()))
        self.commit_time += 1
        text = message.encode()
        mark = self.next_mark
        self.next_mark += 1
        self.stream.write(b"commit refs/heads/%s\nmark :%d\n" % (ref.encode(), mark))
        self.stream.write(b"committer fs-storage <fs-storage@invalid> %d +0000\n" % self.commit_time)
        self.stream.write(b"data %d\n%s\n" % (len(text), text))
        if parent_ref:
            self.stream.write(b"from :%d\n" % self.heads[parent_ref])
        self.heads[ref] = mark
        self.stream.write(b"".join(changes) + b"\n")


def store_references(store_plan, base_state, pool):
    c = Collector(pool)
    for project in store_plan["projects"]:
        name = project["name"]
        c.visit(base_state.entries)
        c.git_commit(f"{name}/main", None, base_state.entries, base_state.entries, f"{name} base")
        heads = {"main": base_state}
        for branch in project["branches"]:
            state = heads[branch["from"]].copy()
            parent = f"{name}/{branch['from']}"
            for step in range(1, branch["commits"] + 1):
                ops = model.plan_step(state, branch["seed"], step)
                touched = {op["path"] for op in ops} | {op["to"] for op in ops if "to" in op}
                c.visit(state.entries)
                c.git_commit(f"{name}/{branch['name']}", parent, state.entries, touched,
                             f"{name}/{branch['name']} {step}")
                parent = f"{name}/{branch['name']}"
            heads[branch["name"]] = state
    out = {"states": c.states, "logical_bytes": c.logical,
           "whole_file_unique": {"bytes": sum(c.unique.values()), "objects": len(c.unique)}}
    out["git_pack"] = git_pack(c.stream.getvalue())
    out["cdc_oracle"] = cdc_oracle(c.contents)
    sizes = [job.get(timeout=600) for job in c.tar_jobs]
    out["tar_zstd"] = {"bytes": sum(sizes), "states": len(sizes)}
    return out


def git_pack(stream):
    with tempfile.TemporaryDirectory() as scratch:
        repo = Path(scratch) / "repo.git"
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": scratch,
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_DIR": str(repo)}
        base_argv = ["git", "-c", "gc.auto=0", "-c", "pack.threads=1"]
        subprocess.run(base_argv + ["init", "-q", "--bare", str(repo)], env=env, check=True,
                       timeout=TIMEOUT_S, capture_output=True)
        subprocess.run(base_argv + ["fast-import", "--quiet"], input=stream, env=env,
                       check=True, timeout=TIMEOUT_S, capture_output=True)
        subprocess.run(base_argv + ["repack", "-a", "-d", "-f", "--window=10", "--depth=50", "-q"],
                       env=env, check=True, timeout=TIMEOUT_S, capture_output=True)
        pack_dir = repo / "objects" / "pack"
        packs = list(pack_dir.glob("*.pack"))
        idx = list(pack_dir.glob("*.idx"))
        commits = subprocess.run(base_argv + ["rev-list", "--all", "--count"], env=env,
                                 check=True, timeout=TIMEOUT_S, capture_output=True,
                                 text=True).stdout.strip()
        return {"status": "MEASURED", "bytes": sum(p.stat().st_size for p in packs + idx),
                "pack_bytes": sum(p.stat().st_size for p in packs),
                "idx_bytes": sum(p.stat().st_size for p in idx), "commits": int(commits),
                "version": subprocess.run(["git", "--version"], capture_output=True, text=True,
                                          timeout=10).stdout.strip()}


def cdc_oracle(contents):
    objects = {}
    for data in contents.values():
        pieces = [data]
        if len(data) >= references.CDC_CUTOFF:
            pieces, start = [], 0
            for end in references.cdc_boundaries(data):
                pieces.append(data[start:end])
                start = end
        for piece in pieces:
            key = hashlib.blake2b(piece, digest_size=32).digest()
            if key not in objects:
                objects[key] = (len(piece), min(len(piece), zstd3(piece)))
    return {"status": "APPROXIMATE",
            "label": "approximate CDC oracle: gear 8/16/32 KiB, cutoff 128 KiB; gear table "
                     "and masks differ from LayerFS",
            "bytes": sum(c for _, c in objects.values()),
            "unique_raw_bytes": sum(r for r, _ in objects.values()),
            "unique_objects": len(objects)}


def case_references(case_id, base_state, pool):
    started = time.monotonic()
    stores = [store_references(s, base_state, pool) for s in cases.shape(case_id)]
    total = {"states": sum(s["states"] for s in stores),
             "logical_bytes": sum(s["logical_bytes"] for s in stores)}
    for key in ("whole_file_unique", "git_pack", "cdc_oracle", "tar_zstd"):
        total[key] = {"bytes": sum(s[key]["bytes"] for s in stores)}
    plan = cases.build_plan(case_id, base_state)
    return {"case": case_id, "workload_sha256": plan["workload_sha256"], "stores": len(stores),
            "per_store": stores if len(stores) <= 1 else None,
            "per_store_bytes": [{k: s[k]["bytes"] for k in ("whole_file_unique", "git_pack",
                                                            "cdc_oracle", "tar_zstd")}
                                for s in stores],
            "total": total, "elapsed_s_ineligible": round(time.monotonic() - started, 1)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--case", action="append", choices=cases.CASE_IDS)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)
    state = base.load_tree(args.base)
    base.check_pins(state.summary())
    out = {"workload_version": cases.WORKLOAD_VERSION, "model": model.MODEL_VERSION,
           "base_manifest_sha256": cases.BASE_MANIFEST_SHA256,
           "tools": {"python": sys.version.split()[0], "zstd": "python compression.zstd level 3"},
           "cases": {}}
    ctx = multiprocessing.get_context("fork")
    with ctx.Pool(args.workers) as pool:
        for case_id in args.case or cases.CASE_IDS:
            out["cases"][case_id] = case_references(case_id, state, pool)
            print(json.dumps({case_id: out["cases"][case_id]["total"]}), flush=True)
    out["input_sha256"] = hashlib.sha256(json.dumps(
        {c: v["workload_sha256"] for c, v in out["cases"].items()}, sort_keys=True).encode()
    ).hexdigest()
    Path(args.output).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(hashlib.sha256(Path(args.output).read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
