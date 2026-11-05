# fio

Four small, finite buffered-I/O cases across four LayerFS machines and two Store
backends. See [AGENTS.md](AGENTS.md) for the frozen workload and cache limits.
This suite shares preparation, CLI execution, deadlines and cleanup with
[shared/src/runner.py](../shared/src/runner.py); it contains no separate lifecycle.

## Tools

Use unchanged upstream [fio 3.40](https://github.com/axboe/fio/tree/ff930c4653ae3952d6b09ab3ec89671aeabf2cbe),
commit `ff930c4653ae3952d6b09ab3ec89671aeabf2cbe`, annotated tag object
`3e0048fdd9e9832e0052de78ebdd39ab7393f911`. Native macOS arm64 and Linux aarch64
builds were checked outside LayerFS using all four exact command bodies and
read-setup jobs. Their successful tool checks do not establish product results.

| Build | Cached executable | SHA-256 |
| --- | --- | --- |
| macOS arm64 | `~/.cache/fs-six-tools/fio/native/bin/fio` | `78bffe4c98240a5e3d9fcde34d9662b4bbed03867d5ab5ed3648e8faefdc154c` |
| Linux aarch64, static | `~/.cache/fs-six-tools/fio/linux/bin/fio` | `7a4ba395670e0795b32dd102916ec2cb71b32a3f9d91d76bed0734c22e0d8bbd` |

The native executable uses only macOS system `libSystem` and `libz`; no Homebrew
runtime library is required. Linux's executable is static and needs no copied
shared libraries. Place each matching binary in a ready machine's tool directory
once, outside any LayerFS Store. Set `machines.<machine>.tool_environment.BENCH_TOOL_ROOT`
to that directory; the exact workload references `$BENCH_TOOL_ROOT/fio` and does
not embed machine-specific paths in its provenance.

Build with existing Clang/GNU make on macOS, or GCC/GNU make and static libc
headers on Linux. The selected optional engines need no added dependencies:

```bash
./configure --disable-native --disable-http --disable-rdma --disable-rados \
  --disable-rbd --disable-gfapi --disable-pmem --disable-numa --disable-libnfs \
  --disable-xnvme --disable-isal --disable-libblkio --disable-libzbc \
  --disable-tcmalloc --disable-dfs --disable-lex
make -j4 fio
```

For Linux add `--build-static`. The recorded Linux build used existing arm64
image `rust@sha256:e51d0265072d2d9d5d320f6a44dde6b9ef13653b035098febd68cce8fa7c0bc4`
with the same flags; no upstream source edits or package installation were needed.
Exact local commands, logs, compiler configuration, binary identities and bounded
tool-only validation outputs are retained under `~/.cache/fs-six-tools/fio/`.
Do not publish that cache as an evidence bundle. The two owned build/validation
containers were removed after use.

`create_fsync=0` is deliberate: upstream normally syncs a newly created data file.
`fallocate=none`, `create_on_open=1`, `end_fsync=0` and `fsync_on_close=0` avoid
unrequested preparation/sync work. Buffered I/O and `invalidate=0` make no cold
claim. The repeated `0x5a` data are nonzero and highly compressible.

## Run

Resolve the current product source and build matched release artifacts first.
Use [environments.example.json](environments.example.json) as a schema, replacing
placeholders and recording exact owned infrastructure. PostgreSQL databases are
independent, pre-provisioned inputs; the shared runner initializes their LayerFS
schema using public CLI calls.

```bash
python3 fio/src/run.py prepare --environment /private/fio.json \
  --cache /private/fio-prepared --case F01 --machine native --backend sqlite
python3 fio/src/run.py run --environment /private/fio.json \
  --cache /private/fio-prepared --case F01 --machine native --backend sqlite \
  --output /retained/fio/F01/native/sqlite
```

Prepare and execute the next row in case → machine → database order, completing
all eight rows before advancing. Verification is skipped unless `--verify` is
selected before that one-time sample. At shared campaign finish, release the
server/data and other exact owned resources once. Do not tear down common
machines between suites.

```bash
python3 fio/src/run.py finish --environment /private/fio.json --cache /private/fio-prepared
python3 shared/src/report.py --suite fio --input /private/fio-prepared \
  --cleanup /retained/final-cleanup.json \
  --output result/YYYY-MM-DD/fio/FULL_LAYERFS_SHA/report.md
```

Run focused harness checks with an explicit wall bound:

```bash
python3 -c 'import subprocess; subprocess.run(["python3", "-m", "unittest", "discover", "-s", "fio/tests", "-v"], check=True, timeout=30)'
```
