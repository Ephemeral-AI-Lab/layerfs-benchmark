# pjdfstest

Four unchanged upstream scripts run with `prove -rv`, preserving 4 open,
6 rename, 5 chmod and 14 symlink assertions on Darwin/Linux. The current explicit
profile is `fixed-posix-tap-unprivileged-subset-v2`.

Pin [pjd/pjdfstest](https://github.com/pjd/pjdfstest/tree/85a8aea9e685999ef0540392fd80535f873d7ff7).
Build unmodified source with `autoreconf -ifs`, `./configure`, `make pjdfstest`.
Keep the helper and original tests tree together under `BENCH_TOOL_ROOT/pjdfstest`.
Provide Perl/TAP::Harness (`prove`), OpenSSL, shell and standard text tools.

The owner selected an ordinary-user subset of upstream's root-oriented full
battery. These exact scripts never request identity switching or root-only
operations; the helper preserves its caller's identity by default. The wrapper
checks and records actual effective UID/GID before running the script. Root
execution and privilege workarounds are outside this profile. See
[AGENTS.md](AGENTS.md) for the per-script source assessment and limitations.

Prior v1's 32 NOT_RUN results remain historical. V2 changes the blanket
prerequisite decision and adds identity evidence; it changes no upstream script,
assertion, helper source or P04's intrinsic one-second wait. A native ordinary-user
investigation passed all 29 assertions; this is separate from LayerFS results.

Use `python3 pjdfstest/src/run.py --help` and supply the campaign's product
artifacts, private home, tool root and database ownership. Extra committed-result
verification defaults off; upstream checks remain enabled. The full lifecycle
is bounded by 15 s and cleanup is required. Unknown caches remain ineligible
for qualified speed claims. The full upstream suite is not being qualified.
