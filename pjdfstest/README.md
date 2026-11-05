# pjdfstest — POSIX file semantics, unprivileged subset
> group: filesystem · measures: correctness

## Basic info

| Item | Value |
| --- | --- |
| Tool | [pjd/pjdfstest](https://github.com/pjd/pjdfstest/tree/85a8aea9e685999ef0540392fd80535f873d7ff7) at `85a8aea9e685999ef0540392fd80535f873d7ff7`, unmodified; scripts run with `prove -rv` |
| Profile | `fixed-posix-tap-unprivileged-subset-v2` |
| Runs on | native, Docker, Lima and Apple Container; SQLite and PostgreSQL Stores (32 rows: four cases × eight configurations) |
| Status | Current profile v2. v1 is retired; its 32 NOT_RUN results remain historical. |
| Frozen rules | [AGENTS.md](AGENTS.md): per-script source assessment, privilege contract and limitations. Exact helper/script hashes and commands: [src/cases.py](src/cases.py). |

## Overview

Four unchanged upstream scripts run with `prove -rv`, preserving 4 open,
6 rename, 5 chmod and 14 symlink assertions on Darwin/Linux. The owner selected
this ordinary-user subset of upstream's root-oriented full battery. These exact
scripts never request identity switching or root-only operations; the helper
preserves its caller's identity by default. A PASS shows that these assertions
held as an ordinary user. It does not qualify the full upstream suite, root
execution or privilege workarounds, which are outside this profile.

| Case | Workload | Expected result |
| --- | --- | --- |
| P01 | `tests/open/04.t`: missing path/open ENOENT | 4 TAP assertions pass |
| P02 | `tests/rename/18.t`: parent-directory rename EINVAL | 6 TAP assertions pass |
| P03 | `tests/chmod/02.t`: NAME_MAX, successful chmod and ENAMETOOLONG | 5 TAP assertions pass |
| P04 | `tests/symlink/00.t`: functional/dangling symlinks and directory times; keeps its intrinsic one-second wait | 14 TAP assertions pass |

The wrapper checks and records the actual effective UID/GID before running the
script. V2 changes the blanket prerequisite decision of v1 and adds this
identity evidence; it changes no upstream script, assertion, helper source or
P04's intrinsic one-second wait. A native ordinary-user investigation passed all
29 assertions; this is separate from LayerFS results.

## Setup

Prerequisites:

- Build the pinned, unmodified source with `autoreconf -ifs`, `./configure`,
  `make pjdfstest`.
- Keep the helper and original tests tree together under
  `BENCH_TOOL_ROOT/pjdfstest`.
- Provide Perl/TAP::Harness (`prove`), OpenSSL, shell and standard text tools.

Config: copy [environments.example.json](environments.example.json) and supply
the campaign's product artifacts, private home, tool root and database
ownership. See `python3 pjdfstest/src/run.py --help`.

```bash
python3 pjdfstest/src/run.py prepare --environment <config.json> --cache <dir> \
  --case P01 --machine native --backend sqlite
python3 pjdfstest/src/run.py run --environment <config.json> --cache <dir> \
  --case P01 --machine native --backend sqlite --output <fresh dir>
python3 pjdfstest/src/run.py finish --environment <config.json> --cache <dir>
```

Extra committed-result verification defaults off (`--verify` turns it on);
upstream checks remain enabled. The full lifecycle of each case is bounded by
15 s, and cleanup is required. Unknown caches remain ineligible for qualified
speed claims. The full upstream suite is not being qualified.

## Past runs

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-06 | `b919f50eaf` | Diagnostic terminal: PASS | [report](../result/2026-11-06/pjdfstest/b919f50eaf9cce79671f8501a580279d23cc5f3c/report.md) |
<!-- runs:end -->

pjdfstest v1 (retired): 32 NOT_RUN; replaced by the unprivileged subset v2 run above.
