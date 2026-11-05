# pjdfstest — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: PASS.** 32 registered rows; execution {'PASS': 32}. Final infrastructure cleanup: **COMPLETE**.

LayerFS `b919f50eaf9cce79671f8501a580279d23cc5f3c` (remote `layerfs_v2_0_0`, resolved at campaign start). Harness: 706d20a00f6b09324da6c95f532970dcaa5852d3. Matched release CLI/daemon/Linux bundle reused after hash checks; no product changes.

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 32}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Cleanup includes Sandbox close and Store remove/disconnect; End-to-end also includes mount/unmount and intervening harness work, excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: Apple M3 Max / macOS26.4.1 arm64, 36GiB RAM; native NFS; Docker FUSE; Lima VZ and Apple Container namespaces/FUSE (2CPU/2GiB/8GiB data each). Dedicated PostgreSQL17.11 Docker server 1CPU/512MiB. Effective UID501/GID20 confirmed on all routes. Host TCP port 63341 rewritten to Docker host.docker.internal, Lima192.168.5.2 and Apple gateway.. Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `1bc5e8d2b19e76c40d39de979f5624f54b932c1dba7c5d8165cc6eb56f702415` |
| Native daemon | `0d04f652b96cbffb3ba40775a41718ef0abf3612141347f1378cf2df40c9f375` |
| Linux bundle seal | `653cf3780ff8379c5ece5a832e9bec1fe112135afdc420e898fc5dba814b13df` |
| Docker tool image | `sha256:cc0814884e1b2acb5ffee43792faf40e7dbb3573ca157ab22af4179632c64dd0` |
| Namespace archive config | `sha256:965c442900ee25039a17ce22d733e01ec846ab870fe5a478e76d5fd983e68403` |

## P01

tests/open/04.t: 4 planned TAP assertions; selected scripts run unprivileged. fixed-posix-tap-unprivileged-subset-v2.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 310.97 | 104.45 | 12.44 | 200.05 | 687.91 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 493.52 | 86.05 | 34.84 | 256.44 | 1028.91 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 35.97 | 962.86 | 79.31 | 66.27 | 1215.18 | 9.22 | 6.37 | 1.77 |
| native | postgresql | PASS | COMPLETE | 89.41 | 151.20 | 148.97 | 99.78 | 631.13 | 1.76 | 4.28 | 0.61 |
| lima | sqlite | PASS | COMPLETE | 768.86 | 79.70 | 15.91 | 140.84 | 1090.99 | 0.76 | 1.28 | 1.59 |
| lima | postgresql | PASS | COMPLETE | 938.13 | 66.01 | 39.37 | 138.84 | 1390.49 | 0.77 | 1.13 | 1.35 |
| apple-container | sqlite | PASS | COMPLETE | 77.86 | 121.52 | 14.85 | 70.31 | 367.55 | 1.16 | 1.19 | 0.53 |
| apple-container | postgresql | PASS | COMPLETE | 345.76 | 134.07 | 97.50 | 86.12 | 922.45 | 1.56 | 2.80 | 0.90 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Assertions | Passed | Failed | Skipped | TODO |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / sqlite | 4 | 4 | 0 | 0 | 0 |
| docker / postgresql | 4 | 4 | 0 | 0 | 0 |
| native / sqlite | 4 | 4 | 0 | 0 | 0 |
| native / postgresql | 4 | 4 | 0 | 0 | 0 |
| lima / sqlite | 4 | 4 | 0 | 0 | 0 |
| lima / postgresql | 4 | 4 | 0 | 0 | 0 |
| apple-container / sqlite | 4 | 4 | 0 | 0 | 0 |
| apple-container / postgresql | 4 | 4 | 0 | 0 | 0 |

## P02

tests/rename/18.t: 6 planned TAP assertions; selected scripts run unprivileged. fixed-posix-tap-unprivileged-subset-v2.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 319.07 | 111.07 | 13.42 | 339.17 | 875.30 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 811.35 | 116.64 | 65.68 | 336.98 | 1512.02 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 51.91 | 204.61 | 80.51 | 82.86 | 529.78 | 1.84 | 6.00 | 0.61 |
| native | postgresql | PASS | COMPLETE | 91.94 | 161.29 | 114.96 | 99.66 | 632.87 | 1.38 | 1.75 | 0.42 |
| lima | sqlite | PASS | COMPLETE | 762.78 | 76.81 | 17.04 | 246.09 | 1231.68 | 0.69 | 1.27 | 1.41 |
| lima | postgresql | PASS | COMPLETE | 939.05 | 71.53 | 40.68 | 207.52 | 1492.42 | 0.61 | 0.62 | 0.99 |
| apple-container | sqlite | PASS | COMPLETE | 69.74 | 100.48 | 9.61 | 68.95 | 469.16 | 0.90 | 0.72 | 0.54 |
| apple-container | postgresql | PASS | COMPLETE | 326.79 | 83.16 | 63.68 | 97.04 | 801.70 | 0.71 | 0.97 | 0.53 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Assertions | Passed | Failed | Skipped | TODO |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / sqlite | 6 | 6 | 0 | 0 | 0 |
| docker / postgresql | 6 | 6 | 0 | 0 | 0 |
| native / sqlite | 6 | 6 | 0 | 0 | 0 |
| native / postgresql | 6 | 6 | 0 | 0 | 0 |
| lima / sqlite | 6 | 6 | 0 | 0 | 0 |
| lima / postgresql | 6 | 6 | 0 | 0 | 0 |
| apple-container / sqlite | 6 | 6 | 0 | 0 | 0 |
| apple-container / postgresql | 6 | 6 | 0 | 0 | 0 |

## P03

tests/chmod/02.t: 5 planned TAP assertions; selected scripts run unprivileged. fixed-posix-tap-unprivileged-subset-v2.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 286.86 | 158.21 | 13.43 | 276.71 | 868.04 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 541.79 | 113.90 | 29.75 | 276.12 | 1187.48 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 53.48 | 242.78 | 77.82 | 91.38 | 606.27 | 1.53 | 5.79 | 0.70 |
| native | postgresql | PASS | COMPLETE | 90.31 | 223.49 | 124.31 | 121.85 | 772.94 | 1.96 | 4.18 | 0.65 |
| lima | sqlite | PASS | COMPLETE | 741.59 | 78.56 | 13.15 | 164.41 | 1139.37 | 0.50 | 0.98 | 1.31 |
| lima | postgresql | PASS | COMPLETE | 923.67 | 79.36 | 39.44 | 159.90 | 1443.33 | 0.70 | 1.33 | 1.22 |
| apple-container | sqlite | PASS | COMPLETE | 59.43 | 112.66 | 9.32 | 85.96 | 425.65 | 0.71 | 0.69 | 0.49 |
| apple-container | postgresql | PASS | COMPLETE | 276.34 | 90.75 | 61.31 | 104.74 | 784.76 | 0.80 | 2.06 | 0.66 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Assertions | Passed | Failed | Skipped | TODO |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / sqlite | 5 | 5 | 0 | 0 | 0 |
| docker / postgresql | 5 | 5 | 0 | 0 | 0 |
| native / sqlite | 5 | 5 | 0 | 0 | 0 |
| native / postgresql | 5 | 5 | 0 | 0 | 0 |
| lima / sqlite | 5 | 5 | 0 | 0 | 0 |
| lima / postgresql | 5 | 5 | 0 | 0 | 0 |
| apple-container / sqlite | 5 | 5 | 0 | 0 | 0 |
| apple-container / postgresql | 5 | 5 | 0 | 0 | 0 |

## P04

tests/symlink/00.t: 14 planned TAP assertions; selected scripts run unprivileged. fixed-posix-tap-unprivileged-subset-v2.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 360.18 | 1128.91 | 13.82 | 294.40 | 1956.20 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 548.43 | 1116.03 | 43.46 | 307.64 | 2275.70 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 27.85 | 1209.32 | 89.08 | 109.20 | 1612.66 | 1.07 | 6.45 | 0.82 |
| native | postgresql | PASS | COMPLETE | 97.19 | 1249.13 | 131.36 | 123.09 | 1842.64 | 1.12 | 3.02 | 0.81 |
| lima | sqlite | PASS | COMPLETE | 731.62 | 1079.18 | 14.91 | 186.94 | 2203.18 | 0.96 | 1.08 | 1.13 |
| lima | postgresql | PASS | COMPLETE | 909.61 | 1077.17 | 51.33 | 183.38 | 2511.03 | 0.97 | 1.18 | 1.10 |
| apple-container | sqlite | PASS | COMPLETE | 57.92 | 1107.54 | 20.00 | 104.54 | 1479.23 | 0.98 | 1.45 | 0.76 |
| apple-container | postgresql | PASS | COMPLETE | 348.73 | 1116.30 | 127.50 | 147.33 | 2098.32 | 1.00 | 2.93 | 0.92 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Assertions | Passed | Failed | Skipped | TODO |
| --- | ---: | ---: | ---: | ---: | ---: |
| docker / sqlite | 14 | 14 | 0 | 0 | 0 |
| docker / postgresql | 14 | 14 | 0 | 0 | 0 |
| native / sqlite | 14 | 14 | 0 | 0 | 0 |
| native / postgresql | 14 | 14 | 0 | 0 | 0 |
| lima / sqlite | 14 | 14 | 0 | 0 | 0 |
| lima / postgresql | 14 | 14 | 0 | 0 | 0 |
| apple-container / sqlite | 14 | 14 | 0 | 0 | 0 |
| apple-container / postgresql | 14 | 14 | 0 | 0 | 0 |

## Preparation, limits and cleanup

Attempted row preparation: 4.989 s total; maximum 0.278 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final runtime infrastructure cleanup: **COMPLETE**. Overall teardown wall: **2.981238417 s**; serial resource-release commands total 2.657856831 s, excluding local-file cleanup from that sum.

All case Workspaces/Sandboxes/Stores released through public CLI. Owned Lima/Apple machines, Docker worker/container/data volume, PostgreSQL server/container/data volume, tool image, private home, secret, temporary input/archive and released build/source trees removed. Apple Container service restored to its prior stopped state. Small pinned binaries, recipes and local receipts retained; shared dependencies, earlier product artifacts/worktree and other owners resources preserved. Linux private target/Cargo volumes were removed separately; native target/debug and release remain protected because an active host VM holds files.

Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

Upstream source commit: `85a8aea9e685999ef0540392fd80535f873d7ff7`. Exact flags and setup: [frozen suite definition](https://github.com/Ephemeral-AI-Lab/layerfs-benchmark/blob/706d20a00f6b09324da6c95f532970dcaa5852d3/pjdfstest/src/cases.py).

## Profile history and interpretation

| Profile / product | PASS | FAIL | NOT_RUN | Disposition |
| --- | ---: | ---: | ---: | --- |
| Blanket-root-gate v1 / b919f50e | 0 | 0 | 32 | Retained historical prerequisite outcomes |
| Selected unprivileged scripts v2 / b919f50e | 32 | 0 | 0 | Current P01–P04 checkpoint |

The unchanged selected scripts produced **232 passing TAP assertions** across eight configurations (P01=4, P02=6, P03=5, P04=14 per configuration), with zero failed, skipped or TODO assertions. Every measured command observed ordinary effective UID501/GID20, without an identity switch. The four-script source review corrected the earlier blanket root prerequisite prospectively; it does not qualify the full privileged upstream suite. P04 retains its intrinsic one-second sleep.

[Immutable earlier report](https://github.com/Ephemeral-AI-Lab/layerfs-benchmark/blob/11b252ab4bf530fdfd7dd02822ee6f571b496e14/result/2026-11-06/pjdfstest/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) preserves the original released outcomes and configuration. Logs, receipts, manifests and source snapshots remain local and unpublished.
