# fsstress — CLI execution and cleanup

> Status: Retired checkpoint; timings are performance-ineligible.

**Superseded by the [corrected-product checkpoint](../b9ad9edd7ea3a9314625dee53466aa59a7ea69c7/report.md).** The INCOMPLETE result below is preserved history.

**Diagnostic terminal: INCOMPLETE.** 8 registered rows; execution {'PASS': 2, 'FAIL': 1, 'NOT_RUN': 5}. Final infrastructure cleanup: **COMPLETE**.

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

## S01

Two processes × 512 requested operation slots, seed 1; frozen operation weights and per-operation allocation bounds. Effective work, skipped slots and expected errno are separate below. fsstress-S01-v2.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | FAIL | COMPLETE | 314.24 | 178.45 | — | 258.57 | 793.79 | — | — | — |
| docker | postgresql | NOT_RUN | COMPLETE | — | — | — | — | — | — | — | — |
| native | sqlite | PASS | COMPLETE | 26.00 | 794.27 | 174.15 | 70.70 | 1135.14 | — | — | — |
| native | postgresql | PASS | COMPLETE | 72.96 | 318.86 | 301.10 | 82.24 | 918.25 | — | — | — |
| lima | sqlite | NOT_RUN | COMPLETE | — | — | — | — | — | — | — | — |
| lima | postgresql | NOT_RUN | COMPLETE | — | — | — | — | — | — | — | — |
| apple-container | sqlite | NOT_RUN | COMPLETE | — | — | — | — | — | — | — | — |
| apple-container | postgresql | NOT_RUN | COMPLETE | — | — | — | — | — | — | — | — |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Requested slots | Completed slots | Effective operations | Skipped slots | Expected errno | Unexpected errors | Page bytes | Requested write bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| native / sqlite | 1024 | 1024 | 921 | 61 | 42 | 0 | 16384 | 27481153 |
| native / postgresql | 1024 | 1024 | 921 | 61 | 42 | 0 | 16384 | 27481153 |

- docker/sqlite: exec: workload exit 1
- docker/postgresql, lima/sqlite, lima/postgresql, apple-container/sqlite, apple-container/postgresql: Withdrawn before attempt after Docker/SQLite exposed the pinned product contract rejecting symlink hard links. v2 failure retained; product capability assessment in progress.

## Preparation, limits and cleanup

Attempted row preparation: 0.286 s total; maximum 0.174 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final runtime infrastructure cleanup: **COMPLETE**. Overall teardown wall: **2.981238417 s**; serial resource-release commands total 2.657856831 s, excluding local-file cleanup from that sum.

All case Workspaces/Sandboxes/Stores released through public CLI. Owned Lima/Apple machines, Docker worker/container/data volume, PostgreSQL server/container/data volume, tool image, private home, secret, temporary input/archive and released build/source trees removed. Apple Container service restored to its prior stopped state. Small pinned binaries, recipes and local receipts retained; shared dependencies, earlier product artifacts/worktree and other owners resources preserved. Linux private target/Cargo volumes were removed separately; native target/debug and release remain protected because an active host VM holds files.

Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

Upstream source commit: `edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed`. Exact flags and setup: [frozen suite definition](https://github.com/Ephemeral-AI-Lab/layerfs-benchmark/blob/706d20a00f6b09324da6c95f532970dcaa5852d3/fsstress/src/cases.py).

## Retained failure and successor

This report records the **retired** b919f50e v2 checkpoint, not an active full-matrix success. Native SQLite and PostgreSQL passed; Docker/SQLite failed after six symlink-inode hardlinks returned EPERM. The five later selections were withdrawn before any product attempt. The product explicitly restricted hardlinks to regular files; this is a retained product-capability failure, not an allowed errno or a privilege workaround.

| Profile / product | PASS | FAIL | NOT_RUN | Disposition |
| --- | ---: | ---: | ---: | --- |
| xfstests v1 / b919f50e | 6 | 0 | 2 | Retired Linux-only profile |
| Portable secfs.test v2 / b919f50e | 2 | 1 | 5 | Retained failure; remaining selections withdrawn |
| Same portable v2 / b9ad9edd | 8 | 0 | 0 | Separate corrected-product checkpoint |

The failed row's compact metric table is unavailable because strict result admission rejected its six unexpected errors; its receipt retains 1,024 attempted slots and the exact error records. Failure timing stays diagnostic. The [corrected-product report](../b9ad9edd7ea3a9314625dee53466aa59a7ea69c7/report.md) uses the unchanged workload and error policy at a new matched product identity. No old/new timing ratio is claimed.

[Immutable earlier report](https://github.com/Ephemeral-AI-Lab/layerfs-benchmark/blob/11b252ab4bf530fdfd7dd02822ee6f571b496e14/result/2026-11-06/fsstress/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) preserves the original released outcomes and configuration. Logs, receipts, manifests and source snapshots remain local and unpublished.
