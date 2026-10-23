# layerfs-benchmark

Benchmark suites, harnesses and released results for
[LayerFS](https://github.com/Ephemeral-AI-Lab/layerfs). This was the
`benchmark/` folder of the layerfs repository until 2026-10-23. Its history
was carried over: every commit that changed `benchmark/` is here, with its
original author, date and message.

Read [AGENTS.md](AGENTS.md) before any measurement. The measurement rules
themselves stay in layerfs (its root `AGENTS.md` §1–3 and `docs/general/`).

| Path | What it is |
| --- | --- |
| [data/](data/) | Released results, one folder per suite and version (`data/<suite>/v<version>/`). The LayerFS website reads it. |
| [fs-bench/](fs-bench/README.md) | Cloudflare Computer's `fs-bench.sh`, run against Computer and LayerFS as a pair |
| `fio/`, `fsstress/`, `fsx/`, `mdtest/`, `pjdfstest/`, `smallfile/`, `dsh-dedup/` | Per-suite clients and scripts |
| `common/` | Shared helpers |
| [fs-bench-pro/](fs-bench-pro/AGENTS.md) | **Frozen and broken** (owner, 2026-10-18): do not edit, build, run or repair it |
| `deepseek-sdk-experiment/` | Broken: calls Rust SDK operations that layerfs #352 removed |
| `research/` | Research notes |

**Paths into layerfs.** Builds, SDK sources and tools named in these files
(`core/`, `sdk/js/`, `tools/cleanup.py`, `.cargo/config.toml`) are paths in a
layerfs checkout at the measured commit, not in this repository. Relative
links such as `../docs/...` or `../core/...` inside the suites point into
layerfs; read them there. fs-bench-pro's files are left exactly as moved.
