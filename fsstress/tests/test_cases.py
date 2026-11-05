import errno
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "fsstress_cases", Path(__file__).parents[1] / "src" / "cases.py"
)
cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases)


class FsstressResultTests(unittest.TestCase):
    def summary(self, lines, platform=None):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name, text in [("stdout", "".join(lines)), ("stderr", "")]:
                path = Path(directory) / name
                path.write_text(text)
                paths.append(str(path))
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import sys; sys.platform=" + repr(platform) + "\n"
                        if platform
                        else ""
                    )
                    + cases.SUMMARY,
                    "0",
                    json.dumps(cases.EXPECTED_ERRNOS),
                    json.dumps(list(cases.WEIGHTS)),
                    *paths,
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if not result.stdout.startswith("FSSTRESS_RESULT "):
                self.fail(result.stderr)
            return result.stdout

    def complete_lines(self):
        return [
            "".join(f"{worker}/{number}: stat f0 0\n" for number in range(512))
            for worker in range(2)
        ]

    def test_two_complete_workers_and_compact_summary(self):
        output = self.summary(self.complete_lines())
        result = cases.parse_result("S01", output)
        self.assertEqual(result["operations_effective"], 1024)
        self.assertLess(len(output), 4096)

    def test_parent_success_does_not_hide_incomplete_child(self):
        lines = self.complete_lines()
        lines[1] = ""
        with self.assertRaises(ValueError):
            cases.parse_result("S01", self.summary(lines))

    def test_expected_nonempty_directory_is_reported(self):
        lines = self.complete_lines()
        lines[0] = lines[0].replace(
            "0/0: stat f0 0", f"0/0: rmdir d0 {errno.ENOTEMPTY}"
        )
        result = cases.parse_result("S01", self.summary(lines))
        self.assertEqual(result["operations_expected_errors"], 1)
        self.assertEqual(result["errno_counts"], {"rmdir:ENOTEMPTY": 1})

    def test_io_error_is_not_accepted_as_expected(self):
        lines = self.complete_lines()
        lines[0] = lines[0].replace("0/0: stat f0 0", "0/0: stat f0 5")
        with self.assertRaises(ValueError):
            cases.parse_result("S01", self.summary(lines))

    def test_zero_work_no_object_slots_are_not_pass(self):
        lines = [
            "".join(f"{worker}/{number}: stat - no entries\n" for number in range(512))
            for worker in range(2)
        ]
        with self.assertRaises(ValueError):
            cases.parse_result("S01", self.summary(lines))

    def test_darwin_dangling_symlink_link_exception_is_narrow(self):
        lines = self.complete_lines()
        lines[0] = lines[0].replace("0/0: stat f0 0", "0/0: link d0/la d0/lb 2")
        result = cases.parse_result("S01", self.summary(lines, platform="darwin"))
        self.assertEqual(result["operations_expected_errors"], 1)
        self.assertEqual(result["errno_counts"], {"link:ENOENT": 1})
        with self.assertRaises(ValueError):
            cases.parse_result("S01", self.summary(lines, platform="linux"))
        ordinary = self.complete_lines()
        ordinary[0] = ordinary[0].replace("0/0: stat f0 0", "0/0: link d0/fa d0/fb 2")
        with self.assertRaises(ValueError):
            cases.parse_result("S01", self.summary(ordinary, platform="darwin"))

    def test_actual_request_lengths_are_reported_not_transferred_bytes(self):
        lines = self.complete_lines()
        lines[0] = lines[0].replace("0/0: stat f0 0", "0/0: write f0 [0,4096] 0")
        result = cases.parse_result("S01", self.summary(lines))
        self.assertEqual(
            result["io_requests"]["write"],
            {"operations": 1, "requested_bytes": 4096, "max_requested_bytes": 4096},
        )
        self.assertIn("not transferred bytes", result["io_request_scope"])

    def test_auxiliary_lines_do_not_double_count(self):
        lines = self.complete_lines()
        lines[0] = lines[0].replace(
            "0/0: stat f0 0", "0/0: creat f0 x:0 0 0\n0/0: creat add id=0,parent=-1"
        )
        result = cases.parse_result("S01", self.summary(lines))
        self.assertEqual(result["operation_counts"]["creat"], 1)
