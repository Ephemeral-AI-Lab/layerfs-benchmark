# fsx tool build

> Status: Current general guide.

How the pinned fsx binary is selected and built for X01 v2. The workload rules
are in [the suite guide](AGENTS.md).

## Upstream pin

The upstream source is portable secfs.test, pinned to
[`edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed`](https://github.com/billziss-gh/secfs.test/blob/edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed/fstools/src/fsx/fsx.c).
It runs unchanged. macOS and Linux use the same pinned upstream source and
flags, built separately for each platform. The exact flags and source/summarizer
hashes are in [cases.py](src/cases.py).

## Build

Build the unmodified selected source on each platform with
`make -C fstools/src/fsx`, then install the resulting `fsx` under `bin/`.
Only a C compiler and make are needed; preserve compiler diagnostics and source/
binary hashes. The native macOS build was established without a compatibility
patch. Default four-byte data elements and all intrinsic file-size/read-data
assertions remain enabled.

Provisioning and tool builds happen before measurement.

## Earlier v1 profile

The original v1 Linux-only xfstests profile used commit
`31f7192f90a89a6f808a37c3a3cd30491bd50eba`. Its six Linux passes and two native
NOT_RUN outcomes stay in the original campaign receipts. The owner authorized
v2 prospectively to cover the full matrix with one portable upstream; previous
results are never relabeled as v2. See [the suite guide](AGENTS.md).
