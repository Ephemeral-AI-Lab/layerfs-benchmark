"""fs-storage-micro workload, command and report contracts; no LayerFS calls."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared/src"))
sys.path.insert(0, str(ROOT / "fs-storage-micro/src"))
import cases  # noqa: E402
import references  # noqa: E402
import report  # noqa: E402
import storage  # noqa: E402

gen = cases.gen


class InDirectory:
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory()

    def __enter__(self):
        self.previous = os.getcwd()
        os.chdir(self.temporary.name)
        return Path(self.temporary.name)

    def __exit__(self, *exc):
        os.chdir(self.previous)
        self.temporary.cleanup()


class PlanTests(unittest.TestCase):
    def test_commit_counts_match_the_spec(self):
        counts = {case: len(plan) for case, plan in gen.PLAN.items()}
        self.assertEqual(counts, {"M01": 1, "M02": 2, "M03": 21, "M04": 21, "M05": 21, "M06": 6, "M07": 3, "M08": 12})
        self.assertEqual(cases.CASE_IDS, tuple(f"M0{i}" for i in range(1, 9)))
        self.assertEqual(len(gen.PLAN["M02"][1]), 10)

    def test_streams_are_deterministic(self):
        a, b = gen.Draws("x"), gen.Draws("x")
        self.assertEqual([a.below(97) for _ in range(500)], [b.below(97) for _ in range(500)])
        self.assertEqual(gen.Text("t").lines_to(5000), gen.Text("t").lines_to(5000))
        self.assertEqual(len(gen.Text("t").lines_to(5000)), 5000)
        self.assertEqual(sum(gen.m02_sizes()), 50_000_000)

    def test_write_methods(self):
        inodes = {}
        for case in ("M03", "M04", "M05"):
            with InDirectory() as root:
                gen.step(case, "create")
                before = {p.name: p.stat().st_ino for p in root.rglob("*.txt")}
                first = (root / "d00" / ("f000.v00.txt" if case == "M05" else "f000.txt")).read_bytes()
                gen.step(case, "edit:01")
                after = {p.name: p.stat().st_ino for p in root.rglob("*.txt")}
                if case == "M05":
                    self.assertTrue(all(n.endswith(".v01.txt") for n in after))
                    second = (root / "d00" / "f000.v01.txt").read_bytes()
                else:
                    self.assertEqual(set(before), set(after))
                    second = (root / "d00" / "f000.txt").read_bytes()
                inodes[case] = before.get("f000.txt") == after.get("f000.txt")
                changed = sum(x != y for x, y in zip(first.split(b"\n"), second.split(b"\n")))
                lines = first.count(b"\n")
                self.assertEqual(changed, max(1, round(lines * 0.01)))
                self.assertEqual(len(list(root.rglob("*.tmp"))), 0)
        self.assertTrue(inodes["M03"])   # same inode (O_TRUNC)
        self.assertFalse(inodes["M04"])  # temp + rename

    def test_m03_family_has_identical_content(self):
        digests = []
        for case in ("M03", "M05"):
            with InDirectory() as root:
                gen.step(case, "create")
                gen.step(case, "edit:01")
                digests.append(sorted(references.file_sha256(p) for p in root.rglob("*.txt")))
        self.assertEqual(digests[0], digests[1])

    def test_generator_manifest_matches_shared_manifest(self):
        with InDirectory() as root:
            gen.step("M03", "create")
            os.symlink("d00/f000.txt", "link")
            self.assertEqual(gen.manifest("."), references.manifest(root))

    def test_m08_database_and_churn(self):
        with InDirectory() as root:
            gen.step("M08", "create")
            size = (root / "data.db").stat().st_size
            self.assertGreater(size, 30 * gen.MiB)
            gen.step("M08", "update:01")
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["data.db"])


class CommandTests(unittest.TestCase):
    def test_step_command_checks_generator_hash(self):
        command = cases.step_command("M03", "edit:05")
        self.assertIn(cases.GEN_SHA256, command)
        self.assertIn("sha256sum -c --quiet", command)
        self.assertTrue(command.endswith("python3 /opt/fs-storage-micro/gen.py step M03 edit:05"))
        with self.assertRaises(ValueError):
            cases.step_command("M03", "edit:5; rm -rf /")

    def test_spec_is_bounded_and_complete(self):
        config = {"empty_source": "/e", "machines": {"docker": {"name": "docker"}},
                  "postgresql": {"password_env": "PW"}, "storage": {"allocated": {"volume": "v", "image": "i"}}}
        for case in cases.CASE_IDS:
            spec = cases.spec(case, "postgresql", "fsm-x", config, "postgresql://u@h:1/d")
            commits = [s for s in spec["steps"] if s["op"] == "commit"]
            self.assertEqual(len(commits), len(gen.PLAN[case]))
            self.assertTrue(all(s.get("timeout_s", 60) <= storage.MAX_COMMAND_S for s in spec["steps"]))
            self.assertEqual(spec["steps"][-1], {"op": "close", "sandbox": "fsm-x"})
            self.assertEqual(spec["stores"][0]["url"], "postgresql://u@h:1/d")
            self.assertEqual(len(spec["verify"]), 1)

    def test_oracle_check(self):
        cases.ORACLE.setdefault("M01", {"sha256": "a", "entries": 1, "files": 1, "bytes": 1})
        check = cases.check_manifest("M01")
        check({"stdout": json.dumps(cases.ORACLE["M01"]) + "\n"})
        with self.assertRaises(ValueError):
            check({"stdout": json.dumps({**cases.ORACLE["M01"], "sha256": "b"})})

    def test_pins_match_the_generator(self):
        path = ROOT / "fs-storage-micro/src/pins.json"
        if path.exists():
            pins = json.loads(path.read_text())
            self.assertEqual(pins["gen_sha256"], cases.GEN_SHA256)
            self.assertEqual(pins["workload_version"], cases.WORKLOAD_VERSION)
            self.assertEqual(set(pins["oracle"]), set(cases.CASE_IDS))


class ReportTests(unittest.TestCase):
    def test_outcome_and_tables(self):
        def row(case, backend, repeat=1, stored=(100, 5)):
            commits = [{"id": f"{case}{i}", "parent": None, "logical": 10, "new_canonical": 1,
                        "new_stored": stored[0], "new_metadata": stored[1]} for i in range(len(gen.PLAN[case]))]
            return {
                "id": f"{case}/docker/{backend}" + (f"/r{repeat}" if repeat > 1 else ""),
                "case": case, "backend": backend, "repeat": repeat,
                "execution": "PASS", "verification": "PASS", "cleanup": "COMPLETE",
                "probes": {"floor": {"s": {"backend": backend, "total_bytes": 1000, "file_bytes": 1000, "wal_bytes": 0}},
                           "final": {"s": {"backend": backend, "total_bytes": 9000, "file_bytes": 9000, "wal_bytes": 0}}},
                "histories": [{"project": "s/p", "branch": "lane", "commits": commits}],
            }
        rows = [row(c, b) for c in cases.CASE_IDS for b in ("sqlite", "postgresql")]
        rows.append(row("M01", "sqlite", 2))
        state = {"source_sha": "6d820c756b9b12541ac84af7b88467069f31bcbf", "rows": {r["id"]: r for r in rows}}
        config = {"machines": {"docker": {"name": "docker"}}, "artifacts": {}}
        text = report.render(state, config, cleanup="COMPLETE")
        self.assertTrue(text.splitlines()[2].startswith("**16 of 16 fs-storage-micro rows PASS"))
        self.assertIn("byte-identical", text)
        self.assertIn("| M01 | SQLite | PASS | 1,000 | 9,000 | 8,000 |", text)
        self.assertLess(text.index("### M01"), text.index("### M08"))


if __name__ == "__main__":
    unittest.main()
