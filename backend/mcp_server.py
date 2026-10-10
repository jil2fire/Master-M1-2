"""Read-only stdio MCP bridge to the same Firestore data used by the web app."""

from mcp.server import MCPServer

from services.firestore_service import get_conversation as load_conversation
from services.summary_service import current_summary


mcp = MCPServer("SeatScope AI", instructions="가상 좌석 예약 데이터만 조회합니다.")


@mcp.tool()
def get_reservation_summary() -> dict:
    """저장된 일별 예약 건수의 기간, 통계, 최신 14일 추세를 조회합니다."""
    return current_summary()


@mcp.tool()
def get_conversation(conversation_id: str) -> dict:
    """지정한 가상 데모 대화의 제목과 전체 메시지를 조회합니다."""
    item = get_conversation_record(conversation_id)
    return {"id": item["id"], "title": item["title"], "messages": item["messages"]}


def get_conversation_record(conversation_id: str) -> dict:
    item = load_conversation(conversation_id)
    if not item.get("is_demo"):
        raise ValueError("데모 대화만 조회할 수 있습니다")
    return item


if __name__ == "__main__":
    mcp.run(transport="stdio")
