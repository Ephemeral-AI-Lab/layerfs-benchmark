ARG BASE_IMAGE=layerfs-352-runtime@sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e
FROM ${BASE_IMAGE}
ARG JUICEFS_SHA256
COPY juicefs /usr/local/bin/juicefs
RUN test -n "$JUICEFS_SHA256" \
 && echo "$JUICEFS_SHA256  /usr/local/bin/juicefs" | sha256sum -c - \
 && chmod 0555 /usr/local/bin/juicefs \
 && juicefs version
