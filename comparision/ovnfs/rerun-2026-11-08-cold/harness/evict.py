"""evict.py ROOT [ROOT...]: fsync every regular file under ROOT, drop its pages from the page cache
(POSIX_FADV_DONTNEED), and print resident bytes before and after (util-linux fincore) as JSON.
Files ending -shm are mmapped by their owner: reported separately, never counted."""
import json, os, subprocess, sys


def files(roots):
    for root in roots:
        for d, _, names in os.walk(root):
            for n in names:
                p = os.path.join(d, n)
                if os.path.isfile(p) and not os.path.islink(p):
                    yield p


def resident(paths):
    out = {}
    for i in range(0, len(paths), 200):
        r = subprocess.run(["fincore", "--bytes", "--raw", "--noheadings", "-o", "RES,SIZE,FILE",
                            *paths[i:i + 200]], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            res, size, path = line.split(" ", 2)
            out[path] = (int(res), int(size))
    return out


paths = list(files(sys.argv[1:]))
before = resident(paths)
for p in paths:
    try:
        fd = os.open(p, os.O_RDONLY)
    except FileNotFoundError:
        continue
    try:
        os.fsync(fd)
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
    finally:
        os.close(fd)
after = resident(paths)
rec = {"files": 0, "bytes": 0, "resident_before": 0, "resident_after": 0, "shm_resident_after": 0, "left": []}
for p, (res, size) in after.items():
    if p.endswith("-shm"):
        rec["shm_resident_after"] += res
        continue
    rec["files"] += 1
    rec["bytes"] += size
    rec["resident_before"] += before.get(p, (0, 0))[0]
    rec["resident_after"] += res
    if res:
        rec["left"].append([p, res])
rec["left"] = sorted(rec["left"], key=lambda x: -x[1])[:5]
print(json.dumps(rec))
