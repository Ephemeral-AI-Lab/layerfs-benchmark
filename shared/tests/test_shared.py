"""Selection, tool-validation and compact reporting contracts; no product calls."""

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared/src"))
import measure
import report


def load_runner():
    provider = types.ModuleType("cases")
    provider.CASE_IDS = ("A01", "A02")
    provider.get_case = lambda cell, verify=False: {
        "exec_argv": ["true"],
        "provenance": {"id": cell},
    }
    provider.parse_result = lambda *args: {"effective_ops": 1}
    spec = importlib.util.spec_from_file_location(
        "shared_unit", ROOT / "shared/src/runner.py"
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"cases": provider}):
        spec.loader.exec_module(module)
    return module


class SharedTests(unittest.TestCase):
    def test_case_list_drives_matrix_and_order(self):
        run = load_runner()
        rows = run.selections()
        self.assertEqual(len(rows), 16)
        self.assertEqual(
            [x["id"] for x in rows[:3]],
            ["A01/native/sqlite", "A01/native/postgresql", "A01/docker/sqlite"],
        )
        self.assertEqual(run.selections(["A02"])[0]["cell"], "A02")

    def test_failed_and_missing_rows_never_terminal_pass(self):
        state = {
            "matrix": [
                {
                    "id": "A01/docker/sqlite",
                    "cell": "A01",
                    "machine": "docker",
                    "backend": "sqlite",
                }
            ],
            "rows": {},
            "source_sha": "a" * 40,
        }
        # Render needs complete matrix; retain a full cell with one failed result.
        run = load_runner()
        state["matrix"] = run.selections(["A01"])
        state["rows"] = {
            x["id"]: {**x, "execution": "PASS", "cleanup": "COMPLETE"}
            for x in state["matrix"]
        }
        state["rows"]["A01/native/sqlite"]["execution"] = "FAIL"
        text = report.render("unit", state, {"cleanup": "COMPLETE"}, {})
        self.assertIn("Diagnostic terminal: INCOMPLETE", text)
        self.assertIn("| native | sqlite | FAIL", text)
        self.assertLess(
            text.index("| docker | sqlite"), text.index("| native | sqlite")
        )

    def test_ratio_requires_success_and_nonzero_baseline(self):
        row = {"execution": "PASS", "timings_ns": {"exec": 50}}
        base = {"execution": "PASS", "timings_ns": {"exec": 100}}
        self.assertEqual(report.ratio(row, base, "exec"), "0.50")
        self.assertEqual(report.ratio(row, {**base, "execution": "FAIL"}, "exec"), "—")
        self.assertEqual(
            report.ratio(row, {"execution": "PASS", "timings_ns": {"exec": 0}}, "exec"),
            "—",
        )

    def test_setup_parser_rejects_exit_zero_worker_failure_before_commit(self):
        run = load_runner()

        def invalid(*args):
            raise ValueError("worker error")

        run.cases.parse_setup_result = invalid
        with tempfile.TemporaryDirectory() as directory:
            config = {
                "campaign_id": "unit",
                "source_sha": "a" * 40,
                "cli": "/fake",
                "home": directory,
                "machines": {"native": {}},
                "empty_source": directory,
            }
            campaign = run.Campaign(config, directory)
            row = campaign.row(run.selections()[0])
            results = [
                {},
                {"ws": "unit:setup"},
                {"exit_code": 0, "stdout": "worker error"},
            ]
            replies = [
                {
                    "process_exit": 0,
                    "stdout": json.dumps(x),
                    "stderr": "",
                    "elapsed_ns": 1,
                }
                for x in results
            ]
            with (
                patch.object(
                    run.measure, "run_command", side_effect=replies
                ) as command,
                self.assertRaisesRegex(run.Failure, "setup tool result: worker error"),
            ):
                campaign.prepare_base(
                    row, {"setup_argv": ["true"]}, run.measure.Deadline.after(1)
                )
            self.assertEqual(command.call_count, 3)
            self.assertEqual(row["workspace"], "unit:setup")

    def test_explicit_failed_proof_cannot_pass_report(self):
        run = load_runner()
        matrix = run.selections(["A01"])
        rows = {
            x["id"]: {
                **x,
                "execution": "PASS",
                "cleanup": "COMPLETE",
                "verification": "SKIPPED",
            }
            for x in matrix
        }
        rows["A01/native/sqlite"]["verification"] = "FAIL"
        text = report.render(
            "unit",
            {"matrix": matrix, "rows": rows, "source_sha": "a" * 40},
            {"cleanup": "COMPLETE"},
            {},
        )
        self.assertIn("Diagnostic terminal: INCOMPLETE", text)
        self.assertIn("'FAIL': 1", text)
        self.assertIn("teardown wall: UNAVAILABLE", text)

    def test_deadline_is_shared_and_expired_before_send(self):
        with self.assertRaises(measure.BudgetExceeded):
            measure.run_command(["false"], measure.Deadline(0))


if __name__ == "__main__":
    unittest.main()
