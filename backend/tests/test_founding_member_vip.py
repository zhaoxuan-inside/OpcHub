"""创始创客活动：配额内注册创客自动获赠 1 年黑钻 VIP，过期后权益与等级标签自动失效。"""
from datetime import datetime, timedelta

import pytest

from src.core.config import settings
from src.domains.user.models import UserRegisterRequest
from src.domains.user.service import (
    user_service,
    FOUNDING_VIP_ENTITLEMENT_ID,
    FOUNDING_VIP_TIER_NAME,
)

_EXPIRY_FORMAT = "%Y-%m-%d %H:%M:%S"


def _maker_count() -> int:
    return sum(1 for rec in user_service._users_by_email.values() if rec.get("role") != "ADMIN")


def _register(email: str):
    return user_service.register_by_email(UserRegisterRequest(
        email=email,
        password="Founder#Pass2026",
        nickname=email.split("@")[0],
        agreed_terms=True,
    ))


def _unique_email(prefix: str) -> str:
    return f"{prefix}_{datetime.now().timestamp():.0f}@test.com"


async def test_founding_vip_granted_within_quota(monkeypatch):
    ordinal_next = _maker_count() + 1
    monkeypatch.setattr(settings, "founding_member_quota", ordinal_next)

    resp = await _register(_unique_email("founder"))

    assert resp.tier_name == FOUNDING_VIP_TIER_NAME
    assert "创始创客" in resp.message and "1 年黑钻 VIP" in resp.message

    profile = user_service.get_profile(resp.uid)
    vip = next(e for e in profile.entitlements if e.id == FOUNDING_VIP_ENTITLEMENT_ID)
    assert vip.is_active is True

    record = user_service._users_by_uid[resp.uid]
    expiry = datetime.strptime(
        record["entitlement_expiries"][FOUNDING_VIP_ENTITLEMENT_ID], _EXPIRY_FORMAT
    )
    assert timedelta(days=360) < expiry - datetime.now() <= timedelta(days=366)


async def test_founding_vip_denied_beyond_quota(monkeypatch):
    monkeypatch.setattr(settings, "founding_member_quota", _maker_count())

    resp = await _register(_unique_email("late_bloomer"))

    assert resp.tier_name == "标准创客"
    profile = user_service.get_profile(resp.uid)
    vip = next(e for e in profile.entitlements if e.id == FOUNDING_VIP_ENTITLEMENT_ID)
    assert vip.is_active is False


async def test_founding_vip_expires_after_one_year(monkeypatch):
    monkeypatch.setattr(settings, "founding_member_quota", _maker_count() + 1)

    resp = await _register(_unique_email("expiring_founder"))

    record = user_service._users_by_uid[resp.uid]
    record["entitlement_expiries"][FOUNDING_VIP_ENTITLEMENT_ID] = (
        datetime.now() - timedelta(days=1)
    ).strftime(_EXPIRY_FORMAT)

    profile = user_service.get_profile(resp.uid)
    vip = next(e for e in profile.entitlements if e.id == FOUNDING_VIP_ENTITLEMENT_ID)
    assert vip.is_active is False
    assert profile.tier_name == "标准创客"
