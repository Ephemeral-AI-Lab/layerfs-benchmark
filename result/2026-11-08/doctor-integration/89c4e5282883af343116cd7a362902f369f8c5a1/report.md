# Doctor final integration on the current v2 target

**Outcome: PASS for Doctor integration on the current v2 target.**

The final candidate `89c4e5282883af343116cd7a362902f369f8c5a1` integrates the advanced `layerfs_v2_0_0` target `d1be0714b48d01b9e7836b1566538f42b6d254f5` into the completed Doctor work. The target advanced just before merge with saved branch/file query changes. It was integrated without text conflicts; shared API/module/call-table/worker/test-schedule merges were reviewed independently.

The [B1–B6 full backend report](../6b9640783c4652b7ad662d9610ab8a89670a7d85/report.md) remains the150-test/actual-PG31 evidence at its original source pin6b9640783c. It is not relabeled as a new run. Exact Git object comparisons establish unchanged Core, Persistence production/SQL, Doctor orchestration, Store diagnostic adapter, worker diagnostic handler, daemon/registry, StoreService kernel_guard and Cargo dependency/lock inputs. The entire Persistence tree differs only by the additional explicit FK test assertion. Saved-query readers/dispatch are a separate path; they change no Store format or writes.

## Final-source checks

| Scope | Result | Receipt |
| --- | --- | --- |
| Affected package build | PASS; API/CLI/Control/Store/Machine/Daemon/StoreService, machine/PostgreSQL/TLS enabled | `cargo-macos-4c345fc597914edba0e2a036f9a065d6` |
| Routing/call-table/Doctor tests |60 passed,0 failed;2 ignored helper entry points exercised by passing parents | `cargo-macos-ba7b32f32fce467f9c2ac308f6ff9ef0` |
| Selected saved-query/scanner build | PASS; saved_branch_queries, sdk_file_history, saved_namespace_pages, sdk_text_scan | `cargo-macos-44fda92632fe495c8081679bd62cc054` |
| Selected saved-query/scanner tests |25 passed,0 failed,0 ignored;90-second invocation after build-first | `cargo-macos-b7121bf4824645a6b07aa44bdf760af3` |
| All-target Clippy | PASS;7 affected packages, warnings denied | `cargo-macos-1148d6d97eac47208ec38aa5de18fdc4` |
| No-default-feature build | PASS;Control/Store/Persistence | `cargo-macos-d51590705ce146ec9e4d692594fbc521` |
| Source boundary guard | PASS;1331 production files | `tools/check_product_boundary.py` |
| Tooling | PASS;173 tests, explicit90-second bound | private `advanced-tooling-tests.json` |
| Formatting/whitespace | PASS; scoped changed Rust files with skip_children=true, target inherited formatting preserved | rustfmt1.85.1; `git diff --check` |
| Matching worker/daemon/bundle and full+quick remote SQLite | PASS; full58 checks, quick55 checks/3 explicit skips, both complete; records/leases unchanged | actual owned Docker `target-update-receipts` |

Counts above and the prior150/PG31 overlap and are not additive. No frontend feature implementation, Node/Python rebuild campaign, GC, Durable execution or performance/cold-cache claim was added. The ordinary API now has64 calls; Doctor remains outside that dispatcher. Both the saved-query scanner and diagnostic-overwrite timing entries survive integration. The Doctor worker refusal decoder visibility remains preserved.

One attempted saved-query test build selected a nonexistent StoreService `tls` feature and failed at Cargo feature admission before compilation/execution (`cargo-macos-98de3485881449e8822acbdcd67de8ff`). Manifest inspection corrected the harness selection to its supported PostgreSQL feature; the following build and25 tests passed. The failed receipt is retained as a harness invocation error.

## Scope and resource boundaries

The full B1–B6 report and [runtime ledger](../../doctor-runtime/6b9640783c4652b7ad662d9610ab8a89670a7d85/report.md) retain native/Docker/Lima, versioned MinIO, R2, Linux resolver and adversarial source evidence at original pins. The advanced target does not touch those diagnostic code paths. The final matching-bundle Docker run rechecks the source identity boundary; it does not substitute for or relabel the earlier matrices.

Existing quick/full, unsupported amcheck/R2 write, physical-observation interval, cancellation boundary and long-read effects remain explicit. Prior database fixtures were removed through exact-owned teardown. Runtime resources were normally unmounted/closed/stopped and MinIO removed; the one old native NFS retained-custody failure remains separately protected in [layerfs-project#136](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/136), with no replay, forced deletion or successful-cleanup claim. Any temporary Docker requalification lifecycle is recorded separately.

Production LOC against the current targetd1be0714:146640→154882 (+8242), scopes API4448/Control37983/Core39671/Engine72780. Baseline-pinned production_loc.py over exact target/candidate source snapshots; tests/docs/tooling excluded. Original target716197c4 comparison143682→151919 (+8237) remains in the prior report. The candidate merge's first-parent comparison151919→154882 (+2963) imports the independent saved-query target changes. Reference absent (retired R9c; last counted65,417 at498dd1917812).

## Final89c runtime identity

Matching macOS CLI SHA256 `2c86f455f8e679a3a5856063e643a86679214ded21ab4bc1327a709c697d3985`, daemon `a894ecb594779492b2a2d2ca74e5f7869b3d5c391d25e336cd884eabbfa4355d`, Linux bundle `aacc5f3242c1a164bcca3aead6f5d5ba7eae21380ab47ce5740ec5f0729487b7`.

Actual owned Docker machine compatibility/ping, new-daemon registry/session and full/quick same-kernel SQLite passed. The requalification created no credential copies. The workspace was publicly unmounted, Sandbox closed and provider stopped afterward. No operation was replayed; old native#136 custody remained untouched. Detailed target-update receipts and final cache releases are recorded in the runtime ledger.

## Final concurrent CLI integration supplement

After the backend proof, targetdbd12393 imported migration/npm metadata without backend changes, then target `52ec0b5dbb62406f166f248d135def8e8d669501` added a CLI library entry and terminal rendering. Final candidate `c4fbf039fab5308b64c1dcd2346fbf7833e77328` integrates both. Shared `main.rs`/`run.rs` conflicts were resolved by using the target library entry, declaring the existing private Doctor module there and retaining the targeted Doctor dispatcher. The obsolete legacy dispatcher copy was removed. No Doctor family/selector/default or backend algorithm changed.

| Final CLI check | Result | Exact proof |
| --- | --- | --- |
| Doctor/legacy/rendering build | PASS; machine/PostgreSQL/TLS | `cargo-macos-17114c2dbbed49dfb0ba722f80e417dd` |
| Existing doctor,doctor_targets,rendering tests |8 passed,0 failed; built first,90-second bound | `cargo-macos-0a3c8a6135ca4ae396a50b6a43f1608f` |
| CLI all-target Clippy | PASS; warnings denied | `cargo-macos-e916f357311e4ce5a31c969db877ed18` |
| Final CLI no-default-features check | PASS; PostgreSQL/TLS without host machine adapters, sourcec4fbf039 | `cargo-macos-adedaa44e10843ac8ada7dcfb9e441a8` |
| Final scoped formatting/whitespace | PASS; final change formats one help tuple only, preserving Rust tokens | rustfmt1.85.1 skip_children=true |
| Final source boundary guard | PASS;1332 production files | `tools/check_product_boundary.py` |

CLI execution proof source is `7656db1c172aaa6c7fa9c229778fca89b7406b25`; compiled CLI SHA256 `c90f491ae8b1e4d526e7853a00c37e0c525c1b45da86b70b6fcce6b453d010a2`. Final c4fbf039 changes only that tuple's formatting. JSON remains default in this exact source; `--text` is explicit, no `--json` flag was introduced. Legacy Doctor exit0 despite findings, bad-usage2 and targeted refusal125 stay covered.

Exact comparison confirms Core, Engine, Control, API Rust library/bindings, dependency lock and `worker.rs` unchanged from qualified89c. The worker guard and UTF-8 argument loop retain their behavior across the module move. No new PostgreSQL/runtime matrix was required for this frontend-entry integration; original150/PG31 and final89c live-worker proof retain their original source pins. New frontend features, npm package publication and rebuilding the imported prebuilt CLI artifact remain outside the accepted Doctor completion scope. The existing8 tests verify compatibility of the already-delivered Doctor wiring.

Final source count against target52ec0b5d:146867→155114 (+8247), API4680/Control37983/Core39671/Engine72780. CLI target import first-parent154882→155109 (+227); final formatting155109→155114 (+5 line layout only). Same pinned exact-tree counter and exclusions. No new performance/cold-cache claim. Implementation merge and issue-closure receipts are recorded in [layerfs#623](https://github.com/Ephemeral-AI-Lab/layerfs/pull/623) and [layerfs-project#116](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/116).
