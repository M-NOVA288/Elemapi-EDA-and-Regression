import json
import unittest
from datetime import datetime, timedelta, timezone

from slo_toolkit.anomaly import group_incidents, per_minute, rolling_zscore_anomalies
from slo_toolkit.generate import generate
from slo_toolkit.parse import is_good, read_lines
from slo_toolkit.slo import burn_rate, evaluate_alerts, slo_report
from slo_toolkit.stats import percentile, summarize_by_event

T0 = datetime(2026, 10, 12, 14, 0, tzinfo=timezone.utc)


def rec(minute, ok=True, ms=100, event="http.analyze"):
    ts = (T0 + timedelta(minutes=minute)).isoformat().replace("+00:00", "Z")
    return json.dumps({"ts": ts, "level": "info" if ok else "error", "event": event, "ms": ms, "ok": ok})


class ParseTests(unittest.TestCase):
    def test_bad_lines_are_counted_not_fatal(self):
        logs = read_lines([rec(0), "not json", '{"no": "ts"}', "", rec(1)])
        self.assertEqual(len(logs.records), 2)
        self.assertEqual(logs.malformed, 2)

    def test_records_are_sorted_by_time(self):
        logs = read_lines([rec(5), rec(1)])
        self.assertLess(logs.records[0]["_ts"], logs.records[1]["_ts"])

    def test_good_vs_bad(self):
        self.assertTrue(is_good({"level": "info"}))
        self.assertFalse(is_good({"level": "error"}))
        self.assertFalse(is_good({"level": "warn", "ok": False}))


class StatsTests(unittest.TestCase):
    def test_nearest_rank_percentile(self):
        vals = list(range(1, 101))
        self.assertEqual(percentile(vals, 50), 50)
        self.assertEqual(percentile(vals, 95), 95)
        self.assertEqual(percentile(vals, 99), 99)
        self.assertIsNone(percentile([], 95))

    def test_summary_by_event(self):
        logs = read_lines([rec(0, ms=10), rec(0, ms=20), rec(0, ok=False, ms=30), rec(0, event="x", ms=5)])
        s = summarize_by_event(logs.records)
        self.assertEqual(s["http.analyze"]["count"], 3)
        self.assertAlmostEqual(s["http.analyze"]["error_rate"], 1 / 3)
        self.assertEqual(s["x"]["errors"], 0)


class SloTests(unittest.TestCase):
    def test_budget_math(self):
        lines = [rec(i) for i in range(995)] + [rec(1000 + i, ok=False) for i in range(5)]
        rep = slo_report(read_lines(lines).records, 0.99)
        self.assertEqual(rep.total, 1000)
        self.assertAlmostEqual(rep.sli, 0.995)
        self.assertAlmostEqual(rep.budget_events, 10)
        self.assertEqual(rep.budget_spent_events, 5)
        self.assertAlmostEqual(rep.budget_remaining_pct, 50)

    def test_invalid_slo_rejected(self):
        with self.assertRaises(ValueError):
            slo_report([], 99.5)

    def test_burn_rate(self):
        # 10% errors against a 99% SLO = 10x burn
        lines = [rec(0, ok=(i % 10 != 0)) for i in range(100)]
        recs = read_lines(lines).records
        self.assertAlmostEqual(burn_rate(recs, 0.99, T0 + timedelta(minutes=1), timedelta(hours=1)), 10)

    def test_no_alert_on_healthy_traffic(self):
        recs = read_lines([json.dumps(r) for r in generate(minutes=120, incident_len=0, seed=1)]).records
        self.assertEqual(evaluate_alerts(recs, 0.995), [])

    def test_incident_pages_then_resolves(self):
        recs = read_lines([json.dumps(r) for r in generate(minutes=240, incident_start=150, incident_len=15, seed=3)]).records
        alerts = evaluate_alerts(recs, 0.995)
        page = [a for a in alerts if a["severity"] == "page"]
        self.assertEqual(len(page), 1)
        incident_start = T0 + timedelta(minutes=150)
        self.assertGreaterEqual(page[0]["fired_at"], incident_start)
        self.assertLess(page[0]["fired_at"], incident_start + timedelta(minutes=20))
        self.assertIsNotNone(page[0]["resolved_at"])


class AnomalyTests(unittest.TestCase):
    def test_flags_the_whole_injected_incident(self):
        recs = read_lines([json.dumps(r) for r in generate(minutes=240, incident_start=150, incident_len=15, seed=3)]).records
        incidents = group_incidents(rolling_zscore_anomalies(per_minute(recs, "errors")))
        main = max(incidents, key=lambda i: i["minutes"])
        self.assertEqual(main["start"], T0 + timedelta(minutes=150))
        self.assertGreaterEqual(main["minutes"], 12, "a long incident must not become the new baseline")

    def test_flat_baseline_does_not_flag_small_blips(self):
        series = [(T0 + timedelta(minutes=i), 0.0) for i in range(60)]
        series[45] = (series[45][0], 1.0)
        self.assertEqual(rolling_zscore_anomalies(series), [])

    def test_empty_minutes_are_included(self):
        recs = read_lines([rec(0), rec(5)]).records
        self.assertEqual(len(per_minute(recs, "requests")), 6)


if __name__ == "__main__":
    unittest.main()
