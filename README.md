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
| [fio](fio/) | speed | buffered sequential and random file I/O | 2026-11-06 · `b919f50e` · Diagnostic terminal: PASS · [report](result/2026-11-06/fio/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) |
| [fs-bench-cloudflare-computer](fs-bench-cloudflare-computer/) | speed | Cloudflare's fs-bench.sh on LayerFS | 2026-11-06 · `6d820c75` · 8 of 8 rows ran all twelve scenarios (8 PASS); final cleanup COMPLETE · [report](result/2026-11-06/fs-bench-cloudflare-computer/6d820c756b9b12541ac84af7b88467069f31bcbf/report.md) |
| [fs-bench-quick](fs-bench-quick/) | speed | CLI case times for eighteen small file workloads | 2026-11-06 · `b919f50e` · 96/96 CLI execution checks passed. Case and final runtime cleanup: COMPLETE · [report](result/2026-11-06/fs-bench-quick/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) |
| [fs-storage-dsh](fs-storage-dsh/) | storage | Store bytes for a real repository history replayed through Workspace Commits | 2026-11-06 · `6d820c75` · 4 of 4 rows PASS (applied, committed, measured and verified at state 157); net Store bytes D10 56,139,776 B SQLite / 69,967,872 B PostgreSQL, D03 73,015,296 B / 93,388,800 B, against a Git pack + idx of 41,805,317 / 48,166,223 B; final cleanup COMPLETE · [report](result/2026-11-06/fs-storage-dsh/6d820c756b9b12541ac84af7b88467069f31bcbf/report.md) |
| [fs-storage-history](fs-storage-history/) | storage | Store bytes by history shape: long history, branches, forks and projects | 2026-11-06 · `6d820c75` · All 14 rows (7 cases × Docker × SQLite, PostgreSQL) PASS with every Branch head verified (171 heads per backend); 50 identical Branches cost ≈ 5.3 KB of metadata each, 20 projects in separate Stores need 17.1× (SQLite) / 11.2× (PostgreSQL) the net bytes of one shared Store, and 500 Commits add a flat ≈ 3.4 KB of packs each; final cleanup COMPLETE · [report](result/2026-11-06/fs-storage-history/6d820c756b9b12541ac84af7b88467069f31bcbf/report.md) |
| [fs-storage-micro](fs-storage-micro/) | storage | Store bytes for one LayerFS storage mechanism per case | 2026-11-06 · `6d820c75` · 16 of 16 fs-storage-micro rows PASS with verified final state; repeat M03/docker/postgresql/r2: page-granular Store bytes identical in this repeat, total +0 B, per-Commit new_stored ±25 B; repeat M03/docker/sqlite/r2: page-granular Store bytes identical in this repeat, total -8,240 B, per-Commit new_stored ±15 B; final cleanup COMPLETE · [report](result/2026-11-06/fs-storage-micro/6d820c756b9b12541ac84af7b88467069f31bcbf/report.md) |
| [fs-storage-quick](fs-storage-quick/) | storage | quick Store-bytes gate for LayerFS storage optimizations, SQLite and PostgreSQL | 2026-11-06 · `b4fa173e` · 12 of 12 fs-storage-quick rows PASS with verified final state on the base build, pinned as the #84 baseline; matrix wall SQLite 52.9 s and PostgreSQL 117.4 s (INELIGIBLE, target ≤ 120 s per backend); after the late probe every SQLite Store had 0 B of WAL (Q1 8,798,208 → 4,796,416 B net) and Q6 PostgreSQL shrank 38,158,336 → 31,358,976 B; a same-build repeat stayed within noise; cleanup COMPLETE · [report](result/2026-11-06/fs-storage-quick/b4fa173e401fc87af6610c151225096288e4ba57/report.md) |
| [fsstress](fsstress/) | correctness | random concurrent filesystem operations | 2026-11-06 · `b9ad9edd` · Diagnostic terminal: PASS · [report](result/2026-11-06/fsstress/b9ad9edd7ea3a9314625dee53466aa59a7ea69c7/report.md) |
| [fsx](fsx/) | correctness | random file reads, writes and truncates checked by fsx itself | 2026-11-06 · `b919f50e` · Diagnostic terminal: PASS · [report](result/2026-11-06/fsx/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) |
| [mdtest](mdtest/) | speed | create, stat and remove 512 empty files or directories | 2026-11-06 · `b919f50e` · Diagnostic terminal: PASS · [report](result/2026-11-06/mdtest/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) |
| [pjdfstest](pjdfstest/) | correctness | POSIX file semantics, unprivileged subset | 2026-11-06 · `b919f50e` · Diagnostic terminal: PASS · [report](result/2026-11-06/pjdfstest/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) |
| [smallfile](smallfile/) | speed | two-worker small-file create, read, stat, rename and delete | 2026-11-06 · `b919f50e` · Diagnostic terminal: PASS · [report](result/2026-11-06/smallfile/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) |

## Transfer

Connect: moving Stores between a home and a bucket.

| Benchmark | Measures | What it checks | Latest run |
| --- | --- | --- | --- |
| [backup-verify](backup-verify/) | correctness, recovery | backup and restore on MinIO and R2 under failures | 2026-11-06 · `c51d04b9` · Outcome: PASS on both providers after three product fixes · [report](result/2026-11-06/backup-verify/c51d04b9428c4d56df690223ced1e3fe20f73dc2/report.md) |
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
