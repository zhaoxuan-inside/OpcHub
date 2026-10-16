"""Configuration module for OpcHub."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application global settings."""
    app_name: str = "OpcHub Microkernel Platform"
    app_version: str = "v1.0.4-live"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(env_prefix="OPCHUB_", env_file=".env", extra="ignore")


settings = Settings()
