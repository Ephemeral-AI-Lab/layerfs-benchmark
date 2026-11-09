# juicefs-bench — large-file, small-file and stat throughput with JuiceFS bench
> group: filesystem · measures: speed

Runs the unmodified JuiceFS Community Edition benchmark against a LayerFS
Workspace. The LayerFS arm only needs the JuiceFS executable; the separate
JuiceFS/PG16 baseline below mounts JuiceFS itself. Read [AGENTS.md](AGENTS.md)
before preparing a campaign.

| Setting | Value |
| --- | --- |
| Tool | JuiceFS v1.4.2, Linux ARM64 for the initial campaign |
| LayerFS | Latest `layerfs_v2_0_0`, resolved and pinned per campaign |
| Initial selection | Docker, SQLite, disposable Store |
| Concurrency | 4 workers |
| Large files | 4 × 1 GiB, 1 MiB I/O |
| Small files | 400 × 128 KiB, 100 files per worker |
| Metrics | Large write/read MiB/s; small write/read/stat files/s |
| Cache | Purge disabled; all timings INELIGIBLE diagnostics |
| Verification | UNVERIFIED; the tool deletes its output |

The initial 25 s campaign timed out. The owner authorized a separate campaign
with a 60 s lifecycle limit on 2026-11-09; Docker/SQLite completed all five
phases in that campaign. The report preserves both attempts and their unchanged
artifact/workload identities. The 60 s exception is recorded in its environment
as `budget_exceptions.docker`, with the owner's approval and reason.

The owner also selected an actual JuiceFS/PG16 baseline. It uses the same
JuiceFS v1.4.2 binary/client image and four-worker workload on the same Docker
VM, with dedicated PostgreSQL 16.15 metadata and local-file object data/cache.
Compression is none, writeback is disabled, the buffer is 300 MiB and disk-cache
limit 100 GiB; the fresh filesystem has trash disabled. PostgreSQL retains its
default durability settings. The samples are diagnostic and not a matched
durability or cold-cache comparison; no LayerFS rerun is needed.

With the pinned client image already installed, pull PG16 once and resolve its
immutable image ID, then use [src/juicefs_pg.py](src/juicefs_pg.py):

```bash
python3 juicefs-bench/src/juicefs_pg.py prepare --root /absolute/fresh-pg16-run \
  --pg-image sha256:PINNED_PG16_IMAGE
python3 juicefs-bench/src/juicefs_pg.py run --root /absolute/fresh-pg16-run
python3 juicefs-bench/src/juicefs_pg.py finish --root /absolute/fresh-pg16-run
```

The runner owns two containers, two data volumes and an internal Docker network;
it records allocation intent, exact IDs, settings, mount proof and tool source.
It refuses workload replay and checks resource owner labels before cleanup.
Setup is outside its 60 s benchmark Exec timer. Add `--juicefs-pg
/absolute/fresh-pg16-run/state.json` to the report command to include the baseline
and diagnostic throughput ratios. The report validates tool/image/workload
identity against the LayerFS arm and lists the baseline first.

Prepare matching release CLI, Linux daemon and bundle using the product's private
worktree launcher. Put a checksum-pinned JuiceFS binary in the Sandbox image
outside the Workspace. [image/Dockerfile](image/Dockerfile) accepts the base image
and binary hash explicitly; its context must contain the downloaded `juicefs`.
Use a private home and XDG cache, and an empty source directory. Record the
ready Docker machine and exact owned infrastructure release commands in a private
environment JSON based on [environments.example.json](environments.example.json).

```bash
python3 juicefs-bench/src/run.py prepare --environment /absolute/environment.json \
  --cache /absolute/campaign --case J01 --machine docker --backend sqlite
python3 juicefs-bench/src/run.py run --environment /absolute/environment.json \
  --cache /absolute/campaign --case J01 --machine docker --backend sqlite \
  --output /absolute/fresh-output
python3 juicefs-bench/src/run.py finish --environment /absolute/environment.json \
  --cache /absolute/campaign
python3 juicefs-bench/src/report.py --environment /absolute/environment.json \
  --cache /absolute/campaign --output result/YYYY-MM-DD/juicefs-bench/FULL_SHA/report.md
python3 shared/src/readme_index.py
```

When updating the single report after an explicitly authorized new campaign,
pass `--previous-cache` and `--previous-environment` for the earlier attempt.
The reporter checks source, artifact and workload identity equality and keeps
the earlier failure visible. Retain the previous report text locally before
updating the published report; never overwrite its raw receipts.

One attempt per arm; the shared runner rejects replay. Do not pass `--matrix`
unless the larger selection has actually been prepared. Parser checks validate
results, not filesystem contents:

```bash
python3 -c 'import subprocess,sys; sys.exit(subprocess.run([sys.executable,"-m","unittest","discover","-s","juicefs-bench/tests"],timeout=30).returncode)'
```

The internal benchmark writes then reads its own files. It neither measures a
LayerFS Commit of that dataset nor guarantees durable writes; its repeated random
block also affects compression/deduplication. A separate retained-file workload
is needed for Commit or cold committed-read measurements. `fio` is a separate suite.

Sources: [benchmark guide](https://juicefs.com/docs/community/performance_evaluation_guide/),
[v1.4.2 implementation](https://github.com/juicedata/juicefs/blob/v1.4.2/cmd/bench.go).

## Past runs

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-09 | `833d04cf44` | LayerFS/SQLite execution PASS; JuiceFS/PG16 execution PASS; timings INELIGIBLE diagnostics; final cleanup COMPLETE | [report](../result/2026-11-09/juicefs-bench/833d04cf44e8e747929d50ab1170a48260d9381c/report.md) |
<!-- runs:end -->
