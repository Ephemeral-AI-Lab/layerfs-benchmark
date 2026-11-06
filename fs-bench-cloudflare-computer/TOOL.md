# fs-bench-cloudflare-computer tool image

> Status: Current general guide.

How the Sandbox image for the Linux machines is built. The frozen workload is
in [AGENTS.md](AGENTS.md).

## Base userland

The script needs bash 4+, GNU `date` with `%N`, coreutils, gawk and git. The
base is the LayerFS runtime image `layerfs-352-runtime:node24-https-apt-20261024`,
`sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e`
(Debian 12, bash 5.2.15, git 2.39.5), the registered Sandbox image of the
worktree launcher. Its default awk is mawk, whose `%d` saturates at 2³¹−1, so
the suite image adds Debian's `gawk` 1:5.2.1-2 (network needed for `apt-get`).

## Suite image

[image/Dockerfile](image/Dockerfile) installs gawk, adds the frozen script at
`/opt/fs-bench-cloudflare-computer/fs-bench.sh` and checks its SHA-256, bash 4+,
nanosecond `date` and gawk:

```bash
docker build --pull=false --platform linux/arm64 \
  -t fs-bench-layerfs-tools:<product-short-sha> fs-bench-cloudflare-computer/image
```

Set `BENCH_TOOL_ROOT=/opt/fs-bench-cloudflare-computer` for every Linux machine.

## LayerFS machines

Seal the selected product's Linux bundle with this image as its Sandbox image,
so Lima and Apple Container boot the same userland as Docker:

```bash
python3 tools/linux_bundle.py seal --resources R --profile release \
  --image <suite image id> --dest <XDG_CACHE_HOME>/layerfs/bundle
layerfs machine update docker --image <suite image id>
layerfs machine create <name> lima --cpus 2 --memory 2G --disk 8G \
  --image <bundle>/sandbox-image.tar
layerfs machine create <name> apple-container --cpus 2 --memory 2G --disk 8G \
  --image <bundle>/sandbox-image.tar
```

## Native macOS

macOS ships bash 3.2.57 and a BSD `sha256sum` without `--quiet`. Native rows
use a tool folder outside any Store, set as `BENCH_TOOL_ROOT`, holding:

| File | Identity |
| --- | --- |
| `fs-bench.sh` | the frozen script, SHA-256 `0e2004339a92…37230ef` |
| `bin/bash` | GNU bash 5.2.37 from `bash-5.2.37.tar.gz` (SHA-256 `9599b22ecd1d…a621ff`), `./configure --without-bash-malloc --disable-nls`, built with Apple clang on macOS 26.4.1 arm64; binary SHA-256 `fbea3631ff82…50f94fc`; links only macOS system libraries |
| `bin/sha256sum` | 9-line wrapper: exactly `-c --quiet` runs `/sbin/sha256sum -c -` and prints only on failure; anything else goes to `/sbin/sha256sum`; SHA-256 `838a14f6ab33…46a2cc` |

Set the native machine's `tool_environment` to
`BENCH_TOOL_ROOT=<folder>` and `PATH=<folder>/bin:/usr/bin:/bin:/usr/sbin:/sbin`.
The body then runs the script with the pinned bash and checks its hash with the
wrapper; git is macOS's `/usr/bin/git` (2.39.5, Apple Git-154).

The 2026-11-06 build is cached in `~/.cache/fs-bench-cloudflare-computer/tools/`
with its source tarball; it is not published here.
