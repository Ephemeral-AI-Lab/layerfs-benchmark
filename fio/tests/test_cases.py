"""Argument and result contracts; subprocess tests exercise only tiny proof data."""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "fio_cases", Path(__file__).resolve().parents[1] / "src/cases.py"
)
cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases)


def response(case_id="F01"):
    rw, size, block = cases.PROFILES[case_id]
    direction = "read" if "read" in rw else "write"
    opposite = "write" if direction == "read" else "read"
    options = {
        key[2:]: value
        for argument in cases.arguments(case_id, rw, size, block)
        if "=" in argument
        for key, value in [argument.split("=", 1)]
    }
    return {
        "fio version": cases.TOOL_VERSION,
        "jobs": [
            {
                "jobname": case_id,
                "error": 0,
                "job options": options,
                opposite: {"io_bytes": 0},
                direction: {
                    "io_bytes": size,
                    "total_ios": size // block,
                    "short_ios": 0,
                    "drop_ios": 0,
                    "runtime": 10,
                    "bw_bytes": size * 100,
                    "iops": size // block * 100,
                    "clat_ns": {"min": 1, "max": 10, "mean": 5, "stddev": 2},
                },
            }
        ],
    }


class FioCasesTests(unittest.TestCase):
    def test_frozen_sizes_patterns_and_no_implicit_read_setup(self):
        self.assertEqual(cases.CASE_IDS, ("F01", "F02", "F03", "F04"))
        for case_id in cases.CASE_IDS:
            case = cases.get_case(case_id)
            command = case["command"]
            for argument in (
                "--ioengine=sync",
                "--iodepth=1",
                "--numjobs=1",
                "--thread=1",
                "--direct=0",
                "--fallocate=none",
                "--create_fsync=0",
                "--fsync=0",
                "--fdatasync=0",
                "--end_fsync=0",
                "--fsync_on_close=0",
                "--randseed=1",
            ):
                self.assertIn(argument, command)
            self.assertNotIn("--time_based=1", command)
            self.assertIsNone(case["verifier"])
            if case_id in ("F02", "F04"):
                self.assertIn("--allow_file_create=0", command)
                self.assertIn("--rw=write", case["setup"])
                self.assertIn("--buffer_pattern=0x5a", case["setup"])
                self.assertEqual(case["starting_view"], "committed-base")
            else:
                self.assertEqual(case["setup"], "")
            self.assertEqual(
                case["provenance"]["command_sha256"], cases.sha256(command)
            )

    def test_parse_exact_completed_pass_and_upstream_units(self):
        for case_id in cases.CASE_IDS:
            metrics = cases.parse_result(case_id, json.dumps(response(case_id)))
            self.assertEqual(
                metrics["total_ios"], 64 if case_id in ("F01", "F02") else 2048
            )
            self.assertEqual(metrics["completion_latency_ns"]["mean"], 5)
            self.assertTrue(metrics["completed_pass"])

    def test_failed_malformed_partial_and_zero_work_are_rejected(self):
        for stdout in ("", "not JSON", "{}", "[]"):
            with self.assertRaises(ValueError):
                cases.parse_result("F01", stdout)
        with self.assertRaises(ValueError):
            cases.parse_result("F01", json.dumps(response()), exit_code=1)
        mutations = [
            lambda value: value["jobs"][0].update(error=5),
            lambda value: value["jobs"][0]["write"].update(io_bytes=0),
            lambda value: value["jobs"][0]["write"].update(total_ios=63),
            lambda value: value["jobs"][0]["write"].update(short_ios=1),
            lambda value: value["jobs"][0]["write"].update(iops=float("nan")),
            lambda value: value["jobs"][0]["job options"].update(ioengine="libaio"),
            lambda value: value["jobs"].append(copy.deepcopy(value["jobs"][0])),
            lambda value: value["jobs"][0].update(read=None),
        ]
        for mutate in mutations:
            value = response()
            mutate(value)
            with self.assertRaises(ValueError):
                cases.parse_result("F01", json.dumps(value))

    def test_optional_oracle_checks_every_byte_and_rejects_extras(self):
        with patch.dict(cases.PROFILES, {"F01": ("write", 16, 4)}):
            verifier = cases.get_case("F01", verify=True)["verifier"]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fio.data"
            path.write_bytes(b"Z" * 16)
            command = ["/bin/bash", "-o", "pipefail", "-c", verifier]
            self.assertEqual(
                subprocess.run(
                    command, cwd=temporary, capture_output=True, timeout=2
                ).returncode,
                0,
            )
            path.write_bytes(b"Z" * 15 + b"Y")
            self.assertNotEqual(
                subprocess.run(
                    command, cwd=temporary, capture_output=True, timeout=2
                ).returncode,
                0,
            )
            path.write_bytes(b"Z" * 16)
            (Path(temporary) / ".extra").touch()
            self.assertNotEqual(
                subprocess.run(
                    command, cwd=temporary, capture_output=True, timeout=2
                ).returncode,
                0,
            )


if __name__ == "__main__":
    unittest.main()
