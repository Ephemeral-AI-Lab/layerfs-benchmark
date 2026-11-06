"""Focused lifecycle unit tests; the fake call result never launches LayerFS."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
spec = importlib.util.spec_from_file_location(
    "quick_run", Path(__file__).resolve().parents[1] / "src" / "run.py"
)
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


def result(value=None, **changes):
    return {
        "process_exit": 0,
        "stdout": json.dumps(value or {}),
        "stderr": "",
        "elapsed_ns": 10,
        "timed_out": False,
        "uncertainty": False,
        "output_truncated": False,
        **changes,
    }


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.empty = self.base / "empty"
        self.empty.mkdir()
        self.cli = self.base / "layerfs"
        self.cli.write_text("fake artifact, never executed")
        self.cli.chmod(0o700)
        self.config = {
            "campaign_id": "unit",
            "source_sha": "a" * 40,
            "cli": str(self.cli),
            "home": str(self.base / "home"),
            "empty_source": str(self.empty),
            "machines": {
                machine: {"ready": True, "name": machine} for machine in run.MACHINES
            },
            "artifacts": {"cli_sha256": run.digest(self.cli)},
        }
        self.campaign = run.Campaign(self.config, self.base / "cache")
        self.selection = run.selections(["C01"], ["native"], ["sqlite"])[0]

    def prepare(self):
        with patch.object(run.measure, "run_command", return_value=result()) as command:
            row = self.campaign.prepare(self.selection)
        self.assertEqual(row["preparation"], "READY")
        self.assertEqual(command.call_count, 3)
        return row

    def test_postgresql_url_allows_tls_settings_but_never_password_parameters(self):
        selection = run.selections(["C09"], ["docker"], ["postgresql"])[0]
        row = self.campaign.row(selection)
        pg = {
            "password_env": "BENCH_UNIT_PG_PASSWORD",
            "disposal_resource": "unit-pg",
            "databases": {
                "C09/docker": "postgresql://bench@server/db?sslmode=verify-full"
            },
        }
        self.config["postgresql"] = pg
        self.campaign.state["resources"] = [
            {"id": "unit-pg", "owned": True, "release_argv": ["remove", "unit-pg"]}
        ]
        with patch.dict(run.os.environ, {"BENCH_UNIT_PG_PASSWORD": "not-logged"}):
            self.assertIsNone(self.campaign.prerequisite(row))
            for suffix in (
                "?password=secret",
                "?sslpassword=secret",
                "?%70assword=secret",
            ):
                pg["databases"]["C09/docker"] = "postgresql://bench@server/db" + suffix
                self.assertIn("password", self.campaign.prerequisite(row))
            pg["databases"]["C09/docker"] = "postgresql://bench:secret@server/db"
            self.assertIn("password", self.campaign.prerequisite(row))

    def test_committed_base_preparation_pushes_small_store_then_releases_setup(self):
        selection = run.selections(["C09"], ["docker"], ["sqlite"])[0]
        prepared_results = [
            result(),
            result(),
            result(),
            result(),
            result(),
            result({"ws": "unit:setup"}),
            result({"exit_code": 0}, elapsed_ns=2_000_000_000),
            result({"kind": "Committed", "head": "base-head"}),
            result(),
            result(),
        ]
        with patch.object(
            run.measure, "run_command", side_effect=prepared_results
        ) as command:
            row = self.campaign.prepare(selection)
        prep_argv = [call.args[0] for call in command.call_args_list]
        self.assertEqual(
            [argv[1:3] for argv in prep_argv],
            [
                ["store", "create"],
                ["project", "init"],
                ["branch", "fork"],
                ["store", "push"],
                ["sandbox", "create"],
                ["workspace", "mount"],
                ["workspace", "exec"],
                ["workspace", "commit"],
                ["workspace", "unmount"],
                ["sandbox", "close"],
            ],
        )
        self.assertEqual(prep_argv[4][-1], "docker")
        self.assertEqual(len({id(call.args[1]) for call in command.call_args_list}), 1)
        self.assertIn("dd if=/dev/zero of=big", prep_argv[6][-1])
        self.assertIn("export LANG=C LC_ALL=C", prep_argv[6][-1])
        self.assertEqual(row["preparation"], "READY")
        self.assertTrue(row["store_live"])
        self.assertFalse(row["sandbox_live"])
        self.assertIsNone(row["workspace"])
        self.assertEqual(row["base_fixture"]["commit"]["head"], "base-head")
        self.assertNotIn("performance_invocation_elapsed_ns", row)
        measured_results = [
            result(),
            result({"ws": "unit:measured"}),
            result({"exit_code": 0}),
            result({"kind": "UpToDate"}),
            result(),
            result(),
            result(),
        ]
        with patch.object(
            run.measure, "run_command", side_effect=measured_results
        ) as command:
            self.campaign.execute(selection, self.base / "committed-base")
        measured_argv = [call.args[0] for call in command.call_args_list]
        self.assertEqual(len(measured_argv), 7)
        self.assertTrue(all("dd if=" not in argv[-1] for argv in measured_argv))
        self.assertIn("cat big > /dev/null", measured_argv[2][-1])
        self.assertEqual(row["timings_ns"]["setup_exec"], 2_000_000_000)
        self.assertEqual(row["timings_ns"]["exec"], 10)
        self.assertLess(row["performance_invocation_elapsed_ns"], 2_000_000_000)
        self.assertEqual(row["execution"], "PASS")
        self.assertEqual(row["cleanup"], "COMPLETE")

    def test_exact_matrix_order(self):
        rows = run.selections()
        # C01-C12 keep their order; C13-C18 (layerfs-project#62) follow.
        self.assertEqual(len(rows), 144)
        self.assertEqual(
            [row["id"] for row in rows[:4]],
            [
                "C01/native/sqlite",
                "C01/native/postgresql",
                "C01/docker/sqlite",
                "C01/docker/postgresql",
            ],
        )
        self.assertEqual(rows[8]["id"], "C02/native/sqlite")

    def test_prepare_registers_intent_before_effect_and_closes_pristine_input(self):
        def observe(argv, deadline, **kwargs):
            saved = json.loads(self.campaign.path.read_text())
            self.assertIsNotNone(saved["rows"][self.selection["id"]]["pending"])
            self.assertEqual(kwargs["env"]["LAYERFS_HOME"], self.config["home"])
            self.assertEqual(kwargs["env"]["LAYERFS_CONSTRUCTION_WORKERS"], "1")
            self.assertEqual(argv[0], self.config["cli"])
            return result()

        with patch.object(run.measure, "run_command", side_effect=observe):
            row = self.campaign.prepare(self.selection)
        self.assertTrue(row["store_live"])
        self.assertFalse(row["sandbox_live"])
        self.assertIsNone(row["workspace"])

    def test_embedded_workload_failure_is_not_cli_success(self):
        row = self.prepare()
        answers = [
            result(),
            result({"ws": "unit:measured"}),
            result({"exit_code": 7}),
            result(),
            result(),
            result(),
        ]
        with patch.object(run.measure, "run_command", side_effect=answers) as command:
            self.campaign.execute(self.selection, self.base / "output")
        self.assertEqual(row["execution"], "FAIL")
        self.assertEqual(row["cleanup"], "COMPLETE")
        self.assertEqual(row["verification"], "SKIPPED")
        self.assertEqual(command.call_count, 6)

    def test_timeout_retains_entire_containing_state_and_finish_does_not_replay(self):
        row = self.prepare()
        with patch.object(
            run.measure,
            "run_command",
            return_value=result(process_exit=None, timed_out=True, uncertainty=True),
        ) as command:
            self.campaign.execute(self.selection, self.base / "output")
            self.campaign.finish()
        self.assertEqual(command.call_count, 1)
        self.assertEqual(row["cleanup"], "INCOMPLETE")
        self.assertTrue(row["store_live"])
        self.assertEqual(self.campaign.state["cleanup"], "INCOMPLETE")

    def test_success_accepts_uptodate_and_verification_is_default_off(self):
        row = self.prepare()
        answers = [
            result(),
            result({"ws": "unit:measured"}),
            result({"exit_code": 0}),
            result({"kind": "UpToDate"}),
            result(),
            result(),
            result(),
        ]
        with patch.object(run.measure, "run_command", side_effect=answers) as command:
            self.campaign.execute(self.selection, self.base / "output")
        self.assertEqual(row["execution"], "PASS")
        self.assertEqual(row["correctness"], "UNVERIFIED")
        self.assertEqual(row["performance"], "INELIGIBLE")
        self.assertEqual(row["cleanup"], "COMPLETE")
        self.assertEqual(command.call_count, 7)
        with self.assertRaisesRegex(run.Failure, "no resampling"):
            self.campaign.execute(self.selection, self.base / "another-output")

    def test_finish_never_claims_disconnect_dropped_postgresql_data(self):
        row = self.campaign.row(run.selections(["C01"], ["native"], ["postgresql"])[0])
        row["database_allocation"] = "postgresql://host/exact_db"
        row["cleanup"] = "COMPLETE"
        receipt = self.campaign.finish()
        self.assertEqual(receipt["cleanup"], "INCOMPLETE")
        self.assertEqual(row["postgresql_data"], "RETAINED")

    def test_finish_records_exact_owned_infrastructure_and_retains_borrowed(self):
        self.campaign.state["resources"] = [
            {
                "id": "owned-server",
                "owned": True,
                "release_argv": ["provider", "remove", "exact-id"],
            },
            {"id": "borrowed", "owned": False},
        ]
        with patch.object(run.measure, "run_command", return_value=result()) as command:
            receipt = self.campaign.finish()
        self.assertEqual(receipt["cleanup"], "COMPLETE")
        self.assertEqual(command.call_count, 1)
        self.assertEqual(command.call_args.args[0], ["provider", "remove", "exact-id"])
        self.assertNotIn("released", self.campaign.state["resources"][1])

    def test_failed_infrastructure_release_retains_parent_and_is_never_replayed(self):
        scenarios = [
            (result(process_exit=1), "FAIL"),
            (result(process_exit=None, timed_out=True, uncertainty=True), "INCOMPLETE"),
            (run.measure.BudgetExceeded("not started"), "FAIL"),
            (KeyboardInterrupt(), "INCOMPLETE"),
        ]
        for index, (outcome, expected) in enumerate(scenarios):
            with self.subTest(expected=expected, scenario=index):
                campaign = run.Campaign(self.config, self.base / f"release-{index}")
                campaign.state["resources"] = [
                    {
                        "id": "worker",
                        "owned": True,
                        "release_argv": ["stop", "exact-worker"],
                    },
                    {
                        "id": "parent-volume",
                        "owned": True,
                        "release_argv": ["remove", "exact-volume"],
                    },
                ]
                kwargs = (
                    {"side_effect": outcome}
                    if isinstance(outcome, BaseException)
                    else {"return_value": outcome}
                )
                with patch.object(run.measure, "run_command", **kwargs) as command:
                    receipt = campaign.finish()
                    repeated = campaign.finish()
                self.assertEqual(command.call_count, 1)
                self.assertEqual(command.call_args.args[0], ["stop", "exact-worker"])
                self.assertEqual(receipt["cleanup"], expected)
                self.assertEqual(repeated["cleanup"], expected)
                first, parent = campaign.state["resources"]
                self.assertEqual(first["disposition"], expected)
                self.assertEqual(parent["disposition"], "RETAINED")
                self.assertNotIn("attempted", parent)
                self.assertIn("worker", parent["retained_reason"])
                if isinstance(outcome, run.measure.BudgetExceeded):
                    events = [
                        json.loads(line)
                        for line in campaign.log.read_text().splitlines()
                    ]
                    release = next(
                        event
                        for event in events
                        if event["event"] == "infrastructure_release_result"
                    )
                    self.assertTrue(release["not_started"])

    def test_opt_in_proof_runs_only_after_measured_unmount(self):
        row = self.prepare()
        answers = [
            result(),
            result({"ws": "unit:measured"}),
            result({"exit_code": 0}),
            result({"kind": "Committed"}),
            result(),
            result({"ws": "unit:verification"}),
            result({"exit_code": 0}),
            result(),
            result(),
            result(),
        ]
        with patch.object(run.measure, "run_command", side_effect=answers) as command:
            self.campaign.execute(self.selection, self.base / "verified", verify=True)
        self.assertEqual(row["verification"], "PASS")
        self.assertEqual(row["correctness"], "VERIFIED")
        self.assertEqual(row["cleanup"], "COMPLETE")
        self.assertGreaterEqual(row["verification_elapsed_ns"], 0)
        calls = [call.args[0][1:3] for call in command.call_args_list]
        self.assertEqual(
            calls,
            [
                ["sandbox", "create"],
                ["workspace", "mount"],
                ["workspace", "exec"],
                ["workspace", "commit"],
                ["workspace", "unmount"],
                ["workspace", "mount"],
                ["workspace", "exec"],
                ["workspace", "unmount"],
                ["sandbox", "close"],
                ["store", "remove"],
            ],
        )

    def test_explicit_failed_proof_makes_main_fail_despite_successful_measurement(self):
        self.prepare()
        environment = self.base / "environment.json"
        environment.write_text(json.dumps(self.config))
        answers = [
            result(),
            result({"ws": "unit:measured"}),
            result({"exit_code": 0}),
            result({"kind": "Committed"}),
            result(),
            result({"ws": "unit:verification"}),
            result({"exit_code": 1}),
            result(),
            result(),
            result(),
        ]
        with (
            patch.object(run.measure, "run_command", side_effect=answers),
            patch("builtins.print"),
        ):
            exit_code = run.main(
                [
                    "run",
                    "--environment",
                    str(environment),
                    "--cache",
                    str(self.base / "cache"),
                    "--case",
                    "C01",
                    "--machine",
                    "native",
                    "--backend",
                    "sqlite",
                    "--verify",
                    "--output",
                    str(self.base / "failed-proof"),
                ]
            )
        self.assertEqual(exit_code, 1)
        receipt = json.loads((self.base / "failed-proof" / "receipt.json").read_text())
        self.assertEqual(receipt["execution"], "PASS")
        self.assertEqual(receipt["verification"], "FAIL")
        self.assertEqual(receipt["cleanup"], "COMPLETE")

    def test_known_cleanup_failure_is_fail_and_never_replayed(self):
        row = self.prepare()
        row["sandbox_live"] = True
        failure = result(
            process_exit=125, stderr=json.dumps({"code": "InUse", "message": "busy"})
        )
        with patch.object(run.measure, "run_command", return_value=failure) as command:
            self.campaign.cleanup(row)
            receipt = self.campaign.finish()
        self.assertEqual(command.call_count, 1)
        self.assertEqual(row["cleanup"], "FAIL")
        self.assertEqual(receipt["cleanup"], "FAIL")

    def test_execution_snapshot_matches_retained_receipt_bytes(self):
        self.prepare()
        answers = [
            result(),
            result({"ws": "unit:measured"}),
            result({"exit_code": 0}),
            result({"kind": "Committed"}),
            result(),
            result(),
            result(),
        ]
        output = self.base / "source-snapshot"
        with patch.object(run.measure, "run_command", side_effect=answers):
            self.campaign.execute(self.selection, output)
        receipt = json.loads((output / "receipt.json").read_text())
        self.assertEqual(
            {path.name for path in (output / "harness").iterdir()},
            set(run.HARNESS_FILES),
        )
        for name, expected in receipt["harness_sha256"].items():
            captured = output / "harness" / name
            self.assertEqual(run.digest(captured), expected)
            self.assertEqual(
                captured.read_bytes(), (run.harness_sources()[name]).read_bytes()
            )

    def test_receipt_retains_execution_hashes_when_harness_changes_later(self):
        row = self.prepare()
        answers = [
            result(),
            result({"ws": "unit:measured"}),
            result({"exit_code": 0}),
            result({"kind": "Committed"}),
            result(),
            result(),
            result(),
        ]
        snapshot = {
            "run.py": "run-pin",
            "cases.py": "case-pin",
            "measure.py": "measure-pin",
        }
        with (
            patch.object(run, "snapshot_harness", return_value=snapshot),
            patch.object(run.measure, "run_command", side_effect=answers),
        ):
            self.campaign.execute(self.selection, self.base / "hashed")
        with patch.object(run, "harness_hashes", return_value={"run.py": "new"}):
            self.campaign.finish()
        receipt = json.loads((self.base / "hashed" / "receipt.json").read_text())
        self.assertEqual(receipt["harness_sha256"], snapshot)
        self.assertEqual(receipt["matrix_index"], 0)
        self.assertEqual(
            self.campaign.state["attempt_sequence"][0]["harness_sha256"], snapshot
        )
        self.assertEqual(set(row["prepare_harness_sha256"]), set(run.HARNESS_FILES))

    def test_campaign_cursor_rejects_backward_configuration(self):
        later = run.selections(["C01"], ["docker"], ["sqlite"])[0]
        self.campaign.execute(later, self.base / "later-not-run")
        with self.assertRaisesRegex(run.Failure, "earlier than the campaign cursor"):
            self.campaign.execute(self.selection, self.base / "earlier")

    def test_infrastructure_shell_failure_is_known_and_does_not_infer_unknown(self):
        row = self.campaign.row(self.selection)
        with (
            patch.object(
                run.measure,
                "run_command",
                return_value=result(process_exit=1, stderr="failed"),
            ),
            self.assertRaises(run.Failure) as failure,
        ):
            self.campaign.call(
                row,
                "cache_control",
                ["control", "owned-id"],
                run.measure.Deadline.after(1),
                cli=False,
            )
        self.assertFalse(failure.exception.uncertain)
        self.assertFalse(row["uncertain"])
        self.assertIsNone(row["pending"])

    def test_unsettled_persisted_intent_is_never_replayed(self):
        row = self.campaign.row(self.selection)
        row["pending"] = {
            "phase": "store_create",
            "argv": ["layerfs", "store", "create", row["store"]],
        }
        self.campaign.persist()
        with patch.object(run.measure, "run_command") as command:
            self.campaign.finish()
        command.assert_not_called()
        self.assertEqual(row["cleanup"], "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
