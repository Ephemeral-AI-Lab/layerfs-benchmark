"""DIAGNOSTIC per-table attribution (optional, default OFF; owner decision pending).

The repository rule bans direct Store SQL in benchmarks. layerfs-project#85
task 1 asks the owner whether read-only per-table attribution may live in this
suite; until the owner decides, it runs only behind ``late-probe
--attribution``, after the row's measurements are complete, and is labelled
DIAGNOSTIC in every output. It never touches a live Store:

* SQLite: the Store's ``store.sqlite``/``-wal`` are copied read-only out of the
  Docker worker volume (``docker run --rm --network none -v <vol>:/d:ro``) into
  a private directory, then ``dbstat`` runs on that closed copy with a host
  ``sqlite3`` built with ``SQLITE_ENABLE_DBSTAT_VTAB``. The copy is deleted.
* PostgreSQL: one read-only transaction on the row's own disposable database in
  the owned server container: ``pg_total_relation_size`` (heap + TOAST +
  indexes), ``pg_relation_size``, ``pg_indexes_size``, ``n_live_tup``,
  ``n_dead_tup``, ``last_autovacuum`` per table of schema ``layerfs``.

Tool calls go through ``Campaign.call(cli=False)`` (intent first, one attempt).
Failures are recorded in the row's ``attribution`` record, never raised.
"""

import json
import shutil
from pathlib import Path
from urllib.parse import urlsplit

import measure
import storage

LABEL = "DIAGNOSTIC (owner decision pending, layerfs-project#85 task 1)"
DBSTAT_SQL = (
    "SELECT name, count(*) AS pages, sum(pgsize) AS bytes, sum(payload) AS payload, "
    "sum(unused) AS unused, sum(ncell) AS cells, "
    "sum(CASE WHEN pagetype='overflow' THEN 1 ELSE 0 END) AS overflow_pages "
    "FROM dbstat GROUP BY name ORDER BY bytes DESC;"
)
PRAGMA_SQL = (
    "SELECT (SELECT page_size FROM pragma_page_size) AS page_size, "
    "(SELECT page_count FROM pragma_page_count) AS page_count, "
    "(SELECT freelist_count FROM pragma_freelist_count) AS freelist_count;"
)
PG_SQL = (
    "BEGIN READ ONLY; "
    "SELECT coalesce(json_agg(t ORDER BY t.total_bytes DESC), '[]') FROM ("
    "SELECT c.relname AS name, pg_total_relation_size(c.oid) AS total_bytes, "
    "pg_relation_size(c.oid) AS heap_bytes, pg_indexes_size(c.oid) AS index_bytes, "
    "coalesce(pg_total_relation_size(nullif(c.reltoastrelid, 0)), 0) AS toast_bytes, "
    "s.n_live_tup AS live_tuples, s.n_dead_tup AS dead_tuples, "
    "s.last_autovacuum, s.last_vacuum, s.autovacuum_count "
    "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'layerfs' "
    "LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid WHERE c.relkind IN ('r', 'm')) t; "
    "COMMIT;"
)


def _call(campaign, row, phase, argv, timeout_s=60):
    row["sequence"] = row.get("sequence", 0) + 1
    return campaign.call(row, f"{row['sequence']:05d}_{phase}", argv,
                         measure.Deadline.after(timeout_s), cli=False)


def sqlite_copy_argv(volume, image, store, out_dir):
    return [
        "docker", "run", "--rm", "--network", "none", "--pull", "never", "--user", "0:0",
        "-v", f"{volume}:/d:ro", "-v", f"{out_dir}:/out", "--entrypoint", "sh", image, "-c",
        f"cp /d/store/{store}/store.sqlite /out/ && "
        f"if [ -e /d/store/{store}/store.sqlite-wal ]; then cp /d/store/{store}/store.sqlite-wal /out/; fi",
    ]


def sqlite(campaign, row, store, work):
    config = campaign.config
    options = config.get("attribution", {})
    binary = options.get("sqlite3") or shutil.which("sqlite3")
    image = options.get("copy_image") or config["artifacts"]["base_image"]
    volume = storage.docker_volume_for(config["home"])
    out = Path(work) / row["id"].replace("/", "_")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    try:
        _call(campaign, row, "attribution_copy", sqlite_copy_argv(volume, image, store, out))
        db = str(out / "store.sqlite")
        stat = _call(campaign, row, "attribution_dbstat", [binary, "-json", db, DBSTAT_SQL])
        pragma = _call(campaign, row, "attribution_pragma", [binary, "-json", db, PRAGMA_SQL])
        tables = json.loads(stat.get("stdout") or "[]")
        return {"label": LABEL, "status": "MEASURED", "method": "dbstat on a closed copy",
                "copy_bytes": {p.name: p.stat().st_size for p in out.iterdir()},
                "pragma": (json.loads(pragma.get("stdout") or "[{}]") or [{}])[0], "tables": tables}
    finally:
        shutil.rmtree(out, ignore_errors=True)


def postgresql(campaign, row, store):
    config = campaign.config
    info = row["owned"]["stores"][store]
    url = urlsplit(info["database"])
    container = config["postgresql"]["server_container"]
    argv = ["docker", "exec", container, "psql", "-U", url.username or "bench", "-d", url.path.lstrip("/"),
            "-X", "-q", "-At", "-c", PG_SQL]
    result = _call(campaign, row, "attribution_pg", argv)
    text = result.get("stdout") or ""
    start = text.find("[")
    return {"label": LABEL, "status": "MEASURED", "method": "read-only catalog query on the owned database",
            "tables": json.loads(text[start:].strip()) if start >= 0 else []}


def collect(campaign, row, work):
    out = {}
    for store, info in row["owned"]["stores"].items():
        if not info.get("live"):
            continue
        try:
            if info["backend"] == "sqlite":
                out[store] = sqlite(campaign, row, store, work)
            else:
                out[store] = postgresql(campaign, row, store)
        except Exception as error:  # noqa: BLE001 - diagnostic only; never fails the row
            out[store] = {"label": LABEL, "status": "FAIL", "reason": f"{type(error).__name__}: {error}"}
            if row.get("pending") or row.get("uncertain"):
                break
    return out
