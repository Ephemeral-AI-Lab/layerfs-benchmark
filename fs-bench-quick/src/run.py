#!/usr/bin/env python3
"""Use the shared CLI-only lifecycle with this suite's cases."""

import sys
from pathlib import Path

_shared = Path(__file__).resolve().parents[2] / "shared" / "src"
sys.path.insert(0, str(_shared))
exec(
    compile((_shared / "runner.py").read_bytes(), str(_shared / "runner.py"), "exec"),
    globals(),
)
