**PASS: 27 PostgreSQL Doctor backend tests passed against actual owned PostgreSQL 17.11 primary/physical-standby fixtures, including TLS, corruption, privileges and cancellation.**

This is backend correctness qualification for remaining-spec B5 and PostgreSQL
B4, not whole-Doctor qualification or a throughput/latency benchmark. Internal
crate tests and fixture-only database administration were explicitly authorized
for this campaign. Ordinary LayerFS operations in other benchmarks remain CLI
only. No CLI/SDK parity, daemon/bundle, UI or GC claim is made here.

## Pinned configuration

| Item | Identity |
| --- | --- |
| LayerFS source | `c011512bc129803215e33d0b7f93ac1becccc68a` |
| Source tree | `af3cd780e05b4b39ab859cee88ab0a79bd49725f` |
| Prior PG implementation | `7213563f5135a7015212f70a84504c3fef490bc9` |
| Platform / Rust | macOS ARM64 / Rust 1.85.1, locked/offline private Cargo target, jobs 2 |
| Flags | shipped aarch64 cfgs aes_armv8/polyval_armv8/chacha20_force_neon; target-feature +aes,+sha2; repository LIBSQLITE3_FLAGS unchanged |
| PostgreSQL image | `postgres@sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652` |
| Server | PostgreSQL 17.11 (Debian 17.11-1.pgdg12+2), aarch64-unknown-linux-gnu |
| Fixture | Disposable; SCRAM primary with fixture self-signed TLS, streaming physical standby, separate database without amcheck |
| Setup reuse | Warm compiled binaries/dependencies; independent freshly initialized primary/standby for final harness proof |
| Invocation ceilings | inner launcher 90 seconds, outer loader 100 seconds; build-first no-run completed |

The final run used the README command with its five named targets. All fixture
variables were present, including the explicitly disposable container flag;
none of these passes are environment-missing early returns. The test inputs
match the committed source tree. Neither a LayerFS daemon nor a Linux bundle
participates in this internal lane.

## Results and expected observations

| Target | Tests passed | Scope |
| --- | ---: | --- |
| postgresql_diagnostic (existing baseline first) | 5 | coherent publication snapshot, ordinary synchronous writer regression, actual SQL lock deadline and no-deadline cancellation/release, denied signature classification, stalled authentication EOF |
| doctor_store_postgresql | 1 | actual saved alias and password-reference path; correct/wrong binding, wrong password, absent schema; failed admission blocks audit; no home/database data mutation |
| postgresql_doctor_access | 6 | schema USAGE/table privilege, wrong credentials, unreachable transport, self-signed TLS rejection, distinct Unix/TCP fallback, live constraints/indexes/triggers, namespace disconnect and permission timing |
| postgresql_doctor_cancellation | 5 | pre-cancel avoids resolution/socket, cancellation after actual auth startup and TLS ClientHello, independent blocked-query release, watcher joins during observer unwind |
| postgresql_doctor_physical | 10 | online amcheck capability/coverage, missing/denied extension, unsupported hash index, real standby, oversized bodies/digests/authority, resealed retained object, removal snapshot, authority replacement, admission vs audit budget |
| Total | 27 | no failed, ignored or filtered test entries |

| Mutation/fault | Expected and observed diagnostic result | Verdict |
| --- | --- | --- |
| Wrong saved binding; wrong password; absent/denied schema/table | `store.connection.identity`, `.authentication`, `.schema` or `.read` Fail respectively; no logical snapshot after failed authority admission; credentials absent from output | PASS |
| Unreachable endpoint or stalled/untrusted TLS | `.transport` Unknown, bounded operation and actual peer socket EOF; no corruption inference | PASS |
| Valid schema with extra benign objects vs damaged required constraint/index/trigger | `store.schema.objects.summary` Pass for valid required subset; `store.schema.objects` Fail for damaged required authority | PASS |
| Backend killed at history-to-namespace phase | `store.namespace` Unknown and session disappears independently; no fabricated corruption finding | PASS |
| Privilege revoked after transaction has admitted reads | Already admitted snapshot may continue successfully; new denied session fails/incomplete. No forced cache clear or false permission promise | PASS |
| amcheck installed, missing, EXECUTE denied, hash index | Per-relation OID/function/duration Pass where supported; `.relations.summary` Unknown for missing/denied/unsupported coverage; no doctor extension creation or strong parent-check invocation | PASS |
| Physical streaming standby | `store.snapshot` and applicable online relation checks Pass; no primary data writes by doctor | PASS |
| One MiB wrong pack body; 5000-byte invalid inode; one MiB descriptor digest | `store.packs`, `store.ordinal_blocks` and locator-driven `store.objects` Fail as applicable; independent TCP proxy confirms corrupt large values do not cross the wire before rejection | PASS |
| Resealed retained object (outer pack digest recomputed) | `store.packs.summary` Pass plus canonical `store.objects` Fail | PASS |
| Two valid projects removed concurrently after snapshot pin | Current scan reports both historical contexts; next scan one; retained objects remain valid | PASS |
| Catalog/incarnation replacement between admitted open and pinned audit | `store.identity` Fail and inventory does not proceed | PASS |
| One MiB authority/saved-DDL values | Server-side trusted comparison or bounded identity projection refuses malformed authority; proxy confirms no large raw extraction | PASS |
| Borrowed cancellation during authentication/TLS or locked metadata query | Unknown/incomplete cancellation, actual EOF or independent backend release; `store.connection.cancellation.release` Pass only after cancellation/ROLLBACK acknowledgment | PASS |
| Observer panics while watcher exists | Expected panic caught by fixture; scoped watcher joins without hanging | PASS |

Source nonmutation is checked with owned-schema row fingerprints and server
write counters at stable fixture boundaries; saved home/password-reference
files remain unchanged. Fixture administration intentionally creates roles,
extensions, constraints and faults only in owned disposable databases. Doctor
itself creates no helper/temporary schema, migration, repair or extension.
Physical checks are live interval observations separate from the coherent
logical repeatable-read read-only snapshot. Physical bytes/TOAST layout are
server-managed; logical limits use actual payload lengths, not allocated size.

## Executable identities

SHA-256 of final native test executables (the path stem is the Cargo test target):

| Executable stem | SHA-256 |
| --- | --- |
| doctor_store_postgresql-ab6a2f69f34c4da0 | `4c1344122fb2576c4a06f6ce14b09a7911edfdcb466bf0a7d346ff53ac064604` |
| postgresql_diagnostic-31ddd1734e1cff93 | `4ec3927c3fc8414bc64b1d360b50e3141b98919948ba6e3952efaea9aeffa6d0` |
| postgresql_doctor_access-aeb20c01e44176fd | `c685ea68b95c040dcd5d2f07dacf364149ae8ff4e1088adccce5bbe8d0eca6f5` |
| postgresql_doctor_cancellation-e40df0e1f402e0cc | `554c3ada7294ae9be3e8fd3c158985dcf8e0375c0f5f514cb3dcbed2c853e347` |
| postgresql_doctor_physical-979e857ffedda515 | `407a7bbab54aa96f4d80e7d04273fb73cb4632253b40aa391df622eebc7f6ee7` |

Local final launcher receipt: `cargo-macos-ef635dc32cb54c47b04c887300ae684f`.
Earlier full acceptance receipt: `cargo-macos-141e4627b0d14dbab52e66ebec3b2f6b`.
PostgreSQL all-target warning-denying Clippy, boundary guard and changed Rust
formatting passed. Fixture harness actual up/run/down and Python compilation
passed. Receipts and credentials stay private; this report is the published
ledger, not an evidence bundle.

## Failures retained and limits

Development failed runs were retained privately and corrected before this pin:
leading-whitespace live-DDL normalization; information_schema falsely hiding a
denied table (replaced by pg_catalog); invalid fixture regclass typing and
oversized inline-row setup. The expectation that mid-transaction privilege
revocation must fail the already admitted namespace read was invalid; it became
a negative control plus separate real backend-termination test. An old fixture
URL pointing at a removed container was NOT_RUN infrastructure, not corruption.
No waived failures or silent reruns are counted as final passes.

Server 17 is the qualified live-DDL formatting contract; other supported server
versions with unrecognized formatting report explicit compatibility Unknown.
Randomized multi-host diagnostic admission is explicitly unsupported. DNS
cancellation is checked at bounded resolver boundaries; Linux getent lifecycle
qualification belongs to the separate runtime lane. No offline checksums,
strong-lock bt_index_parent_check, arbitrary index-method coverage, extension
installation, instant DNS preemption, repair or production write-permission
claim is made. Shared engine adversarial history/acquisition completion and
combined integration use their own root receipts.

This is a warm correctness lane: no controlled cold cache, throughput, latency
or peak-RSS claim. Corrupt-value extraction is bounded by actual format lengths
and independently observed wire bytes, not a claim that whole server storage is
small. Long logical snapshots may retain obsolete server versions while open;
actual cancellation/termination tests verify their release.

## Cleanup

The fresh harness-validation primary/standby, exact labelled volumes and network
were removed successfully using `fixtures.py down`; a second cleanup was not
replayed. The original acceptance primary/standby stay explicitly protected for
parent integrated-candidate reruns, with private mode-0600 credential files.
No unrelated service, host trust, cache or runtime state was modified or removed.
Product private build cache and source remain warm until integration handoff.
