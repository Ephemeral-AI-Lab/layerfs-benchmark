"""The export family: pinned cases, fixtures and expected results.

A case exports one committed project (`main`) from a SQLite Store on one
machine to a fresh folder on the macOS host with the public
`layerfs project export <store>/<project> <destination> --progress`.
"""

FAMILY = "export"
WORKLOAD_VERSION = "export-v1"
MACHINES = ("native", "docker", "lima", "apple-container")

# fixture kind -> expected tree, from fixture.py at WORKLOAD_VERSION
FIXTURES = {
    "small": {
        "manifest": "8638d2973cfce62d1169e771f9649a35c5d2d78f5f553695c6342b8544e50c1e",
        "files": 10000,
        "directories": 132,
        "symlinks": 50,
        "bytes": 46486561,
    },
    "large": {
        "manifest": "a4735ecdaf8a95a18953f474c5ee616b47eca599769843ac56ccd148b8b5e205",
        "files": 2,
        "directories": 0,
        "symlinks": 0,
        "bytes": 268435480,
    },
}

CASES = {
    "E01": {"fixture": "small", "work": "export 10,000 small files (46.5 MB) with 50 symlinks and 132 folders"},
    "E02": {"fixture": "large", "work": "export one 256 MiB file and a README"},
}

# complete command (cold control + timed export + verification + cleanup)
BUDGET_S = 15.0
# declared exceptions, each up to 25 s (none yet)
DECLARED_EXCEPTIONS: dict = {}
VERIFY_BUDGET_S = 10.0
