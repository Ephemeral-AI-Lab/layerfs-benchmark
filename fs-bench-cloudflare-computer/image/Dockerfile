# syntax=docker/dockerfile:1
# The LayerFS Sandbox image for this suite: the LayerFS runtime image
# (Debian 12, bash 5.2, GNU coreutils, git 2.39) plus GNU awk and the frozen
# fs-bench.sh. gawk keeps the script's printf "%d" from saturating at 2^31-1
# as Debian's default mawk does. Build context: this directory.
FROM layerfs-352-runtime@sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e
RUN apt-get -o Acquire::Retries=0 update \
 && apt-get install -y --no-install-recommends gawk \
 && rm -rf /var/lib/apt/lists/*
COPY fs-bench.sh LICENSE.cloudflare-computer /opt/fs-bench-cloudflare-computer/
RUN chmod 0555 /opt/fs-bench-cloudflare-computer/fs-bench.sh \
 && echo "0e2004339a9269b88c2de451d56575957477bde16b96a10cf1837519e37230ef  /opt/fs-bench-cloudflare-computer/fs-bench.sh" | sha256sum -c --quiet \
 && bash -c '(( BASH_VERSINFO[0] >= 4 ))' \
 && test "$(date +%s%N | wc -c)" -ge 19 \
 && test "$(readlink -f "$(command -v awk)")" = /usr/bin/gawk \
 && test "$(awk 'BEGIN { printf "%d", 3000000000 }')" = 3000000000
