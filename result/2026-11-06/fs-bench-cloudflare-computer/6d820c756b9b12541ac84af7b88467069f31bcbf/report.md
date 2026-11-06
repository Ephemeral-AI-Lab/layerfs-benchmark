# fs-bench-cloudflare-computer — Cloudflare's fs-bench.sh on LayerFS

> Status: Diagnostic observations; every timing and ratio is performance-ineligible.

**6 of 8 rows ran all twelve scenarios (2 NOT_RUN, 6 PASS); final cleanup COMPLETE.** One sample per row; every time and ratio is an INELIGIBLE diagnostic.

LayerFS `6d820c756b9b12541ac84af7b88467069f31bcbf` (remote `layerfs_v2_0_0`, resolved at campaign start). Harness `28cc23c220caac1bbb513c8a96b7eb81ff991c5a`. Each row runs Cloudflare Computer's byte-identical `script/fs-bench.sh` (Computer `de87919a4fd37242e960e13b7b3ba802d1eef0a0`, SHA-256 `0e2004339a9269b88c2de451d56575957477bde16b96a10cf1837519e37230ef`) once, with REPS=1, WARMUP=0, RANDOMIZE_TARGETS=0, no BASE, and the twelve offline scenarios. The script times each scenario itself with `date +%s%N`, inside the Workspace, in a fresh directory it removes afterwards. Computer itself is not measured.

All LayerFS work uses the public CLI: Sandbox create, Workspace mount, one Exec running the script on the Workspace root, LayerFS Commit, unmount, Sandbox close and Store remove/disconnect. SQLite Disposable/WAL/OFF; PostgreSQL synchronous commit off; one construction worker; kernel writeback off.

Ratios divide a machine's time by Docker's time for the same scenario and database; Docker = 1.00, below 1 means less time. `pure read`, `pure copy` and `overwrite` read or rewrite a file the script wrote just before its clock started, so they are own-write warm. The 64 MiB rows write zeros. The sum is a convenience total, not an agent turn.

Environment: Apple M3 Max (14 cores, 36 GiB), macOS 26.4.1; Docker Desktop 29.5.2 (linuxkit 6.12.76, 8 CPUs, 7.75 GiB); Lima 2.2.1 vz VM (2 CPUs, 2 GiB, Ubuntu kernel 6.8.0); Apple container 1.6.1 (2 CPUs, 2 GiB, kernel 6.18.35); dedicated PostgreSQL 17 container (1 CPU, 512 MiB) on the host at 127.0.0.1:59275. Sandbox image: LayerFS runtime image plus gawk and the frozen script.

| Build input | Identity |
| --- | --- |
| CLI (macOS, release, PostgreSQL) | `da25a81bdc692b9a2989650a35716648ab3a64f360281edaff51f870b322e57f` |
| Native daemon | `b0b961bf004bef7bb0e53724ad5a4a4155e731128093cddfb0a0d3bdd8ff803f` |
| Linux bundle seal | `05891b572d5bcad989f7f05821a856e2ea9cf540186fb18f813ccacbd4cbb0e3` |
| Sandbox tool image | `sha256:99c3223c2c8305fe80cf1fcb303588496bbb95c68c2cb0acab17d65966377cbb` |
| Namespace archive config | `sha256:7785fc0cff9d72bbf1e8c5e5f95aead60c9c1f9e311d4fdefb684f293a8e1770` |

## Rows

CLI call times in milliseconds, including launch and routing. Create is Sandbox creation; Exec is the whole script run; Commit is the LayerFS Commit; Cleanup is Sandbox close and Store remove/disconnect; End-to-end also includes mount and unmount and excludes preparation.

| Machine | Database | Execution | Cleanup | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Commit result |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Docker | SQLite | PASS | COMPLETE | 325.0 | 5,173.9 | 19.6 | 258.2 | 5,825.9 | UpToDate |
| Docker | PostgreSQL | PASS | COMPLETE | 575.2 | 5,193.8 | 43.8 | 251.7 | 6,218.0 | UpToDate |
| native | SQLite | NOT_RUN | COMPLETE | — | — | — | 0.0 | — | — |
| native | PostgreSQL | NOT_RUN | COMPLETE | — | — | — | 0.0 | — | — |
| Lima | SQLite | PASS | COMPLETE | 796.8 | 7,164.8 | 25.0 | 138.4 | 8,200.3 | UpToDate |
| Lima | PostgreSQL | PASS | COMPLETE | 944.0 | 4,735.7 | 42.5 | 154.0 | 6,032.0 | UpToDate |
| Apple Container | SQLite | PASS | COMPLETE | 92.0 | 6,015.2 | 16.7 | 57.6 | 6,250.3 | UpToDate |
| Apple Container | PostgreSQL | PASS | COMPLETE | 318.6 | 4,311.7 | 137.5 | 88.8 | 5,112.1 | UpToDate |

- native SQLite, native PostgreSQL: frozen fs-bench.sh needs bash 4 or newer (declare -A); native macOS has /bin/bash 3.2.57 and no pinned bash 4+ was supplied

## Scenario times, SQLite

| Scenario | Cache state | Docker ms | native ms | Lima ms | Apple Container ms | native / Docker | Lima / Docker | Apple Container / Docker |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| create 1000 files | self-contained | 281.5 | — | 199.9 | 260.2 | — | 0.71 | 0.92 |
| stat 1000 files | self-contained | 693.2 | — | 1,163.0 | 797.1 | — | 1.68 | 1.15 |
| rm 1000 files | self-contained | 337.4 | — | 478.5 | 461.2 | — | 1.42 | 1.37 |
| mkdir tree (10x10x10) | self-contained | 561.6 | — | 966.1 | 812.8 | — | 1.72 | 1.45 |
| find tree | self-contained | 718.7 | — | 1,050.8 | 708.2 | — | 1.46 | 0.99 |
| write 64 MiB | self-contained | 152.7 | — | 248.1 | 183.4 | — | 1.62 | 1.20 |
| copy 64 MiB | self-contained | 312.6 | — | 498.6 | 308.9 | — | 1.59 | 0.99 |
| read 64 MiB | self-contained | 139.9 | — | 167.4 | 174.5 | — | 1.20 | 1.25 |
| pure read 64 MiB | own-write warm | 11.6 | — | 7.1 | 6.5 | — | 0.61 | 0.56 |
| pure copy 64 MiB | own-write warm | 164.2 | — | 188.3 | 230.8 | — | 1.15 | 1.41 |
| overwrite 64 MiB | own-write warm | 82.0 | — | 72.5 | 69.8 | — | 0.88 | 0.85 |
| git init + commit 100 files | self-contained | 138.8 | — | 148.6 | 123.8 | — | 1.07 | 0.89 |
| Sum of scenarios | — | 3,594.3 | — | 5,189.0 | 4,137.3 | — | 1.44 | 1.15 |

## Scenario times, PostgreSQL

| Scenario | Cache state | Docker ms | native ms | Lima ms | Apple Container ms | native / Docker | Lima / Docker | Apple Container / Docker |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| create 1000 files | self-contained | 200.0 | — | 202.3 | 297.4 | — | 1.01 | 1.49 |
| stat 1000 files | self-contained | 712.5 | — | 679.0 | 662.4 | — | 0.95 | 0.93 |
| rm 1000 files | self-contained | 367.4 | — | 349.5 | 320.8 | — | 0.95 | 0.87 |
| mkdir tree (10x10x10) | self-contained | 600.6 | — | 545.1 | 426.5 | — | 0.91 | 0.71 |
| find tree | self-contained | 610.4 | — | 587.8 | 485.8 | — | 0.96 | 0.80 |
| write 64 MiB | self-contained | 125.0 | — | 121.6 | 111.3 | — | 0.97 | 0.89 |
| copy 64 MiB | self-contained | 279.8 | — | 286.4 | 238.1 | — | 1.02 | 0.85 |
| read 64 MiB | self-contained | 140.7 | — | 158.4 | 100.5 | — | 1.13 | 0.71 |
| pure read 64 MiB | own-write warm | 12.2 | — | 5.0 | 4.8 | — | 0.41 | 0.39 |
| pure copy 64 MiB | own-write warm | 193.0 | — | 154.9 | 119.6 | — | 0.80 | 0.62 |
| overwrite 64 MiB | own-write warm | 86.7 | — | 70.5 | 58.1 | — | 0.81 | 0.67 |
| git init + commit 100 files | self-contained | 147.9 | — | 141.2 | 112.8 | — | 0.95 | 0.76 |
| Sum of scenarios | — | 3,476.3 | — | 3,301.8 | 2,938.0 | — | 0.95 | 0.85 |

## Main observations

- Sum of scenario times ranged from 2,938.0 ms (Apple Container PostgreSQL) to 5,189.0 ms (Lima SQLite).
- Longest complete row: 8,200.3 ms against the declared 25,000 ms budget.
- LayerFS Commit results: 6 UpToDate; the script removes every directory it creates, so nothing new is committed.
- Single unrepeated samples under shared host load: differences of a few tens of percent between rows are within what one sample can show and are not a ranking.

## Limits and cleanup

Each row is one unrepeated sample on a shared macOS host. Other owners' containers and VMs ran during the campaign and were left alone. No cache was cleared or proven cold. Execution PASS means the CLI lifecycle succeeded and the script reported one sample for each of the twelve scenarios; it is not independent content verification (every scenario deletes its own directory).

Final cleanup: **COMPLETE**. All six executed rows released their Sandbox and Store through the CLI (case cleanup COMPLETE). Shared infrastructure was then released once in dependency order in 2.781 s: the Lima and Apple Container machines, the Docker machine worker, its container and data volume, the dedicated PostgreSQL server, container and data volume (all row databases), and the Apple container service the campaign started. Verified afterwards: no campaign containers, volumes or VMs, no Stores or Sandboxes. Kept: the pinned release binaries, sealed bundle and suite image, the build worktree's private caches, and local receipts. An earlier attempt in this session (campaign fbcc-1106a) ran no rows; its configuration let a NOT_RUN native prepare release all infrastructure, which completed cleanly and led to the shared-infrastructure rule in AGENTS.md.

