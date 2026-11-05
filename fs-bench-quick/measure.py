"""Bounded local command observations; unavailable cache proof stays ineligible.

Only the public LayerFS CLI caller owns remote effects. Killing its local process
never proves that the worker, daemon or workload has stopped.
"""

from __future__ import annotations

import dataclasses
import math
import os
import selectors
import signal
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path


class BudgetExceeded(TimeoutError):
    """The shared phase/case deadline has expired; no new call may start."""


@dataclasses.dataclass(frozen=True)
class Deadline:
    end_ns: int

    @classmethod
    def after(cls, seconds: float) -> Deadline:
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("deadline must be finite and positive")
        return cls(time.monotonic_ns() + int(seconds * 1_000_000_000))

    def remaining(self) -> float:
        remaining_ns = self.end_ns - time.monotonic_ns()
        if remaining_ns <= 0:
            raise BudgetExceeded("shared wall budget exhausted")
        return remaining_ns / 1_000_000_000


def run_command(
    argv: Sequence[str],
    deadline: Deadline,
    *,
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
    output_limit: int = 65536,
) -> dict:
    """Run once, retaining bounded output and per-child CPU/RSS observations.

    The caller supplies the SAME deadline throughout its phase/case. Output is
    drained after the retention limit so a noisy child cannot deadlock or consume
    unbounded memory. Local process-group termination has a separate 250ms reap
    ceiling, reported in elapsed wall; it does not extend the operation budget.
    No process-wide RUSAGE_CHILDREN delta or lifetime server peak is used.
    """
    if not argv or isinstance(argv, (str, bytes)):
        raise ValueError("argv must be a nonempty argument array")
    if output_limit < 1:
        raise ValueError("output_limit must be positive")
    deadline.remaining()
    started = time.monotonic_ns()
    result = {
        "process_exit": None,
        "elapsed_ns": None,
        "stdout": "",
        "stderr": "",
        "stdout_bytes": 0,
        "stderr_bytes": 0,
        "output_truncated": False,
        "timed_out": False,
        "uncertainty": False,
        "error": None,
        "child_cpu_ns": None,
        "child_maxrss_bytes": None,
        "resource_scope": "local CLI process lifetime, including reaped descendants; excludes remote workers/daemon/database",
        "remote_resources": {
            "status": "UNAVAILABLE",
            "reason": "no phase-scoped remote observer registered",
        },
    }
    try:
        child = subprocess.Popen(
            list(argv),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=dict(env) if env is not None else None,
            start_new_session=True,
        )
    except OSError as error:
        result.update(error=str(error), elapsed_ns=time.monotonic_ns() - started)
        return result

    retained = {"stdout": bytearray(), "stderr": bytearray()}
    selector = selectors.DefaultSelector()
    for name in retained:
        stream = getattr(child, name)
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, name)
    usage = None

    def reap() -> bool:
        nonlocal usage
        if child.returncode is not None:
            return True
        if hasattr(os, "wait4"):
            pid, status, observed = os.wait4(child.pid, os.WNOHANG)
            if pid:
                child.returncode = os.waitstatus_to_exitcode(status)
                usage = observed
        else:
            child.poll()
        return child.returncode is not None

    try:
        while True:
            exited = reap()
            if exited and not selector.get_map():
                break
            remaining_ns = deadline.end_ns - time.monotonic_ns()
            if remaining_ns <= 0:
                result.update(
                    timed_out=True,
                    uncertainty=True,
                    error="shared wall budget exhausted",
                )
                # One cancellation attempt; never replay the remote operation.
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except OSError as error:
                    result["error"] += f"; local cancellation failed: {error}"
                reap_end = time.monotonic_ns() + 250_000_000
                while not reap() and time.monotonic_ns() < reap_end:
                    time.sleep(0.002)
                break
            for key, _ in selector.select(min(remaining_ns / 1_000_000_000, 0.025)):
                data = os.read(key.fileobj.fileno(), 65536)
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                name = key.data
                result[f"{name}_bytes"] += len(data)
                available = max(0, output_limit - len(retained[name]))
                retained[name].extend(data[:available])
                if len(data) > available:
                    result["output_truncated"] = True
    except BaseException:
        # Parent records the already-written intent as uncertain. Do not leave a
        # local caller alive after a handled interruption, or replay its call.
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        reap_end = time.monotonic_ns() + 250_000_000
        while not reap() and time.monotonic_ns() < reap_end:
            time.sleep(0.002)
        raise
    finally:
        selector.close()
        child.stdout.close()
        child.stderr.close()
    result["elapsed_ns"] = time.monotonic_ns() - started
    result["process_exit"] = child.returncode
    for name, data in retained.items():
        result[name] = data.decode("utf-8", errors="replace")
    if usage is not None:
        result["child_cpu_ns"] = round((usage.ru_utime + usage.ru_stime) * 1_000_000_000)
        result["child_maxrss_bytes"] = int(usage.ru_maxrss) * (1 if sys.platform == "darwin" else 1024)
    return result


def assess_cache(evidence: Mapping | None, phase: str, machine: str, backend: str) -> dict:
    """Fail closed until an implemented, demonstrated cold protocol exists.

    A JSON configuration may describe proposed controls but cannot certify its
    own coldness. The pinned product has no public cache eviction/residency API.
    New mount/process, independent Stores, copy and restart assertions therefore
    never make a numeric claim eligible. Add a source-backed enforcement and
    residency validator here before admitting any new protocol.
    """
    if machine not in {"native", "docker", "lima", "apple-container"}:
        raise ValueError(f"unknown machine: {machine}")
    if backend not in {"sqlite", "postgresql"}:
        raise ValueError(f"unknown database: {backend}")
    domains = ["layerfs-daemon-worker", "filesystem-metadata", "host-page-cache"]
    if machine != "native":
        domains.append("guest-page-cache")
    if backend == "postgresql":
        domains.extend(["postgresql-shared-buffers", "postgresql-server-page-cache"])
    return {
        "status": "INELIGIBLE",
        "phase": phase,
        "machine": machine,
        "backend": backend,
        "required_domains": domains,
        "reasons": [
            "No implemented, demonstrated owned cold-cache enforcement and residency protocol for this route/phase.",
            "Fresh CLI process/mount, distinct database and copied fixture do not prove coldness.",
        ],
        "configured_evidence": dict(evidence or {}),
    }
