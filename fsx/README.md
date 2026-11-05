# fsx

X01 runs the original Linux xfstests `fsx`, with built-in size and read-consistency
checks, through the public LayerFS CLI. One shared lifecycle supports the four
machine routes and both databases. Native macOS is explicitly unsupported by
this unchanged upstream, rather than using a different tool on that row.

The upstream source is pinned to
[`31f7192f90a89a6f808a37c3a3cd30491bd50eba`](https://kernel.googlesource.com/pub/scm/fs/xfs/xfstests-dev/+/31f7192f90a89a6f808a37c3a3cd30491bd50eba/ltp/fsx.c).
The exact flags and source/summarizer hashes are in [cases.py](src/cases.py).
There are 1,000 requested slots, seed 1, a maximum 8 MiB file and maximum 64 KiB
operation. Only ordinary read/write/truncate work executes; upstream disabled
operation slots remain skipped and are separately counted. No sync option or
verification-disabling option is selected.

Copy [environments.example.json](environments.example.json) to a local ignored
file and supply the matching product artifacts and owned database/infrastructure
records. Set each machine's `tool_environment.BENCH_TOOL_ROOT`; the Linux tool
is `bin/fsx` beneath that root and requires only glibc. Python 3 must also be on
the guest PATH. Provisioning and tool builds happen before measurement.

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

Unmodified Linux build: use Debian 12/aarch64 with a C compiler, make, autoconf,
automake, libtool-bin, uuid-dev, libattr1-dev, libacl1-dev and xfslibs-dev. Run
`make configure`, `./configure --disable-shared`, `make -C lib`, then
`make -C ltp fsx fsstress`. Install the resulting executables under `bin/`.
No generated build file is a third-party source patch. Record compiler/package,
source and binary identities. The native compiler fails on the required XFS/
Linux headers; do not fake a compatibility header.
