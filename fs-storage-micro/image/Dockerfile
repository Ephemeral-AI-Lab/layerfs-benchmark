# syntax=docker/dockerfile:1
# fs-storage-micro Sandbox image: the LayerFS runtime image (Debian 12,
# Python 3.11 with sqlite3 3.40.1, git) plus the stdlib generator/verifier.
# No network or package install. Build context: this directory. Every Exec
# re-checks gen.py's SHA-256 against the harness copy before running it.
FROM layerfs-352-runtime@sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e
COPY gen.py /opt/fs-storage-micro/gen.py
RUN chmod 0555 /opt/fs-storage-micro/gen.py \
 && python3 -c 'import sqlite3, sys; assert sys.version_info >= (3, 9) and sqlite3.sqlite_version == "3.40.1"' \
 && python3 /opt/fs-storage-micro/gen.py plan > /dev/null
