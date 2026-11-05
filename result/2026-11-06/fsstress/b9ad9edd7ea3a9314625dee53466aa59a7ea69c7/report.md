# fsstress — CLI execution and cleanup

> Status: Diagnostic observations; timings are performance-ineligible.

**Diagnostic terminal: PASS.** 8 registered rows; execution {'PASS': 8}. Final infrastructure cleanup: **COMPLETE**.

LayerFS `b9ad9edd7ea3a9314625dee53466aa59a7ea69c7` (clean derived symlink-hard-link fix from remote layerfs_v2_0_0 reference b919f50eaf9cce79671f8501a580279d23cc5f3c). Harness: d2e735b3a723de9b5bc9a3b220d406f841773736. Matched release CLI/native daemon/Linux worker/daemon/helper bundle built from the clean derived correction; source fingerprint `7c0542e033bda8960fee08131f5fe915382dd2270cb6d735b908bfc26c81fbfd`. The v2 workload and error policy are unchanged; old product artifacts are excluded from this checkpoint.

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, Exec, LayerFS Commit, unmount, Sandbox close, and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker. Independent committed-result verification is optional. Tool-internal checks remain enabled. Actual verification outcomes: {'SKIPPED': 8}.

Warm builds, tools, ready machines and closed setup are reused. No public CLI protocol demonstrates cold live-Workspace state before Commit. Every timing and Docker ratio below is an **INELIGIBLE diagnostic**.

Times are milliseconds of CLI calls including launch/routing. Create means Sandbox creation. Cleanup includes Sandbox close and Store remove/disconnect; End-to-end also includes mount/unmount and intervening harness work, excludes preparation, Python startup and optional proof. Ratios divide the machine's time by Docker's time for the same cell/backend; Docker = 1.00, below 1 means less elapsed time. One sample per row, no median or repeatability claim.

Environment: Apple M3 Max / macOS26.4.1 arm64, 36GiB RAM; native NFS; Docker FUSE; Lima VZ and Apple Container namespaces/FUSE (2CPU/2GiB/8GiB data each). Dedicated PostgreSQL17.11 Docker server 1CPU/512MiB. Effective UID501/GID20 confirmed on all routes. Host TCP port 63341 rewritten to Docker host.docker.internal, Lima192.168.5.2 and Apple gateway.. Command-only timing, phase-scoped remote CPU/memory, Store/WAL/overlay/temp growth and server storage are UNAVAILABLE; no storage-efficiency claim.

| Build input | SHA-256 / identity |
| --- | --- |
| CLI | `3118a65cdacd6198bce72e47aefa5ff1640332d55dbe47e69b5b224a67e91e5a` |
| Native daemon | `9a86e883d697af8c41619f74181bd14480d58403f3328225615892c02ae802bb` |
| Linux bundle seal | `b36658002ba74461217437144b290a8312d847fbd8cec84e40033e1203ae8ca8` |
| Docker tool image | `sha256:cc0814884e1b2acb5ffee43792faf40e7dbb3573ca157ab22af4179632c64dd0` |
| Namespace archive config | `sha256:965c442900ee25039a17ce22d733e01ec846ab870fe5a478e76d5fd983e68403` |

## S01

Two processes × 512 requested operation slots, seed 1; frozen operation weights and per-operation allocation bounds. Effective work, skipped slots and expected errno are separate below. fsstress-S01-v2.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | PASS | COMPLETE | 392.06 | 194.24 | 88.98 | 250.65 | 1014.72 | 1.00 | 1.00 | 1.00 |
| docker | postgresql | PASS | COMPLETE | 660.55 | 161.42 | 201.50 | 312.39 | 1549.39 | 1.00 | 1.00 | 1.00 |
| native | sqlite | PASS | COMPLETE | 56.97 | 402.60 | 287.87 | 95.67 | 946.68 | 2.07 | 3.24 | 0.93 |
| native | postgresql | PASS | COMPLETE | 114.42 | 424.39 | 448.63 | 118.76 | 1287.11 | 2.63 | 2.23 | 0.83 |
| lima | sqlite | PASS | COMPLETE | 743.75 | 144.42 | 84.72 | 160.40 | 1232.18 | 0.74 | 0.95 | 1.21 |
| lima | postgresql | PASS | COMPLETE | 1016.05 | 152.44 | 235.42 | 182.78 | 1818.92 | 0.94 | 1.17 | 1.17 |
| apple-container | sqlite | PASS | COMPLETE | 77.45 | 188.66 | 79.63 | 79.62 | 524.13 | 0.97 | 0.89 | 0.52 |
| apple-container | postgresql | PASS | COMPLETE | 327.48 | 193.19 | 278.06 | 122.11 | 1226.17 | 1.20 | 1.38 | 0.79 |

Tool observations (intrinsic checks only; rates retain their upstream denominator):

| Machine / database | Requested slots | Completed slots | Effective operations | Skipped slots | Expected errno | Unexpected errors | Page bytes | Requested write bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker / sqlite | 1024 | 1024 | 932 | 52 | 40 | 0 | 4096 | 6171091 |
| docker / postgresql | 1024 | 1024 | 932 | 52 | 40 | 0 | 4096 | 6171091 |
| native / sqlite | 1024 | 1024 | 921 | 61 | 42 | 0 | 16384 | 27481153 |
| native / postgresql | 1024 | 1024 | 921 | 61 | 42 | 0 | 16384 | 27481153 |
| lima / sqlite | 1024 | 1024 | 932 | 52 | 40 | 0 | 4096 | 6171091 |
| lima / postgresql | 1024 | 1024 | 932 | 52 | 40 | 0 | 4096 | 6171091 |
| apple-container / sqlite | 1024 | 1024 | 932 | 52 | 40 | 0 | 4096 | 6171091 |
| apple-container / postgresql | 1024 | 1024 | 932 | 52 | 40 | 0 | 4096 | 6171091 |

## Preparation, limits and cleanup

Attempted row preparation: 1.375 s total; maximum 0.258 s (25 s bound). Preparation is outside the case timers; database creation and initial shared infrastructure commands are separate. Tools/image were built once and machines/server reused; each input was independent and consumed once.

Final runtime infrastructure cleanup: **COMPLETE**. Overall teardown wall: **2.981238417 s**; serial resource-release commands total 2.657856831 s, excluding local-file cleanup from that sum.

All case Workspaces/Sandboxes/Stores released through public CLI. Owned Lima/Apple machines, Docker worker/container/data volume, PostgreSQL server/container/data volume, tool image, private home, secret, temporary input/archive and released build/source trees removed. Apple Container service restored to its prior stopped state. Small pinned binaries, recipes and local receipts retained; shared dependencies, earlier product artifacts/worktree and other owners resources preserved. Linux private target/Cargo volumes were removed separately; native target/debug and release remain protected because an active host VM holds files.

Execution PASS is a checked CLI lifecycle and accepted tool result, not independent committed-content proof or cold performance qualification. All failed and unsupported rows remain visible. Measured rows ran serially; tools/builds and infrastructure preparation did not overlap them.

External host isolation was not established; report/audit/Git activity overlapped some samples and other owners' processes/resources were preserved. No campaign build, provisioning, server restart or cache reset overlapped a measured row.

Upstream source commit: `edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed`. Exact flags and setup: [frozen suite definition](https://github.com/Ephemeral-AI-Lab/layerfs-benchmark/blob/d2e735b3a723de9b5bc9a3b220d406f841773736/fsstress/src/cases.py).

## Product correction, proof and retained history

| Profile / product | PASS | FAIL | NOT_RUN | Disposition |
| --- | ---: | ---: | ---: | --- |
| xfstests v1 / b919f50e | 6 | 0 | 2 | Retired Linux-only profile |
| Portable secfs.test v2 / b919f50e | 2 | 1 | 5 | Retained EPERM failure; five withdrawn selections |
| Same portable v2 / b9ad9edd | 8 | 0 | 0 | Current corrected-product checkpoint |

All current rows account for 1,024 slots, two workers with 512 each, and zero unexpected errors. Native rows have 921 successful operations, 42 expected errors and 61 skips; Linux rows have 932 successful operations, 40 expected errors and 52 skips. Source-derived page sizes and libc sequences differ, so identical flags and seeds do not establish identical byte work. Requested-write bytes are upstream logged request lengths, not transferred bytes. Linux symlink hardlinks now succeed; the predeclared narrow Darwin dangling-symlink ENOENT allowance is unchanged.

The [product correction (PR #580)](https://github.com/Ephemeral-AI-Lab/layerfs/pull/580) permits Workspace links to symlink inodes and preserves exact reachable counts, opaque targets, directory single parentage and Commit/remount behavior. Object encoding and database schema are unchanged; older readers can reject the expanded symlink-count semantics. Project Init and recursive-copy preservation of symlink alias identity remain outside this correction. The [retired b919f50e report](../b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) retains the failure.

Product validation passed **135 focused checks** (106 core, 21 Workspace, six NFS, two real FUSE). An initial captured-test lifecycle failure is retained; its fixture was corrected to install before the next capture. Separate public CLI proof-v2 passed all eight machine/database configurations through create, inherited aliases, removal, Commit and fresh mounts; maximum complete proof was **4.185105791 s**, within its 9.5 s budget. This proof is separate from the benchmark's default SKIPPED optional verification.

The original public CLI proof-v1 failed native/SQLite before LINK when the selected macOS NFS client rejected a non-UTF8 symlink target with EINVAL. Its failed receipt is retained and cleanup was resolved separately after public status proved Idle/no pending merge/no base, followed by explicit discard, close and Store removal. Proof-v2 froze one shared ASCII dangling target prospectively and passed eight rows. Canonical, Workspace, FUSE and NFS-wire tests retain opaque non-UTF8 coverage; this does not claim arbitrary-byte support through every host-client route. No proof or workload failure was relabeled.

[Immutable earlier report](https://github.com/Ephemeral-AI-Lab/layerfs-benchmark/blob/11b252ab4bf530fdfd7dd02822ee6f571b496e14/result/2026-11-06/fsstress/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) preserves the original released outcomes and configuration. Logs, receipts, manifests and source snapshots remain local and unpublished.
