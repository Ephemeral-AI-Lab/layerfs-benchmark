# fs-bench-quick diagnostic results

> Status: Research; informative and not a product contract.

**96/96 execution PASS, all case cleanup COMPLETE, final runtime cleanup
COMPLETE. All96 timings are INELIGIBLE diagnostics. Verification SKIPPED;
content correctness UNVERIFIED.** This is the owner-approved execution/cleanup
scope, not performance or release qualification.

The date is the campaign completion date in Asia/Singapore. The parent folder
identifies the full LayerFS source commit; this folder identifies the UTC-start
campaign. Never overwrite an existing campaign to publish another attempt.

- [Manifest, identities and file hashes](manifest.json)
- [Readable report and all96 receipt links](report/report.md)
- [Machine-readable phase times CSV](report/summary.csv)
- [Machine-readable summary JSON](report/summary.json)
- [Docker-baseline diagnostic ratios CSV](docker-baseline-diagnostics.csv)
- [Docker-baseline diagnostic ratios JSON](docker-baseline-diagnostics.json)
- [Original append-only CLI ledger](ledger.jsonl)
- [Runtime cleanup receipt](cleanup.json) and [absence audit](post-finish-audit.json)
- [Preparation and cleanup statistics](diagnostic-statistics.json)
- [Owner scope](owner-scope.json) and [change/evidence-reuse ledger](changes.jsonl)
- [Retained harness snapshot manifest](harness/manifest.json)

**End-to-end case time** includes Sandbox creation, mount, Exec, LayerFS Commit,
unmount and case cleanup. It excludes preparation and initial Python
startup/configuration validation. Exec/Commit times include CLI launch/routing.
In-Sandbox command-only time, full C01 outer wall time and complete remote
CPU/memory/storage peaks are unavailable. Requested ratios are arithmetic
comparisons of diagnostic observations, not qualified speed claims.

The CLI pin did not demonstrate cold live-Workspace cache state before Commit.
Earlier rows did not retain evolving harness source bytes; hashes and exact CLI
commands remain in the receipts/ledger. The completed source snapshot is not a
reconstruction of those earlier versions. The original campaign record contains
additional context: [campaign record](../../../../../fs-bench-quick/records/quick-20261105T185054Z.md).

Runtime resources and temporary credentials were released. The
[build-cache report](build-cache-report.json) separately records a protected
macOS target held by a pre-existing VM process. Protected evidence/artifacts and
that cache are not deleted by runtime cleanup. Other owners were preserved.

Raw receipts and the CLI ledger are preserved byte-for-byte. Private environment
configuration, credential files, runtime databases, binary bundles and unrelated
host/provider inventories are not published. Final tests and Ruff receipts are
included; no benchmark attempts were repeated for publication.
