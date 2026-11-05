# fsstress tool build

> Status: Current general guide.

S01 v2 uses unchanged
[`secfs.test` at `edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed`](https://github.com/billziss-gh/secfs.test/tree/edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed/fsstress).
Back to the [README](README.md); the frozen rules are in [AGENTS.md](AGENTS.md).

## Build

Both binaries build with the upstream command `make -C fsstress`, without
patches or new tool dependencies. Native depends only on macOS `libSystem`;
Linux depends on the glibc supplied by the matching Debian base. Install at
`$BENCH_TOOL_ROOT/bin/fsstress` and provide Python 3.

| Artifact | SHA-256 |
| --- | --- |
| Native arm64 fsstress | `59a1c48b185d9ea7868e8be7f8806ccfc9714d45d41bdc855bb6a3125abe4618` |
| Linux aarch64 fsstress | `1e91b7d31af9989fdd81a0b59f76a8f6b940419e958a5883523645bbc6e3aca1` |
| Linux combined image | `sha256:cc0814884e1b2acb5ffee43792faf40e7dbb3573ca157ab22af4179632c64dd0` |

## Linux combined image

The combined image uses verified base
`sha256:66aeb6bbf7fc825686a0e6d8c8486d90c99d03ce81f854008f179a23bdf4097e`.
It packages the unchanged portable fsx/fsstress tools, pinned pjdfstest runtime,
Python and Perl/prove.

## Local records

Build recipe, package/binary manifest, logs and standalone compatibility
results remain local under `~/.cache/fs-six-fix-tools/build/`. No source tree
or binaries are published with reports.
