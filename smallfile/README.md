# smallfile

Five two-worker file workloads: create, read, stat, rename and delete. Every
worker processes 256 files of 4 KiB. Read/stat/rename/delete use committed inputs
created by the same pinned tool during destination preparation.

Pin [distributed-system-analysis/smallfile](https://github.com/distributed-system-analysis/smallfile/tree/aa2519de5bf0b3b383db2c31eacbf8ac4328e19c).
Copy its unmodified Python tree once to `BENCH_TOOL_ROOT/smallfile`; provide
Python 3. The suite uses an explicit POSIX fork context on macOS and Linux,
upstream --as-host bench, fixed sizes/distribution, full completion and enabled
read verification. Extra xattr/fallocate libraries are unnecessary for these
selected operations. Exact commands and provenance are in src/cases.py.

The hidden hostname flag prevents changes in Sandbox hostname from breaking
prepared names. Workspace-local TMPDIR retains seed files across setup Commit
and bounds cleanup to campaign-owned state. Tool code stays outside the Store.

Use `python3 smallfile/src/run.py --help`, supplementing the environment example
with the campaign's product artifacts, home and database ownership. Extra
committed-result verification is optional/off by default. Tool-internal read
checks are always enabled. Upstream includes a 2–3 s synchronization delay;
retain it, and report its file rate separately from complete CLI time.

Unknown cache state is INELIGIBLE, even if execution and internal checks pass.
Every case and final infrastructure release must complete or retain an exact
reason/custody record. See [AGENTS.md](AGENTS.md) for workload and reporting rules.

Payload `--fsync N` does not remove upstream control-file synchronization:
`sync_files.write_sync_file` and `write_pickle` call fsync for their gate/result
files. Preserve those intrinsic calls and report them; this profile does not
claim zero fsync requests. LayerFS remains Disposable/OFF.
