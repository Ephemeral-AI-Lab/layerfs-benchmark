"""Focused guardrails for deadlines, bounded output and cache honesty."""

import sys
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import measure
from measure import BudgetExceeded, Deadline, assess_cache, run_command


class MeasurementTests(unittest.TestCase):
    def test_separate_cli_and_workload_exit_is_preserved_as_output(self):
        result = run_command([sys.executable, "-c", "print('{\"exit_code\": 7}')"], Deadline.after(2))
        self.assertEqual(result["process_exit"], 0)
        self.assertIn('"exit_code": 7', result["stdout"])
        self.assertFalse(result["uncertainty"])
        self.assertGreater(result["elapsed_ns"], 0)
        self.assertGreaterEqual(result["child_cpu_ns"], 0)
        self.assertEqual(result["remote_resources"]["status"], "UNAVAILABLE")

    def test_output_is_bounded_but_fully_drained(self):
        result = run_command(
            [
                sys.executable,
                "-c",
                "import sys; sys.stdout.write('x'*200000); sys.stderr.write('y'*200000)",
            ],
            Deadline.after(2),
            output_limit=1024,
        )
        self.assertEqual(result["process_exit"], 0)
        self.assertEqual(len(result["stdout"]), 1024)
        self.assertEqual(len(result["stderr"]), 1024)
        self.assertEqual(result["stdout_bytes"], 200000)
        self.assertEqual(result["stderr_bytes"], 200000)
        self.assertTrue(result["output_truncated"])

    def test_timeout_is_uncertain_even_after_local_kill(self):
        result = run_command([sys.executable, "-c", "import time; time.sleep(3)"], Deadline.after(0.1))
        self.assertTrue(result["timed_out"])
        self.assertTrue(result["uncertainty"])
        self.assertLess(result["elapsed_ns"], 1_000_000_000)
        self.assertNotEqual(result["process_exit"], 0)

    def test_expired_shared_deadline_cannot_start_next_operation(self):
        with self.assertRaises(BudgetExceeded):
            run_command(
                [sys.executable, "-c", "raise AssertionError('must not run')"],
                Deadline(time.monotonic_ns() - 1),
            )

    def test_spawn_failure_did_not_send_remote_operation(self):
        result = run_command(["/definitely/missing/layerfs"], Deadline.after(1))
        self.assertIsNone(result["process_exit"])
        self.assertFalse(result["uncertainty"])
        self.assertTrue(result["error"])

    def test_declarations_cannot_self_certify_coldness(self):
        for machine in ["native", "docker", "lima", "apple-container"]:
            for backend in ["sqlite", "postgresql"]:
                result = assess_cache(
                    {"cold": True, "status": "PASS", "method": "fresh-mount"},
                    "commit",
                    machine,
                    backend,
                )
                self.assertEqual(result["status"], "INELIGIBLE")
                self.assertIn("layerfs-daemon-worker", result["required_domains"])
                if backend == "postgresql":
                    self.assertIn("postgresql-shared-buffers", result["required_domains"])

    def test_unknown_phase_evidence_remains_ineligible(self):
        self.assertEqual(assess_cache({}, "exec", "native", "sqlite")["status"], "INELIGIBLE")

    def test_interruption_reaps_local_caller_before_propagating(self):
        children = []
        original_popen = measure.subprocess.Popen

        def launch(*args, **kwargs):
            child = original_popen(*args, **kwargs)
            children.append(child)
            return child

        with (
            mock.patch.object(measure.subprocess, "Popen", side_effect=launch),
            mock.patch.object(
                measure.selectors.DefaultSelector,
                "select",
                side_effect=KeyboardInterrupt,
            ),
            self.assertRaises(KeyboardInterrupt),
        ):
            run_command(
                [
                    sys.executable,
                    "-c",
                    "import time; print('ready', flush=True); time.sleep(3)",
                ],
                Deadline.after(2),
            )
        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].returncode)

    def test_invalid_deadline_is_rejected(self):
        for seconds in [0, -1, float("inf"), float("nan")]:
            with self.assertRaises(ValueError):
                Deadline.after(seconds)


if __name__ == "__main__":
    unittest.main()
