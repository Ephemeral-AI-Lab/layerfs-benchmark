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

macOS ships bash 3.2.57. A native row needs a pinned bash 4+ built from source
and supplied on the Exec path, recorded here with its hash. None is provided
yet, so native rows are NOT_RUN.
