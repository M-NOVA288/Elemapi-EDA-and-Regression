"""SLO compliance, error budget and burn-rate alerting.

Burn rate = observed error rate / allowed error rate (1 - SLO).
A burn rate of 1 spends exactly the whole budget over the SLO window; 14.4 spends 2% of a
30-day budget in one hour. Alerting uses the multiwindow, multi-burn-rate approach from the
Google SRE Workbook: page only if BOTH a long and a short window are burning fast, so alerts
fire quickly on real incidents but stop as soon as the problem is fixed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .parse import is_good

# (name, long window, short window, burn-rate threshold, severity)
ALERT_RULES = [
    ("fast-burn", timedelta(hours=1), timedelta(minutes=5), 14.4, "page"),
    ("slow-burn", timedelta(hours=6), timedelta(minutes=30), 6.0, "ticket"),
]


@dataclass
class SloReport:
    slo: float
    total: int
    good: int
    sli: float
    budget_events: float
    budget_spent_events: int
    budget_remaining_pct: float


def slo_report(records: list[dict], slo: float) -> SloReport:
    if not 0 < slo < 1:
        raise ValueError("slo must be between 0 and 1, e.g. 0.995")
    total = len(records)
    good = sum(1 for r in records if is_good(r))
    bad = total - good
    budget = (1 - slo) * total
    remaining = 100.0 if budget == 0 else max(0.0, (1 - bad / budget) * 100)
    return SloReport(slo, total, good, good / total if total else 1.0, budget, bad, remaining)


def burn_rate(records: list[dict], slo: float, end: datetime, window: timedelta) -> float:
    start = end - window
    in_window = [r for r in records if start < r["_ts"] <= end]
    if not in_window:
        return 0.0
    error_rate = sum(1 for r in in_window if not is_good(r)) / len(in_window)
    return error_rate / (1 - slo)


def evaluate_alerts(records: list[dict], slo: float, step: timedelta = timedelta(minutes=1)) -> list[dict]:
    """Replays the logs minute by minute and returns when each alert would have fired and resolved."""
    if not records:
        return []
    t, end = records[0]["_ts"], records[-1]["_ts"]
    firing: dict[str, dict] = {}
    events: list[dict] = []
    while t <= end:
        for name, long_w, short_w, threshold, severity in ALERT_RULES:
            long_br = burn_rate(records, slo, t, long_w)
            short_br = burn_rate(records, slo, t, short_w)
            active = long_br >= threshold and short_br >= threshold
            if active and name not in firing:
                firing[name] = {"alert": name, "severity": severity, "fired_at": t, "peak_burn": long_br}
            elif active:
                firing[name]["peak_burn"] = max(firing[name]["peak_burn"], long_br)
            elif not active and name in firing:
                ev = firing.pop(name)
                ev["resolved_at"] = t
                events.append(ev)
        t += step
    for ev in firing.values():
        ev["resolved_at"] = None
        events.append(ev)
    return sorted(events, key=lambda e: e["fired_at"])
