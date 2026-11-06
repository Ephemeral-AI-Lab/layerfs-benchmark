"""Docker subset gate (layerfs-project#98): plan order and the paired-delta rule."""

import importlib.util
import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
spec = importlib.util.spec_from_file_location("quick_gate", SRC / "gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class Plan(unittest.TestCase):
    def test_ninety_six_rows_alternating_pairs(self):
        rows = gate.plan()
        self.assertEqual(len(rows), 96)
        first = rows[:4]
        self.assertEqual([(r["round"], r["ident"]) for r in first], [(1, "a"), (1, "b"), (2, "b"), (2, "a")])
        self.assertEqual({r["arm"] for r in first}, {"sqlite"})
        # C04 has an odd CASE_IDS index: the runner reverses its arm order.
        c04 = [r["arm"] for r in rows if r["cell"] == "C04"][::4]
        self.assertEqual(c04, ["pg-colocated", "postgresql", "sqlite"])

    def test_each_campaign_follows_matrix_order(self):
        for ident in "ab":
            for rnd in (1, 2):
                seq = [(r["cell"], r["arm"]) for r in gate.plan() if r["ident"] == ident and r["round"] == rnd]
                expected = [(c, a) for c in gate.CELLS for a in gate.arm_order(c)]
                self.assertEqual(seq, expected)


class Rule(unittest.TestCase):
    def test_flag_needs_both_pairs_slower_and_threshold(self):
        self.assertEqual(gate.flag([100, 100], [130, 120])[2], "FLAG")
        self.assertEqual(gate.flag([100, 100], [130, 99])[2], "ok")  # 1/2 slower
        self.assertEqual(gate.flag([100, 100], [110, 112])[2], "ok")  # under 15%

    def test_five_ms_floor(self):
        self.assertEqual(gate.flag([10, 10], [14, 14])[2], "ok")  # +4 ms, 40%
        self.assertEqual(gate.flag([10, 10], [16, 16])[2], "FLAG")

    def test_missing_pair_is_incomplete(self):
        self.assertEqual(gate.flag([10, None], [16, 16])[2], "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
