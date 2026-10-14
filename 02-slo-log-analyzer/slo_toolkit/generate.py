"""Synthetic log generator for demos and tests.

Produces logs in the same JSON shape as the Deal Liaison service (ts, level, event, ms, ok,
requestId), with an injected incident so the analysis has something real to find.
The data is synthetic: it is NOT production traffic.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone

EVENTS = [
    # (event, share of traffic, typical latency ms)
    ("http.analyze", 0.55, 60),
    ("http.checkout", 0.15, 450),
    ("webhook.stripe.processed", 0.10, 300),
    ("health.check", 0.20, 120),
]


def generate(minutes: int = 240, rpm: int = 25, incident_start: int = 150, incident_len: int = 15,
             incident_error_rate: float = 0.35, base_error_rate: float = 0.002, seed: int = 7,
             start: datetime | None = None) -> list[dict]:
    rng = random.Random(seed)
    t0 = start or datetime(2026, 10, 12, 14, 0, tzinfo=timezone.utc)
    out = []
    for minute in range(minutes):
        in_incident = incident_start <= minute < incident_start + incident_len
        n = max(1, int(rng.gauss(rpm, rpm * 0.1)))
        for _ in range(n):
            event, _share, base_ms = rng.choices(EVENTS, weights=[e[1] for e in EVENTS])[0]
            ts = t0 + timedelta(minutes=minute, seconds=rng.uniform(0, 59.999))
            # During the incident the database is slow and failing (e.g. connection pool exhausted).
            err_p = incident_error_rate if in_incident else base_error_rate
            ms = rng.lognormvariate(0, 0.35) * base_ms * (6 if in_incident else 1)
            failed = rng.random() < err_p
            out.append({
                "ts": ts.isoformat().replace("+00:00", "Z"),
                "level": "error" if failed else "info",
                "event": event.replace("processed", "failed") if failed and event.startswith("webhook") else event,
                "ms": round(ms),
                "ok": not failed,
                "requestId": f"{rng.getrandbits(64):016x}",
            })
    out.sort(key=lambda r: r["ts"])
    return out


def write_jsonl(records: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
