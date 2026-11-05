"""Builds the benchmark indexes from the published reports.

Each benchmark is a top-level folder whose README.md starts with

    # <name> — <what it checks>
    > group: <filesystem|transfer> · measures: <value>, <value>

Reports are `result/<date>/<benchmark>/<full-layerfs-sha>/report.md`; a
report's outcome is its first bold sentence. This script rewrites the
generated blocks only:

- root README.md, between `<!-- index:begin -->` and `<!-- index:end -->`:
  one table per group, each benchmark with its latest run;
- each benchmark README.md, between `<!-- runs:begin -->` and
  `<!-- runs:end -->`: every run, newest first.

A report whose outcome starts with "Superseded" is listed but never latest.

    python3 shared/src/readme_index.py          # rewrite the blocks
    python3 shared/src/readme_index.py --check  # exit 1 if any is stale
"""

import argparse
import re
import sys
from pathlib import Path

GROUPS = {
    "filesystem": ("Filesystem", "The LayerFS engine: Workspaces, file I/O, metadata and Commit."),
    "transfer": ("Transfer", "Connect: moving Stores between a home and a bucket."),
}
MEASURES = ("correctness", "speed", "storage", "recovery")
SKIP = {"shared", "result"}
HEADER = re.compile(r"^> group: (\S+) · measures: (.+)$")
TITLE = re.compile(r"^# (\S+) — (.+)$")
BOLD = re.compile(r"\*\*(.+?)\*\*", re.S)
LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")


class IndexProblem(Exception):
    pass


def benchmarks(root):
    """`{name: {group, measures, checks}}` from each benchmark README."""
    found = {}
    for readme in sorted(root.glob("*/README.md")):
        name = readme.parent.name
        if name in SKIP or name.startswith("."):
            continue
        lines = readme.read_text().splitlines()
        title = TITLE.match(lines[0]) if lines else None
        header = next((HEADER.match(line) for line in lines[1:4] if HEADER.match(line)), None)
        if not title or not header or title.group(1) != name:
            raise IndexProblem(f"{readme}: needs '# {name} — …' then '> group: … · measures: …'")
        group, measures = header.group(1), [m.strip() for m in header.group(2).split(",")]
        if group not in GROUPS:
            raise IndexProblem(f"{readme}: group {group!r} is not one of {', '.join(GROUPS)}")
        unknown = [m for m in measures if m not in MEASURES]
        if unknown or not measures:
            raise IndexProblem(f"{readme}: measures {unknown or measures} not in {', '.join(MEASURES)}")
        found[name] = {"group": group, "measures": measures, "checks": title.group(2), "readme": readme}
    return found


def outcome(report):
    """The report's first bold sentence, links reduced to their text."""
    match = BOLD.search(report.read_text())
    if not match:
        raise IndexProblem(f"{report}: no bold outcome sentence")
    text = LINK.sub(r"\1", " ".join(match.group(1).split()))
    return text.rstrip(".")


def runs(root):
    """`{benchmark: [run, …]}` newest first; a run is `{date, sha, outcome, path}`."""
    found = {}
    for report in root.glob("result/*/*/*/report.md"):
        date, name, sha = report.parts[-4:-1]
        found.setdefault(name, []).append({"date": date, "sha": sha, "outcome": outcome(report), "path": report.relative_to(root)})
    for items in found.values():
        items.sort(key=lambda r: (r["date"], not r["outcome"].startswith("Superseded")), reverse=True)
    return found


def latest(items):
    current = [r for r in items if not r["outcome"].startswith("Superseded")]
    return current[0] if current else None


def root_block(found, all_runs):
    out = []
    for group, (title, about) in GROUPS.items():
        names = [n for n, b in found.items() if b["group"] == group]
        if not names:
            continue
        out += [f"## {title}", "", about, "", "| Benchmark | Measures | What it checks | Latest run |", "| --- | --- | --- | --- |"]
        for name in names:
            b, last = found[name], latest(all_runs.get(name, []))
            run = f"{last['date']} · `{last['sha'][:8]}` · {last['outcome']} · [report]({last['path']})" if last else "none yet"
            out.append(f"| [{name}]({name}/) | {', '.join(b['measures'])} | {b['checks']} | {run} |")
        out.append("")
    return "\n".join(out).rstrip("\n")


def runs_block(items):
    if not items:
        return "No published runs yet."
    out = ["| Date | LayerFS commit | Outcome | Report |", "| --- | --- | --- | --- |"]
    for r in items:
        out.append(f"| {r['date']} | `{r['sha'][:10]}` | {r['outcome']} | [report](../{r['path']}) |")
    return "\n".join(out)


def replace(path, tag, body):
    """`path`'s text with its `tag` block replaced by `body`."""
    text = path.read_text()
    begin, end = f"<!-- {tag}:begin -->", f"<!-- {tag}:end -->"
    if text.count(begin) != 1 or text.count(end) != 1:
        raise IndexProblem(f"{path}: needs exactly one {begin} … {end} block")
    head, rest = text.split(begin)
    _, tail = rest.split(end)
    return f"{head}{begin}\n{body}\n{end}{tail}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report stale blocks, write nothing")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args(argv)
    try:
        found, all_runs = benchmarks(args.root), runs(args.root)
        orphans = sorted(set(all_runs) - set(found))
        if orphans:
            raise IndexProblem(f"reports for benchmarks with no README header: {', '.join(orphans)}")
        targets = [(args.root / "README.md", replace(args.root / "README.md", "index", root_block(found, all_runs)))]
        targets += [(b["readme"], replace(b["readme"], "runs", runs_block(all_runs.get(n, [])))) for n, b in found.items()]
    except IndexProblem as error:
        print(f"readme_index: {error}", file=sys.stderr)
        return 2
    stale = [path for path, text in targets if path.read_text() != text]
    if args.check:
        for path in stale:
            print(f"stale: {path.relative_to(args.root)}")
        return 1 if stale else 0
    for path, text in targets:
        path.write_text(text)
    print(f"readme_index: {len(stale)} file(s) updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
