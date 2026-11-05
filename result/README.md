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

The six-suite campaign completed its active **17 cases / 136 execution PASS
rows** on 2026-11-06. Case cleanup and final runtime infrastructure cleanup are
COMPLETE. Timings and Docker ratios remain **INELIGIBLE diagnostics**, and
optional independent benchmark verification remains SKIPPED.

| Active report | Cases | PASS rows | LayerFS product identity |
| --- | ---: | ---: | --- |
| [fio](2026-11-06/fio/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) | 4 | 32 | `b919f50e…` |
| [fsx portable v2](2026-11-06/fsx/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) | 1 | 8 | `b919f50e…` |
| [fsstress v2, corrected product](2026-11-06/fsstress/b9ad9edd7ea3a9314625dee53466aa59a7ea69c7/report.md) | 1 | 8 | `b9ad9edd…` |
| [mdtest launcher v2](2026-11-06/mdtest/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) | 2 | 16 | `b919f50e…` |
| [pjdfstest unprivileged subset v2](2026-11-06/pjdfstest/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) | 4 | 32 | `b919f50e…` |
| [smallfile](2026-11-06/smallfile/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) | 5 | 40 | `b919f50e…` |

This is 128 passing rows at
`b919f50eaf9cce79671f8501a580279d23cc5f3c` plus eight at clean derived product
`b9ad9edd7ea3a9314625dee53466aa59a7ea69c7`. It does not qualify the entire
matrix at the corrected commit. The fsstress workload/error policy is unchanged;
the product now permits Workspace hardlinks to symlink inodes. No ratio mixes
these product treatments. The correction also passed 135 focused product checks
and separate ASCII-target public CLI proof on all eight configurations; that
does not establish arbitrary-byte support through every host-client route.

| Retired selection | PASS | FAIL | NOT_RUN |
| --- | ---: | ---: | ---: |
| fsx v1 | 6 | 0 | 2 |
| fsstress v1 | 6 | 0 | 2 |
| [fsstress v2, original product](2026-11-06/fsstress/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) | 2 | 1 | 5 withdrawn |
| pjdfstest v1 | 0 | 0 | 32 |
| mdtest v1 | 4 | 1 | 11 |

Historical failures and prerequisite outcomes remain retained. The
[immutable earlier report index](https://github.com/Ephemeral-AI-Lab/layerfs-benchmark/blob/11b252ab4bf530fdfd7dd02822ee6f571b496e14/result/README.md)
preserves the original released reports. The failed non-UTF8 native NFS public
CLI proof also remains retained with a separate completed-cleanup resolution;
its successor froze an ASCII target before execution.

The latest runtime teardown took **2.981238417 s**. Separate cleanup released
the private Linux build volumes and a stopped test container; native target
artifacts held by a live VM remain protected. Pinned tools, recipes and local
evidence remain. Build-cache disposition is separate from runtime cleanup.
