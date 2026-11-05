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
            f"PJDFSTEST_IDENTITY uid=501 gid=20\n1..{count}\n"
            + "\n".join(f"ok {number}{suffix}" for number in range(1, count + 1))
            + "\nResult: PASS\n"
        )

    def test_frozen_scripts_and_counts(self):
        for case_id in cases.CASE_IDS:
            self.assertFalse(cases.get_case(case_id)["requires_root"])
            self.assertNotIn("setup_argv", cases.get_case(case_id))
            self.assertEqual(cases.get_case(case_id)["setup"], "")
            self.assertTrue(cases.get_case(case_id)["requires_nonroot"])
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
        self.assertEqual(
            {key: result[key] for key in ["pass", "fail", "skip", "todo"]},
            result["tap"],
        )

    def test_effective_identity_is_observed_and_nonroot(self):
        result = cases.parse_result("P01", self.output())
        self.assertEqual(
            result["execution_identity"],
            {"effective_uid": 501, "effective_gid": 20, "switched": False},
        )
        for output in [
            self.output().replace("PJDFSTEST_IDENTITY uid=501 gid=20\n", ""),
            self.output().replace("uid=501", "uid=0"),
            self.output().replace("gid=20", "gid=0"),
            "PJDFSTEST_IDENTITY uid=501 gid=20\n" + self.output(),
        ]:
            with self.assertRaises(ValueError):
                cases.parse_result("P01", output)

    def test_unmodified_subset_and_no_identity_switch(self):
        expected_scripts = {
            "P01": "open/04.t",
            "P02": "rename/18.t",
            "P03": "chmod/02.t",
            "P04": "symlink/00.t",
        }
        self.assertEqual(cases.SCRIPTS, expected_scripts)
        self.assertEqual(cases.PLANS, {"P01": 4, "P02": 6, "P03": 5, "P04": 14})
        for case_id in cases.CASE_IDS:
            case = cases.get_case(case_id)
            self.assertEqual(
                case["provenance"]["workload_version"],
                "fixed-posix-tap-unprivileged-subset-v2",
            )
            self.assertNotIn("sudo", case["body"])
            self.assertNotIn("setuid", case["body"])
            self.assertIn("id -u", case["body"])
            self.assertIn("id -g", case["body"])
            self.assertIsNone(case["verifier"])
