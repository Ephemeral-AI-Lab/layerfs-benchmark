"""Evidence admission and missing-row accounting for retained reports."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import report


class ReportTests(unittest.TestCase):
    def test_execution_alone_cannot_pass_before_final_cleanup(self):
        rows = [
            {
                "id": identity,
                "execution": "PASS",
                "cleanup": "COMPLETE",
                "verification": "SKIPPED",
                "performance": "INELIGIBLE",
            }
            for identity in report.matrix()
        ]
        self.assertEqual(report.diagnostic_outcome(rows, {})["diagnostic_terminal"], "INCOMPLETE")
        self.assertEqual(report.diagnostic_outcome(rows, {"cleanup": "COMPLETE"})["diagnostic_terminal"], "PASS")
        rows[-1]["cleanup"] = "INCOMPLETE"
        self.assertEqual(report.diagnostic_outcome(rows, {"cleanup": "COMPLETE"})["diagnostic_terminal"], "INCOMPLETE")

    def test_missing_attempts_keep_all_96_rows(self):
        with tempfile.TemporaryDirectory() as root:
            rows = report.load_rows(Path(root))
        self.assertEqual(len(rows), 96)
        self.assertEqual(rows[0]["id"], "C01/native/sqlite")
        self.assertEqual(rows[-1]["id"], "C12/apple-container/postgresql")
        self.assertTrue(all(row["execution"] == "NOT_RUN" for row in rows))

    def test_duplicate_attempts_are_not_silently_selected(self):
        with tempfile.TemporaryDirectory() as root:
            for name in ("first", "second"):
                path = Path(root) / name
                path.mkdir()
                (path / "receipt.json").write_text(json.dumps({"id": "C01/native/sqlite"}))
            with self.assertRaisesRegex(ValueError, "duplicate retained attempts"):
                report.load_rows(Path(root))

    def test_status_and_source_alone_cannot_admit_comparison(self):
        row = {"execution": "PASS", "performance": "ELIGIBLE", "source_sha": "a" * 40, "artifacts": {}, "exec_ns": 100}
        self.assertFalse(report.comparable(row, dict(row)))
        row["artifacts"] = {key: "present" for key in ("cli_sha256", "daemon_sha256", "linux_bundle_sha256", "profile")}
        self.assertFalse(report.comparable(row, dict(row)))


if __name__ == "__main__":
    unittest.main()
