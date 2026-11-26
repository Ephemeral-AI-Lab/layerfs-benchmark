"""Offline tests of the run.py row wrapper, proofs, redaction and check_results.py (no LayerFS needed; POSIX shell only).

run: python3 -I fs-file-calls/test_harness.py
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
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

    def result(self, rows, **extra):
        return {"arms": {"a": {"rows": rows}}, "expected": {"a": [r["case"] for r in rows]},
                "proof": {}, "failed_arms": {}, **extra}

    def test_passes_a_complete_result(self):
        self.assertEqual(check_results.check(self.result([self.row()])), [])

    def test_flags_missing_identity_and_proof(self):
        errs = check_results.check(self.result([self.row(identity={}), self.row(proof={}, case="d")]))
        self.assertEqual(len(errs), 2)

    def test_flags_a_cold_row_that_is_not_ineligible(self):
        errs = check_results.check(self.result([self.row(kind="cold", status="OK")]))
        self.assertTrue(any("INELIGIBLE" in e for e in errs))

    def test_registry_failed_arms_and_proofs(self):
        r = self.result([self.row()], expected={"a": ["c", "never ran"]}, failed_arms={"pg": "boom"},
                        proof={"x": {"F100": {"match": None}}, "y": False})
        text = "\n".join(check_results.check(r))
        self.assertIn("registered case missing: never ran", text)
        self.assertIn("failed arm pg", text)
        self.assertIn("proof not True: x.F100", text)
        self.assertIn("proof not True: y", text)


class Proofs(unittest.TestCase):
    def test_empty_read_text_does_not_pass(self):
        self.assertFalse(run.read_window_ok({"text": ""}, "abc\n" * 100))
        self.assertFalse(run.read_window_ok({"text": "abc\n"}, "abc\n" * 10000))  # far shorter than the window
        self.assertTrue(run.read_window_ok({"text": "abc\n" * 10}, "abc\n" * 10))  # the whole small file
        self.assertTrue(run.read_window_ok({"text": ("abc\n" * 10000)[:40000]}, "abc\n" * 100000))
        self.assertFalse(run.read_window_ok({"text": "xyz\n"}, "abc\n"))

    def test_raising_proof_is_a_failed_proof(self):
        fx = {"sizes": {"root": Path("."), "sha": "x"}, "hist": {"root": Path("."), "sha": "x"}}
        proofs = run.build_proofs(fx, [10])
        good, err = run.eval_proof(proofs["file.history (H10, head)"][2], {"items": []})  # IndexError on an empty page
        self.assertFalse(good)
        self.assertIn("IndexError", err)
        self.assertFalse(run.eval_proof(proofs["file.blame (H10, head)"][2], {})[0])  # KeyError

    def test_guarded_turns_any_exception_into_a_fail_row(self):
        rows: list[dict] = []
        run.guarded(rows, "c", "read", lambda: {}["missing"])
        self.assertEqual((rows[0]["status"], rows[0]["case"]), ("FAIL", "c"))

    def test_finalize_survives_a_bad_sdk_sample(self):
        proofs = {"file.stat (F1)": ("F1", "d", lambda d: d["size"] == 1)}
        arm = {"rows": [{"case": "file.stat (F1)", "kind": "read", "status": "OK", "_sample": {}}],
               "_proofs": proofs, "_fx": {"F1": {"sha": "s"}}, "concurrency": []}
        run.finalize_arm(arm, {"host": {"cpu": "x"}}, "sqlite", "sdk")
        self.assertFalse(arm["rows"][0]["proof"]["manifest"]["match"])
        self.assertTrue(any(r["status"] == "INELIGIBLE" for r in arm["rows"]))

    def test_proof_problems_fold_manifest_checks(self):
        self.assertEqual(run.proof_problems({"a_match": True, "m": {"F": {"match": True}}}), [])
        self.assertEqual(run.proof_problems({"m": {"F": {"match": None}}, "b": False}), ["m.F", "b"])


FAKE_FAIL = """#!/bin/sh
echo '{"error":"Failed","message":"setup broke"}' >&2
exit 125
"""

FAKE_PSQL = """#!/bin/sh
echo "psql: error: connection to postgresql://admin:s3cret@127.0.0.1:1/x failed password=hunter2" >&2
exit 2
"""


def fake_psql_env(tmp: Path) -> dict:
    bindir = tmp / "bin"
    bindir.mkdir()
    (bindir / "psql").write_text(FAKE_PSQL)
    (bindir / "psql").chmod(0o755)
    return {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}"}


class Redaction(unittest.TestCase):
    def test_url_userinfo_and_passwords_are_stripped(self):
        text = "Command failed: psql postgresql://admin:s3cret@db:5432/x?sslmode=disable host=h password=hunter2 ok"
        out = run.redact(text)
        for secret in ("admin", "s3cret", "hunter2"):
            self.assertNotIn(secret, out)

    @unittest.skipUnless(sys.platform != "win32", "needs /bin/sh")
    def test_psql_error_carries_no_credentials(self):
        old = os.environ["PATH"]
        os.environ.update(fake_psql_env(Path(tempfile.mkdtemp())))
        try:
            with self.assertRaises(RuntimeError) as ctx:
                run.psql("postgresql://admin:s3cret@127.0.0.1:1/x", "select 1")
        finally:
            os.environ["PATH"] = old
        for secret in ("admin", "s3cret", "hunter2"):
            self.assertNotIn(secret, str(ctx.exception))


@unittest.skipUnless(sys.platform != "win32", "needs /bin/sh")
class BrokenRun(unittest.TestCase):
    def test_setup_failure_still_writes_results_and_report(self):
        tmp = Path(tempfile.mkdtemp())
        fake = tmp / "fake"
        fake.write_text(FAKE_FAIL)
        fake.chmod(0o755)
        repo = tmp / "repo"
        repo.mkdir()
        git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "x"], check=True)
        head = subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip()
        env = {**fake_psql_env(tmp), "LAYERFS_TEST_TMPDIR": str(tmp)}
        done = subprocess.run(
            [sys.executable, "-I", str(HERE / "run.py"), "--cli", str(fake), "--node-pkg", str(HERE / "run.py"),
             "--source-dir", str(repo), "--source", head, "--n-read", "1", "--n-write", "1", "--trees", "F100",
             "--output", str(tmp / "out"), "--report", str(tmp / "out" / "report.md"),
             "--pg-admin-url", "postgresql://admin:s3cret@127.0.0.1:1/postgres"],
            capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        raw = (tmp / "out" / "results.json").read_text()
        results = json.loads(raw)
        self.assertIn("sqlite", results["failed_arms"])
        self.assertIn("pg", results["failed_arms"])
        everything = raw + (tmp / "out" / "report.md").read_text() + done.stderr
        for secret in ("s3cret", "hunter2"):
            self.assertNotIn(secret, everything)
        rows = results["arms"]["sqlite_cli"]["rows"]
        self.assertEqual(rows[0]["status"], "FAIL")
        self.assertTrue(all(r["status"] in ("NOT_RUN", "FAIL", "INELIGIBLE") for r in rows))
        self.assertTrue(check_results.check(results))  # the checker rejects it


if __name__ == "__main__":
    unittest.main()
