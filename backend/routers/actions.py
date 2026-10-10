from hmac import compare_digest

from fastapi import APIRouter, Header

from config import settings
from errors import AppError
from services.firestore_service import get_conversation
from services.summary_service import current_summary

router = APIRouter(prefix="/api/actions", tags=["actions"])


def authorize(authorization):
    secret = settings()["action_api_key"]
    if not secret:
        raise AppError(503, "Actions API가 설정되지 않았습니다")
    expected = f"Bearer {secret}"
    if not authorization or not compare_digest(authorization, expected):
        raise AppError(401, "인증에 실패했습니다")


@router.get("/summary")
def summary(authorization: str | None = Header(default=None)):
    authorize(authorization)
    return current_summary()


@router.get("/conversations/{conversation_id}")
def conversation(conversation_id: str, authorization: str | None = Header(default=None)):
    authorize(authorization)
    item = get_conversation(conversation_id)
    if not item.get("is_demo"):
        raise AppError(404, "대화를 찾을 수 없습니다")
    return {"id": item["id"], "title": item["title"], "messages": item["messages"]}
