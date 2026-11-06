"""fs-storage-quick workload, lifecycle, export/compare and report contracts; no LayerFS."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared/src"))
sys.path.insert(0, str(ROOT / "fs-storage-quick/src"))
import cases  # noqa: E402
import report  # noqa: E402
import results  # noqa: E402
import rows  # noqa: E402

gen, model = cases.gen, cases.model
BASE = Path(os.environ.get("FSQ_BASE", Path.home() / ".cache/fs-opt-84/quick/base-157"))


class InDirectory:
    def __enter__(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.previous = os.getcwd()
        os.chdir(self.temporary.name)
        return Path(self.temporary.name)

    def __exit__(self, *exc):
        os.chdir(self.previous)
        self.temporary.cleanup()


class WorkloadTests(unittest.TestCase):
    def test_frozen_counts(self):
        self.assertEqual(cases.WORKLOAD_VERSION, "fs-storage-quick-v1")
        self.assertEqual(cases.CASE_IDS, ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6"))
        self.assertEqual({c: cases.commits(c) for c in cases.CASE_IDS},
                         {"Q1": 1, "Q2": 13, "Q3": 13, "Q4": 13, "Q5": 6, "Q6": 23})
        self.assertEqual((gen.Q1_FILES, gen.TEXT_FILES, gen.TEXT_EDITS, gen.LARGE_BYTES),
                         (2000, 25, 12, 32 << 20))
        self.assertEqual((cases.Q6_INITS, cases.Q6_EDIT_COMMITS, cases.Q6_IDENTICAL), (1, 20, 3))

    def test_streams_are_keyed_by_the_suite_version(self):
        self.assertEqual(gen.Text("t").lines_to(3000), gen.Text("t").lines_to(3000))
        self.assertEqual(gen.shake("x", 16), __import__("hashlib").shake_256(b"fs-storage-quick-v1|x").digest(16))

    def test_text_cases_share_content_and_differ_in_method(self):
        finals = {}
        for case in ("Q2", "Q3", "Q4"):
            with InDirectory() as root:
                gen.step(case, "create")
                name = "f000.v00.txt" if case == "Q4" else "f000.txt"
                inode = (root / "d00" / name).stat().st_ino
                gen.step(case, "edit:01")
                if case == "Q2":
                    self.assertEqual((root / "d00/f000.txt").stat().st_ino, inode)
                elif case == "Q4":
                    self.assertFalse((root / "d00/f000.v00.txt").exists())
                    self.assertTrue((root / "d00/f000.v01.txt").exists())
                finals[case] = sorted(p.read_bytes() for p in root.rglob("*.txt"))
        self.assertEqual(finals["Q2"], finals["Q3"])
        self.assertEqual(finals["Q2"], finals["Q4"])

    def test_pins_match_the_scripts(self):
        self.assertIsNotNone(cases.PINS_SHA256, "pins.json must match gen.py and model.py")
        self.assertEqual(set(cases.ORACLE), set(cases.CASE_IDS))
        self.assertEqual(cases.ORACLE["Q2"]["sha256"], cases.ORACLE["Q3"]["sha256"])

    def test_q2_oracle_reproduces(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(gen.oracle("Q2", os.path.join(directory, "x")), cases.ORACLE["Q2"])

    def test_commands_check_script_hashes(self):
        self.assertIn(cases.GEN_SHA256, cases.step_command("Q1", "files"))
        self.assertIn(cases.MODEL_SHA256, cases.apply_command("abc"))
        with self.assertRaises(ValueError):
            cases.step_command("Q1", "files; rm -rf /")

    def test_namespace_paths_round_trip(self):
        paths = ["b/x.txt", "a.txt", "a.txt"]
        self.assertEqual(gen.decode_paths(gen.encode_paths(paths)), ["a.txt", "b/x.txt"])

    @unittest.skipUnless(BASE.is_dir(), "extracted base tree not present")
    def test_q6_plan_matches_pins_and_disk(self):
        state = cases.load_base(BASE)
        plan = cases.q6_plan(state)
        for key in ("lane_head", "shared_head", "lane_check", "shared_check"):
            self.assertEqual(plan[key], cases.PINS["q6"][key])
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory) / "t"
            import shutil

            shutil.copytree(BASE, tree, symlinks=True)
            model.apply_ops(model.decode_ops(plan["shared_step"]), str(tree))
            self.assertEqual(gen.namespace(plan["shared_touched"], str(tree)), plan["shared_check"])


CONFIG = {
    "campaign_id": "t", "empty_source": "/empty", "base_dir": "/base",
    "machines": {"docker": {"name": "docker"}},
    "postgresql": {"password_env": "PW"}, "artifacts": {"base_image": "img"},
}


class SpecTests(unittest.TestCase):
    def test_generator_rows(self):
        spec = cases.spec("Q2", "sqlite", "t-q2s", CONFIG)
        ops = [s["op"] for s in spec["steps"]]
        self.assertEqual(ops.count("commit"), 13)
        self.assertEqual(ops[-3:], ["unmount", "verify", "close"])
        self.assertEqual(spec["floor_project"]["project"], "t-q2s/p")

    def test_q6_row(self):
        plan = {"lane_steps": ["x"] * cases.Q6_EDIT_COMMITS, "lane_touched": ["a"], "lane_check": {},
                "shared_step": "y", "shared_touched": ["b"], "shared_check": {}, "base_logical": 10}
        spec = cases.spec("Q6", "postgresql", "t-q6p", CONFIG, "postgresql://u@h:1/d", plan)
        self.assertEqual([i["label"] for i in spec["inits"]], ["init_p1"])
        self.assertEqual(spec["floor_project"]["project"], "t-q6p/e")
        ops = [s["op"] for s in spec["steps"]]
        self.assertEqual(ops.count("commit"), cases.Q6_EDIT_COMMITS + cases.Q6_IDENTICAL)
        self.assertEqual(ops.count("verify"), 1 + cases.Q6_IDENTICAL)  # every head by content
        self.assertEqual(len(spec["collect"]), 1 + cases.Q6_IDENTICAL)
        self.assertEqual(spec["init_logical"], 10)


class FakeCampaign:
    """Answers CLI argv with canned JSON; records every call."""

    def __init__(self, fail_check=False):
        self.config = {"storage": {}}
        self.state = {"rows": {}}
        self.calls = []
        self.commits = 0
        self.file_bytes = 200_000

    def persist(self):
        pass

    def call(self, row, phase, argv, deadline, cli=True):
        self.calls.append(argv)
        row.setdefault("commands", []).append({"phase": phase, "elapsed_ns": 5_000_000, "child_cpu_ns": 1_000_000})
        verb = tuple(argv[:2])
        if verb == ("workspace", "mount"):
            return {"ws": f"{argv[2]}:{argv[-1]}"}
        if verb == ("workspace", "exec"):
            out = json.dumps(cases.ORACLE["Q1"]) if "manifest" in argv[3] else ""
            return {"exit_code": 0, "stdout": out}
        if verb == ("workspace", "commit"):
            self.commits += 1
            self.file_bytes += 40_960
            return {"kind": "Committed", "commit": {"id": f"c{self.commits}", "logical": 100, "new_canonical": 90,
                                                    "new_stored": 50, "new_metadata": 10}}
        if verb == ("store", "status"):
            return {"kind": "sqlite", "state": "idle", "holders": [], "machine": "docker",
                    "file": {"exists": True, "bytes": self.file_bytes, "wal_bytes": 32 + 4120 * 3}}
        if verb == ("commit", "list"):
            items = [{"id": f"c{i}", "parent": f"c{i - 1}" if i > 1 else None, "logical": 100,
                      "new_canonical": 90, "new_stored": 50, "new_metadata": 10}
                     for i in range(self.commits, 0, -1)]
            return {"items": items, "has_more": False}
        return {}


class LifecycleTests(unittest.TestCase):
    def run_q1(self, defer=False, check=None):
        campaign = FakeCampaign()
        row = {"id": "Q1/docker/sqlite", "case": "Q1", "backend": "sqlite", "pending": None, "uncertain": False,
               "execution": "NOT_RUN", "verification": "NOT_RUN", "cleanup": "NOT_RUN"}
        campaign.state["rows"][row["id"]] = row
        spec = cases.spec("Q1", "sqlite", "t-q1s", CONFIG)
        spec["defer_release"] = defer
        if check:
            for step in spec["steps"]:
                if step["op"] == "verify":
                    step["check"] = check
        rows.run_row(campaign, row, spec)
        return campaign, row

    def test_order_verify_before_final_probe_then_release(self):
        campaign, row = self.run_q1()
        self.assertEqual((row["execution"], row["verification"], row["cleanup"]), ("PASS", "PASS", "COMPLETE"))
        verbs = [tuple(a[:2]) for a in campaign.calls]
        self.assertLess(max(i for i, v in enumerate(verbs) if v == ("workspace", "exec")),
                        max(i for i, v in enumerate(verbs) if v == ("store", "status")))
        self.assertEqual(verbs[-1], ("store", "remove"))
        summary = results.row_summary(row)
        self.assertEqual(summary["net_bytes"], 40_960)
        self.assertEqual(summary["final"]["wal_frames"], 3)
        self.assertEqual(summary["curve"][0]["wall_ms_ineligible"], 5.0)

    def test_mismatch_is_recorded_and_still_probed(self):
        def bad(result):
            raise ValueError("differs")

        campaign, row = self.run_q1(check=bad)
        self.assertEqual((row["execution"], row["verification"]), ("PASS", "FAIL"))
        self.assertIn("final", row["probes"])

    def test_deferred_release_and_late_probe(self):
        campaign, row = self.run_q1(defer=True)
        self.assertEqual(row["cleanup"], rows.DEFERRED)
        self.assertNotIn(("store", "remove"), [tuple(a[:2]) for a in campaign.calls])
        slept = []
        done = rows.late_probe(campaign, 75, sleep=slept.append)
        self.assertEqual(len(done), 1)
        self.assertTrue(slept and 70 < slept[0] <= 75)
        self.assertEqual(row["late_probe"]["status"], "MEASURED")
        self.assertIn("late", row["probes"])
        self.assertEqual(row["cleanup"], "COMPLETE")
        self.assertEqual(tuple(campaign.calls[-1][:2]), ("store", "remove"))


def summary(case, backend, net=1_000_000, stored=500_000, meta=10_000, commits=10, raw=9_000_000):
    return {"id": f"{case}/docker/{backend}", "case": case, "backend": backend, "execution": "PASS",
            "verification": "PASS", "cleanup": "COMPLETE", "commits": commits, "raw": raw,
            "sum_new_canonical": 2_000_000, "sum_new_stored": stored, "sum_new_metadata": meta,
            "sum_new_payload": stored - meta, "net_bytes": net, "net_file_bytes": net - 4_194_304 if backend == "sqlite" else None,
            "net_wal_bytes": 4_194_304 if backend == "sqlite" else None, "late_net_bytes": None,
            "init_logical": 0, "curve": [{"branch": "p@lane", "logical": 1, "new_canonical": 1, "new_stored": 1,
                                         "new_metadata": 1, "cli_cpu_ms_ineligible": 1.0}] * commits,
            "diagnostics": {"row_wall_s": 3.0}, "final": {"total_bytes": net}, "floor": {"total_bytes": 0}}


def export_of(rows_):
    return {"workload_version": "fs-storage-quick-v1", "source_sha": "a" * 40, "campaign_id": "x",
            "rows": {f"{r['case']}/{r['backend']}": r for r in rows_},
            "wall_ineligible": {"sqlite": {"matrix_wall_s": 80.0, "sum_row_wall_s": 79.0, "rows": 1}}}


class CompareTests(unittest.TestCase):
    def test_wal_frames(self):
        self.assertEqual(results.wal_frames(0), 0)
        self.assertEqual(results.wal_frames(32 + 4120 * 1018), 1018)
        self.assertIsNone(results.wal_frames(100))

    def test_noise_bands_and_verdicts(self):
        base = export_of([summary("Q1", "sqlite"), summary("Q1", "postgresql")])
        cand = export_of([summary("Q1", "sqlite", net=1_000_000 + 25 * 4096, meta=10_000 + 160, stored=500_160),
                          summary("Q1", "postgresql", net=1_000_000 - 22 * 8192 - 1)])
        out = results.compare(base, cand)
        verdicts = {(r["key"], m["metric"]): m["verdict"] for r in out["rows"] for m in r["metrics"]}
        self.assertEqual(verdicts[("Q1/sqlite", "Store file+WAL net")], "same")  # exactly 25 pages
        self.assertEqual(verdicts[("Q1/sqlite", "Σ new_metadata")], "same")  # 16 B × 10 Commits
        self.assertEqual(verdicts[("Q1/postgresql", "Store schema net")], "lower")
        self.assertEqual(out["regressions"], [])
        worse = export_of([summary("Q1", "sqlite", meta=10_161, stored=500_161), summary("Q1", "postgresql")])
        out = results.compare(base, worse)
        self.assertEqual(len(out["regressions"]), 2)  # new_stored and new_metadata beyond 160 B
        self.assertIn("Σ payload", [m["metric"] for m in out["rows"][0]["metrics"]])

    def test_workload_mismatch_is_not_comparable(self):
        base = export_of([summary("Q1", "sqlite")])
        cand = export_of([summary("Q1", "sqlite", raw=1)])
        out = results.compare(base, cand)
        self.assertTrue(out["not_comparable"])
        self.assertIn("compare", results.compare_markdown(out, base, cand))

    def test_report_renders(self):
        data = export_of([summary(c, b) for c in ("Q1", "Q2") for b in ("sqlite", "postgresql")])
        data["wall_ineligible"]["postgresql"] = {"matrix_wall_s": 100.0, "sum_row_wall_s": 99.0, "rows": 2}
        text = report.render(data, "## Limits\n\nnone")
        self.assertTrue(text.startswith("# fs-storage-quick — aaaaaaaaaa\n\n**4 of 4"))
        self.assertIn("Raw ÷ stored", text)
        self.assertIn("UNAVAILABLE", text)


if __name__ == "__main__":
    unittest.main()
