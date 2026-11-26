# layerfs-benchmark

Benchmarks for [LayerFS](https://github.com/Ephemeral-AI-Lab/layerfs), each
with its latest published run. Read [AGENTS.md](AGENTS.md) before running any
of them.

Each benchmark belongs to one **group** and lists what it **measures**:
`correctness` (behaves as it should, PASS/FAIL), `speed` (operation times),
`storage` (bytes stored per byte written) or `recovery` (survives failures
and restores intact). Speed timings are diagnostic unless a report says
otherwise. A benchmark's README has its setup and every past run.

<!-- index:begin -->
## Filesystem

The LayerFS engine: Workspaces, file I/O, metadata and Commit.

| Benchmark | Measures | What it checks | Latest run |
| --- | --- | --- | --- |
| [doctor-integration](doctor-integration/) | correctness | backend correctness qualification | 2026-11-08 · `6b964078` · Outcome: PASS for the specified Doctor backend contract · [report](result/2026-11-08/doctor-integration/6b9640783c4652b7ad662d9610ab8a89670a7d85/report.md) |
| [doctor-postgresql](doctor-postgresql/) | correctness | PostgreSQL Doctor backend qualification | 2026-11-08 · `c011512b` · PASS: 27 PostgreSQL Doctor backend tests passed against actual owned PostgreSQL 17.11 primary/physical-standby fixtures, including TLS, corruption, privileges and cancellation · [report](result/2026-11-08/doctor-postgresql/c011512bc129803215e33d0b7f93ac1becccc68a/report.md) |
| [doctor-runtime](doctor-runtime/) | correctness | real Doctor runtime and S3 qualification | 2026-11-08 · `6b964078` · PASS — B6 Doctor expectations passed, including the integrated Linux worker and full/quick SQLite routes; an independent native NFS teardown failure remains preserved in issue #136 · [report](result/2026-11-08/doctor-runtime/6b9640783c4652b7ad662d9610ab8a89670a7d85/report.md) |
| [fio](fio/) | speed | buffered sequential and random file I/O | 2026-11-06 · `76a32a9a` (pgr2-six) · Diagnostic terminal: INCOMPLETE. 36 registered rows; execution {'PASS': 36}. Final infrastructure cleanup: INCOMPLETE · [report](result/2026-11-06/fio/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md) |
| [fs-bench-cloudflare-computer](fs-bench-cloudflare-computer/) | speed | Cloudflare's fs-bench.sh on LayerFS | 2026-11-07 · `85a0865c` · 8 of 8 rows ran all twelve scenarios (8 PASS); final cleanup COMPLETE · [report](result/2026-11-07/fs-bench-cloudflare-computer/85a0865cde92f1d85a4e8bf402c597c935ff8db6/report.md) |
| [fs-bench-pro](fs-bench-pro/) | speed, correctness | cold project export from each machine into a host folder | 2026-11-08 · `4cd63f16` · Export works from all four machines into a host folder: 7 of 8 samples completed with exact content (6 QUALIFIED, native E01 OVER_BUDGET under the first harness rule); Apple Container E01 FAILED mid-stream · [report](result/2026-11-08/fs-bench-pro/4cd63f16ddbea5791c88fe34be369de27bcfff81/report.md) |
| [fs-bench-quick](fs-bench-quick/) | speed | CLI case times for eighteen small file workloads | 2026-11-06 · `76a32a9a` (pgr2-final) · Diagnostic terminal: INCOMPLETE. 162 registered rows; execution {'PASS': 162}. Final infrastructure cleanup: INCOMPLETE · [report](result/2026-11-06/fs-bench-quick/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-final/report.md) |
| [fs-file-calls](fs-file-calls/) | speed, storage, correctness | mountless file call family latency, throughput and storage growth | 2026-11-25 · `ca4be0bf` · PARTIAL (diagnostic warm): measured the mountless LayerFS 2.0 `file.*` + `commit.diff` calls across CLI and persistent `@layerfs/node` SDK on native SQLite (ext4) and PostgreSQL 18.7 (Debian 18.7-1.pgdg13+5) and the docker machine's worker (SQLite) (file.stat (F1k) p50: SQLite SDK `2.126 ms`, SQLite CLI `8.525 ms`, PG SDK `25.106 ms`, PG CLI `59.652 ms`, docker-route SDK `3.16 ms`, docker-route CLI `5.218 ms`); rows by status: FAIL 2, NOT_RUN 10, OK 321, REFUSED 8; 222 cold rows registered as INELIGIBLE (no cold claim); fixture and export proofs passed; 2 unavailable routes recorded as NOT_RUN · [report](result/2026-11-25/fs-file-calls/ca4be0bf3c4e9df47f9b21caca46cdb1faee48fe/report.md) |
| [fs-storage-dsh](fs-storage-dsh/) | storage | Store bytes for a real repository history replayed through Workspace Commits | 2026-11-06 · `6d820c75` · 4 of 4 rows PASS (applied, committed, measured and verified at state 157); net Store bytes D10 56,139,776 B SQLite / 69,967,872 B PostgreSQL, D03 73,015,296 B / 93,388,800 B, against a Git pack + idx of 41,805,317 / 48,166,223 B; final cleanup COMPLETE · [report](result/2026-11-06/fs-storage-dsh/6d820c756b9b12541ac84af7b88467069f31bcbf/report.md) |
| [fs-storage-history](fs-storage-history/) | storage | Store bytes by history shape: long history, branches, forks and projects | 2026-11-06 · `6d820c75` · All 14 rows (7 cases × Docker × SQLite, PostgreSQL) PASS with every Branch head verified (171 heads per backend); 50 identical Branches cost ≈ 5.3 KB of metadata each, 20 projects in separate Stores need 17.1× (SQLite) / 11.2× (PostgreSQL) the net bytes of one shared Store, and 500 Commits add a flat ≈ 3.4 KB of packs each; final cleanup COMPLETE · [report](result/2026-11-06/fs-storage-history/6d820c756b9b12541ac84af7b88467069f31bcbf/report.md) |
| [fs-storage-micro](fs-storage-micro/) | storage | Store bytes for one LayerFS storage mechanism per case | 2026-11-06 · `6d820c75` · 16 of 16 fs-storage-micro rows PASS with verified final state; repeat M03/docker/postgresql/r2: page-granular Store bytes identical in this repeat, total +0 B, per-Commit new_stored ±25 B; repeat M03/docker/sqlite/r2: page-granular Store bytes identical in this repeat, total -8,240 B, per-Commit new_stored ±15 B; final cleanup COMPLETE · [report](result/2026-11-06/fs-storage-micro/6d820c756b9b12541ac84af7b88467069f31bcbf/report.md) |
| [fs-storage-quick](fs-storage-quick/) | storage | quick Store-bytes gate for LayerFS storage optimizations, SQLite and PostgreSQL | 2026-11-06 · `7691ac20` · 12 of 12 fs-storage-quick rows PASS with verified final state on final integration 7691ac20b0 (= 8b701f42f0 + #92 + #91 + #90, PRs pending owner merge); against the Phase 0 baseline b4fa173e40 every row is smaller or within noise on SQLite file+WAL, SQLite late and PostgreSQL schema bytes (Q1 SQLite 8,798,208 → 4,538,368 B, Q6 PostgreSQL 38,158,336 → 25,640,960 B), and against the Phase 2 baseline 02133596ae there are no regressions; cleanup COMPLETE · [report](result/2026-11-06/fs-storage-quick/7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3/report.md) |
| [fsstress](fsstress/) | correctness | random concurrent filesystem operations | 2026-11-06 · `76a32a9a` (pgr2-six) · Diagnostic terminal: INCOMPLETE. 9 registered rows; execution {'PASS': 2, 'FAIL': 7}. Final infrastructure cleanup: INCOMPLETE · [report](result/2026-11-06/fsstress/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md) |
| [fsx](fsx/) | correctness | random file reads, writes and truncates checked by fsx itself | 2026-11-06 · `76a32a9a` (pgr2-six) · Diagnostic terminal: INCOMPLETE. 9 registered rows; execution {'PASS': 9}. Final infrastructure cleanup: INCOMPLETE · [report](result/2026-11-06/fsx/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md) |
| [mdtest](mdtest/) | speed | create, stat and remove 512 empty files or directories | 2026-11-06 · `76a32a9a` (pgr2-six) · Diagnostic terminal: INCOMPLETE. 18 registered rows; execution {'PASS': 4, 'NOT_RUN': 14}. Final infrastructure cleanup: INCOMPLETE · [report](result/2026-11-06/mdtest/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md) |
| [pjdfstest](pjdfstest/) | correctness | POSIX file semantics, unprivileged subset | 2026-11-06 · `76a32a9a` (pgr2-six) · Diagnostic terminal: INCOMPLETE. 36 registered rows; execution {'PASS': 36}. Final infrastructure cleanup: INCOMPLETE · [report](result/2026-11-06/pjdfstest/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md) |
| [sdk-branch-file](sdk-branch-file/) | correctness | saved branch/file API route conformance | 2026-11-08 · `91a59406` · PASS: all 101 CLI-only qualification operations and 588 separate product front-end outcomes passed on final source across native SQLite, native PostgreSQL and worker SQLite · [report](result/2026-11-08/sdk-branch-file/91a5940605576322255a722663a6b956acd0b1c5/report.md) |
| [smallfile](smallfile/) | speed | two-worker small-file create, read, stat, rename and delete | 2026-11-06 · `76a32a9a` (pgr2-six) · Diagnostic terminal: INCOMPLETE. 45 registered rows; execution {'PASS': 45}. Final infrastructure cleanup: INCOMPLETE · [report](result/2026-11-06/smallfile/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md) |

## Transfer

Connect: moving Stores between a home and a bucket.

| Benchmark | Measures | What it checks | Latest run |
| --- | --- | --- | --- |
| [backup-verify](backup-verify/) | correctness, recovery | backup and restore on MinIO and R2 under failures | 2026-11-06 · `7691ac20` · Outcome: PASS on MinIO, 51 of 51 checks: schema v2 Stores round-trip, and a schema v1 backup is refused at open until migrated · [report](result/2026-11-06/backup-verify/7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3/report.md) |
| [store-transfer](store-transfer/) | correctness, recovery, speed | moving a SQLite Store between a home and a machine | 2026-11-08 · `ab4c1a47` · Outcome: PASS on every Store-transfer route, refusal, recovery path and the guide at layerfs `ab4c1a4712` (Ephemeral-AI-Lab/layerfs#617, merged into `layerfs_v2_0_0` as `716197c499` with the same tree), and every Apple Container pull now succeeds on its first attempt · [report](result/2026-11-08/store-transfer/ab4c1a4712ec0e4d032a2ac341638053a02e2c91/report.md) |
<!-- index:end -->

## Layout

| Path | What it is |
| --- | --- |
| `<benchmark>/` | one benchmark: README, harness, cases |
| [shared/](shared/) | the runner the filesystem benchmarks share, and the index script |
| [result/](result/README.md) | published reports, `result/<date>/<benchmark>/<full LayerFS commit>/report.md`, and the rules for them |
| `.archive/` | retired suites and released data from before 2026-11-06; frozen |

The tables above are generated. After publishing a report, run
`python3 shared/src/readme_index.py`; `--check` reports stale tables.
