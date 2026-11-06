# fs-storage-history tool image

> Status: Current general guide.

The Sandbox image adds only the suite's edit-model applier to the LayerFS
runtime image `layerfs-352-runtime:node24-https-apt-20261024`
(`sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e`,
Debian 12, Python 3.11.2). No packages or network are needed.

```bash
docker build --pull=false --platform linux/arm64 -f fs-storage-history/image/Dockerfile \
  -t fs-storage-history:<product-short-sha> fs-storage-history
layerfs machine update docker --image <image id>
layerfs machine start docker
```

[image/Dockerfile](image/Dockerfile) copies [src/model.py](src/model.py) to
`/opt/fs-storage-history/model.py` (0444) and prints its SHA-256; record it
as `artifacts.model_sha256`, which `run.py` checks against the working tree
before a row. The 2026-11-06 build: image `sha256:0627c7f8…a7d1` (config
`sha256:7f458c11…93db`), model `f44c6b23…a307de`.

Docker needs the selected product's sealed Linux bundle in
`<XDG_CACHE_HOME>/layerfs/bundle/2.0.0/linux-aarch64/` for its worker; the
bundle's own Sandbox archive is not used once the machine records an image.
A private `LAYERFS_HOME` gets its own worker `lfs-<home id[:8]>-docker` and
data volume; release both after the campaign (`machine stop docker`,
`docker rm`, `docker volume rm`).

PostgreSQL rows use a dedicated server container (here `fsh-pg`,
`postgres:17-bookworm`, 1 CPU, 512 MiB, published on `127.0.0.1`) with one
empty database per Store, created with `createdb` before the row. The Docker
Sandbox reaches it through the same `127.0.0.1` URL. Give the password only
through an environment variable named in the config.
