"""Unit & Integration Tests for Multi-Vendor Email Routing & Outbound Dispatcher.

Covers:
1. Provider recognition and preset resolution across mainstream vendors (Google Gmail, QQ, 163, 126, Outlook, Aliyun, Sina, Sohu, iCloud, Yahoo, Custom).
2. Dynamic configuration priority: provider-specific env (SMTP_{VENDOR}_*) vs global fallback (SMTP_*) vs mock audit.
3. Verification code dispatch lifecycle with vendor metadata.
4. Gateway scenario `auth.mail-providers` and direct REST API endpoint.
"""
import os
import time
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.domains.user.verification import (
    email_provider_registry,
    email_dispatcher,
    email_verification_service,
    EmailDispatcher,
    EmailProviderRegistry,
)

client = TestClient(app)


def test_email_provider_detection():
    """Verify that domain strings and email addresses map accurately to provider presets."""
    test_cases = [
        ("maker@gmail.com", "gmail", "Google Gmail", 465, False),
        ("dev@googlemail.com", "gmail", "Google Gmail", 465, False),
        ("user@qq.com", "qq", "腾讯 QQ 邮箱 / Foxmail", 465, False),
        ("ceo@vip.qq.com", "qq", "腾讯 QQ 邮箱 / Foxmail", 465, False),
        ("team@foxmail.com", "qq", "腾讯 QQ 邮箱 / Foxmail", 465, False),
        ("opc@163.com", "163", "网易 163 邮箱", 465, False),
        ("opc@126.com", "126", "网易 126 邮箱", 465, False),
        ("user@yeah.net", "yeah", "网易 Yeah 邮箱", 465, False),
        ("lead@outlook.com", "outlook", "微软 Outlook / Hotmail / Office365", 587, True),
        ("admin@hotmail.com", "outlook", "微软 Outlook / Hotmail / Office365", 587, True),
        ("cloud@aliyun.com", "aliyun", "阿里云邮箱 (Aliyun Mail)", 465, False),
        ("maker@sina.com", "sina", "新浪邮箱 (Sina Mail)", 465, False),
        ("founder@sohu.com", "sohu", "搜狐邮箱 (Sohu Mail)", 465, False),
        ("steve@icloud.com", "icloud", "Apple iCloud 邮箱", 587, True),
        ("investor@yahoo.com", "yahoo", "Yahoo 雅虎邮箱", 465, False),
        ("ceo@independent-opc.cn", "custom", "企业自有域名 / 通用 SMTP", 465, False),
    ]

    for email, expected_id, expected_name, expected_port, expected_tls in test_cases:
        preset = email_provider_registry.resolve(email)
        assert preset.provider_id == expected_id, f"Failed on {email}: got {preset.provider_id}"
        assert preset.display_name == expected_name
        assert preset.default_smtp_port == expected_port
        assert preset.default_tls == expected_tls


def test_provider_specific_configuration_routing(monkeypatch):
    """Verify that provider-specific env variables take priority over global fallback."""
    # Set both provider-specific (Gmail) and global variables
    monkeypatch.setenv("SMTP_GMAIL_USER", "dedicated_gmail@gmail.com")
    monkeypatch.setenv("SMTP_GMAIL_PASSWORD", "gmail_app_password_16ch")
    monkeypatch.setenv("SMTP_GMAIL_FROM", "dedicated_gmail@gmail.com")

    monkeypatch.setenv("SMTP_USER", "global_fallback@opchub.cn")
    monkeypatch.setenv("SMTP_PASSWORD", "global_password")
    monkeypatch.setenv("SMTP_HOST", "smtp.global.com")

    dispatcher = EmailDispatcher()

    # 1. Target Gmail -> must pick dedicated Gmail configuration
    gmail_cfg = dispatcher.get_provider_config("test_user@gmail.com")
    assert gmail_cfg["configured"] is True
    assert gmail_cfg["routing_tier"] == "provider_specific"
    assert gmail_cfg["user"] == "dedicated_gmail@gmail.com"
    assert gmail_cfg["host"] == "smtp.gmail.com"
    assert gmail_cfg["port"] == 465
    assert gmail_cfg["use_tls"] is False

    # 2. Target QQ (no dedicated QQ env set) -> must gracefully fallback to global configuration
    qq_cfg = dispatcher.get_provider_config("test_user@qq.com")
    assert qq_cfg["configured"] is True
    assert qq_cfg["routing_tier"] == "global_fallback"
    assert qq_cfg["user"] == "global_fallback@opchub.cn"
    assert qq_cfg["provider_id"] == "qq"


def test_mock_unconfigured_mode_diagnostics(monkeypatch):
    """Verify mock audit mode when no SMTP credentials are set."""
    # Clean env of any SMTP variables
    for k in list(os.environ.keys()):
        if k.startswith("SMTP_"):
            monkeypatch.delenv(k, raising=False)

    dispatcher = EmailDispatcher()
    details = dispatcher.dispatch_with_details("alice@gmail.com", "123456")

    assert details["success"] is True
    assert details["mode"] == "mock_audit"
    assert details["routing_tier"] == "mock_unconfigured"
    assert details["provider_id"] == "gmail"
    assert details["provider_name"] == "Google Gmail"
    assert details["smtp_host"] == "smtp.gmail.com"
    assert details["smtp_port"] == 465


def test_verification_service_send_code_includes_provider_info():
    """Verify send_code returns enriched provider metadata."""
    target_email = f"user_{int(time.time() * 1000)}@outlook.com"
    res = email_verification_service.send_code(target_email)

    assert res["sent"] is True
    assert res["email"] == target_email
    assert "provider" in res
    assert res["provider"]["provider_id"] == "outlook"
    assert res["provider"]["provider_name"] == "微软 Outlook / Hotmail / Office365"
    assert res["provider"]["smtp_port"] == 587
    assert res["cooldown_seconds"] == 60
    assert "微软 Outlook" in res["message"]


def test_gateway_scenario_mail_providers():
    """Verify dispatching auth.mail-providers through unified inbound gateway."""
    # 1. Retrieve all supported providers
    res = client.post("/api/welcom/opc_world", json={
        "scenario": "auth.mail-providers",
        "payload": {},
    })
    assert res.status_code == 200
    providers = res.json()["data"]
    assert isinstance(providers, list)
    ids = [p["provider_id"] for p in providers]
    assert "gmail" in ids
    assert "qq" in ids
    assert "163" in ids
    assert "outlook" in ids
    assert "custom" in ids

    # 2. Resolve for specific email
    res_gmail = client.post("/api/welcom/opc_world", json={
        "scenario": "auth.mail-providers",
        "payload": {"email": "user@gmail.com"},
    })
    assert res_gmail.status_code == 200
    gmail_info = res_gmail.json()["data"]
    assert gmail_info["provider_id"] == "gmail"
    assert gmail_info["host"] == "smtp.gmail.com"


def test_rest_api_mail_providers():
    """Verify GET /api/auth/mail-providers endpoint."""
    res = client.get("/api/auth/mail-providers")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)

    res_specific = client.get("/api/auth/mail-providers?email=test@qq.com")
    assert res_specific.status_code == 200
    qq_data = res_specific.json()
    assert qq_data["provider_id"] == "qq"
    assert qq_data["host"] == "smtp.qq.com"
