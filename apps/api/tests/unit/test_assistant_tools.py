from app.modules.assistant.tools import get_tool_definitions, should_include_reasoning_content_for_history


def test_tool_definitions_are_reserved_for_future_extension():
    assert get_tool_definitions() == []


def test_reasoning_content_history_rule_matches_deepseek_tool_call_docs():
    assert should_include_reasoning_content_for_history(has_tool_call=False) is False
    assert should_include_reasoning_content_for_history(has_tool_call=True) is True
