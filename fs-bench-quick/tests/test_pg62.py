"""layerfs-project#62 harness additions: arms, order, observer, new cases, report."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "src"
SHARED = Path(__file__).resolve().parents[2] / "shared" / "src"
sys.path.insert(0, str(SRC))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run = load("quick_run_pg62", SRC / "run.py")
cases = load("quick_cases_pg62", SRC / "cases.py")
pgrtt = load("quick_pgrtt", SRC / "pgrtt.py")
report = load("shared_report_pg62", SHARED / "report.py")


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


class MatrixTests(unittest.TestCase):
    def test_default_matrix_keeps_original_order_and_adds_cases(self):
        rows = run.selections()
        self.assertEqual(rows[0]["id"], "C01/native/sqlite")
        self.assertEqual(rows[95]["id"], "C12/apple-container/postgresql")
        self.assertEqual(rows[96]["id"], "C13/native/sqlite")
        self.assertNotIn("pg-colocated", {row["backend"] for row in rows})

    def test_colocated_arm_and_alternating_order(self):
        rows = run.selections(
            ["C01", "C02"], ["native", "docker"], colocated=("docker",), alternate=True
        )
        self.assertEqual(
            [row["id"] for row in rows],
            [
                "C01/native/sqlite",
                "C01/native/postgresql",
                "C01/docker/sqlite",
                "C01/docker/postgresql",
                "C01/docker/pg-colocated",
                "C02/native/postgresql",
                "C02/native/sqlite",
                "C02/docker/pg-colocated",
                "C02/docker/postgresql",
                "C02/docker/sqlite",
            ],
        )
        self.assertEqual(run.kind("pg-colocated"), "postgresql")
        self.assertEqual(
            run.database_key(rows[4]), "C01/docker/pg-colocated"
        )
        self.assertEqual(run.database_key(rows[3]), "C01/docker")


class CaseTests(unittest.TestCase):
    def test_original_cases_unchanged_and_new_cases_versioned(self):
        self.assertEqual(cases.get_case("C01")["body"], cases._files_body(1000))
        self.assertEqual(
            cases.get_case("C01")["provenance"]["workload_version"], "R7-byte-exact-v1"
        )
        for case_id in cases.PG62_CASES:
            case = cases.get_case(case_id)
            self.assertEqual(case["provenance"]["workload_version"], "pg62-v1")
            self.assertIsNone(case["verifier"])
        self.assertEqual(cases.get_case("C14")["body"], "true")
        self.assertIn("seq 1 100)", cases.get_case("C15")["body"])
        self.assertEqual(cases.get_case("C16")["performance_budget_s"], 25)
        self.assertNotIn("performance_budget_s", cases.get_case("C15"))
        self.assertIn("echo 2 > b", cases.get_case("C13")["followup_command"])
        self.assertEqual(cases.get_case("C18")["setup"], cases._files_body(1000))
        self.assertIn("stat f{1..1000}", cases.get_case("C18")["body"])

    def test_random_setup_is_non_repeating_and_matches_pin(self):
        with tempfile.TemporaryDirectory() as root:
            case = cases.get_case("C17", verify=True)
            subprocess.run(case["setup_argv"], cwd=root, check=True, timeout=30)
            data = (Path(root) / "rand").read_bytes()
            self.assertEqual(len(data), 64 * 1024 * 1024)
            self.assertNotEqual(data[:1 << 20], data[1 << 20 : 2 << 20])
            proof = subprocess.run(
                ["/bin/bash", "-o", "pipefail", "-c", case["verifier"]],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertIn("VERIFY OK", proof.stdout)


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        (base / "empty").mkdir()
        cli = base / "layerfs"
        cli.write_text("fake artifact, never executed")
        cli.chmod(0o700)
        self.config = {
            "campaign_id": "unit",
            "source_sha": "a" * 40,
            "cli": str(cli),
            "home": str(base / "home"),
            "empty_source": str(base / "empty"),
            "machines": {m: {"ready": True, "name": m} for m in run.MACHINES},
            "artifacts": {"cli_sha256": run.digest(cli)},
            "order": "alternate",
            "postgresql": {
                "password_env": "BENCH_UNIT_PG_PASSWORD",
                "disposal_resource": "pg",
                "colocated_machines": ["docker"],
                "databases": {
                    "C13/docker/pg-colocated": "postgresql://bench@10.0.0.2:5432/q_c13_colo?sslmode=disable"
                },
                "observer": {
                    "admin_argv": ["admin", "psql"],
                    "log_argv": ["logs", "--since", "{since}", "server"],
                },
            },
            "resources": [{"id": "pg", "owned": True, "release_argv": ["drop"]}],
            "shared_infrastructure": True,
        }
        self.base = base
        self.campaign = run.Campaign(self.config, base / "cache")

    def test_phase_boundaries_counts_and_second_commit(self):
        selection = next(
            row for row in self.campaign.state["matrix"]
            if row["id"] == "C13/docker/pg-colocated"
        )
        row = self.campaign.row(selection)
        row["preparation"] = "READY"
        row["store_live"] = True
        row["workload"] = {
            k: v for k, v in cases.get_case("C13")["provenance"].items() if k != "verification"
        }
        separator = "\x1f"
        snapshot = result()
        snapshot["stdout"] = (
            separator.join(["total", "42", "7", "3.5", "40"])
            + "\n"
            + separator.join(["top", "30", "1.0", "30", "SELECT $1"])
            + "\n"
        )
        log = "\n".join(
            [
                "2026-11-06 00:00:00.000 UTC [9] db=postgres LOG:  pg62-boundary row=C13/docker/pg-colocated next=sandbox_create",
                "2026-11-06 00:00:00.100 UTC [10] db=[unknown] LOG:  connection received: host=172.17.0.10 port=1",
                "2026-11-06 00:00:00.101 UTC [10] db=q_c13_colo LOG:  connection authorized: user=bench database=q_c13_colo",
                "2026-11-06 00:00:00.102 UTC [11] db=[unknown] LOG:  connection received: host=172.17.0.1 port=2",
                "2026-11-06 00:00:00.103 UTC [11] db=other LOG:  connection authorized: user=bench database=other",
                "2026-11-06 00:00:00.200 UTC [12] db=postgres LOG:  pg62-boundary row=C13/docker/pg-colocated next=measured_mount",
                "2026-11-06 00:00:00.300 UTC [13] db=[unknown] LOG:  connection received: host=172.17.0.12 port=3",
                "2026-11-06 00:00:00.301 UTC [13] db=q_c13_colo LOG:  connection authorized: user=bench database=q_c13_colo",
                "2026-11-06 00:00:00.400 UTC [14] db=postgres LOG:  pg62-boundary row=C13/docker/pg-colocated next=end",
                "2026-11-06 00:00:00.500 UTC [15] db=[unknown] LOG:  connection received: host=1.1.1.1 port=4",
                "2026-11-06 00:00:00.501 UTC [15] db=q_c13_colo LOG:  connection authorized: user=bench database=q_c13_colo",
            ]
        )
        calls = []

        def answer(argv, deadline, **kwargs):
            calls.append(argv)
            if argv[0] == "admin":
                return snapshot if any("'total'" in part for part in argv) else result()
            if argv[0] == "logs":
                return result(stdout="", stderr=log)
            phase = argv[1:3]
            if phase == ["workspace", "mount"]:
                return result({"ws": "unit:measured"})
            if phase == ["workspace", "exec"]:
                return result({"exit_code": 0})
            if phase == ["workspace", "commit"]:
                return result({"kind": "Committed"})
            return result()

        with (
            patch.dict(run.os.environ, {"BENCH_UNIT_PG_PASSWORD": "x"}),
            patch.object(run.measure, "run_command", side_effect=answer),
        ):
            self.campaign.execute(selection, self.base / "out")
        self.assertEqual(row["execution"], "PASS", row.get("reason"))
        cli = [argv[1:3] for argv in calls if argv[0] not in ("admin", "logs")]
        self.assertEqual(
            cli,
            [
                ["sandbox", "create"],
                ["workspace", "mount"],
                ["workspace", "exec"],
                ["workspace", "commit"],
                ["workspace", "exec"],
                ["workspace", "commit"],
                ["workspace", "unmount"],
                ["sandbox", "close"],
                ["store", "disconnect"],
            ],
        )
        self.assertEqual(row["commit_2"]["kind"], "Committed")
        execs = [argv[-1] for argv in calls if argv[1:3] == ["workspace", "exec"]]
        self.assertIn("echo 1 > a", execs[0])
        self.assertIn("echo 2 > b", execs[1])
        markers = [
            part.split("next=")[1].split("'")[0]
            for argv in calls
            if argv[0] == "admin"
            for part in argv
            if "pg62-boundary" in part
        ]
        self.assertEqual(
            markers,
            [
                "sandbox_create",
                "measured_mount",
                "exec",
                "commit",
                "followup_exec",
                "commit_2",
                "unmount",
                "cleanup",
                "end",
            ],
        )
        first_admin = next(argv for argv in calls if argv[0] == "admin")
        self.assertTrue(any("pg_stat_statements_reset" in p for p in first_admin))
        self.assertFalse(any("'total'" in p for p in first_admin))
        phases = row["pg_phases"]
        self.assertEqual(set(phases), {m for m in markers if m != "end"})
        self.assertEqual(phases["commit_2"]["statements"], 42)
        self.assertEqual(phases["commit_2"]["top"][0]["query"], "SELECT $1")
        self.assertEqual(phases["sandbox_create"]["connections"], 1)
        self.assertEqual(phases["sandbox_create"]["sources"], {"172.17.0.10": 1})
        self.assertEqual(phases["measured_mount"]["connections"], 1)
        self.assertEqual(phases["exec"]["connections"], 0)
        self.assertEqual(row["control_overhead_ns"], 100)  # nine boundaries + logs
        self.assertIn("load_1m", row)

    def test_sqlite_rows_get_marker_only_boundaries(self):
        selection = run.selections(["C01"], ["native"], ["sqlite"])[0]
        row = self.campaign.row(selection)
        with patch.object(run.measure, "run_command", return_value=result()) as command:
            self.campaign.boundary(row, "exec", run.measure.Deadline.after(5))
        argv = command.call_args.args[0]
        self.assertEqual(sum(part == "-c" for part in argv), 1)
        self.assertIn("pg62-boundary row=C01/native/sqlite next=exec", argv[-1])


class ClientAndReportTests(unittest.TestCase):
    def test_rtt_statistics(self):
        values = list(range(1, 11))
        summary = pgrtt.stats(values)
        self.assertEqual((summary["median_ns"], summary["p90_ns"]), (5, 9))
        self.assertIsNone(pgrtt.stats([]))

    def test_report_mount_unmount_counts_deltas_and_overhead(self):
        matrix = run.selections(["C13"], ["docker"], colocated=("docker",))
        timings = {
            "sandbox_create": 300_000_000,
            "measured_mount": 50_000_000,
            "exec": 10_000_000,
            "commit": 20_000_000,
            "commit_2": 15_000_000,
            "unmount": 30_000_000,
            "sandbox_close": 40_000_000,
        }
        rows = {}
        for item in matrix:
            row = {
                **item,
                "execution": "PASS",
                "cleanup": "COMPLETE",
                "timings_ns": dict(timings),
                "performance_invocation_elapsed_ns": 600_000_000,
                "control_overhead_ns": 100_000_000,
                "load_1m": 3.5,
            }
            if item["backend"] == "sqlite":
                row["timings_ns"]["store_remove"] = 5_000_000
            else:
                row["timings_ns"]["store_disconnect"] = 6_000_000
                row["timings_ns"]["measured_mount"] = 90_000_000
                row["pg_phases"] = {"commit": {"statements": 50, "connections": 1}}
            rows[item["id"]] = row
        state = {"matrix": matrix, "rows": rows, "source_sha": "a" * 40}
        calibration = [
            {
                "location": "host",
                "route": "host/published",
                "target": {"host": "127.0.0.1", "port": 1},
                "results": {
                    "trust": {
                        "resolve_ns": 1000,
                        "peer": "127.0.0.1",
                        "select1": {"median_ns": 210_000, "p90_ns": 250_000},
                    }
                },
            }
        ]
        text = report.render(
            "fs-bench-quick", state, {"cleanup": "COMPLETE"},
            {"calibration_results": calibration},
        )
        self.assertIn("| Mount ms | Exec ms | Commit ms | Commit 2 ms | Unmount ms | Close ms | Store release ms | End-to-end ms |", text)
        self.assertIn("| docker | sqlite | PASS | COMPLETE | 3.50 | 300.00 | 50.00 |", text)
        self.assertIn("| 500.00 |", text)  # end-to-end minus control overhead
        self.assertIn("| docker | postgresql | 1 | +0.0 | +40.0 |", text)
        self.assertIn("| Machine | Database | Commit | Statements | Connections |", text)
        self.assertIn("| docker | pg-colocated | 50 / 1 | 50 | 1 | 0.0 |", text)
        self.assertIn("| 0.210 | 0.250 |", text)
        summed = report.render(
            "fs-bench-quick", state, {"cleanup": "COMPLETE"}, {"end_to_end": "phase_sum"}
        )
        # 300 + 50 + 10 + 20 + 15 + 30 + 40 + 5 ms of measured calls, no gaps.
        self.assertIn("| 470.00 |", summed)


if __name__ == "__main__":
    unittest.main()
