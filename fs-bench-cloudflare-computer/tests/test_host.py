import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))

import cases  # noqa: E402
import host  # noqa: E402
import report  # noqa: E402


def script_payload(ns=1000):
    """What the frozen script prints for one complete single-sample run."""
    results = [
        {
            "scenario": name,
            "target": "computerd",
            "meanNs": ns + i,
            "medianNs": ns + i,
            "p95Ns": ns + i,
            "minNs": ns + i,
            "maxNs": ns + i,
            "samples": 1,
        }
        for i, name in enumerate(cases.SCENARIOS)
    ]
    return {
        "config": {"reps": 1, "warmup": 0, "randomizeTargets": 0, "mount": "/apfs/dir", "base": ""},
        "results": results,
    }


def sample(**overrides):
    """A recorded host-baseline.json, as src/host.py writes it."""
    times = [1000 + i for i in range(len(cases.SCENARIOS))]
    value = {
        "record": "host-baseline",
        "source_sha": "a" * 40,
        "campaign_id": "fbcc-host",
        "measured_at": "2026-11-07T09:00:00Z",
        "platform": "Darwin 26.4.1 arm64",
        "directory": "/Volumes/work-apfs",
        "filesystem": "apfs, not NFS",
        "tool_environment": {"BENCH_TOOL_ROOT": "/tools", "PATH": "/tools/bin:/usr/bin", "bash_sha256": "b" * 64},
        "script_sha256": cases.SCRIPT_SHA256,
        "body_sha256": cases.sha256(cases.LAYERFS_BODY),
        "settings": dict(cases.SETTINGS),
        "scenarios": [{"scenario": name, "ns": ns} for name, ns in zip(cases.SCENARIOS, times)],
        "sum_ns": sum(times),
        "one_sample": True,
        "status": "PASS",
        "reason": "",
        "elapsed_ns": 15_000_000_000,
    }
    value.update(overrides)
    return value


def campaign():
    """Eight rows where native is 2× the host sample on every scenario."""
    def row(scale):
        metrics = cases.parse_result(
            "B01",
            json.dumps(
                {
                    "config": {"reps": 1, "warmup": 0, "randomizeTargets": 0, "mount": "/m", "base": ""},
                    "results": [
                        {
                            "scenario": item["scenario"],
                            "target": "computerd",
                            "meanNs": item["ns"] * scale,
                            "medianNs": item["ns"] * scale,
                            "p95Ns": item["ns"] * scale,
                            "minNs": item["ns"] * scale,
                            "maxNs": item["ns"] * scale,
                            "samples": 1,
                        }
                        for item in sample()["scenarios"]
                    ],
                }
            ),
        )
        return {"execution": "PASS", "cleanup": "COMPLETE", "tool_metrics": metrics, "commit": {"kind": "UpToDate"}}

    rows = {}
    for machine, scale in (("docker", 3), ("native", 2), ("lima", 4), ("apple-container", 5)):
        for backend in ("sqlite", "postgresql"):
            rows[f"B01/{machine}/{backend}"] = row(scale)
    return {"source_sha": "a" * 40, "rows": rows, "campaigns": [], "superseded": []}


class Parse(unittest.TestCase):
    def test_receipt_parses_the_frozen_twelve(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            path.write_text(json.dumps(script_payload()))
            parsed = cases.parse_result("B01", path.read_text())
        self.assertEqual([item["scenario"] for item in parsed["scenarios"]], list(cases.SCENARIOS))
        self.assertEqual(parsed["sum_ns"], sum(1000 + i for i in range(12)))


class Preflight(unittest.TestCase):
    """The directory must be proven plain APFS outside LayerFS before any run."""

    def config(self, **extra):
        value = {
            "campaign_id": "c",
            "source_sha": "a" * 40,
            "home": "/Users/example/layerfs-home",
            "environment": {"XDG_CACHE_HOME": "/Users/example/cache"},
        }
        value.update(extra)
        return value

    def test_rejects_a_missing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            facts = host.preflight(Path(directory) / "absent", self.config(), Path(directory))
        self.assertFalse(facts["ok"])
        self.assertIn("not an existing directory", facts["reason"])

    def test_rejects_a_layerfs_owned_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "layerfs-home"
            inside = home / "workspaces" / "1"
            inside.mkdir(parents=True)
            facts = host.preflight(inside, self.config(home=str(home)), Path(directory))
        self.assertFalse(facts["ok"])
        self.assertIn("which this campaign's LayerFS owns", facts["reason"])

    def test_rejects_a_non_apfs_filesystem(self):
        real = host.filesystem

        def fake(path):
            return {"type": "exfat", "source": "/dev/disk4s1", "mountpoint": "/Volumes/EXFAT"}

        host.filesystem = fake
        try:
            with tempfile.TemporaryDirectory() as directory:
                facts = host.preflight(directory, self.config(), Path(directory) / "cache")
        finally:
            host.filesystem = real
        self.assertFalse(facts["ok"])
        self.assertIn("not apfs", facts["reason"])

    def test_rejects_a_layerfs_nfs_mount(self):
        real = host.filesystem

        def fake(path):
            return {"type": "nfs", "source": "127.0.0.1:/Users/example/store/ws", "mountpoint": "/Volumes/nfs"}

        host.filesystem = fake
        try:
            with tempfile.TemporaryDirectory() as directory:
                facts = host.preflight(directory, self.config(), Path(directory) / "cache")
        finally:
            host.filesystem = real
        self.assertFalse(facts["ok"])
        self.assertIn("127.0.0.1:", facts["reason"])
        self.assertIn("LayerFS NFS mount", facts["reason"])

    def test_rejects_another_network_mount(self):
        real = host.filesystem

        def fake(path):
            return {"type": "smbfs", "source": "//server/share", "mountpoint": "/Volumes/share"}

        host.filesystem = fake
        try:
            with tempfile.TemporaryDirectory() as directory:
                facts = host.preflight(directory, self.config(), Path(directory) / "cache")
        finally:
            host.filesystem = real
        self.assertFalse(facts["ok"])
        self.assertIn("not local APFS", facts["reason"])

    @unittest.skipUnless(sys.platform == "darwin", "APFS check is macOS-only")
    def test_accepts_a_plain_apfs_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            facts = host.preflight(directory, self.config(), Path(directory) / "cache")
        self.assertTrue(facts["ok"], facts["reason"])
        self.assertEqual(facts["details"]["type"], "apfs")
        self.assertFalse(facts["details"]["source"].startswith("127.0.0.1:"))

    def test_record_refuses_a_rejected_directory_without_number(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = host.record(self.config(), Path(directory) / "cache", Path(directory) / "absent")
        self.assertEqual(receipt["status"], "NOT_RUN")
        self.assertEqual(receipt["scenarios"], [])
        self.assertIsNone(receipt["sum_ns"])
        self.assertTrue(receipt["one_sample"])
        self.assertEqual(receipt["record"], "host-baseline")
        # The host body is the native rows' body, byte for byte.
        self.assertEqual(
            receipt["body_sha256"],
            cases.get_case("B01")["provenance"]["body_sha256"],
        )

    def test_record_refuses_a_directory_inside_a_row(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = host.record(self.config(), Path(directory), directory)
        self.assertEqual(receipt["status"], "NOT_RUN")
        self.assertEqual(receipt["scenarios"], [])
        self.assertIn("which this campaign's LayerFS owns", receipt["reason"])

    def test_cli_refuses_a_second_sample(self):
        with tempfile.TemporaryDirectory() as cache:
            (Path(cache) / "host-baseline.json").write_text(json.dumps(sample()))
            environment = Path(cache) / "campaign-config.json"
            environment.write_text(json.dumps(self.config()))
            done = subprocess.run(
                [sys.executable, str(SUITE / "src" / "host.py"),
                 "--environment", str(environment), "--cache", str(cache)],
                capture_output=True, text=True, check=False, timeout=30,
            )
        self.assertEqual(done.returncode, 2)
        self.assertIn("one host sample per campaign", done.stderr)


class Load(unittest.TestCase):
    def test_accepts_a_complete_sample(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "host-baseline.json"
            path.write_text(json.dumps(sample()))
            loaded = host.load(path, "a" * 40)
        self.assertTrue(loaded["available"])
        self.assertEqual(loaded["sum_ns"], sample()["sum_ns"])
        self.assertEqual(loaded["scenarios"]["find tree"], 1000 + 4)

    def test_rejects_a_short_scenario_set(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "host-baseline.json"
            path.write_text(json.dumps(sample(scenarios=sample()["scenarios"][:11])))
            loaded = host.load(path, "a" * 40)
        self.assertFalse(loaded["available"])
        self.assertIn("frozen twelve", loaded["reason"])

    def test_rejects_a_saturated_time(self):
        with tempfile.TemporaryDirectory() as directory:
            scenarios = sample()["scenarios"]
            scenarios[1]["ns"] = cases.SATURATED_NS
            path = Path(directory) / "host-baseline.json"
            path.write_text(json.dumps(sample(scenarios=scenarios)))
            loaded = host.load(path, "a" * 40)
        self.assertFalse(loaded["available"])
        self.assertIn("invalid scenario time", loaded["reason"])

    def test_rejects_another_product_commit_and_a_failed_sample(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "host-baseline.json"
            path.write_text(json.dumps(sample()))
            other = host.load(path, "b" * 40)
            self.assertFalse(other["available"])
            self.assertIn("not `b", other["reason"])
            path.write_text(json.dumps(sample(status="FAIL", reason="scenario rows differ", scenarios=[])))
            failed = host.load(path, "a" * 40)
            self.assertFalse(failed["available"])
            self.assertIn("host sample was FAIL", failed["reason"])

    def test_rejects_an_unreadable_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "host-baseline.json"
            path.write_text("not json")
            loaded = host.load(path, "a" * 40)
        self.assertFalse(loaded["available"])
        self.assertIn("unreadable", loaded["reason"])


class ReportWithHost(unittest.TestCase):
    def test_columns_subtract_the_host_sample(self):
        loaded = {
            "available": True,
            "campaign_id": "fbcc-host",
            "measured_at": "2026-11-07T09:00:00Z",
            "directory": "/Volumes/work-apfs",
            "filesystem": "apfs, not NFS",
            "tool_environment": {"bash_sha256": "b" * 64},
            "scenarios": {item["scenario"]: item["ns"] for item in sample()["scenarios"]},
            "sum_ns": sample()["sum_ns"],
        }
        text = report.render(campaign(), {"cleanup": "COMPLETE"}, {}, loaded)
        self.assertIn("Host baseline: one sample recorded by campaign `fbcc-host`", text)
        # native is 2× the host sample, Docker 3×: the subtraction and the ratios follow them.
        self.assertIn(
            "| create 1000 files | self-contained | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 "
            "| 0.33 | 0.0 | 0.67 | 1.33 | 1.67 |",
            text,
        )
        self.assertNotIn("| UNAVAILABLE |", text)

    def test_sum_row_totals_host_and_attributable_time(self):
        scenarios = [1_000_000] * len(cases.SCENARIOS)
        loaded = {
            "available": True,
            "campaign_id": "fbcc-host",
            "measured_at": "2026-11-07T09:00:00Z",
            "directory": "/Volumes/work-apfs",
            "filesystem": "apfs, not NFS",
            "tool_environment": {},
            "scenarios": dict(zip(cases.SCENARIOS, scenarios)),
            "sum_ns": 12_000_000,
        }
        state = {
            "source_sha": "a" * 40,
            "rows": {
                f"B01/{machine}/{backend}": {
                    "execution": "PASS",
                    "tool_metrics": cases.parse_result("B01", json.dumps(
                        {**script_payload(scale), "config": {"reps": 1, "warmup": 0, "randomizeTargets": 0, "mount": "/m", "base": ""}})),
                }
                for machine, scale in (("docker", 3_000_000), ("native", 5_000_000))
                for backend in ("sqlite", "postgresql")
            },
        }
        text = report.render(state, {"cleanup": "COMPLETE"}, {}, loaded)
        rows = [line for line in text.splitlines() if line.startswith("| Sum of scenarios |")]
        self.assertEqual(len(rows), 2)  # SQLite and PostgreSQL tables share the one host sample
        self.assertIn("| Sum of scenarios | — | 12.0 | 36.0 | 60.0 | — | — | 0.33 | 48.0 | 1.67 | — | — |", rows[0])

    def test_missing_host_renders_unavailable(self):
        text = report.render(campaign(), {"cleanup": "COMPLETE"}, {}, {"available": False, "reason": "no --host-baseline given"})
        self.assertIn("Host baseline: UNAVAILABLE — no --host-baseline given", text)
        self.assertIn("| create 1000 files | self-contained | UNAVAILABLE |", text)


if __name__ == "__main__":
    unittest.main()
