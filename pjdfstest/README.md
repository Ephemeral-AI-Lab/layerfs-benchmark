# pjdfstest

Four fixed upstream POSIX assertion scripts, run with `prove -rv`. This suite
reports assertion outcomes rather than treating a successful shell exit as proof.
See [AGENTS.md](AGENTS.md) for the selected scripts and expected counts.

Pin [pjd/pjdfstest](https://github.com/pjd/pjdfstest/tree/85a8aea9e685999ef0540392fd80535f873d7ff7).
Build unmodified source with `autoreconf -ifs`, `./configure`, `make pjdfstest`.
Keep the binary and tests tree together under `BENCH_TOOL_ROOT/pjdfstest`;
Perl/TAP::Harness (`prove`), OpenSSL, shell and standard text tools must be ready.

Upstream requires root. The native macOS build is available, but nonroot execution
is a recorded prerequisite exclusion, not a failed assertion or a pass. Linux
Sandbox command identity must also be checked before admitting each route.
No third-party patches or disabled assertions are used.

Use `python3 pjdfstest/src/run.py --help` and the environment example with the
campaign's product/ownership configuration. Default extra verification is off;
the selected upstream assertions remain mandatory. Each lifecycle is bounded
by 15 s and cleanup is required. Timings with unknown cache state remain
ineligible diagnostics and establish no qualified speed comparison.
