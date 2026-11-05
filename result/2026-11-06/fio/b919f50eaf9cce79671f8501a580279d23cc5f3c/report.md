# fio — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: PASS.** 32 registered rows; execution {'PASS': 32}. Final infrastructure cleanup: **COMPLETE**.

LayerFS `b919f50eaf9cce79671f8501a580279d23cc5f3c` (remote `layerfs_v2_0_0`, resolved at campaign start). Harness: db7e0b341aabcbbe0c5f789b2856387674e52c5a. Matched release CLI/daemon/Linux bundle reused after hash checks; no product changes.

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 32}.

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

## F01

Sequential write: 64 MiB, 1024 KiB blocks; buffered synchronous engine, one job/depth 1, seed 1, nonzero 0x5a pattern. fio-buffered-single-pass-v1.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 288.96 | 625.88 | 222.39 | 270.68 | 1484.18 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 587.39 | 629.82 | 295.82 | 250.89 | 1932.99 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 51.58 | 1161.59 | 325.10 | 67.53 | 1683.25 | 1.86 | 1.46 | 1.13 |
| native | postgresql | PASS | COMPLETE | 71.70 | 361.72 | 394.42 | 89.07 | 1048.75 | 0.57 | 1.33 | 0.54 |
| lima | sqlite | PASS | COMPLETE | 745.59 | 596.16 | 217.19 | 148.18 | 1781.07 | 0.95 | 0.98 | 1.20 |
| lima | postgresql | PASS | COMPLETE | 908.48 | 370.30 | 272.15 | 136.85 | 1886.11 | 0.59 | 0.92 | 0.98 |
| apple-container | sqlite | PASS | COMPLETE | 74.96 | 617.07 | 224.85 | 65.09 | 1069.64 | 0.99 | 1.01 | 0.72 |
| apple-container | postgresql | PASS | COMPLETE | 350.52 | 373.65 | 336.88 | 87.07 | 1419.05 | 0.59 | 1.14 | 0.73 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | I/O MiB | I/O count | MiB/s | IOPS | Mean completion μs |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / sqlite | 64.00 | 64 | 533.33 | 533.33 | 1856.24 |
| docker / postgresql | 64.00 | 64 | 477.61 | 477.61 | 2077.58 |
| native / sqlite | 64.00 | 64 | 615.38 | 615.38 | 1551.30 |
| native / postgresql | 64.00 | 64 | 533.33 | 533.33 | 1852.41 |
| lima / sqlite | 64.00 | 64 | 474.07 | 474.07 | 2087.84 |
| lima / postgresql | 64.00 | 64 | 621.36 | 621.36 | 1599.78 |
| apple-container / sqlite | 64.00 | 64 | 429.53 | 429.53 | 2301.24 |
| apple-container / postgresql | 64.00 | 64 | 603.77 | 603.77 | 1639.70 |

## F02

Sequential read: 64 MiB, 1024 KiB blocks; buffered synchronous engine, one job/depth 1, seed 1, nonzero 0x5a pattern. fio-buffered-single-pass-v1.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 302.53 | 365.53 | 18.76 | 301.87 | 1115.33 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 427.94 | 368.00 | 23.51 | 294.27 | 1323.81 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 25.16 | 344.64 | 119.01 | 77.26 | 678.40 | 0.94 | 6.34 | 0.61 |
| native | postgresql | PASS | COMPLETE | 78.53 | 357.77 | 97.60 | 101.01 | 809.56 | 0.97 | 4.15 | 0.61 |
| lima | sqlite | PASS | COMPLETE | 721.07 | 346.55 | 14.82 | 159.57 | 1404.76 | 0.95 | 0.79 | 1.26 |
| lima | postgresql | PASS | COMPLETE | 865.12 | 342.97 | 20.93 | 153.34 | 1610.75 | 0.93 | 0.89 | 1.22 |
| apple-container | sqlite | PASS | COMPLETE | 60.70 | 354.70 | 15.61 | 113.17 | 725.14 | 0.97 | 0.83 | 0.65 |
| apple-container | postgresql | PASS | COMPLETE | 251.82 | 371.24 | 51.98 | 103.41 | 1068.32 | 1.01 | 2.21 | 0.81 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | I/O MiB | I/O count | MiB/s | IOPS | Mean completion μs |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / sqlite | 64.00 | 64 | 1422.22 | 1422.22 | 686.55 |
| docker / postgresql | 64.00 | 64 | 1422.22 | 1422.22 | 695.40 |
| native / sqlite | 64.00 | 64 | 1684.21 | 1684.21 | 578.91 |
| native / postgresql | 64.00 | 64 | 2064.52 | 2064.52 | 468.58 |
| lima / sqlite | 64.00 | 64 | 1600.00 | 1600.00 | 612.27 |
| lima / postgresql | 64.00 | 64 | 1306.12 | 1306.12 | 760.69 |
| apple-container / sqlite | 64.00 | 64 | 1254.90 | 1254.90 | 781.65 |
| apple-container / postgresql | 64.00 | 64 | 1454.55 | 1454.55 | 670.99 |

## F03

Random write: 8 MiB, 4 KiB blocks; buffered synchronous engine, one job/depth 1, seed 1, nonzero 0x5a pattern. fio-buffered-single-pass-v1.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 323.56 | 639.53 | 84.92 | 304.99 | 1526.31 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 518.63 | 370.62 | 88.77 | 291.13 | 1515.80 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 25.96 | 599.50 | 163.13 | 98.07 | 1052.52 | 0.94 | 1.92 | 0.69 |
| native | postgresql | PASS | COMPLETE | 69.42 | 619.95 | 210.62 | 118.13 | 1244.25 | 1.67 | 2.37 | 0.82 |
| lima | sqlite | PASS | COMPLETE | 740.92 | 599.59 | 51.20 | 173.47 | 1736.64 | 0.94 | 0.60 | 1.14 |
| lima | postgresql | PASS | COMPLETE | 916.35 | 588.84 | 98.47 | 166.41 | 2044.42 | 1.59 | 1.11 | 1.35 |
| apple-container | sqlite | PASS | COMPLETE | 47.37 | 340.73 | 46.69 | 94.70 | 681.23 | 0.53 | 0.55 | 0.45 |
| apple-container | postgresql | PASS | COMPLETE | 275.93 | 360.44 | 121.17 | 139.32 | 1160.60 | 0.97 | 1.37 | 0.77 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | I/O MiB | I/O count | MiB/s | IOPS | Mean completion μs |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / sqlite | 8.00 | 2048 | 66.67 | 17066.67 | 56.93 |
| docker / postgresql | 8.00 | 2048 | 68.38 | 17504.27 | 55.91 |
| native / sqlite | 8.00 | 2048 | 47.90 | 12263.47 | 79.78 |
| native / postgresql | 8.00 | 2048 | 52.63 | 13473.68 | 72.64 |
| lima / sqlite | 8.00 | 2048 | 56.74 | 14524.82 | 67.06 |
| lima / postgresql | 8.00 | 2048 | 54.79 | 14027.40 | 69.61 |
| apple-container / sqlite | 8.00 | 2048 | 61.07 | 15633.59 | 62.21 |
| apple-container / postgresql | 8.00 | 2048 | 70.80 | 18123.89 | 53.66 |

## F04

Random read: 8 MiB, 4 KiB blocks; buffered synchronous engine, one job/depth 1, seed 1, nonzero 0x5a pattern. fio-buffered-single-pass-v1.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 314.62 | 375.54 | 14.52 | 258.96 | 1154.30 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 450.81 | 373.86 | 16.33 | 335.11 | 1467.73 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 28.47 | 347.56 | 80.48 | 127.22 | 785.48 | 0.93 | 5.54 | 0.68 |
| native | postgresql | PASS | COMPLETE | 90.79 | 369.28 | 107.95 | 143.97 | 983.82 | 0.99 | 6.61 | 0.67 |
| lima | sqlite | PASS | COMPLETE | 737.80 | 339.04 | 13.53 | 199.85 | 1495.84 | 0.90 | 0.93 | 1.30 |
| lima | postgresql | PASS | COMPLETE | 920.16 | 342.74 | 21.40 | 198.55 | 1773.08 | 0.92 | 1.31 | 1.21 |
| apple-container | sqlite | PASS | COMPLETE | 58.20 | 344.20 | 13.03 | 114.03 | 789.05 | 0.92 | 0.90 | 0.68 |
| apple-container | postgresql | PASS | COMPLETE | 272.24 | 368.58 | 67.43 | 141.06 | 1218.58 | 0.99 | 4.13 | 0.83 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | I/O MiB | I/O count | MiB/s | IOPS | Mean completion μs |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / sqlite | 8.00 | 2048 | 83.33 | 21333.33 | 45.89 |
| docker / postgresql | 8.00 | 2048 | 72.73 | 18618.18 | 52.02 |
| native / sqlite | 8.00 | 2048 | 470.59 | 120470.59 | 7.53 |
| native / postgresql | 8.00 | 2048 | 470.59 | 120470.59 | 7.47 |
| lima / sqlite | 8.00 | 2048 | 86.96 | 22260.87 | 43.55 |
| lima / postgresql | 8.00 | 2048 | 74.77 | 19140.19 | 51.11 |
| apple-container / sqlite | 8.00 | 2048 | 83.33 | 21333.33 | 45.79 |
| apple-container / postgresql | 8.00 | 2048 | 98.77 | 25283.95 | 38.28 |

## Preparation, limits and cleanup

Attempted row preparation: 26.790 s total; maximum 2.247 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **COMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. Serial resource-release commands total 2.493 s, including the refused deletion; diagnosis gaps and local-file cleanup are excluded from that sum.

All case Workspaces/Sandboxes/Store registrations released through public CLI. Owned Lima and Apple machines removed; Docker worker stopped and private data volume deleted; PostgreSQL server/container/data volume removed; owned tool image, temporary archive, source/build trees, home, input directory and credential file removed. Apple Container service restored to its prior stopped state. Small pinned tool binaries/recipes and local receipts retained; shared dependencies, earlier product artifacts/worktree and other owners resources preserved.

Initial volume deletion was refused because the stopped worker container retained its mount. Inspected exact exited worker ownership/PID0, removed it, then explicitly released the volume after the dependency changed. Original failed deletion retained; no uncertain operation replay. Overall uninterrupted teardown wall is UNAVAILABLE because finalization resumed after diagnosis; serial release-command sum is measured separately.

Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

fio writes the declared compressible nonzero 0x5a pattern. Bandwidth and completion latency come from fio's own single job interval; CLI Exec and End-to-end above include additional lifecycle/routing costs.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

Upstream source commit: `ff930c4653ae3952d6b09ab3ec89671aeabf2cbe`. Exact flags and setup: [frozen suite definition](https://github.com/Ephemeral-AI-Lab/layerfs-benchmark/blob/db7e0b341aabcbbe0c5f789b2856387674e52c5a/fio/src/cases.py).

