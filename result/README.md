# Benchmark reports

> Status: Current general guide.

Publish one clear report per result:

```text
result/YYYY-MM-DD/benchmark/full-layerfs-commit/report.md
```

Use the completion date and full LayerFS product SHA. Include the outcome,
configuration, results, main observations, limitations and cleanup status.
Group tables cell by cell, with all machine/database configurations together.
List the baseline machine first.
Keep timing columns clearly named and diagnostic results labeled INELIGIBLE.

Keep logs, receipts, manifests, CSV/JSON exports and source copies local under
the benchmark's ignored working-results directory. Do not commit them here.

[fs-bench-quick, 2026-11-06](2026-11-06/fs-bench-quick/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md)

Six-suite campaign, 2026-11-06:

- [fio](2026-11-06/fio/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md)
- [fsx](2026-11-06/fsx/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md)
- [fsstress](2026-11-06/fsstress/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md)
- [mdtest](2026-11-06/mdtest/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md)
- [pjdfstest](2026-11-06/pjdfstest/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md)
- [smallfile](2026-11-06/smallfile/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md)
