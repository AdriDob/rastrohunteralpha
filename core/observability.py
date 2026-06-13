import logging
import time
from collections import defaultdict
from contextlib import contextmanager
from threading import Lock
from typing import Any, Dict, List

LOG = logging.getLogger("rastro.observability")

_metrics: Dict[str, List[float]] = defaultdict(list)
_metrics_lock = Lock()


@contextmanager
def timer(name: str):
    """Context manager that records execution duration for `name`."""
    t0 = time.monotonic()
    try:
        yield
    finally:
        elapsed = time.monotonic() - t0
        with _metrics_lock:
            _metrics[name].append(elapsed)


def record(name: str, value: float) -> None:
    with _metrics_lock:
        _metrics[name].append(value)


def get_metrics() -> Dict[str, Any]:
    """Return aggregated timing metrics."""
    result: Dict[str, Any] = {}
    with _metrics_lock:
        for name, vals in dict(_metrics).items():
            if not vals:
                continue
            result[name] = {
                "count": len(vals),
                "total_ms": round(sum(vals) * 1000, 1),
                "avg_ms": round((sum(vals) / len(vals)) * 1000, 1),
                "min_ms": round(min(vals) * 1000, 1),
                "max_ms": round(max(vals) * 1000, 1),
            }
    return result


def reset_metrics() -> None:
    with _metrics_lock:
        _metrics.clear()
