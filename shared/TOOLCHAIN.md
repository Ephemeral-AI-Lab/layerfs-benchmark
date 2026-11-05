# Cached tools for the six suites

Use one image and one native tool directory for all suites. Build/install once
outside measurement, record hashes and package versions, then reuse them. Keep
sources and binaries in a private cache, never in Git or a measured Store.

| Tool | Unmodified upstream commit | Runtime location under BENCH_TOOL_ROOT |
| --- | --- | --- |
| fio | `ff930c4653ae3952d6b09ab3ec89671aeabf2cbe` | `fio` |
| fsx / fsstress | `31f7192f90a89a6f808a37c3a3cd30491bd50eba` | `bin/fsx`, `bin/fsstress` |
| mdtest / IOR | `8e109900e24d45f1cd1184f108458f5fa9b4692c` | `bin/mdtest`, `bin/mpirun` |
| pjdfstest | `85a8aea9e685999ef0540392fd80535f873d7ff7` | `pjdfstest/pjdfstest`, `pjdfstest/tests/` |
| smallfile | `aa2519de5bf0b3b383db2c31eacbf8ac4328e19c` | `smallfile/` |

Native tools are built against the host's recorded compiler/MPI/Python. The
selected xfstests sources require Linux. Keep the unchanged pjdfstest tests and
smallfile Python modules beside their executables; do not copy tool trees into
individual Workspace fixtures. See each suite README for build requirements.

The campaign Linux image derives from the cached `fs-bench-computer` image
`sha256:66aeb6bbf7fc825686a0e6d8c8486d90c99d03ce81f854008f179a23bdf4097e`.
It uses Python 3, Perl/prove, OpenSSL and OpenMPI. Build dependencies are GCC,
make, autoconf, automake, libtool, pkg-config and OpenMPI development headers.
Configure IOR with `--without-mpiio CC=mpicc`, build `src/mdtest`, and retain the
matching MPI runtime. Configure/build pjdfstest without modifying upstream.
The cached Linux fio is static; fsx/fsstress require libc only. Save the exact
package list and executable SHA-256 values locally before sealing the image.

Docker selects the image through public `machine update docker --image <id>`.
For Lima and Apple Container, export a Docker archive in the format accepted by
the selected product's `tools/linux_bundle.py:docker_archive`, then use public
`machine create <name> <platform> --image <absolute-archive-path>`. The archive's
config digest may differ from Docker's image identifier; record both. Reuse the
matched product bundle unchanged; the tool image is a separate recorded input.
No SDK/private protocol or guest filesystem injection is needed.

Check tool paths and actual UID once through a small public CLI lifecycle before
measured rows. The selected product's nonroot execution/no-new-privileges
contract cannot satisfy pjdfstest's root prerequisite. No sudo/setuid workaround
or weakened upstream assertions is permitted.

At finish, release owned machines, server/data, image and temporary archives.
Keep only compact local receipts and the small pinned artifacts needed for
reproduction; do not uninstall shared host dependencies or prune other owners'
images/caches. A later campaign resolves product authority again and checks all
cached source/build identities before reuse.
