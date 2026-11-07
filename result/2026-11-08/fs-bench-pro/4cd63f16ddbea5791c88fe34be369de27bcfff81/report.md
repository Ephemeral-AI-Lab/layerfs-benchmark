# fs-bench-pro — 2026-11-08

> Status: Research; informative and not a product contract.

**Export works from all four machines into a host folder: 7 of 8 samples completed with exact content (6 QUALIFIED, native E01 OVER_BUDGET under the first harness rule); Apple Container E01 FAILED mid-stream.**

LayerFS: `4cd63f16ddbea5791c88fe34be369de27bcfff81`, local branch `pr600-export-port`
(`layerfs_v2_0_0` at `98ebfdfb96` plus PR #600 and its review fixes), **not pushed**.
CLI release build (`cargo +1.85.1`) sha256 `5bed87e829a378be6c02f20dbf95d085008edbbd24639d15e8f37e646497f769`;
Linux bundle `bundle.json` sha256 `90671e7df78b9e900230bd44a7b93474dcb4f00e268d5b7a5d5f538aae079acc`,
bundled `layerfs` `fa3fdb038ee992e74e4c6d122c20f5de378e759d270953fba9d7339d1c726c01`. Harness: `ac8a2baa54` (receipts carry harness 1–3, below).
Workload `export-v1`. Guest tool `resident-linux-aarch64` sha256 `cd5210676f24ec0ba2803ba402417644cfd6ef7b3415be5d24d19b8560034780`.

Host: macOS 26.4.1, Apple M3 Max, 36 GiB. Docker Desktop engine 29.5.2, Lima 2.2.1,
Apple Container CLI 1.6.1. SQLite 3.53.2, Disposable. One Store per machine (`s-native`,
`s-docker`, `s-lima` on `lm1`, `s-ac` on `ac1`), each 320 MB holding both fixtures, inited on
native and pushed to the guest before the campaign. Destination: a fresh folder per sample on the
host's internal APFS volume. `LAYERFS_CONSTRUCTION_WORKERS=1`, private `LAYERFS_HOME` and `XDG_CACHE_HOME`.

## Main observations

- Every machine exports into a host folder. All seven completed exports matched the pinned
  manifests exactly (content, modes, symlinks, mtimes) and left no staging folder.
- Small files (E01) run at about 5,000–6,300 files/s on every machine (1.6–2.0 s for 10,000 files).
  Guests and native differ by under 0.5 s.
- One large file (E02): guests take 1.2–1.5 s (175–220 MB/s); native takes 8.2 s (33 MB/s).
  A labeled diagnostic after the campaign separated the cause: native E02 took 1.67 s warm and
  7.95 s right after re-attaching the disk image, while a plain sequential read of the 320 MB Store
  file from a freshly attached image ran at 1.8 GB/s. The native cost is the export's cold read
  pattern on a cold volume, not the writer. The guests' cold control is weaker (limits below), so
  this gap is not a native-vs-guest product difference.
- Apple Container E01 failed after 44.2 of 46.5 MB with exit code 125 and published nothing (no
  folder, no staging left). Under harness 2 the final error line was parsed and dropped, so its
  message is lost. The functional pre-campaign export of the same project succeeded once. This
  matches the open Apple Container issue recorded with the port: its port forward truncates large
  worker answers (PR #600 author: about 36% of 9.4 MB exports; `store.pull` too). Not rerun.
- Native E01's receipt is OVER_BUDGET because harness 1 counted the 12.0 s disk-image detach in
  the 15 s budget; its export took 2.04 s. The receipt is kept as recorded.

## Reading the tables

One row is one sample. **Export ms** is the wall time of the single timed CLI process
(`project export … --progress`). **MB/s** and **Files/s** divide the fixture's bytes and files by it.
**First event ms** is when the `prepare` progress line arrived. **Cold pages** are the Store files'
resident pages after the control (native counts 16 KiB pages, guests 4 KiB).
**Cold control s** and **Verify s** are untimed overhead, outside Export ms. **Load 1m** is the host's
1-minute load before the sample. Order: E01 then E02; native, Docker, Lima, Apple Container.

## E01 — export 10,000 small files (46.5 MB) with 50 symlinks and 132 folders

| Machine | Execution | Verification | Performance | Cold pages | Export ms | MB/s | Files/s | First event ms | Cold control s | Verify s | Load 1m |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| native | PASS | PASS | OVER_BUDGET | 0/19549 | 2039.17 | 22.8 | 4904.0 | 73.88 | 11.967 | 0.588 | 4.9 |
| docker | PASS | PASS | QUALIFIED | 0/78200 | 1685.83 | 27.6 | 5931.8 | 33.62 | 0.103 | 0.544 | 4.3 |
| lima | PASS | PASS | QUALIFIED | 0/78199 | 1581.86 | 29.4 | 6321.7 | 22.88 | 0.123 | 0.569 | 5.0 |
| apple-container | FAIL | FAIL | FAIL | 0/78193 | 1980.52 | — | — | 24.77 | 0.173 | 0.0 | 7.2 |

## E02 — export one 256 MiB file and a README

| Machine | Execution | Verification | Performance | Cold pages | Export ms | MB/s | Files/s | First event ms | Cold control s | Verify s | Load 1m |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| native | PASS | PASS | QUALIFIED | 0/19549 | 8229.23 | 32.6 | 0.2 | 21.1 | 0.775 | 0.362 | 7.3 |
| docker | PASS | PASS | QUALIFIED | 0/78200 | 1534.93 | 174.9 | 1.3 | 22.41 | 0.095 | 0.189 | 6.8 |
| lima | PASS | PASS | QUALIFIED | 0/78199 | 1220.72 | 219.9 | 1.6 | 27.22 | 0.099 | 0.191 | 6.8 |
| apple-container | PASS | PASS | QUALIFIED | 0/78193 | 1371.34 | 195.7 | 1.5 | 19.3 | 0.084 | 0.177 | 6.8 |
## Harness versions

The runner was fixed twice during the campaign; no receipt was relabeled or rerun.

| Harness | Receipts | Change |
| --- | --- | --- |
| 1 | E01 native | budget counted the cold control (12.0 s detach) plus verification |
| 2 | E01 Docker, Lima, Apple Container | budget judges the timed export only, as fs-bench-quick reports control overhead apart |
| 3 (`ac8a2baa54`) | E02 all | stderr lines that are not progress events are kept verbatim |

## Limits

- Guest cold control drops the Store's pages from the guest page cache only. The host may still
  cache the VM's disk file (Docker Desktop VM, Lima VM, Apple Container VM), which is shared and was
  not purged. Native detaches the whole owned volume, which is the stronger state.
- One sample per row; no variance claim. Host load was 4.3–7.3. A build in another worktree (the
  Microsandbox/SSH removal) ran 3–4 `rustc` processes during E02 native, Lima and Apple Container.
- Product source is an unpushed branch; SQLite only (no PostgreSQL arm); macOS host only; Durable:
  `NOT_RUN — disabled by owner until explicit reauthorization`.
- Prepared Stores were reused across samples; export only reads them. The cold control ran before
  every sample.

## Cleanup

Every exported folder was removed after verification. Machines, Stores, the disk image and fixtures
were kept for the follow-up on the Apple Container failure; they are released separately.
