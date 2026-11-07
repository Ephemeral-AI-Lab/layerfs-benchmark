# fs-bench-pro — 2026-11-08 (worker close-order fix)

> Status: Research; informative and not a product contract.

**All 8 export samples QUALIFIED: every machine exported both fixtures into a host folder with exact content, from a cold Store, within budget.**

LayerFS: `97fac452bd4c1f834bdc2df005cf01caf8b415d0`, local branch `pr600-export-port`, **not pushed**:
the [earlier run](../4cd63f16ddbea5791c88fe34be369de27bcfff81/report.md)'s commit plus one fix, the worker
waits for the client to close after its answer. CLI release build (`cargo +1.85.1`) sha256
`acf1e63b0bfe888c10d29f2f9eb10631e22610c0b5ffb8b4a632c7dfadf61b43`; sealed Linux bundle hash
`238efd1913e0910b66d6af08e1b0b436addeb763c74212b90fddaaad23e5f843`, installed on all three guests by
`machine stop` + `machine start`. Harness: `ac8a2baa54` (harness 3 in every receipt). Workload `export-v1`.

Host, machines, Stores, fixtures and cold control are as in the earlier run: macOS 26.4.1, Apple M3 Max,
36 GiB; Docker Desktop 29.5.2, Lima 2.2.1, Apple Container 1.6.1; SQLite 3.53.2, Disposable; one 320 MB
Store per machine holding both fixtures; a fresh destination folder per sample on the host's internal
APFS volume. `LAYERFS_CONSTRUCTION_WORKERS=1`, private `LAYERFS_HOME` and `XDG_CACHE_HOME`.

## Main observations

- Apple Container E01, which failed in the earlier run, now passes. The cause: Apple Container's
  published port drops what it still holds for the host when the guest side closes first, and the
  worker closed right after its last frame. A plain 50 MB stream through a throwaway Apple Container
  lost 78–570 KB at the tail in 4 of 30 slow reads when the guest closed first, and 0 of 16 when the
  host closed first. After the fix, 12 of 12 small and 4 of 4 large Apple Container exports
  (untimed checks before this campaign) matched the manifests.
- Small files (E01): 1.3–1.9 s on every machine, 5,400–7,500 files/s.
- One large file (E02): Apple Container 1.18 s (227 MB/s); Lima 3.58 s, Docker 4.00 s; native 7.57 s.
  Docker and Lima took 2.6x and 2.9x their earlier-run times. That run had a lower host load (6.8 vs
  10.5–10.9) and its guests had not just been restarted; one sample each does not separate these.
  Native E02 remains cold-read bound (1.67 s warm in the earlier run's diagnostic).

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
| native | PASS | PASS | QUALIFIED | 0/19549 | 1862.49 | 25.0 | 5369.2 | 24.55 | 1.11 | 0.601 | 10.7 |
| docker | PASS | PASS | QUALIFIED | 0/78200 | 1573.13 | 29.6 | 6356.8 | 31.32 | 0.088 | 0.602 | 10.9 |
| lima | PASS | PASS | QUALIFIED | 0/78199 | 1377.3 | 33.8 | 7260.6 | 25.69 | 0.1 | 0.577 | 10.9 |
| apple-container | PASS | PASS | QUALIFIED | 0/78193 | 1326.26 | 35.1 | 7540.0 | 21.56 | 0.108 | 0.615 | 11.7 |

## E02 — export one 256 MiB file and a README

| Machine | Execution | Verification | Performance | Cold pages | Export ms | MB/s | Files/s | First event ms | Cold control s | Verify s | Load 1m |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| native | PASS | PASS | QUALIFIED | 0/19549 | 7566.83 | 35.5 | 0.3 | 21.06 | 4.106 | 0.196 | 12.1 |
| docker | PASS | PASS | QUALIFIED | 0/78200 | 3996.32 | 67.2 | 0.5 | 19.75 | 0.086 | 0.18 | 10.9 |
| lima | PASS | PASS | QUALIFIED | 0/78199 | 3577.84 | 75.0 | 0.6 | 17.68 | 0.097 | 0.222 | 10.5 |
| apple-container | PASS | PASS | QUALIFIED | 0/78193 | 1180.54 | 227.4 | 1.7 | 23.43 | 0.1 | 0.201 | 9.8 |

## Limits

- Guest cold control drops the Store's pages from the guest page cache only. The host may still
  cache the VM's disk file, which is shared and was not purged; native detaches the whole owned volume.
- One sample per row; no variance claim. Host load was 9.8–12.1; two `rustc` processes of another
  session ran through the campaign (gone before they could be attributed).
- Product source is an unpushed branch; SQLite only; macOS host only; Durable:
  `NOT_RUN — disabled by owner until explicit reauthorization`.
- Prepared Stores were reused across samples; export only reads them.

## Cleanup

Every exported folder was removed after verification and no staging folder was left. Machines,
Stores, the disk image and fixtures are released after this report.
