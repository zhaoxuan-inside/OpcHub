"""Operator-kernel v2 flow tests for the user / auth domain.

Every business flow is executed through the declarative scenario assets
(``config/scenarios/auth.yaml`` / ``config/scenarios/user.yaml``); identity always
travels in the pipeline ``context``. The legacy service only exposes data/query
shims, so it is used to prove profile reads stay consistent with scenario writes.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from src.core.entity import entity_store
from src.core.scenario import ensure_scenarios_loaded
from src.core.security import verify_session_token
from src.main import app
from src.domains.orchestration.models import ScenarioExecuteRequest
from src.domains.orchestration.service import orchestration_service
from src.domains.user.entities import (
    ENTITY_USER_ACCOUNT,
    ENTITY_USER_CAPTCHA,
    ENTITY_USER_ENTITLEMENT,
    ENTITY_USER_ENTITLEMENT_GRANT,
    ENTITY_USER_RATE_LIMIT,
    ENTITY_USER_VERIFICATION_CODE,
    UserAccountAdapter,
)
from src.domains.user.service import user_service

CAPTCHA_PIPELINE = "OPC_AUTH_CAPTCHA_PIPELINE"
SEND_CODE_PIPELINE = "OPC_AUTH_SEND_CODE_PIPELINE"
VERIFY_CODE_PIPELINE = "OPC_AUTH_VERIFY_CODE_PIPELINE"
REGISTER_PIPELINE = "OPC_AUTH_REGISTER_PIPELINE"
LOGIN_PIPELINE = "OPC_AUTH_LOGIN_PIPELINE"
SESSION_PIPELINE = "OPC_AUTH_SESSION_PIPELINE"
CHANGE_PASSWORD_PIPELINE = "OPC_AUTH_CHANGE_PASSWORD_PIPELINE"
PROFILE_PIPELINE = "OPC_USER_PROFILE_PIPELINE"
PROFILE_UPDATE_PIPELINE = "OPC_USER_PROFILE_UPDATE_PIPELINE"
ENTITLEMENT_ACTIVATE_PIPELINE = "OPC_USER_ENTITLEMENT_ACTIVATE_PIPELINE"

PASSWORD = "Operator#Kernel2026"


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@opchub.test"


async def _run(scenario: str, inputs: dict[str, Any], context: dict[str, Any] | None = None):
    ensure_scenarios_loaded()
    return await orchestration_service.execute_scenario(
        ScenarioExecuteRequest(
            scenario_code=scenario,
            version="v1.0.0",
            inputs=dict(inputs or {}),
            context=dict(context or {}),
        )
    )


async def _send_code(email: str, **extra: Any) -> dict[str, Any]:
    res = await _run(SEND_CODE_PIPELINE, {"email": email, **extra})
    assert res.status == "SUCCESS", res.error_message
    return res.final_output["response"]


async def _register(email: str, password: str = PASSWORD, **overrides: Any) -> dict[str, Any]:
    payload = {
        "email": email,
        "password": password,
        "nickname": email.split("@")[0],
        "agreed_terms": True,
    }
    payload.update(overrides)
    res = await _run(REGISTER_PIPELINE, payload)
    assert res.status == "SUCCESS", res.error_message
    return res.final_output["response"]


@pytest.fixture
def cleanup():
    """Delete every entity document created by one test (keeps process state clean)."""
    entities = [
        ENTITY_USER_ACCOUNT,
        ENTITY_USER_VERIFICATION_CODE,
        ENTITY_USER_CAPTCHA,
        ENTITY_USER_ENTITLEMENT_GRANT,
        ENTITY_USER_RATE_LIMIT,
    ]
    baseline: dict[str, set[str]] = {}
    for name in entities:
        spec = entity_store.spec(name)
        baseline[name] = {spec.key_of(row) for row in entity_store.adapter(name).all()}

    yield

    for name in entities:
        spec = entity_store.spec(name)
        adapter = entity_store.adapter(name)
        for row in list(adapter.all()):
            key = spec.key_of(row)
            if key and key not in baseline[name]:
                adapter.delete(key)


# ---------------------------------------------------------------------------
# 1. Entity declarations / route assets
# ---------------------------------------------------------------------------
def test_user_entity_specs_are_declarative():
    assert entity_store.spec(ENTITY_USER_ACCOUNT).name == "user.account"
    assert isinstance(entity_store.adapter(ENTITY_USER_ACCOUNT), UserAccountAdapter)
    assert entity_store.spec(ENTITY_USER_CAPTCHA).family == "user.captchas"
    assert entity_store.spec(ENTITY_USER_VERIFICATION_CODE).family == "user.verification_codes"
    assert entity_store.spec(ENTITY_USER_ENTITLEMENT).family == "user.entitlements"
    assert entity_store.spec(ENTITY_USER_RATE_LIMIT).family == "user.rate_limits"


def test_route_assets_map_every_user_auth_gateway():
    routes_dir = Path(__file__).resolve().parents[1] / "config" / "routes"
    auth = yaml.safe_load((routes_dir / "auth.yaml").read_text(encoding="utf-8"))["routes"]
    user = yaml.safe_load((routes_dir / "user.yaml").read_text(encoding="utf-8"))["routes"]
    auth_map = {row["gateway"]: row["pipeline"] for row in auth}
    user_map = {row["gateway"]: row["pipeline"] for row in user}
    assert auth_map == {
        "auth.register": REGISTER_PIPELINE,
        "auth.captcha": CAPTCHA_PIPELINE,
        "auth.send-code": SEND_CODE_PIPELINE,
        "auth.verify-code": VERIFY_CODE_PIPELINE,
        "auth.password-strength": "OPC_AUTH_PASSWORD_STRENGTH_PIPELINE",
        "auth.legal-agreements": "OPC_AUTH_LEGAL_AGREEMENTS_PIPELINE",
        "auth.mail-providers": "OPC_AUTH_MAIL_PROVIDERS_PIPELINE",
        "auth.login": LOGIN_PIPELINE,
        "auth.change_password": CHANGE_PASSWORD_PIPELINE,
        "auth.change-password": CHANGE_PASSWORD_PIPELINE,
        "auth.session": SESSION_PIPELINE,
    }
    assert user_map == {
        "user.profile": PROFILE_PIPELINE,
        "user.profile.update": PROFILE_UPDATE_PIPELINE,
        "user.entitlements.activate": ENTITLEMENT_ACTIVATE_PIPELINE,
    }


# ---------------------------------------------------------------------------
# 2. Captcha + verification code lifecycle
# ---------------------------------------------------------------------------
async def test_captcha_is_single_use_and_rejects_wrong_answer(cleanup):
    captcha = await _run(CAPTCHA_PIPELINE, {})
    assert captcha.status == "SUCCESS", captcha.error_message
    body = captcha.final_output["response"]
    assert body["captcha_id"].startswith("cap_")
    assert "<svg" in body["captcha_svg"]
    assert body["captcha_image"].startswith("data:image/svg+xml")
    assert body["expires_in"] == 300

    record = entity_store.get(ENTITY_USER_CAPTCHA, {"key": body["captcha_id"]})
    assert record is not None

    email = _email("captcha_wrong")
    rejected = await _run(
        SEND_CODE_PIPELINE,
        {"email": email, "captcha_id": body["captcha_id"], "captcha_code": "definitely-wrong"},
    )
    assert rejected.status == "FAILED"
    assert "图形验证码错误" in (rejected.error_message or "")
    # Any verification attempt consumes the challenge (anti-replay).
    assert entity_store.get(ENTITY_USER_CAPTCHA, {"key": body["captcha_id"]}) is None

    fresh = (await _run(CAPTCHA_PIPELINE, {})).final_output["response"]
    answer = entity_store.get(ENTITY_USER_CAPTCHA, {"key": fresh["captcha_id"]})["answer"]
    sent = await _run(
        SEND_CODE_PIPELINE,
        {"email": email, "captcha_id": fresh["captcha_id"], "captcha_code": answer},
    )
    assert sent.status == "SUCCESS", sent.error_message
    assert sent.final_output["response"]["sent"] is True


async def test_send_code_cooldown_and_verify_code_single_use(cleanup):
    email = _email("code_lifecycle")
    sent = await _send_code(email)
    assert sent["sent"] is True
    assert sent["cooldown_seconds"] == 60
    assert sent["expires_in"] == 300
    code = sent["mock_code"]
    assert code and len(code) == 6

    cooldown = await _run(SEND_CODE_PIPELINE, {"email": email})
    assert cooldown.status == "FAILED"
    assert "验证码发送过于频繁" in (cooldown.error_message or "")

    wrong = await _run(VERIFY_CODE_PIPELINE, {"email": email, "code": "000000"})
    assert wrong.status == "FAILED"
    assert "验证码错误或已失效" in (wrong.error_message or "")

    ok = await _run(VERIFY_CODE_PIPELINE, {"email": email, "code": code})
    assert ok.status == "SUCCESS", ok.error_message
    assert ok.final_output["response"] == {"valid": True, "message": "验证码有效"}

    reuse = await _run(VERIFY_CODE_PIPELINE, {"email": email, "code": code})
    assert reuse.status == "FAILED"


async def test_verify_code_locks_after_max_attempts(cleanup):
    email = _email("code_bruteforce")
    await _send_code(email)
    for _ in range(5):
        res = await _run(VERIFY_CODE_PIPELINE, {"email": email, "code": "999999"})
        assert res.status == "FAILED"
    locked = await _run(VERIFY_CODE_PIPELINE, {"email": email, "code": "999999"})
    assert locked.status == "FAILED"
    assert "连续错误次数超限" in (locked.error_message or "")


# ---------------------------------------------------------------------------
# 3. Registration
# ---------------------------------------------------------------------------
async def test_register_with_email_code_creates_account_and_session(cleanup):
    email = _email("register_ok")
    code = (await _send_code(email))["mock_code"]

    response = await _register(
        email,
        nickname="独立创客小核",
        company_name="算子内核工作室",
        verification_code=code,
    )
    assert response["email"] == email
    assert response["nickname"] == "独立创客小核"
    assert response["role"] == "MAKER"
    assert response["token"].count(".") == 1

    payload = verify_session_token(response["token"])
    assert payload is not None and payload["uid"] == response["uid"]

    account = entity_store.get(ENTITY_USER_ACCOUNT, {"key": response["uid"]})
    assert account is not None
    assert account["email"] == email
    assert account["password_hash"] and account["password_hash"] != PASSWORD
    # Verification code is single-use: consumed by registration.
    assert entity_store.get(ENTITY_USER_VERIFICATION_CODE, {"key": email}) is None

    session = await _run(SESSION_PIPELINE, {"token": response["token"]})
    assert session.status == "SUCCESS", session.error_message
    assert session.final_output["response"]["authenticated"] is True
    assert session.final_output["response"]["email"] == email


async def test_register_rejects_duplicate_weak_password_and_consent(cleanup):
    email = _email("register_dup")
    await _register(email)

    duplicate = await _run(
        REGISTER_PIPELINE,
        {"email": email, "password": PASSWORD, "agreed_terms": True},
    )
    assert duplicate.status == "FAILED"
    assert "该邮箱已被注册" in (duplicate.error_message or "")

    weak = await _run(
        REGISTER_PIPELINE,
        {"email": _email("register_weak"), "password": "123456", "agreed_terms": True},
    )
    assert weak.status == "FAILED"
    assert "密码过于简单" in (weak.error_message or "")

    short = await _run(
        REGISTER_PIPELINE,
        {"email": _email("register_short"), "password": "123", "agreed_terms": True},
    )
    assert short.status == "FAILED"
    assert "密码长度不能少于 6 位" in (short.error_message or "")

    no_consent = await _run(
        REGISTER_PIPELINE,
        {"email": _email("register_consent"), "password": PASSWORD, "agreed_terms": False},
    )
    assert no_consent.status == "FAILED"
    assert "必须阅读并同意" in (no_consent.error_message or "")


async def test_register_rejects_wrong_verification_code(cleanup):
    email = _email("register_bad_code")
    await _send_code(email)
    result = await _run(
        REGISTER_PIPELINE,
        {"email": email, "password": PASSWORD, "verification_code": "000000", "agreed_terms": True},
    )
    assert result.status == "FAILED"
    assert "邮箱验证码错误或已过期" in (result.error_message or "")
    rows, total = entity_store.list(
        ENTITY_USER_ACCOUNT, {"filters": {"email": email}, "limit": 0}
    )
    assert total == 0


# ---------------------------------------------------------------------------
# 4. Login (password / email-code / account) + session failures
# ---------------------------------------------------------------------------
async def test_login_password_email_code_and_account(cleanup):
    email = _email("login_multi")
    nick = _uid("Nick")
    registered = await _register(email, nickname=nick)

    by_password = await _run(LOGIN_PIPELINE, {"email": email, "password": PASSWORD})
    assert by_password.status == "SUCCESS", by_password.error_message
    assert by_password.final_output["response"]["uid"] == registered["uid"]

    by_account = await _run(
        LOGIN_PIPELINE,
        {"login_type": "account_password", "account": nick, "password": PASSWORD},
    )
    assert by_account.status == "SUCCESS", by_account.error_message
    assert by_account.final_output["response"]["uid"] == registered["uid"]

    by_uid = await _run(
        LOGIN_PIPELINE,
        {"login_type": "account_password", "account": registered["uid"], "password": PASSWORD},
    )
    assert by_uid.status == "SUCCESS", by_uid.error_message

    code = (await _send_code(email))["mock_code"]
    by_code = await _run(LOGIN_PIPELINE, {"email": email, "code": code})
    assert by_code.status == "SUCCESS", by_code.error_message
    assert by_code.final_output["response"]["uid"] == registered["uid"]
    assert entity_store.get(ENTITY_USER_VERIFICATION_CODE, {"key": email}) is None


async def test_login_failures_and_invalid_session(cleanup):
    email = _email("login_fail")
    await _register(email)

    wrong = await _run(LOGIN_PIPELINE, {"email": email, "password": "WrongPassword#1"})
    assert wrong.status == "FAILED"
    assert "邮箱或密码错误" in (wrong.error_message or "")

    unknown = await _run(LOGIN_PIPELINE, {"email": _email("ghost"), "password": PASSWORD})
    assert unknown.status == "FAILED"
    assert "该邮箱未注册或密码不正确" in (unknown.error_message or "")

    bad_code = await _run(LOGIN_PIPELINE, {"email": email, "code": "000000"})
    assert bad_code.status == "FAILED"
    assert "验证码" in (bad_code.error_message or "")

    invalid_session = await _run(SESSION_PIPELINE, {"token": "invalid.token"})
    assert invalid_session.status == "FAILED"
    assert "会话已失效" in (invalid_session.error_message or "")


async def test_change_password_rotates_credential(cleanup):
    email = _email("change_pwd")
    registered = await _register(email)
    new_password = "Rotated#Kernel2026"

    changed = await _run(
        CHANGE_PASSWORD_PIPELINE,
        {"old_password": PASSWORD, "new_password": new_password},
        {"user_id": registered["uid"], "user_role": "MAKER"},
    )
    assert changed.status == "SUCCESS", changed.error_message
    assert changed.final_output["response"]["must_change_password"] is False

    old_login = await _run(LOGIN_PIPELINE, {"email": email, "password": PASSWORD})
    assert old_login.status == "FAILED"
    new_login = await _run(LOGIN_PIPELINE, {"email": email, "password": new_password})
    assert new_login.status == "SUCCESS", new_login.error_message

    wrong_old = await _run(
        CHANGE_PASSWORD_PIPELINE,
        {"old_password": "not-the-password", "new_password": "Another#Kernel2026"},
        {"user_id": registered["uid"], "user_role": "MAKER"},
    )
    assert wrong_old.status == "FAILED"
    assert "原密码不正确" in (wrong_old.error_message or "")


# ---------------------------------------------------------------------------
# 5. Profile read / update
# ---------------------------------------------------------------------------
async def test_profile_guest_and_registered_read(cleanup):
    guest = await _run(PROFILE_PIPELINE, {})
    assert guest.status == "SUCCESS", guest.error_message
    assert guest.final_output["response"]["uid"] == "usr_guest"
    assert guest.final_output["response"]["role"] == "GUEST"

    email = _email("profile_read")
    registered = await _register(
        email,
        nickname="档案创客",
        company_name="超级个体档案所",
        account_type="OPC",
        industry_track="AI 原生独立开发",
    )
    profile = await _run(PROFILE_PIPELINE, {"user_id": registered["uid"]})
    assert profile.status == "SUCCESS", profile.error_message
    body = profile.final_output["response"]
    assert body["orchestrated_by"] == PROFILE_PIPELINE
    assert body["nickname"] == "档案创客"
    assert body["company_name"] == "超级个体档案所"
    assert body["account_type"] == "OPC"
    assert body["entitlements"]
    # The legacy service shim must read the same entity document.
    assert user_service.get_profile(registered["uid"]).nickname == "档案创客"


async def test_profile_update_and_failure_paths(cleanup):
    email = _email("profile_update")
    registered = await _register(email)

    updated = await _run(
        PROFILE_UPDATE_PIPELINE,
        {"nickname": "新昵称", "avatar_id": "dev", "phone": "13800138000"},
        {"user_id": registered["uid"], "user_role": "MAKER"},
    )
    assert updated.status == "SUCCESS", updated.error_message
    body = updated.final_output["response"]
    assert body["nickname"] == "新昵称"
    assert body["avatar_id"] == "dev"
    assert body["phone"] == "13800138000"
    assert user_service.get_profile(registered["uid"]).avatar_id == "dev"

    bad_avatar = await _run(
        PROFILE_UPDATE_PIPELINE,
        {"avatar_id": "<svg onload=alert(1)>"},
        {"user_id": registered["uid"], "user_role": "MAKER"},
    )
    assert bad_avatar.status == "FAILED"
    assert "不支持的头像标识" in (bad_avatar.error_message or "")

    anonymous = await _run(PROFILE_UPDATE_PIPELINE, {"nickname": "游客改名"})
    assert anonymous.status == "GUARD_REJECTED"
    assert "登录" in (anonymous.error_message or "")


# ---------------------------------------------------------------------------
# 6. Entitlement activation
# ---------------------------------------------------------------------------
async def test_entitlement_activation_and_profile_reflection(cleanup):
    email = _email("entitlement")
    registered = await _register(email)
    uid = registered["uid"]

    activated = await _run(
        ENTITLEMENT_ACTIVATE_PIPELINE,
        {"user_id": uid, "entitlement_id": "ent_ai_tax_assistant"},
    )
    assert activated.status == "SUCCESS", activated.error_message
    activation = activated.final_output["activation"]
    assert activation["orchestrated_by"] == ENTITLEMENT_ACTIVATE_PIPELINE
    assert activation["is_active"] is True
    assert activation["receipt_no"].startswith("REC-")

    grant = entity_store.get(
        ENTITY_USER_ENTITLEMENT_GRANT,
        {"user_id": uid, "entitlement_id": "ent_ai_tax_assistant"},
    )
    assert grant is not None and grant["status"] == "ACTIVE"

    profile = await _run(PROFILE_PIPELINE, {"user_id": uid})
    target = next(
        item for item in profile.final_output["response"]["entitlements"]
        if item["id"] == "ent_ai_tax_assistant"
    )
    assert target["is_active"] is True

    # Idempotent re-activation produces a fresh receipt without duplicates.
    again = await _run(
        ENTITLEMENT_ACTIVATE_PIPELINE,
        {"user_id": uid, "entitlement_id": "ent_ai_tax_assistant"},
    )
    assert again.status == "SUCCESS", again.error_message
    rows, total = entity_store.list(
        ENTITY_USER_ENTITLEMENT_GRANT,
        {"filters": {"user_id": uid, "entitlement_id": "ent_ai_tax_assistant"}, "limit": 0},
    )
    assert total == 1


async def test_entitlement_activation_failures(cleanup):
    email = _email("entitlement_fail")
    registered = await _register(email)

    missing_user = await _run(
        ENTITLEMENT_ACTIVATE_PIPELINE,
        {"user_id": "", "entitlement_id": "ent_ai_tax_assistant"},
    )
    assert missing_user.status == "FAILED"
    assert "user_id is required" in (missing_user.error_message or "")

    missing_ent = await _run(
        ENTITLEMENT_ACTIVATE_PIPELINE,
        {"user_id": registered["uid"], "entitlement_id": ""},
    )
    assert missing_ent.status == "FAILED"
    assert "entitlement_id or entitlement_code is required" in (missing_ent.error_message or "")

    unknown = await _run(
        ENTITLEMENT_ACTIVATE_PIPELINE,
        {"user_id": registered["uid"], "entitlement_id": "ent_does_not_exist"},
    )
    assert unknown.status == "FAILED"
    assert "not found" in (unknown.error_message or "")


# ---------------------------------------------------------------------------
# 7. Legacy REST endpoints now execute the scenario assets
# ---------------------------------------------------------------------------
async def test_auth_rest_endpoints_run_scenarios(cleanup):
    ensure_scenarios_loaded()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        captcha = await client.get("/api/auth/captcha")
        assert captcha.status_code == 200
        assert captcha.json()["captcha_id"].startswith("cap_")

        strength = await client.post(
            "/api/auth/password-strength", json={"password": "OpcHub#SuperMaker999!"}
        )
        assert strength.status_code == 200
        assert strength.json()["meets_commercial_standard"] is True

        agreements = await client.get("/api/auth/agreements")
        assert agreements.status_code == 200
        assert agreements.json()["terms_of_service"]["version"]

        providers = await client.get("/api/auth/mail-providers")
        assert providers.status_code == 200
        assert any(p["provider_id"] == "gmail" for p in providers.json())

        email = _email("rest_register")
        registered = await client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": PASSWORD,
                "nickname": "REST 创客",
                "agreed_terms": True,
            },
        )
        assert registered.status_code == 200, registered.text
        assert registered.json()["email"] == email
        assert registered.json()["token"]

        duplicate = await client.post(
            "/api/auth/register",
            json={"email": email, "password": PASSWORD, "agreed_terms": True},
        )
        assert duplicate.status_code == 400
        assert "该邮箱已被注册" in duplicate.json()["detail"]

        wrong = await client.post(
            "/api/auth/login", json={"email": email, "password": "WrongPassword#1"}
        )
        assert wrong.status_code == 400

        login = await client.post(
            "/api/auth/login", json={"email": email, "password": PASSWORD}
        )
        assert login.status_code == 200
        assert login.json()["email"] == email
