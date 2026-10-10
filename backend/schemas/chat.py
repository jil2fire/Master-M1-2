from pydantic import BaseModel, Field, field_validator


class ChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = None

    @field_validator("message", mode="before")
    @classmethod
    def strip_message(cls, value):
        if not isinstance(value, str):
            return value
        value = value.strip()
        if not value:
            raise ValueError("질문은 비어 있을 수 없습니다")
        return value
