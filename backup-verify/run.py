"""backup-verify host driver: one case against one provider per invocation.

    python3 run.py --provider minio|r2 --case NAME --run-id ID \
        --env-file PRIVATE.env [--cli DIR] [--mib N] [--part-size 16M]

Each case runs the pinned LayerFS CLI inside a Linux container (the CLI's
Store calls are Linux only), applies host-side faults (kill or pause MinIO,
cut a container's network, kill the CLI) and inspects or damages bucket
objects with MinIO's `mc` client, which also speaks R2's S3 API. Receipts go
to receipts/<run-id>/<provider>/ (ignored). Every container command is bounded
by --timeout (default 110 s); nothing is retried.

The private env file holds the provider's keys and is never copied into
receipts:
  minio: LAYERFS_REMOTE_ENDPOINT (as the CLI container reaches it),
         LAYERFS_REMOTE_BUCKET, LAYERFS_REMOTE_ACCESS_KEY, LAYERFS_REMOTE_SECRET_KEY,
         MINIO_CONTAINER, MINIO_NETWORK
  r2:    LAYERFS_R2_ACCESS_KEY, LAYERFS_R2_SECRET_KEY, R2_ACCOUNT, R2_BUCKET
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD_IMAGE = "sha256:378b799ef43343fc64008b6a5ef456dd6bf0cb8f6ea4cec72e7b42dfc17d2cd6"
# Docker Desktop may inject an HTTP proxy into every container and override
# env-file values for it; a MinIO on a Docker network is reached directly, so
# MinIO containers clear the proxy with explicit -e flags.
NO_PROXY_FLAGS = ["-e", "HTTP_PROXY=", "-e", "http_proxy=", "-e", "HTTPS_PROXY=", "-e", "https_proxy="]
MINIO_IMAGE = "cgr.dev/chainguard/minio@sha256:4692462f35d97d7e82c30371d82f057703c5d9489bcae726010594c812f2d285"


def env_file(path):
    values = {}
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value
    return values


class Case:
    def __init__(self, args):
        self.args = args
        self.env = env_file(args.env_file)
        self.provider = args.provider
        self.out = os.path.join(HERE, "receipts", args.run_id, args.provider)
        os.makedirs(self.out, exist_ok=True)
        os.chmod(os.path.join(HERE, "receipts"), 0o700)
        self.volume = f"lfs-bv-{args.run_id}-{args.provider}"
        subprocess.run(["docker", "volume", "create", self.volume], check=True, capture_output=True)
        # isolated restores the roundtrip's backup into a fresh home
        self.tag = args.prefix or ("roundtrip" if args.case == "isolated" else args.case)
        self.prefix = f"bv-{args.run_id}/{self.tag}"
        if self.provider == "minio":
            self.network = self.env["MINIO_NETWORK"]
            self.proxy_flags = NO_PROXY_FLAGS
            self.url = f"{self.env['LAYERFS_REMOTE_ENDPOINT']}/{self.env['LAYERFS_REMOTE_BUCKET']}/{self.prefix}"
            self.key = "env:LAYERFS_REMOTE"
            self.bucket = self.env["LAYERFS_REMOTE_BUCKET"]
            # mc gets 503 from this MinIO by container name; its IP works
            mc_host = f"http://{self.env['LAYERFS_REMOTE_ACCESS_KEY']}:{self.env['LAYERFS_REMOTE_SECRET_KEY']}@{{ip}}:9000"
        else:
            self.network = "bridge"
            self.proxy_flags = []
            self.url = f"r2://{self.env['R2_ACCOUNT']}/{self.env['R2_BUCKET']}/{self.prefix}"
            self.key = "env:LAYERFS_R2"
            self.bucket = self.env["R2_BUCKET"]
            mc_host = (
                f"https://{self.env['LAYERFS_R2_ACCESS_KEY']}:{self.env['LAYERFS_R2_SECRET_KEY']}"
                f"@{self.env['R2_ACCOUNT']}.r2.cloudflarestorage.com"
            )
        # private files: the CLI's env (keys plus a wrong key for refusals) and mc's
        self.cli_env = os.path.join(self.out, ".cli.env")
        self.mc_env = os.path.join(self.out, ".mc.env")
        old = os.umask(0o077)
        with open(self.cli_env, "w") as f:
            for key, value in self.env.items():
                f.write(f"{key}={value}\n")
            good = "LAYERFS_REMOTE" if self.provider == "minio" else "LAYERFS_R2"
            f.write(f"LAYERFS_BAD_ACCESS_KEY={self.env[good + '_ACCESS_KEY']}\n")
            f.write("LAYERFS_BAD_SECRET_KEY=" + "0" * len(self.env[good + "_SECRET_KEY"]) + "\n")
        self.mc_host = mc_host
        os.umask(old)
        self.log = open(os.path.join(self.out, f"{args.case}.log"), "a")
        self.verdicts = []
        self.say(f"== case {args.case} provider {self.provider} prefix {self.prefix} at {time.strftime('%Y-%m-%dT%H:%M:%S%z')}")

    def say(self, text):
        text = self.redact(text)
        print(text, flush=True)
        self.log.write(text + "\n")
        self.log.flush()

    def redact(self, text):
        for key in ("LAYERFS_R2_ACCESS_KEY", "LAYERFS_R2_SECRET_KEY", "R2_ACCOUNT", "LAYERFS_REMOTE_ACCESS_KEY", "LAYERFS_REMOTE_SECRET_KEY"):
            value = self.env.get(key, "")
            if len(value) >= 8:
                text = text.replace(value, "<redacted>")
        return text

    def docker_cli(self, home, detach=False, network=None):
        return [
            "docker", "run", "--pull", "never", *([] if detach else ["--rm"]), *(["-d"] if detach else []),
            "--network", network or self.network,
            "--env-file", self.cli_env, *self.proxy_flags,
            "-e", f"LAYERFS_HOME=/scratch/{self.tag}/{home}",
            "-e", "LAYERFS_CONSTRUCTION_WORKERS=1",
            "--mount", f"type=volume,src={self.volume},dst=/scratch",
            "--mount", f"type=bind,src={self.args.cli},dst=/cli,readonly",
            "--mount", f"type=bind,src={HERE},dst=/bv,readonly",
            "--mount", f"type=bind,src={self.out},dst=/out",
            "--entrypoint", "timeout", BUILD_IMAGE, str(self.args.timeout), "python3", "/bv/cases.py",
        ]

    def inside(self, home, *step, stdin=None, expect_ok=True):
        """One cases.py step in a fresh container; returns (exit, output)."""
        proc = subprocess.run(self.docker_cli(home) + list(step), input=stdin, capture_output=True)
        output = proc.stdout.decode(errors="replace") + proc.stderr.decode(errors="replace")
        for line in output.splitlines():
            if not line.startswith("PROGRESS"):
                self.say("   " + line)
        if expect_ok and proc.returncode != 0:
            self.verdict(f"step {step[0]} {' '.join(step[1:])[:80]}", False, f"exit {proc.returncode}")
        return proc.returncode, output

    def start(self, home, *step, network=None):
        """A cases.py step in a detached container; returns its id."""
        return subprocess.run(self.docker_cli(home, detach=True, network=network) + list(step), check=True, capture_output=True, text=True).stdout.strip()

    def wait_for(self, container, pattern, seconds=100):
        """Waits (bounded) until the container's output matches `pattern`."""
        deadline = time.time() + seconds
        while time.time() < deadline:
            logs = subprocess.run(["docker", "logs", container], capture_output=True, text=True)
            if re.search(pattern, logs.stdout + logs.stderr):
                return True
            if subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", container], capture_output=True, text=True).stdout.strip() != "true":
                return False
            time.sleep(0.1)
        return False

    def finish(self, container):
        """Waits for a detached container (bounded by its timeout) and logs it."""
        code = subprocess.run(["docker", "wait", container], capture_output=True, text=True).stdout.strip()
        logs = subprocess.run(["docker", "logs", container], capture_output=True, text=True)
        subprocess.run(["docker", "rm", container], capture_output=True)
        output = logs.stdout + logs.stderr
        for line in output.splitlines():
            self.say("   " + line)
        return int(code or -1), output

    def mc(self, *args, script=None):
        """`mc` against the bucket; `script` runs a shell with mc instead."""
        host = self.mc_host
        if self.provider == "minio":
            ip = subprocess.run(["docker", "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", self.env["MINIO_CONTAINER"]], capture_output=True, text=True).stdout.strip()
            host = host.replace("{ip}", ip)
        old = os.umask(0o077)
        with open(self.mc_env, "w") as f:
            f.write(f"MC_HOST_t={host}\n")
        os.umask(old)
        base = ["docker", "run", "--rm", "--pull", "never", "--user", "0:0", "--network", self.network, "--env-file", self.mc_env, *self.proxy_flags,
                "--mount", f"type=volume,src={self.volume},dst=/scratch"]
        if script:
            command = base + ["--entrypoint", "sh", MINIO_IMAGE, "-c", script]
        else:
            command = base + ["--entrypoint", "mc", MINIO_IMAGE, *args]
        proc = subprocess.run(command, capture_output=True, text=True)
        return proc.returncode, proc.stdout + proc.stderr

    def sh(self, script):
        """A shell in the build image over the scratch volume (it has find)."""
        proc = subprocess.run(["docker", "run", "--rm", "--pull", "never", "--network", "none",
                               "--mount", f"type=volume,src={self.volume},dst=/scratch",
                               "--entrypoint", "sh", BUILD_IMAGE, "-c", script], capture_output=True, text=True)
        return proc.returncode, proc.stdout + proc.stderr

    def obj(self, file="shop"):
        return f"t/{self.bucket}/{self.prefix}/{file}/store.sqlite"

    def verdict(self, name, passed, detail=""):
        self.verdicts.append({"case": self.args.case, "check": name, "verdict": "PASS" if passed else "FAIL", "detail": self.redact(detail)})
        self.say(f"VERDICT {'PASS' if passed else 'FAIL'} {name} {self.redact(detail)}")

    def note(self, name, detail):
        self.verdicts.append({"case": self.args.case, "check": name, "verdict": "NOTE", "detail": self.redact(detail)})
        self.say(f"NOTE {name} {self.redact(detail)}")

    def close(self):
        with open(os.path.join(self.out, "verdicts.jsonl"), "a") as f:
            for v in self.verdicts:
                f.write(json.dumps(v) + "\n")
        for path in (self.cli_env, self.mc_env):
            if os.path.exists(path):
                os.remove(path)
        failed = [v for v in self.verdicts if v["verdict"] == "FAIL"]
        self.say(f"== case {self.args.case}: {len(self.verdicts) - len(failed)} ok, {len(failed)} failed")
        return 1 if failed else 0

    # shared steps

    def connect(self, home, name="b", key=None, expect=0, extra=()):
        """`backup connect`; returns the exit code (cases.py exits 1 when it
        differs from `expect`)."""
        size = () if "--part-size" in extra else ("--part-size", self.args.part_size)
        code, out = self.inside(home, "cli", "--label", f"connect {name}", "--expect", str(expect), "--",
                                "backup", "connect", name, self.url, "--key", key or self.key,
                                *size, *extra, expect_ok=False)
        return expect if code == 0 else 1

    def cli(self, home, label, *args, expect=0, stdin=None):
        code, out = self.inside(home, "cli", "--label", label, "--expect", str(expect), "--", *args, stdin=stdin, expect_ok=False)
        passed = ("expected=" in out and " PASS" in out.split("RESULT", 1)[-1].splitlines()[0]) if expect != "any" else True
        self.verdict(label, passed, refusal(out))
        return out

    def last(self, output, label):
        """The parsed stdout of the last receipt with `label`."""
        rows = [json.loads(l) for l in open(os.path.join(self.out, "receipts.jsonl")) if l.strip()]
        rows = [r for r in rows if r["label"] == label]
        if not rows:
            return None, None
        row = rows[-1]
        try:
            return row, json.loads(row["stdout"]) if row["stdout"].strip() else None
        except ValueError:
            return row, None


def refusal(output):
    match = re.search(r"refusal=([A-Za-z]+): (.*)", output)
    return f"{match.group(1)}: {match.group(2)[:200]}" if match else ""


def progress_ok(row):
    """Each byte phase's counts never go down; return (ok, last update)."""
    if not row:
        return False, None
    seen = {}
    for _, update in row["progress"]:
        done = update.get("done")
        if done is not None:
            if done < seen.get(update["phase"], 0):
                return False, update
            seen[update["phase"]] = done
    return True, row["progress"][-1][1] if row["progress"] else None


# cases ------------------------------------------------------------------


def c_roundtrip(c):
    """#2: fixture with history -> connect, list, create, restore, compare,
    write after restore, disconnect keeps objects, reconnect lists them."""
    h = "home-a"
    c.inside(h, "fixture", "--store", "shop", "--history")
    c.inside(h, "snapshot", "--store", "shop", "--trees", "--out", "/out/roundtrip-src.json")
    c.verdict("connect", c.connect(h) == 0)
    c.cli(h, "list before", "backup", "list", "b")
    c.cli(h, "create", "backup", "create", "shop", "b", "--progress")
    made_row, made = c.last(None, "create")
    c.cli(h, "list after create", "backup", "list", "b")
    c.cli(h, "restore as copy", "backup", "restore", "copy", "b", "shop", "--progress")
    row, restored = c.last(None, "restore as copy")
    if made and restored:
        c.verdict("restored sha256 equals uploaded", made["sha256"] == restored["sha256"], made["sha256"])
        c.verdict("restored heads equal uploaded", made["heads"] == restored["heads"], made["heads"])
        for label, r, phase in (("create", made_row, "upload"), ("restore", row, "download")):
            good, lastp = progress_ok(r)
            ends = [u for _, u in r["progress"] if u["phase"] == phase]
            c.verdict(f"{label} progress counts up and ends at bytes", good and bool(ends) and ends[-1]["done"] == ends[-1]["total"] == made["bytes"], json.dumps(ends[-1] if ends else None))
    c.inside(h, "snapshot", "--store", "copy", "--trees", "--out", "/out/roundtrip-copy.json")
    code, _ = c.inside(h, "compare", "/out/roundtrip-src.json", "/out/roundtrip-copy.json", expect_ok=False)
    c.verdict("projects, branches, commits (ids, roots) and trees equal", code == 0)
    code, _ = c.inside(h, "write-read", "--project", "copy/api", "--branch", "topic", expect_ok=False)
    c.verdict("new commit on the restored Store", code == 0)
    out = c.cli(h, "disconnect", "backup", "disconnect", "b")
    code, listing = c.mc("ls", "--recursive", f"t/{c.bucket}/{c.prefix}/")
    c.verdict("disconnect keeps the remote object", "shop/store.sqlite" in listing, listing.strip()[-200:])
    c.verdict("reconnect", c.connect(h) == 0)
    c.cli(h, "list after reconnect", "backup", "list", "b")
    _, listed = c.last(None, "list after reconnect")
    states = sorted((i.get("file"), i.get("store"), i.get("state")) for i in (listed or {}).get("items", []))
    c.verdict("reconnected list shows the copy, links gone", any(s[0] == "shop" for s in states) and all(s[2] != "current" for s in states), json.dumps(states))


def c_isolated(c):
    """#2/#6: restore into a fresh home from only the bucket, the key and the
    file name; compare with the source snapshot from `roundtrip`."""
    h = "home-isolated"
    c.verdict("connect from a fresh home", c.connect(h) == 0)
    c.cli(h, "list from fresh home", "backup", "list", "b")
    c.cli(h, "restore into fresh home", "backup", "restore", "shop", "b", "shop", "--progress")
    c.inside(h, "snapshot", "--store", "shop", "--trees", "--out", "/out/isolated.json")
    code, _ = c.inside(h, "compare", "/out/roundtrip-src.json", "/out/isolated.json", expect_ok=False)
    c.verdict("isolated restore equals the source", code == 0)
    code, _ = c.inside(h, "write-read", "--project", "shop/api", "--branch", "topic", expect_ok=False)
    c.verdict("new commit after isolated restore", code == 0)


def c_refusals(c):
    """#2: bad key, missing bucket and backup, foreign overwrite, changed
    Store, invalid part sizes; unrelated data intact."""
    h = "home-r"
    c.inside(h, "fixture", "--store", "other", "--history")
    c.inside(h, "snapshot", "--store", "other", "--out", "/out/refusals-before.json")
    c.cli(h, "connect with a wrong secret refused", "backup", "connect", "bad", c.url, "--key", "env:LAYERFS_BAD", expect=125)
    c.cli(h, "nothing recorded for the refused bucket", "backup", "list", "bad", expect=125)
    missing = c.url.replace(f"/{c.bucket}/", "/layerfs-no-such-bucket-zz/")
    c.cli(h, "connect to a missing bucket refused", "backup", "connect", "nobucket", missing, "--key", c.key, expect=125)
    for size in ("1M", "6G") + (("5G",) if c.provider == "r2" else ()):
        c.cli(h, f"connect --part-size {size} refused", "backup", "connect", f"p{size.lower()}", c.url, "--key", c.key, "--part-size", size, expect=125)
    # another home writes a copy named `foreign` first
    c.inside("home-f", "fixture", "--store", "f")
    c.verdict("connect from the other home", c.connect("home-f") == 0)
    c.cli("home-f", "other home creates foreign", "backup", "create", "f", "b", "foreign")
    c.verdict("connect", c.connect(h) == 0)
    c.cli(h, "restore of a missing backup refused", "backup", "restore", "ghost", "b", "no-such-file", expect=125)
    c.cli(h, "no Store made by the refused restore", "store", "get", "ghost", expect=125)
    c.cli(h, "create over another home's copy refused", "backup", "create", "other", "b", "foreign", expect=125)
    c.cli(h, "restore of another home's copy as a new Store is allowed", "backup", "restore", "fcopy", "b", "foreign")
    c.cli(h, "create own copy", "backup", "create", "other", "b", "other-copy")
    c.cli(h, "change the Store", "file", "write", "other/api", "topic", "/changed.txt", stdin=b"changed\n")
    c.cli(h, "restore over a changed Store refused", "backup", "restore", "other", "b", "other-copy", expect=125)
    c.inside(h, "snapshot", "--store", "other", "--out", "/out/refusals-after.json")
    before = json.load(open(os.path.join(c.out, "refusals-before.json")))
    after = json.load(open(os.path.join(c.out, "refusals-after.json")))
    topic_before = before["projects"]["api"]["branches"]["topic"]["commits"]
    topic_after = after["projects"]["api"]["branches"]["topic"]["commits"]
    c.verdict("refusals left the Store's history intact (only the one new commit)", topic_after[1:] == topic_before and len(topic_after) == len(topic_before) + 1)


def c_size(c):
    """#4: one fixture of --mib MiB of incompressible data -> create and
    restore; records time, peak RSS and peak scratch use."""
    h = f"home-s{c.args.mib}"
    store = f"s{c.args.mib}"
    c.inside(h, "fixture", "--store", store, "--mib", str(c.args.mib))
    c.verdict("connect", c.connect(h) == 0)
    c.cli(h, f"create {c.args.mib} MiB", "backup", "create", store, "b", "--progress")
    made_row, made = c.last(None, f"create {c.args.mib} MiB")
    c.cli(h, f"restore {c.args.mib} MiB", "backup", "restore", f"{store}-copy", "b", store, "--progress")
    row, restored = c.last(None, f"restore {c.args.mib} MiB")
    if made and restored:
        c.verdict("sha256 round trip", made["sha256"] == restored["sha256"], f"{made['bytes']} bytes")
        c.note("sizes", json.dumps({"store_bytes": made["bytes"], "create_s": made_row["seconds"], "create_rss_kib": made_row["peak_rss_kib"], "create_scratch_peak": made_row["scratch_used_peak"], "restore_s": row["seconds"], "restore_rss_kib": row["peak_rss_kib"], "restore_scratch_peak": row["scratch_used_peak"], "part_size": c.args.part_size}))
        good, _ = progress_ok(made_row)
        c.verdict("upload progress ends at bytes", good and made_row["progress"][-1][1].get("done") == made["bytes"])
    code, stat = c.mc("stat", "--json", c.obj(store))
    try:
        info = json.loads(stat)
        c.note("object", json.dumps({"size": info.get("size"), "etag": info.get("etag")}))
    except ValueError:
        c.note("object", stat.strip()[:200])
    code, inc = incomplete(c)
    c.verdict("no incomplete multipart uploads after success", not inc.strip(), inc.strip()[:200])


def metadata(c, file):
    code, out = c.mc("stat", "--json", c.obj(file))
    info = json.loads(out)
    meta = info.get("metadata") or {}
    return info, {k: v for k, v in meta.items() if k.lower().startswith("x-amz-meta-")}


def incomplete(c, files=("shop",)):
    """Incomplete multipart uploads under the case's prefix: listed by prefix
    and by each object key, since MinIO lists them by exact key only."""
    lines, code = [], 0
    for path in [f"t/{c.bucket}/{c.prefix}/", *(c.obj(f) for f in files)]:
        rc, out = c.mc("ls", "--incomplete", "--recursive", path)
        code = code or rc
        lines += [l for l in out.splitlines() if l.strip() and l not in lines]
    return code, "\n".join(lines)


def put(c, file, script_body, meta):
    """Replaces the object with bytes a shell script writes to /scratch/obj,
    carrying `meta` as its metadata."""
    attrs = ";".join(f"{k}={v}" for k, v in meta.items())
    code, out = c.mc(script=f"set -e; {script_body}; mc cp --quiet --attr '{attrs}' /scratch/obj {c.obj(file)} >/dev/null")
    return code, out


def c_corrupt(c):
    """#6 (and #5's failure after full transfer): damage the remote copy in
    ways each check must catch; a restore over the existing Store must refuse
    and leave it as it was, with no staging left."""
    h = "home-c"
    c.inside(h, "fixture", "--store", "shop", "--history", "--mib", "2")
    c.verdict("connect", c.connect(h) == 0)
    c.cli(h, "create good backup", "backup", "create", "shop", "b")
    c.inside(h, "snapshot", "--store", "shop", "--out", "/out/corrupt-before.json")
    info, meta = metadata(c, "shop")
    size = int(info["size"])
    pristine = f"t/{c.bucket}/{c.prefix}/pristine.sqlite"
    c.mc("cp", "--quiet", c.obj("shop"), pristine)
    sha_key = next(k for k in meta if k.lower().endswith("layerfs-sha256"))
    cases = [
        ("truncated object", f"mc cat {pristine} | head -c {size // 2} > /scratch/obj", meta),
        ("one byte changed", f"mc cat {pristine} > /scratch/obj; printf 'X' | dd of=/scratch/obj bs=1 seek={size // 3} conv=notrunc 2>/dev/null", meta),
        ("sha256 metadata altered", f"mc cat {pristine} > /scratch/obj", {**meta, sha_key: "0" * 64}),
        ("not a Store, valid sha256 (fails at verify)", "head -c 65536 /dev/urandom > /scratch/obj", None),
        ("forged manifest", "printf 'layerfs-pieces 1\\nbytes 10\\nsha256 bad\\n' > /scratch/obj", {**meta, next(k for k in meta if k.lower().endswith('layerfs-layout')): "pieces"}),
        ("manifest naming a missing piece", None, None),
        ("object removed", None, None),
    ]
    for name, script_body, use_meta in cases:
        if name == "object removed":
            c.mc("rm", "--quiet", c.obj("shop"))
        elif name == "manifest naming a missing piece":
            digest = "a" * 64
            text = f"layerfs-pieces 1\\nbytes 10\\nsha256 {digest}\\npiece-size 10\\npiece 10 {digest}\\n"
            layout = next(k for k in meta if k.lower().endswith("layerfs-layout"))
            code, out = put(c, "shop", f"printf '{text}' > /scratch/obj", {**meta, layout: "pieces", sha_key: digest})
            c.verdict(f"damage applied: {name}", code == 0, c.redact(out)[-200:])
        elif use_meta is None:
            # random bytes with their own true sha256 and size
            code, out = c.mc(script=f"set -e; {script_body}; sha256sum /scratch/obj | cut -d' ' -f1; stat -c %s /scratch/obj")
            digest, nbytes = out.split()[-2:]
            bytes_key = next(k for k in meta if k.lower().endswith("layerfs-bytes"))
            code, out = put(c, "shop", "true", {**meta, sha_key: digest, bytes_key: nbytes})
            c.verdict(f"damage applied: {name}", code == 0, c.redact(out)[-200:])
        else:
            code, out = put(c, "shop", script_body, use_meta)
            c.verdict(f"damage applied: {name}", code == 0, c.redact(out)[-200:])
        label = f"restore refuses: {name}"
        c.cli(h, label, "backup", "restore", "shop", "b", "shop", "--progress", expect=125)
        row, _ = c.last(None, label)
        phases = [u["phase"] for _, u in row["progress"]] if row else []
        c.note(f"{name}: phases", json.dumps(phases))
        if "verify" in name:
            downloads = [u for _, u in row["progress"] if u["phase"] == "download"]
            c.verdict("bytes fully moved, then verify refused, no success", bool(downloads) and downloads[-1]["done"] == downloads[-1]["total"] and phases[-1] == "verify" and row["exit"] == 125, json.dumps(phases))
        code, out = c.inside(h, "snapshot", "--store", "shop", "--out", "/out/corrupt-after.json", expect_ok=False)
        code2, _ = c.inside(h, "compare", "/out/corrupt-before.json", "/out/corrupt-after.json", expect_ok=False)
        c.verdict(f"destination Store intact after: {name}", code == 0 and code2 == 0)
        code, out = c.mc(script=f"n=0; for f in /scratch/{c.tag}/home-c/store/.restore-*; do [ -e $f ] && n=$((n+1)); done; echo $n")
        c.verdict(f"no staging left after: {name}", out.strip() == "0", out.strip())
        c.mc("cp", "--quiet", pristine, c.obj("shop"))
    c.cli(h, "restore of the pristine copy works", "backup", "restore", "shop", "b", "shop")


def c_kill(c):
    """#6: kill the CLI (SIGKILL) mid-upload of a replacement and mid-download;
    the previous copy stays restorable, leftovers are recorded, the next call
    works."""
    h = "home-k"
    c.inside(h, "fixture", "--store", "shop", "--history", "--mib", str(c.args.mib or 48))
    c.verdict("connect", c.connect(h) == 0)
    c.cli(h, "create good backup", "backup", "create", "shop", "b")
    _, good = c.last(None, "create good backup")
    c.cli(h, "change the Store", "file", "write", "shop/api", "topic", "/next.txt", stdin=b"next\n")
    phase = c.args.phase or "upload"
    cid = c.start(h, "cli", "--label", "create killed", "--expect", "any", "--", "backup", "create", "shop", "b", "--progress")
    hit = c.wait_for(cid, rf'PROGRESS create killed [0-9.]+ {{"phase": "{phase}", "done": [1-9]')
    subprocess.run(["docker", "kill", cid], capture_output=True)
    code, _ = c.finish(cid)
    c.verdict(f"CLI killed during {phase}", hit, f"container exit {code}")
    code, out = c.sh(f"find /scratch/{c.tag}/home-k -name '*.backup' -o -name 'backup.staging' -o -name '.restore-*' | sed 's|/scratch/{c.tag}/||'")
    c.note("local leftovers after killed create", out.strip() or "none")
    code, inc = incomplete(c)
    c.note("incomplete multipart uploads after killed create", f"mc exit {code}: " + (inc.strip()[:300] or "none"))
    c.cli(h, "restore after killed create", "backup", "restore", "check", "b", "shop")
    _, restored = c.last(None, "restore after killed create")
    c.verdict("previous copy still restorable and unchanged", bool(good and restored) and good["sha256"] == restored["sha256"])
    c.cli(h, "next create works", "backup", "create", "shop", "b")
    cid = c.start(h, "cli", "--label", "restore killed", "--expect", "any", "--", "backup", "restore", "dl", "b", "shop", "--progress")
    hit = c.wait_for(cid, r'PROGRESS restore killed [0-9.]+ {"phase": "download", "done": [1-9]')
    subprocess.run(["docker", "kill", cid], capture_output=True)
    c.finish(cid)
    c.verdict("CLI killed during download", hit)
    c.cli(h, "no Store from the killed restore", "store", "get", "dl", expect=125)
    code, out = c.sh(f"find /scratch/{c.tag}/home-k/store -maxdepth 1 -name '.restore-*' | sed 's|/scratch/{c.tag}/||'")
    c.note("staging left by the killed restore", out.strip() or "none")
    c.cli(h, "restore after killed restore works", "backup", "restore", "dl", "b", "shop")
    code, out = c.sh(f"find /scratch/{c.tag}/home-k/store -maxdepth 1 -name '.restore-*' | wc -l")
    c.verdict("the next restore removed the killed restore's staging", out.strip() == "0", out.strip())


def c_cut(c):
    """#5/#6: lose the connection mid-upload and mid-download (MinIO: kill
    the server; R2: disconnect the CLI container's network). Records the
    error, the partial count, the time to fail and the previous copy."""
    h = "home-x"
    direction = c.args.phase or "upload"
    c.inside(h, "fixture", "--store", "shop", "--history", "--mib", str(c.args.mib or 48))
    c.verdict("connect", c.connect(h) == 0)
    c.cli(h, "create good backup", "backup", "create", "shop", "b")
    _, good = c.last(None, "create good backup")
    if direction == "upload":
        c.cli(h, "change the Store", "file", "write", "shop/api", "topic", "/next.txt", stdin=b"next\n")
        argv = ["backup", "create", "shop", "b", "--progress"]
        phase = "upload"
    else:
        argv = ["backup", "restore", "dl", "b", "shop", "--progress"]
        phase = "download"
    label = f"{direction} cut"
    cid = c.start(h, "cli", "--label", label, "--expect", "any", "--", *argv)
    hit = c.wait_for(cid, rf'PROGRESS {label} [0-9.]+ {{"phase": "{phase}", "done": [1-9]')
    cut = time.time()
    if c.provider == "minio":
        subprocess.run(["docker", "kill", c.env["MINIO_CONTAINER"]], capture_output=True)
    else:
        subprocess.run(["docker", "network", "disconnect", "bridge", cid], capture_output=True)
    code, out = c.finish(cid)
    took = time.time() - cut
    if c.provider == "minio":
        subprocess.run(["docker", "start", c.env["MINIO_CONTAINER"]], capture_output=True)
        time.sleep(3)
    row, _ = c.last(None, label)
    ended = row is not None
    ups = [u for _, u in (row or {}).get("progress", []) if u["phase"] == phase]
    c.verdict(f"connection lost during {phase}", hit)
    c.verdict("the CLI ended with a refusal, not success", ended and row["exit"] == 125, refusal(out) or f"no receipt (killed by timeout after {took:.0f} s)")
    if ups:
        c.verdict("partial count, not 100%", ups[-1]["done"] < ups[-1]["total"], json.dumps(ups[-1]))
    c.note("seconds from cut to end", f"{took:.1f}")
    if direction == "download":
        c.cli(h, "no Store from the failed restore", "store", "get", "dl", expect=125)
        code, out = c.sh(f"find /scratch/{c.tag}/home-x/store -maxdepth 1 -name '.restore-*' | wc -l")
        c.verdict("staging removed after the failed restore", out.strip() == "0", out.strip())
    c.cli(h, "restore of the previous copy", "backup", "restore", "check", "b", "shop")
    _, restored = c.last(None, "restore of the previous copy")
    c.verdict("previous copy intact", bool(good and restored) and good["sha256"] == restored["sha256"])
    code, inc = incomplete(c)
    c.note("incomplete multipart uploads left", inc.strip()[:300] or "none")


def c_race(c):
    """#5/#6: a Store of the restore's name appears during its download: the
    restore refuses at install, after all bytes moved, and never reports success."""
    h = "home-race"
    c.inside(h, "fixture", "--store", "shop", "--mib", str(c.args.mib or 96))
    c.verdict("connect", c.connect(h) == 0)
    c.cli(h, "create", "backup", "create", "shop", "b")
    code, out = c.inside(h, "race-install", "--store", "raced", "--restore", json.dumps(["backup", "restore", "raced", "b", "shop", "--progress"]), expect_ok=False)
    c.verdict("restore refused at install after the download", "RACE PASS" in out, refusal(out))
    c.cli(h, "the racing Store is the new empty one", "store", "get", "raced")


def c_consistency(c):
    """#6: Commits land while the backup snapshots: the restored branch is one
    frontier (its /counter equals its Commit count at every sampled Commit)."""
    h = "home-cons"
    c.inside(h, "fixture", "--store", "shop", "--mib", str(c.args.mib or 64))
    c.cli(h, "fork work", "branch", "fork", "shop/api", "work", "main")
    c.verdict("connect", c.connect(h) == 0)
    code, out = c.inside(h, "churn-backup", "--project", "shop/api", "--branch", "work", "--seconds", "8", "--delay", "1", "--", "backup", "create", "shop", "b", "--progress", expect_ok=False)
    c.verdict("create during churn succeeded", code == 0, out.strip().splitlines()[-1][:200] if out.strip() else "")
    c.cli(h, "restore the churned backup", "backup", "restore", "copy", "b", "shop")
    code, out = c.inside(h, "counter-check", "--project", "copy/api", "--branch", "work", expect_ok=False)
    c.verdict("restored branch is one consistent frontier", code == 0, out.strip().splitlines()[-1] if out.strip() else "")
    code, out = c.inside(h, "counter-check", "--project", "shop/api", "--branch", "work", expect_ok=False)
    c.verdict("source branch consistent too", code == 0)


def c_concurrent(c):
    """#6: two creates of the same file at once, and a restore racing a
    replacement: outcomes recorded, no mixed bytes, the copy restorable."""
    h = "home-cc"
    c.inside(h, "fixture", "--store", "shop", "--mib", str(c.args.mib or 32))
    c.verdict("connect", c.connect(h) == 0)
    create = json.dumps(["backup", "create", "shop", "b"])
    code, out = c.inside(h, "parallel", "--a", create, "--b", create, expect_ok=False)
    codes = json.loads(re.search(r"PARALLEL (\{.*\})", out).group(1))
    c.note("two creates at once: exits", json.dumps(codes))
    why = refusal(out)
    c.verdict("one create succeeded; another, if refused, is Busy (no shared staging)", sorted(codes.values()) == [0, 0] or (sorted(codes.values()) == [0, 125] and why.startswith("Busy")), why)
    c.cli(h, "restore after concurrent creates", "backup", "restore", "copy1", "b", "shop")
    c.cli(h, "fork", "branch", "fork", "shop/api", "dev", "main")
    c.cli(h, "change it", "file", "write", "shop/api", "dev", "/x.txt", stdin=b"x\n")
    replace = json.dumps(["backup", "create", "shop", "b"])
    restore = json.dumps(["backup", "restore", "copy2", "b", "shop"])
    code, out = c.inside(h, "parallel", "--a", replace, "--b", restore, expect_ok=False)
    codes = json.loads(re.search(r"PARALLEL (\{.*\})", out).group(1))
    c.note("replacement racing a restore: exits", json.dumps(codes))
    results = dict(re.findall(r"PARALLEL-RESULT (\w) (\{.*\})", out))
    rows = {k: json.loads(v) for k, v in results.items()}
    if codes.get("b") == 0 and "b" in rows:
        known = [r.get("sha256") for r in rows.values()]
        c.verdict("restore got one whole copy (sha256 verified on download)", rows["b"].get("sha256") is not None, rows["b"].get("sha256", ""))
    else:
        c.verdict("restore refused cleanly while the copy was replaced", codes.get("b") == 125, refusal(out))
    c.cli(h, "final copy restorable", "backup", "restore", "copy3", "b", "shop")


def c_cleanup(c):
    """#6: inventory leftovers under this run's prefix (objects, piece
    objects, incomplete multipart uploads) and in the homes; on MinIO, abort
    the incomplete uploads and check they are gone. R2 is inventoried only."""
    root = f"t/{c.bucket}/bv-{c.args.run_id}/"
    code, objects = c.mc("ls", "--recursive", root)
    pieces = [l for l in objects.splitlines() if ".piece-" in l]
    c.note("objects under the run prefix", str(len([l for l in objects.splitlines() if l.strip()])))
    c.note("piece objects", str(len(pieces)))
    # MinIO lists incomplete uploads by exact key only: ask for each object
    keys = sorted({l.split()[-1] for l in objects.splitlines() if l.strip()})
    inc = []
    for path in [root, *(root + k for k in keys)]:
        code, out = c.mc("ls", "--incomplete", "--recursive", path)
        inc += [l for l in out.splitlines() if l.strip() and l not in inc]
    inc = "\n".join(inc)
    c.note("incomplete multipart uploads", inc.strip()[:600] or "none")
    code, out = c.sh("find /scratch -maxdepth 6 \\( -name '*.backup' -o -name 'backup.staging' -o -name '.restore-*' -o -name '*.layerfs-manifest' \\) | sed 's|/scratch/||'")
    c.note("local staging leftovers in this run's homes", out.strip() or "none")
    if c.provider == "minio" and inc.strip():
        for k in ["", *keys]:
            c.mc("rm", "--incomplete", "--recursive", "--force", root + k)
        again = "\n".join(l for k in ["", *keys] for l in c.mc("ls", "--incomplete", "--recursive", root + k)[1].splitlines() if l.strip())
        c.verdict("incomplete uploads aborted with the provider's tool", not again.strip(), again.strip()[:200])
        code, objects2 = c.mc("ls", "--recursive", root)
        c.verdict("complete objects untouched by that cleanup", objects2.count("\n") == objects.count("\n"))


def bucket_bytes(c, path=""):
    """Bytes stored under `path` of the bucket (the whole bucket by default)."""
    code, out = c.mc("du", "--json", f"t/{c.bucket}/{path}")
    if code != 0:
        raise RuntimeError(f"mc du failed: {c.redact(out)[:200]}")
    return sum(json.loads(line).get("size", 0) for line in out.splitlines() if line.startswith("{"))


def c_usage(c):
    """Storage held in the bucket: the whole bucket and this run's prefixes."""
    c.note("bucket bytes", str(bucket_bytes(c)))
    c.note(f"bv-{c.args.run_id} bytes", str(bucket_bytes(c, f"bv-{c.args.run_id}/")))
    code, inc = c.mc("ls", "--incomplete", "--recursive", f"t/{c.bucket}/")
    c.note("incomplete uploads", str(len([l for l in inc.splitlines() if l.strip()])))


# R2 runs on the owner's account: stay far inside the free tier (10 GB-month)
R2_BUDGET = 5 * 10**9


def r2_guard(c):
    """Refuses an R2 case whose worst case would take the bucket past
    R2_BUDGET: two copies of the largest Store (a replacement and its
    predecessor) plus 64 MiB for fixtures."""
    used = bucket_bytes(c)
    worst = 2 * max(c.args.mib, 96) * 2**20 + 64 * 2**20  # 96: largest case default
    c.note("r2 budget", json.dumps({"bucket_bytes": used, "case_worst": worst, "budget": R2_BUDGET}))
    if used + worst > R2_BUDGET:
        raise SystemExit(f"refused: {used} + {worst} bytes would pass the R2 budget {R2_BUDGET}")


PERMS = {
    "read": ["s3:ListBucket", "s3:GetObject"],
    "write": ["s3:ListBucket", "s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"],
    "full": ["s3:ListBucket", "s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts", "s3:DeleteObject"],
}


def c_perms(c):
    """#3 (MinIO only): which bucket permissions each CLI call needs, and a
    revoked key failing clearly without showing the secret. Users with
    scoped policies are made with `mc admin` and removed afterwards."""
    if c.provider != "minio":
        c.note("perms", "NOT_RUN on R2: scoped R2 tokens need the Cloudflare account API")
        return
    run = c.args.run_id.replace("-", "")
    users = {}
    for name, actions in PERMS.items():
        user, secret = f"bv{run}{name}", f"bv-{run}-{name}-" + os.urandom(8).hex()
        policy = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": actions, "Resource": [f"arn:aws:s3:::{c.bucket}", f"arn:aws:s3:::{c.bucket}/*"]}]}
        script = (f"set -e; printf '%s' '{json.dumps(policy)}' > /tmp/p.json; mc admin user add t {user} {secret} >/dev/null; "
                  f"mc admin policy create t {user} /tmp/p.json >/dev/null; mc admin policy attach t {user} --user {user} >/dev/null")
        code, out = c.mc(script=script)
        c.verdict(f"user with {name} policy made", code == 0, c.redact(out)[-200:].replace(secret, "<redacted>"))
        users[name] = (user, secret)
        tag = name.upper()
        with open(c.cli_env, "a") as f:
            f.write(f"LAYERFS_{tag}_ACCESS_KEY={user}\nLAYERFS_{tag}_SECRET_KEY={secret}\n")
    h = "home-perms"
    c.inside(h, "fixture", "--store", "shop", "--mib", "8")
    c.verdict("connect with the full key", c.connect(h, name="b") == 0)
    c.cli(h, "seed backup", "backup", "create", "shop", "b")
    table = {}
    for name in PERMS:
        bucket = f"b{name}"
        tag = name.upper()
        got = {}
        for op, argv in [("connect", ["backup", "connect", bucket, c.url, "--key", f"env:LAYERFS_{tag}", "--part-size", c.args.part_size]),
                         ("list", ["backup", "list", bucket]),
                         ("restore", ["backup", "restore", f"r{name}", bucket, "shop"]),
                         ("create", ["backup", "create", "shop", bucket, f"p{name}"]),
                         ("replace", ["backup", "create", "shop", bucket, f"p{name}"])]:
            if got and got["connect"][0] != 0:
                break
            c.cli(h, f"{op} with {name}", *argv, expect="any")
            row, _ = c.last(None, f"{op} with {name}")
            got[op] = (row["exit"], row.get("refusal")) if row else None
        table[name] = got
        c.note(f"{name} policy outcomes", json.dumps(got))
    read, write, full = table["read"], table["write"], table["full"]
    ok = lambda got, op: bool(got.get(op)) and got[op][0] == 0
    c.verdict("read key: connect, list and restore work; create refused", all(ok(read, o) for o in ("connect", "list", "restore")) and bool(read.get("create")) and read["create"][0] == 125, json.dumps(read))
    c.verdict("write key (no delete): every call works", all(ok(write, o) for o in ("connect", "list", "restore", "create", "replace")), json.dumps(write))
    c.verdict("full key: every call works", all(ok(full, o) for o in ("connect", "list", "restore", "create", "replace")), json.dumps(full))
    # revocation: disable the write user; its next call fails, secret not shown
    user, secret = users["write"]
    code, out = c.mc("admin", "user", "disable", "t", user)
    c.cli(h, "list after the key was revoked", "backup", "list", "bwrite", expect=125)
    row, _ = c.last(None, "list after the key was revoked")
    shown = json.dumps(row or {})
    c.verdict("revoked key refused clearly", bool(row) and row["exit"] == 125 and "403" in shown, json.dumps((row or {}).get("refusal")))
    c.verdict("refusal does not show the secret", secret not in shown and secret not in open(c.log.name).read())
    # rotation: a new key for the same user works after `backup connect` again
    for name, (user, _) in users.items():
        c.mc(script=f"mc admin user remove t {user} >/dev/null; mc admin policy remove t {user} >/dev/null")
    code, out = c.mc("admin", "user", "list", "t")
    c.verdict("scoped test users removed", all(u not in out for u, _ in users.values()))


CASES = {
    "usage": c_usage,
    "roundtrip": c_roundtrip,
    "isolated": c_isolated,
    "refusals": c_refusals,
    "size": c_size,
    "corrupt": c_corrupt,
    "kill": c_kill,
    "cut": c_cut,
    "race": c_race,
    "consistency": c_consistency,
    "concurrent": c_concurrent,
    "cleanup": c_cleanup,
    "perms": c_perms,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--provider", choices=["minio", "r2"], required=True)
    parser.add_argument("--case", choices=sorted(CASES), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--cli", default=os.path.join(HERE, "bin"))
    parser.add_argument("--prefix", help="bucket prefix under bv-<run-id>/ (default: the case name)")
    parser.add_argument("--mib", type=int, default=0)
    parser.add_argument("--phase", help="kill/cut: upload or download")
    parser.add_argument("--part-size", default="16M")
    parser.add_argument("--timeout", type=int, default=110)
    args = parser.parse_args()
    case = Case(args)
    if args.provider == "r2" and args.case != "usage":
        try:
            r2_guard(case)
        except SystemExit as refused:
            case.say(str(refused))
            case.close()
            sys.exit(3)
    try:
        CASES[args.case](case)
    except Exception as error:  # a broken step is a failed case, recorded
        case.verdict("case ran to its end", False, repr(error)[:300])
    sys.exit(case.close())


if __name__ == "__main__":
    main()
