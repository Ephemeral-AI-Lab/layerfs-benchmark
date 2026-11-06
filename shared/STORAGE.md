# Shared storage measurement

> Status: Current general guide for the fs-storage suites.

Storage suites (`fs-storage-micro`, `fs-storage-dsh`, `fs-storage-history`)
measure how many bytes a LayerFS Store holds for a known workload. They never
time anything: wall time is an INELIGIBLE diagnostic. Three modules serve them;
`runner.py`, `measure.py` and `report.py` stay unchanged for speed suites.

| Module | Owns |
| --- | --- |
| [src/storage.py](src/storage.py) | Store-byte probe, Commit collector, summary, multi-Commit driver |
| [src/references.py](src/references.py) | Offline host-side references and the canonical final-state manifest |
| [src/storage_report.py](src/storage_report.py) | Markdown tables with exact bytes and labelled units |

## Measurement contract

- **Quiesced boundary.** Probe only after every Workspace is unmounted and
  every Sandbox closed; `Driver.probe` refuses otherwise and requires the
  Store to be `idle` with no holders.
- **Store bytes** come from `layerfs store status <store>` (checked against
  the pinned 2.0 CLI):
  - SQLite: `file.bytes` (st_size) + `file.wal_bytes` = `total_bytes`. The
    product keeps a WAL after quiesce (autocheckpoint 1,000 pages, journal size
    limit 4 MiB), so `wal_bytes` can hold already-checkpointed frames; report
    the parts as well as the sum.
  - SQLite allocated bytes: `st_blocks × 512` of `store.sqlite` and
    `store.sqlite-wal` in the Docker worker volume
    (`lfs-<home id[:8]>-docker-data`, path `store/<name>/`), read-only with
    `docker run --rm --network none -v <volume>:/d:ro --entrypoint find <image>`.
    Without it, `allocated_status` is `UNAVAILABLE`.
  - PostgreSQL: `server.schemas.layerfs` (sum of `pg_total_relation_size`,
    including TOAST and indexes). Optional `config.storage.server_wal_argv`
    records the server WAL LSN at each probe (owning-infrastructure admin
    command, e.g. `docker exec <pg> psql -Atc 'select pg_current_wal_lsn()'`);
    otherwise server WAL is UNAVAILABLE.
- **Empty-Store floor**: the same Store probed right after
  `store create`/`store connect` + `project init` of an empty folder
  (+ `store push` to Docker for SQLite), before any fork or Sandbox. Net bytes
  = final − floor. Observed on 2.0: SQLite 212,992 B, PostgreSQL 753,664 B.
- **Per Commit**: `commit list <project> <branch> --page-size N --page-pos P`
  followed until `has_more` is false. `logical` is the Commit's whole-tree
  logical size (not a delta); `new_canonical`, `new_stored`, `new_metadata`
  are that Commit's new bytes. Per the 2.0 source (`CommitStatistics`),
  `new_stored` is **all** new pack bytes and `new_metadata` is the
  metadata-domain **subset** (fs-storage-micro M02's copy Commit has
  `new_stored == new_metadata`), so payload = `new_stored − new_metadata`. The collector fails on a broken first-parent
  chain, a repeated id or paging that does not advance.
- **Summary** (`storage.summarize`): net, net file/WAL/allocated parts,
  Σ logical (sum of per-Commit tree sizes), Σ new_canonical, Σ new_stored,
  Σ new_metadata, Σ payload (`sum_new_payload`), unattributed after packs =
  net − Σ new_stored (`unattributed_after_packs_bytes`; report this), the
  spec's unattributed = net − (Σ new_stored + Σ new_metadata)
  (`unattributed_bytes`; counts metadata twice, kept for comparability),
  logical ÷ net, net ÷ each reference, net ÷ ideal unique. A Commit listed on
  several branches counts once.
- **Determinism (observed on 2.0).** Store bytes are not byte-identical in
  general. fs-storage-micro M03 repeats: SQLite `file.bytes` and PostgreSQL
  schema bytes happened to repeat exactly, SQLite `wal_bytes` moved by whole
  WAL frames, per-Commit `new_metadata` (and so `new_stored`) by up to 25 B,
  while payload (`new_stored − new_metadata`), `new_canonical` and `logical`
  were identical. Counterexample: fs-storage-dsh D10 SQLite repeated with
  `file.bytes` +28,672 B (7 pages), WAL unchanged, `new_metadata` drifting up
  to 101 B per Commit. Report the variance; do not claim determinism.
- **One fresh Store per row.** A failed or uncertain Commit marks the row FAIL
  and keeps its Store (`cleanup: INCOMPLETE`, `retained_reason`).

## `storage.py` API

```python
import storage
run = storage.load_runner(cases_module)     # shared runner with your cases
campaign = run.Campaign(config, cache)      # custody: ledger, intent, redaction
row = campaign.state["rows"].setdefault(id, {"id": id, "backend": "sqlite",
                                            "pending": None, "uncertain": False})
storage.run_row(campaign, row, spec, verify=True)   # whole lifecycle, below
summary = storage.row_summary(row, references={"git_pack": 123}, ideal_unique=None)
campaign.finish()   # releases config "resources" (rows already have terminal cleanup)
```

`run_row(campaign, row, spec)` creates or connects every Store, inits its
projects, pushes SQLite Stores to the machine, probes the floor, forks
`spec["branches"]`, runs `spec["steps"]`, checks quiescence, probes `final`,
collects `spec["collect"]` histories, optionally verifies (fresh Sandbox
`<prefix>-v<i>` per item, one Exec, `check(result)` raises on mismatch, then a
`post_verify` probe), and finally releases Workspaces, Sandboxes and Stores.
It never raises for a workload failure; read `row["execution"]`,
`row["verification"]`, `row["cleanup"]`, `row["reason"]`.

```python
spec = {
  "prefix": "fsm-1106-m03-sqlite",          # unique; names verify Sandboxes
  "machine": "docker",
  "password_env": "BENCH_PG_PASSWORD",      # PostgreSQL rows
  "allocated": {"volume": storage.docker_volume_for(home), "image": "sha256:..."},
  "stores": [{"name": "...", "backend": "sqlite" | "postgresql", "url": "postgresql://u@h:p/db",
              "projects": [{"project": "<store>/p", "source": "/abs/empty"}]}],
  "branches": [{"project": "<store>/p", "name": "lane", "from": "main", "commit": None}],
  "steps": [
    {"op": "sandbox", "project": "<store>/p", "sandbox": "<name>"},
    {"op": "mount", "sandbox": "<name>", "branch": "lane", "name": "w", "as": "w"},
    {"op": "exec", "ws": "w", "command": "<bash>", "timeout_s": 120},
    {"op": "commit", "ws": "w", "label": "c01"},
    {"op": "fork", "project": "<store>/p", "name": "b2", "from": "lane"},
    {"op": "unmount", "ws": "w"},
    {"op": "close", "sandbox": "<name>"},
  ],
  "collect": [{"project": "<store>/p", "branch": "lane"}],
  "verify": [{"project": "<store>/p", "branch": "lane", "command": "<bash>", "check": fn}],
  "timeout_s": 60,                          # default per command; ≤ 120 enforced
  "release_stores": True,
}
```

For shapes `run_row` does not cover, use `storage.Driver(campaign, row)`
directly: `store_create`, `store_connect`, `project_init`, `store_push`,
`fork`, `sandbox_create`, `mount` (returns `ws`), `exec`, `commit`,
`unmount`, `sandbox_close`, `store_release`, `probe(store, label, allocated)`,
(`exec` also appends `{label, phase, ws, exit_code, stdout, stderr}` to
`row["exec_results"]`, first 8,000 characters each),
`commits(project, branch)`, `quiesced()`, `cleanup()`. Each call is one
bounded `Campaign.call` with a unique phase label; Exec `exit_code` ≠ 0, a
truncated Exec, a non-`Committed` Commit, or any CLI refusal raises and is
never retried. Campaign state keeps the first 2,000 characters of each
command's output; `ledger.jsonl` keeps the full output.

Pure helpers: `parse_status`, `parse_allocated`, `allocated_argv`,
`server_wal_bytes(row)` (PostgreSQL LSN delta floor→final),
`docker_volume_for`, `collect_commits(list_page, project, branch)`,
`commit_record`, `total`, `summarize`, `pg_lsn_bytes`, `safe_database_url`,
`POLICY` (the fixed 2.0 storage policy to record in reports).

## `references.py`

`references.compute(snapshot_dirs)` → `{states, manifests, input_sha256,
tools, whole_file_unique, tar_zstd, git_pack, cdc_oracle}`; each reference has
`bytes` (or `status: UNAVAILABLE`). `reference_bytes(result)` gives
name → bytes for `summarize`; `pin(result, path)` writes the JSON and returns
its SHA-256. `export_git_states(repo, commits, dest)` turns a Git history into
snapshot directories. CLI: `python3 shared/src/references.py out.json s0 s1 …`.

- Whole-file unique: Σ distinct regular-file contents (SHA-256).
- Σ `tar | zstd -3`: deterministic PAX tar (sorted, mtime/uid 0) per state,
  `zstd -3 -T1`.
- Git pack + idx: fresh bare repo, one Commit per state (fixed dates),
  `git repack -a -d -f --window=10 --depth=50`, `pack.threads=1`. Git does not
  track empty directories or modes beyond the executable bit.
- CDC oracle (**approximate**): gear hash, FastCDC normalized masks, 8/16/32
  KiB, files ≥ 128 KiB chunked, smaller files whole; Σ min(raw, zstd-3) over
  unique objects (Python 3.14 `compression.zstd`). The gear table differs
  from LayerFS's, so it is context, never a gate. Pure Python: roughly
  5–10 MB/s of unique large-file content.

**Final-state manifest.** `references.manifest(root)` hashes canonical lines
`<f|d|l> <mode:04o> <size> <sha256|-> <path>\n` sorted by path (root
excluded; symlink size/hash are of the target text). An in-Sandbox verifier
prints the same digest, so a suite pins one SHA-256 per branch head instead of
a full file list.

## `storage_report.py`

`b` (exact bytes `1,234,567`), `mb`, `mib`, `ratio`, `table`, `ordered`
(case, then SQLite before PostgreSQL), `store_bytes_table`,
`attribution_table`, `reference_table`, `references_bytes_table`,
`commit_curve_table`, `UNITS_NOTE`. Input rows are
`{case, backend, outcome, summary}`.

Tests: `python3 -m unittest discover -s shared/tests` (no LayerFS execution).
