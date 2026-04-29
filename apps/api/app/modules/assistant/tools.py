from typing import Any


def get_tool_definitions() -> list[dict[str, Any]]:
    return []


def should_include_reasoning_content_for_history(has_tool_call: bool) -> bool:
    return has_tool_call
