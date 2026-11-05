"""Compatibility import for the shared bounded measurement implementation."""

from pathlib import Path

_shared = Path(__file__).resolve().parents[2] / "shared" / "src" / "measure.py"
exec(compile(_shared.read_bytes(), str(_shared), "exec"), globals())
