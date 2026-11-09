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
| [fio](fio/) | speed | buffered sequential and random file I/O | 2026-11-06 · `76a32a9a` (pgr2-six) · Diagnostic terminal: INCOMPLETE. 36 registered rows; execution {'PASS': 36}. Final infrastructure cleanup: INCOMPLETE · [report](result/2026-11-06/fio/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md) |
| [fs-bench-cloudflare-computer](fs-bench-cloudflare-computer/) | speed | Cloudflare's fs-bench.sh on LayerFS | 2026-11-08 · `98ebfdfb` · 4 of 8 rows ran all twelve scenarios (4 NOT_RUN, 4 PASS); final cleanup COMPLETE · [report](result/2026-11-08/fs-bench-cloudflare-computer/98ebfdfb96fcb88a1c7275c4323e1a387349a219/report.md) |
| [fs-bench-quick](fs-bench-quick/) | speed | CLI case times for eighteen small file workloads | 2026-11-06 · `76a32a9a` (pgr2-final) · Diagnostic terminal: INCOMPLETE. 162 registered rows; execution {'PASS': 162}. Final infrastructure cleanup: INCOMPLETE · [report](result/2026-11-06/fs-bench-quick/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-final/report.md) |
| [fs-storage-dsh](fs-storage-dsh/) | storage | Store bytes for a real repository history replayed through Workspace Commits | 2026-11-06 · `7691ac20` · 4 of 4 rows PASS (applied, committed, measured and verified at state 157); net Store bytes D10 47,927,296 B SQLite / 53,272,576 B PostgreSQL, D03 61,014,016 B / 68,419,584 B, against a Git pack + idx of 41,805,317 / 48,166,223 B; final cleanup COMPLETE · [report](result/2026-11-06/fs-storage-dsh/7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3/report.md) |
| [fs-storage-history](fs-storage-history/) | storage | Store bytes by history shape: long history, branches, forks and projects | 2026-11-06 · `7691ac20` · All 14 rows (7 cases × Docker × SQLite, PostgreSQL) PASS with every Branch head verified on final integration 7691ac20b0 (= 8b701f42f0 + #92 + #91 + #90, PRs pending owner merge); against the Phase 0 reference b4fa173e40, net Store bytes fell in every comparable row (SQLite −2.93 % … −17.93 %, PostgreSQL −18.03 % … −53.26 %), Σ new_metadata fell 19–41 % with payload unchanged, and PostgreSQL ÷ SQLite is now 1.07–1.10× in every case (Phase 0: 1.11–2.22×). Final cleanup COMPLETE · [report](result/2026-11-06/fs-storage-history/7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3/report.md) |
| [fs-storage-micro](fs-storage-micro/) | storage | Store bytes for one LayerFS storage mechanism per case | 2026-11-06 · `7691ac20` · 16 of 16 fs-storage-micro rows PASS with verified final state; repeat M03/docker/postgresql/r2: page-granular Store bytes identical in this repeat, total +0 B, per-Commit new_stored ±15 B; repeat M03/docker/sqlite/r2: Store pages DIFFER, total +8,192 B, per-Commit new_stored ±14 B; final cleanup COMPLETE · [report](result/2026-11-06/fs-storage-micro/7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3/report.md) |
| [fs-storage-quick](fs-storage-quick/) | storage | quick Store-bytes gate for LayerFS storage optimizations, SQLite and PostgreSQL | 2026-11-06 · `7691ac20` · 12 of 12 fs-storage-quick rows PASS with verified final state on final integration 7691ac20b0 (= 8b701f42f0 + #92 + #91 + #90, PRs pending owner merge); against the Phase 0 baseline b4fa173e40 every row is smaller or within noise on SQLite file+WAL, SQLite late and PostgreSQL schema bytes (Q1 SQLite 8,798,208 → 4,538,368 B, Q6 PostgreSQL 38,158,336 → 25,640,960 B), and against the Phase 2 baseline 02133596ae there are no regressions; cleanup COMPLETE · [report](result/2026-11-06/fs-storage-quick/7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3/report.md) |
| [fsstress](fsstress/) | correctness | random concurrent filesystem operations | 2026-11-06 · `76a32a9a` (pgr2-six) · Diagnostic terminal: INCOMPLETE. 9 registered rows; execution {'PASS': 2, 'FAIL': 7}. Final infrastructure cleanup: INCOMPLETE · [report](result/2026-11-06/fsstress/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md) |
| [fsx](fsx/) | correctness | random file reads, writes and truncates checked by fsx itself | 2026-11-06 · `76a32a9a` (pgr2-six) · Diagnostic terminal: INCOMPLETE. 9 registered rows; execution {'PASS': 9}. Final infrastructure cleanup: INCOMPLETE · [report](result/2026-11-06/fsx/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md) |
| [juicefs-bench](juicefs-bench/) | speed | large-file, small-file and stat throughput with JuiceFS bench | 2026-11-09 · `833d04cf` · LayerFS/SQLite execution PASS; JuiceFS/PG16 execution PASS; timings INELIGIBLE diagnostics; final cleanup COMPLETE · [report](result/2026-11-09/juicefs-bench/833d04cf44e8e747929d50ab1170a48260d9381c/report.md) |
| [mdtest](mdtest/) | speed | create, stat and remove 512 empty files or directories | 2026-11-06 · `76a32a9a` (pgr2-six) · Diagnostic terminal: INCOMPLETE. 18 registered rows; execution {'PASS': 4, 'NOT_RUN': 14}. Final infrastructure cleanup: INCOMPLETE · [report](result/2026-11-06/mdtest/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md) |
| [pjdfstest](pjdfstest/) | correctness | POSIX file semantics, unprivileged subset | 2026-11-06 · `76a32a9a` (pgr2-six) · Diagnostic terminal: INCOMPLETE. 36 registered rows; execution {'PASS': 36}. Final infrastructure cleanup: INCOMPLETE · [report](result/2026-11-06/pjdfstest/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md) |
| [smallfile](smallfile/) | speed | two-worker small-file create, read, stat, rename and delete | 2026-11-06 · `76a32a9a` (pgr2-six) · Diagnostic terminal: INCOMPLETE. 45 registered rows; execution {'PASS': 45}. Final infrastructure cleanup: INCOMPLETE · [report](result/2026-11-06/smallfile/76a32a9a10e7b7b1379699ece52d45e233da5a50/pgr2-six/report.md) |

## Transfer

Connect: moving Stores between a home and a bucket.

| Benchmark | Measures | What it checks | Latest run |
| --- | --- | --- | --- |
| [backup-verify](backup-verify/) | correctness, recovery | backup and restore on MinIO and R2 under failures | 2026-11-06 · `7691ac20` · Outcome: PASS on MinIO, 51 of 51 checks: schema v2 Stores round-trip, and a schema v1 backup is refused at open until migrated · [report](result/2026-11-06/backup-verify/7691ac20b0a8c8b741dd2b701e7aa77b63aaa8a3/report.md) |
| [store-transfer](store-transfer/) | correctness, recovery, speed | moving a SQLite Store between a home and a machine | 2026-11-08 · `d8dddd50` · Outcome: PASS on every Store-transfer route, refusal and recovery path of layerfs-project #8–#13 at the fixed build · [report](result/2026-11-08/store-transfer/d8dddd50d04c92e4656131e71273fbe0bac0daae/report.md) |
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
