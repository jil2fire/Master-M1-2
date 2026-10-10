"""Pure time-series calculations. Missing dates are never treated as zero."""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from services.firestore_service import list_data


def _round1(value):
    return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _average(values):
    return _round1(sum(values) / len(values)) if values else None


def calculate(rows):
    if not rows:
        return {
            "period": None, "as_of_date": None, "count": 0, "metrics": None,
            "trend_coverage": None, "trend": None,
            "trend_message": "분석할 예약 데이터가 없습니다. 데이터를 추가해 주세요.",
        }

    records = sorted(rows, key=lambda row: row["date"])
    first = date.fromisoformat(records[0]["date"])
    latest = date.fromisoformat(records[-1]["date"])
    recent_start = latest - timedelta(days=13)
    previous_start = latest - timedelta(days=27)
    previous_end = latest - timedelta(days=14)
    recent = [row["value"] for row in records if recent_start <= date.fromisoformat(row["date"]) <= latest]
    previous = [row["value"] for row in records if previous_start <= date.fromisoformat(row["date"]) <= previous_end]
    weekdays = [row["value"] for row in records if date.fromisoformat(row["date"]).weekday() < 5]
    weekends = [row["value"] for row in records if date.fromisoformat(row["date"]).weekday() >= 5]
    last_week = [row["value"] for row in records if latest - timedelta(days=6) <= date.fromisoformat(row["date"]) <= latest]
    highest = max(records, key=lambda row: row["value"])
    lowest = min(records, key=lambda row: row["value"])
    coverage = {
        "recent_start": recent_start.isoformat(), "recent_end": latest.isoformat(),
        "previous_start": previous_start.isoformat(), "previous_end": previous_end.isoformat(),
        "recent_observed_days": len(recent), "previous_observed_days": len(previous),
    }
    trend = None
    trend_message = None
    if len(recent) < 7 or len(previous) < 7:
        trend_message = "비교할 기록이 부족합니다"
    else:
        recent_raw = sum(recent) / len(recent)
        previous_raw = sum(previous) / len(previous)
        if previous_raw == 0:
            change_rate = 0 if recent_raw == 0 else None
            label = "유지" if recent_raw == 0 else "상승"
            if recent_raw > 0:
                trend_message = "직전 기간 0건에서 증가"
        else:
            raw_change = (recent_raw - previous_raw) / previous_raw * 100
            change_rate = _round1(raw_change)
            label = "상승" if raw_change > 5 else "감소" if raw_change < -5 else "유지"
        trend = {
            "label": label, "change_rate": change_rate,
            "recent_14_day_average": _round1(recent_raw),
            "previous_14_day_average": _round1(previous_raw),
        }
    return {
        "period": f"{first.isoformat()} ~ {latest.isoformat()}",
        "as_of_date": latest.isoformat(), "count": len(records),
        "metrics": {
            "total": sum(row["value"] for row in records),
            "average": _average([row["value"] for row in records]),
            "max": {"date": highest["date"], "value": highest["value"]},
            "min": {"date": lowest["date"], "value": lowest["value"]},
            "weekday_average": _average(weekdays),
            "weekend_average": _average(weekends),
            "recent_7_day_average": _average(last_week),
        },
        "trend_coverage": coverage, "trend": trend, "trend_message": trend_message,
    }


def current_summary():
    return calculate(list_data())
