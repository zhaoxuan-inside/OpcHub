"""Persona avatar selection: profile field roundtrip, whitelist enforcement, catalog integrity."""
import pytest

from src.domains.user.service import user_service, BUILTIN_AVATAR_IDS
from src.domains.user.models import UserProfileUpdateRequest


async def test_avatar_update_roundtrip_switch_and_reset():
    """avatar_id 可保存、切换与清空，并通过档案读取回显。"""
    uid = "usr_avatar_test_tmp"
    try:
        prof = await user_service.update_profile(UserProfileUpdateRequest(user_id=uid, avatar_id="dev"))
        assert prof.avatar_id == "dev"
        assert user_service.get_profile(uid).avatar_id == "dev"

        prof = await user_service.update_profile(UserProfileUpdateRequest(user_id=uid, avatar_id="farmer"))
        assert prof.avatar_id == "farmer"
        assert user_service.get_profile(uid).avatar_id == "farmer"

        prof = await user_service.update_profile(UserProfileUpdateRequest(user_id=uid, avatar_id=""))
        assert prof.avatar_id == ""
        assert user_service.get_profile(uid).avatar_id == ""
    finally:
        user_service._users_by_uid.pop(uid, None)


async def test_avatar_update_rejects_unknown_id():
    """非内置画像头像标识被白名单拒绝，且不改动既有档案。"""
    uid = "usr_avatar_test_tmp"
    try:
        await user_service.update_profile(UserProfileUpdateRequest(user_id=uid, avatar_id="designer"))
        with pytest.raises(ValueError):
            await user_service.update_profile(
                UserProfileUpdateRequest(user_id=uid, avatar_id="<svg onload=alert(1)>")
            )
        # 拒绝后原值保持不变
        assert user_service.get_profile(uid).avatar_id == "designer"
    finally:
        user_service._users_by_uid.pop(uid, None)


def test_builtin_avatar_catalog_integrity():
    """内置画像头像恰好 20 种，且与前端画像目录 id 一一对应。"""
    frontend_ids = {
        "dev", "designer", "writer", "founder", "ecommerce", "consultant",
        "photographer", "illustrator", "video", "musician", "teacher",
        "finance", "legal", "crossborder", "researcher", "craftsman",
        "fitness", "foodie", "traveler", "farmer",
    }
    assert len(BUILTIN_AVATAR_IDS) == 20
    assert set(BUILTIN_AVATAR_IDS) == frontend_ids


def test_guest_profile_has_empty_avatar():
    """访客档案头像为空（前端回退为昵称首字圆标）。"""
    assert user_service.get_profile(uid="usr_guest").avatar_id == ""
