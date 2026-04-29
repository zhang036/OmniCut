from fastapi.testclient import TestClient

from app.main import app


def test_assistant_options_returns_deepseek_models_and_reasoning_modes():
    client = TestClient(app)

    response = client.get("/api/assistant/options")

    assert response.status_code == 200
    data = response.json()
    model_ids = {model["id"] for model in data["models"]}
    reasoning_ids = {mode["id"] for mode in data["reasoning_modes"]}
    assert {"deepseek-v4-pro", "deepseek-v4-flash"}.issubset(model_ids)
    assert {"disabled", "high", "max"}.issubset(reasoning_ids)
