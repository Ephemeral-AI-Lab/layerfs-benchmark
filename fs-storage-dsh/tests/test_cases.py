import hashlib
import importlib.util
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))

import cases  # noqa: E402


def load(name):
    spec = importlib.util.spec_from_file_location(f"dsh_{name}", SUITE / "image" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


apply = load("apply")
verify = load("verify")


class Selections(unittest.TestCase):
    def test_selection_shapes(self):
        self.assertEqual(len(cases.SELECTIONS["D10"]), 17)
        self.assertEqual(cases.SELECTIONS["D10"][:3], [1, 11, 21])
        self.assertEqual(cases.SELECTIONS["D10"][-2:], [151, 157])
        self.assertEqual(len(cases.SELECTIONS["D03"]), 53)
        self.assertEqual(cases.SELECTIONS["D03"][-2:], [154, 157])

    def test_steps_start_empty_and_chain(self):
        for case_id in cases.CASE_IDS:
            steps = cases.steps(case_id)
            self.assertEqual(steps[0], (0, 1))
            for (_, b), (c, _) in zip(steps, steps[1:]):
                self.assertEqual(b, c)

    def test_case_commands(self):
        case = cases.get_case("D10")
        self.assertEqual(case["commands"][0], "python3 /opt/fs-storage-dsh/apply.py 0 1")
        self.assertEqual(case["verify_command"], "python3 /opt/fs-storage-dsh/verify.py 157")
        self.assertEqual(case["final_tree"], cases.FINAL_TREES[157])
        self.assertEqual(cases.get_case("D03")["final_state"], 157)
        with self.assertRaises(ValueError):
            cases.get_case("D01")

    def test_final_states_have_pinned_oracles(self):
        for case_id in cases.CASE_IDS:
            final = cases.SELECTIONS[case_id][-1]
            self.assertIn(f"oracles/{final}.json", cases.SEED_FILES)
            self.assertIn(final, cases.ORACLE_SOURCES)

    def test_seed_sources(self):
        self.assertEqual(cases.seed_source("oracles/157.json"), f"oracles/{cases.ORACLE_SOURCES[157]}.json")
        self.assertEqual(cases.seed_source("mapping.json"), "git-snapshots-157-v1/mapping.json")
        self.assertEqual(cases.seed_source("checkpoint-manifest.json"), "checkpoint-manifest.json")
        pack = [p for p in cases.SEED_FILES if p.endswith(".pack")]
        self.assertEqual(cases.SEED_FILES[pack[0]][1], "27c7598c04404730200654a1a4ad8f000d63d41da87531cc6e8f206a4e8133bc")
        self.assertEqual(len(cases.seed_manifest_sha256()), 64)

    def test_parse_apply_and_verify(self):
        line = json.dumps({"from": 0, "to": 1, "created": 3})
        self.assertEqual(cases.parse_apply("noise\n" + line + "\n", 0, 1)["created"], 3)
        with self.assertRaises(ValueError):
            cases.parse_apply(line, 1, 11)
        with self.assertRaises(ValueError):
            cases.parse_apply("", 0, 1)
        good = json.dumps({"state": 157, "entries": 5, "expected": 5, "mismatches": 0})
        self.assertEqual(cases.parse_verify(good, 157)["entries"], 5)
        bad = json.dumps({"state": 157, "entries": 5, "expected": 6, "mismatches": 1})
        with self.assertRaises(ValueError):
            cases.parse_verify(bad, 157)


def blob_store(*contents):
    blobs = {hashlib.sha1(c).hexdigest(): c for c in contents}
    return blobs, blobs.__getitem__


def oid(content):
    return hashlib.sha1(content).hexdigest()


class Apply(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.fsencode(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def path(self, rel):
        return os.path.join(self.root, rel)

    def test_in_place_rewrite_keeps_inode(self):
        a, b = b"version one\n", b"version two, longer\n"
        _, read = blob_store(a, b)
        apply.apply({}, {b"d/f.txt": ("100644", oid(a))}, read, self.root)
        inode = os.stat(self.path(b"d/f.txt")).st_ino
        counts = apply.apply({b"d/f.txt": ("100644", oid(a))}, {b"d/f.txt": ("100644", oid(b))}, read, self.root)
        self.assertEqual(counts["overwritten"], 1)
        self.assertEqual(os.stat(self.path(b"d/f.txt")).st_ino, inode)
        with open(self.path(b"d/f.txt"), "rb") as stream:
            self.assertEqual(stream.read(), b)

    def test_create_remove_type_change_and_empty_dirs(self):
        x, y, target = b"x\n", b"y\n", b"../x"
        _, read = blob_store(x, y, target)
        old = {b"a/x": ("100644", oid(x)), b"gone/y": ("100755", oid(y)), b"l": ("100644", oid(y))}
        apply.apply({}, old, read, self.root)
        self.assertTrue(os.stat(self.path(b"gone/y")).st_mode & stat.S_IXUSR)
        new = {b"a/x": ("100755", oid(x)), b"l": ("120000", oid(target)), b"b/new": ("100644", oid(y))}
        counts = apply.apply(old, new, read, self.root)
        self.assertEqual(counts["removed"], 2)  # gone/y and the file l becoming a link
        self.assertEqual(counts["chmod"], 1)
        self.assertEqual(counts["dirs_removed"], 1)
        self.assertFalse(os.path.exists(self.path(b"gone")))
        self.assertEqual(os.readlink(self.path(b"l")), target)
        self.assertTrue(os.stat(self.path(b"a/x")).st_mode & stat.S_IXUSR)

    def test_file_becomes_directory_and_back(self):
        x, y = b"x\n", b"y\n"
        _, read = blob_store(x, y)
        one = {b"p": ("100644", oid(x))}
        two = {b"p/q": ("100644", oid(y))}
        apply.apply({}, one, read, self.root)
        apply.apply(one, two, read, self.root)
        self.assertTrue(os.path.isdir(self.path(b"p")))
        apply.apply(two, one, read, self.root)
        self.assertTrue(os.path.isfile(self.path(b"p")))

    def test_symlink_retarget(self):
        t1, t2 = b"one", b"two"
        _, read = blob_store(t1, t2)
        apply.apply({}, {b"l": ("120000", oid(t1))}, read, self.root)
        counts = apply.apply({b"l": ("120000", oid(t1))}, {b"l": ("120000", oid(t2))}, read, self.root)
        self.assertEqual(counts["relinked"], 1)
        self.assertEqual(os.readlink(self.path(b"l")), t2)


class Verify(unittest.TestCase):
    def test_observe_and_compare(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.fsencode(tmp)
            os.makedirs(os.path.join(root, b"d"))
            with open(os.path.join(root, b"d", b"f"), "wb") as stream:
                stream.write(b"hello")
            os.symlink(b"d/f", os.path.join(root, b"l"))
            seen = verify.observe(root)
            oracle = {
                b"d": ("40755", 0, "-"),
                b"d/f": ("100644", 5, hashlib.sha256(b"hello").hexdigest()),
                b"l": ("120000", 3, hashlib.sha256(b"d/f").hexdigest()),
            }
            self.assertEqual(verify.compare(oracle, seen), [])
            oracle[b"extra"] = ("100644", 0, hashlib.sha256(b"").hexdigest())
            self.assertEqual(verify.compare(oracle, seen), [b"extra"])


class SuiteFiles(unittest.TestCase):
    def test_readme_header(self):
        lines = (SUITE / "README.md").read_text().splitlines()
        self.assertTrue(lines[0].startswith("# fs-storage-dsh — "))
        self.assertEqual(lines[1], "> group: filesystem · measures: storage")
        text = "\n".join(lines)
        self.assertIn("<!-- runs:begin -->", text)
        self.assertIn("<!-- runs:end -->", text)

    def test_dockerfile_pins_base_and_checks(self):
        text = (SUITE / "image" / "Dockerfile").read_text()
        self.assertIn("sha256:afa1ef9c27294f9c7298820c06483e6fb1ddafc43a7cc7d6dec8cd2e67abf38e", text)
        self.assertIn("sha256sum -c --quiet pins.sha256", text)
        self.assertIn(cases.FINAL_TREES[157], text)


class Driver(unittest.TestCase):
    def setUp(self):
        import run

        self.run = run
        self.config = {
            "home": "/abs/home",
            "empty_source": "/abs/empty",
            "command_timeout_s": 110,
            "machines": {"docker": {"name": "docker"}},
            "storage": {"docker_volume": "lfs-x-docker-data", "probe_image": "sha256:img"},
            "postgresql": {"password_env": "PW", "databases": {"D10/docker": "postgresql://u@h:1/d"}},
        }

    def campaign(self):
        return type("C", (), {"config": self.config})()

    def test_spec_shape(self):
        row = {"store": "q-s", "sandbox": "q-s", "backend": "sqlite", "cell": "D10"}
        spec = self.run.spec_for(self.campaign(), row, cases.get_case("D10"))
        ops = [s["op"] for s in spec["steps"]]
        self.assertEqual(ops[:2], ["sandbox", "mount"])
        self.assertEqual(ops[2:-2], ["exec", "commit"] * 17)
        self.assertEqual(ops[-2:], ["unmount", "close"])
        self.assertTrue(all(s["timeout_s"] <= 120 for s in spec["steps"]))
        self.assertEqual(spec["allocated"]["volume"], "lfs-x-docker-data")
        self.assertEqual(spec["verify"][0]["command"], cases.verify_command(157))
        spec_pg = self.run.spec_for(self.campaign(), dict(row, backend="postgresql"), cases.get_case("D10"))
        self.assertEqual(spec_pg["stores"][0]["url"], "postgresql://u@h:1/d")
        self.assertIsNone(spec_pg["allocated"])

    def test_apply_results_from_commands(self):
        case = cases.get_case("D10")
        commands = [
            {"phase": f"{i:05d}_exec", "process_exit": 0,
             "stdout": json.dumps({"stdout": json.dumps({"from": a, "to": b}) + "\n"})}
            for i, (a, b) in enumerate(case["steps"])
        ]
        results = self.run.apply_results({"commands": commands}, case)
        self.assertEqual(len(results), 17)
        self.assertEqual(results[-1]["to"], 157)

    def test_matrix_order(self):
        self.assertEqual(self.run.matrix()[0], "D10/docker/sqlite")
        self.assertEqual(self.run.matrix()[-1], "D03/docker/postgresql")


if __name__ == "__main__":
    unittest.main()
