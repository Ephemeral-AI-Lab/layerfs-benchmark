"""Offline tests of the run.py row wrapper and check_results.py (no LayerFS needed; POSIX shell only).

run: python3 -I fs-file-calls/test_harness.py
"""

from __future__ import annotations

import stat
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import check_results  # noqa: E402
import run  # noqa: E402

FAKE = """#!/bin/sh
case "$1" in
  refuse) echo '{"error":"Capacity","message":"no room"}' >&2; exit 125 ;;
  slow) sleep 5 ;;
  junk) echo not-json ;;
  *) echo '{"ok":true}' ;;
esac
"""


@unittest.skipUnless(sys.platform != "win32", "needs /bin/sh and os.wait4")
class RowWrapper(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        fake = self.tmp / "fake"
        fake.write_text(FAKE)
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        (self.tmp / "home").mkdir()
        self.cli = run.CliRunner(fake, self.tmp / "home")

    def test_success_has_rusage(self):
        r = self.cli.call(["ok"])
        self.assertEqual(r["data"], {"ok": True})
        self.assertGreater(r["max_rss_bytes"], 0)
        self.assertIsNotNone(r["cpu_ms"])

    def test_refusal_becomes_a_row_with_its_code(self):
        rows: list[dict] = []
        run.guarded(rows, "file.apply (8192)", "limit", lambda: run.summarize_calls([self.cli.call(["refuse"])]))
        self.assertEqual((rows[0]["status"], rows[0]["code"], rows[0]["kind"]), ("REFUSED", "Capacity", "limit"))

    def test_timeout_becomes_a_fail_row_with_the_cap(self):
        rows: list[dict] = []
        run.guarded(rows, "slow case", "read", lambda: run.summarize_calls([self.cli.call(["slow"], cap_s=1)]))
        self.assertEqual(rows[0]["status"], "FAIL")
        self.assertEqual(rows[0]["cap_s"], 1)  # the run uses 120

    def test_unparsable_output_is_fail_not_a_crash(self):
        with self.assertRaises(run.CaseAbort) as ctx:
            self.cli.call(["junk"])
        self.assertEqual(ctx.exception.status, "FAIL")

    def test_refusal_code_parsing(self):
        self.assertEqual(run.refusal_code('x\n{"error":"Busy","message":"m"}\n', "")[0], "Busy")
        self.assertEqual(run.refusal_code("", "garbage")[0], "Unknown")


class Checker(unittest.TestCase):
    def row(self, **kw):
        return {"case": "c", "kind": "read", "status": "OK", "identity": {"host": {"cpu": "x"}},
                "proof": {"manifest": {"match": True}}, **kw}

    def test_passes_a_complete_result(self):
        self.assertEqual(check_results.check({"arms": {"a": {"rows": [self.row()]}}}), [])

    def test_flags_missing_identity_and_proof(self):
        errs = check_results.check({"arms": {"a": {"rows": [self.row(identity={}), self.row(proof={})]}}})
        self.assertEqual(len(errs), 2)

    def test_flags_a_cold_row_that_is_not_ineligible(self):
        errs = check_results.check({"arms": {"a": {"rows": [self.row(kind="cold", status="OK")]}}})
        self.assertTrue(any("INELIGIBLE" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
