"""AI provider adapters with one request-frozen summary for both tool protocols."""

import json
import os

from openai import APIError, AuthenticationError, OpenAI, PermissionDeniedError, RateLimitError

from config import settings
from errors import AppError
from services.firestore_service import get_conversation


TOOLS = [
    {
        "type": "function", "name": "get_reservation_summary",
        "description": "현재 채팅 요청에 고정된 좌석 예약 통계와 14일 추세를 확인합니다.",
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function", "name": "get_conversation",
        "description": "현재 선택된 대화의 이전 메시지를 조회합니다. 현재 대화 ID가 있을 때만 사용합니다.",
        "parameters": {
            "type": "object", "properties": {"conversation_id": {"type": "string"}},
            "required": ["conversation_id"], "additionalProperties": False,
        },
        "strict": True,
    },
]
CHAT_TOOLS = [
    {"type": "function", "function": {key: value for key, value in tool.items() if key != "type"}}
    for tool in TOOLS
]


def _create_response(client, **kwargs):
    try:
        return client.responses.create(**kwargs)
    except (AuthenticationError, PermissionDeniedError):
        raise AppError(503, "OpenAI API 키 인증에 실패했습니다. 서버 환경 변수를 확인해 주세요") from None
    except RateLimitError:
        raise AppError(503, "OpenAI 사용 한도에 도달했습니다. 계정의 사용량을 확인해 주세요") from None
    except APIError:
        raise AppError(503, "AI 서비스에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요") from None


def _create_chat_completion(client, **kwargs):
    try:
        return client.chat.completions.create(**kwargs)
    except (AuthenticationError, PermissionDeniedError):
        raise AppError(503, "AI API 키 인증에 실패했습니다. 서버 환경 변수를 확인해 주세요") from None
    except RateLimitError:
        raise AppError(503, "AI 사용 한도에 도달했습니다. 계정의 사용량을 확인해 주세요") from None
    except APIError:
        raise AppError(503, "AI 서비스에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요") from None


def _run_tool(name, arguments_json, summary, conversation_id):
    try:
        arguments = json.loads(arguments_json)
    except (ValueError, TypeError):
        raise AppError(503, "AI 도구 요청을 해석하지 못했습니다") from None
    if not isinstance(arguments, dict):
        raise AppError(503, "AI 도구 인수가 올바르지 않습니다")
    if name == "get_reservation_summary" and arguments == {}:
        return summary
    if name == "get_conversation" and arguments.get("conversation_id") == conversation_id and conversation_id:
        item = get_conversation(conversation_id)
        return {"id": item["id"], "title": item["title"], "messages": [
            {"role": message["role"], "content": message["content"]} for message in item["messages"][-20:]
        ]}
    return {"error": "현재 대화에서 허용되지 않는 도구 요청입니다"}


def _final_text(value):
    result = (value or "").strip()
    if not result:
        raise AppError(503, "AI 답변을 생성하지 못했습니다. 다시 시도해 주세요")
    if len(result) > 5000:
        raise AppError(503, "AI 답변이 너무 깁니다. 질문을 줄여 다시 시도해 주세요")
    return result


def _answer_chat_completions(client, options, instructions, prior, question, summary, conversation_id, tool_trace):
    messages = [{"role": "system", "content": instructions}, *prior, {"role": "user", "content": question}]
    kwargs = {"model": options["model"], "max_tokens": options["max_output_tokens"], "tools": CHAT_TOOLS}
    executed = 0
    while True:
        completion = _create_chat_completion(client, messages=messages, **kwargs)
        if not completion.choices:
            raise AppError(503, "AI 답변을 생성하지 못했습니다. 다시 시도해 주세요")
        message = completion.choices[0].message
        calls = message.tool_calls or []
        if not calls:
            return _final_text(message.content)
        if executed + len(calls) > 3:
            raise AppError(503, "AI 도구 호출 횟수를 초과했습니다. 다시 시도해 주세요")
        messages.append({
            "role": "assistant", "content": message.content,
            "tool_calls": [{
                "id": call.id, "type": "function",
                "function": {"name": call.function.name, "arguments": call.function.arguments},
            } for call in calls],
        })
        for call in calls:
            result = _run_tool(call.function.name, call.function.arguments, summary, conversation_id)
            tool_trace.append({
                "name": call.function.name,
                "arguments": json.loads(call.function.arguments),
                "result": result,
            })
            messages.append({
                "role": "tool", "tool_call_id": call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })
            executed += 1


def answer(question, history, summary, conversation_id, tool_trace=None):
    if not os.getenv("OPENAI_API_KEY"):
        raise AppError(503, "AI 서비스가 설정되지 않았습니다")
    options = settings()
    instructions = (
        "당신은 공유 오피스 좌석 예약 분석 비서 SeatScope AI입니다. "
        "아래 요약에 있는 숫자만 근거로 답하고, 데이터에 없는 사실은 추측하지 마세요. "
        "최근에 관한 답변은 '데이터 최신일 YYYY-MM-DD 기준'이라고 명시하세요. "
        "과거 대화의 숫자는 현재 데이터와 다를 수 있습니다.\n"
        f"[이번 요청의 예약 데이터 요약]\n{json.dumps(summary, ensure_ascii=False)}"
    )
    prior = [{"role": item["role"], "content": item["content"]} for item in history[-20:]]
    if tool_trace is None:
        tool_trace = []
    provider = options["ai_provider"]
    if provider == "codyssey":
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url=options["openai_base_url"])
        return _answer_chat_completions(client, options, instructions, prior, question, summary, conversation_id, tool_trace)
    if provider != "openai":
        raise AppError(503, "AI_PROVIDER 설정이 올바르지 않습니다")
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    kwargs = {
        "model": options["model"], "instructions": instructions,
        "max_output_tokens": options["max_output_tokens"], "tools": TOOLS,
    }
    response = _create_response(client, input=prior + [{"role": "user", "content": question}], **kwargs)
    executed = 0
    while True:
        calls = [item for item in response.output if item.type == "function_call"]
        if not calls:
            return _final_text(response.output_text)
        if executed + len(calls) > 3:
            raise AppError(503, "AI 도구 호출 횟수를 초과했습니다. 다시 시도해 주세요")
        outputs = []
        for call in calls:
            result = _run_tool(call.name, call.arguments, summary, conversation_id)
            tool_trace.append({
                "name": call.name,
                "arguments": json.loads(call.arguments),
                "result": result,
            })
            outputs.append({
                "type": "function_call_output", "call_id": call.call_id,
                "output": json.dumps(result, ensure_ascii=False),
            })
            executed += 1
        response = _create_response(client, previous_response_id=response.id, input=outputs, **kwargs)
