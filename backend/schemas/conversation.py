from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MessageInput(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=5000)

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, value):
        if not isinstance(value, str):
            return value
        value = value.strip()
        if not value:
            raise ValueError("메시지는 비어 있을 수 없습니다")
        return value


class ConversationInput(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    messages: list[MessageInput] = Field(min_length=1, max_length=50)

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value):
        if not isinstance(value, str):
            return value
        value = value.strip()
        if not value:
            raise ValueError("제목은 비어 있을 수 없습니다")
        return value
