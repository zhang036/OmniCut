import asyncio

import httpx

from app.main import app


async def run_assistant_options_returns_deepseek_models_and_reasoning_modes():
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    try:
        response = await client.get("/api/assistant/options")

        assert response.status_code == 200
        data = response.json()
        model_ids = {model["id"] for model in data["models"]}
        reasoning_ids = {mode["id"] for mode in data["reasoning_modes"]}
        assert {"deepseek-v4-pro", "deepseek-v4-flash"}.issubset(model_ids)
        assert {"disabled", "high", "max"}.issubset(reasoning_ids)
    finally:
        await client.aclose()


def test_assistant_options_returns_deepseek_models_and_reasoning_modes():
    asyncio.run(run_assistant_options_returns_deepseek_models_and_reasoning_modes())
