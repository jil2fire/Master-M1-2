"""Create one virtual conversation for the GPT Actions read-only demo."""

from config import db
from services.firestore_service import now


def main():
    client = db()
    existing = list(client.collection("conversations").where("is_demo", "==", True).limit(1).stream())
    if existing:
        print(f"기존 데모 대화 ID: {existing[0].id}")
        return
    timestamp = now()
    ref = client.collection("conversations").document()
    ref.set({
        "title": "가상 예약 추세 상담",
        "is_demo": True,
        "messages": [
            {"role": "user", "content": "이 서비스는 어떤 데이터를 보나요?", "created_at": timestamp.isoformat()},
            {"role": "assistant", "content": "가상 공유 오피스의 일별 좌석 예약 건수를 분석합니다.", "created_at": timestamp.isoformat()},
        ],
        "created_at": timestamp,
        "updated_at": timestamp,
    })
    print(f"데모 대화 ID: {ref.id}")


if __name__ == "__main__":
    main()
