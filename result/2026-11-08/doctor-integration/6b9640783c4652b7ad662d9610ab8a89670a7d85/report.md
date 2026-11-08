# Doctor backend completion — LayerFS 2.0.0

**Outcome: PASS for the specified Doctor backend contract.** Independent native NFS fixture teardown remains incomplete, with custody preserved; it is not included in this Doctor pass.

This is correctness qualification for [layerfs-project#116](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/116), against the remaining backend specification B1–B6. Frontend additions, package publishing, GC and Durable execution are excluded. Existing frontend evidence is retained at its original source pins.

## Source and reproducibility

Final integrated backend source: `6b9640783c4652b7ad662d9610ab8a89670a7d85`, based on target `716197c4999fb087aa0fb17bac5ceb48b0b556ae`. Features: `layerfs-control/machine,layerfs-control/postgresql,layerfs-control/tls`. macOS arm64, Rust1.85.1, registered private Cargo home/target. SQLite fixtures explicitly Disposable/WAL/synchronous=OFF; no Durable execution. Actual PostgreSQL17.11 primary and streaming standby, SCRAM and configured TLS use isolated owned infrastructure.

Build first with the registered `tools/worktree.py cargo` launcher. The private PostgreSQL harness loads connection variables without printing secrets. Final test invocation used inner90/outer100-second ceilings. Raw credentials, logs and fixture resources stay private; reusable public harnesses and source tests are linked below. Timings describe correctness deadlines, not performance or cold caches.

## B1–B6 checklist

| Package | Qualification | Result |
| --- | --- | --- |
| B1 exhaustive inventory/acquisition | Every applicable schema category mapped to keys, authority/advisory role, validator and quick/full policy; valid active/interrupted acquisition, bounded BLOB/TEXT extraction and progress windows | PASS |
| B2 content/dependency/namespace | C01–C09 persisted mutations, resealed identity/semantics, missing/cyclic/over-depth dependencies, required replaced base, locator/block damage, mappings/summaries, attributes/symlinks, aliases/islands/contexts and historical/unreachable winning objects; valid controls retained | PASS |
| B3 history | Authoritative identity/provenance/references/cycles; independent derived height/depth/newest/run/absorption/reach and exact overwrite checks; valid forks/merges/forced/removed history | PASS |
| B4 coherence/cancellation/no mutation | SQLite committed WAL, concurrent pack insertion/publication/removal, coherent paging, independent checkpoint release after cancellation, schema authority/type guards; PostgreSQL snapshot/removal/transport/query/schema-admission release | PASS |
| B5 PostgreSQL | Actual primary/standby/TLS, access/auth/binding/schema distinctions, missing/denied amcheck, supported heap/TOAST/B-tree/sequence, unsupported relation, oversized extraction, namespace transport loss and cancellation | PASS:31 actual tests |
| B6 runtime/providers | Real native/Docker/Lima, local/worker/forwarded daemon, Linux getent release, versioned MinIO and configured R2; same-pin remote SQLite full+quick on Docker/Lima | PASS; explicit serving/overlay boundaries retained |

The [Store coverage map](https://github.com/Ephemeral-AI-Lab/layerfs/blob/6b9640783c4652b7ad662d9610ab8a89670a7d85/docs/architecture/engine/store/diagnostic-coverage.md) identifies all applicable tables and C01–C09 reachability. Full audits inspect all winning rows and physical records; surviving historical contexts supply namespace qualification. This does not compute per-object live reachability counts or perform GC. Losing physical representations receive applicable framing/payload checks without inventing a mixed winner/loser dependency graph.

## Integrated terminal evidence

| Check | Observed result | Receipt |
| --- | --- | --- |
| Final affected backend build | PASS;8 packages,31 selected test targets built before execution | `cargo-macos-dce3e7bb0c60452d9eea157302895bbe` |
| Combined backend execution | 150 passed,0 failed;31 actual PostgreSQL cases included | `cargo-macos-c4e6677a7eea4480bce1fcc6ac253f28` |
| All-target warning-denying Clippy | PASS;8 affected backend packages with machine/PostgreSQL/TLS | `cargo-macos-7e2bd886986b4c768dab46b6c7f7b13f` |
| No-default-feature build | PASS;Control/Store/Persistence | `cargo-macos-32799ec7c1f5425da51a9137ba3d5a4f` |
| Dependency/source guard | PASS;1311 production Rust/SQL/JavaScript files | `tools/check_product_boundary.py` |
| Tooling regressions | PASS;173 tests | `python3 -m unittest discover -s tools -p 'test_*.py'` |
| Changed-file formatting/whitespace | PASS;Rust1.85.1 with skip_children=true, avoiding unrelated baseline child formatting | scoped rustfmt and `git diff --check` |

Two ignored entries in the combined run are helper subprocess entry points executed by their passing parent tests. They are not two missing qualification cases. Tests with deliberately caught observer panics retain their panic output and independently assert watcher cleanup.

A final test-only follow-up explicitly requires `store.database.foreign_keys` failure for the existing missing-parent fixture. All4 affected history tests pass after build-first: `cargo-macos-ad0ae2360b0d4575867a1991ae11cdf0`. Product source is unchanged from the qualified6b revision.

The35 new persisted Store cases overlap the150 combined tests. Likewise PostgreSQL31 is included in150, not additive. Existing unaffected Storage/overwrite/S3/frontend tests retain their earlier receipts; no inflated aggregate is claimed. The final independent review found no remaining concrete Doctor false-health, unsafe mutation, unbounded extraction or cancellation-release defect.

## Limits and prior failures

Quick completes its reduced scope with explicit full-only skips. Full integrity has bounded admission and no invented total Store-size or audit-duration cap; long snapshots retain WAL/MVCC versions. Retained check/evidence entries are capped at1024 while exact totals survive truncation. Local synchronous filesystem/CPU observations check budgets at their documented boundaries. PostgreSQL cancellation may use up to one additional second for cleanup; physical online checks have a separately named observation interval.

Absent/denied amcheck and unsupported relation/version formatting remain explicit incomplete physical coverage, never healthy corruption checks. Doctor does not install extensions or claim offline checksum verification. Registry readiness does not qualify FUSE/NFS serving, mutable overlays or Store integrity. R2 TLS/listing is qualified; unsafe temporary writes are blocked before PUT because immutable-version ownership is unavailable. Version-owned MinIO PUT/GET/DELETE is qualified. Neither proves multipart/restore correctness.

Retained failing regressions exposed SQLite saved-DDL authority spoofing, authority replacement, oversized scalar extraction and malformed-incarnation classification; all were fixed and their affected cases pass. Runtime R2 first-address selection, unclean owned session closure and Host runtime-tree traversal were diagnosed and fixed. Harness expectation/setup failures remain documented separately from product results. Known independent issue#115 is not a Doctor dependency; no unrelated filesystem/concurrent-publication pass is invented.

Production LOC:143682 ->151919 (delta+8237), API4278/Control37853/Core39671/Engine70117. Same baseline-pinned production counter over exact source trees; tests/docs/tooling excluded. Reference absent (retired R9c; last counted65,417 at498dd1917812). This is source-size accounting, not a performance claim.

## Final runtime source pin and cleanup boundary

The final public-CLI runtime smoke uses source6b9640783c with matching macOS CLI SHA256 `be033e74312b8b22a27869daf2e2450c5553c8c2034d7baa9d9f9f5af60a2858`, daemon `994b5091dfd145edab97458a3b22c7495a8a2d6125247b78bb29d855772d78b5`, and Linux bundle `a072d9e97f5d216516d487a832ec925967c91303491f327da0d4720272d06129`. Real Docker and Lima worker/forwarded daemon checks and both remote SQLite full/quick audits completed with no unexpected failures, logical records/leases unchanged and daemon-log hashes unchanged. A fresh native fixture separately passed Host/Machine/Sandbox control checks. Prior mounted native session proof retains its original pin and unchanged-log evidence; no fresh NFS serving claim is made.

The old native fixture's one public unmount attempt failed after about66 seconds when its helper did not complete. Exit125 retained Detach custody. It was not retried, forced away or deleted. A fresh independent home supplied Doctor qualification while that old lifecycle state remained protected. This is a distinct fixture-lifecycle failure, not a passing cleanup result. [Lifecycle follow-up#136](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/136) records the retained custody; the runtime report records exact resources and release scope.

The owned PostgreSQL primary/standby containers, volumes and network were removed through their exact-label harness and independently verified absent. Credentials and certificate keys were removed; secrets-free receipts remain. Cache releases identify exact completed targets and protect source/evidence/pinned binaries. No cache deletion or recovered-space claim is made.

Detailed environment ledgers: [PostgreSQL31 and owned teardown](../../doctor-postgresql/eca5ca749608b1b9f8e63a9ac8b41dd309772727/report.md), [same-pin real runtime/S3 qualification and retained custody](../../doctor-runtime/6b9640783c4652b7ad662d9610ab8a89670a7d85/report.md).

Subsequent target advancement is qualified in the [final89c4e528 integration report](../89c4e5282883af343116cd7a362902f369f8c5a1/report.md); original run source pins above remain unchanged.
