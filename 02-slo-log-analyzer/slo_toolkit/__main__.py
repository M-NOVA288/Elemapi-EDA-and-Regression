"""Command line: python -m slo_toolkit <command> ...

  report LOGFILE [--slo 0.995] [--event PREFIX]   SLO, error budget, alerts, anomalies, latency by event
  generate OUTFILE [--minutes 240] [--seed 7]     write synthetic demo logs
"""
from __future__ import annotations

import argparse
import sys

from .anomaly import group_incidents, per_minute, rolling_zscore_anomalies
from .generate import generate, write_jsonl
from .parse import read_file
from .slo import evaluate_alerts, slo_report
from .stats import summarize_by_event


def fmt_ms(v):
    return "-" if v is None else f"{v:.0f}"


def cmd_report(args) -> int:
    logs = read_file(args.logfile)
    records = [r for r in logs.records if not args.event or r["event"].startswith(args.event)]
    if not records:
        print("no matching records", file=sys.stderr)
        return 1

    span = records[-1]["_ts"] - records[0]["_ts"]
    print(f"Records: {len(records):,} over {str(span).split('.')[0]}  (malformed lines skipped: {logs.malformed})\n")

    rep = slo_report(records, args.slo)
    print(f"SLO target           {rep.slo:.3%}")
    print(f"Measured SLI         {rep.sli:.3%}  ({rep.good:,} good / {rep.total:,})")
    print(f"Error budget         {rep.budget_events:,.0f} bad events allowed, {rep.budget_spent_events:,} spent")
    print(f"Budget remaining     {rep.budget_remaining_pct:.1f}%\n")

    print("Alerts (multiwindow burn rate)")
    alerts = evaluate_alerts(records, args.slo)
    if not alerts:
        print("  none")
    for a in alerts:
        resolved = a["resolved_at"].strftime("%H:%M") if a["resolved_at"] else "still firing"
        print(f"  {a['severity'].upper():6} {a['alert']:10} fired {a['fired_at']:%H:%M}  resolved {resolved}  peak burn {a['peak_burn']:.1f}x")

    print("\nAnomalies (per-minute errors, rolling z-score >= 3)")
    incidents = group_incidents(rolling_zscore_anomalies(per_minute(records, "errors")))
    if not incidents:
        print("  none")
    for inc in incidents:
        print(f"  {inc['start']:%H:%M}-{inc['end']:%H:%M} UTC  {inc['minutes']} anomalous min, peak {inc['peak']:.0f} errors/min")

    print("\nBy event")
    print(f"  {'event':32} {'count':>7} {'err%':>6} {'p50':>6} {'p95':>6} {'p99':>6}")
    for event, s in summarize_by_event(records).items():
        print(f"  {event:32} {s['count']:>7,} {s['error_rate']*100:>5.2f}% {fmt_ms(s['p50_ms']):>6} {fmt_ms(s['p95_ms']):>6} {fmt_ms(s['p99_ms']):>6}")
    return 0


def cmd_generate(args) -> int:
    recs = generate(minutes=args.minutes, seed=args.seed)
    write_jsonl(recs, args.outfile)
    print(f"wrote {len(recs):,} synthetic records to {args.outfile}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="slo_toolkit")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("logfile")
    r.add_argument("--slo", type=float, default=0.995)
    r.add_argument("--event", help="only events starting with this prefix, e.g. webhook.stripe")
    r.set_defaults(fn=cmd_report)
    g = sub.add_parser("generate")
    g.add_argument("outfile")
    g.add_argument("--minutes", type=int, default=240)
    g.add_argument("--seed", type=int, default=7)
    g.set_defaults(fn=cmd_generate)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
