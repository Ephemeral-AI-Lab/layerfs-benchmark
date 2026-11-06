# syntax=docker/dockerfile:1
FROM golang:1.27-bookworm AS build
WORKDIR /src
COPY repo/ .
RUN CGO_ENABLED=0 go build -trimpath -o /out/ovnfs . && /out/ovnfs version
FROM layerfs-352-runtime@sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e
RUN apt-get update && apt-get install -y --no-install-recommends fuse3 && rm -rf /var/lib/apt/lists/*
COPY --from=build /out/ovnfs /usr/local/bin/ovnfs
COPY model.py /opt/fs-storage-history/model.py
RUN chmod 0444 /opt/fs-storage-history/model.py && sha256sum /opt/fs-storage-history/model.py /usr/local/bin/ovnfs
