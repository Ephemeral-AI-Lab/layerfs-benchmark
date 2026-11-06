# fs-storage-dsh tool image and infrastructure

> Status: Current general guide.

## Seed and build context

`src/seed.py stage --data <deepseek-history-data> --out <new folder>` copies
the pinned seed files (`cases.SEED_FILES`: the bare repository's 9 files,
`mapping.json`, `checkpoint-manifest.json`, `oracles/157.json` from the corpus
oracle of source commit `b0a7d2ce…`), checks each size and SHA-256, adds
`apply.py`, `verify.py` and the Dockerfile, and writes `opt/pins.sha256`. Keep
the folder outside Git (e.g. `~/.cache/fs-storage-dsh/context-v1`). No git
command runs on the host.

## Suite image

[image/Dockerfile](image/Dockerfile) builds FROM the LayerFS runtime image
`layerfs-352-runtime:node24-https-apt-20261024`
(`sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e`;
Debian 12, Python 3.11.2, git 2.39.5). It copies the context to
`/opt/fs-storage-dsh` root-owned and read-only, re-checks `pins.sha256`, adds
`safe.directory` for the seed in the system git config, and proves a non-root
uid can read state 157's tree and count 157 Commits.

```bash
docker build --pull=false --platform linux/arm64 -t fs-storage-dsh:v1-<product-short-sha> <context>
layerfs machine update docker --image <image id>
layerfs machine start docker
```

The image adds about 60 MB to the base. Docker uses it for the worker and the
Sandboxes; the Linux bundle is reused unchanged (Docker does not need a
bundle sealed with this image).

## LayerFS and PostgreSQL

- Matched release CLI, native daemon and Linux bundle of the selected source;
  private `LAYERFS_HOME` and `XDG_CACHE_HOME` (holding the bundle),
  `LAYERFS_CONSTRUCTION_WORKERS=1`, `machine update native --daemon <daemon>`.
- A dedicated `postgres:17-bookworm` container (1 CPU, 512 MiB) published on
  127.0.0.1 only, password from a 0600 file through `POSTGRES_PASSWORD_FILE`,
  one `createdb` per PostgreSQL row. The CLI receives the password only as
  `env:<VAR>`.
- SQLite allocated bytes are read with `find -printf` in the worker volume
  `lfs-<home id[:8]>-docker-data`, mounted read-only into the suite image.

Release the worker, its volume, the PostgreSQL container and volume, and the
suite image at finish.
