# fsstress

Portable S01 v2 uses unchanged
[`secfs.test` at `edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed`](https://github.com/billziss-gh/secfs.test/tree/edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed/fsstress).
Native macOS and Linux execute the same two-process, 512-slots-per-process,
seed-1 profile. [cases.py](src/cases.py) freezes argv, symbolic error policy,
per-child accounting and provenance; [AGENTS.md](AGENTS.md) explains platform
semantics and the narrow Darwin dangling-symlink link exception.

Both binaries build with the upstream command `make -C fsstress`, without
patches or new tool dependencies. Native depends only on macOS `libSystem`;
Linux depends on the glibc supplied by the matching Debian base. Install at
`$BENCH_TOOL_ROOT/bin/fsstress` and provide Python 3.

| Artifact | SHA-256 |
| --- | --- |
| Native arm64 fsstress | `59a1c48b185d9ea7868e8be7f8806ccfc9714d45d41bdc855bb6a3125abe4618` |
| Linux aarch64 fsstress | `1e91b7d31af9989fdd81a0b59f76a8f6b940419e958a5883523645bbc6e3aca1` |
| Linux combined image | `sha256:cc0814884e1b2acb5ffee43792faf40e7dbb3573ca157ab22af4179632c64dd0` |

The combined image uses verified base
`sha256:66aeb6bbf7fc825686a0e6d8c8486d90c99d03ce81f854008f179a23bdf4097e`.
It packages the unchanged portable fsx/fsstress tools, pinned pjdfstest runtime,
Python and Perl/prove. Build recipe, package/binary manifest, logs and standalone
compatibility results remain local under `~/.cache/fs-six-fix-tools/build/`.
No source tree or binaries are published with reports.

Configure [environments.example.json](environments.example.json) with the selected
current LayerFS SHA, matched release artifacts, independent PostgreSQL databases,
ready tool roots and exact owned infrastructure. Every LayerFS operation uses
[the shared public-CLI runner](../shared/src/runner.py):

```bash
python3 fsstress/src/run.py prepare --environment /private/fsstress.json \
  --cache /owned/fsstress-cache --case S01 --machine native --backend sqlite
python3 fsstress/src/run.py run --environment /private/fsstress.json \
  --cache /owned/fsstress-cache --case S01 --machine native --backend sqlite \
  --output /retained/fsstress/S01/native/sqlite
```

Complete all eight rows in native/Docker/Lima/Apple Container order, SQLite then
PostgreSQL. Release each known-safe case through the CLI, then finish shared
campaign infrastructure once all selected suites release their users.

The result distinguishes requested slots, successful operations, no-object or
zero-size skips and expected errors. Each child must complete all 512 slots;
zero effective work or unexpected errors fail. Requested read/write lengths are
reported separately from transferred bytes. Native uses 16 KiB pages and Linux
uses 4 KiB pages, so the page-derived request ranges differ; these are descriptive
diagnostics rather than identical-byte performance comparisons.

Extra committed-result proof is off by default and explicitly unsupported.
Upstream checks remain active; unknown cache state means INELIGIBLE. Preserve
prior v1/Linux-only evidence and the failed initial native standalone error-policy
check. Neither is silently converted into a current successful row.
