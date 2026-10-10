"""Load the checked-in virtual dataset. Existing dates are left untouched."""

import csv
from pathlib import Path

from pydantic import ValidationError

from errors import AppError
from schemas.data import DataInput
from services.firestore_service import create_data


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != ["date", "value", "memo"]:
            raise ValueError("CSV 헤더는 date,value,memo여야 합니다")
        seen = set()
        result = []
        for line_number, row in enumerate(reader, start=2):
            if row["date"] in seen:
                raise ValueError(f"CSV {line_number}행의 날짜가 중복됩니다")
            seen.add(row["date"])
            try:
                payload = DataInput(date=row["date"], value=int(row["value"]), memo=row["memo"])
            except (ValidationError, ValueError) as error:
                raise ValueError(f"CSV {line_number}행이 유효하지 않습니다: {error}") from error
            result.append(payload.model_dump(mode="json"))
        if len(result) != 120:
            raise ValueError(f"초기 데이터는 120행이어야 합니다. 현재 {len(result)}행")
        return result


def main():
    rows = read_rows(Path(__file__).parent / "data" / "initial_data.csv")
    added = skipped = 0
    for row in rows:
        try:
            create_data(row)
            added += 1
        except AppError as error:
            if error.status_code != 409:
                raise
            skipped += 1
    print(f"적재: {added}건, 기존 날짜 건너뜀: {skipped}건")


if __name__ == "__main__":
    main()
