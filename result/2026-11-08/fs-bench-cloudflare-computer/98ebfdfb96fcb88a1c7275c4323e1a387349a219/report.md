# fs-bench-cloudflare-computer — Cloudflare's fs-bench.sh on LayerFS

> Status: Diagnostic observations; every timing and ratio is performance-ineligible.

**4 of 8 rows ran all twelve scenarios (4 NOT_RUN, 4 PASS); final cleanup COMPLETE.** One sample per row; every time and ratio is an INELIGIBLE diagnostic.

LayerFS `98ebfdfb96fcb88a1c7275c4323e1a387349a219` (remote `layerfs_v2_0_0`, resolved at campaign start). Campaigns: `fbcc-1108a` (harness `6f20516a7a`): Docker PostgreSQL, Docker SQLite, native PostgreSQL, native SQLite. All campaigns use the same CLI and daemon, Linux bundle and image. Each row runs Cloudflare Computer's byte-identical `script/fs-bench.sh` (Computer `de87919a4fd37242e960e13b7b3ba802d1eef0a0`, SHA-256 `0e2004339a9269b88c2de451d56575957477bde16b96a10cf1837519e37230ef`) once, with REPS=1, WARMUP=0, RANDOMIZE_TARGETS=0, no BASE, and the twelve offline scenarios. The script times each scenario itself with `date +%s%N`, inside the Workspace, in a fresh directory it removes afterwards. Computer itself is not measured.

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, one Exec running the script on the Workspace root, LayerFS Commit, unmount, Sandbox close and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker; kernel writeback off.

Ratios divide a machine's time by Docker's time for the same scenario and database; Docker = 1.00, below 1 means less time. `pure read`, `pure copy` and `overwrite` read or rewrite a file the script wrote just before its clock started, so they are own-write warm. The 64 MiB rows write zeros. The sum is a convenience total, not an agent turn.

Environment: Apple M3 Max (14 cores, 36 GiB), macOS 26.4.1; Docker Desktop 4.76.0 / Engine 29.5.2 (linuxkit 6.12.76, 8 CPUs, 7.75 GiB); dedicated PostgreSQL 17 container (1 CPU, 512 MiB) on the host at 127.0.0.1:50268; other owners' containers (two PostgreSQL servers, MinIO, three workers) ran on the same Docker Desktop; Lima and Apple Container not run.

Native macOS ships bash 3.2, which the script cannot run, so native rows put a pinned GNU bash 5.2.37 (source SHA-256 `9599b22ecd1d5787…`, binary `fbea3631ff823846…`) first on the Exec PATH, plus a small `sha256sum` wrapper that gives macOS's checker GNU's `-c --quiet` form. The workload command is byte-identical on every row. Native Workspaces are NFS mounts, and every `stat`, `mkdir` and `echo >` loop step launches a macOS process.

Host baseline: one sample recorded by campaign `fbcc-1108a` at 2026-11-07T22:40:03Z from `Darwin 25.4.0 arm64`, on a directory the recorder proved to be apfs, not NFS, with the same frozen script body, the same pinned bash (`fbea3631ff823846…`) and PATH as the native rows, one sample per campaign. It is host cost, not a LayerFS row: it has no create/mount/Exec/Commit/unmount/close lifecycle and is never counted as a ninth row. `native − host` is the LayerFS-attributable time per scenario, and it is only attributable when the sample's platform is the machine the native rows ran on.

| Build input | Identity |
| --- | --- |
| CLI (macOS, release, PostgreSQL) | `47fd699cde3b2877637d2f6f8c7ec88d90e4f693eaf1d15e0ea3c90557450cb7` |
| Native daemon | `eb3a1c23a1fed93251af87fa72e82f289b6707825f8fe9ef1add00660e74e866` |
| Linux bundle seal | `a69bddd469ca7fb8046c950ee51f857ad6c37092893bbadf1912a760712716a3` |
| Sandbox tool image | `sha256:99c3223c2c8305fe80cf1fcb303588496bbb95c68c2cb0acab17d65966377cbb` |
| Namespace archive config | `sha256:7785fc0cff9d72bbf1e8c5e5f95aead60c9c1f9e311d4fdefb684f293a8e1770` |

## Rows

CLI call times in milliseconds, including launch and routing. Create is Sandbox creation; Exec is the whole script run; Commit is the LayerFS Commit; Cleanup is Sandbox close and Store remove/disconnect; End-to-end also includes mount and unmount and excludes preparation.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Commit result |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Docker | SQLite | PASS | COMPLETE | 5,345.0 | 6,384.9 | 21.2 | 562.8 | 12,392.9 | UpToDate |
| Docker | PostgreSQL | PASS | COMPLETE | 273.4 | 6,036.4 | 89.6 | 137.9 | 6,729.1 | UpToDate |
| native | SQLite | PASS | COMPLETE | 940.4 | 24,555.2 | 184.6 | 141.3 | 25,925.2 | UpToDate |
| native | PostgreSQL | PASS | COMPLETE | 57.1 | 23,711.7 | 145.4 | 84.4 | 24,094.4 | UpToDate |
| Lima | SQLite | NOT_RUN | NOT_RUN | — | — | — | — | — | — |
| Lima | PostgreSQL | NOT_RUN | NOT_RUN | — | — | — | — | — | — |
| Apple Container | SQLite | NOT_RUN | NOT_RUN | — | — | — | — | — | — |
| Apple Container | PostgreSQL | NOT_RUN | NOT_RUN | — | — | — | — | — | — |

- Lima SQLite, Lima PostgreSQL, Apple Container SQLite, Apple Container PostgreSQL: not in this campaign: the owner asked for native, host and Docker Desktop rows only (2026-11-08)
- native SQLite ran under a 60 s budget (owner, 2026-11-06: native macOS launches one process per file on an NFS mount; the frozen script needs more than 25 s there); other rows use 25 s. This row took 25,925.2 ms end to end.
- native PostgreSQL ran under a 60 s budget (owner, 2026-11-06: native macOS launches one process per file on an NFS mount; the frozen script needs more than 25 s there); other rows use 25 s. This row took 24,094.4 ms end to end.

## Scenario times, SQLite

| Scenario | Cache state | host ms | Docker ms | native ms | Lima ms | Apple Container ms | host / Docker | native − host ms | native / Docker | Lima / Docker | Apple Container / Docker |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| create 1000 files | self-contained | 105.0 | 257.7 | 762.8 | — | — | 0.41 | 657.8 | 2.96 | — | — |
| stat 1000 files | self-contained | 7,225.0 | 956.4 | 7,766.4 | — | — | 7.55 | 541.4 | 8.12 | — | — |
| rm 1000 files | self-contained | 241.4 | 458.4 | 1,283.1 | — | — | 0.53 | 1,041.7 | 2.80 | — | — |
| mkdir tree (10x10x10) | self-contained | 3,312.5 | 718.5 | 4,562.1 | — | — | 4.61 | 1,249.6 | 6.35 | — | — |
| find tree | self-contained | 3,399.0 | 758.5 | 4,890.4 | — | — | 4.48 | 1,491.4 | 6.45 | — | — |
| write 64 MiB | self-contained | 44.7 | 190.6 | 150.3 | — | — | 0.23 | 105.6 | 0.79 | — | — |
| copy 64 MiB | self-contained | 76.3 | 360.8 | 264.7 | — | — | 0.21 | 188.4 | 0.73 | — | — |
| read 64 MiB | self-contained | 63.5 | 169.6 | 141.7 | — | — | 0.37 | 78.2 | 0.84 | — | — |
| pure read 64 MiB | own-write warm | 16.6 | 18.9 | 15.6 | — | — | 0.88 | -1.0 | 0.83 | — | — |
| pure copy 64 MiB | own-write warm | 36.7 | 196.7 | 137.8 | — | — | 0.19 | 101.0 | 0.70 | — | — |
| overwrite 64 MiB | own-write warm | 17.7 | 119.3 | 84.6 | — | — | 0.15 | 66.9 | 0.71 | — | — |
| git init + commit 100 files | self-contained | 219.0 | 188.1 | 610.9 | — | — | 1.16 | 391.9 | 3.25 | — | — |
| Sum of scenarios | — | 14,757.5 | 4,393.5 | 20,670.4 | — | — | 3.36 | 5,913.0 | 4.70 | — | — |

## Scenario times, PostgreSQL

| Scenario | Cache state | host ms | Docker ms | native ms | Lima ms | Apple Container ms | host / Docker | native − host ms | native / Docker | Lima / Docker | Apple Container / Docker |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| create 1000 files | self-contained | 105.0 | 196.2 | 867.4 | — | — | 0.54 | 762.4 | 4.42 | — | — |
| stat 1000 files | self-contained | 7,225.0 | 796.1 | 7,674.5 | — | — | 9.08 | 449.4 | 9.64 | — | — |
| rm 1000 files | self-contained | 241.4 | 430.6 | 1,270.3 | — | — | 0.56 | 1,028.9 | 2.95 | — | — |
| mkdir tree (10x10x10) | self-contained | 3,312.5 | 724.7 | 4,347.1 | — | — | 4.57 | 1,034.6 | 6.00 | — | — |
| find tree | self-contained | 3,399.0 | 754.6 | 4,368.1 | — | — | 4.50 | 969.2 | 5.79 | — | — |
| write 64 MiB | self-contained | 44.7 | 164.9 | 139.4 | — | — | 0.27 | 94.8 | 0.85 | — | — |
| copy 64 MiB | self-contained | 76.3 | 344.5 | 250.9 | — | — | 0.22 | 174.6 | 0.73 | — | — |
| read 64 MiB | self-contained | 63.5 | 164.0 | 128.3 | — | — | 0.39 | 64.8 | 0.78 | — | — |
| pure read 64 MiB | own-write warm | 16.6 | 13.1 | 18.8 | — | — | 1.27 | 2.3 | 1.44 | — | — |
| pure copy 64 MiB | own-write warm | 36.7 | 196.7 | 165.4 | — | — | 0.19 | 128.7 | 0.84 | — | — |
| overwrite 64 MiB | own-write warm | 17.7 | 104.4 | 117.2 | — | — | 0.17 | 99.5 | 1.12 | — | — |
| git init + commit 100 files | self-contained | 219.0 | 181.5 | 528.5 | — | — | 1.21 | 309.5 | 2.91 | — | — |
| Sum of scenarios | — | 14,757.5 | 4,071.3 | 19,875.9 | — | — | 3.62 | 5,118.5 | 4.88 | — | — |

## Main observations

- Sum of scenario times ranged from 4,071.3 ms (Docker PostgreSQL) to 20,670.4 ms (native SQLite).
- Longest complete row: 25,925.2 ms.
- LayerFS Commit results: 4 UpToDate; the script removes every directory it creates, so nothing new is committed.
- Native macOS is the slowest machine: `stat 1000 files` took 7,766.4 ms against Docker's 956.4 ms on SQLite. The 1,000-step loops launch one macOS process per file on an NFS mount; the 64 MiB rows are close to Docker.
- The host baseline is the same frozen script on a plain APFS folder outside LayerFS, one sample per campaign and unrelated to the database, so both tables share it. It is host cost, not a LayerFS row; `native − host` is the LayerFS-attributable part and the `native / Docker` and `host / Docker` ratios stay the only cross-machine comparisons.
- Single unrepeated samples under shared host load: differences of a few tens of percent between rows are within what one sample can show and are not a ranking.

## Limits and cleanup

Each row is one unrepeated sample on a shared macOS host. Other owners' containers and VMs ran during the campaign and were left alone. No cache was cleared or proven cold. Execution PASS means the CLI lifecycle succeeded and the script reported one sample for each of the twelve scenarios; it is not independent content verification (every scenario deletes its own directory).

Final cleanup: **COMPLETE**. All four rows released their Sandbox and Store through the CLI. Afterwards the campaign's shared infrastructure was released once, in order: the Docker machine's worker (`machine stop docker`), its container `lfs-58ff7613-docker` and data volume, then the dedicated PostgreSQL 17 server `fbcc-1108a-pg` and its data volume. Verified afterwards: no campaign container or volume remains, mount holds no 127.0.0.1 NFS Workspace, no campaign daemon runs, and the campaign home lists no Store and no Sandbox. Kept for audit: the pinned release CLI and daemon, the sealed Linux bundle, the suite image (the same image as the 2026-11-06 run, `sha256:99c3223c…`), the four row receipts, the host sample and the pinned native tool folder.

Scope and conditions, stated plainly: the owner asked for the native, host and Docker Desktop rows only, so Lima and Apple Container are NOT_RUN. Every row passed on its first attempt, and nothing was resampled. Host load (1-, 5-, 15-minute) before each row: native SQLite 6.53/12.21/10.60, native PostgreSQL 7.07/11.61/10.45, host 7.30/11.22/10.35, Docker SQLite 7.36/10.97/10.28, Docker PostgreSQL 7.35/10.79/10.23. On 2026-11-06 the same rows started at about 6.3–7.9 on all three averages. Other owners' containers were running on Docker Desktop throughout. Docker SQLite's 5.3 s Sandbox create includes the first copy of the bundle into the new Docker machine. Measured outside the harness just before the rows: one macOS process start cost 2.3 ms (`/usr/bin/true`) and 6.6 ms (`/usr/bin/stat`), which matches the out-of-sandbox figures in layerfs-project#73, so the agent shell adds no process-start cost.


## Diagnostic: why Docker Desktop is slower than on 2026-11-06

Docker Desktop's SQLite sum rose from 3,594.3 ms (2026-11-06, `6d820c756b`) to 4,393.5 ms in this report. To separate the build from the day, three more single samples were taken right after this campaign, back to back on the same Docker Desktop, with the same suite image (`sha256:99c3223c…`). They are not rows of this report:

- `fbcc-1108b`: Docker SQLite on the old build `6d820c756b`. The CLI and daemon are the 2026-11-06 binaries (`da25a81b…`, `b0b961bf…`). The Linux bundle was rebuilt from the same source and is not byte-identical (`91ebef3b…`, against `05891b57…` on 2026-11-06).
- `fbcc-1108c`: Docker SQLite on this report's build `98ebfdfb96`, same bundle.
- A plain container: the same command body on the image, in the container's own filesystem, with no LayerFS.

| Scenario | old, 2026-11-06 | old, today | new, this report | new, today | plain container, today |
| --- | ---: | ---: | ---: | ---: | ---: |
| create 1000 files | 281.5 | 449.3 | 257.7 | 198.6 | 32.9 |
| stat 1000 files | 693.2 | 1,208.3 | 956.4 | 852.5 | 695.7 |
| rm 1000 files | 337.4 | 645.4 | 458.4 | 475.1 | 30.1 |
| mkdir tree (10x10x10) | 561.6 | 1,010.2 | 718.5 | 723.8 | 588.7 |
| find tree | 718.7 | 764.3 | 758.5 | 890.3 | 588.3 |
| write 64 MiB | 152.7 | 174.1 | 190.6 | 213.4 | 25.0 |
| copy 64 MiB | 312.6 | 359.5 | 360.8 | 383.8 | 50.6 |
| read 64 MiB | 139.9 | 173.5 | 169.6 | 192.9 | 41.5 |
| pure read 64 MiB | 11.6 | 15.8 | 18.9 | 13.0 | 15.5 |
| pure copy 64 MiB | 164.2 | 196.7 | 196.7 | 198.2 | 23.5 |
| overwrite 64 MiB | 82.0 | 103.7 | 119.3 | 112.4 | 17.8 |
| git init + commit 100 files | 138.8 | 198.0 | 188.1 | 184.0 | 23.1 |
| **Sum** | **3,594.3** | **5,298.8** | **4,393.5** | **4,437.8** | **2,132.7** |
| Exec (CLI call) | 5,173.9 | 7,415.9 | 6,384.9 | 6,509.2 | — |
| Sandbox create | 325.0 | 420.0 | 5,345.0 | 4,247.8 | — |

Host load (1-, 5-, 15-minute) before each run: old today 11.74/11.07/10.21; new today 13.01/11.35/10.32; plain container 10.22/10.82/10.16.

- **The slowdown is the day, not the build.** The same old build took 5,298.8 ms today against 3,594.3 ms on 2026-11-06. Back to back today, the new build's sum is 16% lower (4,437.8 against 5,298.8) and its Exec 12% lower.
- **The new build is faster on the per-file loops** (create, stat, rm, mkdir). The likely cause is the new route between the two builds: since layerfs-project#111 (D-8), the docker machine runs each Sandbox in namespaces inside one worker container instead of one container per Sandbox. It may be slower on 64 MiB I/O (write 174.1 → 213.4 ms), which is within what one sample can show; it needs operation counts, not more timings.
- **Sandbox create on a fresh docker machine is about 10× slower on the new build** (4.2–5.3 s against 0.3–0.4 s). Each of these was the machine's first Sandbox; later creates were not measured.
- **The post-11-06 Commit and storage work is not visible here.** The script deletes everything it creates, so every Commit is `UpToDate` and no Store bytes are measured.
- **LayerFS's cost on Docker Desktop** is about 2.3 s over the plain container (sum 4,437.8 against 2,132.7), against 5.9 s on native over plain APFS in this report.

Single samples under shared load: INELIGIBLE diagnostics, not a ranking. Each diagnostic campaign released its worker container and volume; the old build's worktree and Linux build volumes were removed afterwards.
