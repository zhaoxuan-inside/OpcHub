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
_EXT_SECTION = _YAML_DATA.get("external_gateway", {})
_SILICONFLOW_SECTION = _EXT_SECTION.get("siliconflow", {})
_PAYMENT_SECTION = _EXT_SECTION.get("payment", {})
_WECHAT_SECTION = _PAYMENT_SECTION.get("wechat", {})
_STRIPE_SECTION = _PAYMENT_SECTION.get("stripe", {})
_CRAWLER_SECTION = _EXT_SECTION.get("gov_crawler", {})


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

    # Outbound External Ecosystem Gateways
    siliconflow_base_url: str = _SILICONFLOW_SECTION.get("base_url", "https://api.siliconflow.cn/v1")
    siliconflow_api_key_env: str = _SILICONFLOW_SECTION.get("api_key_env", "SILICONFLOW_API_KEY")
    siliconflow_default_model: str = _SILICONFLOW_SECTION.get("default_model", "deepseek-ai/DeepSeek-V3")
    siliconflow_timeout: float = float(_SILICONFLOW_SECTION.get("timeout_seconds", 30))
    siliconflow_mock_mode: bool = bool(_SILICONFLOW_SECTION.get("mock_mode", True))

    wechat_pay_mch_id: str = _WECHAT_SECTION.get("mch_id", "1900000109")
    wechat_pay_base_url: str = _WECHAT_SECTION.get("base_url", "https://api.mch.weixin.qq.com")
    wechat_pay_api_key_env: str = _WECHAT_SECTION.get("api_key_env", "WECHAT_PAY_V3_KEY")
    wechat_pay_mock_mode: bool = bool(_WECHAT_SECTION.get("mock_mode", True))

    stripe_base_url: str = _STRIPE_SECTION.get("base_url", "https://api.stripe.com")
    stripe_api_key_env: str = _STRIPE_SECTION.get("api_key_env", "STRIPE_SECRET_KEY")
    stripe_mock_mode: bool = bool(_STRIPE_SECTION.get("mock_mode", True))

    gov_crawler_base_url: str = _CRAWLER_SECTION.get("base_url", "https://www.gov.cn")
    gov_crawler_sat_base_url: str = _CRAWLER_SECTION.get("sat_base_url", "https://www.chinatax.gov.cn")
    gov_crawler_rate_limit: float = float(_CRAWLER_SECTION.get("rate_limit_per_second", 2.0))
    gov_crawler_timeout: float = float(_CRAWLER_SECTION.get("timeout_seconds", 15))
    gov_crawler_mock_mode: bool = bool(_CRAWLER_SECTION.get("mock_mode", True))

    model_config = SettingsConfigDict(env_prefix="OPCHUB_", env_file=".env", extra="ignore")


settings = Settings()
