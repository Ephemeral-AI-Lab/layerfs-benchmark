import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "pjdfstest_cases", Path(__file__).parents[1] / "src/cases.py"
)
cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases)


class CasesTests(unittest.TestCase):
    def output(self, case_id="P01", suffix=""):
        count = cases.PLANS[case_id]
        return (
            f"1..{count}\n"
            + "\n".join(f"ok {number}{suffix}" for number in range(1, count + 1))
            + "\nResult: PASS\n"
        )

    def test_frozen_scripts_and_counts(self):
        for case_id in cases.CASE_IDS:
            self.assertTrue(cases.get_case(case_id)["requires_root"])
            self.assertEqual(
                cases.parse_result(case_id, self.output(case_id))["tap"]["pass"],
                cases.PLANS[case_id],
            )

    def test_assertions_are_not_replaced_by_successful_shell_exit(self):
        with self.assertRaises(ValueError):
            cases.parse_result("P01", self.output().replace("ok 2", "not ok 2"))
        with self.assertRaises(ValueError):
            cases.parse_result("P01", self.output().replace("ok 2\n", ""))

    def test_all_skipped_and_bailout_not_pass(self):
        with self.assertRaises(ValueError):
            cases.parse_result("P01", self.output(suffix=" # SKIP unsupported"))
        with self.assertRaises(ValueError):
            cases.parse_result("P01", self.output() + "Bail out! stopped\n")

    def test_mixed_skip_counts_are_retained(self):
        result = cases.parse_result(
            "P01", self.output().replace("ok 2\n", "ok 2 # SKIP unsupported\n")
        )
        self.assertEqual(result["tap"], {"pass": 3, "fail": 0, "skip": 1, "todo": 0})
