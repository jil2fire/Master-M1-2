"""Replace virtual reservations with a current daily dataset after a local backup."""

import argparse
import csv
import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from firebase_admin import firestore

from config import db
from services.firestore_service import now
from services.summary_service import current_summary


def generate_rows(start, end):
    rng = random.Random(20260701)
    rows = []
    for index in range((end - start).days + 1):
        day = start + timedelta(days=index)
        weekend = day.weekday() >= 5
        baseline = 20 if weekend else [47, 54, 58, 56, 45][day.weekday()]
        value = baseline + index // 18 + rng.randint(-7, 7)
        memo = "가상 데이터 · 주말 이용" if weekend else "가상 데이터 · 일반 예약"
        if not weekend and day.day in (8, 22):
            value += 17
            memo = "가상 데이터 · 입주사 교류 행사"
        elif not weekend and day.day in (15, 16):
            value += 9
            memo = "가상 데이터 · 팀 워크숍"
        rows.append({"date": day.isoformat(), "value": max(0, value), "memo": memo})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2026, 7, 1))
    parser.add_argument("--end", type=date.fromisoformat,
                        default=datetime.now(timezone(timedelta(hours=9))).date())
    parser.add_argument("--apply", action="store_true", help="백업 후 기존 가상 예약 전체 교체")
    args = parser.parse_args()
    if args.end < args.start:
        parser.error("종료일은 시작일 이후여야 합니다")
    rows = generate_rows(args.start, args.end)
    if not args.apply:
        print(f"미리보기: {len(rows)}건, {args.start} ~ {args.end}. 반영하려면 --apply")
        return
    client = db()
    stamp = now()
    backup = Path(__file__).parent / ".venv" / "backups" / f"before-refresh-{stamp:%Y%m%dT%H%M%S%fZ}.json"
    backup.parent.mkdir(parents=True, exist_ok=True)
    collections = {
        name: {snap.id: snap.to_dict() for snap in client.collection(name).stream()}
        for name in ("data", "data_dates", "conversations")
    }
    backup.write_text(json.dumps({"project": client.project, "collections": collections},
                                 ensure_ascii=False, default=str, indent=2), encoding="utf-8")
    target_ids = {f"demo-{row['date']}" for row in rows}
    target_dates = {row["date"] for row in rows}

    @firestore.transactional
    def replace(transaction):
        old_data = list(transaction.get(client.collection("data").order_by("__name__")))
        old_dates = list(transaction.get(client.collection("data_dates").order_by("__name__")))
        for snap in old_data:
            if snap.id not in target_ids:
                transaction.delete(snap.reference)
        for snap in old_dates:
            if snap.id not in target_dates:
                transaction.delete(snap.reference)
        for row in rows:
            identifier = f"demo-{row['date']}"
            transaction.set(client.collection("data").document(identifier),
                            {**row, "created_at": stamp, "updated_at": stamp})
            transaction.set(client.collection("data_dates").document(row["date"]),
                            {"data_id": identifier})

    replace(client.transaction())
    path = Path(__file__).parent / "data" / "initial_data.csv"
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["date", "value", "memo"])
        writer.writeheader()
        writer.writerows(rows)
    print("Backup:", backup)
    print(json.dumps(current_summary(), ensure_ascii=False))


if __name__ == "__main__":
    main()
