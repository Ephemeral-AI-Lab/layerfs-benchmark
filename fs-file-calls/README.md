# fs-file-calls — mountless file call family latency, throughput and storage growth
> group: filesystem · measures: speed, storage, correctness

Measures the mountless LayerFS 2.0 `file` call family (`read`, `stat`, `list`,
`glob`, `grep`, `blame`, `history`, `write`, `edit`, `apply`, `cp`, `mv`, `rm`,
`mkdir`) plus `commit.diff` (which replaced 1.x `file.diff` in 2.0).

Compares:
- **Front end**: CLI (fresh `layerfs` process per call, matching `dsh-layerfs`) vs persistent Node SDK (`@layerfs/node` `client({ home })`).
- **Route / backend**: native SQLite (`ext4`), native PostgreSQL (`18.6`, with `pg_stat_statements`), and worker routes (`docker`, `lima`, `apple-container` — registered as `NOT_RUN` when unavailable on the host).
- **Scale & history**: trees `F100`, `F1k`, `F10k` (depth `<= 6`); file sizes `0 B`, `1 KiB`, `64 KiB`, `1 MiB`, `16 MiB`; history depths `H1` and `H<--h-depth>` (default 50; the label in the report is the depth that was seeded).
- **Concurrency**: 1, 4, and 8 parallel readers; parallel writers on separate Branches and on one Branch, recording every `Busy` / `Conflict` / `Failed` refusal by code.
- **Independent proof**: write results verified via subsequent `file.read`/`file.stat` and `project.export` SHA-256 tree hash; read results verified against the fixture manifest.

## Rows, limits, cold and attribution

- **One case, one row.** A non-zero CLI exit (or an SDK `LayerFSError`) becomes a `REFUSED` row carrying the product's refusal `code`; a call over the 120 s cap becomes a `FAIL` row with `cap_s`; the run continues and exits 0. Rows are never dropped; skipped fixtures are `NOT_RUN`.
- **Fixtures.** `--trees F100,F1k,F10k[,F100k]` (depth 4, `F100k` has 100 files per directory), `--h-depths 10,100,1000` (H1 always runs; branch `h<d>` holds `d` Commits of `/target.txt`), `--big-write-mib 64` adds a `file.write (64m)` case. Each fixture manifest (sha256 over sorted `path`, size, content sha256) is recorded in `results.json` under `fixtures`. Writing rows run on a branch forked from the seeded one; after them the seeded `main` of every read fixture is exported and its manifest hash re-checked (`proof.<arm>_manifest_unchanged_after_writes`). Each phase stops with `NOT_RUN` rows when fewer than 25 GB would stay free.
- **Read proof.** Every OK read row carries `proof.manifest` (fixture, manifest hash, the check, `matched`/`checked`). The CLI arm checks every sample, the SDK arm its last sample.
- **Limits** (`limit:` rows, `--write-ladder-mib`, `--apply-rows`): largest `file.write` content on a ladder, `file.apply` row counts, `commit.diff` page limit 1000/1001, `file.read` window 2000/2001 lines with the reply size. Each row cites the source line that sets the limit.
- **Cold rows.** One `[cold]` row per read case, gated by `shared/src/measure.py:assess_cache`; always `INELIGIBLE` with `required_domains` and the reason. No row is labelled cold.
- **Attribution.** CLI rows carry per-call CPU and max RSS (`os.wait4` rusage) and a `dispatch` step time from `LAYERFS_TRACE`/`LAYERFS_TRACE_STEP` (the native route writes `dispatch` only; `route`/`connect`/`request` are `UNAVAILABLE`). SDK rows carry `process.cpuUsage()` / `memoryUsage()` deltas per case. PostgreSQL rows reset `pg_stat_statements` before each case and carry the top statements per call (`pg_statements`; this path needs a server and is untested without one).
- **Content transport.** CLI writes pass content with `--from <file>` (staged before the clock starts), not stdin.

## Run

`--source` is the **full 40-hex commit** and must equal `HEAD` of `--source-dir`. `--node-pkg` is the package **entry file** (`api/node/src/index.js`), not its directory; the native addon is read from `api/node/layerfs.node` (or `LAYERFS_NATIVE`) and its sha256 is recorded. Run under an outer timeout, writing local receipts (`results.json`, `results.csv`, never committed) to an ignored folder and publishing the report under `result/YYYY-MM-DD/fs-file-calls/<full-sha>/report.md`:

```sh
python3 -I fs-file-calls/run.py   --cli /absolute/path/to/layerfs   --node-pkg /absolute/path/to/layerfs/api/node/src/index.js   --source-dir /absolute/path/to/layerfs   --source FULL_40_CHAR_SHA   --trees F100,F1k,F10k --h-depths 10,100 --big-write-mib 64   --pg-admin-url postgresql://postgres@127.0.0.1:55432/postgres?sslmode=disable   --pg-user layerfs_pg --pg-password layerfs-test-pw   --output fs-file-calls/receipts/run1   --report result/2026-11-22/fs-file-calls/FULL_40_CHAR_SHA/report.md
python3 -I fs-file-calls/check_results.py fs-file-calls/receipts/run1/results.json
python3 -I fs-file-calls/test_harness.py   # offline tests of the row wrapper and the checker
```

Flags: `--n-read` (15), `--n-write` (10), `--trees`, `--h-depths` (default: `--h-depth`, 50), `--big-write-mib` (0 = off), `--write-ladder-mib` (16,64,256), `--apply-rows` (1000,8191,8192), `--node-arm-timeout` (1800 s), `--pg-admin-url` (empty = PostgreSQL arms are `NOT_RUN`). `F100k` and `H1000` are slow; keep them out of quick runs.

## Past runs

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-25 | `ca4be0bf3c` | PARTIAL (diagnostic warm): measured the mountless LayerFS 2.0 `file.*` + `commit.diff` calls across CLI and persistent `@layerfs/node` SDK on native SQLite (ext4) and PostgreSQL 18.7 (Debian 18.7-1.pgdg13+5) (file.stat (F1k) p50: SQLite SDK `2.085 ms`, SQLite CLI `8.473 ms`, PG SDK `24.722 ms`, PG CLI `56.207 ms`); rows by status: FAIL 2, NOT_RUN 10, OK 235, REFUSED 8; 160 cold rows registered as INELIGIBLE (no cold claim); fixture and export proofs passed; 3 unavailable routes recorded as NOT_RUN | [report](../result/2026-11-25/fs-file-calls/ca4be0bf3c4e9df47f9b21caca46cdb1faee48fe/report.md) |
| 2026-11-22 | `54937e6434` | PASS (diagnostic warm): measured all 15 mountless LayerFS 2.0 `file.*` + `commit.diff` calls across CLI and persistent `@layerfs/node` SDK on native SQLite (ext4) and PostgreSQL 18.6 (F1k `file.stat` p50: SQLite SDK `5.104 ms` vs CLI `17.042 ms`, PG18 SDK `15.822 ms`; independent export SHA-256 proofs passed; 3 unavailable worker routes recorded as NOT_RUN) | [report](../result/2026-11-22/fs-file-calls/54937e64348dc8c2c801fc6d98db28b995a48ac8/report.md) |
<!-- runs:end -->
