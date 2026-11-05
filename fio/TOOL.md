# fio tool build

> Status: Current general guide.

How the pinned fio binaries for the [fio benchmark](README.md) were built and
checked. The frozen workload is in [AGENTS.md](AGENTS.md).

## Source

Use unchanged upstream [fio 3.40](https://github.com/axboe/fio/tree/ff930c4653ae3952d6b09ab3ec89671aeabf2cbe),
commit `ff930c4653ae3952d6b09ab3ec89671aeabf2cbe`, annotated tag object
`3e0048fdd9e9832e0052de78ebdd39ab7393f911`. Native macOS arm64 and Linux aarch64
builds were checked outside LayerFS using all four exact command bodies and
read-setup jobs. Their successful tool checks do not establish product results.

## Binaries

| Build | Cached executable | SHA-256 |
| --- | --- | --- |
| macOS arm64 | `~/.cache/fs-six-tools/fio/native/bin/fio` | `78bffe4c98240a5e3d9fcde34d9662b4bbed03867d5ab5ed3648e8faefdc154c` |
| Linux aarch64, static | `~/.cache/fs-six-tools/fio/linux/bin/fio` | `7a4ba395670e0795b32dd102916ec2cb71b32a3f9d91d76bed0734c22e0d8bbd` |

The native executable uses only macOS system `libSystem` and `libz`; no Homebrew
runtime library is required. Linux's executable is static and needs no copied
shared libraries.

## Build

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
