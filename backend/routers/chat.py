from datetime import datetime, timezone

from fastapi import APIRouter

from errors import AppError
from schemas.chat import ChatInput
from services import firestore_service as store
from services.ai_service import answer
from services.summary_service import current_summary

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
def chat(payload: ChatInput):
    history = []
    if payload.conversation_id:
        history = store.get_conversation(payload.conversation_id)["messages"]
        if len(history) + 2 > 50:
            raise AppError(409, "대화가 길어졌습니다. 새 대화를 시작해 주세요")
    summary = current_summary()
    if summary["count"] == 0:
        raise AppError(409, summary["trend_message"])
    snapshot = {**summary, "calculated_at": datetime.now(timezone.utc).isoformat()}
    store.claim_chat_quota()
    result = answer(payload.message, history, summary, payload.conversation_id)
    return store.append_chat(payload.conversation_id, payload.message, payload.message, result, snapshot)
