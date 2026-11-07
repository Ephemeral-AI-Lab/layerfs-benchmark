# ovnfs vs LayerFS: storage and overlay design

**Both systems now use content addressing, zstd compression, whole-object deduplication,
zstd-prefix deltas and packs. The gap that remains is structural. ovnfs versions git trees,
whose directories are rewritten in full along every changed path and never delta'd, and a
new checkout re-captures the folder. LayerFS keys inodes by serial, delta-encodes its
metadata pages and chunks large files. That is why the two now store a starting tree in
about the same space (25.1 vs 23.8 MB), while LayerFS still adds 11–35× fewer bytes per
commit and nearly nothing per branch.**

Read from source: ovnfs `5d54cb0aec474c9aad90f43214ae4ba2bfab1d89` and LayerFS
`layerfs_v2_0_0` @ `751b6b83c4dd2051a112518591442e6c98808ba4`. Paths are relative to each
repository. Where a statement is an inference rather than read in code, it says so. The
measured numbers are from [report.md](report.md): both systems at these commits, run on
2026-11-07.

## At a glance

| | ovnfs | LayerFS |
| --- | --- | --- |
| Object id | git SHA-1 over `"<type> <len>\0"` + body (`store/store.go`) | BLAKE3 over `"layerfs/object/v2\0"` + canonical `LFSO` envelope, 32 B (`core/crates/layerfs-content/src/object/id.rs`) |
| Objects | blobs and git trees; a snapshot is a root tree id; no commit object | 13 roles (whole file, chunk, extent, inode, directory, attribute, symlink and root pages); commits and branches are SQL rows pointing at a root |
| Verify on read | CRC-32C per packed frame; SHA-1 only after rebuilding a delta; loose objects unchecked | every decoded record re-hashed against its id |
| Dedup unit | whole file | whole file below 128 KiB; content-defined chunks (GEAR, 8/16/32 KiB min/target/max) above |
| Dedup scope | one store per daemon: all snapshots, checkouts and folders | one Store: all commits, branches and projects in it |
| Compression | zstd `SpeedDefault` per frame, raw if not smaller; files over 1 MiB stay plain loose files | zstd level 3 per payload record; metadata grouped (48–64 KiB) at level 1; stored raw if the first KiB saves under 1/32 |
| Delta algorithm | zstd with the base as raw dictionary | zstd with the base as prefix (`refPrefix`) for payloads; custom COPY/INSERT for metadata pages |
| Delta base | only the same path in the parent snapshot | the previous version, a rename's predecessor, or a similarity ring (8,192 slots, bottom-k signature) |
| Delta limits | chain depth < 8, files ≤ 16 MiB, kept only if ≤ ½ the plain frame | depth 16 for whole files, 8 for chunks, 8 for metadata; chain budgets; capped chains rebase onto the full root |
| Trees / metadata | git trees, always stored whole, never delta'd | serial-keyed inode pages, field-packed, delta'd; a deep edit doesn't rewrite parent directories |
| Packs | append-only files, 44 B frame header, sealed at 32 MiB with an `.idx` | SQLite `pack` rows, 24 B header, 256 KiB packs (16 MiB singletons), 4 lanes |
| Garbage collection | mark from roots, 1 h grace; rewrite a pack once ¼ is garbage | no unreachable-object collection found; history is kept; only explicit SQLite free-page reclamation |
| Durability | fsync only when a pack seals or is rewritten | SQLite WAL; Disposable profile `synchronous=OFF`; idle WAL checkpoint + truncate |
| Overlay | AUFS-style: upper → frozen layers → base (the live source folder); whiteouts | per-Workspace overlay SQLite: generation-versioned inodes and entries, 4 KiB data cells |
| Copy-up | whole file (reflink/`clonefile` where the filesystem has it) | none: unchanged ranges stay references to committed content; only changed cells are written |
| Branch / checkout | `new` re-captures the folder into a new base; `fork` reuses the parent | one branch row; no objects, no history rows copied |

## 1. Content addressing

**ovnfs** uses git's object model. A blob id is SHA-1 over a git header plus the bytes. The
header is hashed but not stored, so a loose object file is the file's exact bytes and can be
served or cloned as-is. Trees are git trees. A snapshot is a root tree id, and so is the
checkout's private `.git`. Integrity is partial. Packed frames carry a CRC-32C and their
header id. Full SHA-1 is checked only when a delta is rebuilt, and loose objects are read
unchecked (`store/pack.go:178-187`, `store/delta.go:104`, `store/store.go:282`).

**LayerFS** hashes a canonical, typed envelope with BLAKE3 and a domain-separation string.
Every object kind, including inode and directory pages, is content-addressed. Every
decoded record is re-hashed on read (`encoding/delta/read.rs`, `pool/read.rs`). Commits and
branches are catalog rows rather than objects.

*Consequence:* ovnfs stays interoperable with git, so blobs match git blob ids and it can
reuse a repository's index ids. LayerFS's ids can't be checked by git, but every read is
authenticated.

## 2. Deduplication

Both deduplicate exact objects across their whole store, so identical content on different
branches is stored once. S4 shows this on both sides: five branches each making the same
commit added 32,768 B to ovnfs's packs and 28,397 B to LayerFS.

The differences are granularity and what counts as an object:

- **Large files.** ovnfs has no chunking. A one-line edit to a 10 MB file is a new 10 MB
  blob, which then relies on a delta (§4). LayerFS chunks files of 128 KiB and up with
  content-defined chunking, so unchanged chunks are shared even when bytes shift.
- **Metadata.** ovnfs trees are objects, but a changed directory is a new tree object, so
  directories dedup only when they are unchanged. LayerFS shares unchanged inode pages and
  delta-encodes changed ones.
- **What ovnfs leaves out of the store.** Files over 1 MiB are loose, uncompressed files.
  Raw bytes stay in an upper or layer until a snapshot is hashed. In a git repository,
  stat-clean tracked files aren't stored at import: ovnfs uses the index's blob id and
  reads bytes from the repository (`source/capture.go:421-427`, `base/base.go:266-301`).
  That last point means ovnfs's import size depends on whether the folder is a git
  checkout. This benchmark's tree isn't one, so every file was stored.

## 3. Compression

Both use zstd at a default-ish level and fall back to raw when compression doesn't pay.

- **ovnfs** compresses each pack frame on its own (`zstd.SpeedDefault`, `store/pack.go:69`)
  and keeps the raw bytes if the frame isn't smaller. Files over 1 MiB
  (`cloneFile = 1 << 20`, `store/store.go:384`) are stored uncompressed so they can be
  reflinked. Its metadata uses deflate (`capture.bin`, layer manifests), plain JSON
  (`state.json`) or an uncompressed varint log (`nodes.log`).
- **LayerFS** compresses each payload record at level 3 (`PAYLOAD_LEVEL`,
  `encoding/codec.rs:63`) with a size-dependent window. It probes the first 1 KiB and stores
  verbatim if that saves under 1/32. Metadata objects are gathered into 48–64 KiB groups and
  compressed together at level 1 (`GROUP_LEVEL`, `codec.rs:68`). That is the one place
  either system compresses across objects. Inode values are field-packed varints, not
  compressed. (The codec is frozen by owner decision, 2026-11-06.)

*Measured:* the 65.0 MB base tree became 23.9 MB of ovnfs packs plus a 1.05 MB loose file
(25.1 MB). LayerFS stored 23.8 MB (24.4 MB at `b4fa173e`). Per-file zstd at similar levels lands in the same place;
LayerFS's small edge is likely grouped metadata compression and the one >1 MiB file being
compressed (inferred).

## 4. Delta encoding

Both encode a new version as zstd with the old version as reference: ovnfs as a raw
dictionary (`WithEncoderDictRaw`, `store/delta.go:75`), LayerFS as a prefix
(`ZSTD_CCtx_refPrefix`). For a small edit to one file, the two produce similar bytes.

The differences are how a base is found and what gets delta'd:

| | ovnfs | LayerFS |
| --- | --- | --- |
| Base for an edited file | the same path's blob in the parent snapshot | the previous version (advisory predecessor) |
| Renamed or recreated file | no base, stored whole | the rename's recorded predecessor, or the similarity ring (#88) |
| New file similar to an existing one | stored whole | the similarity ring can propose a base |
| Large files | whole-file delta up to 16 MiB | per-chunk deltas, each against its base extent |
| Directories and metadata | never delta'd (trees are plain frames) | COPY/INSERT deltas on inode, directory and extent pages |
| Chain depth | < 8 (`deltaDepth`) | 16 whole file, 8 chunk, 8 metadata; capped chains rebase |
| Acceptance | delta ≤ ½ the compressed plain frame | one trial; keep the smaller record |

The edit model renames about 10% of the time. Every ovnfs rename stores the file again in
full, while LayerFS deltas it against its predecessor.

## 5. Packs and physical layout

- **ovnfs** writes append-only `store/packs/<n>.pack` files: 44-byte frame header (CRC-32C,
  SHA-1 id, flags, lengths, freshness), sealed at 32 MiB with a `.idx` written then. Before
  sealing, the index lives in memory and is rebuilt by scanning at open, and a torn tail is
  cut. Collection marks from tree roots with a one-hour grace and rewrites a pack once a
  quarter is garbage. Appends aren't synced; only seals and rewrites are.
- **LayerFS** keeps packs as immutable rows in the Store's SQLite database (UPDATE/DELETE
  triggers abort). Small packs (256 KiB, up to 256 groups) sit in four lanes: ordinary
  metadata, chunks, whole files, and singletons up to 16 MiB. An `object_location` table
  maps each id to pack, group and record. Durability is SQLite's: WAL, which the Disposable
  profile runs with `synchronous=OFF` and, since #86, checkpoints and truncates when idle.
  I found no unreachable-object collection: history is retained, and the only reclamation
  frees unused SQLite pages.

*Consequence:* ovnfs can drop what no snapshot references, which suits disposable agent
checkouts. LayerFS keeps every Commit, which suits long retained history; its size only
grows.

## 6. Overlay and copy-on-write

**ovnfs: file-level overlay.**
- The read stack is the writable upper, then frozen layers, then the base. The base's
  bottom is the live source folder, served while each file's size, mtime and inode still
  match the capture; otherwise the stored blob is served.
- The first write copies up the whole file, using reflink or `clonefile` where the
  filesystem supports it. A memory tier holds small new or copied-up files, up to 1 MiB, and
  spills them after 2 s idle.
- A snapshot:
  1. renames the upper into a layer;
  2. hashes it into the parent tree in the background, rewriting the trees along the changed
     paths;
  3. once hashing pauses for 200 ms, stores the blobs and collapses the layer into a
     manifest.
- `ovnfs new` makes a new base by re-capturing the folder. A stat cache skips re-hashing,
  but it still writes a new `capture.bin` and lock for all 9,415 paths. `ovnfs fork` reuses
  the parent's base.

**LayerFS: block-level overlay in a database.**
- Each Workspace has its own overlay SQLite database. Inodes and entries are
  generation-versioned rows, with whiteouts. File data lives in 4 KiB cells, and unchanged
  ranges are reference pieces pointing at committed content, so nothing is copied up.
- Commit captures the changed namespace, builds content objects (whole file or chunks, each
  with a delta predecessor), then dedups, selects deltas, packs, and publishes in one Save.
- A branch fork writes one row.
- Reads of committed content go through the Store with a shared 64 MiB object cache per
  daemon. On a cold mount that means several daemon round trips per file, which is why
  full-tree reads of 9,415 small files took 7–25 s on 2026-11-06 (`b4fa173e`) and 3.7–4.2 s
  at `751b6b83`, against 1.6–2.1 s for ovnfs.

## 7. Why the measured costs differ

| Cost | ovnfs (measured) | LayerFS (measured) | Main design reason |
| --- | ---: | ---: | --- |
| Import of 65.0 MB | 25.1 MB | 23.8 MB | both: per-file zstd plus exact dedup |
| Per commit (5 edits) | 25–30 KB in packs (29–67 KB apparent overall) | 2.1–3.3 KB `new_stored` | ovnfs rewrites every git tree on each changed path (20-byte SHA-1 per entry, never delta'd) and stores renames whole. LayerFS's serial-keyed inode pages don't ripple up, and its page deltas are small. |
| Per new branch | ~115 KB (82 KB `capture.bin`, ~24 KB `nodes.log`, upper) | one row, plus its first commit's metadata | ovnfs re-captures the folder per checkout; LayerFS forks by reference |
| Per snapshot, besides packs | ~4 KB layer manifest, `nodes.log` | none outside the Store | ovnfs keeps per-layer state on the filesystem |

The breakdown of ovnfs's per-commit pack bytes into trees versus file deltas is an
inference from the code, not a measurement. Measuring it would take an object-level dump
of a pack.

## What this means

- For a **starting tree**, the two are now equivalent: both are compressed, deduplicated
  object stores.
- For **history**, LayerFS's metadata design matters more than its payload codec. Its
  serial-keyed inode pages with deltas cost about 1.6 KB per commit (per its own
  per-write storage notes); ovnfs's git trees cost tens of KB. The gap grows with directory
  size and depth.
- For **large files**, LayerFS's content-defined chunks share unchanged ranges.
  ovnfs relies on a whole-file delta capped at 16 MiB. Larger files are stored whole (and
  reflinked where possible). Not measured here; this tree's largest file is about 1.2 MB.
- For **branches**, LayerFS forks are free. An ovnfs `new` checkout costs about 115 KB plus
  a full stat pass over the folder. `fork` is cheaper.
- For **integrity and retention**, LayerFS authenticates every read and keeps all history.
  ovnfs checks frame CRCs, collects garbage, and syncs less. That fits each system's purpose:
  LayerFS is retained versioned storage; ovnfs is disposable, git-integrated agent
  checkouts.
