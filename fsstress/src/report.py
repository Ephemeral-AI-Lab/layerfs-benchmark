#!/usr/bin/env python3
"""Render a suite report through the shared reporting command."""

import sys
from pathlib import Path

_shared = Path(__file__).resolve().parents[2] / "shared" / "src"
sys.path.insert(0, str(_shared))
sys.argv[1:1] = ["--suite", Path(__file__).resolve().parents[1].name]
exec(  # noqa: S102 - load the tracked shared implementation with suite globals
    compile((_shared / "report.py").read_bytes(), str(_shared / "report.py"), "exec"),
    globals(),
)
