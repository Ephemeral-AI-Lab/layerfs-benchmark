"""backup-verify schema v2 checks (layerfs-project #84, #91): a schema v1
backup meets a schema v2 CLI, on MinIO only.

    python3 schema_v2.py --case v1-restore|v1-migrate --run-id ID --env-file PRIVATE.env \
        --cli-v1 DIR --cli-v2 DIR --tree-v2 DIR

  v1-restore (B3): the v1 CLI makes a Store with history and backs it up; the
      v2 CLI's restore of that backup into a fresh home is refused at the open
      check, naming the conversion; no Store and no staging folder are left,
      and an unrelated v2 Store in that home is unchanged.
  v1-migrate (B4): the closed v1 Store from v1-restore is converted with the
      v2 tree's `tools/store_blocks.py migrate`, put back in its home, and
      read by the v2 CLI (equal to the v1 snapshot); then the roundtrip and
      isolated checks run on it with the v2 CLI under a new prefix.

--tree-v2 holds the v2 commit's `tools/` and
`engine/crates/layerfs-persistence/sql/` (for example from `git archive`).
Reuses run.py's Case; one attempt per step; receipts go to
receipts/<run-id>/minio/.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run  # noqa: E402

TAG = "v1"


def use(c, cli):
    c.args.cli = cli


def store_file(home, store):
    return f"/scratch/{TAG}/{home}/store/{store}/store.sqlite"


def file_facts(c, path):
    """sha256, SQLite user_version and sidecars of a Store file (read only)."""
    script = (
        "import hashlib,json,os,sqlite3,sys;p=sys.argv[1];"
        "d=sqlite3.connect('file:'+p+'?mode=ro&immutable=1',uri=True);"
        "print(json.dumps({'sha256':hashlib.sha256(open(p,'rb').read()).hexdigest(),"
        "'user_version':d.execute('PRAGMA user_version').fetchone()[0],"
        "'sidecars':[s for s in ('-wal','-shm','-journal') if os.path.exists(p+s)]}))"
    )
    code, out = c.sh(f"python3 -c \"{script}\" {path}")
    try:
        return json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        c.verdict(f"read facts of {path}", False, out.strip()[-200:])
        return {}


def v1_restore(c, args):
    use(c, args.cli_v1)
    h1 = "home-v1"
    c.inside(h1, "fixture", "--store", "shop", "--history")
    c.inside(h1, "snapshot", "--store", "shop", "--trees", "--out", "/out/v1-src.json")
    c.verdict("v1 connect", c.connect(h1) == 0)
    c.cli(h1, "v1 create", "backup", "create", "shop", "b")
    facts = file_facts(c, store_file(h1, "shop"))
    c.verdict("source Store is schema v1", facts.get("user_version") in (16, 17, 18, 22, 23, 24), json.dumps(facts))

    use(c, args.cli_v2)
    h2 = "home-v2"
    c.inside(h2, "fixture", "--store", "keep")
    c.inside(h2, "snapshot", "--store", "keep", "--trees", "--out", "/out/v2-keep-before.json")
    keep = file_facts(c, store_file(h2, "keep"))
    c.verdict("unrelated Store is schema v2", keep.get("user_version") in (36, 37, 38, 42, 43, 44), json.dumps(keep))
    c.verdict("v2 connect", c.connect(h2) == 0)
    c.cli(h2, "v2 list shows the v1 backup", "backup", "list", "b")
    out = c.cli(h2, "v2 restore of the v1 backup refused", "backup", "restore", "shop", "b", "shop", expect=125)
    c.verdict("refusal names the conversion", "store_blocks.py migrate" in out, run.refusal(out))
    c.cli(h2, "no Store made by the refused restore", "store", "get", "shop", expect=125)
    code, listing = c.sh(f"ls -a /scratch/{TAG}/{h2}/store")
    names = listing.split()
    c.verdict("no staging folder or Store folder left", not any(n.startswith(".restore-") or n == "shop" for n in names), " ".join(names))
    c.inside(h2, "snapshot", "--store", "keep", "--trees", "--out", "/out/v2-keep-after.json")
    code, _ = c.inside(h2, "compare", "/out/v2-keep-before.json", "/out/v2-keep-after.json", expect_ok=False)
    after = file_facts(c, store_file(h2, "keep"))
    c.verdict("unrelated v2 Store unchanged (history and file)", code == 0 and after.get("sha256") == keep.get("sha256"), after.get("sha256", ""))
    after_v1 = file_facts(c, store_file(h1, "shop"))
    c.verdict("v1 source Store unchanged", after_v1.get("sha256") == facts.get("sha256"), after_v1.get("sha256", ""))


def v1_migrate(c, args):
    h1 = "home-v1"
    src = store_file(h1, "shop")
    before = file_facts(c, src)
    c.verdict("v1 Store closed and schema v1", not before.get("sidecars") and before.get("user_version") in (16, 17, 18, 22, 23, 24), json.dumps(before))
    proc = subprocess.run(
        ["docker", "run", "--rm", "--pull", "never", "--network", "none",
         "--mount", f"type=volume,src={c.volume},dst=/scratch",
         "--mount", f"type=bind,src={args.tree_v2},dst=/tree,readonly",
         "--entrypoint", "sh", run.BUILD_IMAGE, "-c",
         f"cp {src} /scratch/{TAG}/shop-v1.sqlite && "
         f"python3 /tree/tools/store_blocks.py migrate /scratch/{TAG}/shop-v1.sqlite /scratch/{TAG}/shop-v2.sqlite"],
        capture_output=True, text=True, timeout=args.timeout)
    c.say("   migrate: " + (proc.stdout + proc.stderr).strip()[-400:])
    c.verdict("store_blocks.py migrate", proc.returncode == 0, f"exit {proc.returncode}")
    migrated = file_facts(c, f"/scratch/{TAG}/shop-v2.sqlite")
    c.verdict("migrated copy is schema v2", migrated.get("user_version") in (36, 37, 38, 42, 43, 44), json.dumps(migrated))
    kept = file_facts(c, f"/scratch/{TAG}/shop-v1.sqlite")
    c.verdict("migration source copy unchanged", kept.get("sha256") == before.get("sha256"), kept.get("sha256", ""))
    code, out = c.sh(f"mv /scratch/{TAG}/shop-v2.sqlite {src}")
    c.verdict("migrated copy installed in its home", code == 0, out.strip()[-200:])

    use(c, args.cli_v2)
    c.inside(h1, "snapshot", "--store", "shop", "--trees", "--out", "/out/v1-migrated.json")
    code, _ = c.inside(h1, "compare", "/out/v1-src.json", "/out/v1-migrated.json", expect_ok=False)
    c.verdict("v2 CLI reads the migrated Store equal to the v1 source", code == 0)
    # B1 on the migrated Store, under its own prefix
    url = c.url + "/after"
    code, _ = c.inside(h1, "cli", "--label", "connect b2", "--", "backup", "connect", "b2", url, "--key", c.key, "--part-size", c.args.part_size, expect_ok=False)
    c.verdict("connect b2", code == 0)
    c.cli(h1, "create from migrated", "backup", "create", "shop", "b2", "--progress")
    _, made = c.last(None, "create from migrated")
    c.cli(h1, "restore migrated as copy", "backup", "restore", "copy", "b2", "shop", "--progress")
    _, restored = c.last(None, "restore migrated as copy")
    if made and restored:
        c.verdict("restored sha256 equals uploaded", made["sha256"] == restored["sha256"], made["sha256"])
        c.verdict("restored heads equal uploaded", made["heads"] == restored["heads"], made["heads"])
    else:
        c.verdict("create and restore reported", False)
    c.inside(h1, "snapshot", "--store", "copy", "--trees", "--out", "/out/v1-migrated-copy.json")
    code, _ = c.inside(h1, "compare", "/out/v1-src.json", "/out/v1-migrated-copy.json", expect_ok=False)
    c.verdict("restored copy equals the v1 source", code == 0)
    code, _ = c.inside(h1, "write-read", "--project", "copy/api", "--branch", "topic", expect_ok=False)
    c.verdict("new commit on the restored copy", code == 0)
    code, _ = c.inside(h1, "write-read", "--project", "shop/api", "--branch", "topic", expect_ok=False)
    c.verdict("new commit on the migrated Store", code == 0)
    h3 = "home-v2-isolated"
    code, _ = c.inside(h3, "cli", "--label", "connect b2 fresh", "--", "backup", "connect", "b2", url, "--key", c.key, "--part-size", c.args.part_size, expect_ok=False)
    c.verdict("connect b2 from a fresh home", code == 0)
    c.cli(h3, "restore migrated into fresh home", "backup", "restore", "shop", "b2", "shop")
    c.inside(h3, "snapshot", "--store", "shop", "--trees", "--out", "/out/v1-migrated-isolated.json")
    code, _ = c.inside(h3, "compare", "/out/v1-src.json", "/out/v1-migrated-isolated.json", expect_ok=False)
    c.verdict("isolated restore equals the v1 source", code == 0)
    code, _ = c.inside(h3, "write-read", "--project", "shop/api", "--branch", "topic", expect_ok=False)
    c.verdict("new commit after isolated restore", code == 0)


CASES = {"v1-restore": v1_restore, "v1-migrate": v1_migrate}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", choices=sorted(CASES), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--cli-v1", required=True)
    parser.add_argument("--cli-v2", required=True)
    parser.add_argument("--tree-v2", required=True)
    parser.add_argument("--part-size", default="16M")
    parser.add_argument("--timeout", type=int, default=110)
    args = parser.parse_args()
    args.provider, args.prefix, args.cli = "minio", TAG, args.cli_v1
    for path in (args.cli_v1, args.cli_v2):
        with open(os.path.join(path, "layerfs"), "rb") as f:
            print(f"cli {path} sha256 {hashlib.sha256(f.read()).hexdigest()}", flush=True)
    case = run.Case(args)
    try:
        CASES[args.case](case, args)
    except Exception as error:  # a broken step is a failed case, recorded
        case.verdict("case ran to its end", False, repr(error)[:300])
    sys.exit(case.close())


if __name__ == "__main__":
    main()
