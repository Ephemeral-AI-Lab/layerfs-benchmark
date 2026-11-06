# syntax=docker/dockerfile:1
# The LayerFS Sandbox image for fs-storage-dsh: the LayerFS runtime image
# (Debian 12, Python 3.11, git 2.39.5) plus the pinned 157-state seed
# repository, the state-157 oracle and apply.py / verify.py under
# /opt/fs-storage-dsh, all root-owned and read-only to the Sandbox identity.
# Build context: the folder `src/seed.py stage` writes (never this folder).
FROM layerfs-352-runtime@sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e
COPY --chown=0:0 opt /opt/fs-storage-dsh
RUN cd /opt/fs-storage-dsh \
 && sha256sum -c --quiet pins.sha256 \
 && chmod -R a+rX,go-w /opt/fs-storage-dsh \
 && chmod 0555 apply.py verify.py \
 && git config --system --add safe.directory /opt/fs-storage-dsh/seed/snapshots.git \
 && setpriv --reuid=501 --regid=501 --clear-groups \
      git --git-dir=/opt/fs-storage-dsh/seed/snapshots.git cat-file -e 0175125b5dc4dd08965eb576b7c8aee28a73e0c3 \
 && setpriv --reuid=501 --regid=501 --clear-groups \
      git --git-dir=/opt/fs-storage-dsh/seed/snapshots.git rev-list --count main | grep -qx 157
