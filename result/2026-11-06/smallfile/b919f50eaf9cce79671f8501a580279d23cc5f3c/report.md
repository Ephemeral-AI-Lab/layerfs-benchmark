# smallfile — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: PASS.** 40 registered rows; execution {'PASS': 40}. Final infrastructure cleanup: **COMPLETE**.

LayerFS `b919f50eaf9cce79671f8501a580279d23cc5f3c` (remote `layerfs_v2_0_0`, resolved at campaign start). Harness: 5b47f0be45ce4e9c6d8d0416dca89dc74f7d0f39. Matched release CLI/daemon/Linux bundle reused after hash checks; no product changes.

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 40}.

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

## L01

Create 512 files: two workers × 256 files, 4 KiB/file, 64 files/directory. two-worker-256x4k-as-host-v1.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 317.82 | 3723.18 | 62.19 | 243.14 | 4418.17 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 552.78 | 3680.20 | 167.70 | 231.63 | 4806.83 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 55.83 | 3914.81 | 148.87 | 71.78 | 4284.63 | 1.05 | 2.39 | 0.97 |
| native | postgresql | PASS | COMPLETE | 93.55 | 3865.94 | 221.78 | 108.72 | 4434.46 | 1.05 | 1.32 | 0.92 |
| lima | sqlite | PASS | COMPLETE | 747.19 | 3945.43 | 59.17 | 148.34 | 4987.74 | 1.06 | 0.95 | 1.13 |
| lima | postgresql | PASS | COMPLETE | 924.39 | 3775.23 | 174.05 | 133.99 | 5201.08 | 1.03 | 1.04 | 1.08 |
| apple-container | sqlite | PASS | COMPLETE | 67.39 | 3788.54 | 54.33 | 60.39 | 4044.11 | 1.02 | 0.87 | 0.92 |
| apple-container | postgresql | PASS | COMPLETE | 306.20 | 3818.39 | 274.79 | 112.89 | 4738.32 | 1.04 | 1.64 | 0.99 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Files | Σ worker files/s | Worker 00 records | Worker 01 records |
| --- | ---: | ---: | ---: | ---: |
| docker / sqlite | 512 | 5782.38 | 256 | 256 |
| docker / postgresql | 512 | 6793.89 | 256 | 256 |
| native / sqlite | 512 | 2458.05 | 256 | 256 |
| native / postgresql | 512 | 2227.28 | 256 | 256 |
| lima / sqlite | 512 | 6778.41 | 256 | 256 |
| lima / postgresql | 512 | 7136.25 | 256 | 256 |
| apple-container / sqlite | 512 | 7312.27 | 256 | 256 |
| apple-container / postgresql | 512 | 5627.95 | 256 | 256 |

## L02

Read 512 files: two workers × 256 files, 4 KiB/file, 64 files/directory. two-worker-256x4k-as-host-v1.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 327.50 | 3710.64 | 21.56 | 303.69 | 4487.41 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 460.25 | 3654.84 | 60.34 | 293.80 | 4668.87 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 38.36 | 3711.00 | 97.13 | 82.02 | 4042.46 | 1.00 | 4.51 | 0.90 |
| native | postgresql | PASS | COMPLETE | 89.62 | 3766.60 | 153.98 | 110.23 | 4316.37 | 1.03 | 2.55 | 0.92 |
| lima | sqlite | PASS | COMPLETE | 704.98 | 3749.29 | 22.27 | 159.41 | 4750.35 | 1.01 | 1.03 | 1.06 |
| lima | postgresql | PASS | COMPLETE | 873.88 | 3745.76 | 53.96 | 155.83 | 5075.69 | 1.02 | 0.89 | 1.09 |
| apple-container | sqlite | PASS | COMPLETE | 38.48 | 3766.52 | 12.43 | 79.34 | 4017.02 | 1.02 | 0.58 | 0.90 |
| apple-container | postgresql | PASS | COMPLETE | 255.36 | 3863.16 | 144.35 | 161.88 | 4703.70 | 1.06 | 2.39 | 1.01 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Files | Σ worker files/s | Worker 00 records | Worker 01 records |
| --- | ---: | ---: | ---: | ---: |
| docker / sqlite | 512 | 7319.87 | 256 | 256 |
| docker / postgresql | 512 | 8948.61 | 256 | 256 |
| native / sqlite | 512 | 6143.00 | 256 | 256 |
| native / postgresql | 512 | 4690.40 | 256 | 256 |
| lima / sqlite | 512 | 9818.79 | 256 | 256 |
| lima / postgresql | 512 | 9595.63 | 256 | 256 |
| apple-container / sqlite | 512 | 9048.49 | 256 | 256 |
| apple-container / postgresql | 512 | 3760.38 | 256 | 256 |

## L03

Stat 512 files: two workers × 256 files, 4 KiB/file, 64 files/directory. two-worker-256x4k-as-host-v1.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 279.31 | 3610.89 | 17.34 | 292.18 | 4359.21 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 479.63 | 3651.68 | 79.22 | 320.03 | 4812.30 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 25.41 | 3653.42 | 106.96 | 99.94 | 4043.27 | 1.01 | 6.17 | 0.93 |
| native | postgresql | PASS | COMPLETE | 85.92 | 3737.56 | 174.93 | 125.81 | 4362.02 | 1.02 | 2.21 | 0.91 |
| lima | sqlite | PASS | COMPLETE | 722.30 | 3697.66 | 15.29 | 178.04 | 4773.33 | 1.02 | 0.88 | 1.09 |
| lima | postgresql | PASS | COMPLETE | 875.85 | 3762.61 | 88.89 | 175.57 | 5180.44 | 1.03 | 1.12 | 1.08 |
| apple-container | sqlite | PASS | COMPLETE | 56.98 | 3766.88 | 26.13 | 105.20 | 4143.65 | 1.04 | 1.51 | 0.95 |
| apple-container | postgresql | PASS | COMPLETE | 206.10 | 3855.21 | 207.41 | 126.56 | 4715.61 | 1.06 | 2.62 | 0.98 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Files | Σ worker files/s | Worker 00 records | Worker 01 records |
| --- | ---: | ---: | ---: | ---: |
| docker / sqlite | 512 | 29403.23 | 0 | 0 |
| docker / postgresql | 512 | 13871.14 | 0 | 0 |
| native / sqlite | 512 | 13274.22 | 0 | 0 |
| native / postgresql | 512 | 7219.74 | 0 | 0 |
| lima / sqlite | 512 | 32325.89 | 0 | 0 |
| lima / postgresql | 512 | 8675.18 | 0 | 0 |
| apple-container / sqlite | 512 | 13051.17 | 0 | 0 |
| apple-container / postgresql | 512 | 5847.44 | 0 | 0 |

## L04

Rename 512 files: two workers × 256 files, 4 KiB/file, 64 files/directory. two-worker-256x4k-as-host-v1.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 305.64 | 3718.44 | 37.23 | 318.40 | 4596.35 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 444.70 | 3769.19 | 101.07 | 302.05 | 4942.78 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 40.70 | 3874.68 | 88.28 | 113.77 | 4329.36 | 1.04 | 2.37 | 0.94 |
| native | postgresql | PASS | COMPLETE | 84.60 | 3891.54 | 167.28 | 151.40 | 4569.43 | 1.03 | 1.66 | 0.92 |
| lima | sqlite | PASS | COMPLETE | 738.51 | 3752.77 | 34.25 | 201.75 | 4966.48 | 1.01 | 0.92 | 1.08 |
| lima | postgresql | PASS | COMPLETE | 851.31 | 3781.08 | 108.01 | 201.16 | 5281.99 | 1.00 | 1.07 | 1.07 |
| apple-container | sqlite | PASS | COMPLETE | 55.41 | 3829.46 | 33.79 | 117.05 | 4275.17 | 1.03 | 0.91 | 0.93 |
| apple-container | postgresql | PASS | COMPLETE | 258.38 | 3865.65 | 175.48 | 141.77 | 4822.82 | 1.03 | 1.74 | 0.98 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Files | Σ worker files/s | Worker 00 records | Worker 01 records |
| --- | ---: | ---: | ---: | ---: |
| docker / sqlite | 512 | 4756.40 | 0 | 0 |
| docker / postgresql | 512 | 3687.53 | 0 | 0 |
| native / sqlite | 512 | 2027.66 | 0 | 0 |
| native / postgresql | 512 | 1982.49 | 0 | 0 |
| lima / sqlite | 512 | 7132.79 | 0 | 0 |
| lima / postgresql | 512 | 6168.43 | 0 | 0 |
| apple-container / sqlite | 512 | 4905.72 | 0 | 0 |
| apple-container / postgresql | 512 | 3940.29 | 0 | 0 |

## L05

Delete 512 files: two workers × 256 files, 4 KiB/file, 64 files/directory. two-worker-256x4k-as-host-v1.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 282.89 | 3684.83 | 39.64 | 358.58 | 4644.70 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 424.95 | 3698.97 | 102.33 | 366.31 | 4959.05 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 25.40 | 3719.61 | 94.81 | 141.77 | 4237.09 | 1.01 | 2.39 | 0.91 |
| native | postgresql | PASS | COMPLETE | 88.64 | 3780.23 | 174.41 | 165.32 | 4534.73 | 1.02 | 1.70 | 0.91 |
| lima | sqlite | PASS | COMPLETE | 723.87 | 3736.00 | 33.45 | 215.80 | 4967.58 | 1.01 | 0.84 | 1.07 |
| lima | postgresql | PASS | COMPLETE | 878.01 | 3739.82 | 117.68 | 209.25 | 5311.33 | 1.01 | 1.15 | 1.07 |
| apple-container | sqlite | PASS | COMPLETE | 40.86 | 3781.78 | 32.17 | 138.18 | 4297.11 | 1.03 | 0.81 | 0.93 |
| apple-container | postgresql | PASS | COMPLETE | 225.60 | 3842.24 | 175.74 | 160.32 | 4805.52 | 1.04 | 1.72 | 0.97 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Files | Σ worker files/s | Worker 00 records | Worker 01 records |
| --- | ---: | ---: | ---: | ---: |
| docker / sqlite | 512 | 7167.72 | 0 | 0 |
| docker / postgresql | 512 | 5965.32 | 0 | 0 |
| native / sqlite | 512 | 4742.94 | 0 | 0 |
| native / postgresql | 512 | 3523.04 | 0 | 0 |
| lima / sqlite | 512 | 10799.91 | 0 | 0 |
| lima / postgresql | 512 | 9025.33 | 0 | 0 |
| apple-container / sqlite | 512 | 7700.93 | 0 | 0 |
| apple-container / postgresql | 512 | 4722.42 | 0 | 0 |

## Preparation, limits and cleanup

Attempted row preparation: 156.406 s total; maximum 5.594 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **COMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. Serial resource-release commands total 2.493 s, including the refused deletion; diagnosis gaps and local-file cleanup are excluded from that sum.

All case Workspaces/Sandboxes/Store registrations released through public CLI. Owned Lima and Apple machines removed; Docker worker stopped and private data volume deleted; PostgreSQL server/container/data volume removed; owned tool image, temporary archive, source/build trees, home, input directory and credential file removed. Apple Container service restored to its prior stopped state. Small pinned tool binaries/recipes and local receipts retained; shared dependencies, earlier product artifacts/worktree and other owners resources preserved.

Initial volume deletion was refused because the stopped worker container retained its mount. Inspected exact exited worker ownership/PID0, removed it, then explicitly released the volume after the dependency changed. Original failed deletion retained; no uncertain operation replay. Overall uninterrupted teardown wall is UNAVAILABLE because finalization resumed after diagnosis; serial release-command sum is measured separately.

Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

Smallfile upstream rate = 256/T00 + 256/T01 files/s. Each worker timer starts after directory, seed/buffer preparation and gate waiting; it uses upstream time.time(). It excludes launcher/startup work, so it is not 512 divided by CLI Exec time. Its control-file fsyncs are intrinsic upstream behavior; payload fsync is disabled. The declared 4KiB payload pattern is nonzero and compressible.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

Upstream source commit: `aa2519de5bf0b3b383db2c31eacbf8ac4328e19c`. Exact flags and setup: [frozen suite definition](https://github.com/Ephemeral-AI-Lab/layerfs-benchmark/blob/5b47f0be45ce4e9c6d8d0416dca89dc74f7d0f39/smallfile/src/cases.py).

