from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

import numpy as np


@contextmanager
def track_stage(state: dict[str, Any], stage: str) -> Iterator[None]:
    started_at = datetime.now(UTC)
    started = perf_counter()
    status = "ok"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        ended_at = datetime.now(UTC)
        state.setdefault("timings", []).append(
            {
                "stage": stage,
                "started_at": started_at,
                "ended_at": ended_at,
                "duration_ms": round((perf_counter() - started) * 1000, 3),
                "status": status,
            }
        )


def percentile_report(records: list[list[dict[str, Any]]]) -> dict[str, dict[str, float]]:
    stages: dict[str, list[float]] = defaultdict(list)
    for record in records:
        for timing in record:
            stages[timing["stage"]].append(float(timing["duration_ms"]))
        stages["total"].append(sum(float(item["duration_ms"]) for item in record))
    return {
        stage: {
            "p50_ms": round(float(np.percentile(values, 50)), 3),
            "p70_ms": round(float(np.percentile(values, 70)), 3),
            "p100_ms": round(float(np.percentile(values, 100)), 3),
        }
        for stage, values in stages.items()
        if values
    }
