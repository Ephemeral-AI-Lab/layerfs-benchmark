**PASS: all 101 CLI-only qualification operations and 588 separate product front-end outcomes passed on final source across native SQLite, native PostgreSQL and worker SQLite.**

# Saved branch/file SDK qualification

Source: `91a5940605576322255a722663a6b956acd0b1c5`, LayerFS 2.0.0, production source 146640 lines ([product PR #624](https://github.com/Ephemeral-AI-Lab/layerfs/pull/624)). The CLI-only runner in this repository imports no SDK, sends no private worker requests and executes no Store SQL. Separate focused product tests exercise actual JavaScript, Python sync, Python async and CLI clients; their outcomes are identified separately below.

## Configuration and identities

macOS aarch64 host; Rust 1.85.1 debug builds with PostgreSQL features. Every LayerFS operation uses a private home and independent disposable data. Native/worker SQLite uses the Disposable profile. PostgreSQL 17 uses fresh private databases with `synchronous_commit=off`. No Durable or FUSE workload ran.

| Artifact | SHA-256 / identity |
| --- | --- |
| Absolute CLI | `/Users/yifanxu/Ephemeral-AI-Lab/layerfs-sdk-verify-134/target/debug/layerfs` |
| macOS CLI | `9be4555204b5f599ac4dccbeb39f6e822b077b1cd38977f0726ca4838a8975b2` |
| Node addon | `741ef42482b63421167a039761d38661ea084331c89ce6a6daad75a27e88196e` |
| Python extension | `4fd97bd6257d4c65b5fad138d1b33355374d41630e318de842c7258981079435` |
| Sealed linux-aarch64 bundle | `4d3ea29503821cd98724c8e5f196b39624e9e9251b380f836e29493a3f147376` |
| Linux CLI/worker binary | `0b33861141ae43083a79cd4f7d0876368a6867eecb7f1a9fecba42cc3f92265c` |
| Linux daemon | `f2d33c8f89f78f32fb9caf7aacf3cee5b7df32502414e0b46acbe700ee098167` |
| Worker runtime image | `sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e` |

The matching bundle was rebuilt and sealed from the clean final source. CLI child calls have at most 20 seconds, the runner has a 110-second ceiling and each outer test at most 120 seconds. Product conformance uses a 100-second test deadline and 110-second outer deadline. This is correctness qualification: cache state is unspecified/warm, builds/images reused, and no performance or cold-cache claim is made.

## Results

The baseline `716197c4999fb087aa0fb17bac5ceb48b0b556ae` passed existing SDK smoke/contract tests and actual four-front-end routing on native SQLite, PostgreSQL and worker SQLite before the additions. It cannot exercise calls introduced by this change. Intermediate source results are retained locally and are not substituted for final-source results.

| Final route | CLI-only public operations | Separate product cases | Product front-end outcomes | Outcome |
| --- | ---: | ---: | ---: | --- |
| Native SQLite | 32 | 49 | 196 | PASS |
| Native PostgreSQL | 32 | 49 | 196 | PASS |
| Worker SQLite | 37 | 49 | 196 | PASS |
| Total | 101 | 147 | 588 | PASS, zero route skips |

Expected structured refusals count as successful assertions, including `InvalidInput`, `NoSuchPath` and `Capacity`. Each product case compares four real clients against the same Store. Equality retains full IDs, nulls, relationships, flags and coverage. Only actual-work counters (`scan.examined`, `scan.candidates_examined`) are excluded from semantic equality after independently checking integer bounds; persistent-client cache hits legitimately change work performed. Repeating the comparison page checks cold/warm semantic equivalence.

The final Node declaration, Python stub and coverage generators all passed `--check`. Inventory and CLI-help tests passed 2/2: 64 calls total, including eight branch calls and fifteen file calls. Three calls are added: `branch.commits`, `branch.get_commit`, `file.revision`. Earlier integrated-source strict TypeScript usage passed; Python stub checks passed six with two optional mypy checks skipped because mypy was absent. Those optional skips are not runtime evidence.

## Acceptance mapping

| SDK issue | Executed evidence |
| --- | --- |
| #129 shared contract | Typed immutable refs; moving-head pinned second page; invalid/conflicting pages; full-ID same-Store foreign-project refusals; scope guards; explicit Capacity instead of partial mandatory row; unknown/clipped coverage retained. |
| #130 saved branch history | Main publication and Init pages, unwritten side branch base, first Commit/base, compact summaries versus full details, source relationship, unavailable publication timestamp, legacy commit.get/list. |
| #131 branch comparison | All four Commit/Layer endpoint combinations; same bytes/different ownership discovered; exact same binary endpoint attribution false; cache-stable comparison membership/coverage. |
| #132 file revisions | Literal saved path revision including metadata and inherited history, pinned anchor, invalid page and folder-scope refusal. Additional deep/sparse traversal and large-budget cases are covered by retained product Store tests owned by the implementation agents. |
| #133 diff/blame/saved reads | Aligned unchanged-text owners; publication source and inherited Init owner; additions/deletions with opt-in missing sides; legacy missing refusal; binary unknown; clipped long-line blame; oversized mandatory diff Capacity; pinned read/stat/list/glob/grep. |
| #134 bindings/routes/docs | Generated declarations and coverage check; 64-call inventory/CLI help; actual JS/Python sync/async/CLI parity on all three routes; worker placement confirmed by public Store get. |

## Observations and limits

Main remains project core content. Its publication Layer is distinct from the source Commit; publication time is null/unavailable rather than borrowing source time. Comparisons discover attribution-only changes without inventing human authorship. Binary/coarse/unavailable provenance remains explicitly unknown. The client does not reconstruct Store history.

No renderer fixture, desktop launch, FUSE, Durable profile, PostgreSQL worker placement, remote network fault, performance ratio or mypy execution is claimed. Existing worker forwarding is exercised by real CLI placement and real SDK clients, not mock routing. This report is focused cross-layer qualification; the lead retains broader Rust regression/clippy evidence independently.

During earlier integration, baseline test assumptions for progress-call count and fake worker protocol framing were corrected without changing the product protocol. An actual publication read-lane regression and bounded-comparison/coverage issues found in review were repaired before the final source. An early baseline harness invocation used incorrect positional commit grammar, failed, and was corrected; that failure is retained rather than hidden or counted as product failure. Final qualified runs had no failures or automatic retries.

## Evidence and cleanup

Append-only raw receipts remain local/ignored: `sdk-branch-file/receipts/final-91a-{native,postgresql,worker}/{receipt.json,steps.jsonl}` and `final-91a-cleanup.txt`. Separate product JSONL/logs are at `/tmp/layerfs-134-evidence/qualified-91a/`; each route has 49 rows containing all four client outcomes. No raw JSON, log bundle or source copy is published in this repository.

All CLI Stores were removed/disconnected through public CLI calls; the CLI worker was stopped through `machine.stop`. Exact stopped worker `809c2b2a0078de7561386758932f3ce3a3847247c4b23515ea5233a219961003` and volume `lfs-b7f5af9f-docker-data` were ownership/bundle/mount checked and removed with provider tools. Exact owned PostgreSQL container `935e8108f9f9ec324375107ccf33b557d3701313a7dd5993935726e975a22f74` and its anonymous volume were stopped/removed after both suites finished. Product fixture workers and their exact volumes were released by the fixture after success. Benchmark private homes/input folders and evidence are retained; no manual LayerFS runtime-state deletion occurred. Final source build caches remain private and warm pending handoff, not globally pruned. Host free space after this batch was 362.07 GB; no disk recovery threshold was triggered.
