# store-transfer — moving a SQLite Store between a home and a machine
> group: transfer · measures: correctness, recovery, speed

## Basic info

| | |
| --- | --- |
| Tool | in-house: `matrix.py`, `lp08s2.py`, `crash.py`, `guide_repro.py`, `docker-cap.py` (host drivers, Python stdlib) and `manifest.sh` (runs inside a Workspace) |
| Drives | the public `layerfs store` / `machine` / `sandbox` / `workspace` CLI only; nothing links LayerFS code |
| Runs on | `native` on macOS plus a `docker` (colima), a `lima` and an `apple-container` machine, each with a sealed release Linux bundle of the same source head |
| Status | active; first run 2026-11-08 (layerfs-project #8–#13) |
| Rules | the root [AGENTS.md](../AGENTS.md); one case per invocation, failures keep their scene and are never retried automatically |

## Overview

A Store moves as one file: `store push` takes the whole SQLite Store from
`native` to a machine, `store pull` brings it back. The transfer is seven
phases in a fixed order — `check → snapshot → send → verify → install →
record → retire` — 8 MiB per piece, one writer at a time, with the target's
own `statvfs` deciding capacity. A PASS here means the Store is identical
after the move at three levels, and that every interruption leaves one
authority and a reachable recovery command; it does not cover PostgreSQL
Stores (they never move), non-`native` to non-`native` transfers (there is no
direct route) or any platform product policy refuses ([#7](https://github.com/Ephemeral-AI-Lab/layerfs/issues/7)).

| Ticket | Checked here | Cases |
| --- | --- | --- |
| [#9](https://github.com/Ephemeral-AI-Lab/layerfs/issues/9) | `native` ↔ docker / lima / apple-container both ways, `docker → native → lima`, and the 16 refusals | `R9-*` in `matrix.py` |
| [#10](https://github.com/Ephemeral-AI-Lab/layerfs/issues/10) | the operation guide, [GUIDE-zh.md](GUIDE-zh.md), run block by block in a fresh `LAYERFS_HOME` | `guide_repro.py` |
| [#11](https://github.com/Ephemeral-AI-Lab/layerfs/issues/11) | a 256 MiB and a 512 MiB Store each way: per-phase time, throughput, caller and worker peak RSS, `.incoming` peak; the `check` capacity refusal; a mid-`send` ENOSPC | `R11-*` in `lp08s2.py` and `docker-cap.py` |
| [#12](https://github.com/Ephemeral-AI-Lab/layerfs/issues/12) | the seven phases as CLI `--progress` events and as the Node SDK's `on_progress`; the quiet path; a small Store | `R12-*` in `matrix.py` and `lp08s2.py`, `sdk-progress.mjs` |
| [#13](https://github.com/Ephemeral-AI-Lab/layerfs/issues/13) | SIGKILL in each phase, a tampered piece, a failed `record` and `retire`, read-only zero side effects, a reverse command, the same command again, concurrency, `store remove` on both sides | `R13-*` in `crash.py` |

Three levels of evidence are taken on every round trip, and a case's verdict
needs all three, never just exit code 0:

1. **Bytes** — `sha256` of the Store file, kept on the caller or checked
   against `last_transfer.sha256`;
2. **History** — `store get`'s `heads`, `last_transfer`, `commit list`,
   `branch list`;
3. **Use** — mount the Store in a Workspace on the machine it should now be
   on and diff `manifest.sh` output line by line: entry type, 4-digit mode,
   size, sha256, symlink target, UTF-8 and space-bearing names. `manifest.sh`
   works on macOS (`stat -f`, `shasum`) and inside a guest (`stat -c`,
   `sha256sum`).

## Files

| File | What it is |
| --- | --- |
| `GUIDE-zh.md` | the operation guide reproduced by `guide_repro.py`: setup, a normal round trip, the failure and recovery manual, the limits |
| `matrix.py` | `setup`, `route docker\|lima\|ac`, `hop`, `refuse`, `acsweep`, `rawprogress`, `cleanup` — the #9 routes, the refusal matrix, #12's CLI progress |
| `lp08s2.py` | `setup`, `route docker\|lima\|ac`, `acsweep`, `acrounds`, `sdk`, `report` — #11's sizes, capacity and ENOSPC, #12's quiet and SDK paths |
| `docker-cap.py` | `cap`, `enospc` — the same #11 injections inside a docker worker, as a tmpfs over the directory the product measures |
| `crash.py` | `setup`, `route docker\|lima\|ac`, `only …` — #13's interruptions, tampering, ownership recovery and cleanup |
| `guide_repro.py` | runs every `bash` block of `GUIDE-zh.md` in order, in one shell, in a fresh home, and asserts what the guide says the output is |
| `make_fixture.py` | #9/#12 fixture: 20 MiB seed-derived `data/big.bin` (more than one 8 MiB piece) plus text, an empty file, a 0755 script, a symlink, a deep path and a UTF-8 name with a space |
| `make_fixture-s2.py` | #11 fixtures: `s256` (32 × 8 MiB), `s512` (64 × 8 MiB) and `quiet` (16 MiB), incompressible, plus `fixtures.json` with per-file sha256 |
| `make_fixture-s3.py` | #13 fixture: 64 MiB `data/big.bin` in the #9 shape; `python3 make_fixture-s3.py /abs/dir [seed]` |
| `manifest.sh` | the three-level manifest, one line per entry (`D`/`F`/`L`), used inside a Workspace and on the host fixture |
| `report.py` | rolls `matrix.py`'s receipts up into a table and `matrix.json` |
| `sdk-progress.mjs` | collects the Node SDK's `on_progress` events for a push and a pull, including a handler that throws at every event |

Receipts (`json`/`jsonl` per case, raw progress streams, per-block guide
output) are local only: they stay in `receipts/`, which is ignored. The
prose evidence they support is in the report.

## Setup

1. Build the CLI and daemon at the pin, then seal a release Linux bundle from
   the same tree into `~/.cache/layerfs/bundle/<version>/linux-<arch>`
   (`tools/linux_bundle.py {daemon,worker,helper,seal} --profile release`,
   four commands). The guests run the bundle's `layerfs`, so a bundle from a
   different head is a different product — check `bundle.json`'s
   `source.head` and `profile` before measuring, and `sha256sum
   /layerfs/bundle/layerfs` inside a guest against the sealed listing.
2. Point the drivers' `CLI`/`DAEMON`/`BASE` constants at this environment.
   They carry the absolute paths of the 2026-11-08 run.
3. A private `LAYERFS_HOME` per run, `mkdir` mode 700, absolute paths only,
   `LAYERFS_CONSTRUCTION_WORKERS=1`. Machines are named per home (a VM's name
   carries the home id), so one home is one set of machines; `#10` needs a
   second, empty home.
4. `native` needs its daemon registered before a Workspace can mount on it:
   `layerfs machine update native --daemon <abs>/layerfs-daemon`.
5. Bring up the routing layer: `colima start` (or Docker Desktop, with
   `LP08_DOCKER_SOCK=$HOME/.docker/run/docker.sock` for the drivers and
   `DOCKER_SOCK` for the guide) for docker, `limactl` on `PATH` for lima (the
   first `machine create` may fetch the Ubuntu image), `container system
   status` for apple-container. `lp08s2.py` needs `LP08_DISK=8G`: the Sandbox
   image in the bundle leaves too little of a 4 GiB disk for the 512 MiB Store.
6. Fixtures: `python3 make_fixture.py <dir>/p1`,
   `python3 make_fixture-s2.py <dir>` and
   `python3 make_fixture-s3.py <dir>/p1` — the same seeds every time, so a
   Store's bytes are recomputable rather than stored.

## Running

```bash
# #9 routes, the refusal matrix and #12's CLI progress
python3 matrix.py setup
python3 matrix.py route docker          # R9-D-RT, R9-D-MOD, R9-X-RETIRE-DIR-D
python3 matrix.py cleanup && python3 matrix.py route lima
python3 matrix.py cleanup && python3 matrix.py route ac && python3 matrix.py acsweep
python3 matrix.py cleanup && python3 matrix.py route docker && python3 matrix.py hop
python3 matrix.py refuse                # the 16 refusals
python3 matrix.py rawprogress
python3 report.py

# #11 sizes, capacity, ENOSPC and #12's quiet and SDK paths
python3 make_fixture-s2.py <dir>/fixture
python3 lp08s2.py setup
python3 lp08s2.py route docker && python3 lp08s2.py route lima && python3 lp08s2.py route ac
python3 lp08s2.py acsweep && python3 lp08s2.py acrounds && python3 lp08s2.py sdk
python3 docker-cap.py cap && python3 docker-cap.py enospc

# #13 interruptions and recovery, then #10 from the guide itself
python3 make_fixture-s3.py <dir>/fixture/p1
python3 crash.py setup && python3 crash.py route docker
python3 crash.py route lima && python3 crash.py route ac
python3 guide_repro.py
```

Budget: the three routes plus the two-hop and the 16 refusals ran in about
30 min; the 256/512 MiB matrix about 60 min; #13's 45 cases about 45 min;
#10 about 30 s of execution. The 16 GiB host ran one route at a time, 2 GiB
per VM, and needed ≥ 25 GiB free on `/`.

## Cache boundary

Per-phase times and throughput are **diagnostic**: the native Store comes
from a just-imported fixture (host page cache warm), the guest reads cold,
and the Stores use the `disposable` profile. The physical quantities — bytes,
caller and worker peak RSS, `.incoming` peak, `df`, `needed`/`free` — do not
depend on the cache and are what #11's rows claim. A repeat of the same
measurement on the same build moved times by up to 30 % while bytes and RSS
stayed within 0.2 %.

## Limits and known issues

- A single writer per Store: a concurrent second call must be `Busy`, and the
  drivers poll `store status`'s `op` rather than sleeping to reach a phase.
- Injection reaches phases by freezing the CLI (`SIGSTOP`) the instant it
  writes that phase's progress event, reading the record on disk, then
  killing it. `enter(phase)` writes the event before the `op`, so a case
  frozen at phase *n* usually reads back phase *n−1*; that is the product's
  order, not a defect, and rows must be read that way.
- Mid-`send` ENOSPC must be injected against `total − used` (ext4 keeps 5 %
  for root), otherwise the write succeeds and the case lies.
- `install`'s ENOSPC and a `.snapshot` temporary file are **N/A**: `snapshot`
  and `verify` hash in place, and `install` is one `rename`. The only
  temporary file in the transfer is the target's `store.sqlite.incoming`.
- apple-container 1.6.1 used to lose the tail of large answers. Since
  layerfs `97fac452bd` the worker waits for the client to close first and
  the product reads each piece once (no retry); every pull in the
  `ab4c1a4712` run succeeded first time. Guide blocks 11–12 still teach the
  recovery from such a loss and fail when none occurs.
- A record of a removed platform (firecracker, ssh, microsandbox) answers
  only `machine list`/`get`; `REF-*-RECORD` still expects `machine status`
  to answer, as for the old *disabled* platforms.
- `store connect` needs a quoted password (`env:NAME` or `file:/path`); the
  drivers read it from the server's environment and never write it down.

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-08 | `ab4c1a4712` | Outcome: PASS on every Store-transfer route and recovery path at layerfs `ab4c1a4712` (Ephemeral-AI-Lab/layerfs#617, merged into `layerfs_v2_0_0` as `716197c499` with the same tree), and every Apple Container pull now succeeds on its first attempt; the only checks that did not pass expect behaviour layerfs#616/#617 changed on purpose or infrastructure this host lacks | [report](../result/2026-11-08/store-transfer/ab4c1a4712ec0e4d032a2ac341638053a02e2c91/report.md) |
| 2026-11-08 | `d8dddd50d0` | Outcome: PASS on every Store-transfer route, refusal and recovery path of layerfs-project #8–#13 at the fixed build | [report](../result/2026-11-08/store-transfer/d8dddd50d04c92e4656131e71273fbe0bac0daae/report.md) |
<!-- runs:end -->
