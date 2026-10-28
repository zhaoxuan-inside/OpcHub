"""Static mail-provider presets and SMTP config resolution.

Pure configuration data + resolution: this module performs no network I/O. The
actual SMTP transmission lives in :mod:`src.domains.user.mailer` behind the
``external.email.send`` operator, and the facts are consumed by

* ``calc.auth.mail_providers`` / ``calc.auth.mail_provider`` (scenario assets),
* the legacy compatibility shims in :mod:`src.domains.user.verification`.
"""
from __future__ import annotations

import os
from typing import Any, Optional

MAIL_PROVIDER_PRESETS: list[dict[str, Any]] = [
    {
        "provider_id": "gmail",
        "display_name": "Google Gmail",
        "domains": ["gmail.com", "googlemail.com"],
        "default_smtp_host": "smtp.gmail.com",
        "default_smtp_port": 465,
        "default_tls": False,
        "auth_note": "Google 账号需开启两步验证，并在「安全性 -> 两步验证」底部生成 16 位应用专用密码 (App Password)",
    },
    {
        "provider_id": "qq",
        "display_name": "腾讯 QQ 邮箱 / Foxmail",
        "domains": ["qq.com", "vip.qq.com", "foxmail.com"],
        "default_smtp_host": "smtp.qq.com",
        "default_smtp_port": 465,
        "default_tls": False,
        "auth_note": "需在 QQ 邮箱「设置 -> 账户」开启 POP3/SMTP 服务并生成独立授权码",
    },
    {
        "provider_id": "163",
        "display_name": "网易 163 邮箱",
        "domains": ["163.com"],
        "default_smtp_host": "smtp.163.com",
        "default_smtp_port": 465,
        "default_tls": False,
        "auth_note": "需在 163 邮箱「设置 -> POP3/SMTP/IMAP」开启服务并设置客户端授权密码",
    },
    {
        "provider_id": "126",
        "display_name": "网易 126 邮箱",
        "domains": ["126.com"],
        "default_smtp_host": "smtp.126.com",
        "default_smtp_port": 465,
        "default_tls": False,
        "auth_note": "需在 126 邮箱设置中开启 POP3/SMTP 服务并获取专用授权码",
    },
    {
        "provider_id": "yeah",
        "display_name": "网易 Yeah 邮箱",
        "domains": ["yeah.net"],
        "default_smtp_host": "smtp.yeah.net",
        "default_smtp_port": 465,
        "default_tls": False,
        "auth_note": "需在 Yeah 邮箱设置中开启 POP3/SMTP 服务并获取专用授权码",
    },
    {
        "provider_id": "outlook",
        "display_name": "微软 Outlook / Hotmail / Office365",
        "domains": ["outlook.com", "hotmail.com", "live.com", "msn.com", "office365.com"],
        "default_smtp_host": "smtp.office365.com",
        "default_smtp_port": 587,
        "default_tls": True,
        "auth_note": "微软个人/商业账户需使用 SMTP AUTH 协议或专用应用密码",
    },
    {
        "provider_id": "aliyun",
        "display_name": "阿里云邮箱 (Aliyun Mail)",
        "domains": ["aliyun.com", "aliyun.cn"],
        "default_smtp_host": "smtp.aliyun.com",
        "default_smtp_port": 465,
        "default_tls": False,
        "auth_note": "需在阿里云邮箱网页端「设置 -> 账户与安全」开启第三方客户端安全密码",
    },
    {
        "provider_id": "exmail",
        "display_name": "腾讯企业邮 (Tencent Exmail)",
        "domains": ["exmail.qq.com"],
        "default_smtp_host": "smtp.exmail.qq.com",
        "default_smtp_port": 465,
        "default_tls": False,
        "auth_note": "需在企业邮「设置 -> 微信绑定与安全」开启客户端专用密码",
    },
    {
        "provider_id": "sina",
        "display_name": "新浪邮箱 (Sina Mail)",
        "domains": ["sina.com", "sina.cn"],
        "default_smtp_host": "smtp.sina.com",
        "default_smtp_port": 465,
        "default_tls": False,
        "auth_note": "需在新浪邮箱设置中开启 POP3/SMTP 并生成动态客户端授权码",
    },
    {
        "provider_id": "sohu",
        "display_name": "搜狐邮箱 (Sohu Mail)",
        "domains": ["sohu.com"],
        "default_smtp_host": "smtp.sohu.com",
        "default_smtp_port": 465,
        "default_tls": False,
        "auth_note": "需在搜狐邮箱选项中开启 SMTP 服务并设置独立访问凭据",
    },
    {
        "provider_id": "icloud",
        "display_name": "Apple iCloud 邮箱",
        "domains": ["icloud.com", "me.com", "mac.com"],
        "default_smtp_host": "smtp.mail.me.com",
        "default_smtp_port": 587,
        "default_tls": True,
        "auth_note": "需登录 appleid.apple.com 生成 App-Specific Password 专用密码",
    },
    {
        "provider_id": "yahoo",
        "display_name": "Yahoo 雅虎邮箱",
        "domains": ["yahoo.com", "yahoo.co.jp", "yahoo.com.cn", "ymail.com"],
        "default_smtp_host": "smtp.mail.yahoo.com",
        "default_smtp_port": 465,
        "default_tls": False,
        "auth_note": "需在 Yahoo Account Security 页面生成专用 App Password",
    },
]

CUSTOM_MAIL_PRESET: dict[str, Any] = {
    "provider_id": "custom",
    "display_name": "企业自有域名 / 通用 SMTP",
    "domains": [],
    "default_smtp_host": "",
    "default_smtp_port": 465,
    "default_tls": False,
    "auth_note": "使用企业定制 SMTP 服务器与授权凭据",
}

_DOMAIN_MAP: dict[str, dict[str, Any]] = {
    domain.lower(): preset
    for preset in MAIL_PROVIDER_PRESETS
    for domain in preset["domains"]
}


def list_mail_providers() -> list[dict[str, Any]]:
    """Return every supported provider preset plus the custom fallback."""
    return [dict(p) for p in MAIL_PROVIDER_PRESETS] + [dict(CUSTOM_MAIL_PRESET)]


def resolve_mail_preset(email_or_domain: str) -> dict[str, Any]:
    """Resolve a provider preset from an email address or bare domain."""
    raw = str(email_or_domain or "").strip().lower()
    domain = raw.split("@")[-1] if "@" in raw else raw
    return dict(_DOMAIN_MAP.get(domain, CUSTOM_MAIL_PRESET))


def _flag(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes")


def resolve_mail_config(to_email: str) -> dict[str, Any]:
    """Resolve the active SMTP configuration for a target mailbox.

    Reads environment configuration only (no network calls). Provider-specific
    ``SMTP_<VENDOR>_*`` credentials win over the global ``SMTP_*`` fallback; when
    neither exists the dispatcher degrades to audited mock mode.
    """
    clean_email = str(to_email or "").strip().lower()
    preset = resolve_mail_preset(clean_email)
    prefix = f"SMTP_{str(preset['provider_id']).upper()}_"

    p_user = os.getenv(f"{prefix}USER")
    p_password = os.getenv(f"{prefix}PASSWORD")
    p_host = os.getenv(f"{prefix}HOST")
    p_port = os.getenv(f"{prefix}PORT")
    p_from = os.getenv(f"{prefix}FROM")
    p_tls = os.getenv(f"{prefix}TLS")

    g_user = os.getenv("SMTP_USER", "")
    g_password = os.getenv("SMTP_PASSWORD", "")
    g_host = os.getenv("SMTP_HOST", "")
    g_port = os.getenv("SMTP_PORT", "")
    g_from = os.getenv("SMTP_FROM", "")
    g_tls = os.getenv("SMTP_TLS", "")

    has_provider_specific = bool(p_user and p_password)
    has_global = bool(g_user and g_password)

    if has_provider_specific:
        user = p_user
        password = p_password
        host = p_host or preset["default_smtp_host"] or g_host
        port = int(p_port) if p_port else (preset["default_smtp_port"] or int(g_port or "465"))
        from_email = p_from or user or g_from or "no-reply@opchub.cn"
        use_tls = _flag(p_tls, bool(preset["default_tls"]))
        routing_tier = "provider_specific"
    elif has_global:
        user = g_user
        password = g_password
        host = g_host or preset["default_smtp_host"]
        port = int(g_port) if g_port else preset["default_smtp_port"]
        from_email = g_from or user or "no-reply@opchub.cn"
        use_tls = _flag(g_tls, bool(preset["default_tls"]))
        routing_tier = "global_fallback"
    else:
        user = ""
        password = ""
        host = p_host or g_host or preset["default_smtp_host"]
        port = int(p_port or g_port or str(preset["default_smtp_port"] or 465))
        from_email = p_from or g_from or "no-reply@opchub.cn"
        use_tls = bool(preset["default_tls"])
        routing_tier = "mock_unconfigured"

    return {
        "configured": bool(user and password and host),
        "routing_tier": routing_tier,
        "provider": preset,
        "provider_id": preset["provider_id"],
        "provider_name": preset["display_name"],
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from_email": from_email,
        "use_tls": use_tls,
        "auth_note": preset["auth_note"],
    }
