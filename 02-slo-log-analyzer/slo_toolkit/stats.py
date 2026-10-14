"""Latency and error statistics."""
from __future__ import annotations

import math
from collections import defaultdict

from .parse import is_good


def percentile(values: list[float], p: float) -> float | None:
    """Nearest-rank percentile (the same definition most monitoring tools use for p50/p95/p99)."""
    if not values:
        return None
    s = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(s)))
    return s[rank - 1]


def summarize_by_event(records: list[dict]) -> dict[str, dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        groups[r["event"]].append(r)
    out = {}
    for event, recs in sorted(groups.items()):
        lat = [float(r["ms"]) for r in recs if isinstance(r.get("ms"), (int, float))]
        bad = sum(1 for r in recs if not is_good(r))
        out[event] = {
            "count": len(recs),
            "errors": bad,
            "error_rate": bad / len(recs),
            "p50_ms": percentile(lat, 50),
            "p95_ms": percentile(lat, 95),
            "p99_ms": percentile(lat, 99),
        }
    return out
