from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(default="sqlite:///./bundles.db", alias="DATABASE_URL")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    # DB tuning
    db_connect_timeout: int = Field(default=10, alias="DB_CONNECT_TIMEOUT")

    # AI settings
    ai_provider: str | None = Field(default=None, alias="AI_PROVIDER")  # "openrouter" or "groq"
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_model: str | None = Field(default=None, alias="OPENROUTER_MODEL")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str | None = Field(default=None, alias="GROQ_MODEL")
    
    # Local Image Generation settings (via cloudflared tunnel)
    local_image_api_url: str = Field(default="https://image.huggle.tech", alias="LOCAL_IMAGE_API_URL")
    image_generation_timeout: int = Field(default=180, alias="IMAGE_GENERATION_TIMEOUT")


settings = Settings()
