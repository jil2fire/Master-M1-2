"""Run a separate MCP client process and print proof of live tool calls."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters


async def verify(conversation_id: str | None):
    backend = Path(__file__).resolve().parent
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(backend / "mcp_server.py")],
        cwd=backend,
    )
    async with Client(params) as client:
        tools = await client.list_tools()
        names = sorted(tool.name for tool in tools.tools)
        expected = {"get_reservation_summary", "get_conversation"}
        if not expected.issubset(names):
            raise RuntimeError(f"MCP 도구가 누락됐습니다: {expected - set(names)}")
        print("MCP tools:", ", ".join(names))

        result = await client.call_tool("get_reservation_summary", {})
        if result.is_error:
            raise RuntimeError("요약 도구 호출 실패")
        summary = result.structured_content
        if summary is None and result.content:
            summary = json.loads(result.content[0].text)
        if not isinstance(summary, dict) or summary.get("count", 0) < 100:
            raise RuntimeError("MCP 요약 결과에 100건 이상의 데이터가 없습니다")
        print("get_reservation_summary arguments: {}")
        print("get_reservation_summary result:", json.dumps(summary, ensure_ascii=False))

        if conversation_id:
            result = await client.call_tool("get_conversation", {"conversation_id": conversation_id})
            if result.is_error:
                raise RuntimeError("데모 대화 조회 실패")
            item = result.structured_content
            if item is None and result.content:
                item = json.loads(result.content[0].text)
            if not isinstance(item, dict) or item.get("id") != conversation_id or not item.get("messages"):
                raise RuntimeError("MCP 데모 대화 결과가 올바르지 않습니다")
            print("get_conversation arguments:", json.dumps({"conversation_id": conversation_id}))
            print("get_conversation result:", json.dumps(item, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--conversation-id", help="seed_demo_conversations.py가 출력한 데모 대화 ID")
    args = parser.parse_args()
    asyncio.run(verify(args.conversation_id))
