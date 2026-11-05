# C01 cache protocol and eligibility gap

Status: Current-cell analysis, not an implemented cold protocol. No cache reset,
product change or measurement is authorized by this document alone.

Product reference: `Ephemeral-AI-Lab/layerfs` commit
`b919f50eaf9cce79671f8501a580279d23cc5f3c`. All source paths below refer to that
snapshot. Governing policy: `docs/general/agent-measurement-policy.md` sections
1–3; suite contract: `SPEC.md`. C01 remains the only selected implementation cell.

## What is allowed to stay ready

Reuse release binaries, installed tools, images, machines and closed independent
inputs. Executable/code pages and an idle running machine are not proof that the
case's filesystem/database pages are cold. The required controls concern the
actual data/metadata dependencies of each timed phase, not unrelated files or
all memory on the machine.

Keep authoritative live state: Workspace identity, bound root, overlay frontier,
open/reference ownership and pending published mutations. A cache reset must not
unmount a dirty Workspace, discard changes, reconstruct them outside the timer,
advance its Branch or change the exact body. Resident authoritative state and a
replaceable cache serving an avoidable physical read are different things. Their
classification needs source-backed dependency accounting, not an RSS threshold.

## C01 does not read a prepared payload; it still reads metadata

Exact body: `for i in $(seq 1 1000); do echo $i > f$i; done`.
The empty base supplies no existing file payload. C01 writes 1,000 small payloads
rather than reading a prepared 64 MiB file. No eviction of nonexistent base file
payload is necessary. Metadata first acquired by Exec must pay that acquisition
inside its timer; metadata already supplied by mount requires separate scrutiny.
This does not permit own-write payload-read credit or allow arbitrary warm state
inside a multi-operation body. Do not revise the exact body by inserting resets
between its 1,000 creations.

An empty namespace is not an absence of immutable metadata. Source:

- `engine/crates/layerfs-workspace/src/operations/namespace/create.rs`:
  `free_name` resolves the directory and layered binding before creating a name.
- `engine/crates/layerfs-workspace/src/mutation/driver.rs`: missing immutable
  facts are supplied outside the overlay job.
- `engine/crates/layerfs-workspace/src/mutation/facts.rs`: `BaseView::supply`
  obtains base inode/name facts, directory shape and portable metadata.
- `engine/crates/layerfs-workspace/src/base/view.rs`: `BaseView::open` acquires
  the filesystem root at mount; `child`, `inode` and `stat` can demand additional
  committed objects. The bound root is retained as Workspace state.

Therefore **C01 Exec is currently UNKNOWN/INELIGIBLE**, not automatically cold
because its starting view is empty. To admit this phase independently, identify
which metadata demands actually remain at Exec entry and demonstrate either
that they cannot be served by setup/mount caches, or enforce and verify their
coldness. A byte-exact body hash plus a zero payload-read count would establish
only the payload fact, not metadata coldness. Existing source inspection alone
does not supply the missing run evidence. An eligible Exec would still not make
the full row eligible if Mount or Commit remains ineligible.

## Phase-specific minimum next steps

| Phase | Required boundary and evidence | Current gap |
| --- | --- | --- |
| Mount | After preparation, before mount. Account for case Store/history/root metadata and overlay-template pages actually read by this call. | No demonstrated owned invalidation plus residency check for those inputs. New CLI process does not reset worker/daemon/backend/OS caches. |
| C01 Exec | After mount, before exact body. Distinguish retained bound-root/open ownership from replaceable canonical metadata, SQLite pager pages and OS metadata/data pages used by first demands. | No per-case dependency/hit evidence proving mount-prepared metadata cannot credit the phase; no scoped reset/validator. |
| C01 Commit | After Exec, before Commit, preserving the same live overlay frontier. Account for the new inode/name/payload rows Commit consumes, plus committed/history metadata and backend pages. | Exec's writes may be served by the live overlay SQLite pager and OS cache. No public cache-release/residency control preserving this frontier. |
| Unmount | After Commit. Record teardown cost and actual release outcomes separately. | Do not use it as a reset for a preceding dirty Commit; it ends the Workspace and deletes its overlay. |

Each control needs an exact owned target, enforcement start/end, method/version,
phase identity, relevant bytes/pages, observed residency or equivalent validated
bypass evidence, failures and elapsed cost. Validation must not itself touch
measured data into cache. No arbitrary `cold: true` configuration is sufficient.
A run with missing evidence keeps its raw duration as diagnostic.

## Product boundary that blocks a simple cold Commit

`engine/crates/layerfs-overlay/src/database/profile.rs` initializes the live
Workspace connection with `journal_mode=MEMORY`, `synchronous=OFF`,
`locking_mode=EXCLUSIVE`, `mmap_size=0` and a configurable pager cache (default
2 MiB). Per-job writes complete while that connection stays open. Newly written
rows can consequently remain in its pager through Exec to Commit.

`engine/crates/layerfs-workspace/src/base/cache.rs` independently retains
immutable/decoded objects and derived facts. A published Commit can seed its
constructed namespace metadata. These are not all the Workspace's essential
identity/open state, and clearing only OS pages cannot clear these caches.

`docs/architecture/api/sdk/workspace/unmount.md` confirms that unmount closes and
deletes the overlay and refuses dirty state unless discarded. Unmount/remount is
therefore not a preserving reset. `engine/crates/layerfs-daemon/src/control/invalidate.rs`
is post-merge coherence, not a pre-phase coldness operation. The public CLI and
`engine/crates/layerfs-daemon/src/operator/dispatch.rs` expose no general cold
release-and-observe operation.

The smallest product investigation is whether a bounded, quiescent operation
can release **replaceable clean pager/canonical caches** and return effective
observations without changing identity/frontier or retaining physical-data
warmth. SQLite cache-release advice is only a candidate: success must not be
assumed to mean complete eviction. Any necessary product route must be designed
and exposed through the public CLI before this suite uses it. Do not add a
private protocol or direct Store SQL escape hatch. No fsync, preallocation,
Durable execution or synthetic rewrite belongs in the disposable overlay reset.

## Machine and backend controls

| Route/domain | Required scope | Status |
| --- | --- | --- |
| Native SQLite | Exact Store/overlay files, relevant pager/canonical state and macOS metadata/page cache. | Missing validated scoped controls. `purge` would affect the shared host and is not an accepted default. |
| Guest SQLite | Exact guest Store/overlay state, guest OS pages and host pages backing the guest disk/VM image when those can serve the sample. | Missing validated controls for both layers. Guest `drop_caches` alone would not establish host-backing coldness. |
| Any PostgreSQL | Same live overlay requirements, exact case database pages in PostgreSQL shared buffers, server OS cache and backing virtualization caches where applicable. | Distinct databases isolate mutations, not shared buffers. Connection close is not eviction. No demonstrated instance-owned reset/residency protocol. |

A dedicated campaign-owned server/guest makes scoped infrastructure controls
possible; it does not demonstrate their effectiveness. Server restart alone
leaves server OS pages; OS page invalidation alone leaves PostgreSQL shared
buffers. macOS `F_NOCACHE` or Linux page advice alone does not evict SQLite's
pager or LayerFS's canonical heap state and needs effective, correctly scoped
validation. Stop/restart or cache controls may touch only exact owned resources.
Never purge the shared host or restart another owner's PostgreSQL server.

## Admission for the current implementation

Retain per-phase cache verdicts. C01 may execute once as a labelled diagnostic;
execution success, optional verification, budgets and cleanup remain independent
of numeric eligibility. Current `measure.assess_cache` fails closed for all eight
routes. Add only source-backed and demonstrated phase validators; do not change
policy to make an existing receipt pass or relabel it after the fact. No build,
provisioning, reset or measurement runs accompany this document.
