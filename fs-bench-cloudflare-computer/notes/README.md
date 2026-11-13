# fs-bench-cloudflare-computer — local measurement notes

> Status: appendix notes, not a run report and not part of the published campaign record.

These three notes are the local measurements that
[layerfs-project#73](https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/73)
and PRs [#604](https://github.com/Ephemeral-AI-Lab/layerfs/pull/604),
[#605](https://github.com/Ephemeral-AI-Lab/layerfs/pull/605),
[#606](https://github.com/Ephemeral-AI-Lab/layerfs/pull/606),
[#607](https://github.com/Ephemeral-AI-Lab/layerfs/pull/607) cite. They are
kept here so a reader can check the numbers behind those claims instead of
trusting a summary. They are written in Chinese, on one MacBook Air M2
(macOS 27.2), and none of them is a qualified cold-cache performance claim.

They are **not** `result/<date>/<benchmark>/<sha>/report.md` on purpose: the
published run report for the twelve-scenario suite is
[`../result/2026-11-07/…/85a0865cd…/report.md`](../../../result/2026-11-07/fs-bench-cloudflare-computer/85a0865cde92f1d85a4e8bf402c597c935ff8db6/report.md),
and these notes do not repeat it. `shared/src/readme_index.py` only indexes
`report.md` files, so nothing here enters the generated index blocks.

| Note | What it records | LayerFS commit |
| --- | --- | --- |
| [74-ATTRIBUTION-RESULTS.md](74-ATTRIBUTION-RESULTS.md) | Attribution of the twelve scenarios: host APFS vs native NFS, per-scenario NFSv3 procedure counts, daemon CPU by procedure, the 64 MiB cold read path, the AppleDouble `._*` sidecar evidence and the server-side sidecar strategies (memory companion, `NFS3ERR_ACCES`, real inode) | `b1802332b` |
| [LP75-78-BENCH-RESULTS.md](LP75-78-BENCH-RESULTS.md) | FAST-A/FAST-B before-and-after the four combined branches, the 1 MiB transfer window regression and its 128 KiB diagnosis, and §12 on the final combined commit | `b1802332b` → `1c49afc78` → `85a0865cd` |
| [LP77-DEEP-RESULTS.md](LP77-DEEP-RESULTS.md) | Root causes behind that regression: the `._*` companion `wcc_data` invalidating the macOS NFSv3 attribute cache, and `nm_biosize` costing on `max(rsize, wsize)`; the measurements behind the 256 KiB window and the 4 MiB pager | `1c49afc78` |

What was changed when publishing them: only sanitising. Local worktree and
cache prefixes were rewritten to `~/LayerFS/…`, a hostname was replaced by the
machine model, and one decision line names the maintainer instead of a person.
The measurements, tables, code paths and conclusions are untouched, including
the sections that record what was **not** run.

What these notes replace: nothing. The pre- and post-optimization numbers of
the whole eight-row campaign belong in its run report, which is where a reader
should look for publishable figures; these notes are the earlier, single-machine
diagnostics that explain them.
