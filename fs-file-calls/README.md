# fs-file-calls — mountless file call family latency, throughput and storage growth
> group: filesystem · measures: speed, storage, correctness

Measures the mountless LayerFS 2.0 `file` call family (`read`, `stat`, `list`,
`glob`, `grep`, `blame`, `history`, `write`, `edit`, `apply`, `cp`, `mv`, `rm`,
`mkdir`) plus `commit.diff` (which replaced 1.x `file.diff` in 2.0).

Compares:
- **Front end**: CLI (fresh `layerfs` process per call, matching `dsh-layerfs`) vs persistent Node SDK (`@layerfs/node` `client({ home })`).
- **Route / backend**: native SQLite (`ext4`), native PostgreSQL (`18.6`, with `pg_stat_statements`), and worker routes (`docker`, `lima`, `apple-container` — registered as `NOT_RUN` when unavailable on the host).
- **Scale & history**: trees `F100`, `F1k`, `F10k` (depth `<= 6`); file sizes `0 B`, `1 KiB`, `64 KiB`, `1 MiB`, `16 MiB`; history depths `H1`, `H100` (and optional `H1000`).
- **Concurrency**: 1, 4, and 8 parallel readers; parallel writers on separate Branches and on one Branch, recording every `Busy` / `Conflict` / `Failed` refusal by code.
- **Independent proof**: write results verified via subsequent `file.read`/`file.stat` and `project.export` SHA-256 tree hash; read results verified against the fixture manifest.

Run under an outer timeout, writing local receipts to an ignored folder and publishing the report under `result/YYYY-MM-DD/fs-file-calls/<full-sha>/report.md`:

```sh
python3 fs-file-calls/run.py \
  --cli /absolute/path/to/layerfs \
  --node-pkg /absolute/path/to/layerfs/api/node/src/index.js \
  --source-dir /absolute/path/to/layerfs \
  --source FULL_40_CHAR_SHA \
  --pg-admin-url postgresql://postgres@127.0.0.1:55432/postgres?sslmode=disable \
  --pg-user layerfs_pg --pg-password layerfs-test-pw \
  --output fs-file-calls/receipts/run1 \
  --report result/2026-11-22/fs-file-calls/FULL_40_CHAR_SHA/report.md
```

## Past runs

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-22 | `54937e6434` | PASS (diagnostic warm): measured all 15 mountless LayerFS 2.0 `file.*` + `commit.diff` calls across CLI and persistent `@layerfs/node` SDK on native SQLite (ext4) and PostgreSQL 18.6 (F1k `file.stat` p50: SQLite SDK `5.104 ms` vs CLI `17.042 ms`, PG18 SDK `15.822 ms`; independent export SHA-256 proofs passed; 3 unavailable worker routes recorded as NOT_RUN) | [report](../result/2026-11-22/fs-file-calls/54937e64348dc8c2c801fc6d98db28b995a48ac8/report.md) |
<!-- runs:end -->
