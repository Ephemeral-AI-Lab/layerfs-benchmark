#!/usr/bin/env python3
"""Owned, bounded PostgreSQL fixtures; not LayerFS runtime administration."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import time

OWNER = "layerfs-doctor-pg-116"
IMAGE = "postgres@sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652"


def run(*args, timeout=60, input=None):
    result = subprocess.run(args, text=True, input=input, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed ({result.returncode}): {result.stderr[-2000:]}")
    return result.stdout.strip()


def docker(*args, **kwargs):
    return run("docker", *args, **kwargs)


def sql(container, text):
    return docker("exec", "-u", "postgres", container, "psql", "-XAt", "-v", "ON_ERROR_STOP=1", "-c", text)


def wait_ready(container):
    until = time.monotonic() + 30
    while time.monotonic() < until:
        result = subprocess.run(["docker", "exec", container, "pg_isready", "-U", "postgres"], capture_output=True, timeout=5)
        if result.returncode == 0:
            return
        time.sleep(0.1)
    raise RuntimeError(f"owned fixture {container} did not become ready")


def save(state, data):
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    state.chmod(0o700)
    path = state / "resources.json"
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as output:
        output.write(json.dumps(data, indent=2) + "\n")
    path.chmod(0o600)


def up(state):
    if (state / "resources.json").exists():
        raise RuntimeError("state already registered; inspect status or down explicitly")
    token = secrets.token_hex(6)
    prefix = f"doctor-pg116-{token}"
    data = {"owner": OWNER, "token": token, "profile": "Disposable", "image": docker("image", "inspect", IMAGE, "--format", "{{.Id}}"), "network": prefix, "containers": [], "volumes": [], "password": secrets.token_hex(24)}
    save(state, data)
    docker("network", "create", "--label", f"owner={OWNER}", prefix)
    for suffix in ("primary", "standby"):
        name = f"{prefix}-{suffix}"
        docker("volume", "create", "--label", f"owner={OWNER}", name)
        data["volumes"].append(name)
        save(state, data)
    primary, standby = data["volumes"]
    docker("run", "-d", "--name", primary, "--label", f"owner={OWNER}", "--network", prefix, "--network-alias", "primary", "-e", f"POSTGRES_PASSWORD={data['password']}", "-e", "POSTGRES_HOST_AUTH_METHOD=scram-sha-256", "-p", "127.0.0.1::5432", "-v", f"{primary}:/var/lib/postgresql/data", IMAGE, "-c", "synchronous_commit=off", "-c", "wal_level=replica")
    data["containers"].append(primary)
    save(state, data)
    wait_ready(primary)
    # Fixture-only certificate; never modify host trust or user database settings.
    run("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2", "-subj", "/CN=doctor-pg.fixture.invalid", "-keyout", str(state / "server.key"), "-out", str(state / "server.crt"))
    for file in ("server.key", "server.crt"):
        docker("cp", str(state / file), f"{primary}:/var/lib/postgresql/data/{file}")
    docker("exec", primary, "chown", "postgres:postgres", "/var/lib/postgresql/data/server.key", "/var/lib/postgresql/data/server.crt")
    docker("exec", primary, "chmod", "600", "/var/lib/postgresql/data/server.key")
    sql(primary, "ALTER SYSTEM SET ssl='on'")
    sql(primary, "ALTER SYSTEM SET ssl_cert_file='server.crt'")
    sql(primary, "ALTER SYSTEM SET ssl_key_file='server.key'")
    docker("exec", "-u", "postgres", primary, "sh", "-c", "printf '\nhost replication postgres 0.0.0.0/0 scram-sha-256\n' >> /var/lib/postgresql/data/pg_hba.conf")
    sql(primary, "SELECT pg_reload_conf()")
    sql(primary, "CREATE EXTENSION amcheck")
    sql(primary, "CREATE DATABASE doctor_missing")
    docker("run", "--rm", "--label", f"owner={OWNER}", "--network", prefix, "-e", f"PGPASSWORD={data['password']}", "-v", f"{standby}:/var/lib/postgresql/data", "--user", "postgres", IMAGE, "pg_basebackup", "-h", "primary", "-U", "postgres", "-D", "/var/lib/postgresql/data", "-R", "-X", "stream", "-c", "fast", timeout=60)
    docker("run", "-d", "--name", standby, "--label", f"owner={OWNER}", "--network", prefix, "-p", "127.0.0.1::5432", "-v", f"{standby}:/var/lib/postgresql/data", IMAGE, "-c", "ssl=off", "-c", "synchronous_commit=off", "-c", "hot_standby=on")
    data["containers"].append(standby)
    save(state, data)
    wait_ready(standby)
    if sql(standby, "SELECT pg_is_in_recovery()") != "t":
        raise RuntimeError("standby is not in recovery")
    ports = [json.loads(docker("inspect", "--format", "{{json .NetworkSettings.Ports}}", c))["5432/tcp"][0]["HostPort"] for c in data["containers"]]
    data["ports"] = ports
    data["version"] = sql(primary, "SELECT version()")
    data["ssl"] = sql(primary, "SHOW ssl")
    save(state, data)
    url = f"postgresql://postgres:{data['password']}@127.0.0.1:{ports[0]}/postgres?sslmode=disable"
    env = {"LAYERFS_TEST_POSTGRES_URL": url, "LAYERFS_TEST_POSTGRES_REPLICA_URL": url.replace(f":{ports[0]}/", f":{ports[1]}/"), "LAYERFS_TEST_POSTGRES_MISSING_URL": url.replace("/postgres?", "/doctor_missing?"), "LAYERFS_TEST_POSTGRES_PASSWORD": data["password"], "LAYERFS_TEST_EXPECT_AMCHECK": "1", "LAYERFS_CONSTRUCTION_WORKERS": "1", "LAYERFS_TEST_DOCTOR_PG_DISPOSABLE_CONTAINER": primary}
    with os.fdopen(os.open(state / "environment.json", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as output:
        output.write(json.dumps(env, indent=2) + "\n")
    (state / "environment.json").chmod(0o600)
    print(json.dumps({"state": str(state), "containers": data["containers"], "version": data["version"], "ssl": data["ssl"], "profile": data["profile"]}))


def down(state):
    data = json.loads((state / "resources.json").read_text())
    if data["owner"] != OWNER:
        raise RuntimeError("wrong recorded owner")
    for kind, names in (("container", data["containers"]), ("volume", data["volumes"]), ("network", [data["network"]])):
        for name in names:
            label = docker(kind, "inspect", name, "--format", '{{index .Labels "owner"}}' if kind != "container" else '{{index .Config.Labels "owner"}}')
            if label != OWNER:
                raise RuntimeError(f"owner mismatch: {name}")
            docker(kind, "rm", *( ["-f"] if kind == "container" else []), name)
    data["released"] = True
    save(state, data)
    print("released exact owned PostgreSQL resources")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("up", "down", "status"))
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "up":
        up(args.state.resolve())
    elif args.action == "down":
        down(args.state.resolve())
    else:
        data = json.loads((args.state / "resources.json").read_text())
        data.pop("password", None)
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
