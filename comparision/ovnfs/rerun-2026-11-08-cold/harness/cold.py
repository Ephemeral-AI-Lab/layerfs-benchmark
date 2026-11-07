"""Cold boundaries for the cold-cache rerun (stdlib only).

Inside the Docker VM, `evict.py` (run from a throwaway read-only helper container on the system's
own volume) fsyncs every file under the given roots, drops their pages from the guest page cache
and reports resident bytes before and after (util-linux fincore). A boundary counts as cold only
when `resident_after` is 0. Not controlled: in-process caches of a system that keeps running (both
systems keep their daemon across a commit), the guest's inode/dentry caches (only a VM-wide
drop_caches clears them, which would touch other owners' containers), and the macOS cache under
the VM's disk image.
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
EVICT_IMAGE = "fsh-cmp-layerfs:b4fa173e"  # any local image with python3 and util-linux fincore


def evict_argv(volume, roots):
    return ["docker", "run", "--rm", "--network", "none", "--pull", "never", "-v", f"{volume}:/d:ro",
            "-v", f"{HERE}:/t:ro", "--entrypoint", "python3", EVICT_IMAGE, "/t/evict.py", *roots]


def layerfs_roots(home_id8, store, sandbox):
    """The Store's files and the Sandbox's written-data files; not the Sandbox image (programs)."""
    return [f"/d/store/{store}", f"/d/sandbox/{sandbox}",
            f"/d/machine/native/run/lfs-{home_id8}-{sandbox}/overlay"]


OVNFS_ROOTS = ["/d"]  # ovnfs's whole volume: its state and the source folder checkouts read through
