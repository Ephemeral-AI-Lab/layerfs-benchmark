import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "mdtest_cases", Path(__file__).parents[1] / "src/cases.py"
)
cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases)


class CasesTests(unittest.TestCase):
    def output(self, case_id):
        noun, prefix = (
            ("files", "File") if case_id == "M01" else ("directories", "Directory")
        )
        return (
            f"1 tasks, 512 {noun}\nSUMMARY rate (in ops/sec): (of 1 iterations)\n"
            + "\n".join(
                f"{prefix} {name} 100 100 100 0"
                for name in ["creation", "stat", "removal"]
            )
            + "\n-- finished at date --\n"
        )

    def test_both_workload_types(self):
        for case_id in cases.CASE_IDS:
            result = cases.parse_result(case_id, self.output(case_id))
            self.assertEqual(set(result["phase_rates"]), {"create", "stat", "remove"})
            self.assertIsNone(cases.get_case(case_id)["verifier"])

    def test_partial_wrong_count_and_errors_are_failures(self):
        for output in [
            self.output("M01").replace("512 files", "0 files"),
            self.output("M01") + "WARNING: unable to stat\n",
            "",
        ]:
            with self.assertRaises(ValueError):
                cases.parse_result("M01", output)
        with self.assertRaises(ValueError):
            cases.parse_result("M01", self.output("M01"), exit_code=1)

    def test_v2_launcher_is_identical_for_both_cases(self):
        for case_id in cases.CASE_IDS:
            case = cases.get_case(case_id)
            self.assertIn(
                "--host localhost:1 --map-by slot --bind-to none -np 1", case["body"]
            )
            self.assertEqual(case["environment"]["HWLOC_COMPONENTS"], "no_os,stop")
            self.assertEqual(
                case["provenance"]["workload_version"],
                "one-rank-512-create-stat-remove-v2",
            )
            self.assertIn("-n 512 -i 1 -C -T -r -w 0 -e 0", case["body"])
