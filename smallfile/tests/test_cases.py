import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "smallfile_cases", Path(__file__).parents[1] / "src/cases.py"
)
cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases)


class CasesTests(unittest.TestCase):
    OUTPUT = """host = bench,thr = 00,elapsed = 0.5,files = 256,records = 256,status = ok
host = bench,thr = 01,elapsed = 0.6,files = 256,records = 256,status = ok
total threads = 2
total files = 512
100.00% of requested files processed, warning threshold is 70.00%
files/sec = 938.666667
"""

    def test_independent_setup_and_portable_names(self):
        for case_id in cases.CASE_IDS:
            case = cases.get_case(case_id)
            self.assertIn("--as-host bench", case["body"])
            self.assertNotIn("--host-set", case["body"])
            self.assertIn("--stonewall N", case["body"])
            self.assertIn("--verify-read Y", case["body"])
            self.assertIsNone(case["verifier"])
            self.assertEqual(bool(case["setup"]), case_id != "L01")
            output = (
                self.OUTPUT
                if case_id in {"L01", "L02"}
                else self.OUTPUT.replace("records = 256", "records = 0")
            )
            self.assertEqual(cases.parse_result(case_id, output)["files"], 512)

    def test_zero_work_and_nonzero_worker_status_fail_even_exit_zero(self):
        for text in [
            self.OUTPUT.replace("total files = 512", "total files = 0"),
            self.OUTPUT.replace("status = ok", "status = ERR: Input/output error", 1),
            self.OUTPUT.replace("records = 256", "records = 0"),
        ]:
            with self.assertRaises(ValueError):
                cases.parse_result("L01", text)

    def test_short_upstream_interval_preserves_unavailable_rate(self):
        text = self.OUTPUT.replace(
            "files/sec = 938.666667", "WARNING: test must run longer than a millisecond"
        )
        self.assertIsNone(cases.parse_result("L01", text)["files_per_second"])

    def test_setup_create_validates_worker_outcomes(self):
        self.assertEqual(
            cases.parse_setup_result("L02", self.OUTPUT)["operation"], "create"
        )
        with self.assertRaises(ValueError):
            cases.parse_setup_result(
                "L02", self.OUTPUT.replace("records = 256", "records = 0")
            )
