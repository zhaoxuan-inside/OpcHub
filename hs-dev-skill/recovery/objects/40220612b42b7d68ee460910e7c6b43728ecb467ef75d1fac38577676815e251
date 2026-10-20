"""Comprehensive Verification & Regression Suite for Commercial Registration.

Validates all dimensions of commercial registration:
1. Legal compliance & consent gate (PIPL / Cybersecurity Law: no default consent).
2. Anti-bot SVG Captcha generation & single-use consumption.
3. Email verification code lifecycle: 60s cooldown, 5-minute TTL, attempt limit, single-use.
4. Enterprise password strength policy, entropy scoring, and dictionary blacklist.
5. Unified social credit code and commercial entity types (Maker, OPC, Enterprise).
6. Gateway scenarios dispatch: auth.captcha, auth.send-code, auth.verify-code, auth.password-strength, auth.legal-agreements, auth.register.
7. Direct REST endpoints compatibility and error mapping.
"""
import time
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.domains.user.service import user_service
from src.domains.user.models import UserRegisterRequest, UserProfileUpdateRequest
from src.domains.user.verification import (
    captcha_service,
    email_verification_service,
    PasswordPolicyService,
)

client = TestClient(app)


# =============================================================================
# 1. Anti-Bot SVG Captcha Tests
# =============================================================================
def test_anti_bot_captcha_generation_and_single_use():
    """Verify SVG captcha is generated without external dependencies and is strictly single-use."""
    cap = captcha_service.generate()
    assert "captcha_id" in cap
    assert cap["captcha_id"].startswith("cap_")
    assert "<svg" in cap["captcha_svg"]
    assert "</svg>" in cap["captcha_svg"]
    assert cap["captcha_image"].startswith("data:image/svg+xml")
    assert cap["expires_in"] == 300

    cid = cap["captcha_id"]
    # Retrieve the stored expected answer
    stored = captcha_service._store.get(cid)
    assert stored is not None
    correct_ans = stored["answer"]

    # Incorrect answer fails
    assert not captcha_service.verify(cid, "wrong_answer_xyz")
    # Single-use consumption ensures second attempt also fails
    assert not captcha_service.verify(cid, correct_ans)

    # Test fresh captcha with correct answer
    cap2 = captcha_service.generate()
    cid2 = cap2["captcha_id"]
    ans2 = captcha_service._store[cid2]["answer"]
    assert captcha_service.verify(cid2, ans2)
    # Once verified, it is invalidated immediately
    assert not captcha_service.verify(cid2, ans2)

    # Test bypass token
    assert captcha_service.verify("test_captcha_bypass", "anything")


# =============================================================================
# 2. Email Verification Code & Rate Limiting Tests
# =============================================================================
def test_email_verification_code_lifecycle():
    """Verify code dispatch, 60s cooldown rate limiting, verification, and single-use."""
    test_email = f"commercial_{int(time.time() * 1000)}@opchub.cn"

    # 1. First send succeeds
    res = email_verification_service.send_code(test_email)
    assert res["sent"] is True
    assert res["cooldown_seconds"] == 60
    assert "debug_code" not in res  # Never leaked in public response
    code = email_verification_service.get_last_code(test_email)
    assert code is not None and len(code) == 6

    # 2. Immediate second send is rejected by 60s cooldown
    with pytest.raises(ValueError, match="验证码发送过于频繁"):
        email_verification_service.send_code(test_email)

    # 3. Wrong code fails
    assert not email_verification_service.verify_code(test_email, "000000")

    # 4. Correct code succeeds
    assert email_verification_service.verify_code(test_email, code)

    # 5. Single-use: reusing the code fails
    assert not email_verification_service.verify_code(test_email, code)


def test_email_verification_max_attempts_exceeded():
    """Verify exceeding max attempts invalidates the verification code."""
    test_email = f"bruteforce_{int(time.time() * 1000)}@opchub.cn"
    email_verification_service.send_code(test_email)

    # 5 failed attempts
    for _ in range(5):
        assert not email_verification_service.verify_code(test_email, "999999")

    # 6th attempt triggers max-attempts error
    with pytest.raises(ValueError, match="验证码连续错误次数超限"):
        email_verification_service.verify_code(test_email, "999999")


# =============================================================================
# 3. Password Strength & Policy Tests
# =============================================================================
def test_password_strength_evaluation():
    """Verify password entropy, common dictionary rejection, and suggestions."""
    # Too short
    short = PasswordPolicyService.evaluate("123")
    assert short["level"] == "TOO_SHORT"
    assert short["meets_commercial_standard"] is False

    # Weak dictionary
    weak = PasswordPolicyService.evaluate("12345678")
    assert weak["score"] <= 1
    assert "过于简单" in " ".join(weak["feedback"])
    assert weak["meets_commercial_standard"] is False

    # Fair
    fair = PasswordPolicyService.evaluate("Maker2026")
    assert fair["score"] >= 2
    assert fair["meets_commercial_standard"] is True

    # Strong
    strong = PasswordPolicyService.evaluate("OpcHub#SuperMaker999!")
    assert strong["score"] >= 4
    assert strong["level"] == "STRONG"
    assert strong["meets_commercial_standard"] is True


# =============================================================================
# 4. Legal Compliance & Commercial Registration Gates
# =============================================================================
@pytest.mark.asyncio
async def test_commercial_registration_consent_required():
    """Verify that unchecking or omitting terms agreement is strictly rejected."""
    test_email = f"no_consent_{int(time.time() * 1000)}@opchub.cn"
    req = UserRegisterRequest(
        email=test_email,
        password="MySecurePassword2026!",
        agreed_terms=False,  # Explicitly refused consent
    )
    with pytest.raises(ValueError, match="必须阅读并同意《用户服务协议》与《隐私保护指引》"):
        await user_service.register_by_email(req)


@pytest.mark.asyncio
async def test_commercial_registration_weak_password_rejected():
    """Verify trivial passwords like 123456 are rejected by commercial policy."""
    test_email = f"weak_pwd_{int(time.time() * 1000)}@opchub.cn"
    req = UserRegisterRequest(
        email=test_email,
        password="123456",  # Common trivial password
        agreed_terms=True,
    )
    with pytest.raises(ValueError, match="密码过于简单"):
        await user_service.register_by_email(req)


@pytest.mark.asyncio
async def test_commercial_registration_invalid_credit_code_rejected():
    """Verify malformed unified social credit code is rejected."""
    test_email = f"bad_credit_{int(time.time() * 1000)}@opchub.cn"
    req = UserRegisterRequest(
        email=test_email,
        password="MySecurePassword2026!",
        agreed_terms=True,
        credit_code="SHORT_123",  # Malformed credit code
    )
    with pytest.raises(ValueError, match="统一社会信用代码格式不正确"):
        await user_service.register_by_email(req)


@pytest.mark.asyncio
async def test_commercial_registration_full_success_flow():
    """Verify complete commercial registration with verification code and corporate profile."""
    test_email = f"opc_founder_{int(time.time() * 1000)}@opchub.cn"
    send_res = user_service.send_verification_code(test_email)
    assert send_res["sent"] is True
    verify_code = email_verification_service.get_last_code(test_email)
    assert verify_code is not None

    req = UserRegisterRequest(
        email=test_email,
        password="FounderSecret2026!#",
        nickname="独立创始人老王",
        company_name="极客视界人工智能一人公司",
        account_type="OPC",
        industry_track="AI原生独立开发与出海SaaS",
        credit_code="91310000X00000000Y",
        phone="13800138000",
        verification_code=verify_code,
        agreed_terms=True,
        agreement_version="v1.2.0",
        invitation_code="VIP_OPC_2026",
    )

    session = await user_service.register_by_email(req)
    assert session.email == test_email
    assert session.nickname == "独立创始人老王"
    assert session.company_name == "极客视界人工智能一人公司"
    assert session.account_type == "OPC"
    assert session.industry_track == "AI原生独立开发与出海SaaS"
    assert session.token is not None

    # Verify profile reflects commercial identity
    profile = user_service.get_profile(session.uid)
    assert profile.company_name == "极客视界人工智能一人公司"
    assert profile.credit_code == "91310000X00000000Y"


# =============================================================================
# 5. Gateway Dispatch Scenarios Tests
# =============================================================================
def test_gateway_scenarios_commercial_auth():
    """Verify dispatching auth scenarios through unified inbound gateway."""
    # 1. auth.captcha
    res_cap = client.post("/api/welcom/opc_world", json={
        "scenario": "auth.captcha",
        "payload": {},
    })
    assert res_cap.status_code == 200
    data_cap = res_cap.json()["data"]
    assert "captcha_id" in data_cap
    assert "<svg" in data_cap["captcha_svg"]

    # 2. auth.password-strength
    res_pwd = client.post("/api/welcom/opc_world", json={
        "scenario": "auth.password-strength",
        "payload": {"password": "SuperSecureOpc2026#!"},
    })
    assert res_pwd.status_code == 200
    data_pwd = res_pwd.json()["data"]
    assert data_pwd["level"] == "STRONG"

    # 3. auth.legal-agreements
    res_leg = client.post("/api/welcom/opc_world", json={
        "scenario": "auth.legal-agreements",
        "payload": {},
    })
    assert res_leg.status_code == 200
    data_leg = res_leg.json()["data"]
    assert "terms_of_service" in data_leg
    assert "privacy_policy" in data_leg

    # 4. auth.send-code
    target_email = f"gw_auth_{int(time.time() * 1000)}@opchub.cn"
    res_send = client.post("/api/welcom/opc_world", json={
        "scenario": "auth.send-code",
        "payload": {"email": target_email},
    })
    assert res_send.status_code == 200
    data_send = res_send.json()["data"]
    assert data_send["sent"] is True
    assert "debug_code" not in data_send
    code = email_verification_service.get_last_code(target_email)
    assert code is not None

    # 5. auth.verify-code
    res_ver = client.post("/api/welcom/opc_world", json={
        "scenario": "auth.verify-code",
        "payload": {"email": target_email, "code": code},
    })
    assert res_ver.status_code == 200
    assert res_ver.json()["data"]["valid"] is True


# =============================================================================
# 6. Direct REST Endpoints Tests
# =============================================================================
def test_direct_rest_auth_endpoints():
    """Verify direct REST endpoints for captcha, agreements, and registration."""
    # GET /api/auth/captcha
    r_cap = client.get("/api/auth/captcha")
    assert r_cap.status_code == 200
    assert "captcha_id" in r_cap.json()

    # GET /api/auth/agreements
    r_agr = client.get("/api/auth/agreements")
    assert r_agr.status_code == 200
    assert "terms_of_service" in r_agr.json()

    # POST /api/auth/register rejection on missing consent
    bad_reg = client.post("/api/auth/register", json={
        "email": f"rest_bad_{int(time.time() * 1000)}@opchub.cn",
        "password": "ValidPassword2026#",
        "agreed_terms": False,
    })
    assert bad_reg.status_code == 400
    assert "必须阅读并同意" in bad_reg.json()["detail"]


@pytest.mark.asyncio
async def test_custom_industry_track_registration_and_profile_update():
    """Verify user can register with a custom industry track and customize/update it later."""
    email = f"custom_track_{int(time.time() * 1000)}@opchub.cn"
    user_service.send_verification_code(email)
    raw_code = email_verification_service.get_last_code(email)

    custom_track = "数字游民与跨境独立工作室"
    req = UserRegisterRequest(
        email=email,
        password="CustomTrack2026#",
        verification_code=raw_code,
        agreed_terms=True,
        account_type="OPC",
        industry_track=custom_track,
        company_name="数字游民先锋工作室",
    )
    session = await user_service.register_by_email(req)
    assert session.industry_track == custom_track

    # Profile reflects the custom track
    prof = user_service.get_profile(session.uid)
    assert prof.industry_track == custom_track
    assert prof.account_type == "OPC"

    # User updates their track to another custom track
    updated_custom_track = "新媒体AI内容工坊与私域变现"
    update_req = UserProfileUpdateRequest(
        user_id=session.uid,
        industry_track=updated_custom_track,
    )
    updated_prof = await user_service.update_profile(update_req, token=session.token)
    assert updated_prof.industry_track == updated_custom_track

    # Retrieve profile again
    prof_after = user_service.get_profile(session.uid)
    assert prof_after.industry_track == updated_custom_track

