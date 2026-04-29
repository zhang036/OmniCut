from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging
from app.modules.assistant.router import router as assistant_router

configure_logging()

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assistant_router)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
