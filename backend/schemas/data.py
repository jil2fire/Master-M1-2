from datetime import date
import re

from pydantic import BaseModel, Field, field_validator


class DataInput(BaseModel):
    date: date
    value: int = Field(ge=0, le=1000, strict=True)
    memo: str = Field(default="", max_length=300)

    @field_validator("date", mode="before")
    @classmethod
    def iso_date(cls, value):
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다")
        return date.fromisoformat(value)
