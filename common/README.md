# Shared SDK-route harness

> **Status:** Current general guide.

The suites of [#365](https://github.com/Ephemeral-AI-Lab/layerfs/issues/365)
(pjdfstest, fsx, fsstress, smallfile, mdtest, fio) share these files. Each
suite drives LayerFS only through the public JS SDK: `project.init`,
`sandbox.create`, the run's own Branch from `branch.fork`, `sandbox.mount`,
`sandbox.exec`, `sandbox.commit`, `sandbox.unmount` and `sandbox.close`.
Every tool invocation is a `sandbox.exec` in the suite's Sandbox image.

| File | What it does |
| --- | --- |
| `client.sh RUN SUITE SCRIPT [ARG...]` | Runs `benchmark/SUITE/client/SCRIPT` in the SDK runtime image with the run's deployment (`RUN/deploy.env`) |
| `session.mjs` | SDK client (Store policy 16/8/8), ledger helpers, `timed`, `exec` (never throws on a non-zero exit), `setup` (Init, create, fork, mount; path kept in `session.json` for later clients), `commit`, `teardown` |
| `lib.sh` | Shell steps for a suite's `run.sh`: `bench_client` (115 s alarm, `commands.log` with 1-minute load), `bench_next`, `bench_image`, `bench_setup`, `bench_lock` / `bench_unlock`, `bench_cleanup` |

A suite's `run.sh` sets `suite=<folder name>` and sources `lib.sh`. Its
clients import `../../common/session.mjs`. The mounted Workspace survives
between client processes; each client reads its path from `session.json`.

Two arms run in the same Sandbox through `sandbox.exec`: `layerfs`, in the
mounted Workspace, and `sandbox-disk`, in the container's own `/tmp`
(overlayfs), as the reference. `sandbox.exec` runs `bash -c` as uid 501 with
`HOME=/tmp`, no stdin, and keeps at most 1 MiB per stream.

Measured runs hold the host measurement lock
(`benchmark-results/.measure.lock`) from setup to teardown, so only one suite
measures at a time. `bench_lock` exits 75 while another run holds it.
Builds and smoke runs take no lock.

Images: each suite builds its own Sandbox image `FROM fs-bench-computer:gawk-20261020`
(checked against `sha256:66aeb6bb…`, Debian bookworm with gcc, make, git,
perl, prove and python3), with tools from pinned upstream commits, and
records the resulting digest.
