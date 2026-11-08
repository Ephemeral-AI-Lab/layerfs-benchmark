**PASS: all 31 actual PostgreSQL Doctor backend tests passed, including cancellation across both full-integrity admissions and bounded extraction after scalar-column type corruption.**

This completes the PostgreSQL B5/B4 backend lane at source
`eca5ca749608b1b9f8e63a9ac8b41dd309772727`, tree
`17fe88f9aa2893095aa4799d2e7384c08c5211bd`. It is ready for parent
combined qualification; this is not a whole-Doctor/CLI/SDK/UI/GC verdict.

The [27-test baseline report](../c011512bc129803215e33d0b7f93ac1becccc68a/report.md)
records the same PostgreSQL17 authority, live-schema, physical checks, actual
standby, TLS, corruption, retained-data/concurrency and cancellation matrix.
This final pin adds the two actual Control full-integrity cancellation cases,
two additional physical/extraction tests, and corresponding production fixes.
Internal crate entry points remain explicitly authorized for this backend lane.

## Configuration and execution

| Setting | Value |
| --- | --- |
| Source baseline | `c011512bc129803215e33d0b7f93ac1becccc68a` |
| Final production source | `eca5ca749608b1b9f8e63a9ac8b41dd309772727` |
| Rust / host / features | Rust1.85.1, macOS ARM64, locked/offline, jobs2; layerfs-persistence/postgresql + layerfs-control/postgresql |
| Flags | shipped aarch64 AES/polyval/NEON cfgs and +aes,+sha2; ordinary repository profile |
| Docker image | `postgres@sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652` |
| Server | actual PostgreSQL17.11 Debian17.11-1.pgdg12+2 aarch64 primary and streaming physical standby |
| Isolation | explicit Disposable owned fixture; SCRAM; self-signed primary TLS; missing-amcheck database; no user service |
| Setup/cache | warm compiled target and dependencies; owned fixture reused, each test creates independent schema/database; no cold/cache/performance claim |
| Command | README five-target command via private environment loader; build first with --no-run; inner90/outer100 seconds |
| Receipt | `cargo-macos-3ff58034a92d4446a3b5933f4005928b` |

Compiled/tested staged inputs have the exact final tree above; only the commit
object was created afterwards. The loader's earlier HEAD label is the baseline,
not a claim that the modified source was already committed when run. Every
required environment variable was loaded and all real fixtures executed;
environment-missing returns are not counted as proof. No daemon or bundle is
involved in these internal backend tests.

## Result ledger

| Test target (existing baseline first) | Passed | Failed / ignored |
| --- | ---: | ---: |
| postgresql_diagnostic | 5 | 0 / 0 |
| doctor_store_postgresql | 3 | 0 / 0 |
| postgresql_doctor_access | 6 | 0 / 0 |
| postgresql_doctor_cancellation | 5 | 0 / 0 |
| postgresql_doctor_physical | 12 | 0 / 0 |
| Total | 31 | 0 / 0 |

| Additional fault/control | Expected → observed | Verdict |
| --- | --- | --- |
| Real first session preflight succeeds; second authentication stalls after actual startup bytes | `store.connection.identity` Pass, cancelled second socket EOF independently observed, `store.admission.cancelled` Unknown, no logical snapshot | PASS |
| Owned lock acquired after preflight; second schema query blocks | Independent server monitor observes actual Lock wait then sets cancellation; result incomplete, zero retained backend work/xmin independently verified; owned lock process terminated and joined | PASS |
| catalog_incarnation ALTERed to TEXT with1MiB value | Preflight identity Fail through pg_typeof guard, not raw allocation; independent proxy below512KiB wire; no doctor source writes | PASS |
| format_profile ALTERed to TEXT with1MiB value; same incarnation fault through full admission | Trusted actual column-signature predicate produces no raw metadata row; independent proxy below512KiB; pinned prior handle emits `store.schema` Fail and no snapshot | PASS |
| Healthy snapshot label | Server-side MD5 of snapshot text exposes exactly32 hexadecimal bytes, explicitly labelled non-authority; raw active-XID list remains server-side | PASS |

Schema projection remains in the same source read-only transaction as its
trusted-column check. Logical checks keep one coherent read snapshot; physical
amcheck coverage remains a separate live interval. Admission cancellation now
covers both sessions, their handshakes and schema SQL with scoped joined
watchers; audit cancellation remains covered by the baseline tests. Fixed-size
snapshot labels do not authenticate authority; actual catalog/binding/incarnation
are separately revalidated. No extra migration/helper relation/extension or
normal writable open is introduced. Data fingerprints are unchanged at stable
fixture boundaries. No measured peak-RSS or server-physical-byte claim.

## Executable pins

| Executable | SHA-256 |
| --- | --- |
| doctor_store_postgresql-ab6a2f69f34c4da0 | `15340f5808c1a46a1a4db4e2e6fc67bf22164528114e3bdd317aaadf96de6819` |
| postgresql_diagnostic-31ddd1734e1cff93 | `c0fe41799e53a3f2453a8453ed43c4246c54cdeba9ef783dd9a412ee78540d45` |
| postgresql_doctor_access-aeb20c01e44176fd | `dad81f7ff67ee5509879254efd95cb37f600fe074c60d384183a54723ab1f524` |
| postgresql_doctor_cancellation-e40df0e1f402e0cc | `c2f4d17e9b42b9c83d86d28367dcd983d1f175294959eec86a679f0ac18032c6` |
| postgresql_doctor_physical-979e857ffedda515 | `bb102f93171e8b64729277aeedbb6c8f4746ac6d2926b1c65e210c72efffb935` |

PostgreSQL all-target warning-denying Clippy passed:
`cargo-macos-e2bdcc3e817d436fb923393438022871`. Product boundary guard1306,
changed Rust formatting and whitespace checks passed. Exact production count
151040→151058 (+18; control+4,engine+14), tests/docs excluded.

## Retained failures, limits and cleanup

Two development Control test setups were invalid: using an arbitrary schema
where the saved Store contract fixes `layerfs` per database, and waiting for
psql stdout that was buffered until the multi-statement script ended. The final
fixture uses independent owned databases, proper secret references and actual
server PgSleep/Lock observations before signalling; no timing guess or invalid
expected failure is counted. A test compile missed a qualified import and was
corrected before execution. All failed receipts stay private.

Baseline limits remain explicit: server17 live-DDL contract, unknown unsupported
randomized admission/non17 formatting, no offline checksums or strong-lock
parent check, bounded DNS cancellation boundaries. Linux getent lifecycle is
qualified by the separate runtime lane and is not double-counted here. Shared
history/acquisition and combined root integration have separate receipts.
No performance/coldness or full CLI/SDK parity claim.

Original acceptance primary/standby resources and private credentials remain
protected for root integrated reruns. Per-test databases, lock-holding processes
and proxy threads are cleaned/joined by their fixtures. The fresh harness
up/run/down proof already removed only its exact labelled resources, as in the
baseline report. Private product target stays warm. No unrelated cleanup or
reclaimed-space claim.
