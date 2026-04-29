from app.modules.assistant.models import AssistantMessage


def build_llm_messages(history: list[AssistantMessage], user_content: str) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for message in sorted(history, key=lambda item: item.sequence):
        if message.role in {"system", "user", "assistant"} and message.content:
            messages.append({"role": message.role, "content": message.content})
    messages.append({"role": "user", "content": user_content})
    return messages
