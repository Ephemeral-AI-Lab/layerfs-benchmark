"""The README indexes built from published reports."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared/src"))
import readme_index


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class Index(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        write(self.root / "README.md", "# repo\n\n<!-- index:begin -->\n<!-- index:end -->\n")
        write(self.root / "aa/README.md", "# aa — reads files\n> group: filesystem · measures: speed, storage\n\n## Past runs\n\n<!-- runs:begin -->\n<!-- runs:end -->\n")
        write(self.root / "bb/README.md", "# bb — moves Stores\n> group: transfer · measures: recovery\n\n<!-- runs:begin -->\n<!-- runs:end -->\n")
        sha_old, sha_new = "1" * 40, "2" * 40
        write(self.root / f"result/2026-01-01/aa/{sha_old}/report.md", "# aa\n\n**Diagnostic terminal: PASS.** rest\n")
        write(self.root / f"result/2026-02-01/aa/{sha_old}/report.md", "# aa\n\n**Superseded by the [newer](../x/report.md).** old\n")
        write(self.root / f"result/2026-02-01/aa/{sha_new}/report.md", "# aa\n\n**Outcome: PASS\non both.** rest\n")

    def test_tables_are_written_and_then_current(self):
        self.assertEqual(readme_index.main(["--root", str(self.root)]), 0)
        index = (self.root / "README.md").read_text()
        self.assertIn("## Filesystem", index)
        self.assertIn("## Transfer", index)
        self.assertIn("| [aa](aa/) | speed, storage | reads files | 2026-02-01 · `22222222` · Outcome: PASS on both ·", index)
        self.assertIn("| [bb](bb/) | recovery | moves Stores | none yet |", index)
        runs = (self.root / "aa/README.md").read_text()
        rows = [line for line in runs.splitlines() if line.startswith("| 2026")]
        self.assertEqual([r.split(" | ")[0] for r in rows], ["| 2026-02-01", "| 2026-02-01", "| 2026-01-01"])
        self.assertIn("Superseded by the newer", rows[1])
        self.assertIn("No published runs yet.", (self.root / "bb/README.md").read_text())
        self.assertEqual(readme_index.main(["--root", str(self.root), "--check"]), 0)

    def test_check_reports_a_stale_block(self):
        self.assertEqual(readme_index.main(["--root", str(self.root), "--check"]), 1)

    def test_an_unknown_measure_is_refused(self):
        write(self.root / "bb/README.md", "# bb — moves\n> group: transfer · measures: vibes\n<!-- runs:begin -->\n<!-- runs:end -->\n")
        self.assertEqual(readme_index.main(["--root", str(self.root)]), 2)

    def test_a_report_without_a_readme_header_is_refused(self):
        write(self.root / f"result/2026-01-01/cc/{'3' * 40}/report.md", "**PASS.**\n")
        self.assertEqual(readme_index.main(["--root", str(self.root)]), 2)


if __name__ == "__main__":
    unittest.main()
