# mdtest benchmark

Read the repository AGENTS.md and SPEC.md first. This suite owns M01–M02:
16 registered rows. Execute case → native/Docker/Lima/Apple Container →
SQLite/PostgreSQL. Display Docker first in the report. Use the shared public
LayerFS CLI lifecycle; never use an SDK or revive archived code.

Pin unmodified hpc/ior commit `8e109900e24d45f1cd1184f108458f5fa9b4692c`.
`src/cases.py` freezes the relevant source hashes and exact command. M01 is
files (`-F`), M02 directories (`-D`); both use POSIX, `mpirun -np 1`, 512 entries,
one iteration, `-C -T -r`, no read phase, zero-byte files, depth zero and branching
factor one. Do not add `-y`/`-Y` synchronization, iterations, ranks or warm-up.
The upstream main loop includes a one-second delay; preserve it and report
CLI elapsed separately from upstream phase rates.

Require matched mdtest and MPI runtime on each route. Missing prerequisites are
NOT_RUN; upstream failures/warnings or missing create/stat/remove rates are FAIL.
Keep rates in upstream ops/sec and identify all four statistics; this is not an
MPI scaling study. Default case budget is 15 s, shared across lifecycle calls.

Empty final state after upstream removals is expected; accept UpToDate Commit.
Independent proof is optional/off by default and bounded below 10 s. All cache
states remain honestly declared; unknown is INELIGIBLE, not a speed claim.
Release per-case resources and preserve unknown custody; the overall campaign
owns final machine/server cleanup. Publish only the single required report.
