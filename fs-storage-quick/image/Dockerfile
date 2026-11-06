# syntax=docker/dockerfile:1
# fs-storage-quick Sandbox image: the LayerFS runtime image (Debian 12,
# Python 3.11) plus the stdlib Q1–Q5 generator/verifier (gen.py) and the Q6
# edit-model applier (model.py, a copy of fs-storage-history's
# fsh-edit-model-v1). No network or package install. Build context: this
# directory. Every Exec re-checks the script's SHA-256 against the harness copy.
FROM layerfs-352-runtime@sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e
COPY gen.py model.py /opt/fs-storage-quick/
RUN chmod 0555 /opt/fs-storage-quick/gen.py && chmod 0444 /opt/fs-storage-quick/model.py \
 && python3 -c 'import sys; assert sys.version_info >= (3, 9)' \
 && python3 /opt/fs-storage-quick/gen.py plan > /dev/null \
 && cd /tmp && python3 -c 'import sys; sys.path.insert(0, "/opt/fs-storage-quick"); import model; assert len(model.WORDS) == 128' \
 && sha256sum /opt/fs-storage-quick/gen.py /opt/fs-storage-quick/model.py
