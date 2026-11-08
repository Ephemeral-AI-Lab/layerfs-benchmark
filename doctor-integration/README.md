# doctor-integration — backend correctness qualification
> group: filesystem · measures: correctness

Combines the Doctor remaining-backend B1–B6 acceptance ledger with exact product test, PostgreSQL and real runtime/provider source pins. This is correctness qualification; it makes no performance or cold-cache claim.

The reusable [PostgreSQL fixture harness](../doctor-postgresql/) and [public-CLI runtime recorder](../doctor-runtime/) own isolated test resources. Persisted corruption fixtures remain in the product crate tests. Build first using registered private worktree resources, explicitly select Disposable, and bound each test invocation to at most120 seconds. No Durable execution or live-data corruption.

Frontend additions, GC and unrelated filesystem lifecycle work are outside this completion scope. Reports retain failed fixtures, unsupported capabilities, source pins and independent cleanup custody.

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-08 | `89c4e52828` | Outcome: PASS for Doctor integration on the current v2 target | [report](../result/2026-11-08/doctor-integration/89c4e5282883af343116cd7a362902f369f8c5a1/report.md) |
| 2026-11-08 | `6b9640783c` | Outcome: PASS for the specified Doctor backend contract | [report](../result/2026-11-08/doctor-integration/6b9640783c4652b7ad662d9610ab8a89670a7d85/report.md) |
<!-- runs:end -->
