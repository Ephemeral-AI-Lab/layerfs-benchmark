"""Cold Store pages before a timed export, enforced and shown on owned resources only.

Guests (docker, lima, apple-container): `resident --evict` fdatasyncs each of the
Store's own files and drops their clean pages with posix_fadvise(DONTNEED), then
`resident` counts the pages still resident with mincore. Nothing shared is
purged: other files, other containers and the Docker Desktop VM keep their cache.
native (macOS): the home sits on an owned APFS disk image; detaching and
re-attaching it drops that volume's cached pages, then mincore counts the Store
files' resident pages. A row whose Store shows any resident page is INELIGIBLE.
"""

import ctypes
import glob
import mmap
import os
import subprocess
import time
from pathlib import Path

GUEST_TOOL = "/tmp/resident"
STORE_GLOB = "/layerfs/data/store/{store}/store.sqlite*"


def guest_prefix(env: dict, machine: str) -> list:
    return env["machines"][machine]["guest"]


def guest(env: dict, machine: str, script: str) -> str:
    out = subprocess.run(
        guest_prefix(env, machine) + ["sh", "-c", script],
        capture_output=True, text=True, timeout=30, check=True,
    )
    return out.stdout


def install_tool(env: dict, machine: str, tool: Path) -> None:
    """Copies the static tool into the guest's /tmp (owned, outside every Store)."""
    with open(tool, "rb") as data:
        subprocess.run(
            guest_prefix(env, machine) + ["sh", "-c", f"cat > {GUEST_TOOL} && chmod 755 {GUEST_TOOL}"],
            stdin=data, capture_output=True, timeout=30, check=True,
        )


def parse(lines: str) -> list:
    rows = []
    for line in lines.strip().splitlines():
        resident, total, path = line.split(" ", 2)
        rows.append({"path": path, "resident_pages": int(resident), "pages": int(total)})
    return rows


def evict_guest(env: dict, machine: str, store: str) -> dict:
    files = STORE_GLOB.format(store=store)
    script = f"{GUEST_TOOL} --evict {files} >/dev/null && {GUEST_TOOL} {files}"
    started = time.monotonic()
    rows = parse(guest(env, machine, script))
    return {
        "method": "posix_fadvise(DONTNEED) on the Store's own files, then mincore",
        "files": rows,
        "control_s": round(time.monotonic() - started, 3),
    }


def _mincore(path: str) -> dict:
    """Resident pages of `path` on macOS: libc mmap (read-only, shared) + mincore."""
    size = os.path.getsize(path)
    page = mmap.PAGESIZE
    pages = (size + page - 1) // page
    if pages == 0:
        return {"path": path, "resident_pages": 0, "pages": 0}
    libc = ctypes.CDLL(None, use_errno=True)
    libc.mmap.restype = ctypes.c_void_p
    libc.mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_long]
    libc.munmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    libc.mincore.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_char_p]
    fd = os.open(path, os.O_RDONLY)
    try:
        addr = libc.mmap(None, size, mmap.PROT_READ, mmap.MAP_SHARED, fd, 0)
        if addr in (None, ctypes.c_void_p(-1).value):
            raise OSError(ctypes.get_errno(), "mmap")
        try:
            vec = ctypes.create_string_buffer(pages)
            if libc.mincore(addr, size, vec) != 0:
                raise OSError(ctypes.get_errno(), "mincore")
            resident = sum(1 for b in vec.raw[:pages] if b & 1)
        finally:
            libc.munmap(addr, size)
    finally:
        os.close(fd)
    return {"path": path, "resident_pages": resident, "pages": pages}


def evict_native(env: dict, store: str) -> dict:
    image, mount = env["native"]["image"], env["native"]["mount"]
    started = time.monotonic()
    subprocess.run(["hdiutil", "detach", mount], capture_output=True, timeout=60, check=True)
    subprocess.run(
        ["hdiutil", "attach", "-nobrowse", "-mountpoint", mount, image],
        capture_output=True, timeout=60, check=True,
    )
    files = sorted(glob.glob(os.path.join(env["home"], "store", store, "store.sqlite*")))
    if not files:
        raise FileNotFoundError(f"no Store files for {store} under {env['home']}")
    return {
        "method": "detach and re-attach the owned APFS disk image holding the home, then mincore",
        "files": [_mincore(f) for f in files],
        "control_s": round(time.monotonic() - started, 3),
    }


def evict(env: dict, machine: str, store: str) -> dict:
    evidence = evict_native(env, store) if machine == "native" else evict_guest(env, machine, store)
    evidence["cold"] = bool(evidence["files"]) and all(f["resident_pages"] == 0 for f in evidence["files"])
    return evidence
