# fs-bench-pro agent instructions

> Status: Current general guide.

These instructions apply to `fs-bench-pro/` and extend the repository-root
[CLI and cache rules](../AGENTS.md). This file is the suite's current contract;
[cases.py](src/cases.py) pins the cases and expected trees. Reading it does not
start a campaign or authorize repeating completed samples.

This is a new suite, created on 2026-11-08 at the owner's instruction. The
earlier fs-bench-pro in `.archive/` stays frozen: do not edit, build or run it.

## Families and cases

Each family is a case group in [cases.py](src/cases.py) with its own workload
version. Only `export` exists:

| Case | Work | Fixture |
| --- | --- | --- |
| E01 | `project export` of 10,000 small files, 50 symlinks, 132 folders (46,486,561 bytes) | `small` |
| E02 | `project export` of one 256 MiB file and a README (268,435,480 bytes) | `large` |

A case exports branch `main` of one project from a SQLite Store on the selected
machine (native, Docker, Lima, Apple Container) into a fresh folder on the
macOS host. Workload version `export-v1` pins the fixtures' generator and
manifests. Changing a fixture, the command or the verifier needs a new
workload version. Add a family by adding its cases, fixtures and verifier
here, not a second runner.

## Select the product

- Record the full source commit, branch and whether it is pushed; build the
  CLI and the Linux bundle from that one snapshot and record their hashes.
- Use the absolute CLI path from the config file, never `layerfs` on `PATH`.
- Use a private `LAYERFS_HOME` and `XDG_CACHE_HOME`, and
  `LAYERFS_CONSTRUCTION_WORKERS=1`. Store profile: Disposable only.

## Prepare (untimed, through the CLI)

```text
layerfs store create <store>
layerfs project init <store>/small <fixtures>/small
layerfs project init <store>/large <fixtures>/large
layerfs store push <store> <machine>          # guests only
```

`run.py setup` does this for every machine. Init runs on native from the same
fixture bytes; a guest Store is then moved, not rebuilt. Prepared Stores are
reused across samples because export only reads them; the exported folder is
the sample's output and is removed after verification.

## Cold control

A cold claim needs enforcement and evidence on owned resources only. Never
purge the host's or Docker Desktop's shared cache.

- Guests: `tools/resident.c`, built static and copied to `/tmp/resident` in the
  guest, runs `--evict` (fdatasync + `posix_fadvise(DONTNEED)`) on the Store's
  own files, then counts their resident pages with mincore.
- Native: the home sits on an owned APFS disk image; detach and re-attach it,
  then count the Store's resident pages with mincore.
- Any resident page or a failed control: INELIGIBLE. The control's cost is
  overhead, recorded apart from case time.

Limit to state in every report: the guest control empties the guest's page
cache only. The host may still cache the VM's disk file, which belongs to the
shared VM and is not purged, so a guest's cold state is weaker than native's.

## Run one sample per command

```text
python3 src/run.py run --env environments.local.json --case <E01|E02> --machine <machine>
```

- One sample per case per machine; no warm-up, rerun or best-of. A failure
  keeps its receipt and is reported.
- Order: E01 then E02; within a case native, Docker, Lima, Apple Container.
- Record the 1-minute load (the runner does) and any build or test another
  session runs at the same time.
- The timed export has a 15 s budget, verification 10 s, and every command a
  wall limit of at most 120 s.
- A labeled diagnostic (for example a warm export to separate cold read cost)
  may follow, outside the receipts, and is reported as a diagnostic.

## Verdicts

QUALIFIED needs execution PASS (exit 0 and counts equal to the fixture),
verification PASS (manifest equal to the pinned hash), a shown cold Store and
the export within budget. Otherwise OVER_BUDGET, INELIGIBLE or FAIL.
Receipts record the harness version; a harness change never relabels an
earlier receipt.

## Report

Publish `result/<date>/fs-bench-pro/<full-layerfs-sha>/report.md` per the root
rules: bold outcome sentence, configuration and identities, one table per case
(native first) from `src/report.py`, observations, limits, failures and
cleanup. Then run `python3 shared/src/readme_index.py`. Receipts stay local.

## Cleanup

`run.py cleanup` removes the family's Stores. Remove machines with the CLI,
detach the disk image and delete fixtures and outputs you created; report
anything kept.
