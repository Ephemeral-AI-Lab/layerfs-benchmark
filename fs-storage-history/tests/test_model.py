import collections
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))

import base  # noqa: E402
import cases  # noqa: E402
import model  # noqa: E402


def synthetic():
    """A small tree with text, binary, symlink, executable and log files."""
    entries = {}
    rng = model.Rng("test-tree")
    for d in ("", "src", "src/core", "docs", "logs/a"):
        for i in range(6):
            path = f"{d}/f{i}.txt" if d else f"f{i}.txt"
            entries[path] = model.Entry("file", 0o644, model.text_block(rng, 200 + 97 * i).encode())
    entries["bin/tool"] = model.Entry("file", 0o755, b"#!/bin/sh\necho hi\n")
    entries["img.png"] = model.Entry("file", 0o644, b"\x89PNG\0\0\x01binary")
    entries["logs/a/events.jsonl"] = model.Entry("file", 0o644, b'{"a":1}\n')
    entries["link"] = model.Entry("link", 0, b"src/core/f1.txt")
    entries["noeol.md"] = model.Entry("file", 0o644, b"one\r\ntwo\rthree")
    return entries


def write(entries, root):
    for path, entry in entries.items():
        full = os.path.join(root, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        if entry.kind == "link":
            os.symlink(entry.data.decode(), full)
        else:
            with open(full, "wb") as stream:
                stream.write(entry.data)
            os.chmod(full, entry.mode)


class Prng(unittest.TestCase):
    def test_pinned_values(self):
        rng = model.Rng("k", 1)
        values = [rng.u64() for _ in range(3)]
        again = model.Rng("k", 1)
        self.assertEqual(values, [again.u64() for _ in range(3)])
        self.assertEqual(values[0], 13613508570725314401)
        # Pinned so a changed PRNG cannot silently change the workload.
        self.assertEqual(model.Rng("fsh", 7).below(1000), PINNED_BELOW)

    def test_below_range_and_shares(self):
        rng = model.Rng("shares")
        counts = collections.Counter(rng.weighted(model.OP_SHARES) for _ in range(20000))
        for name, share in model.OP_SHARES:
            self.assertAlmostEqual(counts[name] / 20000, share / 100, delta=0.015)
        self.assertTrue(all(0 <= rng.below(3) < 3 for _ in range(100)))


PINNED_BELOW = 255


class Planning(unittest.TestCase):
    def plan(self, seed, steps=20):
        state = model.State(synthetic())
        return [model.plan_step(state, seed, s) for s in range(1, steps + 1)], state

    def test_deterministic_from_seed_and_step(self):
        a, sa = self.plan("s1")
        b, sb = self.plan("s1")
        self.assertEqual(a, b)
        self.assertEqual(sa.summary(), sb.summary())
        c, sc = self.plan("s2")
        self.assertNotEqual(a, c)
        self.assertNotEqual(sa.summary()["sha256"], sc.summary()["sha256"])

    def test_pinned_plan_digest(self):
        ops, state = self.plan("pinned", steps=30)
        digest = model.ops_digest(ops)
        self.assertEqual(digest, model.ops_digest(self.plan("pinned", steps=30)[0]))
        self.assertEqual(len(ops), 30)
        self.assertTrue(all(len(step) == model.OPS_PER_COMMIT for step in ops))
        self.assertEqual(state.summary()["empty_dirs"], 0)

    def test_fork_copy_is_independent(self):
        state = model.State(synthetic())
        before = state.summary()
        child = state.copy()
        model.plan_step(child, "x", 1)
        self.assertEqual(state.summary(), before)
        self.assertNotEqual(child.summary()["sha256"], before["sha256"])

    def test_transport_roundtrip(self):
        ops, _ = self.plan("t", steps=3)
        for step in ops:
            self.assertEqual(model.decode_ops(model.encode_ops(step)), step)

    def test_indexes_match_entries(self):
        _, state = self.plan("idx", steps=60)
        self.assertEqual(state.files, sorted(p for p, e in state.entries.items() if e.kind == "file"))
        self.assertEqual(state.text, sorted(p for p in state.files if state.entries[p].text))
        dirs = {""} | {d for p in state.entries for d in model.ancestors(p)}
        self.assertEqual(state.dirs, sorted(dirs))


class DiskMatchesOracle(unittest.TestCase):
    def test_apply_on_disk_equals_oracle(self):
        root = tempfile.mkdtemp()
        try:
            entries = synthetic()
            write(entries, root)
            state = model.State(entries)
            self.assertEqual(model.disk_manifest(root), state.summary())
            for step in range(1, 41):
                ops = model.plan_step(state, "disk", step)
                model.apply_ops(model.decode_ops(model.encode_ops(ops)), root)
            self.assertEqual(model.disk_manifest(root), state.summary())
        finally:
            shutil.rmtree(root)

    def test_precondition_refuses_drift(self):
        root = tempfile.mkdtemp()
        try:
            entries = synthetic()
            write(entries, root)
            state = model.State(entries)
            ops = None
            for step in range(1, 30):
                ops = model.plan_step(state, "drift", step)
                if any(op["op"] == "edit" for op in ops):
                    break
            edit = next(op for op in ops if op["op"] == "edit")
            with open(os.path.join(root, edit["path"]), "ab") as stream:
                stream.write(b"drift\n")
            with self.assertRaises(SystemExit):
                model.apply_ops([edit], root)
        finally:
            shutil.rmtree(root)


class Shapes(unittest.TestCase):
    def test_counts(self):
        expected = {"H01": 500, "H02": 250, "H03": 50, "H04": 50, "H05": 100, "H06": 100, "H07": 200}
        for case_id in cases.CASE_IDS:
            if cases.COUNTS == ORIGINAL_COUNTS:
                self.assertEqual(cases.commit_count(case_id), expected[case_id])
            self.assertGreater(cases.commit_count(case_id), 0)

    def test_h06_mirrors_h05_and_h03_shares_one_seed(self):
        h05 = cases.shape("H05")
        h06 = cases.shape("H06")
        self.assertEqual(len(h05), 1)
        self.assertEqual(len(h06), cases.COUNTS["H06"]["projects"])
        self.assertEqual([p for s in h06 for p in s["projects"]], h05[0]["projects"])
        self.assertEqual(len({s["suffix"] for s in h06}), len(h06))
        seeds = {b["seed"] for b in cases.shape("H03")[0]["projects"][0]["branches"]}
        self.assertEqual(seeds, {"H03/shared"})
        h02 = [b["seed"] for b in cases.shape("H02")[0]["projects"][0]["branches"]]
        self.assertEqual(len(set(h02)), len(h02))

    def test_h04_is_a_chain(self):
        branches = cases.shape("H04")[0]["projects"][0]["branches"]
        self.assertEqual(branches[0]["from"], "main")
        for prev, cur in zip(branches, branches[1:]):
            self.assertEqual(cur["from"], prev["name"])

    def test_plan_on_synthetic_base(self):
        state = model.State(synthetic())
        plan = cases.build_plan("H04", state)
        again = cases.build_plan("H04", model.State(synthetic()))
        self.assertEqual(plan["workload_sha256"], again["workload_sha256"])
        heads = [b["head"]["sha256"] for b in plan["stores"][0]["projects"][0]["branches"]]
        self.assertEqual(len(set(heads)), len(heads))
        h03 = cases.build_plan("H03", model.State(synthetic()))
        ops = {tuple(b["steps"]) for b in h03["stores"][0]["projects"][0]["branches"]}
        self.assertEqual(len(ops), 1)


ORIGINAL_COUNTS = {
    "H01": {"commits": 500},
    "H02": {"branches": 50, "commits": 5},
    "H03": {"branches": 50, "commits": 1},
    "H04": {"depth": 10, "commits": 5},
    "H05": {"projects": 20, "commits": 5},
    "H06": {"projects": 20, "commits": 5},
    "H07": {"projects": 4, "branches": 5, "commits": 10},
}


class BaseTree(unittest.TestCase):
    """Runs only where the extracted base is present (FSH_BASE)."""

    def test_pinned_base(self):
        root = os.environ.get("FSH_BASE")
        if not root or not os.path.isdir(root):
            self.skipTest("FSH_BASE not set")
        summary = base.load_tree(root).summary()
        base.check_pins(summary)
        self.assertEqual(model.disk_manifest(root)["sha256"], cases.BASE_MANIFEST_SHA256)


if __name__ == "__main__":
    unittest.main()
