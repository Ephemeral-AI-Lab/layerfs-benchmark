**LayerFS/SQLite execution PASS; JuiceFS/PG16 execution PASS; timings INELIGIBLE diagnostics; final cleanup COMPLETE.**

# JuiceFS bench: LayerFS and JuiceFS/PG16

LayerFS `layerfs_v2_0_0` at `833d04cf44e8e747929d50ab1170a48260d9381c`. Campaign `jfs-20261109-60`. Harness base commit `653cb2798e8c8ec9e5c8b7860b648c63e9604abf` plus the suite source hashes retained with the receipts. This exploratory family has no committed product roadmap specification or tracking issue; admission_eligible=false.

## Configuration

One unrepeated Docker/SQLite sample on a shared macOS ARM64 host, Linux FUSE route. Four workers, each writing one 1 GiB file with 1 MiB blocks and 100 files of 128 KiB. Store profile: disposable. LAYERFS_CONSTRUCTION_WORKERS=1. SKIP_DROP_CACHES=true; no cache purge or pre-touch. Phase timers are upstream's Go monotonic elapsed wall times, converted by the tool to aggregate throughput. Launch, checksum validation and lifecycle control are outside these phase timers. Complete measured lifecycle budget: 60 s; preparation: 25 s; cleanup: 10 s.

| Artifact | Identity |
| --- | --- |
| cli_sha256 | `c1a3b99c046d1c0084e79bfdf8e4f7b79485bc6ad5fa1e9b80dde5cf770cc5c7` |
| daemon_sha256 | `c1dd0c2f747d67c78c21472cc8065df2bc2131175d262cf77603d6c868f503b0` |
| linux_worker_sha256 | `e4f7f6077ccda5ece2ed6adc26c2af0b2325aa1e013666b0bb5a60d322bbc9ac` |
| linux_bundle_sha256 | `a7edb147253b4aa4ee09d88aeb956558cc54f3181d488bfbe3617e86130734ce` |
| profile | `release` |
| sandbox_image | `sha256:33dd678ed762dc1ed94ba0a2f70b35aa803e8a5b634b696615c619734ccc28ae` |
| sandbox_archive_config | `sha256:2aa955855185ea3227ed638f47f5be31bed0d6bfac688df2245df2c446a97f7f` |
| juicefs_version | `1.4.2` |
| juicefs_source_commit | `46af7afa9f819b8c9ddafd475fb828d22fe9dd17` |
| juicefs_sha256 | `3c1d7c2d15b4d65949cc809552401e6a01ddb6f5ef313f9df96b8989435b2bd8` |
| juicefs_archive_sha256 | `19f72a30d3642a2f7971c8c4a31d2647de62f19520716e85c3a777de5f4c9036` |

Budget authorization: owner, 2026-11-09: yes, give it more room to finish. Explicitly authorized new campaign after retained 25 s timeout; unchanged workload and artifacts, fresh writable state.

Exact inner workload (the runner also checks the pinned tool binary hash):

```bash
SKIP_DROP_CACHES=true /usr/local/bin/juicefs bench . -p 4 --block-size 1 --big-file-size 1024 --small-file-size 128 --small-file-count 100
```

## J01 results

| Machine | Backend | Execution | Correctness | Performance | Cleanup |
| --- | --- | --- | --- | --- | --- |
| docker | sqlite | PASS | UNVERIFIED | INELIGIBLE | COMPLETE |

| Phase | Value | Unit | Reported cost | Cost unit |
| --- | ---: | --- | ---: | --- |
| Write big file | 350.77 | MiB/s | 11.68 | s/file |
| Read big file | 386.27 | MiB/s | 10.60 | s/file |
| Write small file | 2,137.30 | files/s | 1.87 | ms/file |
| Read small file | 15,089.50 | files/s | 0.27 | ms/file |
| Stat file | 44,630.80 | files/s | 0.09 | ms/file |

CLI lifecycle times include process launch and routing, separately from tool phase throughput.

| Machine | Backend | Create ms | Mount ms | Exec ms | Commit ms | Unmount ms | Cleanup ms | End-to-end ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | sqlite | 3,398.013 | 17.169 | 35,229.923 | 14.893 | 186.758 | 61.736 | 38,927.295 |

## JuiceFS PostgreSQL 16 comparison

This is an actual JuiceFS FUSE mount with PostgreSQL metadata, not a LayerFS PostgreSQL Store. It ran once later on the same shared Docker VM, using the identical JuiceFS binary, client image and inner workload. LayerFS was not rerun. The baseline uses a separate PG16 server over a private Docker bridge and local-file object storage on a dedicated Docker volume. No S3 server or network object store was used.

PostgreSQL image: `sha256:5264710be20f409750ac6dc4e5706dcef929c87e241605463f0f9aefa932a8d9`. JuiceFS client image: `sha256:33dd678ed762dc1ed94ba0a2f70b35aa803e8a5b634b696615c619734ccc28ae`.

Observed PostgreSQL version, fsync, synchronous_commit, full_page_writes and shared_buffers, in order:

```text
PostgreSQL 16.15 (Debian 16.15-1.pgdg12+2) on aarch64-unknown-linux-gnu, compiled by gcc (Debian 12.2.0-14+deb12u1) 12.2.0, 64-bit
on
on
on
128MB
```

JuiceFS: compression none; trash 0 days; writeback disabled; 300 MiB buffer; 100 GiB disk cache limit with a fresh cache directory; all other mount settings at v1.4.2 defaults. LayerFS used its disposable SQLite profile. These durability and storage architectures differ; this is not a matched persistence comparison.

Baseline first. Ratios are LayerFS throughput divided by JuiceFS throughput, provided only as INELIGIBLE diagnostic arithmetic; above 1 means higher observed throughput.

| Phase | Unit | JuiceFS PG16 | LayerFS SQLite | LayerFS / JuiceFS |
| --- | --- | ---: | ---: | ---: |
| Write big file | MiB/s | 1,155.51 | 350.77 | 0.30× |
| Read big file | MiB/s | 1,486.61 | 386.27 | 0.26× |
| Write small file | files/s | 242.90 | 2,137.30 | 8.80× |
| Read small file | files/s | 4,182.10 | 15,089.50 | 3.61× |
| Stat file | files/s | 17,141.60 | 44,630.80 | 2.60× |

JuiceFS execution: **PASS**; content correctness: **UNVERIFIED**; cache eligibility: **INELIGIBLE**; cleanup: **COMPLETE**.

JuiceFS benchmark Exec wall: 9,121.831 ms, under a 60 s limit. Format, mount and readiness were untimed setup. This wall includes Docker Exec launch, checksum validation, bench and its file deletion; it has a different boundary from LayerFS's full lifecycle and must not be used for a lifecycle speedup ratio. The phase throughput columns use the same upstream internal timers on both filesystems.

The baseline's two containers, PG data volume, object/cache volume and private network are tracked by exact IDs and owner labels. Its receipts and source snapshot remain local under `.cache/juicefs-pg16/`.


## Observations and limits

The tool reads and stats its own recent writes. Kernel pages, FUSE metadata, daemon/overlay SQLite caches, VM backing and Store caches are uncontrolled. Every metric remains INELIGIBLE; none establishes cold-storage throughput or a performance advantage over another filesystem. JuiceFS client, PostgreSQL and OS caches were also uncontrolled; settings and topology differ, and the samples were taken at different times on shared hardware.

The write loop reuses one random block per file and does not fsync. These are buffered filesystem API measurements, not durable writes or global-history publication. The tool removes its test directory before returning; a subsequent LayerFS Commit in a successful lifecycle would not save the measured dataset. Observed Commit result: UpToDate. Independent content correctness is UNVERIFIED; successful reads only check that the requested byte counts were returned. Tool COST is upstream's wall-time-derived statistic, not independently observed per-operation latency. Phase-local CPU, memory, peak backing bytes and stored dataset bytes are UNAVAILABLE; the dataset is deleted before the Commit.

Setup reused the earlier sealed release artifacts and tool image, with fresh writable state for this separately authorized campaign. No setup input was pre-touched for measured reads. Concurrent shared-host activity was not interrupted. No automatic retry or uncertain-operation replay was performed.

## Cleanup

Final runtime cleanup: **COMPLETE**. Case cleanup uses public Workspace unmount, Sandbox close and SQLite Store remove; infrastructure releases use exact owned IDs. Raw receipts, ownership ledger, source snapshots, configuration and artifact manifests stay local under ignored `juicefs-bench/.cache/`.

At completion of the earlier LayerFS campaign, machine configuration: macOS 26.4.1 ARM64 host; Docker Linux kernel `6.12.76-linuxkit`, 8 virtual CPUs and 8,321,994,752 B RAM (shared VM, no dedicated CPU allocation). Host free space at LayerFS completion: 326,583,021,568 B (326.583 GB); Docker guest available space at LayerFS completion: 190,041,026,560 B (176.989 GiB). Both satisfy the machine headroom thresholds.

The new campaign's worker container `fc34b09252d8a49c40e68e05ec7b8edfe106d4671b45bd687e77c9b2df47f494` and volume `lfs-b0041c98-docker-data` were independently confirmed absent after registered cleanup. Builds were not repeated: all CLI, daemon, bundle, image and tool identities match the earlier attempt, and only writable home/Store/Workspace state was new. Both earlier private Linux build-cache volumes remain released. The earlier 186 MiB host release-target cache stays protected by an open Virtualization framework file handle; no shared VM was stopped. The prior exact cache-release scope and blocker receipts remain available. Pinned artifacts and all receipts stay local; unrelated resources were preserved.

After the later JuiceFS/PG16 baseline, both of its containers, both data volumes and its private network were independently confirmed absent. Final host free space: 325,975,519,232 B (325.976 GB); final Docker guest available space: 189,399,621,632 B (176.392 GiB). Both satisfy the machine headroom thresholds. The pinned PG16 image is retained for reproducibility; no other owners' resources were selected.

## Retained earlier attempt

Campaign `jfs-20261109` used the same product, tool and workload with a 25 s lifecycle budget. Its failure is preserved; the owner subsequently authorized the separate 60 s campaign above. Each campaign used independent writable state. No throughput is inferred from the timed-out attempt.

| Campaign | Budget s | Execution | Lifecycle ms | Metric table | Runtime cleanup |
| --- | ---: | --- | ---: | --- | --- |
| jfs-20261109 | 25 | FAIL | 25,007.966 | UNAVAILABLE — exec: CLI/process exit -9 | COMPLETE after inspection |

The original failed receipt, original INCOMPLETE cleanup receipt, custody inspection and later successful resource-release receipts remain local and unchanged. The prior report text is retained locally; this is the single published report for both campaigns.
