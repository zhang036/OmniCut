from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field("OmniCut API", validation_alias="APP_NAME")
    app_version: str = Field("0.1.0", validation_alias="APP_VERSION")
    environment: str = Field("development", validation_alias="ENVIRONMENT")
    app_debug: bool = Field(True, validation_alias="APP_DEBUG")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])
    database_url: str = Field("mysql+pymysql://root:password@127.0.0.1:3306/omnicut?charset=utf8mb4", validation_alias="DATABASE_URL")
    llm_base_url: str = Field("https://api.deepseek.com", validation_alias="LLM_BASE_URL")
    llm_api_key: str = Field("", validation_alias="LLM_API_KEY")
    llm_model: str = Field("deepseek-v4-pro", validation_alias="LLM_MODEL")

    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
