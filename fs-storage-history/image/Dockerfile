# syntax=docker/dockerfile:1
# The LayerFS Sandbox image for fs-storage-history: the LayerFS runtime image
# (Debian 12, Python 3.11) plus the suite's edit-model applier and manifest
# tool. No network or packages are needed. Build context: fs-storage-history/.
FROM layerfs-352-runtime@sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e
COPY src/model.py /opt/fs-storage-history/model.py
RUN chmod 0444 /opt/fs-storage-history/model.py \
 && cd /tmp \
 && python3 -c 'import sys; sys.path.insert(0, "/opt/fs-storage-history"); import model; assert sys.version_info >= (3, 9) and len(model.WORDS) == 128' \
 && sha256sum /opt/fs-storage-history/model.py
