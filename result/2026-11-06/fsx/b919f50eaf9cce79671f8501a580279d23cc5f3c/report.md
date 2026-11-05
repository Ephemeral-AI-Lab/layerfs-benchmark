# fsx — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: PASS.** 8 registered rows; execution {'PASS': 8}. Final infrastructure cleanup: **COMPLETE**.

LayerFS `b919f50eaf9cce79671f8501a580279d23cc5f3c` (remote `layerfs_v2_0_0`, resolved at campaign start). Harness: 706d20a00f6b09324da6c95f532970dcaa5852d3. Matched release CLI/daemon/Linux bundle reused after hash checks; no product changes.

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 8}.

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

## X01

1,000 operation slots, seed 1, file ≤8 MiB, operation ≤64 KiB; read/write/truncate and upstream consistency checks. Skipped slots remain explicit. fsx-X01-v2-secfs-portable.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 303.49 | 240.66 | 16.79 | 252.82 | 869.66 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 513.58 | 196.89 | 56.46 | 211.79 | 1139.62 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 25.43 | 1054.63 | 74.20 | 68.19 | 1292.32 | 4.38 | 4.42 | 1.49 |
| native | postgresql | PASS | COMPLETE | 72.59 | 251.69 | 125.34 | 85.76 | 660.88 | 1.28 | 2.22 | 0.58 |
| lima | sqlite | PASS | COMPLETE | 740.00 | 205.35 | 13.72 | 143.75 | 1172.30 | 0.85 | 0.82 | 1.35 |
| lima | postgresql | PASS | COMPLETE | 895.13 | 172.82 | 56.73 | 131.05 | 1433.89 | 0.88 | 1.00 | 1.26 |
| apple-container | sqlite | PASS | COMPLETE | 60.60 | 200.34 | 12.99 | 56.99 | 390.39 | 0.83 | 0.77 | 0.45 |
| apple-container | postgresql | PASS | COMPLETE | 286.68 | 215.07 | 86.22 | 91.51 | 966.66 | 1.09 | 1.53 | 0.85 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Requested slots | Completed slots | Effective operations | Skipped slots | Reads | Writes | Truncates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker / sqlite | 1000 | 1000 | 997 | 3 | 539 | 237 | 221 |
| docker / postgresql | 1000 | 1000 | 997 | 3 | 539 | 237 | 221 |
| native / sqlite | 1000 | 1000 | 997 | 3 | 539 | 237 | 221 |
| native / postgresql | 1000 | 1000 | 997 | 3 | 539 | 237 | 221 |
| lima / sqlite | 1000 | 1000 | 997 | 3 | 539 | 237 | 221 |
| lima / postgresql | 1000 | 1000 | 997 | 3 | 539 | 237 | 221 |
| apple-container / sqlite | 1000 | 1000 | 997 | 3 | 539 | 237 | 221 |
| apple-container / postgresql | 1000 | 1000 | 997 | 3 | 539 | 237 | 221 |

## Preparation, limits and cleanup

Attempted row preparation: 0.947 s total; maximum 0.179 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final runtime infrastructure cleanup: **COMPLETE**. Overall teardown wall: **2.981238417 s**; serial resource-release commands total 2.657856831 s, excluding local-file cleanup from that sum.

All case Workspaces/Sandboxes/Stores released through public CLI. Owned Lima/Apple machines, Docker worker/container/data volume, PostgreSQL server/container/data volume, tool image, private home, secret, temporary input/archive and released build/source trees removed. Apple Container service restored to its prior stopped state. Small pinned binaries, recipes and local receipts retained; shared dependencies, earlier product artifacts/worktree and other owners resources preserved. Linux private target/Cargo volumes were removed separately; native target/debug and release remain protected because an active host VM holds files.

Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

Upstream source commit: `edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed`. Exact flags and setup: [frozen suite definition](https://github.com/Ephemeral-AI-Lab/layerfs-benchmark/blob/706d20a00f6b09324da6c95f532970dcaa5852d3/fsx/src/cases.py).

## Profile history and interpretation

| Profile / product | PASS | FAIL | NOT_RUN | Disposition |
| --- | ---: | ---: | ---: | --- |
| xfstests v1 / b919f50e | 6 | 0 | 2 | Retired Linux-only profile; native prerequisites retained |
| Portable secfs.test v2 / b919f50e | 8 | 0 | 0 | Current selected X01 checkpoint |

All eight current rows completed 1,000 slots: 997 effective operations and three upstream skips. Intrinsic size/read consistency checks remained enabled. This new portable source/profile was frozen before execution; its operation counts and timings do not form a paired claim with xfstests v1.

[Immutable earlier report](https://github.com/Ephemeral-AI-Lab/layerfs-benchmark/blob/11b252ab4bf530fdfd7dd02822ee6f571b496e14/result/2026-11-06/fsx/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) preserves the original released outcomes and configuration. Logs, receipts, manifests and source snapshots remain local and unpublished.
