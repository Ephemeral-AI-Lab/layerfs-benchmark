import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location("juicefs_pg", SOURCE / "juicefs_pg.py")
pg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pg)


class Custody(unittest.TestCase):
    def test_consumed_workload_is_not_replayed(self):
        with tempfile.TemporaryDirectory() as root:
            b = pg.Baseline(Path(root))
            b.state.update(preparation="READY", execution="FAIL")
            with patch.object(b, "command") as run, self.assertRaises(RuntimeError):
                b.run()
            run.assert_not_called()

    def test_foreign_resource_is_never_released(self):
        with tempfile.TemporaryDirectory() as root:
            b = pg.Baseline(Path(root))
            b.state["resources"] = [{"name": "owned-selection", "id": "exact-id", "kind": "volume", "state": "LIVE"}]
            with patch.object(b, "command", return_value={"stdout": '[{"Labels":{"benchmark.owner":"someone-else"}}]'}) as run:
                with self.assertRaises(RuntimeError):
                    b.finish()
            self.assertEqual(run.call_count, 1)
            self.assertEqual(b.state["cleanup"], "INCOMPLETE")
            self.assertEqual(b.state["resources"][0]["state"], "LIVE")
