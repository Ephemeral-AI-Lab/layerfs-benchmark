# fsx

X01 v2 runs the unchanged portable secfs.test `fsx`, with built-in size and read-consistency
checks, through the public LayerFS CLI. One shared lifecycle supports the four
machine routes and both databases. macOS and Linux use the same pinned upstream
source and flags, built separately for each platform.

The upstream source is pinned to
[`edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed`](https://github.com/billziss-gh/secfs.test/blob/edf5eb4a108bfb41073f765aef0cdd32bb3ee1ed/fstools/src/fsx/fsx.c).
The exact flags and source/summarizer hashes are in [cases.py](src/cases.py).
There are 1,000 requested slots, seed 1, a maximum 8 MiB file and maximum 64 KiB
operation. Flags are `-S 1 -N 1000 -F 8388608 -o 65536 -R -W -v -P <owned-logdir> fsx.data`.
Only ordinary read/write/truncate work executes; zero-size/past-EOF operation
slots remain skipped and are separately counted. No sync option or
verification-disabling option is selected.

Copy [environments.example.json](environments.example.json) to a local ignored
file and supply the matching product artifacts and owned database/infrastructure
records. Set each machine's `tool_environment.BENCH_TOOL_ROOT`; its platform's
tool is `bin/fsx` beneath that root. Python 3 must also be on the machine's PATH.
Provisioning and tool builds happen before measurement.

```bash
python3 fsx/src/run.py prepare --environment fsx/environments.local.json --matrix --cache /owned/fsx-cache
python3 fsx/src/run.py run --environment fsx/environments.local.json --matrix --cache /owned/fsx-cache --output /owned/fsx-results
```

Default independent proof is skipped. `--verify` is rejected explicitly because
a separate committed-result oracle has not been implemented. Tool-internal
checks still run, and a success banner without complete operation records or
without effective work fails result parsing. The CLI receives a compact summary;
temporary upstream diagnostic logs are outside the Workspace and are removed
after successful summary generation, or released with the owning Sandbox.
Cache state remains diagnostic unless separately demonstrated.

Build the unmodified selected source on each platform with
`make -C fstools/src/fsx`, then install the resulting `fsx` under `bin/`.
Only a C compiler and make are needed; preserve compiler diagnostics and source/
binary hashes. The native macOS build was established without a compatibility
patch. Default four-byte data elements and all intrinsic file-size/read-data
assertions remain enabled.

The original v1 Linux-only xfstests profile used commit
`31f7192f90a89a6f808a37c3a3cd30491bd50eba`. Its six Linux passes and two native
NOT_RUN outcomes stay in the original campaign receipts. The owner authorized
v2 prospectively to cover the full matrix with one portable upstream; previous
results are never relabeled as v2. See [the suite guide](AGENTS.md).
