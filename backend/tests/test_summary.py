import unittest
from datetime import date, timedelta

from services.summary_service import calculate


class SummaryTests(unittest.TestCase):
    def test_empty(self):
        result = calculate([])
        self.assertEqual(result["count"], 0)
        self.assertIsNone(result["metrics"])
        self.assertIsNone(result["trend_coverage"])

    def test_missing_dates_are_not_zero_and_low_coverage_blocks_trend(self):
        rows = [
            {"date": "2025-01-01", "value": 10},
            {"date": "2025-01-15", "value": 20},
            {"date": "2025-01-28", "value": 30},
        ]
        result = calculate(rows)
        self.assertEqual(result["metrics"]["average"], 20)
        self.assertEqual(result["trend_coverage"]["recent_observed_days"], 2)
        self.assertIsNone(result["trend"])

    def test_zero_baseline_and_earliest_tie(self):
        start = date(2025, 1, 1)
        rows = [{"date": (start + timedelta(days=i)).isoformat(), "value": 0 if i < 14 else 10} for i in range(28)]
        result = calculate(rows)
        self.assertEqual(result["trend"]["label"], "상승")
        self.assertIsNone(result["trend"]["change_rate"])
        self.assertEqual(result["metrics"]["max"]["date"], "2025-01-15")
        self.assertEqual(result["metrics"]["min"]["date"], "2025-01-01")

    def test_uses_unrounded_rate_for_five_percent_boundary(self):
        start = date(2025, 1, 1)
        rows = [{"date": (start + timedelta(days=i)).isoformat(), "value": 100 if i < 14 else 105} for i in range(28)]
        result = calculate(rows)
        self.assertEqual(result["trend"]["label"], "유지")
        self.assertEqual(result["trend"]["change_rate"], 5)

    def test_average_rounds_half_up(self):
        rows = [
            {"date": f"2025-01-0{index + 1}", "value": value}
            for index, value in enumerate([1, 1, 1, 2])
        ]
        self.assertEqual(calculate(rows)["metrics"]["average"], 1.3)


if __name__ == "__main__":
    unittest.main()
