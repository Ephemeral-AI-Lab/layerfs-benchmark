# store-transfer — a SQLite Store between a home and a machine

> Status: verification outcomes; timings are diagnostic and performance-ineligible.

**Outcome: PASS on every Store-transfer route, refusal, recovery path and the
guide at layerfs `ab4c1a4712` (Ephemeral-AI-Lab/layerfs#617, merged into
`layerfs_v2_0_0` as `716197c499` with the same tree), and every Apple Container
pull now succeeds on its first attempt.**

This re-runs the [first report](../d8dddd50d04c92e4656131e71273fbe0bac0daae/report.md)
on the code that landed. Three things changed in the product since then:

- Apple Container's cut answers are fixed by the worker waiting for the client
  to close first (`97fac452bd`), not by the worker closing its write half;
- `send` reads each piece once: the 3× read retry is gone, so a lost answer is
  `Unknown` at `send` like any other;
- Firecracker is removed, as Microsandbox and SSH were by layerfs#616: `machine create`
  refuses all three with ``platform `<name>` was removed in LayerFS 2.0``, and
  `machine connect` no longer exists.

## Configuration

| Item | Identity |
| --- | --- |
| LayerFS | `ab4c1a4712ec0e4d032a2ac341638053a02e2c91`, tree `0e15263bec`, merged as `716197c499` (same tree) |
| CLI | release, macOS arm64, `CARGO_PROFILE_RELEASE_STRIP=none`, sha256 `044960d5b366e022…` |
| Daemon | release, sha256 `a25891a8ae16cb1a…` |
| Node addon | `layerfs-node` release, sha256 `0a736c2b833533f5…` |
| Linux bundle | release, `linux-aarch64`, hash `723629fa0dbfa43c…`, `source.head ab4c1a4712`; guest `layerfs` sha256 `af9e26ee2ef115d5…`; Sandbox image `afa1ef9c2729` (2.7 GB). Installed in a private folder through `LAYERFS_BUNDLE`, not the shared cache |
| Host | macOS 26.4.1, Apple silicon, 36 GiB; Docker Desktop 29.5.2 (8 CPUs, 7.75 GiB); `limactl` 2.2.1; `container` 1.6.1 |
| Guests | `docker` = Docker Desktop's engine (not colima); Lima and Apple Container 2 CPU / 2 GiB / 8 GiB disk |
| Suite | this folder at `e79289d` plus the changes in this report's PR (two commits; see "Suite fixes and re-run") |
| Stores | #9/#12 fixture 21.4 MB; #11 `cap256` 271.7 MB, `cap512` 543.1 MB, `quiet-s` 17.2 MB; #13 64 MiB fixture |
| Duration | 2026-11-08 09:03–09:36 CST; every driver step was its own command, at most 290 s |

Changes to the suite, all in the commit that adds this report:

- `matrix.py`, `lp08s2.py`, `crash.py`: the docker socket comes from
  `LP08_DOCKER_SOCK` (default unchanged, colima's).
- `matrix.py` refusals: the removal text replaces the #7 text; SSH is checked
  with `machine create … ssh` (`REF-SSH-CREATE`); the teardown is
  `machine remove` for both records.
- `lp08s2.py`: `LP08_DISK` sets the Lima/Apple Container disk; the pull
  ladder expects every size to pull on its first attempt (it used to expect
  failures above 32 MiB).
- `GUIDE-zh.md` and `guide_repro.py`: removed platforms are not listed by
  `machine platforms`; the docker socket can be Docker Desktop's
  (`DOCKER_SOCK`); step 3 checks `docker info` instead of running
  `colima start`; block 0 keeps a preset `LAYERFS_HOME` and `FIXTURE`.

## Results

### #9 — routes, the two-hop and refusals

Checks passed / total. `matrix.py`.

| Case | docker | lima | apple-container |
| --- | ---: | ---: | ---: |
| `R9-*-RT` round trip, nothing changed | 43 / 43 | 43 / 43 | 43 / 43 |
| `R9-*-MOD` edit on the target, pull back | 53 / 53 | 53 / 53 | 53 / 53 |
| `R9-X-RETIRE-DIR-*` | 5 / 5 | 5 / 5 | 5 / 5 |
| `R12-PROGRESS` | 64 / 64 | 64 / 64 | 64 / 64 |
| `R9-A-BLOCKER` size sweep, 3–21.7 MiB | — | — | 10 / 10, every pull first attempt |
| `R9-H-HOP` docker → native → lima | 76 / 76 | | |
| `R12-RAW` | 2 / 2 | | |

The docker route ran twice: once as its own row, once to stage `mod-d` for
the hop (the README's order). Both passed.

Refusals: 13 of 16 PASS — `REF-BADNAME`, `REF-BUSY`, `REF-EXISTS`,
`REF-FC-CREATE`, `REF-SSH-CREATE`, `REF-INUSE-SANDBOX`, `REF-LEASE`,
`REF-NOMACHINE`, `REF-NOSTORE`, `REF-PULL-NATIVE`, `REF-PUSH-NATIVE`,
`REF-STOPPED`, `REF-WRONGDIR-PUSH`. The other three:

| Case | Checks | The check that did not pass |
| --- | ---: | --- |
| `REF-FC-RECORD` | 29 / 30 | `machine status fc1` is `Unsupported` with the removal text. The suite expects it answered, as for a *disabled* platform; for a *removed* platform only `machine list` and `machine get` answer (layerfs#616's contract, now Firecracker's too). Every new-work refusal, every kept read and the forgetting `machine remove` passed |
| `REF-SSH-RECORD` | 29 / 30 | the same, for `machine status h1` |
| `REF-PG` | 8 / 9 | `store connect` needs the `lp08-pg` server's password; there is no such server here, so the call failed `Unavailable` before reaching the engine check: NOT_RUN. Both `store push`/`store pull` "does not move" refusals passed |

### #11 — 256 MiB and 512 MiB, capacity and mid-`send` ENOSPC

`lp08s2.py` and `docker-cap.py`. Seconds are the CLI call's wall time (warm
host cache, diagnostic); MB/s is bytes ÷ seconds; caller RSS is the CLI's
`maxrss`; worker peak is the guest worker's `VmHWM` after the call (5.1–5.9
MB before).

| Platform | Transfer | Bytes | Seconds | MiB/s | Caller RSS (MB) | Worker peak (MB) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| docker | 256 push | 271,679,488 | 2.512 | 103.1 | 49.1 | 31.4 |
| docker | 256 pull | 271,679,488 | 2.374 | 109.1 | 29.0 | 32.5 |
| docker | 512 push | 543,162,368 | 5.063 | 102.3 | 39.3 | 29.5 |
| docker | 512 pull | 543,162,368 | 4.441 | 116.6 | 22.5 | 32.5 |
| lima | 256 push | 271,683,584 | 1.278 | 202.7 | 49.1 | 56.7 |
| lima | 256 pull | 271,683,584 | 1.303 | 198.9 | 29.0 | 32.3 |
| lima | 512 push | 543,084,544 | 2.598 | 199.4 | 39.3 | 54.5 |
| lima | 512 pull | 543,084,544 | 2.442 | 212.1 | 22.5 | 32.3 |
| apple-container | 256 push | 271,675,392 | 0.958 | 270.5 | 49.1 | 30.5 |
| apple-container | 256 pull | 271,675,392 | 0.930 | 278.6 | 29.0 | 33.2 |
| apple-container | 512 push | 543,145,984 | 1.881 | 275.4 | 39.2 | 30.4 |
| apple-container | 512 pull | 543,145,984 | 1.718 | 301.5 | 22.5 | 33.1 |

All `R11-*-256-push` (13/13), `-256-pull` (14/14), `-512` (21/21),
`-TARGET-EDIT` (5/5), `-BOOT` (2/2) and `R12-*-QUIET` (6/6) rows pass on all
three platforms.

| Injection | docker | lima | apple-container |
| --- | ---: | ---: | ---: |
| `R11-CAP-PRE` (refused `Capacity` at `check`, nothing sent) | 8 / 8 (`docker-cap.py`) | 6 / 6 | 6 / 6 |
| `R11-ENOSPC-MID` (disk full during `send`, same command recovers) | 11 / 11 (`docker-cap.py`) | 8 / 8 | 8 / 8 |
| `R11-ENOSPC-MID-SYNC` (`nodelalloc`) | — | 9 / 9 | NOT_RUN: `remount,nodelalloc` refused |

Apple Container pulls, each the first attempt of its row:

| Run | Sizes | Pulls | First-attempt successes |
| --- | --- | ---: | ---: |
| `R11-A-PULL-SWEEP` | 8.7, 17.2, 34.1, 68.1, 136.0 MB | 5 | 5 |
| `R11-A-PULL-ROUNDS` | 256 and 512 MiB Stores, 3 rounds each | 6 | 6 (bytes = snapshot every time) |

The first report's build needed up to 25 attempts for a 256 MiB pull and
expected failures above 32 MiB.

Lima's first route ran on the driver's 4 GiB disk: its 256 MiB rows passed,
then the 512 MiB push was refused `Capacity` (1,097,236,480 bytes free;
1,616,863,232 needed, the Store plus 1 GiB headroom) because the 2.7 GB
Sandbox image sits on the same disk, and the ENOSPC case aborted on that
refusal. The refusal is the product's documented behaviour, not a defect. The
machine was removed and the whole route re-run on an 8 GiB disk (the first
report's Lima size); the 4 GiB receipts are kept locally.

### #12 — progress

CLI progress: `R12-PROGRESS` 64/64 on each route and `R12-RAW` 2/2. Quiet
path: `R12-*-QUIET` 6/6 on each platform. Node SDK `on_progress`
(`R12-D-SDK-ONPROGRESS`): 14/14.

The three rows above are the first refusal run. See "Suite fixes and re-run"
below: with the expectations corrected, all 16 refusals pass.

### #13 — interruption, ownership and cleanup

`crash.py only …`, one case per command; `R13-A-AC-PULL` was run on its own
through the module because `only` has no entry for it.

| Platform | Cases | Checks |
| --- | ---: | ---: |
| docker (full set: 7 phase kills, 2 pull kills, flip, truncate, record, retire, read-only, reverse, concurrent, remove, lost answer, lost retire) | 22 | all pass |
| lima (sampled set) | 11 | all pass |
| apple-container (sampled set) | 9 | all pass |
| **total** | **42** | **630 / 630** |

`R13-D-LOST-RETIRE` records 4/4, but its note says the retire finished before
the worker died: the window was missed again, so it counts as NOT_RUN, as in
the first report. `R13-A-AC-PULL` saw no lost answer: 0 of 1 pulls failed.

### #10 — the guide in a fresh home

`guide_repro.py`: 21 blocks, **74 / 79** checks, 85.2 s, no leftover Store
records. The five misses are blocks 11 and 12, which teach recovering from an
Apple Container lost answer and assume one occurs within ten pulls: all ten
succeeded (`attempt N: pull ok`), so there was no unresolved pull to show or to
refuse. Block 13 and every other block passed. See "Suite fixes and re-run"
for the rewritten section and its 76 / 76 replay.

## Suite fixes and re-run

The first run's non-passing checks tested the suite, not the product, so the
suite was corrected and only the affected drivers re-run on the same binaries
and bundle (1-minute load 5.5). The first runs' receipts are kept locally.

| Fix | Re-run |
| --- | --- |
| `REF-FC-RECORD` / `REF-SSH-RECORD`: `machine status` on a removed-platform record moves from "stays available" to the refusal battery (`Unsupported` with the removal text); `machine list`/`get` stay available | 31 / 31 each |
| `REF-PG`: with no `lp08-pg` server the driver now passes a placeholder password, so `store connect` reaches the engine check | 9 / 9: `Unsupported`, "this LayerFS build has no PostgreSQL engine" |
| Refusal matrix as a whole (second re-run, after the `REF-PG` fix) | **16 / 16 PASS** |
| `GUIDE-zh.md` §9 rewritten: block 11 is ten pull + push round trips that must all succeed, block 12 the push to another machine refused `InvalidInput` while the Store is on `ac`, block 13 the pull back; a lost answer's text and the same-command recovery stay as prose pointing at §10's deterministic demo | `guide_repro.py` in a new home: 21 blocks, **76 / 76**, 86.2 s, no leftover records |

## Main observations

- Apple Container is no longer special. With `97fac452bd`'s close order and
  no read retry, every Apple Container pull this run did not interrupt on
  purpose (routes, sweeps, rounds, #13, the guide's ten) succeeded on its first
  attempt, 3.4 MB to 543 MB.
- Removed platforms behave as layerfs#616 documents: creation is refused with the
  exact text, an old record refuses every call except `machine list`/`get`,
  and `machine remove` forgets it.
- Caller and worker memory stays flat from 256 to 512 MiB on every platform.
  Lima's push worker peak was 55–57 MB here and 32 MB on the same binaries on
  the earlier 4 GiB Lima machine; it follows the guest, not the Store size.

## Limitations

- The refusal matrix ran three times and the guide twice: the first runs
  exposed outdated suite expectations, and the re-runs changed only those
  expectations, not the product, binaries or workload.
- NOT_RUN: `R11-ENOSPC-MID-SYNC-A`, `R13-D-LOST-RETIRE`.
- Timings are diagnostic: warm host cache, one sample, other agents' Docker
  containers running (1-minute load 7.7–21.3 during the run).
- Docker Desktop replaced colima, so docker numbers are not comparable with
  the first report's.

## Cleanup

All test machines were stopped at the end; their homes, VMs and the run folder
(4.6 GB) remain on the host, owned by this run, for the owner to release.
Nothing outside this run's homes, its bundle folder and its worktree
registration was touched.
