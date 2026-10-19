"""Independent growth/retention receipt validation; no invented RSS limit."""
from .evidence_engine import rows
from .evidence_jobs import integer, require, SHA


def validate(path, case):
    stream = iter(rows(path))
    start = next(stream)
    require(start.get("schema") == "pre-s8-growth-start-v1" and
            (start["mode"], start["files"], start["amount"]) == (case["mode"], case["files"], case["amount"]),
            "original selected workload")
    require(start["profile"] == "sqlite-wal-off-v2", "Disposable selection")
    points, operations, heads = [], [], set()

    def point(stage, index):
        value = next(stream)
        require(value.get("schema") in ("pre-s8-growth-point-v1", "pre-s8-growth-point-v2", "pre-s8-growth-point-v3") and
                value["stage"] == stage and value["index"] == index, "original point order")
        require(all(integer(v) for k, v in value.items() if k not in {"schema", "stage"}), "point counter type")
        require((value["read_handles"] == (1 if stage == "drained" else 2) if value["schema"] == "pre-s8-growth-point-v3" else value["read_handles"] == 4) and value["cache_bytes"] <= 8388608, "declared reader/cache inventory")
        retired = ("credited_bytes", "outstanding", "queued", "receipt_overruns")
        if value["schema"] == "pre-s8-growth-point-v1":
            # Historical receipts of the queued owner: its gauges must read released.
            require(all(value[name] == 0 for name in retired), "released operation retains credits/jobs")
        else:
            # A Workspace runs each job on its caller: there is no queue or credit to report.
            require(not any(name in value for name in retired), "retired scheduling gauge in a v2 point")
        require(value["closed_namespaces"] == (1 if stage == "drained" else 0), "terminal namespace ownership")
        points.append(value)

    point("bound", 0)
    count = 1 if case["mode"] == "save" else case["amount"]
    for i in range(count):
        value = next(stream)
        require(value.get("schema") == "pre-s8-growth-operation-v1" and value["index"] == i and
                value["attempts"] == 1 and type(value["attempts"]) is int, "original operation identity")
        require(SHA.fullmatch(value["root"]), "root identity")
        require(value["reserve"] == value["initial"] + value["refills"] and value["initial"] == 1 and
                value["writes"] == value["reserve"] + value["publish"] + value["history"], "write arithmetic")
        if case["mode"] == "save":
            require(value["kind"] == "save" and value["bytes"] == case["amount"] and value["history"] == 0,
                    "standalone Save scope")
            require(value["pending_observed_max"] <= 4194303 and value["objects"] > 0, "bounded Save window")
            oracle = next(stream)
            require(oracle == {"schema": "pre-s8-growth-oracle-v1", "bytes": case["amount"],
                               "window": 131072, "full_match": True}, "full streaming byte oracle")
        else:
            require(value["kind"] == "commit" and value["history"] == 1 and value["engine_jobs"] == 2,
                    "complete Store-half Commit")
            require(value["head"].startswith("12") and SHA.fullmatch(value["head"][2:]), "Commit identity")
            require(value["head"] not in heads, "duplicate original publication")
            heads.add(value["head"])
        operations.append(value)
        point("released", i + 1)
    point("drained", case["amount"])
    terminal = next(stream)
    require(terminal.get("schema") == "pre-s8-growth-terminal-v1" and
            terminal["owner_stopped"] is True and terminal["store_released"] is True, "original owner release")
    require(next(stream, None) is None, "trailing or replayed outcome")
    return {"schema": "pre-s8-growth-validation-v1", "functional_counts": "PASS",
            "operations": operations, "points": points, "terminal": terminal,
            "numeric_acceptance": "OWNER_DEFERRED", "memory_growth_verdict": "REQUIRES_CROSS_CASE_AND_SOURCE_ANALYSIS",
            "scope": "Rust requested live bytes are distinct from native malloc, allocator slack, RSS and file cache"}
