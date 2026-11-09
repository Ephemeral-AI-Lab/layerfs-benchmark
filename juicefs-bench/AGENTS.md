# JuiceFS bench agent instructions

Follow the root CLI, cache, report and resource custody rules. Use the shared
runner unchanged. This is an exploratory diagnostic family, not release evidence;
there is no committed product roadmap specification or tracking issue.

J01 runs unmodified JuiceFS Community Edition v1.4.2 `bench` once through public
`workspace exec`, with four workers, 1 MiB blocks, one 1 GiB file and 100 128 KiB
files per worker. The expected five rows are large write/read (MiB/s), small
write/read and stat (files/s). Tool setup and checksum validation are outside
the tool's internal phase timers. Lifecycle timings separately include launch,
routing, Sandbox create, mount, Exec, Commit, unmount and cleanup.

Use `SKIP_DROP_CACHES=true`; never purge this shared host or Docker VM. Every
phase is INELIGIBLE: kernel, daemon, overlay and Store caches are uncontrolled;
reads/stat follow the tool's own writes. A fresh mount does not establish coldness.
Run one sample per selected arm; preserve failures and never replay uncertainty.
The initial campaign selects Docker/SQLite only, no comparison servers. A 25 s
complete performance budget is declared before execution; setup gets 25 s and
cleanup 10 s. Do not enlarge these after a miss or reduce the workload.

Owner exception, 2026-11-09: after the first 25 s attempt timed out, the owner
explicitly authorized one new campaign with a 60 s complete lifecycle limit
("yes, give it more room to finish"). Retain the original failed attempt;
use fresh writable state, identical pinned binaries and workload, and declare
`budget_exceptions.docker` with `max_s: 60` before this new attempt. This does
not change the original result or authorize automatic replay/resampling.

Owner selection, 2026-11-09: run J01 on an actual JuiceFS filesystem with PG16
metadata, as a separate Docker arm (not a LayerFS PostgreSQL Store). Pin the
same JuiceFS image/binary. Own a dedicated PG16 server/database/data volume,
internal Docker network and local-file object/cache volume. Keep PG durability
defaults and record them; use compression none, writeback disabled, 300 MiB
buffer, 100 GiB cache limit and trash disabled. Format/mount/readiness are setup;
the single benchmark Exec has a 60 s budget. Compare internal tool throughput,
not its Exec wall with LayerFS's complete lifecycle. No warmup, cache purge,
automatic retry or rerun of LayerFS. Disclose topology/durability/cache differences.
`src/juicefs_pg.py` owns only this non-LayerFS lifecycle and exact-ID cleanup.

Require successful CLI and workload exits, exactly the five expected metric rows,
finite positive metrics, correct units, and the exact configuration header.
The tool does not independently verify file contents and deletes its files before
returning. Refuse `--verify`; report correctness UNVERIFIED. Commit after bench
does not capture the written dataset and is not a bulk Commit benchmark.
The upstream write loop reuses one random block per file and does not fsync;
neither throughput nor close acknowledges durable global history.

Keep downloads, source copies, manifests, environments, logs and receipts in
ignored `.cache/`. Pin the JuiceFS archive and binary hashes, release LayerFS
CLI/daemon/bundle identities, Sandbox image/config and full product source SHA.
Release exact owned runtime resources and export the private build-cache release
with `tools/worktree.py cleanup-scope` at handoff. Keep evidence protected.
