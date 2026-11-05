# fio agent instructions

> Status: Implemented diagnostic workload contract; no cold-cache qualification.

Follow root [AGENTS.md](../AGENTS.md) and [SPEC.md](../SPEC.md). This suite owns
four cases and 32 rows. Execute F01–F04; for each case use native, Docker, Lima,
Apple Container; SQLite then PostgreSQL. Keep timed rows serial. All LayerFS
operations use the pinned public CLI through [the shared lifecycle](../shared/src/runner.py).
Do not run SDK calls, direct Store SQL, implicit fixture creation in a read job,
automatic retry, pre-touch or warm-up.

## Frozen workloads

The unchanged upstream tool is `fio-3.40`, commit
`ff930c4653ae3952d6b09ab3ec89671aeabf2cbe`. Exact arguments, setup and their
hashes are in [src/cases.py](src/cases.py), workload `fio-buffered-single-pass-v1`.
No third-party patches are authorized.

| Case | Operation | Bytes per pass | Block bytes | I/O count | Starting view |
| --- | --- | ---: | ---: | ---: | --- |
| F01 | Sequential write | 67,108,864 | 1,048,576 | 64 | Empty |
| F02 | Sequential read | 67,108,864 | 1,048,576 | 64 | Committed fio data |
| F03 | Random write | 8,388,608 | 4,096 | 2,048 | Empty |
| F04 | Random read | 8,388,608 | 4,096 | 2,048 | Committed fio data |

All jobs use `sync`, depth 1, one job/thread, buffered I/O, seed 1,
`tausworthe64`, default enabled random map and one byte-count pass. No time-based
loop, ramp, pre-read, allocation, sync-on-create/end/close or automatic cache
invalidation is requested. Read jobs set `allow_file_create=0`. Writes use the
explicit **compressible nonzero repeated byte `0x5a`**; this is not random-content
or incompressible-data qualification. Random offset selection still uses the
fixed seed. Preserve these semantics on macOS and Linux.

For F02/F04, prepare with the same pinned fio, sequential write and matching
size/block/pattern. Construct it on the destination after any small SQLite push,
Commit it, then unmount/close setup. The timed read neither creates nor rewrites
that fixture. Keep tools outside Store contents under `BENCH_TOOL_ROOT`.

## Results and limits

Check CLI and workload exits, then `parse_result(case_id, stdout, stderr,
exit_code)`. Require exactly one matching job, tool error zero, exact bytes and
I/O count, zero short/drop I/O, no opposite-direction bytes, expected effective
job options and finite upstream metrics. Malformed output, zero/partial work or
unexpected errors are FAIL. Report `bw_bytes` as bytes/second, IOPS as I/O/second,
`runtime` in milliseconds and completion latency in nanoseconds. Tool times
and CLI wall time are distinct metrics.

Default performance deadline is 15 seconds and setup deadline 25 seconds. Warm
artifact reuse is allowed; page/daemon/database caches are not proven cold.
Timings and ratios remain INELIGIBLE diagnostics. fio's normal status/error
checks remain enabled; they are not independent committed-result proof.

Independent proof is off by default. `--verify` checks exact root contents,
regular type, size and every byte of the `0x5a` pattern after measured unmount.
Its target is at most one second and its separate total budget stays below ten
seconds. Never add proof by replaying an unchanged sample.

Release each known-safe case through the shared CLI lifecycle, and preserve
uncertain state and its containing resources. Final shared campaign cleanup is
required, including database data; PostgreSQL disconnect is not deletion. Publish
only the compact suite report in the root result convention, with explicit
execution, verification, eligibility and final-cleanup outcomes. Local builds,
raw JSON, logs, manifests and receipts remain ignored.
