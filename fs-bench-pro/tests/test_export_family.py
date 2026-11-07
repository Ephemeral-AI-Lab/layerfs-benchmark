"""Focused local checks of the export family's harness; these are not samples."""

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))


def load(name):
    spec = importlib.util.spec_from_file_location(f"pro_{name}", SRC / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fixture, cold, run = load("fixture"), load("cold"), load("run")


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "t"
        self.root.mkdir()
        (self.root / "a").write_bytes(b"one")
        (self.root / "d").mkdir()
        os.symlink("../a", self.root / "d" / "l")
        fixture.settle(self.root)

    def test_manifest_is_stable_and_sees_content_mode_and_links(self):
        base = fixture.manifest(self.root)
        self.assertEqual(base, fixture.manifest(self.root))
        (self.root / "a").write_bytes(b"two")
        fixture.settle(self.root)
        changed = fixture.manifest(self.root)
        self.assertNotEqual(base, changed)
        os.chmod(self.root / "a", 0o755)
        self.assertNotEqual(changed, fixture.manifest(self.root))
        os.remove(self.root / "d" / "l")
        os.symlink("a", self.root / "d" / "l")
        self.assertNotEqual(changed, fixture.manifest(self.root))


class ColdTests(unittest.TestCase):
    def test_any_resident_page_or_no_file_is_not_cold(self):
        lines = "0 10 /s/store.sqlite\n3 4 /s/store.sqlite-wal\n"
        with mock.patch.object(cold, "evict_guest", return_value={"files": cold.parse(lines)}):
            self.assertFalse(cold.evict({}, "docker", "s")["cold"])
        with mock.patch.object(cold, "evict_guest", return_value={"files": cold.parse("0 10 /s/store.sqlite\n")}):
            self.assertTrue(cold.evict({}, "docker", "s")["cold"])
        with mock.patch.object(cold, "evict_guest", return_value={"files": []}):
            self.assertFalse(cold.evict({}, "docker", "s")["cold"])

    def test_mincore_counts_pages_of_a_file_just_read(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write(os.urandom(1 << 20))
            f.flush()
            Path(f.name).read_bytes()
            got = cold._mincore(f.name)
        self.assertGreater(got["pages"], 0)
        self.assertGreater(got["resident_pages"], 0)


def receipt(**over):
    r = {
        "case": "E01", "machine": "docker", "execution": "PASS",
        "verification": {"status": "PASS", "wall_s": 0.5},
        "cold": {"cold": True, "control_s": 30.0}, "export": {"wall_ms": 1000.0},
    }
    r.update(over)
    return r


class VerdictTests(unittest.TestCase):
    def test_verdicts(self):
        self.assertEqual(run.verdict(receipt()), "QUALIFIED")  # a slow control is not case time
        self.assertEqual(run.verdict(receipt(execution="FAIL")), "FAIL")
        self.assertEqual(run.verdict(receipt(verification={"status": "FAIL", "wall_s": 0})), "FAIL")
        self.assertEqual(run.verdict(receipt(cold={"cold": False})), "INELIGIBLE")
        self.assertEqual(run.verdict(receipt(export={"wall_ms": 15001.0})), "OVER_BUDGET")
        self.assertEqual(run.verdict(receipt(verification={"status": "PASS", "wall_s": 10.5})), "OVER_BUDGET")


class TimedExportTests(unittest.TestCase):
    def test_progress_is_stamped_and_a_refusal_line_is_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            cli = Path(tmp) / "layerfs"
            cli.write_text(
                "#!/bin/sh\n"
                "echo '{\"progress\":{\"phase\":\"prepare\",\"bytes\":0}}' >&2\n"
                "echo '{\"progress\":{\"phase\":\"export\",\"bytes\":7}}' >&2\n"
                "echo '{\"refusal\":{\"kind\":\"Failed\"}}' >&2\n"
                "exit 125\n"
            )
            cli.chmod(0o755)
            env = {"cli": str(cli), "home": tmp, "xdg_cache": tmp}
            got = run.timed_export(env, "s/p", Path(tmp) / "out")
        self.assertEqual(got["rc"], 125)
        self.assertEqual([p.get("phase") for p in got["progress"]], ["prepare", "export", None])
        self.assertIn("refusal", got["progress"][-1]["line"])
        self.assertTrue(all(p["t_ms"] >= 0 for p in got["progress"]))


if __name__ == "__main__":
    unittest.main()
