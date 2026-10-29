"""Add eight clearly marked, curated demo conversations grounded in live data."""

from datetime import timedelta

from config import db
from services.firestore_service import list_data, now
from services.summary_service import current_summary


def main():
    client = db()
    summary = current_summary()
    metrics = summary["metrics"]
    if not metrics or summary["trend"] is None:
        raise RuntimeError("통계와 추세가 있는 예약 데이터를 먼저 적재하세요")
    trend = summary["trend"]
    rows = list_data()
    latest = summary["as_of_date"]
    prefix = f"데이터 최신일 {latest} 기준, "
    monthly = {}
    for row in rows:
        bucket = monthly.setdefault(row["date"][:7], [])
        bucket.append(row["value"])
    monthly_text = "; ".join(
        f"{month}: {len(values)}일, 총 {sum(values):,}건, 일평균 {sum(values) / len(values):.1f}건"
        for month, values in sorted(monthly.items())
    )
    examples = [
        ("전체 예약 현황 살펴보기", "현재 예약 데이터 현황을 알려줘.",
         prefix + f"기간은 {summary['period']}이며 일별 기록 {summary['count']}개, 총 예약 {metrics['total']:,}건, 일평균 {metrics['average']}건입니다.",
         "이건 실제 운영 데이터야?", "아니요. 화면과 기능 확인을 위해 만든 가상 예약 데이터입니다. 이 대화 역시 통계를 바탕으로 구성한 데모 기록입니다."),
        ("최근 14일 예약 추세", "최근 14일 예약 추세가 어때?",
         prefix + f"최근 14일 평균은 {trend['recent_14_day_average']}건, 직전 14일 평균은 {trend['previous_14_day_average']}건입니다. 변화율은 {trend['change_rate']}%이며 추세 분류는 '{trend['label']}'입니다.",
         "현재 날짜 기준이야?", f"분석 기준은 저장된 데이터 최신일인 {latest}입니다. 두 비교 구간 모두 실제 저장된 일별 기록을 사용합니다."),
        ("평일과 주말 이용 비교", "평일과 주말 중 언제 예약이 많아?",
         prefix + f"평일 평균은 {metrics['weekday_average']}건, 주말 평균은 {metrics['weekend_average']}건입니다.",
         "운영에 어떻게 참고하면 좋을까?", "평균 예약이 높은 요일군을 중심으로 좌석과 인력 배치를 검토할 수 있습니다. 가상 데이터이므로 실제 운영 결정에는 실제 기록을 함께 확인해야 합니다."),
        ("가장 붐빈 날 확인", "예약이 가장 많았던 날은 언제야?",
         prefix + f"최다 예약일은 {metrics['max']['date']}이며 {metrics['max']['value']}건입니다.",
         "그날 기록된 메모도 알려줘.", next(row["memo"] for row in rows if row["date"] == metrics["max"]["date"]) + "입니다. 메모만으로 예약 증가의 인과관계를 확정할 수는 없습니다."),
        ("예약이 적었던 날 확인", "예약이 가장 적었던 날을 알려줘.",
         prefix + f"최소 예약일은 {metrics['min']['date']}이며 {metrics['min']['value']}건입니다.",
         "예약이 없던 날도 있어?", f"현재 저장된 {summary['count']}개 일별 기록 중 예약 0건인 날짜는 {sum(row['value'] == 0 for row in rows)}일입니다."),
        ("월별 예약 현황 비교", "7월부터 월별 예약 현황을 정리해줘.",
         prefix + monthly_text + ".",
         "월별 합계를 비교할 때 주의할 점은?", "월마다 관측 일수와 평일·주말 구성이 다릅니다. 합계와 함께 일평균을 보세요. 마지막 달은 데이터 최신일까지의 기록만 포함합니다."),
        ("최근 일주일 이용 현황", "최근 7일 평균 예약 건수는 얼마야?",
         prefix + f"최근 7일 일평균 예약은 {metrics['recent_7_day_average']}건입니다. 전체 기간 평균은 {metrics['average']}건입니다.",
         "예약률도 계산할 수 있어?", "현재는 예약 건수만 저장되어 있습니다. 전체 좌석 수와 예약 가능한 시간 등 분모가 없어서 좌석 예약률은 계산할 수 없습니다."),
        ("데이터 범위와 기록 관리", "데이터가 언제부터 언제까지 있어?",
         prefix + f"{summary['period']}의 일별 기록 {summary['count']}개가 있습니다. 시작일부터 최신일까지 하루에 한 개씩 저장한 가상 데이터입니다.",
         "기록을 수정하면 분석도 달라져?", "네. 기록을 추가·수정·삭제하면 현재 통계는 다시 계산됩니다. 저장된 과거 답변의 통계 스냅샷은 당시 값이므로 현재 통계와 다를 수 있습니다."),
    ]
    stamp = now()
    added = 0
    for index, (title, question, answer, followup, response) in enumerate(examples, 1):
        ref = client.collection("conversations").document(f"demo-{latest}-{index:02d}")
        if ref.get().exists:
            continue
        created = stamp - timedelta(minutes=len(examples) - index)
        messages = []
        for offset, (role, content) in enumerate([
            ("user", question), ("assistant", answer), ("user", followup), ("assistant", response)
        ]):
            message = {"role": role, "content": content, "created_at": (created + timedelta(seconds=offset)).isoformat()}
            if role == "assistant":
                message.update(analysis_summary={**summary, "calculated_at": stamp.isoformat()}, tool_trace=[])
            messages.append(message)
        ref.create({"title": title, "messages": messages, "is_demo": True,
                    "demo_source": "curated_example", "created_at": created,
                    "updated_at": created + timedelta(seconds=3)})
        added += 1
    print(f"추가한 데모 대화: {added}개")


if __name__ == "__main__":
    main()
