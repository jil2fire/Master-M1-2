"""Firestore reads and atomic writes shared by HTTP routes and seed scripts."""

from datetime import datetime, timezone

from firebase_admin import firestore

from config import db, settings
from errors import AppError


def now():
    return datetime.now(timezone.utc)


def _public(snapshot):
    if not snapshot.exists:
        return None
    result = {"id": snapshot.id, **snapshot.to_dict()}
    for key in ("created_at", "updated_at"):
        if isinstance(result.get(key), datetime):
            result[key] = result[key].isoformat()
    return result


def list_data():
    return [_public(s) for s in db().collection("data").order_by("date").stream()]


def create_data(payload):
    client = db()
    ref = client.collection("data").document()
    date = payload["date"]
    index = client.collection("data_dates").document(date)
    timestamp = now()

    @firestore.transactional
    def write(transaction):
        if index.get(transaction=transaction).exists:
            raise AppError(409, "해당 날짜의 기록이 이미 있습니다")
        transaction.create(index, {"data_id": ref.id})
        transaction.create(ref, {**payload, "created_at": timestamp, "updated_at": timestamp})

    write(client.transaction())
    return _public(ref.get())


def update_data(data_id, payload):
    client = db()
    ref = client.collection("data").document(data_id)
    new_index = client.collection("data_dates").document(payload["date"])
    timestamp = now()

    @firestore.transactional
    def write(transaction):
        old = ref.get(transaction=transaction)
        if not old.exists:
            raise AppError(404, "기록을 찾을 수 없습니다")
        old_date = old.to_dict()["date"]
        if old_date != payload["date"] and new_index.get(transaction=transaction).exists:
            raise AppError(409, "해당 날짜의 기록이 이미 있습니다")
        if old_date != payload["date"]:
            transaction.create(new_index, {"data_id": data_id})
            transaction.delete(client.collection("data_dates").document(old_date))
        transaction.update(ref, {**payload, "updated_at": timestamp})

    write(client.transaction())
    return _public(ref.get())


def delete_data(data_id):
    client = db()
    ref = client.collection("data").document(data_id)

    @firestore.transactional
    def write(transaction):
        old = ref.get(transaction=transaction)
        if not old.exists:
            raise AppError(404, "기록을 찾을 수 없습니다")
        transaction.delete(ref)
        transaction.delete(client.collection("data_dates").document(old.to_dict()["date"]))

    write(client.transaction())


def create_conversation(title, messages):
    client = db()
    ref = client.collection("conversations").document()
    timestamp = now()
    ref.set({
        "title": title,
        "messages": [{**message, "created_at": timestamp.isoformat()} for message in messages],
        "is_demo": False,
        "created_at": timestamp,
        "updated_at": timestamp,
    })
    return _public(ref.get())


def list_conversations():
    items = []
    for snap in db().collection("conversations").order_by("updated_at", direction=firestore.Query.DESCENDING).stream():
        item = _public(snap)
        items.append({key: item[key] for key in ("id", "title", "created_at", "updated_at")})
    return items


def get_conversation(conversation_id):
    item = _public(db().collection("conversations").document(conversation_id).get())
    if not item:
        raise AppError(404, "대화를 찾을 수 없습니다")
    return item


def delete_conversation(conversation_id):
    ref = db().collection("conversations").document(conversation_id)
    if not ref.get().exists:
        raise AppError(404, "대화를 찾을 수 없습니다")
    ref.delete()


def append_chat(conversation_id, title, question, answer, summary):
    client = db()
    ref = client.collection("conversations").document(conversation_id) if conversation_id else client.collection("conversations").document()
    timestamp = now()
    stamp = timestamp.isoformat()
    pair = [
        {"role": "user", "content": question, "created_at": stamp},
        {"role": "assistant", "content": answer, "created_at": stamp, "analysis_summary": summary},
    ]

    @firestore.transactional
    def write(transaction):
        if conversation_id:
            snap = ref.get(transaction=transaction)
            if not snap.exists:
                raise AppError(404, "대화를 찾을 수 없습니다")
            messages = snap.to_dict().get("messages", [])
            if len(messages) + 2 > 50:
                raise AppError(409, "대화가 길어졌습니다. 새 대화를 시작해 주세요")
            transaction.update(ref, {"messages": messages + pair, "updated_at": timestamp})
        else:
            transaction.create(ref, {"title": title[:100], "messages": pair, "is_demo": False, "created_at": timestamp, "updated_at": timestamp})

    write(client.transaction())
    return {"conversation_id": ref.id, "answer": answer, "saved_at": stamp}


def claim_chat_quota():
    client = db()
    day = now().date().isoformat()
    ref = client.collection("chat_usage").document(day)
    limit = settings()["chat_daily_limit"]

    @firestore.transactional
    def claim(transaction):
        snap = ref.get(transaction=transaction)
        count = snap.to_dict().get("count", 0) if snap.exists else 0
        if count >= limit:
            raise AppError(429, "오늘의 AI 질문 한도에 도달했습니다. UTC 기준 다음 날 다시 시도해 주세요")
        transaction.set(ref, {"count": count + 1, "updated_at": now()})

    claim(client.transaction())
