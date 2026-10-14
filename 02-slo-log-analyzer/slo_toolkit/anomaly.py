"""Anomaly detection on per-minute time series (rolling z-score)."""
from __future__ import annotations

import statistics
from collections import Counter
from datetime import datetime, timedelta

from .parse import is_good


def per_minute(records: list[dict], metric: str = "errors") -> list[tuple[datetime, float]]:
    """Bucket records into one-minute buckets. metric: 'errors', 'requests' or 'p95_ms'."""
    if not records:
        return []
    start = records[0]["_ts"].replace(second=0, microsecond=0)
    end = records[-1]["_ts"].replace(second=0, microsecond=0)
    buckets: dict[datetime, list[dict]] = {}
    t = start
    while t <= end:  # include empty minutes: a silent minute is data too
        buckets[t] = []
        t += timedelta(minutes=1)
    for r in records:
        buckets[r["_ts"].replace(second=0, microsecond=0)].append(r)

    series = []
    for minute, recs in buckets.items():
        if metric == "errors":
            v = float(sum(1 for r in recs if not is_good(r)))
        elif metric == "requests":
            v = float(len(recs))
        elif metric == "p95_ms":
            lat = sorted(float(r["ms"]) for r in recs if isinstance(r.get("ms"), (int, float)))
            v = lat[max(0, int(0.95 * len(lat)) - 1)] if lat else 0.0
        else:
            raise ValueError(f"unknown metric {metric}")
        series.append((minute, v))
    return series


def rolling_zscore_anomalies(series: list[tuple[datetime, float]], window: int = 30, threshold: float = 3.0,
                             min_std: float = 0.5) -> list[dict]:
    """Flag points more than `threshold` standard deviations above the trailing baseline.

    - The baseline only uses past points, so it works on live data.
    - Points already flagged as anomalous are kept OUT of the baseline. Otherwise a long incident
      quickly becomes "the new normal" and the detector stops flagging it after a few minutes.
    - `min_std` stops a perfectly flat baseline (std = 0) from turning tiny blips into huge z-scores.
    """
    out = []
    baseline: list[float] = []
    for t, v in series:
        if len(baseline) >= window:
            recent = baseline[-window:]
            mean = statistics.fmean(recent)
            std = max(statistics.pstdev(recent), min_std)
            z = (v - mean) / std
            if z >= threshold:
                out.append({"minute": t, "value": v, "baseline_mean": round(mean, 2), "z": round(z, 1)})
                continue
        baseline.append(v)
    return out


def group_incidents(anomalies: list[dict], gap_minutes: int = 5) -> list[dict]:
    """Merge anomalous minutes that are close together into incident windows."""
    incidents: list[dict] = []
    for a in anomalies:
        if incidents and a["minute"] - incidents[-1]["end"] <= timedelta(minutes=gap_minutes):
            incidents[-1]["end"] = a["minute"]
            incidents[-1]["peak"] = max(incidents[-1]["peak"], a["value"])
            incidents[-1]["minutes"] += 1
        else:
            incidents.append({"start": a["minute"], "end": a["minute"], "peak": a["value"], "minutes": 1})
    return incidents
