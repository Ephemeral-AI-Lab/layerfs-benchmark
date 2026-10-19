# dsh-dedup release data

> **Status:** Current general guide.

One folder per release with dsh-dedup results: a LayerFS Workspace walks the
157-checkpoint DeepSeek-harness history (every 100th of 15,632 Commits,
4,936,693,030 logical bytes) at stride 10, 3 and 1, committing each state
through the public JS SDK, and the closed Store is weighed against a Git pack
of the same trees. The harness is [benchmark/dsh-dedup](../../dsh-dedup/README.md).

| Release | Stride | States | Store allocated | Git pack + index | Σ Commit | History proof |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| [v1.0.0](v1.0.0/) | 10 | 17 | 53,125,120 B | 41,797,536 B | 22.4 s | 16 / 16 |
| | 3 | 53 | 69,455,872 B | 48,169,384 B | 45.1 s | 52 / 52 |
| | 1 | 157 | 100,085,760 B | 55,068,665 B | 97.9 s | 156 / 156 |

v1.0.0 has an open [storage regression](v1.0.0/storage-regression.md)
against the 2026-10-07 in-process history results (+4.8% / +8.1% / +17.5%;
stride 1 above the old approved ceiling). The owner accepted the results as
recorded.

Each folder holds:

| File | What it is |
| --- | --- |
| `benchmark-storage.csv` | One row per stride: logical bytes, Store allocated / payload / metadata / other, Git pack and index, ratios, the 2026-10-07 value and old ceiling |
| `benchmark-performance.csv` | One row per stride: Init, Σ / mean / max Commit, Σ apply, Σ verify (live and from history), segments, history proof, Git repack time |
| `environment.csv` | Source, binaries, images, Store policy, route, corpus, Git, host, load |
| `s<stride>/` | That stride's receipts, unchanged: `identity.txt`, `deploy.env`, `selection.json`, `commands.log`, `ledger.jsonl`, `segments.jsonl`, `history.jsonl`, `commits.json`, `store-files.txt`, `store.json`, `states.csv`, `summary.json`, the Git reference `git-reference.json`, and the run's `record.md` |
| `probe-record.md` | The five-state probe that chose the route |
| `storage-regression.md` | The open storage regression |

The CSVs are derived from the receipts (`summary.json`, `store.json`,
`history.jsonl`, `git-reference.json`); everything else is copied unchanged
from `benchmark-results/dsh-dedup/`. Records' relative links point into
`benchmark/dsh-dedup/records/`.

v1.0.0 was measured at `main` `e5c7aaae05` (the fs-bench v1.0.0 build) on
Docker Desktop on an arm64 Mac at 1-minute load 6–13, one sample per
stride, Disposable Store with policy 16/8/8. The stride-3 `commits.json`
lists 47 of its 52 Commits (a harness bug fixed before stride 1; see that
record); its ledger and history proof cover all 52. Not a qualifying result
for a native x86-64 Linux host.

To add a release, create `v<version>/` with the same files from that
release's runs, copied unchanged from `benchmark-results/dsh-dedup/<run>/`.
