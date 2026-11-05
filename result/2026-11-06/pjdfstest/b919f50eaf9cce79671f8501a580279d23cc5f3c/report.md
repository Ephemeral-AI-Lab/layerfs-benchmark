# pjdfstest — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: INCOMPLETE.** 32 registered rows; execution {'NOT_RUN': 32}. Final infrastructure cleanup: **COMPLETE**.

LayerFS `b919f50eaf9cce79671f8501a580279d23cc5f3c` (remote `layerfs_v2_0_0`, resolved at campaign start). Harness: 5b47f0be45ce4e9c6d8d0416dca89dc74f7d0f39. Matched release CLI/daemon/Linux bundle reused after hash checks; no product changes.

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

## P01

tests/open/04.t: 4 planned TAP assertions; upstream root prerequisite. fixed-posix-tap-v1.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| docker | postgresql | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| native | sqlite | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| native | postgresql | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| lima | sqlite | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| lima | postgresql | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| apple-container | sqlite | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| apple-container | postgresql | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |

- All eight configurations: upstream requires root; selected execution route is not root

## P02

tests/rename/18.t: 6 planned TAP assertions; upstream root prerequisite. fixed-posix-tap-v1.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| docker | postgresql | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| native | sqlite | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| native | postgresql | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| lima | sqlite | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| lima | postgresql | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| apple-container | sqlite | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| apple-container | postgresql | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |

- All eight configurations: upstream requires root; selected execution route is not root

## P03

tests/chmod/02.t: 5 planned TAP assertions; upstream root prerequisite. fixed-posix-tap-v1.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| docker | postgresql | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| native | sqlite | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| native | postgresql | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| lima | sqlite | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| lima | postgresql | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| apple-container | sqlite | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| apple-container | postgresql | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |

- All eight configurations: upstream requires root; selected execution route is not root

## P04

tests/symlink/00.t: 14 planned TAP assertions; upstream root prerequisite. fixed-posix-tap-v1.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| docker | postgresql | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| native | sqlite | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| native | postgresql | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| lima | sqlite | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| lima | postgresql | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| apple-container | sqlite | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |
| apple-container | postgresql | NOT_RUN | COMPLETE | — | — | — | 0.00 | — | — | — | — |

- All eight configurations: upstream requires root; selected execution route is not root

## Preparation, limits and cleanup

No case inputs were allocated: prerequisites failed before preparation. Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final infrastructure cleanup: **COMPLETE**. Overall uninterrupted teardown wall: UNAVAILABLE. Serial resource-release commands total 2.493 s, including the refused deletion; diagnosis gaps and local-file cleanup are excluded from that sum.

All case Workspaces/Sandboxes/Store registrations released through public CLI. Owned Lima and Apple machines removed; Docker worker stopped and private data volume deleted; PostgreSQL server/container/data volume removed; owned tool image, temporary archive, source/build trees, home, input directory and credential file removed. Apple Container service restored to its prior stopped state. Small pinned tool binaries/recipes and local receipts retained; shared dependencies, earlier product artifacts/worktree and other owners resources preserved.

Initial volume deletion was refused because the stopped worker container retained its mount. Inspected exact exited worker ownership/PID0, removed it, then explicitly released the volume after the dependency changed. Original failed deletion retained; no uncertain operation replay. Overall uninterrupted teardown wall is UNAVAILABLE because finalization resumed after diagnosis; serial release-command sum is measured separately.

Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

Upstream source commit: `85a8aea9e685999ef0540392fd80535f873d7ff7`. Exact flags and setup: [frozen suite definition](https://github.com/Ephemeral-AI-Lab/layerfs-benchmark/blob/5b47f0be45ce4e9c6d8d0416dca89dc74f7d0f39/pjdfstest/src/cases.py).

Prerequisite blocker: all public CLI execution routes use UID 501/GID 20. The product rejects UID/GID zero and enforces no-new-privileges on guest routes. Upstream pjdfstest requires root; no supported root command route exists. All TAP counts above are planned assertions, with no LayerFS pjdfstest execution PASS claim.

