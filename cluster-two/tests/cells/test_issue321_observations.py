"""Issue 321 receipts: every overlay file is counted, and retired owner bytes are never relabelled."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "benchmark/cluster-one/init"))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "benchmark/cluster-one/history"))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "benchmark/cluster-two"))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "benchmark/cluster-two/registry"))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "benchmark/cluster-two/retired"))
import tempfile
import types
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cells import receipts, registry, runner
import test_counts

STORE, OVERLAY = "/layerfs-store/global/store.sqlite", "/layerfs-local/overlay/"


def listed(base, size=None, blocks=0):
    lines = [f"{base} {size} {blocks} 512" if size is not None else f"{base} ABSENT"]
    return lines + [f"{base}{suffix} ABSENT" for suffix in ("-wal", "-shm", "-journal")]


class OverlayFiles(unittest.TestCase):
    def observed(self, lines):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "snapshot.stdout"
            path.write_text("DAEMON_STATUS\nVmHWM:\t    100 kB\nBACKING_BYTES\n" + "\n".join(lines) + "\nOWN_CONTAINER_CGROUP\n")
            runtime = types.SimpleNamespace(rows=[{"event": "external_snapshot", "fields": {"stdout": str(path)}}])
            observations = {}
            runner.snapshot_observations(runtime, observations)
            return observations

    def test_the_template_and_every_workspace_file_are_summed(self):
        result = self.observed(listed(STORE, 8192, 16) + listed(OVERLAY + "1.sqlite", 40960, 80)
                               + listed(OVERLAY + "2.sqlite", 4096, 8) + listed(OVERLAY + "overlay.sqlite", 122880, 240))
        self.assertEqual(result["overlay_logical_bytes"]["value"], 40960 + 4096 + 122880)
        self.assertEqual(result["overlay_allocated_bytes"]["value"], (80 + 8 + 240) * 512)
        self.assertIn("overlay sums 3 listed file(s)", result["overlay_logical_bytes"]["provenance"])
        self.assertEqual(result["store_logical_bytes"]["value"], 8192)
        self.assertEqual(result["daemon_vmhwm_bytes"]["value"], 102400)

    def test_a_snapshot_of_an_earlier_runtime_lists_the_template_alone(self):
        result = self.observed(listed(STORE, 8192, 16) + listed(OVERLAY + "overlay.sqlite", 122880, 240))
        self.assertEqual(result["overlay_logical_bytes"]["value"], 122880)
        self.assertIn("overlay sums 1 listed file(s)", result["overlay_logical_bytes"]["provenance"])

    def test_workspace_files_without_the_template_are_not_an_overlay_total(self):
        result = self.observed(listed(STORE, 8192, 16) + listed(OVERLAY + "1.sqlite", 40960, 80))
        self.assertNotIn("overlay_logical_bytes", result)
        self.assertIn("store_logical_bytes", result)

    def test_a_file_with_an_unlisted_sidecar_is_not_summed(self):
        result = self.observed(listed(STORE, 8192, 16) + listed(OVERLAY + "overlay.sqlite", 122880, 240)
                               + [f"{OVERLAY}1.sqlite 4096 8 512"])
        self.assertNotIn("overlay_logical_bytes", result)


class RetiredOwnerBytes(unittest.TestCase):
    def ingest(self, rows):
        observations = {name: receipts.unavailable("missing") for name in registry.COUNTERS}
        runner.ingest_observations({rows[0]["call"]: rows}, observations, {})
        return observations

    def test_a_direct_workspace_reports_exact_retirement_and_never_another_counter(self):
        rows = test_counts.DirectWorkspaceCounters.direct(7, jobs=3, read=1, mutation=2)
        owner = next(row for row in rows if row["section"] == 1)
        owner["values"][2], owner["values"][4] = 77, 99
        result = self.ingest(rows)
        expected = receipts.unavailable(receipts.RETIRED_OWNER_BYTES, not_applicable=True)
        self.assertEqual(result["scheduler_bytes"], expected)
        self.assertEqual(result["peak_credited_bytes"], expected)

    def test_a_queued_owner_keeps_its_original_observations(self):
        result = self.ingest(test_counts.snapshot(7, admitted=1))
        self.assertEqual((result["scheduler_bytes"]["value"], result["peak_credited_bytes"]["value"]), (8192, 128))


if __name__ == "__main__":
    unittest.main()
