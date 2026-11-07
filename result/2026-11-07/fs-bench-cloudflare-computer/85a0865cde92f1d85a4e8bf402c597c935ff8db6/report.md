# fs-bench-cloudflare-computer — Cloudflare's fs-bench.sh on LayerFS

> Status: Diagnostic observations; every timing and ratio is performance-ineligible.

**8 of 8 rows ran all twelve scenarios (8 PASS); final cleanup COMPLETE.** One sample per row; every time and ratio is an INELIGIBLE diagnostic.

LayerFS `85a0865cde92f1d85a4e8bf402c597c935ff8db6` (remote `layerfs_v2_0_0`, resolved at campaign start). Campaigns: `fbcc-1107a` (harness `47190eca27`): native SQLite; `fbcc-1107b` (harness `47190eca27`): native PostgreSQL; `fbcc-1107c` (harness `47190eca27`): native SQLite; `fbcc-1107d` (harness `47190eca27`): Apple Container PostgreSQL, Apple Container SQLite, Docker PostgreSQL, Docker SQLite, Lima PostgreSQL, Lima SQLite, native PostgreSQL, native SQLite; `fbcc-1107e` (harness `47190eca27`): native SQLite; `fbcc-1107f` (harness `47190eca27`): native SQLite. All campaigns use the same CLI and daemon, Linux bundle and image. Each row runs Cloudflare Computer's byte-identical `script/fs-bench.sh` (Computer `de87919a4fd37242e960e13b7b3ba802d1eef0a0`, SHA-256 `0e2004339a9269b88c2de451d56575957477bde16b96a10cf1837519e37230ef`) once, with REPS=1, WARMUP=0, RANDOMIZE_TARGETS=0, no BASE, and the twelve offline scenarios. The script times each scenario itself with `date +%s%N`, inside the Workspace, in a fresh directory it removes afterwards. Computer itself is not measured.

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, one Exec running the script on the Workspace root, LayerFS Commit, unmount, Sandbox close and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker; kernel writeback off.

Ratios divide a machine's time by Docker's time for the same scenario and database; Docker = 1.00, below 1 means less time. `pure read`, `pure copy` and `overwrite` read or rewrite a file the script wrote just before its clock started, so they are own-write warm. The 64 MiB rows write zeros. The sum is a convenience total, not an agent turn.

Environment: MacBook Air M2 (8 cores, 16 GiB), macOS 27.2 (26B123); Docker 29.5.2 in a Colima 0.10.3 vz VM (2 CPUs, 4 GiB); Lima 2.2.1 vz VM (2 CPUs, 2 GiB, Ubuntu 24.04 kernel); Apple container 1.6.1 (2 CPUs, 2 GiB); dedicated PostgreSQL 17.11 container (0.5 GiB) in that Colima VM, reached by the Linux machines at the host's LAN address and by the native rows at 127.0.0.1; Native rows and the host sample use a pinned GNU bash 5.2.37 with a sha256sum -c --quiet wrapper, BENCH_TOOL_ROOT=/opt/fs-bench-cloudflare-computer in the machines and the same folder on macOS. Sandbox image: the LayerFS Debian 12 runtime image (sha256:330c88af…) plus gawk 5.2.1, git 2.39.5 and the frozen script; Linux bundle sealed --profile release from this pin with that image.

Native macOS ships bash 3.2, which the script cannot run, so native rows put a pinned GNU bash 5.2.37(1)-release (source SHA-256 `9599b22ecd1d5787…`, binary `e9b45c8b731a0764…`) first on the Exec PATH, plus a small `sha256sum` wrapper that gives macOS's checker GNU's `-c --quiet` form. The workload command is byte-identical on every row. Native Workspaces are NFS mounts, and every `stat`, `mkdir` and `echo >` loop step launches a macOS process.

Host baseline: one sample recorded by campaign `fbcc-1107d` at 2026-11-07T12:11:47Z from `Darwin 27.2.0 arm64`, on a directory the recorder proved to be apfs, not NFS, with the same frozen script body, the same pinned bash (`e9b45c8b731a0764…`) and PATH as the native rows, one sample per campaign. It is host cost, not a LayerFS row: it has no create/mount/Exec/Commit/unmount/close lifecycle and is never counted as a ninth row. `native − host` is the LayerFS-attributable time per scenario, and it is only attributable when the sample's platform is the machine the native rows ran on.

| Build input | Identity |
| --- | --- |
| CLI (macOS, release, PostgreSQL) | `2bf5e16b18cf8575400feb74d6ed30883d0c609ef7ad748af5ba125855dc04d9` |
| Native daemon | `c52af4f214eecca0e8c370fe5094b5a2ba2b2a60c2c62d86e6a5b277c46a1208` |
| Linux bundle seal | `b330bd4a8aa9debc3722e4967104f34ad0e98278843c5c39cc38aed60cc81b11` |
| Sandbox tool image | `sha256:0a098c7b31b6fc585a1e57358adb6bb4fd392ca4a6e76efaed878e85c5cce46f` |
| Namespace archive config | `sha256:adbe5bd3e13f85ff6cefc81b174db09ab3023c1b6c96ff33c89f704147ea7656` |

## Rows

CLI call times in milliseconds, including launch and routing. Create is Sandbox creation; Exec is the whole script run; Commit is the LayerFS Commit; Cleanup is Sandbox close and Store remove/disconnect; End-to-end also includes mount and unmount and excludes preparation.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Commit result |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Docker | SQLite | PASS | COMPLETE | 309.3 | 4,029.0 | 17.5 | 197.4 | 4,597.8 | UpToDate |
| Docker | PostgreSQL | PASS | COMPLETE | 148.7 | 4,100.5 | 49.8 | 45.8 | 4,404.3 | UpToDate |
| native | SQLite | PASS | COMPLETE | 28.3 | 16,121.7 | 108.9 | 74.2 | 16,413.5 | UpToDate |
| native | PostgreSQL | PASS | COMPLETE | 42.2 | 16,396.9 | 110.7 | 56.6 | 16,686.4 | UpToDate |
| Lima | SQLite | PASS | COMPLETE | 929.1 | 4,205.1 | 23.2 | 196.8 | 5,425.9 | UpToDate |
| Lima | PostgreSQL | PASS | COMPLETE | 788.2 | 4,135.1 | 63.0 | 118.8 | 5,202.6 | UpToDate |
| Apple Container | SQLite | PASS | COMPLETE | 221.4 | 3,982.0 | 22.4 | 310.6 | 4,632.8 | UpToDate |
| Apple Container | PostgreSQL | PASS | COMPLETE | 152.7 | 3,895.1 | 57.9 | 59.7 | 4,270.8 | UpToDate |

- native SQLite ran under a 60 s budget (owner, 2026-11-06: native macOS launches one process per file on an NFS mount; the frozen script needs more than 25 s there); other rows use 25 s. This row took 16,413.5 ms end to end.
- native PostgreSQL ran under a 60 s budget (owner, 2026-11-06: native macOS launches one process per file on an NFS mount; the frozen script needs more than 25 s there); other rows use 25 s. This row took 16,686.4 ms end to end.
- Superseded attempt: native SQLite in `fbcc-1107a` was FAIL (Exec — ms, budget 60 s); it is retained, not relabeled.
- Superseded attempt: native PostgreSQL in `fbcc-1107b` was FAIL (Exec 16,831.9 ms, budget 60 s); it is retained, not relabeled.
- Superseded attempt: native SQLite in `fbcc-1107c` was FAIL (Exec 16,687.4 ms, budget 60 s); it is retained, not relabeled.
- Superseded attempt: native SQLite in `fbcc-1107d` was FAIL (Exec 16,768.3 ms, budget 60 s); it is retained, not relabeled.
- Superseded attempt: native SQLite in `fbcc-1107e` was FAIL (Exec 16,517.9 ms, budget 60 s); it is retained, not relabeled.

## Scenario times, SQLite

| Scenario | Cache state | host ms | Docker ms | native ms | Lima ms | Apple Container ms | host / Docker | native − host ms | native / Docker | Lima / Docker | Apple Container / Docker |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| create 1000 files | self-contained | 63.0 | 118.8 | 623.4 | 133.1 | 180.9 | 0.53 | 560.4 | 5.25 | 1.12 | 1.52 |
| stat 1000 files | self-contained | 4,295.6 | 530.9 | 4,445.8 | 570.0 | 514.8 | 8.09 | 150.2 | 8.37 | 1.07 | 0.97 |
| rm 1000 files | self-contained | 104.5 | 331.9 | 1,047.5 | 301.8 | 310.0 | 0.31 | 943.1 | 3.16 | 0.91 | 0.93 |
| mkdir tree (10x10x10) | self-contained | 1,937.3 | 454.9 | 2,955.6 | 466.1 | 403.9 | 4.26 | 1,018.3 | 6.50 | 1.02 | 0.89 |
| find tree | self-contained | 1,876.7 | 475.7 | 2,991.9 | 479.6 | 409.8 | 3.95 | 1,115.2 | 6.29 | 1.01 | 0.86 |
| write 64 MiB | self-contained | 46.9 | 120.1 | 107.5 | 444.6 | 116.6 | 0.39 | 60.6 | 0.90 | 3.70 | 0.97 |
| copy 64 MiB | self-contained | 107.8 | 271.7 | 209.2 | 272.9 | 247.5 | 0.40 | 101.4 | 0.77 | 1.00 | 0.91 |
| read 64 MiB | self-contained | 51.8 | 110.9 | 109.2 | 123.4 | 110.7 | 0.47 | 57.4 | 0.98 | 1.11 | 1.00 |
| pure read 64 MiB | own-write warm | 10.3 | 4.6 | 12.1 | 4.4 | 3.6 | 2.23 | 1.8 | 2.60 | 0.95 | 0.78 |
| pure copy 64 MiB | own-write warm | 72.8 | 141.9 | 106.7 | 136.7 | 129.4 | 0.51 | 33.9 | 0.75 | 0.96 | 0.91 |
| overwrite 64 MiB | own-write warm | 19.6 | 65.9 | 63.5 | 72.6 | 64.5 | 0.30 | 44.0 | 0.96 | 1.10 | 0.98 |
| git init + commit 100 files | self-contained | 112.2 | 71.6 | 446.4 | 117.2 | 104.7 | 1.57 | 334.2 | 6.23 | 1.64 | 1.46 |
| Sum of scenarios | — | 8,698.4 | 2,698.9 | 13,118.8 | 3,122.4 | 2,596.4 | 3.22 | 4,420.4 | 4.86 | 1.16 | 0.96 |

## Scenario times, PostgreSQL

| Scenario | Cache state | host ms | Docker ms | native ms | Lima ms | Apple Container ms | host / Docker | native − host ms | native / Docker | Lima / Docker | Apple Container / Docker |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| create 1000 files | self-contained | 63.0 | 183.8 | 640.0 | 170.4 | 189.8 | 0.34 | 577.0 | 3.48 | 0.93 | 1.03 |
| stat 1000 files | self-contained | 4,295.6 | 578.3 | 4,528.9 | 579.0 | 502.2 | 7.43 | 233.3 | 7.83 | 1.00 | 0.87 |
| rm 1000 files | self-contained | 104.5 | 316.8 | 1,084.1 | 331.0 | 323.1 | 0.33 | 979.6 | 3.42 | 1.05 | 1.02 |
| mkdir tree (10x10x10) | self-contained | 1,937.3 | 456.3 | 2,963.8 | 466.4 | 402.0 | 4.25 | 1,026.5 | 6.49 | 1.02 | 0.88 |
| find tree | self-contained | 1,876.7 | 487.1 | 3,031.2 | 492.6 | 423.2 | 3.85 | 1,154.4 | 6.22 | 1.01 | 0.87 |
| write 64 MiB | self-contained | 46.9 | 108.3 | 109.4 | 104.3 | 99.9 | 0.43 | 62.5 | 1.01 | 0.96 | 0.92 |
| copy 64 MiB | self-contained | 107.8 | 227.4 | 217.3 | 231.8 | 213.9 | 0.47 | 109.5 | 0.96 | 1.02 | 0.94 |
| read 64 MiB | self-contained | 51.8 | 108.5 | 109.0 | 106.9 | 103.2 | 0.48 | 57.2 | 1.00 | 0.99 | 0.95 |
| pure read 64 MiB | own-write warm | 10.3 | 4.6 | 10.8 | 3.8 | 4.5 | 2.27 | 0.5 | 2.38 | 0.82 | 0.98 |
| pure copy 64 MiB | own-write warm | 72.8 | 128.4 | 108.4 | 127.8 | 124.3 | 0.57 | 35.6 | 0.84 | 1.00 | 0.97 |
| overwrite 64 MiB | own-write warm | 19.6 | 64.2 | 67.4 | 65.9 | 60.3 | 0.30 | 47.8 | 1.05 | 1.03 | 0.94 |
| git init + commit 100 files | self-contained | 112.2 | 117.7 | 450.0 | 118.7 | 104.4 | 0.95 | 337.8 | 3.82 | 1.01 | 0.89 |
| Sum of scenarios | — | 8,698.4 | 2,781.4 | 13,320.4 | 2,798.5 | 2,550.6 | 3.13 | 4,621.9 | 4.79 | 1.01 | 0.92 |

## Main observations

- Sum of scenario times ranged from 2,550.6 ms (Apple Container PostgreSQL) to 13,320.4 ms (native PostgreSQL).
- Longest complete row: 16,686.4 ms.
- LayerFS Commit results: 8 UpToDate; the script removes every directory it creates, so nothing new is committed.
- Native macOS is the slowest machine: `stat 1000 files` took 4,445.8 ms against Docker's 530.9 ms on SQLite. The 1,000-step loops launch one macOS process per file on an NFS mount; the 64 MiB rows are close to Docker.
- The host baseline is the same frozen script on a plain APFS folder outside LayerFS, one sample per campaign and unrelated to the database, so both tables share it. It is host cost, not a LayerFS row; `native − host` is the LayerFS-attributable part and the `native / Docker` and `host / Docker` ratios stay the only cross-machine comparisons.
- Single unrepeated samples under shared host load: differences of a few tens of percent between rows are within what one sample can show and are not a ranking.

## Limits and cleanup

Each row is one unrepeated sample on a shared macOS host. Other owners' containers and VMs ran during the campaign and were left alone. No cache was cleared or proven cold. Execution PASS means the CLI lifecycle succeeded and the script reported one sample for each of the twelve scenarios; it is not independent content verification (every scenario deletes its own directory).

Final cleanup: **COMPLETE**. All eight rows released their Sandbox and Store through the CLI (every row cleanup COMPLETE, no retained custody); afterwards the six campaigns' shared infrastructure was released once, in dependency order: the Lima and Apple Container machines, the Docker machine's worker containers and data volumes, the dedicated PostgreSQL 17 server with its named data volume (the four row databases plus two probe databases), and Colima itself, with the leftover native probe Workspaces of the session unmounted and closed through the CLI. Verified afterwards: mount holds no 127.0.0.1 NFS Workspace, limactl lists no instance, container lists nothing, no campaign container or volume remains, the campaign home lists no Store and no Sandbox, no sandbox daemon runs, QUIET is gone, and the disk has 53 GiB free (57 GiB before). Kept for audit: the pinned release CLI and daemon, the sealed release Linux bundle (hash b330bd4a…) and suite image (sha256:0a098c7b…), the twelve row receipts with their harness snapshots, the six campaign caches, the host sample, and the pinned native tool folder. Attempts, stated plainly: the two native rows' `copy 64 MiB` and `pure copy 64 MiB` scenarios failed intermittently on this macOS host — plain `cp` exits 1 with `could not copy extended attributes ...: Operation not permitted` when the 64 MiB file it copies carries `com.apple.provenance` into the NFS-backed Workspace (a 1 MiB file passed 5 of 5 probes, a 64 MiB file failed between 0 of 5 and 5 of 5 depending on host load at that moment). Native SQLite therefore needed five attempts and native PostgreSQL two; every earlier attempt is listed above as superseded, no row was resampled inside a campaign, and each published row is one single sample rather than a best of several.

