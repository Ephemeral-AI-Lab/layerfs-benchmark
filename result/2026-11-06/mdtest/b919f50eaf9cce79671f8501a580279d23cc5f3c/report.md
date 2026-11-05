# mdtest — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: PASS.** 16 registered rows; execution {'PASS': 16}. Final infrastructure cleanup: **COMPLETE**.

LayerFS `b919f50eaf9cce79671f8501a580279d23cc5f3c` (remote `layerfs_v2_0_0`, resolved at campaign start). Harness: 5b47f0be45ce4e9c6d8d0416dca89dc74f7d0f39. Matched release CLI/daemon/Linux bundle reused after hash checks; no product changes.

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 16}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Cleanup includes Sandbox close and Store remove/disconnect; End-to-end also includes mount/unmount and intervening harness work, excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: macOS native NFS (UID501/GID20); Docker FUSE; Lima VZ and Apple Container namespaces/FUSE (2CPU/2GiB/8GiB data each). PostgreSQL17.11 Docker server 1CPU/512MiB, host TCP port54078. All command identities nonroot. Host loopback rewrites to Docker host.docker.internal, Lima192.168.5.2 and Apple host gateway.. Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `1bc5e8d2b19e76c40d39de979f5624f54b932c1dba7c5d8165cc6eb56f702415` |
| Native daemon | `0d04f652b96cbffb3ba40775a41718ef0abf3612141347f1378cf2df40c9f375` |
| Linux bundle seal | `653cf3780ff8379c5ece5a832e9bec1fe112135afdc420e898fc5dba814b13df` |
| Docker tool image | `sha256:26489bb3d6a603025c0dcbed60f4b57a112f312bcefc2d876c58b548dd8b8f45` |
| Namespace archive config | `sha256:de56ab67f0fe4a74374aec628121b8b51b9099a268026b5778538f9b7d809339` |

## M01

512 empty files; one MPI rank; one create/stat/remove iteration. one-rank-512-create-stat-remove-v2.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 311.14 | 1263.34 | 14.59 | 263.31 | 1919.46 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 521.24 | 1285.05 | 46.16 | 253.78 | 2274.82 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 38.18 | 1488.42 | 71.03 | 67.11 | 1735.87 | 1.18 | 4.87 | 0.90 |
| native | postgresql | PASS | COMPLETE | 87.64 | 1552.23 | 121.28 | 91.76 | 1991.94 | 1.21 | 2.63 | 0.88 |
| lima | sqlite | PASS | COMPLETE | 742.64 | 1241.03 | 15.46 | 139.74 | 2211.61 | 0.98 | 1.06 | 1.15 |
| lima | postgresql | PASS | COMPLETE | 931.27 | 1238.41 | 42.13 | 133.63 | 2521.29 | 0.96 | 0.91 | 1.11 |
| apple-container | sqlite | PASS | COMPLETE | 59.67 | 1296.53 | 17.15 | 70.90 | 1528.52 | 1.03 | 1.18 | 0.80 |
| apple-container | postgresql | PASS | COMPLETE | 325.20 | 1289.71 | 113.37 | 116.99 | 2094.12 | 1.00 | 2.46 | 0.92 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Entries | Create ops/s | Stat ops/s | Remove ops/s |
| --- | ---: | ---: | ---: | ---: |
| docker / sqlite | 512 | 6283.05 | 1042467.79 | 8220.28 |
| docker / postgresql | 512 | 5373.18 | 704323.93 | 8047.92 |
| native / sqlite | 512 | 1966.02 | 379548.19 | 3080.12 |
| native / postgresql | 512 | 1831.88 | 364660.15 | 2772.17 |
| lima / sqlite | 512 | 5757.61 | 705249.15 | 10186.63 |
| lima / postgresql | 512 | 5825.12 | 656522.06 | 10599.10 |
| apple-container / sqlite | 512 | 5265.21 | 1202398.46 | 9520.76 |
| apple-container / postgresql | 512 | 4937.18 | 866270.13 | 8735.72 |

## M02

512 directories; one MPI rank; one create/stat/remove iteration. one-rank-512-create-stat-remove-v2.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 311.81 | 1267.51 | 15.77 | 256.17 | 1950.93 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 510.14 | 1286.37 | 42.04 | 282.44 | 2309.34 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 27.89 | 1479.84 | 79.92 | 84.91 | 1794.38 | 1.17 | 5.07 | 0.92 |
| native | postgresql | PASS | COMPLETE | 81.58 | 1473.29 | 121.39 | 99.76 | 1948.61 | 1.15 | 2.89 | 0.84 |
| lima | sqlite | PASS | COMPLETE | 714.18 | 1251.91 | 14.91 | 156.71 | 2250.76 | 0.99 | 0.95 | 1.15 |
| lima | postgresql | PASS | COMPLETE | 921.37 | 1217.80 | 45.70 | 154.32 | 2553.08 | 0.95 | 1.09 | 1.11 |
| apple-container | sqlite | PASS | COMPLETE | 60.08 | 1272.35 | 13.36 | 76.92 | 1533.16 | 1.00 | 0.85 | 0.79 |
| apple-container | postgresql | PASS | COMPLETE | 297.92 | 1248.09 | 67.89 | 100.13 | 1948.49 | 0.97 | 1.61 | 0.84 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Entries | Create ops/s | Stat ops/s | Remove ops/s |
| --- | ---: | ---: | ---: | ---: |
| docker / sqlite | 512 | 5752.67 | 879755.69 | 8147.43 |
| docker / postgresql | 512 | 5332.05 | 814057.49 | 7524.31 |
| native / sqlite | 512 | 1921.96 | 395995.51 | 3408.38 |
| native / postgresql | 512 | 2172.22 | 383273.90 | 3553.48 |
| lima / sqlite | 512 | 7379.21 | 664033.29 | 10922.00 |
| lima / postgresql | 512 | 6924.71 | 613917.57 | 10786.01 |
| apple-container / sqlite | 512 | 5181.66 | 912657.73 | 9523.97 |
| apple-container / postgresql | 512 | 6205.60 | 914211.85 | 9313.00 |

## Preparation, limits and cleanup

Attempted row preparation: 2.066 s total; maximum 0.200 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **COMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. Serial resource-release commands total 2.493 s, including the refused deletion; diagnosis gaps and local-file cleanup are excluded from that sum.

All case Workspaces/Sandboxes/Store registrations released through public CLI. Owned Lima and Apple machines removed; Docker worker stopped and private data volume deleted; PostgreSQL server/container/data volume removed; owned tool image, temporary archive, source/build trees, home, input directory and credential file removed. Apple Container service restored to its prior stopped state. Small pinned tool binaries/recipes and local receipts retained; shared dependencies, earlier product artifacts/worktree and other owners resources preserved.

Initial volume deletion was refused because the stopped worker container retained its mount. Inspected exact exited worker ownership/PID0, removed it, then explicitly released the volume after the dependency changed. Original failed deletion retained; no uncertain operation replay. Overall uninterrupted teardown wall is UNAVAILABLE because finalization resumed after diagnosis; serial release-command sum is measured separately.

Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

Upstream source commit: `8e109900e24d45f1cd1184f108458f5fa9b4692c`. Exact flags and setup: [frozen suite definition](https://github.com/Ephemeral-AI-Lab/layerfs-benchmark/blob/5b47f0be45ce4e9c6d8d0416dca89dc74f7d0f39/mdtest/src/cases.py).

## Retained v1 launcher outcomes

The earlier launcher had **4 PASS, 1 FAIL and 11 NOT_RUN** across 16 registered selections. M01/Lima/SQLite failed before filesystem work: hwloc could not find the namespace CPU-topology sysfs directory, and MPI reported that all allocated nodes were filled. Known case cleanup completed. Remaining v1 selections were withdrawn before attempt. v2 uses generic OS discovery, one explicit localhost slot and no binding on every machine; payload/phase counts are unchanged. v1 is excluded from v2 timing ratios.

### M01 — retired v1

| Machine | Database | Execution | Cleanup | Exec ms | End-to-end ms | Disposition |
| --- | --- | --- | --- | ---: | ---: | --- |
| docker | sqlite | PASS | COMPLETE | 1324.59 | 1950.49 | Original observation retained |
| docker | postgresql | PASS | COMPLETE | 1306.88 | 2400.10 | Original observation retained |
| native | sqlite | PASS | COMPLETE | 1667.24 | 1946.82 | Original observation retained |
| native | postgresql | PASS | COMPLETE | 1661.66 | 2108.93 | Original observation retained |
| lima | sqlite | FAIL | COMPLETE | 1575.96 | 2511.75 | MPI startup failure; v2 corrected configuration |
| lima | postgresql | NOT_RUN | COMPLETE | — | — | Withdrawn before attempt; successor v2 |
| apple-container | sqlite | NOT_RUN | COMPLETE | — | — | Withdrawn before attempt; successor v2 |
| apple-container | postgresql | NOT_RUN | COMPLETE | — | — | Withdrawn before attempt; successor v2 |

### M02 — retired v1

| Machine | Database | Execution | Cleanup | Exec ms | End-to-end ms | Disposition |
| --- | --- | --- | --- | ---: | ---: | --- |
| docker | sqlite | NOT_RUN | COMPLETE | — | — | Withdrawn before attempt; successor v2 |
| docker | postgresql | NOT_RUN | COMPLETE | — | — | Withdrawn before attempt; successor v2 |
| native | sqlite | NOT_RUN | COMPLETE | — | — | Withdrawn before attempt; successor v2 |
| native | postgresql | NOT_RUN | COMPLETE | — | — | Withdrawn before attempt; successor v2 |
| lima | sqlite | NOT_RUN | COMPLETE | — | — | Withdrawn before attempt; successor v2 |
| lima | postgresql | NOT_RUN | COMPLETE | — | — | Withdrawn before attempt; successor v2 |
| apple-container | sqlite | NOT_RUN | COMPLETE | — | — | Withdrawn before attempt; successor v2 |
| apple-container | postgresql | NOT_RUN | COMPLETE | — | — | Withdrawn before attempt; successor v2 |

[Launcher change record](https://github.com/Ephemeral-AI-Lab/layerfs-benchmark/blob/5b47f0b/mdtest/CHANGES.md). Across versions mdtest retains 32 registered selections; the current suite is the 16-row v2 table above.

