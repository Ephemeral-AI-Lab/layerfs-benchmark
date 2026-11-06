# Prompts

## The prompts that produced this comparison (2026-11-06, verbatim)

1. > analyze https://github.com/stencil-hq/ovnfs and compare it to layerfs.
   >
   > ovnfs claim its copy on write, but is it similar to btrfs experiment

2. > can you do a small set of benchmark of layerfs v_2_0_0 vs ovnfs in
   > https://github.com/Ephemeral-AI-Lab/layerfs-benchmark/tree/main/fs-storage-history
   >
   > in both speed, and storage efficiency, and for layerfs_use docker

3. > create a folder comparision/ovnfs/ to record the experiments, prompt to produce, results.
   >
   > and create a graph/diagram of comparision

## Reproduction prompt (for an agent)

Use this to rerun the comparison, for example on a newer LayerFS or ovnfs commit.

```text
Rerun the LayerFS vs ovnfs comparison in layerfs-benchmark/comparision/ovnfs/.
Read its README.md first; keep the workload, case shapes and operation mapping.

Rules: follow layerfs/AGENTS.md and layerfs-benchmark/AGENTS.md. Disposable
SQLite profile only, LAYERFS_CONSTRUCTION_WORKERS=1, public LayerFS CLI only, one
attempt per call (no retries), every command bounded below 2 minutes, one sample
per case and arm, fresh output directories, and no reruns because of host load
(record the 1-minute load). Timings are warm diagnostics; do not claim cold.
Release every resource you create.

1. Pin LayerFS: the layerfs_v2_0_0 commit, a release macOS CLI and a sealed
   linux-aarch64 bundle built from that commit (copy a sealed one if it exists;
   check bundle.json file hashes). Make a private campaign directory with
   artifacts/layerfs, home/ (chmod 700), xdg/layerfs/bundle/2.0.0/linux-aarch64,
   empty/ and results/. Copy harness/compare.py and harness/summarize.py there.
2. Build the LayerFS Sandbox image from fs-storage-history/image/Dockerfile under
   your own tag, then `layerfs machine update docker --image <id>` and
   `layerfs machine start docker` with LAYERFS_HOME/XDG_CACHE_HOME set to the
   campaign. Put the worker volume name (lfs-<home id[:8]>-docker-data) and both
   image tags into compare.py's constants.
3. Pin ovnfs: clone stencil-hq/ovnfs at the chosen commit and build the image
   with harness/ovnfs.Dockerfile (build context: repo/ + model.py + Dockerfile).
4. Check Docker guest free space (>= 20 GiB) and host disk. Then, for each case
   S4, S1, S2, S3 and each arm (alternate which arm goes first), run one unit per
   command:
     python3 compare.py <layerfs|ovnfs> <case> open
     python3 compare.py <layerfs|ovnfs> <case> branch <name>   # every branch, in order
     python3 compare.py <layerfs|ovnfs> <case> close
   Never run diagnostics inside a case's ovnfs container before it closes; if you
   do, keep that attempt (rename it *.attemptN-<reason>) and rerun the case fresh.
5. python3 summarize.py > summary.json; copy summary.json, each results/*/state.json
   and events.jsonl into comparision/ovnfs/results/, then run
   harness/make_figures.py and update README.md tables, outcome and limits.
6. Clean up: stop the docker machine, docker rm its worker container, docker
   volume rm its data volume; confirm no fsh-cmp containers or volumes remain.
   Report what was kept.
```
