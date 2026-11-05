# Benchmark agent instructions

> Status: Current general guide.

These rules apply to every benchmark. Read the selected benchmark's own
`AGENTS.md` for its workloads, setup, execution order, budgets and cleanup.
For `fs-bench-quick`, see [its guide](fs-bench-quick/AGENTS.md).
Preserve unrelated work. Archived benchmarks and their tests are versioned under
`.archive/`; leave their contents unread and frozen unless explicitly assigned.

## LayerFS CLI

Use the public LayerFS CLI for every LayerFS operation. Pin the source commit
and matched CLI/daemon/bundle identities; use the absolute CLI path. Read the
selected source's applicable instructions and check command grammar with
`layerfs help <family> [<call>]` when changing product versions.

| Operation | Command |
| --- | --- |
| Create | `layerfs sandbox create <project> <sandbox> <machine>` |
| Mount | `layerfs workspace mount <sandbox> <branch> --name <name>` |
| Execute | `layerfs workspace exec <ws> <command>` |
| Commit | `layerfs workspace commit <ws>` |
| Unmount | `layerfs workspace unmount <ws>` |
| Destroy/close | `layerfs sandbox close <sandbox>` |

Use a private `LAYERFS_HOME` and `LAYERFS_CONSTRUCTION_WORKERS=1`. Parse the
mount result's `ws` identifier; do not pass its filesystem `path` as the ID.
Invoke the CLI with argument arrays, quote the Exec command correctly, and check
both the CLI exit and workload `exit_code`. JSON is the default output.

No SDK imports, private worker calls, direct Store SQL or manual deletion of
LayerFS runtime state. Provider and database administration may use their owning
infrastructure tools. Record exact owned resources and release them at finish;
preserve uncertain state and other owners' resources. Never automatically retry
or replay a failed/uncertain operation.

## Warm and cold caches

- **Warm setup is allowed:** reuse built binaries, images, dependencies, ready
  machines and closed prepared inputs to keep preparation quick. Each measured
  sample still gets independent writable state.
- **Warm measurement is not cold:** setup reads, earlier phases and writes can
  leave LayerFS caches, OS pages, filesystem metadata or database buffers warm.
  A fresh CLI process, mount, filename or copied database does not prove coldness.
- **A cold claim requires evidence:** declare each phase's cache boundary and
  relevant host, guest, daemon/worker and database caches. Enforce and demonstrate
  the required state outside that phase's timer, using only owned resources.
- **No warm-cache credit:** do not pre-touch measured inputs or credit setup,
  earlier-phase or own-write warmth as measured LayerFS work. Preserve exact
  workloads and explicitly assess cache effects within them.
- **Unknown means INELIGIBLE:** retain timings as labeled diagnostics when the
  required cache state is unknown, mismatched or unenforceable. Do not turn
  execution success or a requested ratio into a qualified performance claim.

Record setup reuse, cache method/evidence and control overhead separately from
operation timings. Never purge a shared host or reset another owner's server to
obtain a cache state.

## Reports

Publish one clear `result/YYYY-MM-DD/<benchmark>/<full-layerfs-sha>/report.md`.
Start it with a bold outcome sentence, then run `python3 shared/src/readme_index.py`
to update the root index and the benchmark's past runs. A new benchmark's README
starts `# <folder> — <what it checks>` and `> group: … · measures: …`.
Include the outcome, configuration, results, main observations, limits and cleanup.
Group tables by cell, put the baseline first, and name each metric and its units.
Keep logs, receipts, manifests, CSV/JSON exports and source copies local and
ignored. Do not publish evidence bundles or duplicate summaries.
