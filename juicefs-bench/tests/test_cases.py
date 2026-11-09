import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("juicefs_cases", Path(__file__).resolve().parents[1] / "src/cases.py")
cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases)


class Results(unittest.TestCase):
    def sample(self):
        return "Benchmark finished!\n" + cases.HEADER + "\n" + "\n".join(
            f"| {name} | 100.00 {unit} | 0.00 {cost_unit} |"
            for name, unit, cost_unit in cases.METRICS)

    def test_complete_result(self):
        self.assertEqual(len(cases.parse_result("J01", self.sample())["metrics"]), 5)

    def test_incomplete_duplicate_wrong_units_and_wrong_workload(self):
        sample = self.sample()
        for invalid in ("\n".join(sample.splitlines()[:-1]), sample + "\n" + sample.splitlines()[-1],
                        sample.replace("MiB/s", "MB/s"), sample.replace("NumThreads: 4", "NumThreads: 8"),
                        sample.replace("100.00", "nan"), sample.replace("100.00", "0.00")):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                cases.parse_result("J01", invalid)

    def test_workload_exit_and_verification_are_not_silent_success(self):
        with self.assertRaises(ValueError):
            cases.parse_result("J01", self.sample(), exit_code=1)
        with self.assertRaises(ValueError):
            cases.get_case("J01", verify=True)

    def test_cleanup_warning_is_not_silent_success(self):
        with self.assertRaises(ValueError):
            cases.parse_result("J01", self.sample(), stderr="WARNING Failed to cleanup directory")


if __name__ == "__main__":
    unittest.main()
