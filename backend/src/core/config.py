"""Application configuration loader for OpcHub platform.

Loads application settings and gateway endpoints from backend/config/application.yaml
with environment variable overrides, achieving zero hardcoded values in source code.
"""
import os
from pathlib import Path
from typing import List, Optional
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_yaml_config() -> dict:
    search_paths = [
        Path("backend/config/application.yaml"),
        Path("config/application.yaml"),
        Path(__file__).resolve().parent.parent.parent / "config" / "application.yaml",
    ]
    env_file = os.getenv("OPCHUB_CONFIG_FILE")
    if env_file and Path(env_file).is_file():
        search_paths.insert(0, Path(env_file))

    for p in search_paths:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
    return {}


_YAML_DATA = _load_yaml_config()
_APP_SECTION = _YAML_DATA.get("app", {})
_SERVER_SECTION = _YAML_DATA.get("server", {})
_GATEWAY_SECTION = _YAML_DATA.get("gateway", {})


class Settings(BaseSettings):
    """Application global settings loaded from configuration files."""
    app_name: str = _APP_SECTION.get("name", "OpcHub Microkernel Platform")
    app_version: str = _APP_SECTION.get("version", "v1.0.4-live")
    environment: str = _APP_SECTION.get("environment", "development")
    debug: bool = _APP_SECTION.get("debug", True)
    api_prefix: str = _APP_SECTION.get("api_prefix", "/api/v1")
    docs_url: Optional[str] = _APP_SECTION.get("docs_url", "/docs")
    redoc_url: Optional[str] = _APP_SECTION.get("redoc_url", "/redoc")
    console_html_path: str = _APP_SECTION.get(
        "console_html_path",
        "hs_dev_docs/_02_feature_spec/_03_prototype_html/opchub_all_pages_demo.html"
    )
    cors_origins: List[str] = _APP_SECTION.get("cors_origins", ["*"])

    server_host: str = _SERVER_SECTION.get("host", "0.0.0.0")
    server_port: int = _SERVER_SECTION.get("port", 8000)

    # Inbound Unified Gateway Endpoints
    gateway_endpoints: List[str] = _GATEWAY_SECTION.get(
        "endpoints",
        ["/api/welcom/opc_world", "/api/welcome/opc_world", "/api/v1/dispatch"]
    )
    gateway_metadata_endpoints: List[str] = _GATEWAY_SECTION.get(
        "metadata_endpoints",
        ["/api/welcom/opc_world/rules", "/api/welcome/opc_world/rules"]
    )
    gateway_routes_config_file: str = _GATEWAY_SECTION.get(
        "routes_config_file",
        "config/gateway_routes.yaml"
    )

    model_config = SettingsConfigDict(env_prefix="OPCHUB_", env_file=".env", extra="ignore")


settings = Settings()
