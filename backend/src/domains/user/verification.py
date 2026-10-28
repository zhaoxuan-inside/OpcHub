"""Compatibility shim for commercial security primitives.

The real implementations now live in:

* ``calc.auth.*`` pure operators (password policy, captcha, verification code,
  rate-limit windows, legal agreements, mail provider resolution);
* ``config/scenarios/auth.yaml`` business flows;
* ``external.email.send`` for outbound SMTP I/O.

This module only keeps the historical object surface
(``captcha_service`` / ``email_verification_service`` / ``PasswordPolicyService``
…) that other modules and older tests still import. It carries no registration
or login flow.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from src.core.entity import entity_store
from src.domains.user import functions as user_functions
from src.domains.user.compat import execute_scenario_sync, raise_for_failure
from src.domains.user.entities import (
    ENTITY_USER_CAPTCHA,
    ENTITY_USER_RATE_LIMIT,
    ENTITY_USER_VERIFICATION_CODE,
)
from src.domains.user.mail_config import (
    CUSTOM_MAIL_PRESET,
    MAIL_PROVIDER_PRESETS,
    list_mail_providers,
    resolve_mail_config,
    resolve_mail_preset,
)
from src.domains.user.mailer import send_email_message
from src.domains.user.service import (
    SEND_CODE_PIPELINE,
    VERIFY_CODE_PIPELINE,
)


@dataclass
class EmailProviderPreset:
    """Pre-configured SMTP parameters for one email provider."""

    provider_id: str
    display_name: str
    domains: List[str]
    default_smtp_host: str
    default_smtp_port: int
    default_tls: bool
    auth_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "domains": self.domains,
            "default_smtp_host": self.default_smtp_host,
            "default_smtp_port": self.default_smtp_port,
            "default_tls": self.default_tls,
            "auth_note": self.auth_note,
        }


def _preset_from_dict(raw: dict[str, Any]) -> EmailProviderPreset:
    return EmailProviderPreset(
        provider_id=str(raw.get("provider_id") or ""),
        display_name=str(raw.get("display_name") or ""),
        domains=list(raw.get("domains") or []),
        default_smtp_host=str(raw.get("default_smtp_host") or ""),
        default_smtp_port=int(raw.get("default_smtp_port") or 465),
        default_tls=bool(raw.get("default_tls")),
        auth_note=str(raw.get("auth_note") or ""),
    )


class EmailProviderRegistry:
    """Read-only registry over the declarative provider presets."""

    PRESETS: List[EmailProviderPreset] = [_preset_from_dict(p) for p in MAIL_PROVIDER_PRESETS]
    CUSTOM_PRESET: EmailProviderPreset = _preset_from_dict(CUSTOM_MAIL_PRESET)

    def __init__(self):
        self._domain_map: Dict[str, EmailProviderPreset] = {}
        for preset in self.PRESETS:
            for domain in preset.domains:
                self._domain_map[domain.lower()] = preset

    def resolve(self, email_or_domain: str) -> EmailProviderPreset:
        raw = str(email_or_domain or "").strip().lower()
        domain = raw.split("@")[-1] if "@" in raw else raw
        return self._domain_map.get(domain, self.CUSTOM_PRESET)

    def list_supported_providers(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self.PRESETS] + [self.CUSTOM_PRESET.to_dict()]


email_provider_registry = EmailProviderRegistry()


class EmailDispatcher:
    """Compatibility facade over ``external.email.send``'s SMTP transport."""

    def __init__(self, registry: Optional[EmailProviderRegistry] = None):
        self.registry = registry or email_provider_registry

    def get_provider_config(self, to_email: str) -> Dict[str, Any]:
        cfg = resolve_mail_config(to_email)
        cfg["provider"] = _preset_from_dict(resolve_mail_preset(to_email))
        return cfg

    def dispatch_with_details(self, to_email: str, code: str) -> Dict[str, Any]:
        return send_email_message(
            to_email=to_email,
            subject="【OpcHub 创客商用平台】账号注册核验验证码",
            text=f"您的邮箱核验验证码为：{code}（5 分钟有效）",
            html_body=f"<p>您的邮箱核验验证码为：<b>{code}</b></p>",
            code=code,
        )

    def dispatch(self, to_email: str, code: str) -> bool:
        return bool(self.dispatch_with_details(to_email, code)["success"])


email_dispatcher = EmailDispatcher()


class CaptchaService:
    """Compatibility facade over the captcha scenario + entity store."""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds

    @property
    def _store(self) -> Dict[str, Dict[str, Any]]:
        return {
            str(row.get("captcha_id")): {
                "answer": row.get("answer"),
                "expires_at": row.get("expires_at"),
                "used": row.get("used", False),
            }
            for row in entity_store.adapter(ENTITY_USER_CAPTCHA).all()
        }

    def generate(self) -> Dict[str, Any]:
        result = execute_scenario_sync("OPC_AUTH_CAPTCHA_PIPELINE")
        return raise_for_failure(result).get("response", {})

    def verify(self, captcha_id: Optional[str], candidate: Optional[str]) -> bool:
        if not captcha_id or not candidate:
            return False
        record = entity_store.get(ENTITY_USER_CAPTCHA, {"key": str(captcha_id)})
        decision = user_functions.captcha_verify(
            {},
            {"captcha_id": captcha_id, "captcha_code": candidate, "record": record},
            {},
        )
        if record is not None:
            # Single-use: any verification attempt consumes the challenge.
            entity_store.delete(ENTITY_USER_CAPTCHA, {"key": str(captcha_id)})
        return bool(decision.get("valid"))


captcha_service = CaptchaService()


class EmailVerificationService:
    """Compatibility facade over the send/verify code scenario assets."""

    def __init__(self, ttl_seconds: int = 300, cooldown_seconds: int = 60, max_attempts: int = 5):
        self.ttl_seconds = ttl_seconds
        self.cooldown_seconds = cooldown_seconds
        self.max_attempts = max_attempts
        self.dispatcher = email_dispatcher

    @property
    def _store(self) -> Dict[str, Dict[str, Any]]:
        return {
            str(row.get("email")): dict(row)
            for row in entity_store.adapter(ENTITY_USER_VERIFICATION_CODE).all()
        }

    def check_rate_limit(self, email: str, client_ip: Optional[str] = None) -> Tuple[bool, str]:
        clean_email = str(email or "").strip().lower()
        record = entity_store.get(ENTITY_USER_VERIFICATION_CODE, {"key": clean_email})
        cooldown = user_functions.verification_cooldown(
            {},
            {"record": record, "cooldown_seconds": self.cooldown_seconds},
            {},
        )
        if not cooldown.get("allowed"):
            return False, str(cooldown.get("message") or "验证码发送过于频繁")
        if client_ip:
            rate_record = entity_store.get(
                ENTITY_USER_RATE_LIMIT, {"scope": "IP_SEND_CODE", "key": client_ip}
            )
            decision = user_functions.rate_limit(
                {}, {"record": rate_record, "limit": 30, "window_seconds": 3600}, {}
            )
            if not decision.get("allowed"):
                return False, str(decision.get("message") or "当前 IP 发送请求过于频繁")
        return True, ""

    def send_code(self, email: str, client_ip: Optional[str] = None) -> Dict[str, Any]:
        result = execute_scenario_sync(
            SEND_CODE_PIPELINE,
            {"email": email, "client_ip": client_ip},
        )
        return raise_for_failure(result).get("response", {})

    def verify_code(self, email: str, code: str) -> bool:
        result = execute_scenario_sync(VERIFY_CODE_PIPELINE, {"email": email, "code": code})
        try:
            raise_for_failure(result)
        except ValueError as exc:
            if "连续错误次数超限" in str(exc):
                raise
            return False
        return True

    def is_verified(self, email: str) -> bool:
        clean_email = str(email or "").strip().lower()
        record = entity_store.get(ENTITY_USER_VERIFICATION_CODE, {"key": clean_email})
        return bool(record and record.get("verified"))

    def get_last_code(self, email: str) -> Optional[str]:
        clean_email = str(email or "").strip().lower()
        record = entity_store.get(ENTITY_USER_VERIFICATION_CODE, {"key": clean_email})
        return str(record.get("code")) if record else None


email_verification_service = EmailVerificationService()


class PasswordPolicyService:
    """Compatibility facade over ``calc.auth.password_strength``."""

    COMMON_WEAK_PASSWORDS = user_functions.COMMON_WEAK_PASSWORDS

    @classmethod
    def evaluate(cls, password: str, email: Optional[str] = None) -> Dict[str, Any]:
        return user_functions.password_strength({}, {"password": password, "email": email}, {})


class LegalAgreementsRepository:
    """Compatibility facade over ``calc.auth.legal_agreements``."""

    TERMS_OF_SERVICE_VERSION = user_functions.TERMS_OF_SERVICE_VERSION
    PRIVACY_POLICY_VERSION = user_functions.PRIVACY_POLICY_VERSION
    TERMS_OF_SERVICE_SUMMARY = user_functions.TERMS_OF_SERVICE_SUMMARY
    PRIVACY_POLICY_SUMMARY = user_functions.PRIVACY_POLICY_SUMMARY

    @classmethod
    def get_agreements(cls) -> Dict[str, Any]:
        return user_functions.legal_agreements({}, {}, {})


__all__ = [
    "CaptchaService",
    "EmailDispatcher",
    "EmailProviderPreset",
    "EmailProviderRegistry",
    "EmailVerificationService",
    "LegalAgreementsRepository",
    "PasswordPolicyService",
    "captcha_service",
    "email_dispatcher",
    "email_provider_registry",
    "email_verification_service",
    "list_mail_providers",
]
