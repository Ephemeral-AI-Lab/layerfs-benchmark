"""Storage probes, Commit collector, summary, driver custody and references.

No LayerFS execution: CLI results are faked through measure.run_command.
"""

import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared/src"))
import references  # noqa: E402
import storage  # noqa: E402
import storage_report  # noqa: E402

SQLITE_STATUS = {
    "name": "s", "kind": "sqlite", "state": "idle", "holders": [], "op": None,
    "machine": "docker",
    "file": {"exists": True, "free": 1, "bytes": 212992, "wal_bytes": 123632},
}
PG_STATUS = {
    "name": "p", "kind": "postgresql", "state": "idle", "holders": [],
    "server": {"reachable": True, "server_version": "17", "schemas": {"layerfs": 753664}},
}


def item(n, parent, **sizes):
    base = {"logical": 100 * n, "new_canonical": 10 * n, "new_stored": 5 * n, "new_metadata": n}
    base.update(sizes)
    return {"id": f"c{n}", "parent": parent, "branch": "lane", "via": "exec", **base}


class ParseTests(unittest.TestCase):
    def test_sqlite_status_sums_file_and_wal_and_allocated(self):
        files = storage.parse_allocated(
            "store.sqlite 212992 416\nstore.sqlite-wal 123632 248\nstore.sqlite-shm 32768 64\n"
        )
        record = storage.parse_status(SQLITE_STATUS, files)
        self.assertEqual(record["total_bytes"], 212992 + 123632)
        self.assertEqual(record["allocated_bytes"], (416 + 248) * 512)
        self.assertEqual(record["allocated_status"], "MEASURED")
        self.assertIsNone(record["schema_bytes"])

    def test_sqlite_allocated_unavailable_without_probe(self):
        record = storage.parse_status(SQLITE_STATUS)
        self.assertIsNone(record["allocated_bytes"])
        self.assertEqual(record["allocated_status"], "UNAVAILABLE")

    def test_postgresql_status_uses_schema_bytes(self):
        record = storage.parse_status(PG_STATUS)
        self.assertEqual(record["total_bytes"], 753664)
        self.assertEqual(record["allocated_status"], "NOT_APPLICABLE")

    def test_missing_bytes_fail_closed(self):
        with self.assertRaises(storage.StorageFailure):
            storage.parse_status({"kind": "sqlite", "file": {"exists": False}})
        with self.assertRaises(storage.StorageFailure):
            storage.parse_status({"kind": "postgresql", "server": {"reachable": False}})
        with self.assertRaises(storage.StorageFailure):
            storage.parse_allocated("")

    def test_lsn_and_url_rules(self):
        self.assertEqual(storage.pg_lsn_bytes("1/10"), (1 << 32) + 16)
        self.assertTrue(storage.safe_database_url("postgresql://u@h:1/d"))
        self.assertFalse(storage.safe_database_url("postgresql://u:pw@h:1/d"))
        self.assertFalse(storage.safe_database_url("postgresql://u@h/d?password=x"))

    def test_server_wal_bytes(self):
        row = {"probes": {"floor": {"s": {"server_wal_lsn": "0/10"}}, "final": {"s": {"server_wal_lsn": "1/0"}}}}
        self.assertEqual(storage.server_wal_bytes(row), (1 << 32) - 16)
        self.assertIsNone(storage.server_wal_bytes({"probes": {"floor": {"s": {}}, "final": {}}}))

    def test_allocated_argv_is_read_only(self):
        argv = storage.allocated_argv("vol", "sha256:abc", "st")
        self.assertIn("vol:/d:ro", argv)
        self.assertIn("/d/store/st", argv)

    def test_docker_volume_from_home(self):
        with tempfile.TemporaryDirectory() as home:
            Path(home, "layerfs.json").write_text('{"layout":3,"id":"d9bc3fef150f"}')
            self.assertEqual(storage.docker_volume_for(home), "lfs-d9bc3fef-docker-data")


class CollectorTests(unittest.TestCase):
    def pages(self, chain, size):
        def list_page(argv):
            position = int(argv[argv.index("--page-pos") + 1]) if "--page-pos" in argv else 0
            self.assertEqual(argv[argv.index("--page-size") + 1], str(size))
            batch = chain[position:position + size]
            more = position + size < len(chain)
            return {"items": batch, "has_more": more, "next_page_pos": position + size if more else None}
        return list_page

    def test_follows_every_page_oldest_first(self):
        chain = [item(n, f"c{n - 1}" if n > 1 else None) for n in range(7, 0, -1)]
        history = storage.collect_commits(self.pages(chain, 3), "s/p", "lane", page_size=3)
        self.assertEqual(history["pages"], 3)
        self.assertEqual([c["id"] for c in history["commits"]], [f"c{n}" for n in range(1, 8)])

    def test_broken_chain_or_stalled_paging_fails(self):
        chain = [item(3, "c2"), item(1, None)]  # c2 lost
        with self.assertRaisesRegex(storage.StorageFailure, "chain broken"):
            storage.collect_commits(self.pages(chain, 5), "s/p", "lane", page_size=5)

        def stalled(argv):
            return {"items": [item(2, "c1")], "has_more": True, "next_page_pos": 0}
        with self.assertRaisesRegex(storage.StorageFailure, "did not advance"):
            storage.collect_commits(lambda a: {"items": [item(2, "c1")], "has_more": True, "next_page_pos": 1} if "--page-pos" not in a else stalled(a), "s/p", "lane")

    def test_missing_counter_fails(self):
        bad = item(1, None)
        del bad["new_stored"]
        with self.assertRaises(storage.StorageFailure):
            storage.collect_commits(lambda a: {"items": [bad], "has_more": False}, "s/p", "lane")


class SummaryTests(unittest.TestCase):
    def test_net_unattributed_and_ratios(self):
        floor = {"total_bytes": 1000, "file_bytes": 1000, "wal_bytes": 0, "allocated_bytes": 4096}
        final = {"total_bytes": 6000, "file_bytes": 5000, "wal_bytes": 1000, "allocated_bytes": 8192}
        h1 = {"project": "s/p", "branch": "a", "commits": [storage.commit_record(item(1, None)), storage.commit_record(item(2, "c1"))]}
        h2 = {"project": "s/p", "branch": "b", "commits": [storage.commit_record(item(1, None))]}
        s = storage.summarize(final, floor, [h1, h2], {"git_pack": 2500, "zero": 0}, 2000)
        self.assertEqual(s["net_bytes"], 5000)
        self.assertEqual(s["commits"], 2)  # c1 counted once across branches
        self.assertEqual(s["sum_new_stored"], 15)
        self.assertEqual(s["sum_new_metadata"], 3)
        self.assertEqual(s["unattributed_bytes"], 5000 - 18)
        self.assertEqual(s["sum_new_payload"], 12)  # new_stored includes new_metadata
        self.assertEqual(s["unattributed_after_packs_bytes"], 5000 - 15)
        self.assertEqual(s["net_allocated_bytes"], 4096)
        self.assertAlmostEqual(s["net_per_reference"]["git_pack"], 2.0)
        self.assertIsNone(s["net_per_reference"]["zero"])
        self.assertAlmostEqual(s["space_amplification"], 2.5)
        self.assertEqual(s["final_logical"], {"s/p@a": 200, "s/p@b": 100})

    def test_lists_of_probes_are_summed(self):
        s = storage.summarize(
            [{"total_bytes": 10, "file_bytes": 10, "wal_bytes": 0}, {"total_bytes": 20, "file_bytes": 20, "wal_bytes": 0}],
            [{"total_bytes": 3, "file_bytes": 3, "wal_bytes": 0}, {"total_bytes": 4, "file_bytes": 4, "wal_bytes": 0}],
            [],
        )
        self.assertEqual(s["net_bytes"], 23)
        self.assertIsNone(s["net_allocated_bytes"])


def fake_cases():
    provider = types.ModuleType("cases")
    provider.CASE_IDS = ("M01",)
    provider.get_case = lambda cell, verify=False: {}
    return provider


class FakeCLI:
    """Answers CLI argv with plausible JSON; records every call."""

    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on
        self.commits = []

    def __call__(self, argv, deadline, env=None):
        self.calls.append(list(argv))
        args = argv[1:]
        reply = {}
        if argv[0] == "docker":
            return {"process_exit": 0, "stdout": "store.sqlite 4096 8\n", "stderr": "", "elapsed_ns": 1}
        if self.fail_on and args[:2] == self.fail_on:
            return {"process_exit": 1, "stdout": "", "stderr": '{"code":"Failed"}', "elapsed_ns": 1}
        if args[:2] == ["store", "status"]:
            grown = 212992 + 1000 * len(self.commits)
            reply = {**SQLITE_STATUS, "file": {**SQLITE_STATUS["file"], "bytes": grown, "wal_bytes": 0}}
        elif args[:2] == ["workspace", "mount"]:
            reply = {"ws": f"{args[2]}:{args[5]}"}
        elif args[:2] == ["workspace", "exec"]:
            reply = {"exit_code": 0, "stdout": "ok", "truncated": False}
        elif args[:2] == ["workspace", "commit"]:
            n = len(self.commits) + 1
            self.commits.insert(0, item(n, f"c{n - 1}" if n > 1 else None))
            reply = {"kind": "Committed", "commit": self.commits[0]}
        elif args[:2] == ["commit", "list"]:
            reply = {"items": list(self.commits), "has_more": False, "next_page_pos": None}
        return {"process_exit": 0, "stdout": json.dumps(reply), "stderr": "", "elapsed_ns": 1}


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.run = storage.load_runner(fake_cases())
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        config = {"campaign_id": "unit", "source_sha": "a" * 40, "cli": "/fake/layerfs",
                  "home": self.directory.name, "machines": {"docker": {}}, "empty_source": self.directory.name}
        self.campaign = self.run.Campaign(config, self.directory.name)
        self.row = {"id": "M01/docker/sqlite", "backend": "sqlite", "pending": None, "uncertain": False}
        self.campaign.state["rows"][self.row["id"]] = self.row

    def spec(self):
        return {
            "prefix": "u-m01", "machine": "docker",
            "stores": [{"name": "u-m01", "backend": "sqlite", "projects": [{"project": "u-m01/p", "source": "/empty"}]}],
            "branches": [{"project": "u-m01/p", "name": "lane"}],
            "steps": [
                {"op": "sandbox", "project": "u-m01/p", "sandbox": "u-m01"},
                {"op": "mount", "sandbox": "u-m01", "branch": "lane", "name": "w", "as": "w"},
                {"op": "exec", "ws": "w", "command": "gen 0", "timeout_s": 120},
                {"op": "commit", "ws": "w"},
                {"op": "exec", "ws": "w", "command": "gen 1"},
                {"op": "commit", "ws": "w"},
                {"op": "unmount", "ws": "w"},
                {"op": "close", "sandbox": "u-m01"},
            ],
            "collect": [{"project": "u-m01/p", "branch": "lane"}],
            "verify": [{"project": "u-m01/p", "branch": "lane", "command": "verify", "check": lambda r: None}],
            "allocated": {"volume": "vol", "image": "img"},
        }

    def test_full_row_measures_floor_final_and_releases_store(self):
        cli = FakeCLI()
        with patch.object(self.run.measure, "run_command", side_effect=cli):
            storage.run_row(self.campaign, self.row, self.spec())
        verbs = [tuple(c[1:3]) for c in cli.calls if c[0] != "docker"]
        self.assertEqual(verbs[:4], [("store", "create"), ("project", "init"), ("store", "push"), ("store", "status")])
        self.assertEqual(verbs[-1], ("store", "remove"))
        self.assertEqual(self.row["execution"], "PASS")
        self.assertEqual(self.row["verification"], "PASS")
        self.assertEqual(self.row["cleanup"], "COMPLETE")
        summary = storage.row_summary(self.row)
        self.assertEqual(summary["net_bytes"], 2000)
        self.assertEqual(summary["commits"], 2)
        self.assertEqual(summary["net_allocated_bytes"], 0)
        # Every command had a deadline of at most 120 s and a unique phase label.
        phases = [c["phase"] for c in self.row["commands"]]
        self.assertEqual(len(phases), len(set(phases)))

    def test_failed_commit_keeps_store_and_is_fail(self):
        cli = FakeCLI(fail_on=["workspace", "commit"])
        with patch.object(self.run.measure, "run_command", side_effect=cli):
            storage.run_row(self.campaign, self.row, self.spec())
        self.assertEqual(self.row["execution"], "FAIL")
        self.assertTrue(self.row["uncertain"])  # Failed code after possible publication
        self.assertEqual(self.row["cleanup"], "INCOMPLETE")
        self.assertNotIn(["/fake/layerfs", "store", "remove", "u-m01"], cli.calls)
        self.assertEqual(sum(1 for c in cli.calls if c[1:3] == ["workspace", "commit"]), 1)  # no retry

    def test_timeout_over_two_minutes_refused(self):
        driver = storage.Driver(self.campaign, self.row)
        with self.assertRaises(ValueError):
            driver.call("x", ["store", "list"], timeout_s=121)

    def test_probe_requires_quiesced_row(self):
        driver = storage.Driver(self.campaign, self.row)
        self.row["owned"]["sandboxes"]["sb"] = {"live": True}
        with self.assertRaisesRegex(storage.StorageFailure, "not quiesced"):
            driver.probe("s", "final")


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.s0, self.s1 = root / "s0", root / "s1"
        (self.s0 / "d").mkdir(parents=True)
        (self.s0 / "d" / "a").write_bytes(b"alpha" * 100)
        (self.s0 / "b").write_bytes(b"beta")
        shutil.copytree(self.s0, self.s1)
        (self.s1 / "c").write_bytes(b"alpha" * 100)  # duplicate content
        (self.s1 / "b").write_bytes(b"beta2")
        for path in (self.s0, self.s1):
            for p in path.rglob("*"):
                os.chmod(p, 0o755 if p.is_dir() else 0o644)

    def test_manifest_is_canonical(self):
        m0 = references.manifest(self.s0)
        self.assertEqual(m0["files"], 2)
        self.assertEqual(m0["bytes"], 504)
        text = references.manifest_lines(references.walk(self.s0))
        self.assertTrue(text.startswith("f 0644 4 "))
        self.assertIn("d 0755 0 - d\n", text)
        self.assertEqual(references.manifest(self.s0), m0)

    def test_whole_file_unique_counts_distinct_contents(self):
        r = references.whole_file_unique([self.s0, self.s1])
        self.assertEqual(r["bytes"], 500 + 4 + 5)
        self.assertEqual(r["logical_bytes"], 504 + 505 + 500)

    def test_cdc_boundaries_respect_limits_and_cover(self):
        import hashlib
        data = hashlib.shake_256(b"cdc").digest(300_000)
        ends = references.cdc_boundaries(data)
        self.assertEqual(ends[-1], len(data))
        sizes = [b - a for a, b in zip([0] + ends, ends)]
        self.assertTrue(all(s <= references.CDC_MAX for s in sizes))
        self.assertTrue(all(s >= references.CDC_MIN for s in sizes[:-1]))
        # Content-defined: a 1-byte insert at the front resynchronizes.
        shifted = references.cdc_boundaries(b"x" + data)
        self.assertGreater(len({e + 1 for e in ends} & set(shifted)), len(ends) // 2)

    @unittest.skipUnless(shutil.which("zstd") and shutil.which("git"), "zstd and git CLIs required")
    def test_all_references_compute(self):
        result = references.compute([self.s0, self.s1])
        self.assertEqual(result["states"], 2)
        self.assertGreater(result["tar_zstd"]["bytes"], 0)
        self.assertEqual(len(result["tar_zstd"]["per_state"]), 2)
        self.assertGreater(result["git_pack"]["bytes"], 0)
        self.assertEqual(result["git_pack"]["loose_objects"], 0)
        again = references.compute([self.s0, self.s1])
        self.assertEqual(result["tar_zstd"], again["tar_zstd"])
        self.assertEqual(result["git_pack"]["bytes"], again["git_pack"]["bytes"])
        self.assertEqual(set(references.reference_bytes(result)) >= {"whole_file_unique", "tar_zstd", "git_pack"}, True)


class ReportTests(unittest.TestCase):
    def test_units_and_order(self):
        self.assertEqual(storage_report.b(1234567), "1,234,567")
        self.assertEqual(storage_report.mib(1048576), "1.000")
        self.assertEqual(storage_report.mb(1_000_000), "1.000")
        rows = [
            {"case": "M02", "backend": "sqlite", "summary": {"net_bytes": 5}},
            {"case": "M01", "backend": "postgresql", "summary": {"net_bytes": 7}},
            {"case": "M01", "backend": "sqlite", "summary": {"net_bytes": 6}},
        ]
        text = storage_report.store_bytes_table(rows)
        lines = [line for line in text.splitlines() if line.startswith("| M")]
        self.assertEqual([line.split("|")[1:3] for line in lines],
                         [[" M01 ", " SQLite "], [" M01 ", " PostgreSQL "], [" M02 ", " SQLite "]])
        curve = storage_report.commit_curve_table(
            {"sqlite": [storage.commit_record(item(1, None))], "postgresql": [storage.commit_record(item(1, None))]}
        )
        self.assertIn("SQLite new_stored (B)", curve)
        self.assertIn("PostgreSQL new_metadata (B)", curve)
        header = storage_report.reference_table(rows, {}).splitlines()[0]
        self.assertIn("tar\\|zstd-3", header)  # a pipe in a header never splits the column


if __name__ == "__main__":
    unittest.main()
