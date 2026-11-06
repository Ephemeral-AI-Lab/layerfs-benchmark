#!/usr/bin/env python3
"""Write one fs-storage-quick environment.json (one campaign) from explicit inputs.

  env.py --campaign-id q86-c1 --source-sha <40 hex> --cli /abs/layerfs --xdg /abs/xdg \
         --home /abs/home --empty /abs/empty --base-dir /abs/base-157 --image sha256:… \
         --pg-container fsopt-86-pg --pg-port 55486 --out /abs/campaign-dir/environment.json

Hashes the CLI and its sibling ``layerfs-daemon``, reads the Linux bundle seal
from ``<xdg>/layerfs/bundle/2.0.0/linux-aarch64/bundle.json`` and names one
fresh database per PostgreSQL row (``<id>_q1`` … with hyphens removed). The
campaign's only owned resource is a single ``dropdb`` of those databases in
the given server, run by ``run.py finish``; the server container, worker and
image are released by their owner outside the campaign. Each campaign id is
used once (a Campaign never replays a registered row).
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

RUNTIME = "sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e"
PG_IMAGE = "postgres:17-bookworm sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652"
CASES = ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def build(args):
    if not re.fullmatch(r"[a-z0-9-]{1,16}", args.campaign_id):
        raise SystemExit("campaign id: 1–16 lowercase letters, digits or hyphens")
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
        raise SystemExit("source sha: 40 lowercase hex")
    cli = Path(args.cli)
    daemon = cli.with_name("layerfs-daemon")
    bundle = json.loads((Path(args.xdg) / "layerfs/bundle/2.0.0/linux-aarch64/bundle.json").read_text())
    tag = args.campaign_id.replace("-", "")
    user = args.pg_user
    databases = {f"{c}/postgresql": f"postgresql://{user}@127.0.0.1:{args.pg_port}/{tag}_{c.lower()}" for c in CASES}
    for repeat in range(2, args.repeats + 1):
        databases.update({f"{c}/postgresql/r{repeat}": f"postgresql://{user}@127.0.0.1:{args.pg_port}/{tag}_{c.lower()}_r{repeat}"
                          for c in CASES})
    names = " ".join(url.rsplit("/", 1)[1] for url in databases.values())
    return {
        "campaign_id": args.campaign_id,
        "source_sha": args.source_sha,
        "cli": str(cli),
        "home": args.home,
        "empty_source": args.empty,
        "base_dir": args.base_dir,
        "environment": {"XDG_CACHE_HOME": args.xdg},
        "artifacts": {
            "cli_sha256": sha256(cli),
            "daemon_sha256": sha256(daemon) if daemon.is_file() else None,
            "linux_bundle_sha256": bundle["hash"],
            "profile": args.profile,
            "base_image": RUNTIME,
            "sandbox_image": f"{args.image} (fs-storage-quick:v1)",
            "label": args.label,
        },
        "machines": {"docker": {"name": "docker", "ready": True, "platform": "linux"}},
        "storage": {"server_wal_argv": ["docker", "exec", args.pg_container, "psql", "-U", user, "-d", "postgres",
                                        "-Atc", "select pg_current_wal_lsn()"]},
        "attribution": {"sqlite3": args.sqlite3},
        "postgresql": {
            "password_env": args.password_env,
            "server_container": args.pg_container,
            "server_image": f"{PG_IMAGE}, 1 CPU / 512 MiB, 127.0.0.1:{args.pg_port}",
            "disposal_resource": "campaign-databases",
            "databases": databases,
        },
        "resources": [{
            "id": "campaign-databases", "owned": True,
            "release_argv": ["docker", "exec", args.pg_container, "sh", "-c",
                             f"for d in {names}; do dropdb -U {user} --if-exists \"$d\" || exit 1; done"],
        }],
        "shared_infrastructure": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--cli", required=True)
    parser.add_argument("--xdg", required=True)
    parser.add_argument("--home", required=True)
    parser.add_argument("--empty", required=True)
    parser.add_argument("--base-dir", required=True)
    parser.add_argument("--image", required=True, help="fs-storage-quick image id (sha256:…)")
    parser.add_argument("--pg-container", required=True)
    parser.add_argument("--pg-port", type=int, required=True)
    parser.add_argument("--pg-user", default="bench")
    parser.add_argument("--password-env", default="BENCH_PG_PASSWORD")
    parser.add_argument("--profile", default="release")
    parser.add_argument("--label", default="", help="free text, e.g. candidate branch and head")
    parser.add_argument("--sqlite3", default="/opt/homebrew/opt/sqlite/bin/sqlite3",
                        help="host sqlite3 with dbstat, only for the DIAGNOSTIC attribution")
    parser.add_argument("--repeats", type=int, default=1, help="also name databases for --repeat 2..N")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f"{out} exists; a campaign id and its environment are used once")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build(args), indent=1) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
