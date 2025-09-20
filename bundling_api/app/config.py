from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(default="sqlite:///./bundles.db", alias="DATABASE_URL")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    # AI settings
    ai_provider: str | None = Field(default=None, alias="AI_PROVIDER")  # "openrouter" or "groq"
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_model: str | None = Field(default=None, alias="OPENROUTER_MODEL")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str | None = Field(default=None, alias="GROQ_MODEL")


settings = Settings()
