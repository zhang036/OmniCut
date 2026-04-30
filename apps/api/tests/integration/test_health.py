import asyncio

import httpx

from app.main import app


async def run_health_endpoint_returns_service_status():
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    try:
        response = await client.get("/api/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "OmniCut API"}
    finally:
        await client.aclose()


def test_health_endpoint_returns_service_status():
    asyncio.run(run_health_endpoint_returns_service_status())
