from app.core.config import Settings
from app.modules.assistant.options import get_assistant_options


def test_default_llm_config_uses_deepseek_v4_pro():
    settings = Settings()

    assert settings.llm_base_url == "https://api.deepseek.com"
    assert settings.llm_model == "deepseek-v4-pro"


def test_assistant_options_use_deepseek_v4_models_and_reasoning_modes():
    options = get_assistant_options()

    assert {model.id for model in options.models} == {"deepseek-v4-pro", "deepseek-v4-flash"}
    assert {mode.id for mode in options.reasoning_modes} == {"disabled", "high", "max"}
