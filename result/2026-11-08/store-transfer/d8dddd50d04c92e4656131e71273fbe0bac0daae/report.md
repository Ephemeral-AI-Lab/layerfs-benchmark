# store-transfer — a SQLite Store between a home and a machine

> Status: verification outcomes; timings are diagnostic and performance-ineligible.

**Outcome: PASS on every Store-transfer route, refusal and recovery path of
layerfs-project #8–#13 at the fixed build.** Four routes (native ↔ docker,
native ↔ lima, native ↔ apple-container and docker → native → lima) kept the
Store identical at byte, history and Workspace level, the 16 refusals each
refused with the documented code and no side effect, the guide's 21 command
blocks reproduced 79/79 in a fresh home, a 256 MiB and a 512 MiB Store moved
both ways on three platforms within 22–50 MB of caller memory, the seven
phases were observable in order on the CLI and through the Node SDK, and all
45 interruption cases ended with one authority and the documented recovery
command. Two diagnostic and cleanup gaps (#13's `F1`/`F2`) failed on all
three platforms in the first run and pass after the product fix.

## Configuration

| Item | Identity |
| --- | --- |
| LayerFS, first run | `8f0ff7b2bae2f09d67bc2e4c13dec2b40945d1ec` (parent `c421d9dba`), branch `feat/lp08b-store-transfer-v2` |
| LayerFS, fix and retests | `d8dddd50d04c92e4656131e71273fbe0bac0daae` (parent `8f0ff7b2b`) |
| CLI `8f0ff7b2b` | 14,018,920 B, sha256 `34cac78cd2b20600e66b8612e1fd524a8521711e906c17c43048292650bd93c3`, `layerfs 2.0.0`, macOS arm64 release, `CARGO_PROFILE_RELEASE_STRIP=none` |
| Daemon `8f0ff7b2b` | 10,514,368 B, sha256 `dd001579357ed1b33cd219428994034f63e1f671eaaaff8f6931edf811061e14` (unchanged at `d8dddd50d`) |
| CLI `d8dddd50d` | sha256 `81c79dfd…` |
| Release Linux bundle `8f0ff7b2b` | `hash 2e98e17e0a86833d968873655e90a444afdc8a59fdfaa59ba32db541fa7e2cbe`, `profile: release`, `platform: linux-aarch64`, guest `layerfs` 16,728,560 B sha256 `52bb6cd47a4a2f1ab81e7b8003c7e04726f2f04fa1166a428b0b3d288c4fa2e1` |
| Release Linux bundle `d8dddd50d` | `hash 05b718e3…`, `source.head d8dddd50d`, guest `layerfs` sha256 `39be850a…`; `layerfs-daemon` and the helper are unchanged (the changed crates are not in their dependency graph) |
| Node addon | `layerfs-node` release, 13,689,336 B, sha256 `0a7aed7b36334af5021446777162a9afa5c9bc5bad2a5d4cea67c6c519ff2568` |
| Guests | `docker` = colima default (2 CPU / 4 GiB / 30 GiB); `lm-*` = lima 2 CPU / 2 GiB / 4–8 GiB ext4; `ac-*` = apple-container 2 CPU / 2 GiB / 4–8 GiB |
| Host | macOS 27.2 (`26B123`), `Mac14,2`, Apple M2, 8 cores, 16 GiB; Docker client 29.9.3; colima 0.10.3; `limactl` 2.2.1; `container` 1.6.1 |
| Stores | #9/#12 fixture 21,426,176 B; #11 `s256` 271,646,720–271,716,352 B and `s512` 543,076,352–543,223,808 B; #11/#12 `quiet` 17,182,720–17,190,912 B; #13 68,046,848 B |
| Duration | 2026-11-07 23:08 – 2026-11-08 01:15 CST, three serial stages plus a fix and retest |

Each guest's `/layerfs/bundle/layerfs` sha256 was compared with the sealed
listing before its rows were kept, so a stale bundle cannot explain a result.
Rows below are at `8f0ff7b2b` unless a row says `d8dddd50d`; that pin changes
the `send`/`verify` failure path and the worker's answer tail only, and the
cases it touches were re-run there.

## Results

### #9 — four routes and 16 refusals

Checks passed / total, one row per case. `matrix.py`.

| Case | docker | lima | apple-container | Checks |
| --- | ---: | ---: | ---: | --- |
| `R9-*-RT` — round trip that must not change the Store | 43 / 43 | 43 / 43 | 43 / 43 (`d8dddd50d`; 30 / 43 before) | sha256 before push = after pull = `last_transfer.sha256`; `heads` unchanged; source `store.sqlite*` gone, record directory kept, every other home file byte-identical |
| `R9-*-MOD` — edit on the target, commit, pull back | 53 / 53 | 53 / 53 | 53 / 53 (`d8dddd50d`; 34 / 48 before) | target `commit list` grows by one; pulled Store's sha256 = `last_transfer.sha256`; native mount reproduces the 24-line edited manifest; `store status` holders empty, `op` null; a local write afterwards succeeds |
| `R9-X-RETIRE-DIR-*` | 5 / 5 | 5 / 5 | 5 / 5 | only this Store retired on the source; machine, project and neighbouring Store records byte-identical |
| `R9-A-BLOCKER` (apple-container, size sweep) | — | — | 10 / 10 (`d8dddd50d`; 10 / 10 with 4 of 8 pulls lost before) | 3, 5, 7, 7.5, 9 MiB and the 21.7 MiB Store each arrived on the first attempt |
| `R9-H-HOP` — docker → native → lima | 76 / 76 | | | both hops `retired: true`; `bytes` and `heads` identical across hop one, hop two and the way back; lima mount equals native's manifest |

Totals at `8f0ff7b2b`: 29 cases, 534 checks, 507 passed; the 27 failures were
all apple-container `store pull` (`Unknown` at `send`), and they pass at
`d8dddd50d`.

Round trips at the 21.4 MB Store took 0.134 s push / 0.104 s pull on docker
(diagnostic, warm host cache); the lima and apple-container round-trip times
were not kept as a comparable pair. One honest
nuance for the two-hop row: after lima had mounted the Store, its raw
`store.sqlite` bytes differed from the first hop's (`1f20f7fa…` vs
`3bd72061…`) because the daemon's checkpoint rewrote the file layout; `heads`,
`bytes`, `last_transfer.sha256` and the 24-line manifest were all equal, and
the round trip that does not use the target keeps its strict byte assertion.

The 16 refusals, each asserted for exit code, error code, message and an
unchanged home tree:

| Refusal | Command | Exit | Code |
| --- | --- | ---: | --- |
| `REF-PG` | `store push ref-pg docker` (PostgreSQL record) | 125 | `Unsupported` / `InvalidInput`: "is a PostgreSQL database; it does not move" |
| `REF-WRONGDIR-PUSH` | `store push ref-docker lm` while on docker | 125 | `InvalidInput`: "`layerfs store pull ref-docker` brings it to native first" |
| `REF-PUSH-NATIVE` | `store push <s> native` | 125 | `InvalidInput` |
| `REF-PULL-NATIVE` | `store pull <s>` on native | 125 | `InvalidInput` |
| `REF-NOSTORE` | `store push nope docker` | 125 | `NotFound` |
| `REF-NOMACHINE` | `store push <s> ghost` | 125 | `NotFound` |
| `REF-BADNAME` | `store push bad/name docker`; `store create "x y"` | 125 | `InvalidInput` |
| `REF-EXISTS` | push onto a machine already holding that name | 125 | `Exists` at `check` |
| `REF-STOPPED` | push to a stopped machine | 125 | `Unavailable`, names `layerfs machine start lm`; the machine stays stopped |
| `REF-INUSE-SANDBOX` | pull while a Sandbox of that project is open | 125 | `InUse`, `detail.related=[{sandbox,…}]` |
| `REF-BUSY` | a second `store push` of the same Store | 125 | `Busy`, names the pid and phase |
| `REF-LEASE` | push while another process holds the lease | 125 | `InUse`, `detail.related=[{lease,<pid>}]` |
| `REF-FC-CREATE` | `machine create fc1 firecracker` | 125 | `Unsupported`: "firecracker is permanently disabled by product policy (layerfs-project#7)" |
| `REF-SSH-CONNECT` | `machine connect h1 10.0.0.5` | 125 | `Unsupported`: "ssh is permanently disabled by product policy (layerfs-project#7)" |
| `REF-FC-RECORD` | 11 write calls against a hand-written firecracker record | 125 | `Unsupported`, same message; `machine.list/get/status`, `store.list/get/status` and `doctor` still exit 0 |
| `REF-SSH-RECORD` | the same 11 calls against a hand-written ssh record | 125 | same, ssh message; `machine.disconnect` is not policy-blocked |

Three behaviours recorded, none of them a #9 requirement: on a hand-written
`firecracker`/`ssh` record, `machine remove`/`disconnect` pass the policy
gate but then answer `InvalidInput` ("names its lima host" / "needs its
host"), i.e. the teardown path is only as usable as those records, which the
product no longer creates; `store remove` of a Store whose record names an
unreachable machine is `Unavailable` and needs the record removed by hand;
and `REF-PG` is only reachable through a hand-written `kind: postgresql`
record because this release CLI is built without the `postgresql` feature.

### #10 — the guide, block by block, in a fresh home

`guide_repro.py` extracted all 21 `bash` blocks of [GUIDE-zh.md](../../../../store-transfer/GUIDE-zh.md)
and ran them in order in one shell in a new `LAYERFS_HOME`: **79 / 79 checks,
21 blocks in 27.3 s**, 20 blocks exiting 0 and one exiting 125 (the reverse
refusal the guide asks for). The home ended with no Store left and exactly
the expected `native` plus a stopped `docker`.

Five guide defects were found by running it literally and fixed in the guide,
not relaxed in the checks: `workspace exec`/`unmount` take the mount's
`<sandbox>:<path>`, not a sandbox and branch; `machine update docker` prints
`ready`, not `stopped`; `chmod 0500` cannot reliably catch the `record`
window, so `Unresolved` is shown with the platform's real lost reply instead;
`retire` failure is made deterministic by locking the source *before* the
push; and the interrupt waits for the first `send` piece rather than a
`sleep`. The capacity refusal is out of this guide's scope; its numbers come
from #11 below.

### #11 — 256 MiB and 512 MiB, capacity and mid-`send` ENOSPC

Per-phase seconds and throughput, caller peak RSS (`/usr/bin/time -l`),
worker `VmHWM` after a fresh `machine stop/start`, `.incoming` peak by
sampling. `lp08s2.py route`.

256 MiB Store (271,646,720–271,716,352 B):

| Route | Direction | Total s | check | snapshot | send | verify | install | record | retire | send MiB/s | caller RSS | worker `VmHWM` |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | push | 1.375 | 0.006 | 0.152 | 1.022 | 0.172 | 0.003 | 0.002 | 0.011 | 253.5 | 49.2 MB | 5.1 → 31.4 MB |
| docker | pull | 1.155 | 0.009 | 0.145 | 0.827 | 0.149 | 0.000 | 0.001 | 0.018 | 313.3 | 29.1 MB | 5.1 → 31.7 MB |
| lima | push | 1.136 | 0.006 | 0.146 | 0.789 | 0.173 | 0.003 | 0.001 | 0.011 | 328.6 | 49.2 MB | 5.0 → 31.2 MB |
| lima | pull | 1.176 | 0.004 | 0.219 | 0.778 | 0.157 | 0.000 | 0.000 | 0.012 | 333.2 | 29.2 MB | 5.0 → 31.6 MB |
| apple-container | push | 0.848 | 0.004 | 0.153 | 0.495 | 0.174 | 0.002 | 0.001 | 0.013 | 523.2 | 49.3 MB | 5.7 → 29.9 MB |
| apple-container | pull at `d8dddd50d` | 1.693 | — | — | — | — | — | — | — | 204 | 29.2 MB | 5,748 → 32,952 KB |
| apple-container | pull at `8f0ff7b2b` | FAIL, 25 attempts | | | | | | | | — | 11.6 MB | 5.7 → 32.5 MB |

512 MiB Store (543,076,352–543,223,808 B):

| Route | Direction | Total s | send s | send MiB/s | caller RSS | worker `VmHWM` | `.incoming` peak |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| docker | push | 3.235 | 2.439 | 212.4 | 39.3 MB | 29.3 MB | 543,223,808 |
| docker | pull | 3.472 | 2.701 | 191.8 | 22.2 MB | 31.7 MB | 543,223,808 |
| lima | push | 3.127 | 2.199 | 235.6 | 39.4 MB | 29.1 MB | 543,150,080 |
| lima | pull | 2.418 | 1.623 | 319.2 | 22.1 MB | 31.6 MB | 543,150,080 |
| apple-container | push | 1.541 | 0.887 | 584.3 | 39.5 MB | 29.8 MB | 543,121,408 |
| apple-container | pull at `d8dddd50d` | 3.169 | — | 212 | 22.2 MB | 5,748 → 33,148 KB | 543,076,352 |

Peak memory does not grow with the Store: doubling 259 MiB → 518 MiB took the
caller from 49.2 to 39.3 MB and the worker from 31.4 to 29.3 MB, which is the
8 MiB piece plus its JSON/base64 copies, not the Store. `.incoming` peaked at
exactly `bytes` on every successful transfer and was gone after `install`
(`store status.file.incoming_bytes = 0`), and the source kept only
`record.json` after `retire`. Hash speed on both paths was ~1.8–1.9 GB/s
(warm), the same sequential `digest()`.

Capacity pre-check (`R11-CAP-PRE`), refused before a byte moves:

| Route | `needed` | target free | exit / code | sent | target written |
| --- | ---: | ---: | --- | ---: | --- |
| lima (4 GiB disk filled to 1.0 GiB free) | 1,345,404,928 = 271,663,104 + 1,073,741,824 | 1,049,448,448 = `df` byte for byte | 125 / `Capacity` | 0 | nothing |
| apple-container (same) | 1,345,404,928 | 1,049,239,552 = `df` | 125 / `Capacity` | 0 | nothing |
| docker at `d8dddd50d` (1 GiB tmpfs over the target directory) | 1,345,388,544 = 271,646,720 + 1,073,741,824 | 1,073,741,824 = the tmpfs `df` | 125 / `Capacity` | 0 | nothing |

In all three the event stream held `check` and the final JSON only, the source
stayed `native`/`idle` with its sha256, the target directory was never
created, and the rejected call peaked at 3.3 MB on the two VM routes.

Mid-`send` ENOSPC, injected once `check` had passed:

| Route / mount | Check | `send` failed after | Error | Source | Target | Same command after clearing |
| --- | --- | ---: | --- | --- | --- | --- |
| lima / delalloc | 8 / 8 | 58,720,256 / 271,663,104 (21.6 %) | 125, `Failed`, `store push, send: Os { code: 28, kind: StorageFull, "No space left on device" }`, `detail.phase: send` | sha256 unchanged, `native`, `idle`, `op` null | `.incoming` 59,342,848 B, no `store.sqlite` | exit 0, 1.111 s, installed copy sha256 = snapshot |
| lima / `remount,nodelalloc` | 9 / 9 | 50,331,648 / 271,663,104 | same | same | same | exit 0, 1.435 s, sha256 = snapshot |
| apple-container / delalloc | 8 / 8 | 50,331,648 / 271,663,104 | same | same | partial `.incoming`, disk 100 % full | exit 0, 0.763 s, sha256 = snapshot |
| docker at `d8dddd50d` (1500 MiB tmpfs, then `remount,size=64m`) | 11 / 11 | 67,108,864 / 271,646,720 (24.7 %) | same | same | partial `.incoming`, no `store.sqlite` | exit 0, target sha256 = `last_transfer.sha256`, `heads` unchanged, no `.incoming` left |
| apple-container / `nodelalloc` | NOT_RUN | — | `mount -o remount,nodelalloc` exits 32 | — | — | — |

So a mid-`send` full disk is a deterministic `Failed` at `send`: the
authority stays on the source, `op` is cleared, the partial `.incoming` is
kept, and the same command succeeds once space is back, because a write at
`offset == 0` truncates. The injection itself has two lessons: a target
mounted ext4 keeps 5 % for root, so the filler must bring `total − used` down
to the budget (using `avail` produced a false success), and the product is
right to judge on `f_bavail`; a tmpfs over the directory the product's
`statvfs` reads is a second-accurate substitute for filling a 30 GiB disk.

### #12 — the seven phases, on the CLI and through the SDK

`matrix.py` (CLI `--progress`) and `lp08s2.py sdk`.

| Check | docker | lima | apple-container |
| --- | --- | --- | --- |
| each of the 7 phases has ≥ 1 event | PASS | PASS | PASS (`d8dddd50d`) |
| first event of each phase in order `check,snapshot,send,verify,install,record,retire` | PASS | PASS | PASS |
| every stderr line is one JSON progress event | PASS | PASS | PASS |
| `send.total` constant, `done` non-decreasing, last `done == total` | PASS | PASS | PASS |
| `send` has more than two counted events (multi-piece) | PASS (0 / 8 MiB / 16 MiB / 21,426,176) | PASS | PASS |
| `snapshot` and `verify` start at 0, rise monotonically, end at `total` | PASS | PASS | PASS |
| last event is `retire` and it precedes process exit | PASS (0.002–0.004 s before) | PASS | PASS |

`R12-PROGRESS` scored 64 / 64 at `d8dddd50d`. A 21.4 MB push emitted, with a
monotonic timestamp per line: `check@0.0060`, `snapshot@0.0132`,
`snapshot 0@0.0136`, `snapshot 21426176@0.0244`, `send 0@0.0254`,
`send 8388608@0.0655`, `send 16777216@0.1003`, `send 21426176@0.1200`,
`verify@0.1200`, `verify 0@0.1219`, `verify 21426176@0.1355`,
`install@0.1402`, `record@0.1420`, `retire@0.1425` — the result JSON is
written to stdout only after `retire`. `snapshot`/`verify` show `(0,total)`
then `(total,total)` on a small Store because their hashes are throttled to
250 ms; the counted middle events of the sizes above are what #11 shows.

The quiet path (no `--progress`) on a 16.4 MiB Store: 6 / 6 on each platform
— exit 0, **zero** stderr lines, exactly one stdout JSON line with
`{store,from,to,bytes,heads}`, 0.06–0.11 s.

The Node SDK's `on_progress` on the same build and the same docker Store: 14 /
14. It received **44 events, the same count and the same per-phase split as
the CLI (1 / 3 / 34 / 3 / 1 / 1 / 1)**, in the same order, `send.total`
constant, the last `done == total == bytes`, **all 44 delivered while the
call had not settled**, push 1.402 s and pull 1.232 s against the CLI's 1.375
s and 1.155 s; a handler that throws at every event still got all 14 events,
produced 14 warnings, and the call returned a normal result that could then be
pulled back.

### #13 — interruption, ownership and cleanup

The state table, measured by freezing the CLI at a phase's progress event,
reading the record on disk, and killing it. `crash.py`.

| Frozen at | `record.machine` | `op` on disk | source copy | target copy | `store status` | `doctor` |
| --- | --- | --- | --- | --- | --- | --- |
| `check` | native | none | intact | none | `idle` | nothing |
| `snapshot` / `send` / `verify` | native | previous phase, certain (dead process → stale) | intact | partial or whole `.incoming` | `idle` | warning: stale intent, remote `.incoming` with its byte count |
| `install` event (before install) | native | `verify`, certain | intact | whole `.incoming` | `idle` | warning: as above |
| `install` done, `record` not written | native | `install`, **uncertain** | intact | whole `store.sqlite` | `unresolved` | error: fix = the same command |
| `record` write failed | native | `record`, **uncertain** | intact | whole `store.sqlite` | `unresolved` | error: same |
| `retire` failed or interrupted | **to** | `retire`, certain (stale) | leftover | authority | `idle`, `last_transfer.retired: false` | warning: "did not retire", fix = the next push/pull |
| pull lost the worker's answer (apple-container 1.6.1) | the source machine | `send`, **uncertain** | intact | native `.incoming` | `unresolved` | error: fix = the same `store pull` |

Case results at `8f0ff7b2b`: **45 cases, 640 checks, 39 PASS / 6 FAIL** —
docker 20 PASS + 2 FAIL, lima 10 + 2, apple-container 9 + 2, where the six
failures are the same two additional diagnostics on each platform (`F1`
`DOCTOR-INCOMING` 4 of 6 checks, `F2` `REMOVE-CERTAIN` 3 of 4). All 15
required items passed on docker, and on the sampled lima and apple-container
lists. At `d8dddd50d` the six now pass 4 / 4 each, with `TAMPER-TRUNCATE`
(14 / 14, 14 / 14, 12 / 12) and `REMOVE` (14 / 14 × 3) unchanged as the
no-regression neighbours.

What each group asserted:

| Group | Evidence |
| --- | --- |
| Six phase interrupts (`KILL-*`, docker full, lima/apple-container sampled) | the frozen row, the row after SIGKILL, `store status`, both sides' existence/size/sha256, `doctor`'s ok and findings, then the same command again: exit 0, `machine` correct, `op` cleared, `retired: true`, `heads` unchanged, one whole copy, no `.incoming`, `doctor` clean. The source copy's sha256 is asserted unchanged in every kill case. |
| Tampered piece (`TAMPER-FLIP`, `TAMPER-TRUNCATE`) | exit 125 `Failed` at `verify` ("the copied Store's sha256 is not the snapshot's" / "the copied Store's bytes is not the snapshot's"); **no ownership switch** (`machine` still native, `last_transfer` untouched), source unchanged, target has no `store.sqlite`, the altered `.incoming` kept; the same push then succeeds and the leftover disappears. The product has no `Corrupt` code, so the plan's word was corrected, not the behaviour. |
| `RECORD-FAIL` / `RETIRE-FAIL` | `record` failing on a `0500` store directory keeps `uncertain` → `unresolved`, and the same push succeeds after the mode is restored. `retire` failing on a locked source file returns `detail: {authority: <to>, source: <from>, retired: false, phase: "retire"}` with exit 125, `store get` shows the authority already moved, `doctor` warns and points at the next pull, and after unlocking, the pull deletes the leftover first and succeeds with `heads` unchanged; a `store push` in that state is refused `InvalidInput` and does not touch the authority. |
| Read-only (`READONLY`, both the `unresolved` and the `retired: false` state) | 16 calls of `store status`, `store get`, `store list` and `doctor` (2 each), all exit 0, with the whole home tree — relative path, 4-digit mode, bytes, `mtime_ns`, content sha256 — **identical before and after**: no lock created, `layerfs.lock`'s mtime untouched, no stale lease swept, no log written. `doctor` reported the remote fragment with its byte count and a fix. |
| Reverse (`REVERSE`) | on an `unresolved` install row, the opposite direction returns 125 `Unresolved` naming the command that clears it; after both refusals the home tree, the target listing and both sides' sha256 are unchanged (so the old "delete first, refuse second" defect is not back); the same direction then succeeds, and immediately repeating it is `InvalidInput` with no second copy. |
| Concurrency (`CONCURRENT`) | during a 68 MB `send`: a second `store push` is `Busy` (naming pid and phase), `store remove` is `Busy`, a `store pull` while a Sandbox of that project is open is `InUse` with `detail.related`; the first transfer lands intact, and after the Sandbox closes `store remove` succeeds and clears the machine side. |
| `store remove` (`REMOVE`) | from an `unresolved` state: exit 0, the home record directory gone, the machine's `store/<name>` gone, **the machine and its volume still there**, a neighbouring Store's sha256/`heads`/`machine`/status unchanged, `doctor` clean for it. |
| apple-container lost reply (`R13-A-AC-PULL`) | the `Unknown` at `send` → `unresolved` + `uncertain` → `doctor` error with the same command → re-running it recovers to `idle`/native with `heads` unchanged; observed 1 loss in 2 runs here, 5 of 5 earlier, and 1 of 1 inside #10's reproduction. |

## Main observations

- Ownership has exactly one authority at every interruption point. The
  observable split is `install`/`record` (uncertain → `unresolved`, two whole
  copies, one named recovery command), `send`/`verify` failures (certain →
  `idle`, source still the authority, a partial `.incoming` that the next
  transfer truncates), and `retire` failures (authority already moved,
  `retired: false`, the next call in the other direction deletes the leftover
  first).
- The two gaps this matrix found were real and are closed: after a **certain**
  failure at `send`/`verify` the intent was erased together with `op`, so
  `doctor` could not name the machine holding the fragment and `store remove`
  could not reach it. The fix records `incoming_on`, and both `doctor` and
  `resolve::leftover` read it. Nothing else in #13 changed.
- apple-container 1.6.1 still loses worker answers at a rate of roughly
  20–30 % of connections; the retry on the read-only `send` piece is what
  makes pulls succeed (`worker.connection` counts: 21.4 MB pull baseline 6,
  measured 8; 68 MB baseline 12, measured 15 and 17; **push always equals the
  baseline**, so no write is ever replayed). The retry is not a fix for the
  transport, and one 256 MiB pull still needed a second invocation.
- Peak memory is the piece size, not the Store: 22–50 MB for a caller and
  29–33 MB for a worker at both 259 MiB and 518 MiB.
- Refusals are cheap and clean: a capacity refusal sends nothing, writes
  nothing, and leaves `op` unset, and every refusal left the home tree
  byte-identical.
- The guide is now executable: the literal reproduction caught five real
  mistakes in it, and the recovery manual's steps (the lost reply, a locked
  source, a leftover fragment, `store remove`) all work as written.

## Limitations

- #13's 45 cases stand at `8f0ff7b2b`; at `d8dddd50d` only the six that failed
  and two no-regression neighbours were re-run. #11's docker capacity and
  ENOSPC rows and the apple-container rows were also re-run at `d8dddd50d`,
  and #9's apple-container route was re-run in full; the docker and lima
  transfer rows were not.
- A certain failure at `install` can still leave a fragment whose machine name
  the record does not hold; the fix covers `send` and `verify` only. It needs
  `install` to fail after `check` passed (an `Exists` race or a rename
  failure) and was not constructed on real machines.
- apple-container's `store pull` is not 100 % first-try; `R11-ENOSPC-MID-SYNC-A`
  is NOT_RUN because that platform refuses `mount -o remount,nodelalloc`.
- `LOST-RETIRE`'s unknown-at-`retire` window was never hit on a real machine
  (every `retire` finished before the kill); `RETIRE-FAIL` covers the same
  `detail` deterministically and a unit test covers the `Unknown` path.
- The SDK's `on_progress` was measured on docker only; the CLI covered all
  three platforms.
- Per-phase times and throughput are diagnostic. The same build repeated a
  512 MiB docker push at 2.499 s and 3.235 s while bytes and RSS stayed within
  0.2 %, and a parallel stage shared the host and colima.
- `#11`'s `.snapshot` and `install`-time ENOSPC rows are N/A by design: there
  is no `.snapshot` file, and `install` is one `rename`.
- PostgreSQL Stores, firecracker and ssh machines are outside this matrix by
  product policy; PostgreSQL is covered only through a hand-written record.

## Cleanup

All machines and their data disks were removed (`limactl list` and
`container list` empty at each stage's end), every docker worker was stopped
with `machine stop docker`, `colima` was stopped last, no NFS or loopback
mounts remained, the filler tmpfs and volume placeholders were unmounted and
deleted, and the temporary fixture/home trees were deleted. The product tree
stayed clean and unpushed. The guide's second home was preserved as the #10
evidence.

## Evidence

Receipts stayed local and are ignored: per-case `json` with the checks,
evidence strings, commands and exit codes, the raw `--progress` and SDK event
streams, the guide's per-block stdout/stderr, and the pin file with the CLI,
daemon and bundle identities. Nothing binary is committed; `store connect`
passwords were read from the server's environment into
`--password env:NAME` and never written down.
