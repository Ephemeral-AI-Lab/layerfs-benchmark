import hashlib
import json
import sys
import unittest
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))

import cases  # noqa: E402
import report  # noqa: E402


def payload(mount="/workspaces/1", **overrides):
    results = [
        {
            "scenario": name,
            "target": "computerd",
            "meanNs": 1000 + i,
            "medianNs": 1000 + i,
            "p95Ns": 1000 + i,
            "minNs": 1000 + i,
            "maxNs": 1000 + i,
            "samples": 1,
        }
        for i, name in enumerate(cases.SCENARIOS)
    ]
    value = {
        "config": {"reps": 1, "warmup": 0, "randomizeTargets": 0, "mount": mount, "base": ""},
        "results": results,
    }
    value.update(overrides)
    return value


class FrozenScript(unittest.TestCase):
    def test_vendored_script_matches_pin(self):
        data = (SUITE / "image" / "fs-bench.sh").read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), cases.SCRIPT_SHA256)
        blob = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
        self.assertEqual(blob, cases.SOURCE_BLOB)

    def test_every_scenario_is_in_the_script(self):
        text = (SUITE / "image" / "fs-bench.sh").read_text()
        for name in cases.SCENARIOS:
            self.assertIn(f'run_scenario "{name}"', text)

    def test_filter_selects_exactly_twelve(self):
        text = (SUITE / "image" / "fs-bench.sh").read_text()
        names = [line.split('"')[1] for line in text.splitlines() if line.startswith("  run_scenario \"") or line.startswith("run_scenario \"")]
        selected = [n for n in names if any(p in n for p in cases.SETTINGS["SCENARIOS"].split(","))]
        self.assertEqual(selected, list(cases.SCENARIOS))


class Body(unittest.TestCase):
    def test_body_pins_settings_and_hash(self):
        self.assertIn('MOUNT="$PWD"', cases.LAYERFS_BODY)
        for key in ("REPS=1", "WARMUP=0", "RANDOMIZE_TARGETS=0", "BASE=''", cases.SCRIPT_SHA256):
            self.assertIn(key, cases.LAYERFS_BODY)

    def test_case_provenance(self):
        case = cases.get_case("B01")
        self.assertEqual(case["exec_argv"][:3], ["/bin/bash", "-o", "pipefail"])
        self.assertEqual(case["provenance"]["scenarios"], list(cases.SCENARIOS))
        with self.assertRaises(ValueError):
            cases.get_case("B01", verify=True)
        with self.assertRaises(ValueError):
            cases.get_case("C01")


class Parse(unittest.TestCase):
    def test_accepts_twelve_single_samples(self):
        result = cases.parse_result("B01", json.dumps(payload()))
        self.assertEqual(len(result["scenarios"]), 12)
        self.assertEqual(result["sum_ns"], sum(1000 + i for i in range(12)))

    def test_rejects_failed_scenario(self):
        value = payload()
        value["results"].pop(4)
        with self.assertRaisesRegex(ValueError, "find tree"):
            cases.parse_result("B01", json.dumps(value))

    def test_rejects_saturated_or_repeated_samples(self):
        value = payload()
        for key in ("meanNs", "medianNs", "p95Ns", "minNs", "maxNs"):
            value["results"][1][key] = cases.SATURATED_NS
        with self.assertRaises(ValueError):
            cases.parse_result("B01", json.dumps(value))
        value = payload()
        value["results"][0]["samples"] = 2
        with self.assertRaises(ValueError):
            cases.parse_result("B01", json.dumps(value))

    def test_rejects_warmup_exit_and_garbage(self):
        value = payload()
        value["config"]["warmup"] = 1
        with self.assertRaises(ValueError):
            cases.parse_result("B01", json.dumps(value))
        with self.assertRaises(ValueError):
            cases.parse_result("B01", json.dumps(payload()), exit_code=97)
        with self.assertRaises(ValueError):
            cases.parse_result("B01", "not json")


class Report(unittest.TestCase):
    def test_render_uses_docker_baseline_per_database(self):
        fast = cases.parse_result("B01", json.dumps(payload()))
        slow_payload = payload()
        for item in slow_payload["results"]:
            for key in ("meanNs", "medianNs", "p95Ns", "minNs", "maxNs"):
                item[key] *= 2
        slow = cases.parse_result("B01", json.dumps(slow_payload))
        state = {
            "source_sha": "a" * 40,
            "rows": {
                "B01/docker/sqlite": {"execution": "PASS", "cleanup": "COMPLETE", "tool_metrics": fast, "commit": {"kind": "UpToDate"}},
                "B01/lima/sqlite": {"execution": "PASS", "cleanup": "COMPLETE", "tool_metrics": slow},
                "B01/native/sqlite": {"execution": "NOT_RUN", "cleanup": "NOT_RUN", "reason": "needs bash 4"},
            },
        }
        text = report.render(state, {"cleanup": "COMPLETE"}, {})
        self.assertIn("**2 of 8 rows ran all twelve scenarios", text)
        self.assertIn("| create 1000 files | self-contained | 0.0 | — | 0.0 | — | — | 2.00 | — |", text)
        self.assertIn("needs bash 4", text)
        self.assertIn("UpToDate", text)
        self.assertLess(text.index("Scenario times, SQLite"), text.index("Scenario times, PostgreSQL"))


if __name__ == "__main__":
    unittest.main()
