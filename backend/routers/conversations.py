from fastapi import APIRouter

from schemas.conversation import ConversationInput
from services import firestore_service as store

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("")
def create(payload: ConversationInput):
    item = store.create_conversation(payload.title, [m.model_dump() for m in payload.messages])
    return {"conversation_id": item["id"], "conversation": item}


@router.get("")
def list_items():
    return store.list_conversations()


@router.get("/{conversation_id}")
def get(conversation_id: str):
    return store.get_conversation(conversation_id)


@router.delete("/{conversation_id}")
def delete(conversation_id: str):
    store.delete_conversation(conversation_id)
    return {"ok": True}
