# pjdfstest benchmark

Read root AGENTS.md and the current SPEC.md. Current profile:
`fixed-posix-tap-unprivileged-subset-v2`. Four fixed scripts register 32 rows,
executed case → native/Docker/Lima/Apple Container → SQLite/PostgreSQL. Use the
shared public LayerFS CLI lifecycle. The primary owns campaign config and reports.

Unmodified upstream pin: `85a8aea9e685999ef0540392fd80535f873d7ff7` in
pjd/pjdfstest. Exact helper/script hashes and commands live in src/cases.py.

| Case | Unchanged script | Darwin/Linux assertions | Scope |
| --- | --- | ---: | --- |
| P01 | tests/open/04.t | 4 | Missing path/open ENOENT |
| P02 | tests/rename/18.t | 6 | Parent-directory rename EINVAL |
| P03 | tests/chmod/02.t | 5 | NAME_MAX, successful chmod and ENAMETOOLONG |
| P04 | tests/symlink/00.t | 14 | Functional/dangling symlinks and directory times |

Do not substitute scripts, remove assertions or change the upstream helper.
P04 retains its one-second sleep and timestamp assertions. P03 retains the
upstream platform branch: lchmod is enabled only for FreeBSD, outside this
Darwin/Linux selection; the original plan is five on both selected OSes.

## Selected subset privilege contract

The upstream README's root prerequisite concerns the full test battery. The
owner explicitly selected these same four unprivileged scripts for v2. Source
inspection shows that none invokes misc.sh's `requires_root`, passes `-u`/`-g`,
changes ownership or creates device nodes. pjdfstest.c initializes `uid=-1` and
`gids=NULL`, and switches identity only when those options are provided. These
scripts manipulate paths created by the ordinary command user. Do not extend
this finding to other upstream scripts or full-suite root qualification.

Run with the public CLI's actual inherited nonzero effective UID and GID. The
first-party prefix checks `id -u`/`id -g`, prints exactly one identity marker,
then calls the unchanged `prove -rv` script. The parser requires that observation
and records its values in tool_metrics. No sudo, setuid, no-new-privileges changes,
root helper, private call, host identity manipulation or assertion workaround.
Record source, helper binary, TAP tooling and effective identity in each receipt.

Retain all 32 earlier v1 NOT_RUN outcomes unchanged. They arose from the previous
blanket full-suite root gate. V2 is a prospective subset profile, not a relabel
of those rows or proof that root commands are supported. Its local ordinary-user
investigation passed all 29 original assertions at UID 501/GID 20; that check is
not LayerFS qualification or a performance sample.

## Outcomes and bounds

Require Perl/TAP::Harness (`prove`), OpenSSL, shell/text tools and the pinned
compiled helper with its original tests/conf and tests/misc.sh. Missing tools or
unsupported platform is NOT_RUN. Retain exact execution failures and uncertainty.

Parse the frozen TAP plan, every numbered assertion and final harness outcome.
Keep pass/fail/skip/TODO counts. A failed assertion remains FAIL even after shell
exit zero; an all-skipped/TODO selection is not PASS. Extra independent empty
committed-result proof stays optional/off by default with a separate budget
below 10 s. Upstream assertions are always part of the workload.

Default complete performance invocation budget is 15 s. Warm setup reuse does
not establish coldness; unknown caches remain INELIGIBLE diagnostics. Per-case
release and final infrastructure cleanup are mandatory, preserving uncertain
custody. Publish only the required report and preserve earlier profile history.
