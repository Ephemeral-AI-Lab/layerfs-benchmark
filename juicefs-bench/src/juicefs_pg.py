#!/usr/bin/env python3
"""Single-attempt JuiceFS/PG16 baseline with dedicated Docker resources."""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

import cases

IMAGE = "sha256:33dd678ed762dc1ed94ba0a2f70b35aa803e8a5b634b696615c619734ccc28ae"
TOOL_HASH = "3c1d7c2d15b4d65949cc809552401e6a01ddb6f5ef313f9df96b8989435b2bd8"
URL = "postgres://jfs@pg:5432/juicefs?sslmode=disable"


def save(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n")
    temp.replace(path)


class Baseline:
    def __init__(self, root):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "state.json"
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {
            "id": "jfs-pg16-20261109", "execution": "NOT_RUN", "cleanup": "NOT_RUN",
            "resources": [], "cache": "INELIGIBLE", "correctness": "UNVERIFIED",
            "budget_s": 60, "client_image": IMAGE, "tool_sha256": TOOL_HASH,
            "metadata_url": URL, "workload": cases.get_case("J01")["provenance"]}

    def persist(self):
        save(self.path, self.state)

    def command(self, name, argv, timeout=30):
        path = self.root / (name + ".json")
        if path.exists():
            raise RuntimeError("already attempted; no replay: " + name)
        start = time.monotonic_ns()
        save(path, {"argv": argv, "status": "ATTEMPTED", "at_ns": time.time_ns()})
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            save(path, {"argv": argv, "status": "UNCERTAIN", "timeout_s": timeout,
                        "elapsed_ns": time.monotonic_ns() - start})
            raise RuntimeError(name + ": timeout; remote execution requires inspection") from error
        result = {"argv": argv, "exit": p.returncode, "stdout": p.stdout,
                  "stderr": p.stderr, "elapsed_ns": time.monotonic_ns() - start}
        save(path, result)
        if p.returncode:
            raise RuntimeError(f"{name}: exit {p.returncode}: {p.stderr[-1500:]}")
        return result

    def allocate(self, name, kind, argv):
        resource = {"name": name, "kind": kind, "state": "ATTEMPTED"}
        self.state["resources"].append(resource)
        self.persist()
        result = self.command("allocate-" + name, argv, timeout=60)
        resource.update(state="LIVE", id=result["stdout"].strip())
        self.persist()
        return resource["id"]

    def prepare(self, pg_image):
        if self.state.get("preparation"):
            raise RuntimeError("preparation already attempted")
        prefix = self.state["id"]
        for kind in ("container", "volume", "network"):
            listing = self.command("preflight-" + kind, ["docker", kind, "ls", "--format", "{{.Name}}"] if kind != "container" else
                                   ["docker", "ps", "-a", "--format", "{{.Names}}"])
            if any(name.startswith(prefix + "-") for name in listing["stdout"].splitlines()):
                raise RuntimeError("resource name collision; existing resources preserved")
        self.state.update(preparation="ATTEMPTED", pg_image=pg_image)
        self.persist()
        prefix = self.state["id"]
        label = "benchmark.owner=" + prefix
        net = self.allocate(prefix + "-net", "network", ["docker", "network", "create", "--internal", "--label", label, prefix + "-net"])
        for suffix in ("pgdata", "objects-cache"):
            self.allocate(prefix + "-" + suffix, "volume", ["docker", "volume", "create", "--label", label, prefix + "-" + suffix])
        pg = self.allocate(prefix + "-pg", "container", ["docker", "run", "-d", "--pull", "never", "--name", prefix + "-pg",
            "--label", label, "--network", net, "--network-alias", "pg", "-e", "POSTGRES_USER=jfs", "-e", "POSTGRES_DB=juicefs",
            "-e", "POSTGRES_HOST_AUTH_METHOD=trust", "-v", prefix + "-pgdata:/var/lib/postgresql/data",
            "--health-cmd", "pg_isready -h 127.0.0.1 -U jfs -d juicefs", "--health-interval", "1s", "--health-timeout", "2s", "--health-retries", "30", pg_image])
        self.state["pg_container"] = pg
        self.persist()
        # Readiness waits do not replay failed operations.
        end = time.monotonic() + 45
        for index in range(90):
            q = self.command(f"readiness-{index}", ["docker", "inspect", pg])
            observed = json.loads(q["stdout"])[0]["State"]
            health = observed.get("Health", {}).get("Status")
            if health == "healthy":
                break
            if not observed["Running"] or health == "unhealthy" or time.monotonic() >= end:
                raise RuntimeError("PostgreSQL failed readiness")
            time.sleep(0.5)
        else:
            raise RuntimeError("PostgreSQL readiness expired")
        self.state["pg_settings"] = self.command("pg-settings", ["docker", "exec", pg, "psql", "-U", "jfs", "-d", "juicefs", "-At", "-c",
            "SELECT version(); SHOW fsync; SHOW synchronous_commit; SHOW full_page_writes; SHOW shared_buffers;"])["stdout"]
        client = self.allocate(prefix + "-client", "container", ["docker", "run", "-d", "--pull", "never", "--init", "--name", prefix + "-client",
            "--label", label, "--network", net, "--device", "/dev/fuse", "--cap-add", "SYS_ADMIN", "--security-opt", "apparmor=unconfined",
            "-v", prefix + "-objects-cache:/data", "--entrypoint", "/bin/bash", IMAGE, "-c", "exec sleep infinity"])
        self.state["client_container"] = client
        self.persist()
        self.command("client-identity", ["docker", "exec", client, "/bin/bash", "-c",
            f"set -eu; echo '{TOOL_HASH}  /usr/local/bin/juicefs' | sha256sum -c -; juicefs version; df -B1 /data; mkdir -p /mnt/jfs /data/objects /data/cache"])
        self.command("format", ["docker", "exec", client, "juicefs", "format", "--storage", "file", "--bucket", "/data/objects",
            "--compress", "none", "--trash-days", "0", URL, "jfs-pg16"])
        self.command("mount", ["docker", "exec", client, "juicefs", "mount", "-d", "--no-syslog", "--log", "/tmp/juicefs-pg16.log",
            "--cache-dir", "/data/cache", "--cache-size", "102400", "--buffer-size", "300", URL, "/mnt/jfs"])
        self.state["mount_proof"] = self.command("mount-proof", ["docker", "exec", client, "/bin/bash", "-c",
            "set -eu; awk '$5==\"/mnt/jfs\" && / - fuse.juicefs / {ok=1; print} END{exit !ok}' /proc/self/mountinfo; juicefs config '" + URL + "'"])["stdout"]
        self.state["preparation"] = "READY"
        self.persist()

    def run(self):
        if self.state.get("preparation") != "READY" or self.state["execution"] != "NOT_RUN":
            raise RuntimeError("requires unconsumed ready baseline; no replay")
        self.state["execution"] = "ATTEMPTED"
        for name in ("juicefs_pg.py", "cases.py"):
            data = (Path(__file__).parent / name).read_bytes()
            (self.root / ("source-" + name)).write_bytes(data)
            self.state.setdefault("source_hashes", {})[name] = hashlib.sha256(data).hexdigest()
        self.persist()
        try:
            result = self.command("bench", ["docker", "exec", "-w", "/mnt/jfs", "-e", "LANG=C", "-e", "LC_ALL=C",
                "-e", "SKIP_DROP_CACHES=true", "-e", "JUICEFS_SHA256=" + TOOL_HASH, self.state["client_container"],
                "/bin/bash", "-o", "pipefail", "-c", cases.BODY], timeout=self.state["budget_s"])
            self.state["metrics"] = cases.parse_result("J01", result["stdout"], result["stderr"], result["exit"])
            self.state.update(execution="PASS", bench_elapsed_ns=result["elapsed_ns"])
        except (RuntimeError, ValueError) as error:
            self.state.update(execution="FAIL", reason=str(error))
            raise
        finally:
            self.persist()

    def finish(self):
        if self.state["cleanup"] != "NOT_RUN":
            raise RuntimeError("cleanup already attempted; inspect rather than replay")
        self.state["cleanup"] = "ATTEMPTED"
        self.persist()
        try:
            if self.state.get("client_container") and self.state["execution"] == "PASS":
                self.command("unmount", ["docker", "exec", self.state["client_container"], "juicefs", "umount", "/mnt/jfs"])
            for resource in reversed(self.state["resources"]):
                if resource["state"] != "LIVE":
                    raise RuntimeError("uncertain allocation requires inspection: " + resource["name"])
                rid, kind = resource["id"], resource["kind"]
                q = self.command("inspect-release-" + resource["name"], ["docker", kind, "inspect", rid])
                data = json.loads(q["stdout"])[0]
                labels = data["Config"]["Labels"] if kind == "container" else data.get("Labels", {})
                if labels.get("benchmark.owner") != self.state["id"]:
                    raise RuntimeError("ownership mismatch; preserved " + rid)
                if kind == "container":
                    self.command("stop-" + resource["name"], ["docker", "stop", "-t", "5", rid])
                    argv = ["docker", "rm", rid]
                else:
                    argv = ["docker", kind, "rm", rid]
                self.command("release-" + resource["name"], argv)
                resource["state"] = "RELEASED"
                self.persist()
            self.state["cleanup"] = "COMPLETE"
        except RuntimeError as error:
            self.state.update(cleanup="INCOMPLETE", cleanup_reason=str(error))
            raise
        finally:
            self.persist()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["prepare", "run", "finish"])
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--pg-image")
    args = p.parse_args()
    baseline = Baseline(args.root)
    if args.action == "prepare":
        if not args.pg_image or not args.pg_image.startswith("sha256:"):
            p.error("prepare requires pinned --pg-image sha256:...")
        baseline.prepare(args.pg_image)
    else:
        getattr(baseline, args.action)()
    print(json.dumps({k: baseline.state.get(k) for k in ("preparation", "execution", "cleanup", "metrics")}))


if __name__ == "__main__":
    main()
