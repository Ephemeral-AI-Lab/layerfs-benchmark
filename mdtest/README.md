# mdtest

Two small metadata diagnostics using the unmodified MPI mdtest tool from IOR.
M01 creates/stats/removes 512 empty files; M02 does the same for directories.
Each runs one MPI rank and one iteration, with separate upstream phase rates.

Tool source: [hpc/ior](https://github.com/hpc/ior/tree/8e109900e24d45f1cd1184f108458f5fa9b4692c).
Build with `autoreconf -ivf`, `./configure --without-mpiio CC=mpicc`, and `make`.
Provide `BENCH_TOOL_ROOT/bin/mdtest` and `BENCH_TOOL_ROOT/bin/mpirun`, retaining
the linked MPI runtime. Native qualification used OpenMPI 5.0.11; the guest
build uses Debian 12's pinned package receipt. Record actual versions and binary
hashes with each campaign. The root-capability OpenMPI environment switches are
set identically on each route; they do not grant filesystem privileges.

Use `python3 mdtest/src/run.py --help` for the shared lifecycle commands and
`environments.example.json` as a configuration outline. A complete configuration
also needs the campaign's product artifacts, private home and database ownership.
Build/install tools once outside measured calls. Optional `--verify` checks the
committed empty result; upstream phases always run.

The 15 s budget includes Create, Mount, Exec, Commit, Unmount and Cleanup.
Upstream includes an intrinsic one-second delay and MPI launch overhead. Its
phase rates cannot be substituted for full CLI wall. Reused setup and unknown
cache state produce explicitly ineligible timing diagnostics. Full scope and
cleanup requirements are in [AGENTS.md](AGENTS.md) and the root specification.

The current v2 MPI launcher uses `--host localhost:1 --map-by slot --bind-to none`
and `HWLOC_COMPONENTS=no_os,stop` identically on every machine. These select a
single local scheduling slot and hwloc's generic processor-count fallback without
binding. They avoid requiring a sysfs CPU hierarchy that namespace Sandboxes do
not expose; no synthetic topology, extra rank or product modification is used.
The suite reports no CPU-topology or binding qualification. Earlier v1 observations
remain separate; see [CHANGES.md](CHANGES.md).
