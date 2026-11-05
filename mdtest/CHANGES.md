# mdtest profile changes

## v2: explicit single-slot launcher

Prospective profile: `one-rank-512-create-stat-remove-v2`.
Product source remains `b919f50eaf9cce79671f8501a580279d23cc5f3c`; upstream IOR,
compiled tools, 512 entries, one MPI rank, empty files, one iteration and
create/stat/remove phases remain unchanged.

The retained v1 `M01/lima/sqlite` attempt returned workload exit 1 before any
mdtest output or LayerFS Commit. Its stderr reports missing sysfs CPU topology,
then OpenMPI reports all allocated nodes filled. Cleanup completed. The pinned
namespace Sandbox builds private `/proc`, `/dev` and `/tmp`, and exposes no `/sys`
CPU topology. Automatic hwloc discovery consequently cannot provide the launcher
with the CPU hierarchy it expects. This is launcher configuration, not a retained
mdtest filesystem assertion failure.

The v1 matrix retains four execution PASS rows, one FAIL and eleven NOT_RUN;
its receipts and verdicts are immutable. No old receipt is promoted or pooled
with v2. The primary registers a separate complete 16-row v2 campaign before
product execution, in the usual case/machine/database order.

V2 applies identically to both cases on all four machines:

- `HWLOC_COMPONENTS=no_os,stop` selects the generic OS processor-count backend
  and stops further topology components.
- `--host localhost:1` declares one local scheduling slot.
- `--map-by slot --bind-to none -np 1` selects one unbound local MPI rank.

The generic backend uses OS processor-count fallback; this is not synthetic
hardware information. Binding, rank count or workload size is never adjusted
per platform. Preserve the original failure; use no retry of an unchanged arm.

Primary references: [hwloc 2.9.0 generic backend](https://github.com/open-mpi/hwloc/blob/hwloc-2.9.0/hwloc/topology-noos.c),
[component selection](https://github.com/open-mpi/hwloc/blob/hwloc-2.9.0/doc/hwloc.doxy),
and [OpenMPI launcher options](https://docs.open-mpi.org/en/v5.0.11/man-openmpi/man1/mpirun.1.html).
