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


# Real lines from a worker-routed call (docker machine, release worker at ca4be0bf3c): `file.read` and one `file.stat`,
# preceded by the `worker.connection` event LAYERFS_TRACE writes beside the steps.
WORKER_TRACE = (
    '{"at":1795657283259,"event":"worker.connection","op":"store.call","worker":"127.0.0.1:46105","sent":true,"ms":5}\n'
    '{"at":1795657283259,"event":"step","op":"file.read","step":"dispatch","us":37,"ms":0}\n'
    '{"at":1795657283259,"event":"step","op":"file.read","step":"route","us":145,"ms":0}\n'
    '{"at":1795657283259,"event":"step","op":"file.read","step":"connect","us":331,"ms":0}\n'
    '{"at":1795657283259,"event":"step","op":"file.read","step":"ready","us":611,"ms":0}\n'
    '{"at":1795657283259,"event":"step","op":"file.read","step":"request","us":63,"ms":0}\n'
    '{"at":1795657283259,"event":"step","op":"file.read","step":"answer","us":4674,"ms":4}\n'
    '{"at":1795657283259,"event":"step","op":"file.read","step":"worker.result","us":4423,"ms":4}\n'
    'not json\n'
)


class WorkerTrace(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.trace = self.tmp / "trace.jsonl"
        self.trace.write_text(WORKER_TRACE, encoding="utf-8")

    def test_steps_are_read_in_microseconds_and_connection_lines_ignored(self):
        steps = run.read_trace(self.trace, 0)
        self.assertEqual(steps, {"dispatch": 37, "route": 145, "connect": 331, "ready": 611, "request": 63,
                                 "answer": 4674, "worker.result": 4423})

    def test_repeated_hops_are_summed_per_call(self):
        with self.trace.open("a") as f:
            f.write('{"at":1,"event":"step","op":"project.init","step":"route","us":1,"ms":0}\n'
                    '{"at":1,"event":"step","op":"project.init","step":"route","us":118,"ms":0}\n')
        offset = len(WORKER_TRACE.encode())
        self.assertEqual(run.read_trace(self.trace, offset), {"route": 119})

    def test_attribution_of_a_worker_call_has_the_full_table(self):
        call = {"steps_us": run.read_trace(self.trace, 0)}
        a = run.attribution([call, call])
        self.assertEqual(a["unavailable"], {})
        self.assertEqual(a["steps_p50_ms"]["answer"], 4.674)
        self.assertEqual(a["source"], run.WORKER_TRACE_SRC)
        native = run.attribution([{"steps_us": {"dispatch": 40}}])
        self.assertIn("route", native["unavailable"])
        self.assertEqual(native["source"], run.TRACE_SRC)

    def test_step_table_orders_caller_steps_then_worker_steps(self):
        a = run.attribution([{"steps_us": run.read_trace(self.trace, 0)}])
        rows = [{"kind": "read", "status": "OK", "attribution": a},
                {"kind": "read", "status": "OK", "attribution": {"steps_p50_ms": {**a["steps_p50_ms"], "answer": 9.0}}},
                {"kind": "write", "status": "OK", "attribution": a},
                {"kind": "read", "status": "FAIL"}]
        table = run.step_table(rows, "read")
        self.assertEqual([n for n, _, _ in table], ["dispatch", "route", "connect", "ready", "request", "answer", "worker.result"])
        self.assertEqual(dict((n, (ms, k)) for n, ms, k in table)["answer"], (6.837, 2))  # median of 4.674 and 9.0

    def test_docker_cold_rows_are_ineligible_with_the_guest_cache(self):
        arm = {"rows": [{"case": "file.stat (F1)", "kind": "read", "status": "OK"}], "concurrency": []}
        run.finalize_arm(arm, {"host": {"cpu": "x"}, "route": "docker"}, "sqlite", "cli", None, "docker")
        cold = arm["rows"][-1]
        self.assertEqual((cold["status"], cold["assessment"]["machine"]), ("INELIGIBLE", "docker"))
        self.assertIn("guest-page-cache", cold["required_domains"])
        self.assertEqual(arm["rows"][0]["identity"]["route"], "docker")

    def test_docker_expectation_has_no_limits(self):
        exp = run.expected_cases("cli", ["F100"], [1, 100], 0, [], [], limits=False)
        self.assertFalse([c for c, _ in exp if c.startswith("limit:")])
        self.assertIn(("file.blame (H100, head)", "read"), exp)

    def test_write_report_survives_failed_cli_stat_when_sdk_stat_passed(self):
        tmp = Path(tempfile.mkdtemp())
        rep = tmp / "report.md"
        base_id = {"cli_sha256": "c", "addon_sha256": "a", "route": "native",
                   "host": {"cpu": "x", "cpus": 4, "ram_gib": 8.0, "kernel": "k"}}
        dk_id = {**base_id, "route": "docker", "backend": "namespaces", "worker_build_id": "b/w",
                 "bundle": {"hash": "b" * 16, "profile": "release", "protocol": 3,
                            "source_head": "0" * 40, "worker_sha256": "w" * 16}}
        results = {
            "meta": {"n_read": 1, "n_write": 1, "trees": ["F1k"], "h_depths": [1], "cap_s": 120,
                     "disk_free_gb_start": 50.0, "disk_free_gb_end": 50.0, "cache_state": "warm", "routes": ["native", "docker"]},
            "identity": base_id, "fixtures": {}, "not_run": [], "proof": {}, "failed_arms": {},
            "arms": {
                "sqlite_sdk": {"rows": [{"case": "file.stat (F1k)", "kind": "read", "status": "OK", "n": 1, "p50_ms": 2.0, "p95_ms": 2.0, "identity": base_id}], "concurrency": []},
                "sqlite_cli": {"rows": [{"case": "file.stat (F1k)", "kind": "read", "status": "FAIL", "n": 0, "cap_s": 120, "identity": base_id}], "concurrency": []},
                "docker_sdk": {"rows": [{"case": "file.stat (F1k)", "kind": "read", "status": "OK", "n": 1, "p50_ms": 3.0, "p95_ms": 3.0, "identity": dk_id}], "concurrency": []},
                "docker_cli": {"rows": [{"case": "file.stat (F1k)", "kind": "read", "status": "FAIL", "n": 0, "cap_s": 120, "identity": dk_id}], "concurrency": []},
            },
        }
        run.write_report(results, run.SimpleNamespace(report=rep), "0" * 40)
        self.assertIn("Docker worker route vs native SQLite", rep.read_text(encoding="utf-8"))


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

    def test_docker_route_failure_is_a_row_and_the_run_finishes(self):
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
        done = subprocess.run(
            [sys.executable, "-I", str(HERE / "run.py"), "--cli", str(fake), "--node-pkg", str(HERE / "run.py"),
             "--source-dir", str(repo), "--source", head, "--n-read", "1", "--n-write", "1", "--trees", "F100",
             "--routes", "native,docker", "--output", str(tmp / "out"), "--report", str(tmp / "out" / "report.md")],
            capture_output=True, text=True, env={**os.environ, "LAYERFS_TEST_TMPDIR": str(tmp)}, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        results = json.loads((tmp / "out" / "results.json").read_text())
        self.assertIn("docker", results["failed_arms"])
        rows = results["arms"]["docker_cli"]["rows"]
        self.assertEqual(rows[0]["status"], "FAIL")
        self.assertEqual({r["identity"]["route"] for r in rows}, {"docker"})
        self.assertNotIn("file.stat (F100)", [c for c in results["expected"]["docker_cli"] if c not in {r["case"] for r in rows}])
        self.assertNotIn("docker-route", (tmp / "out" / "report.md").read_text().split("\n")[2])  # the headline names the route only if it ran

    def test_docker_only_route_writes_report_without_native_arms(self):
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
        done = subprocess.run(
            [sys.executable, "-I", str(HERE / "run.py"), "--cli", str(fake), "--node-pkg", str(HERE / "run.py"),
             "--source-dir", str(repo), "--source", head, "--n-read", "1", "--n-write", "1", "--trees", "F100",
             "--routes", "docker", "--output", str(tmp / "out"), "--report", str(tmp / "out" / "report.md")],
            capture_output=True, text=True, env={**os.environ, "LAYERFS_TEST_TMPDIR": str(tmp)}, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        results = json.loads((tmp / "out" / "results.json").read_text())
        not_run = {nr["route"] for nr in results["not_run"]}
        self.assertIn("native:sqlite", not_run)
        self.assertIn("native:postgresql", not_run)


if __name__ == "__main__":
    unittest.main()
