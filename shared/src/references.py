#!/usr/bin/env python3
"""Offline, host-side storage references over a sequence of tree states.

No LayerFS involvement. Inputs are snapshot directories (one full tree per
state, in order) or a Git repository plus a Commit list exported to such
directories. Each reference is computed once per workload version and pinned
with hashes; storage rows do not rerun it.

References:

- ``whole_file_unique``: Σ size of distinct regular-file contents (SHA-256).
- ``tar_zstd``: Σ over states of ``tar | zstd -3`` (deterministic PAX tar,
  sorted, zero mtime/uid); compression without dedup.
- ``git_pack``: pack + idx bytes of a fresh bare repo with one Commit per
  state after ``git repack -a -d -f --window=10 --depth=50`` (pack.threads=1).
- ``cdc_oracle`` (APPROXIMATE): gear/FastCDC-style chunking 8/16/32 KiB for
  files ≥ 128 KiB, whole objects below; Σ over unique objects of
  min(raw, zstd -3). The gear table and masks differ from LayerFS's, so this is
  labelled approximate and never a gate.

Usage: ``python3 references.py <out.json> <snapshot_dir>...``
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

CDC_MIN, CDC_AVG, CDC_MAX = 8 * 1024, 16 * 1024, 32 * 1024
CDC_CUTOFF = 128 * 1024
TIMEOUT_S = 120  # every external command is bounded
_M64 = (1 << 64) - 1


def _gear_table():
    return [
        int.from_bytes(hashlib.sha256(b"fs-storage-gear-v1:%d" % i).digest()[:8], "little")
        for i in range(256)
    ]


GEAR = _gear_table()


def _spread_mask(bits):
    """A FastCDC-style mask with ``bits`` one-bits spread over the high word."""
    mask, position, step = 0, 63, max(1, 48 // bits)
    for _ in range(bits):
        mask |= 1 << position
        position -= step
    return mask


MASK_SMALL = _spread_mask(15)  # harder before the average size
MASK_LARGE = _spread_mask(13)  # easier after it


# --------------------------------------------------------------------------
# Tree walking and the canonical final-state manifest.


def walk(root):
    """Yield ``(relpath, kind, mode, size, sha256)`` sorted by path.

    ``kind`` is ``f`` (regular), ``d`` (directory) or ``l`` (symlink; size and
    hash are of the target text). The root itself is excluded.
    """
    root = Path(root)
    entries = []
    for directory, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(dirnames + filenames):
            path = Path(directory) / name
            rel = path.relative_to(root).as_posix()
            info = path.lstat()
            mode = stat.S_IMODE(info.st_mode)
            if stat.S_ISLNK(info.st_mode):
                target = os.readlink(path).encode()
                entries.append((rel, "l", mode, len(target), hashlib.sha256(target).hexdigest()))
            elif stat.S_ISDIR(info.st_mode):
                entries.append((rel, "d", mode, 0, "-"))
            elif stat.S_ISREG(info.st_mode):
                entries.append((rel, "f", mode, info.st_size, file_sha256(path)))
            else:
                raise ValueError(f"unsupported file type at {rel}")
    entries.sort()
    return entries


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def manifest_lines(entries):
    """Canonical text: ``<kind> <mode:04o> <size> <sha256|-> <path>`` per line."""
    return "".join(f"{k} {m:04o} {s} {h} {p}\n" for p, k, m, s, h in entries)


def manifest(root):
    entries = walk(root)
    text = manifest_lines(entries)
    return {
        "entries": len(entries),
        "files": sum(1 for e in entries if e[1] == "f"),
        "bytes": sum(e[3] for e in entries if e[1] == "f"),
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


# --------------------------------------------------------------------------
# References.


def whole_file_unique(snapshots):
    seen = {}
    logical = 0
    for snapshot in snapshots:
        for _, kind, _, size, digest in walk(snapshot):
            if kind == "f":
                logical += size
                seen[digest] = size
    return {"bytes": sum(seen.values()), "objects": len(seen), "logical_bytes": logical}


def deterministic_tar(root, stream):
    with tarfile.open(fileobj=stream, mode="w|", format=tarfile.PAX_FORMAT) as archive:
        for rel, kind, mode, size, _ in walk(root):
            info = tarfile.TarInfo(rel)
            info.mode, info.mtime, info.uid, info.gid = mode, 0, 0, 0
            info.uname = info.gname = ""
            path = Path(root) / rel
            if kind == "d":
                info.type = tarfile.DIRTYPE
                archive.addfile(info)
            elif kind == "l":
                info.type, info.linkname = tarfile.SYMTYPE, os.readlink(path)
                archive.addfile(info)
            else:
                info.size = size
                with open(path, "rb") as handle:
                    archive.addfile(info, handle)


def tar_zstd(snapshots, zstd="zstd"):
    if not shutil.which(zstd):
        return {"status": "UNAVAILABLE", "reason": "zstd CLI not found", "bytes": None}
    per_state = []
    for snapshot in snapshots:
        with tempfile.TemporaryFile() as tar_file:
            deterministic_tar(snapshot, tar_file)
            tar_file.seek(0)
            done = subprocess.run(
                [zstd, "-3", "-T1", "-q", "-c"],
                stdin=tar_file, capture_output=True, timeout=TIMEOUT_S, check=True,
            )
        per_state.append(len(done.stdout))
    return {"status": "MEASURED", "bytes": sum(per_state), "per_state": per_state}


def git_pack(snapshots, git="git"):
    if not shutil.which(git):
        return {"status": "UNAVAILABLE", "reason": "git CLI not found", "bytes": None}
    with tempfile.TemporaryDirectory() as scratch:
        repo = Path(scratch) / "repo.git"
        base_env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": scratch,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "fs-storage", "GIT_AUTHOR_EMAIL": "fs-storage@invalid",
            "GIT_COMMITTER_NAME": "fs-storage", "GIT_COMMITTER_EMAIL": "fs-storage@invalid",
            "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
        }

        def run(argv, **env):
            return subprocess.run(
                [git, "-c", "gc.auto=0", "-c", "pack.threads=1", "-c", "core.autocrlf=false", *argv],
                env={**base_env, **env}, capture_output=True, text=True,
                timeout=TIMEOUT_S, check=True,
            ).stdout.strip()

        run(["init", "-q", "--bare", str(repo)])
        index = Path(scratch) / "index"
        parent = None
        for number, snapshot in enumerate(snapshots):
            env = {"GIT_DIR": str(repo), "GIT_WORK_TREE": str(snapshot), "GIT_INDEX_FILE": str(index)}
            run(["add", "-A", "-f"], **env)
            tree = run(["write-tree"], **env)
            argv = ["commit-tree", tree, "-m", f"state {number}"]
            if parent:
                argv += ["-p", parent]
            parent = run(argv, **env)
        run(["update-ref", "refs/heads/main", parent], GIT_DIR=str(repo))
        run(["repack", "-a", "-d", "-f", "--window=10", "--depth=50", "-q"], GIT_DIR=str(repo))
        packs = list((repo / "objects" / "pack").glob("*.pack"))
        idx = list((repo / "objects" / "pack").glob("*.idx"))
        loose = [p for p in (repo / "objects").glob("??/*")]
        return {
            "status": "MEASURED",
            "bytes": sum(p.stat().st_size for p in packs + idx),
            "pack_bytes": sum(p.stat().st_size for p in packs),
            "idx_bytes": sum(p.stat().st_size for p in idx),
            "loose_objects": len(loose),
            "commits": len(snapshots),
            "version": subprocess.run([git, "--version"], capture_output=True, text=True, timeout=10).stdout.strip(),
        }


def cdc_boundaries(data):
    """Chunk end offsets of ``data`` (gear hash, normalized FastCDC masks)."""
    ends, start, length = [], 0, len(data)
    gear = GEAR
    while start < length:
        remaining = length - start
        if remaining <= CDC_MIN:
            ends.append(length)
            break
        stop = start + min(remaining, CDC_MAX)
        normal = start + min(remaining, CDC_AVG)
        h, i, cut = 0, start + CDC_MIN, stop
        while i < normal:
            h = ((h << 1) + gear[data[i]]) & _M64
            if not h & MASK_SMALL:
                cut = i + 1
                break
            i += 1
        else:
            while i < stop:
                h = ((h << 1) + gear[data[i]]) & _M64
                if not h & MASK_LARGE:
                    cut = i + 1
                    break
                i += 1
        ends.append(cut)
        start = cut
    return ends


def _zstd3():
    try:
        from compression import zstd  # Python 3.14+

        return lambda data: len(zstd.compress(data, level=3)), "python compression.zstd level 3"
    except ImportError:
        return None, "UNAVAILABLE: Python has no compression.zstd (3.14+)"


def cdc_oracle(snapshots):
    compress, method = _zstd3()
    objects = {}  # BLAKE2 digest -> (raw, compressed)
    files_seen = set()
    for snapshot in snapshots:
        for rel, kind, _, size, digest in walk(snapshot):
            if kind != "f" or digest in files_seen:
                continue
            files_seen.add(digest)
            data = (Path(snapshot) / rel).read_bytes()
            pieces = [data] if size < CDC_CUTOFF else []
            if size >= CDC_CUTOFF:
                start = 0
                for end in cdc_boundaries(data):
                    pieces.append(data[start:end])
                    start = end
            for piece in pieces:
                key = hashlib.blake2b(piece, digest_size=32).digest()
                if key not in objects:
                    packed = compress(piece) if compress else None
                    objects[key] = (len(piece), min(len(piece), packed) if packed is not None else None)
    raw = sum(r for r, _ in objects.values())
    packed = None if compress is None else sum(c for _, c in objects.values())
    return {
        "status": "APPROXIMATE" if compress else "PARTIAL",
        "label": "approximate CDC oracle: gear 8/16/32 KiB, cutoff 128 KiB; gear table and masks differ from LayerFS",
        "bytes": packed,
        "unique_raw_bytes": raw,
        "unique_objects": len(objects),
        "compression": method,
    }


def compute(snapshots, include=("whole_file_unique", "tar_zstd", "git_pack", "cdc_oracle")):
    """All references plus the input manifests that pin them."""
    snapshots = [Path(s) for s in snapshots]
    out = {
        "states": len(snapshots),
        "manifests": [manifest(s) for s in snapshots],
        "tools": {"python": sys.version.split()[0]},
    }
    if shutil.which("zstd"):
        out["tools"]["zstd"] = subprocess.run(
            ["zstd", "--version"], capture_output=True, text=True, timeout=10
        ).stdout.strip()
    functions = {
        "whole_file_unique": whole_file_unique,
        "tar_zstd": tar_zstd,
        "git_pack": git_pack,
        "cdc_oracle": cdc_oracle,
    }
    for name in include:
        out[name] = functions[name](snapshots)
    out["input_sha256"] = hashlib.sha256(
        json.dumps(out["manifests"], sort_keys=True).encode()
    ).hexdigest()
    return out


def reference_bytes(result):
    """name → bytes for the references that produced a number."""
    return {
        name: result[name]["bytes"]
        for name in ("whole_file_unique", "tar_zstd", "git_pack", "cdc_oracle")
        if isinstance(result.get(name), dict) and isinstance(result[name].get("bytes"), int)
    }


def pin(result, path):
    """Write ``result`` as JSON and return its SHA-256 (the pin)."""
    text = json.dumps(result, indent=1, sort_keys=True) + "\n"
    Path(path).write_text(text)
    return hashlib.sha256(text.encode()).hexdigest()


def export_git_states(repo, commits, destination, git="git"):
    """Extract each Commit's tree of a (bare) Git repo to ``destination/NNNN``."""
    destination = Path(destination)
    out = []
    for number, commit in enumerate(commits):
        target = destination / f"{number:04d}"
        target.mkdir(parents=True)
        archive = subprocess.run(
            [git, "--git-dir", str(repo), "archive", "--format=tar", commit],
            capture_output=True, timeout=TIMEOUT_S, check=True,
        ).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(target, filter="tar")
        out.append(target)
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    result = compute(argv[1:])
    print(pin(result, argv[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
