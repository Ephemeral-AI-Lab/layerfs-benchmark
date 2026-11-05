# pjdfstest benchmark

Read the repository AGENTS.md and SPEC.md. Four fixed scripts produce 32
registered rows, executed case → native/Docker/Lima/Apple Container →
SQLite/PostgreSQL. Public LayerFS CLI only, through the shared lifecycle.

Unmodified upstream pin: `85a8aea9e685999ef0540392fd80535f873d7ff7` in
pjd/pjdfstest. Exact scripts/hashes/argv live in src/cases.py:

| Case | Script | Darwin/Linux assertions | Scope |
| --- | --- | ---: | --- |
| P01 | tests/open/04.t | 4 | Missing path/open ENOENT |
| P02 | tests/rename/18.t | 6 | Parent-directory rename EINVAL |
| P03 | tests/chmod/02.t | 5 | NAME_MAX, successful chmod and ENAMETOOLONG |
| P04 | tests/symlink/00.t | 14 | Functional/dangling symlinks and directory times |

Do not substitute scripts or drop assertions. P04's upstream one-second sleep is
part of the workload. Upstream README requires root, Perl/TAP::Harness and a
compiled pjdfstest. Establish identity/capability before the product attempt;
missing root or platform prerequisites is NOT_RUN. No sudo prompts or identity
workarounds. Native Darwin builds, but the macOS nonroot route is NOT_RUN unless
its command identity is independently established as root. tests/conf explicitly
has Darwin and Linux cases; compile success alone is not a runtime PASS.

Use prove -rv so TAP remains observable. Parse the frozen plan, every numbered
assertion and the final harness outcome. Keep pass/fail/skip/TODO counts. Failed
assertions stay FAIL even if a script exits zero. An all-skipped/TODO selection
is not PASS. No silent filtering of unsupported operations after a failure.

Default lifecycle budget 15 s. Independent empty-result proof optional/off by
default, with separate budget below 10 s. Cache state unknown means INELIGIBLE.
Per-case release and campaign-final cleanup are mandatory; preserve uncertain
state. Publish only the required report, with upstream outcomes and exclusions.

## Selected CLI prerequisite

At the selected LayerFS pin all four routes execute as UID 501/GID 20. The
public CLI admits no root identity and the guest routes enforce no-new-privileges.
Upstream requires root: all 32 selections must remain NOT_RUN under this pin.
A sudo/setuid image does not supply the missing product capability. Do not weaken
the upstream requirement or remove the product restriction to obtain PASS.
