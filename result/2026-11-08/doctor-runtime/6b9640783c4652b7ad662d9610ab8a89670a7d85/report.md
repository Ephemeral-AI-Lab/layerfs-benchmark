**PASS — B6 Doctor expectations passed, including the integrated Linux worker and full/quick SQLite routes; an independent native NFS teardown failure remains preserved in issue #136.**

This is backend correctness and observation-safety qualification for Doctor B6,
not a performance or cold-cache benchmark. Frontend additions and GC are excluded.
Public LayerFS operations used the absolute pinned CLI, a private home and
`LAYERFS_CONSTRUCTION_WORKERS=1`; new Stores used public `store create`, whose only profile is Disposable (verified in setup receipts).
Actual runtime setup and diagnostic operations have separate receipts. Each
Doctor/test invocation was bounded at100 seconds; fixture/build steps at300.

## Pins and environment

| Item | Identity |
| --- | --- |
| Integrated qualification source | `6b9640783c4652b7ad662d9610ab8a89670a7d85`; later product head `93aed94f12` changes only tests/docs |
| Integrated macOS CLI | SHA256 `be033e74312b8b22a27869daf2e2450c5553c8c2034d7baa9d9f9f5af60a2858`, machine/TLS/PostgreSQL |
| Integrated macOS daemon | SHA256 `994b5091dfd145edab97458a3b22c7495a8a2d6125247b78bb29d855772d78b5`, PostgreSQL enabled |
| Integrated Linux bundle | `a072d9e97f5d216516d487a832ec925967c91303491f327da0d4720272d06129`, exact integrated source; daemon+worker PostgreSQL, guest worker without host machine adapters |
| Product fixes | `d2a1977989f38e4cbd13b820179c0fac89635df5` |
| Additional Doctor worker negatives | `5ca38b3865c80241e02bd2b6d6e276c74b8342ea` (tests only) |
| Pinned macOS CLI | SHA256 `d028963689cd06e7abce020b437fc397dd489bece9e90ba52f147f1914a42a20`, built at `d2a1977989` with machine,TLS |
| Initial Linux bundle | `c15d80ce858c52429de0850eb12d7ce6f83c25a1fa6777cee19d0c39ccdc2283`, source `8f0b962be3`; preserved for explicit compatibility tests |
| Fixed-family Linux bundle | `63c0bf78214a8947957f7e95fadfd74cdfe95c990723c78509b856279a27197d`, source `d2a1977989` |
| Host | macOS26.4.1, Darwin25.4.0, arm64 |
| Providers | Docker client/server29.5.2 (Linux6.12.76-linuxkit aarch64); Lima2.2.1; native process/NFS |
| MinIO | RELEASE.2026-09-22T19-25-18Z; image `sha256:4692462f35d97d7e82c30371d82f057703c5d9489bcae726010594c812f2d285` |
| R2 | Existing saved operator connection, TLS and saved-prefix listing; account/credentials private |
| Recorder | benchmark commit `05ecac3`; six recorder unit tests passed |

Raw outputs, credential-bearing environment files, provider ownership receipts,
before/after hashes and manifests remain private under the registered worktree's
`qualification/` directory. `final-receipts/<case>.json` and `integrated-receipts/<case>.json` record source commit,
tracked patch SHA, CLI SHA, arguments, expected checks, actual report, coverage,
logical-record comparison, duration and verdict. They are not published bundles.

## B6 requirement-to-evidence map

| Requirement | Actual environment or focused test | Receipt/case | Result |
| --- | --- | --- | --- |
| Host current layout, capacity/identity, active mounted runtime excluded | Real initialized home with one active native NFS workspace; records/artifacts/bundle pass in24.6ms | `host-mounted-runtime-final` | PASS |
| Default native artifact present/absent; absent home stays absent | Actual pinned CLI and isolated cache/home selections | `host-absent-home-default-artifact`, `host-default-native-absent-cache` | PASS |
| Configured artifacts, manifest compatibility and required files | Owned artifact directory references pinned binaries; wrong manifest version and absent helper fail only applicable checks | `host-configured-artifact-valid`, `host-artifact-wrong-version`, `host-artifact-required-missing` | PASS |
| Unused optional tools do not suppress independent checks | Empty PATH; independent record/artifact/bundle observations still pass | `host-unused-optional-tools` | PASS |
| Host current/previous/malformed, live/dead owners and observable record race | Eight crate-local Host fixtures, including unchanged modes and inaccessible runtime subtree | `cargo-macos-8d0fa90d9e87486785c907f67c7ac7ee`, `doctor_host` | PASS |
| Machine supported native, Docker and VM running | Real native, Docker worker and Lima worker | `native-machine-final`, `docker-machine-final-old-bundle`, `lima-machine-final-old-bundle` | PASS |
| Actual provider stopped/missing; no lifecycle effect | Own Docker/Lima stopped publicly before read-only diagnosis; fresh-home missing Docker runtime never created | `docker-actual-stopped-typed-outcome`, `lima-actual-stopped`, `docker-missing-without-worker-registration` | PASS |
| Actual incompatible worker version/bundle | New sealed bundle expectation against old owned Docker/Lima workers; hello compatibility fail, ping blocked | `docker-real-bundle-mismatch`, `lima-real-bundle-mismatch` | PASS |
| Machine missing tool/active intent/bad endpoint | Existing dedicated provider and machine fixtures preserve home and prevent lifecycle/probe calls | `doctor_provider`, `doctor_machine_target`, baseline combined suite receipt `cargo-macos-5cf15f78999d484ba423a3cfa163ee62` | PASS; reused baseline |
| Doctor worker wrong protocol/version, typed ping refusal, ping timeout | Dedicated DiagnosticWorker path; incompatible hello sends no request; peer closes/joins and saved home stays unchanged | `cargo-macos-1763183276144ca59f6bc72ecd1ef3b0`, `worker_failure` matrix | PASS |
| Sandbox actual local/worker/forward routes | Native process, Docker fixed-root worker, Lima SSH forward | initial `native-real-daemon`, `docker-real-worker-daemon`, `lima-real-forwarded-daemon`; final `native-session-log-proof`, `lima-forward-own-session-final` | Registry/route PASS; initial log side effect fixed below |
| Actual stale/restarted identity, lost runtime, reused carrier identity, missing worker metadata and authentication denial | Owned real-runtime negative test; separately create/close native daemon, never kill primary | `cargo-macos-8a7d64c46c334c42bc1d31bd59badb42`, `actual_runtime_negative_observations_preserve_records_and_ownership` | PASS |
| Busy producer/consumer, changed/interrupted pages and cancellation | Real Engine Service admission gate produces typed Busy with2 requests/2 joined threads, unchanged rows and zero Store SQL/object batches. Bounded authenticated peers verify consumer incomplete/cancellation behavior. Engine test also detects real registry generation change | `doctor_registry` at `6c868c390c`, receipt `cargo-macos-80a10b38bc4240e48688e287d32a9364`; `doctor_sandbox::busy_changed_lost_reply_and_deadline_remain_incomplete_without_replay` | PASS; crate producer + protocol consumer + live route composition, no live pressure campaign |
| Successful owned session releases cleanly | Actual native daemon with one mounted workspace: EndSession pass; exact daemon.log hash and logical ownership unchanged | `native-session-log-proof`; `native-session-log-proof.json` | PASS |
| Linux actual bounded getent and helper cleanup | Actual getent child against owned DNS blackhole: two DNS packets,150ms timeout, child killed/reaped (ECHILD), observer/server threads joined | `linux-resolver-lifecycle-final/output.log`; no-run `cargo-linux-56aeb1dad41245b585fe9ad07df3fad3` | PASS |
| Linux final integrated worker/daemon and remote SQLite path | Same-pin Docker and Lima machine compatibility/ping, actual worker and forwarded daemon sessions, mounted workspace registry | `integrated-docker-machine`, `integrated-lima-machine`, `integrated-docker-worker-daemon`, `integrated-lima-forward-daemon` | PASS; complete coverage, logical records/leases unchanged |
| Integrated remote SQLite full/quick | Both owned Docker and Lima Stores: full58 pass; quick55 pass/3 explicit skips; both modes complete | `integrated-b6-docker-full`, `integrated-b6-docker-quick`, `integrated-b6-lima-full`, `integrated-b6-lima-quick` | PASS; all four read-only audits |
| Integrated native independent control path | Fresh private home with exact pinned daemon, Disposable Store and no mounted workspace; Host/Machine/Sandbox/session pass | `integrated-native-host`, `integrated-native-machine`, `integrated-native-sandbox` | PASS; no NFS serving claim |
| Integrated successful-session logs | Actual worker and forwarded daemon each retain one mounted workspace; native has0; all daemon.log hashes unchanged | `integrated-worker-clean-log`, `integrated-forward-clean-log`, `integrated-native-clean-log`; `integrated-log-proofs.json` | PASS |
| MinIO saved-prefix listing and version-owned PUT/GET/DELETE | Actual owned versioned MinIO; immutable version ownership, not key-only delete | `minio-versioned-final`; exact `minio-before.jsonl` = `minio-final-after.jsonl` (3 existing versions) | PASS; no probe leftovers |
| R2 TLS connection/listing | Actual saved credentials, host IPv6+IPv4 resolution; IPv4 pre-send fallback; repeated on exact integrated source | `r2-list-final`, `integrated-r2-list` | PASS |
| R2 unsafe/unowned write blocked | Actual versioning prerequisite HTTP403: capability Unknown, PUT/GET/DELETE Blocked, coverage incomplete | `r2-write-gated-final`, `integrated-r2-write-gated` | PASS safety gate; R2 write capability unqualified |
| S3 uncertain mutation, collision, replacement, cleanup denial/loss | Existing fault-peer tests retained; new address fallback test proves exactly one PUT/committed version despite lost reply | `doctor_connection`, `doctor_backup_target`; affected S3 `cargo-macos-a8f48a14a112404faa1bee78e64543ac` | PASS; no operation replay |

## Diagnosed failures and retained evidence

- Original R2 Doctor selected only the first (unreachable IPv6) address while
  the ordinary saved connection succeeded. Independent per-address observations
  showed two IPv6 failures and two IPv4 successes. The fix tries TCP addresses
  under one budget only before sending any TLS/HTTP bytes; it keeps the original
  TLS hostname. A TLS/HTTP failure never restarts the operation.
- Original native diagnosis passed its checks but appended daemon.log errors
  by dropping a successfully authenticated session without EndSession. The fix
  closes only that owned session within the remaining budget; uncertain or
  quarantined exchanges are never retried. Actual log hashes now match.
- Original Host metadata fingerprint and the first harness snapshot traversed
  runtime payloads. The harness stalled after a successful native mount. Only
  the confirmed owned recorder was stopped; the mutation was not replayed.
  A public Sandbox get reconciled the mounted workspace. Product and harness
  observations now select management metadata and exclude mount/runtime trees.
- Retained initial expectation mistakes are harness failures, not hidden passes:
  Stopped uses outcome `fail` with severity `warning`; unregistered worker
  checks are `skipped`; the macOS default artifact uses XDG cache rather than the
  Linux-only bundle override. Corrected cases preserve those original receipts.
- The first live negative test execution used an incorrect absolute CLI path;
  it failed before spawning a CLI operation. Corrected pinned-path execution
  passed. An initial R2 config had empty credentials and failed admission before
  networking; valid saved credentials were then discovered privately.

## Coverage boundaries and resources

Registry/control readiness does not establish FUSE/NFS serving, mutable-overlay
integrity or Store health. Skipped serving/overlay checks remain explicit.
Ambiguous raw authentication close remains Unknown. Host race comparison is a
bounded observed before/after check, not a transactional or ABA-proof snapshot.
Artifact presence does not authenticate bytes; bundle hash recomputation remains
explicitly skipped. Quick/full Store guarantees belong to the Store report.

Owned home identity `e3c4406e`, Docker runtime `lfs-e3c4406e-docker`, Lima VM
`lfs-e3c4406e-b6-vm`, MinIO `doctor-b6-minio-116-42658`, private Stores/projects
and pinned bundles remain owned/warm for integrated requalification. Docker/Lima
workspaces were publicly unmounted, Sandboxes closed and providers stopped before
redeployment. Existing user VM `lfs-ba8a6d34-lm` remained Stopped, and existing
user containers/provider policies were untouched. No R2 policy or object cleanup
was performed. Resource final release is pending the parent integration handoff. This is owned/warm custody, not a claim that cleanup is complete.


## Preserved native lifecycle failure

One public unmount attempt (integrated CLI against the original daemon from
source `8f0b962be3`, initial build receipt `cargo-macos-85dcbceba5404ec099c48264f792f43d`)
on the original native fixture returned exit125 after
66.18 seconds. It reported retained Detach custody: helper did not finish in60s,
KILL was attempted, no exit was observed after another5s, detached=false,
loops entered1/exited0/joined0. This operation was not replayed and no retained
runtime state was deleted. It is tracked independently in
[issue #136](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/136), not
misattributed to Doctor or the unrelated dependency-cycle issue #115.

Exact retained fixture:

- Home: `/Users/yifanxu/.cache/layerfs-worktrees/layerfs-doctor-complete--531158446566/qualification/runtime-home`.
- Runtime: `machine/native/run/lfs-e3c4406e-b6-native`; Sandbox `b6-native`;
  Workspace `b6-native:owned-native`, namespace1,
  ID `e1ffc5ddc8b32e434f32523c661b447a59a3e4bd483a1f2d511f0b2c1df30238`.
- Original daemon PID49942 remains alive. Helper PID90388 was later observed as
  a zombie child of49942; the exact workspace path no longer appeared in the
  mount table at that later observation. That does not settle the original
  daemon's retained custody or authorize deletion/replay.
- Evidence: `integrated-native-release-old.json` and `native-retained-custody.json`.

The final native Doctor proof uses independent home `integrated-native-home`,
identity3446c2a9, runtime `lfs-3446c2a9-native-integrated`, exact integrated daemon
and0 mounted workspaces. The earlier mounted-workspace clean-session log proof
remains separately pinned. Neither proof claims NFS filesystem serving or
successful cleanup of the original retained fixture.

## Validation and handoff

Product fixes/test commits: `d2a1977989` (+146 production LOC), `5ca38b3865`
(test-only +0), `6c868c390c` (test-only +0); integrated equivalents are in the
parent branch. Scoped builds, changed formatting, Clippy, dependency guard and
173 tooling tests passed. Root independently reports150 backend tests passed
(including31 PostgreSQL tests), all-target Clippy across8 packages and the1311-file
boundary scan at the combined candidate; these overlap reused cases and are not
added into a synthetic new-test total.

Unchanged bridge, bucket, Host fingerprint and sandbox-session source trees were
compared between `d2a1977989` and `6b9640783c`; no diff exists. Their earlier
specific fault/cleanup qualification is reused with its original pins. Integrated
runtime operations all use the exact combined source and immutable binaries.
Host free space after the batch was365.3GB; Docker guest free space was196.3GB
before redeployment (separate measurements, not product limits/test verdicts).
Pinned binaries/bundles, active owned runtimes and evidence remain protected for
parent handoff; the retained native fixture is explicitly excluded from routine
cleanup under issue #136.


Exact active handoff selections: Docker machine `docker` / container
`lfs-e3c4406e-docker` / Workspace `b6-docker-box:integrated-docker`; Lima machine
`b6-vm` / VM `lfs-e3c4406e-b6-vm` / Workspace
`b6-lima-box:integrated-lima`; independent native Sandbox `native-integrated`
in `qualification/integrated-native-home` (no workspace); MinIO container
`doctor-b6-minio-116-42658`. Use public Workspace unmount/Sandbox close/Machine
stop/remove for normal owned lifecycle cleanup; preserve the old native #136
custody. No user resource is included in the release selection.

## Final resource cleanup addendum — 2026-11-08T13:09Z

The earlier warm handoff is now superseded for normal active fixtures. All seven
public cleanup commands passed: Docker/Lima workspaces unmounted, both Sandboxes
closed, both owned providers stopped, and the independent zero-workspace native
Sandbox closed. The owned MinIO container was removed by exact recorded ID after
one last unchanged three-version inventory check. Docker is Exited; the owned VM
is Stopped; the user's separate VM remains Stopped. Provider data remains idle;
this does not claim that every retained byte or resource was deleted.

Pinned binaries/bundles and private evidence remain outside disposable targets.
The exact two idle Linux cache volumes were owner-released in
`qualification/cache-release-scope.json`; no cache deletion was applied. The
macOS debug target remains protected because PID49942 still maps its daemon
executable. Old native #136 custody, records, keys and runtime state were not
retried, forced, deleted or changed.

Copied R2/MinIO child-environment values were redacted and `minio.env` removed.
A bounded audit of123 owned metadata/receipt files found no additional copied
R2 credential values. Operator configuration was unchanged; protected old-native
recovery keys were preserved. Final receipts: `cleanup-receipts/`,
`cleanup-minio.json`, `cleanup-final-provider-state.json`,
`copied-credential-release.json`, `copied-credential-audit.json` and the cache
release scope. Host free space was362.2GB after cleanup; no300GB recovery or
global cleanup was required or claimed.
