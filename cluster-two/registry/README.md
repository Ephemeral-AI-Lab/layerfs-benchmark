# Cluster-two historical registrations

> **Status:** Archived; retained for historical evidence only.

The R8 v1–v4 JSON files are closed registrations. Their source paths, executable
paths, source identities, receipts and verdicts describe their original trees;
they are not runnable target discovery for current source. Preserve their bytes.

Issue #327 removed `layerfs-daemon/tests/shared_processes.rs` and its support
files because they tested overwrite-on-stale behavior, replaced by merge and
single-attempt HeadMoved refusal. Consequently `host:shared_processes`,
`linux:shared_processes`, `PREREQ-SHARED-PROCESSES-LINUX` and
`Q1-shared-processes-linux` in those registries are **historical only — target
removed** at current source. Do not resolve their pinned binaries as current
products, schedule them, or reinterpret their historical results as new PASS.

The kept publish-race behavior is exercised by the current daemon target
`mounted_parallel_commits`; that test is not a replacement for the historical
shared-process campaign or the JS SDK's still-open cross-process A9 proof.
Current #327 cleanup and acceptance are tracked in
[the implementation plan](../../../core/docs/issues/327/IMPLEMENTATION-PLAN.md) and
[Phase 2](../../../core/docs/issues/327/PHASE2.md).
