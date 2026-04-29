from app.modules.assistant.context import build_llm_messages
from app.modules.assistant.models import AssistantMessage


def test_build_llm_messages_excludes_reasoning_content():
    messages = [
        AssistantMessage(role="user", content="第一轮问题", sequence=1),
        AssistantMessage(role="assistant", content="第一轮回答", reasoning_content="内部思考链", sequence=2),
    ]

    llm_messages = build_llm_messages(messages, "第二轮问题")

    assert llm_messages == [
        {"role": "user", "content": "第一轮问题"},
        {"role": "assistant", "content": "第一轮回答"},
        {"role": "user", "content": "第二轮问题"},
    ]
    assert all("reasoning_content" not in message for message in llm_messages)
