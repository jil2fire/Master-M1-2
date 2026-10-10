from fastapi import APIRouter

from schemas.data import DataInput
from services import firestore_service as store
from services.summary_service import current_summary

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("")
def create(payload: DataInput):
    return store.create_data(payload.model_dump(mode="json"))


@router.get("")
def list_items():
    return store.list_data()


@router.get("/summary")
def summary():
    return current_summary()


@router.put("/{data_id}")
def update(data_id: str, payload: DataInput):
    return store.update_data(data_id, payload.model_dump(mode="json"))


@router.delete("/{data_id}")
def delete(data_id: str):
    store.delete_data(data_id)
    return {"ok": True}
