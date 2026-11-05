# smallfile benchmark

Read root [AGENTS.md](../AGENTS.md). L01–L05 are create/read/stat/rename/delete,
40 registered rows. Execute case → native/Docker/Lima/Apple Container →
SQLite/PostgreSQL using the shared public LayerFS CLI lifecycle.

Pin unmodified distributed-system-analysis/smallfile commit
`aa2519de5bf0b3b383db2c31eacbf8ac4328e19c`. src/cases.py freezes source hashes,
flags, first-party launcher and fixture semantics. Each case uses two upstream
workers (processes), 256 files each, 4 KiB data and records, 64 files per directory,
four subdirectories per directory. Fixed sizes, no directory hashing or shared
worker directories; --stonewall N, --finish Y and --verify-read Y.
No distributed --host-set/launcher. Do not shrink counts or drop read checks.

Use upstream's hidden --as-host bench flag so prepared filenames survive a new
Sandbox hostname. Set TMPDIR=$PWD/.smallfile-tmp before imports; seed/log/control
files stay in the owned Workspace and preparation seeds survive Commit. The
first-party launcher selects multiprocessing's supported fork context on both
macOS and Linux; it does not edit or monkeypatch upstream. Data is the pinned
nonzero deterministic create_biggest_buf(False) pattern, not incompressible
random payload. Time-based upstream seeds are retained but do not change this
fixed/unhashed payload selection.

L02–L05 consume files built by the same create tool/configuration in destination
setup and committed before measurement. L01 starts empty. Setup and measured
state are independent per row. The tool's own directory preparation and its
intrinsic 2–3 s synchronization delay stay in Exec; never relabel its reported
per-worker rates as CLI wall or remove this delay by patching third-party code.

Parse both per-worker statuses and exact 512 total files; upstream may print
warnings while exiting zero. Missing workers, partial work or read mismatch is
FAIL. Preserve the upstream files/sec aggregation denominator. A sub-millisecond
upstream interval may have no rate; retain UNAVAILABLE with its reason.

Budget 15 s for the complete performance invocation. Optional independent proof
off by default, below 10 s, checks committed filenames/content or deletion.
Do not add implicit fsync, response-time output, warm-up or retries. Unknown
caches remain INELIGIBLE diagnostics. Required per-case and final campaign cleanup
preserves uncertain state; publish only the required short report.

Payload `--fsync N` does not remove upstream control-file synchronization:
`sync_files.write_sync_file` and `write_pickle` call fsync for their gate/result
files. Preserve those intrinsic calls and report them; this profile does not
claim zero fsync requests. LayerFS remains Disposable/OFF.
