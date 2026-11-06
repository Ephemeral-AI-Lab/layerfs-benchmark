"""Pinned workload definitions; optional proofs never run during measurement."""

import hashlib

SOURCE_COMMIT = "b919f50eaf9cce79671f8501a580279d23cc5f3c"
SOURCE_PATH = "api/node/test/verify/cells/workloads.mjs"
SOURCE_BLOB = "f3a65cc9aec02af2d772edd929daa8b2b446638d"
ORIGINAL_CASES = tuple(f"C{number:02d}" for number in range(1, 13))
# layerfs-project#62 additions: separate fixed from per-entry Commit cost and
# read non-repeating committed data. C01 is the sweep's 1,000-file point.
PG62_CASES = ("C13", "C14", "C15", "C16", "C17", "C18")
CASE_IDS = ORIGINAL_CASES + PG62_CASES
IMPLEMENTED_CASES = CASE_IDS
PG62_VERSION = "pg62-v1"
SWEEP = {"C14": 0, "C15": 100, "C16": 10_000}
# 64 MiB of AES-128-CTR keystream: deterministic, non-repeating, and identical
# from OpenSSL 3 (guest images) and LibreSSL/OpenSSL on macOS.
RANDOM_KEY = "6c617965726673706733322d70657266"
RANDOM_SHA256 = "bf1dda74febef555d66fdc9f19d3869b3fa50d6f64c94c01d66fc854052e9643"
RANDOM_SETUP = (
    "head -c 67108864 /dev/zero | openssl enc -aes-128-ctr -nosalt "
    f"-K {RANDOM_KEY} -iv 00000000000000000000000000000000 > rand"
)
ENVIRONMENT = {
    "LANG": "C",
    "LC_ALL": "C",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_AUTHOR_DATE": "2026-10-03T00:00:00Z",
    "GIT_COMMITTER_DATE": "2026-10-03T00:00:00Z",
}


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _numbered_checks(count, extra_entries=0):
    """Exact root entries, regular-file types, contents and per-file sizes.

    Bash does the name/type checks. Two bulk tool passes avoid one process per
    file, and the size pass rejects missing final newlines that awk normalizes.
    """
    return f"""export LANG=C LC_ALL=C
fail() {{ echo "VERIFY FAIL $*"; exit 1; }}
shopt -s nullglob dotglob
entries=(*)
[ "${{#entries[@]}}" -eq {count + extra_entries} ] || fail "root entry count"
files=()
for ((i=1; i<={count}; i++)); do
  [ -f "f$i" ] && [ ! -L "f$i" ] || fail "f$i is not a regular file"
  files+=("f$i")
done
awk 'FNR != 1 || "x" $0 != "x" substr(FILENAME, 2) {{ bad = 1 }}
  END {{ if (bad || NR != {count}) exit 1 }}' "${{files[@]}}" || fail "numbered contents"
wc -c "${{files[@]}}" | awk '
  $2 != "total" && $1 != length(substr($2, 2)) + 1 {{ bad = 1 }}
  END {{ exit bad }}' || fail "numbered sizes"
"""


def _numbered_verifier(count):
    return _numbered_checks(count) + 'echo "VERIFY OK"\n'


def _git_verifier():
    return (
        _numbered_checks(100, extra_entries=1)
        + """export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
[ -d .git ] && [ ! -L .git ] || fail ".git directory"
g() { git -c safe.directory='*' -c core.fsmonitor=false "$@"; }
[ "$(g rev-list --count HEAD)" = 1 ] || fail "commit count"
[ "$(g ls-files | wc -l | tr -d ' ')" = 100 ] || fail "tracked files"
[ "$(g log -1 --format=%s)" = init ] || fail "commit subject"
status=$(g status --porcelain) || fail "Git status command"
[ -z "$status" ] || fail "Git status is not clean"
echo "VERIFY OK"
"""
    )


def _empty_verifier():
    return """export LANG=C LC_ALL=C
shopt -s nullglob dotglob
entries=(*)
if [ "${#entries[@]}" -ne 0 ]; then
  echo "VERIFY FAIL root is not empty"
  exit 1
fi
echo "VERIFY OK"
"""


def _tree_verifier():
    """Check every expected path and type, and reject extras at each level."""
    return """export LANG=C LC_ALL=C
fail() { echo "VERIFY FAIL $*"; exit 1; }
shopt -s nullglob dotglob
entries=(*)
[ "${#entries[@]}" -eq 10 ] || fail "top directory count"
for ((a=1; a<=10; a++)); do
  [ -d "$a" ] && [ ! -L "$a" ] || fail "directory $a"
  entries=("$a"/*)
  [ "${#entries[@]}" -eq 10 ] || fail "nested directory count at $a"
  for ((b=1; b<=10; b++)); do
    [ -d "$a/$b" ] && [ ! -L "$a/$b" ] || fail "directory $a/$b"
    entries=("$a/$b"/*)
    [ "${#entries[@]}" -eq 10 ] || fail "file count at $a/$b"
    for ((c=1; c<=10; c++)); do
      file="$a/$b/$c"
      [ -f "$file" ] && [ ! -L "$file" ] && [ ! -s "$file" ] || fail "empty regular file $file"
    done
  done
done
echo "VERIFY OK"
"""


def _big_verifier(files):
    """Read all expected zero bytes; a size-only result cannot satisfy proof."""
    script = f"""export LANG=C LC_ALL=C
fail() {{ echo "VERIFY FAIL $*"; exit 1; }}
shopt -s nullglob dotglob
entries=(*)
[ "${{#entries[@]}}" -eq {len(files)} ] || fail "root entry count"
"""
    comparisons = []
    for name in files:
        script += f"""[ -f {name} ] && [ ! -L {name} ] || fail "regular file {name}"
[ "$(wc -c < {name} | tr -d ' ')" = 67108864 ] || fail "{name} size"
"""
        comparisons.append(f'cmp -n 67108864 {name} /dev/zero >/dev/null || fail "{name} zero contents"\n')
    return script + "".join(comparisons) + 'echo "VERIFY OK"\n'


def _files_body(count):
    return f"for i in $(seq 1 {count}); do echo $i > f$i; done" if count else "true"


def _random_verifier():
    return f"""export LANG=C LC_ALL=C
fail() {{ echo "VERIFY FAIL $*"; exit 1; }}
shopt -s nullglob dotglob
entries=(*)
[ "${{#entries[@]}}" -eq 1 ] && [ -f rand ] && [ ! -L rand ] || fail "rand only"
sum=$(openssl dgst -sha256 < rand | awk '{{print $NF}}') || fail "digest"
[ "$sum" = {RANDOM_SHA256} ] || fail "rand contents"
echo "VERIFY OK"
"""


def _pg62_case(case_id, verify):
    """Cases added for layerfs-project#62; their bodies are this suite's own."""
    setup = followup = ""
    budget = None
    if case_id == "C13":
        body, followup = "echo 1 > a", "echo 2 > b"
        verifier = """export LANG=C LC_ALL=C
shopt -s nullglob dotglob
entries=(*)
[ "${#entries[@]}" -eq 2 ] && [ "$(cat a)" = 1 ] && [ "$(cat b)" = 2 ] || { echo "VERIFY FAIL a/b"; exit 1; }
echo "VERIFY OK"
"""
    elif case_id in SWEEP:
        body = _files_body(SWEEP[case_id])
        verifier = (
            _numbered_verifier(SWEEP[case_id]) if SWEEP[case_id] else _empty_verifier()
        )
        # Declared before execution: 10,000 files take the 25 s exception.
        budget = 25 if SWEEP[case_id] >= 10_000 else None
    elif case_id == "C17":
        setup, body = RANDOM_SETUP, "cat rand > /dev/null"
        verifier = _random_verifier()
    else:  # C18
        setup, body = _files_body(1000), "stat f{1..1000} > /dev/null"
        verifier = _numbered_verifier(1000)
    command = f"{{ {body}; }} >/dev/null"
    result = {
        "id": case_id,
        "body": body,
        "setup": setup,
        "command": command,
        "exec_argv": ["/bin/bash", "-o", "pipefail", "-c", command],
        "environment": dict(ENVIRONMENT),
        "starting_view": "committed-base" if setup else "empty",
        "verifier": verifier if verify else None,
        "provenance": {
            "origin": "https://github.com/Ephemeral-AI-Lab/layerfs-project/issues/62",
            "source_definition": f"fs-bench-quick {case_id}",
            "workload_version": PG62_VERSION,
            "body_sha256": sha256(body),
            "setup_sha256": sha256(setup),
            "command_sha256": sha256(command),
        },
    }
    if followup:
        result["followup_command"] = f"{{ {followup}; }} >/dev/null"
        result["followup_argv"] = [
            "/bin/bash",
            "-o",
            "pipefail",
            "-c",
            result["followup_command"],
        ]
        result["provenance"]["followup_command_sha256"] = sha256(
            result["followup_command"]
        )
    if budget:
        result["performance_budget_s"] = budget
        result["provenance"]["performance_budget_s"] = budget
    if setup:
        result["setup_command"] = f"{{ {setup}; }} >/dev/null"
        result["setup_argv"] = ["/bin/bash", "-o", "pipefail", "-c", result["setup_command"]]
        result["provenance"]["setup_command_sha256"] = sha256(result["setup_command"])
    if verify:
        result["provenance"]["verification"] = {
            "version": f"{case_id.lower()}-exact-v1",
            "sha256": sha256(verifier),
        }
    return result


def get_case(case_id, verify=False):
    """Return fresh JSON-serializable data for the current implemented cell.

    Future registered rows intentionally have no executable definition yet.
    Request proof explicitly; default callers neither build nor receive it.
    """
    if case_id not in CASE_IDS:
        raise ValueError(f"Unknown cell: {case_id}")
    if case_id not in IMPLEMENTED_CASES:
        raise NotImplementedError(f"{case_id} is registered but not implemented yet")
    if case_id in PG62_CASES:
        return _pg62_case(case_id, verify)
    setup = ""
    body = "for i in $(seq 1 1000); do echo $i > f$i; done"
    if case_id == "C02":
        body += "; for i in $(seq 1 1000); do stat f$i; done"
    elif case_id == "C03":
        body += "; rm f*"
    elif case_id in ("C04", "C05"):
        body = "for a in $(seq 1 10); do for b in $(seq 1 10); do mkdir -p $a/$b; for c in $(seq 1 10); do touch $a/$b/$c; done; done; done"
        if case_id == "C05":
            body += "; find . -type f | wc -l"
    elif case_id in ("C06", "C07", "C08"):
        body = "dd if=/dev/zero of=big bs=1M count=64 status=none"
        if case_id == "C07":
            body += "; cp big big2"
        elif case_id == "C08":
            body += "; cat big > /dev/null"
    elif case_id in ("C09", "C10"):
        body = "cat big > /dev/null" if case_id == "C09" else "cp big big2"
        setup = "dd if=/dev/zero of=big bs=1M count=64 status=none"
    elif case_id == "C11":
        setup = "dd if=/dev/zero of=big bs=1M count=64 status=none"
        body = setup + " conv=notrunc"
    elif case_id == "C12":
        body = "git init -q; for i in $(seq 1 100); do echo $i > f$i; done; git add -A; git -c user.email=a@b -c user.name=a commit -qm init"
    command = f"{{ {body}; }} >/dev/null"
    result = {
        "id": case_id,
        "body": body,
        "setup": setup,
        "command": command,
        "exec_argv": ["/bin/bash", "-o", "pipefail", "-c", command],
        "environment": dict(ENVIRONMENT),
        "starting_view": "committed-base" if setup else "empty",
        "verifier": None,
        "provenance": {
            "repository": "https://github.com/Ephemeral-AI-Lab/layerfs",
            "source_commit": SOURCE_COMMIT,
            "source_path": SOURCE_PATH,
            "source_blob": SOURCE_BLOB,
            "source_definition": f"CF.{case_id} (MK1000), command({case_id}), VERIFIER.{case_id}",
            "workload_version": "R7-byte-exact-v1",
            "body_sha256": sha256(body),
            "setup_sha256": sha256(setup),
            "command_sha256": sha256(command),
            "source_verifier_sha256": "829c5428fab703bc31a1d6805b4b781864be265c3fec4834bbf9062727d919a0",
        },
    }
    if case_id == "C03":
        result["provenance"]["source_verifier_sha256"] = (
            "f6140622c8ba65c8bd0f7f447457b06ea71b3109c8e6383138172e73628f22a4"
        )
    elif case_id in ("C04", "C05"):
        result["provenance"]["source_definition"] = f"CF.{case_id} (MKTREE), command({case_id}), VERIFIER.{case_id}"
        result["provenance"]["source_verifier_sha256"] = (
            "b91a2b57cd4c8f1ebd447973f6ee5dffa91023260da315b43f63c7409088afeb"
        )
    elif case_id in ("C06", "C08"):
        result["provenance"]["source_definition"] = f"CF.{case_id} (DD), command({case_id}), VERIFIER.{case_id}"
        result["provenance"]["source_verifier_sha256"] = (
            "eaebfbfc2ee0099f8c7681d55cee0e775215bab47f29e6af557f8b74aa3fd599"
        )
    elif case_id == "C07":
        result["provenance"]["source_definition"] = "CF.C07 (DD), command(C07), VERIFIER.C07"
        result["provenance"]["source_verifier_sha256"] = (
            "3e0bd7b2461821ce354727e940cc7f32e881a1a9cfb31e25a4ee764ab2264305"
        )
    elif case_id == "C09":
        result["provenance"]["source_definition"] = "CF.C09 (read + DD setup), command(C09), VERIFIER.C09"
        result["provenance"]["source_verifier_sha256"] = (
            "eaebfbfc2ee0099f8c7681d55cee0e775215bab47f29e6af557f8b74aa3fd599"
        )
    elif case_id == "C10":
        result["provenance"]["source_definition"] = "CF.C10 (copy + DD setup), command(C10), VERIFIER.C10"
        result["provenance"]["source_verifier_sha256"] = (
            "3e0bd7b2461821ce354727e940cc7f32e881a1a9cfb31e25a4ee764ab2264305"
        )
    elif case_id == "C11":
        result["provenance"]["source_definition"] = "CF.C11 (DD conv=notrunc + DD setup), command(C11), VERIFIER.C11"
        result["provenance"]["source_verifier_sha256"] = (
            "eaebfbfc2ee0099f8c7681d55cee0e775215bab47f29e6af557f8b74aa3fd599"
        )
    elif case_id == "C12":
        result["provenance"]["source_definition"] = "CF.C12 (Git + 100 numbered files), command(C12), VERIFIER.C12"
        result["provenance"]["source_verifier_sha256"] = (
            "e6228c3cfb9a59c9d455532ce443882f56d5168a92181be8f78ca0f631e19da6"
        )
    if setup:
        result["setup_command"] = f"{{ {setup}; }} >/dev/null"
        result["setup_argv"] = ["/bin/bash", "-o", "pipefail", "-c", result["setup_command"]]
        result["provenance"]["setup_command_sha256"] = sha256(result["setup_command"])
    if verify:
        result["verifier"] = _numbered_verifier(1000)
        result["provenance"]["verification"] = {
            "version": "numbered-exact-v1",
            "source": f"VERIFIER.{case_id} -> CHECKS.numbered at the pinned source",
            "change": "Exact entry/type checks replace checksum-only name comparison",
            "sha256": sha256(result["verifier"]),
        }
        if case_id == "C03":
            result["verifier"] = _empty_verifier()
            result["provenance"]["verification"] = {
                "version": "empty-exact-v1",
                "source": "VERIFIER.C03 -> CHECKS.empty at the pinned source",
                "change": "Bash includes hidden entries without launching a recursive scan",
                "sha256": sha256(result["verifier"]),
            }
        elif case_id in ("C04", "C05"):
            result["verifier"] = _tree_verifier()
            result["provenance"]["verification"] = {
                "version": "tree-exact-v1",
                "source": f"VERIFIER.{case_id} -> CHECKS.tree at the pinned source",
                "change": "Exact paths/types and hidden-entry checks replace checksum-only names",
                "sha256": sha256(result["verifier"]),
            }
        elif case_id in ("C06", "C07", "C08", "C09", "C10", "C11"):
            result["verifier"] = _big_verifier(("big", "big2") if case_id in ("C07", "C10") else ("big",))
            result["provenance"]["verification"] = {
                "version": "big-exact-v1",
                "source": f"VERIFIER.{case_id} -> CHECKS.{'big2' if case_id in ('C07', 'C10') else 'big'} at the pinned source",
                "change": "Exact entry/type checks replace checksum-only names; full byte comparison retained",
                "sha256": sha256(result["verifier"]),
            }
        elif case_id == "C12":
            result["verifier"] = _git_verifier()
            result["provenance"]["verification"] = {
                "version": "git-exact-v1",
                "source": "VERIFIER.C12 -> CHECKS.git at the pinned source",
                "change": "Exact names/types/content checks; commit/tracking/status assertions retained",
                "sha256": sha256(result["verifier"]),
            }
    return result
