import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "fsx_cases", Path(__file__).parents[1] / "src" / "cases.py"
)
cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases)


class FsxResultTests(unittest.TestCase):
    def summary(self, text, tool_exit=0):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tool.stdout"
            path.write_text(text)
            result = subprocess.run(
                [sys.executable, "-c", cases.SUMMARY, str(tool_exit), str(path)],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout

    def complete_output(self, operation="READ"):
        return "All 1000 operations completed A-OK!\n" + "".join(
            f"{i}({i % 256:3d} mod 256): {operation} 0x0 thru 0x1\n"
            for i in range(1, 1001)
        )

    def test_completed_effective_counts_and_compact_output(self):
        output = self.summary(self.complete_output())
        result = cases.parse_result("X01", output)
        self.assertEqual(result["operations_effective"], 1000)
        self.assertLess(len(output), 2048)

    def test_success_banner_without_records_is_not_pass(self):
        with self.assertRaises(ValueError):
            cases.parse_result(
                "X01", self.summary("All 1000 operations completed A-OK!\n")
            )

    def test_zero_effective_work_is_not_pass(self):
        with self.assertRaises(ValueError):
            cases.parse_result("X01", self.summary(self.complete_output("SKIPPED")))

    def test_tool_exit_failure_survives_success_banner(self):
        with self.assertRaises(ValueError):
            cases.parse_result("X01", self.summary(self.complete_output(), tool_exit=1))

    def test_frozen_flags_and_optional_proof(self):
        case = cases.get_case("X01")
        self.assertIn("-T -P", case["body"])
        self.assertNotIn("-n", cases.TOOL_ARGV)
        self.assertEqual(case["supported_platforms"], ["linux"])
        self.assertIsNone(case["verifier"])
        with self.assertRaises(NotImplementedError):
            cases.get_case("X01", verify=True)
