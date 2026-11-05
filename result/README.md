# Published benchmark results

> Status: Current general guide.

Publish reviewed datasets under:

```text
result/YYYY-MM-DD/benchmark/full-layerfs-commit/campaign-id/
```

- **Date:** campaign completion date, `YYYY-MM-DD`; record its timezone and date
  basis in the manifest. A campaign ID may encode a different UTC start date.
- **Benchmark:** canonical suite name, such as `fs-bench-quick`.
- **LayerFS commit:** full 40-character product source SHA used by the run, not
  the benchmark repository commit, a moving branch name or a guessed version.
- **Campaign ID:** unique run identity. Keep it even for the first campaign so
  later runs at the same date/product commit cannot overwrite earlier evidence.

The requested date/benchmark/product-commit path remains the stable grouping;
its README indexes campaigns. Do not rename an old run to a newer product pin,
overwrite failed outcomes, or mix artifacts from different product identities.

Each campaign contains a README, `manifest.json`, readable report, machine-readable
CSV/JSON, original row receipts, and the available command/cleanup evidence. The
manifest records product and harness identities separately, outcomes, known gaps,
and SHA-256 hashes of published files. Raw observations are immutable; derived
report corrections must record their scope and retain the original observations.
Git attributes preserve exact file bytes under `result/`, including CSV line
endings, so the manifest hashes remain valid after checkout on another platform.

Publish complete row accounting: execution, verification, performance eligibility
and cleanup remain separate. Diagnostic observations and requested ratios retain
their INELIGIBLE status. Label timing boundaries and use separate metric columns.

Working output under a suite's ignored `results/` stays local. Publish only an
explicitly selected, reviewed dataset here. Exclude credential files, private
environment configuration, runtime databases, build caches/binaries and unrelated
host/provider inventories. Preserve raw receipt bytes; omit sensitive evidence
rather than silently rewriting it as an original receipt. Record omissions.

See [the first fs-bench-quick publication](2026-11-06/fs-bench-quick/b919f50eaf9cce79671f8501a580279d23cc5f3c/quick-20261105T185054Z/README.md).
