import json
import sys
import tempfile
import unittest
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))

import report  # noqa: E402


def probe(label, file_bytes, wal=0):
    return {"label": label, "total_bytes": file_bytes + wal, "file_bytes": file_bytes,
            "wal_bytes": wal, "allocated_bytes": file_bytes + wal}


def fake_row(case_id, backend, stores=1, branches=2, commits=3):
    out = {"case": case_id, "backend": backend, "execution": "PASS", "verification": "PASS",
           "cleanup": "COMPLETE", "calls": 10, "wall_ns_ineligible": 5_000_000_000,
           "workload": {"workload_sha256": "ab" * 32}, "stores": []}
    totals = {k: 0 for k in ("floor", "init_floor", "final", "net", "init", "growth", "commits",
                             "sum_new_stored", "sum_new_metadata", "head_logical",
                             "net_allocated")}
    counter = 0
    for s in range(stores):
        floor, init = probe("floor", 1000), probe("init_p01", 50_000)
        record = {"store": f"s{s}", "floor": floor, "init_floor": init, "probes": [floor, init],
                  "projects": [{"name": "p01", "after_init": 50_000, "branches": []}]}
        after = 50_000
        for i in range(branches):
            history = []
            for c in range(commits):
                counter += 1
                history.append({"id": f"c{counter}", "logical": 9000, "new_stored": 100 + c,
                                "new_canonical": 500, "new_metadata": 40})
            after += 400
            record["projects"][0]["branches"].append({
                "name": f"b{i:02d}", "from": "main", "verification": "PASS",
                "history": history, "listed_commits": commits,
                "sum_new_stored": sum(h["new_stored"] for h in history),
                "sum_new_metadata": 40 * commits, "marginal_bytes": 400, "after_branch": after})
        p = record["projects"][0]
        p["sum_new_stored"] = sum(x["sum_new_stored"] for x in p["branches"])
        p["sum_new_metadata"] = sum(x["sum_new_metadata"] for x in p["branches"])
        record["final"] = probe("final", after - 4096, 4096)
        record["accounting"] = {"init": 49_000}
        out["stores"].append(record)
        totals["floor"] += 1000
        totals["init_floor"] += 50_000
        totals["final"] += after
        totals["net"] += after - 1000
        totals["init"] += 49_000
        totals["growth"] += after - 50_000
        totals["commits"] += branches * commits
        totals["sum_new_stored"] += p["sum_new_stored"]
        totals["sum_new_metadata"] += p["sum_new_metadata"]
    totals["unattributed_after_init"] = totals["growth"] - totals["sum_new_stored"] - totals["sum_new_metadata"]
    totals["complete"] = True
    out["totals"] = totals
    return out


class Report(unittest.TestCase):
    def test_tables_render_and_gain(self):
        rows = {("H05", "sqlite"): fake_row("H05", "sqlite"),
                ("H06", "sqlite"): fake_row("H06", "sqlite", stores=2, branches=1),
                ("H01", "sqlite"): fake_row("H01", "sqlite", branches=1, commits=120)}
        summary = report.summary_table(rows)
        self.assertIn("NOT_RUN", summary)  # PostgreSQL rows absent
        self.assertIn("| H05 | SQLite | PASS |", summary)
        self.assertIn("Cross-project gain", report.project_section(rows))
        self.assertIn("101–120", report.h01_section(rows))
        self.assertIn("Own Σ", report.branch_section(rows, "H05"))

    def test_main_writes_report(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root / "results" / "H03-sqlite").mkdir(parents=True)
            (root / "results" / "H03-sqlite" / "result.json").write_text(
                json.dumps(fake_row("H03", "sqlite")))
            (root / "refs.json").write_text(json.dumps({"input_sha256": "x", "cases": {"H03": {
                "total": {"states": 3, "logical_bytes": 27000,
                          **{k: {"bytes": 2000} for k in ("whole_file_unique", "tar_zstd",
                                                          "git_pack", "cdc_oracle")}}}}}))
            env = {"source_sha": "a" * 40, "artifacts": {k: "x" for k in (
                "cli_sha256", "daemon_sha256", "linux_bundle_sha256", "sandbox_image_tag",
                "sandbox_image", "base_image", "model_sha256")},
                "postgresql": {"server_image": "pg"}}
            (root / "env.json").write_text(json.dumps(env))
            (root / "notes.md").write_text("**Outcome.**\n\n## Cleanup\n\nDone.\n")
            out = root / "report.md"
            report.main(["--results", str(root / "results"), "--references", str(root / "refs.json"),
                         "--environment", str(root / "env.json"), "--notes", str(root / "notes.md"),
                         "--output", str(out)])
            text = out.read_text()
            self.assertTrue(text.startswith("# fs-storage-history report\n\n**Outcome.**"))
            self.assertIn("## Cleanup", text)
            self.assertIn("| H03 | SQLite |", text)


if __name__ == "__main__":
    unittest.main()
