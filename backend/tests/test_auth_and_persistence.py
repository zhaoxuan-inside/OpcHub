"""Unit and integration tests for Authentication, Session Security, and Data Persistence (TASK-027)."""
import time
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.security import (
    hash_password,
    verify_password,
    create_session_token,
    verify_session_token,
)
from src.domains.user.service import user_service
from src.domains.user.models import UserRegisterRequest, UserLoginRequest
from src.core.gateway import scenario_router, DispatchRequest


client = TestClient(app)


def test_password_hashing_and_verification():
    """Verify standard PBKDF2-HMAC-SHA256 password hashing security."""
    raw_pwd = "MakerSecurePassword2026!"
    hashed = hash_password(raw_pwd)

    assert "$" in hashed
    parts = hashed.split("$")
    assert len(parts) == 3
    assert int(parts[0]) == 100000
    assert len(parts[1]) > 0
    assert len(parts[2]) > 0

    # Correct password succeeds
    assert verify_password(raw_pwd, hashed) is True
    # Wrong password fails
    assert verify_password("WrongPassword123", hashed) is False
    # Empty password fails
    assert verify_password("", hashed) is False
    # Malformed hash string fails gracefully
    assert verify_password(raw_pwd, "invalid_hash_string") is False


def test_session_token_generation_and_tampering():
    """Verify HMAC-SHA256 session token generation, decoding, and tamper rejection."""
    payload = {
        "uid": "usr_test_1001",
        "email": "test@opchub.cn",
        "nickname": "测试创客",
        "role": "MAKER",
    }
    token = create_session_token(payload, expires_in_seconds=3600)
    parts = token.split(".")
    assert len(parts) == 2

    # Verification of valid token
    decoded = verify_session_token(token)
    assert decoded is not None
    assert decoded["uid"] == "usr_test_1001"
    assert decoded["email"] == "test@opchub.cn"
    assert decoded["nickname"] == "测试创客"
    assert decoded["role"] == "MAKER"

    # Tampered signature rejected
    tampered_sig_token = f"{parts[0]}.tampered_signature_payload"
    assert verify_session_token(tampered_sig_token) is None

    # Tampered payload rejected
    tampered_payload_token = f"eyJ1aWQiOiAidXNyX2hhY2tlciJ9.{parts[1]}"
    assert verify_session_token(tampered_payload_token) is None

    # Expired token rejected
    expired_token = create_session_token(payload, expires_in_seconds=-10)
    assert verify_session_token(expired_token) is None


@pytest.mark.asyncio
async def test_email_registration_validation():
    """Verify input validation rules for email registration."""
    # Invalid email formats
    with pytest.raises(ValueError, match="邮箱格式不正确"):
        await user_service.register_by_email(
            UserRegisterRequest(email="invalid_email_no_at", password="password123")
        )

    with pytest.raises(ValueError, match="邮箱格式不正确"):
        await user_service.register_by_email(
            UserRegisterRequest(email="@no-username.com", password="password123")
        )

    # Password too short (< 6 chars)
    with pytest.raises(ValueError, match="密码长度不能少于 6 位"):
        await user_service.register_by_email(
            UserRegisterRequest(email="valid@test.com", password="123")
        )


@pytest.mark.asyncio
async def test_email_registration_and_login_flow():
    """Verify complete registration, duplicate prevention, and login flow."""
    test_email = f"maker_test_{int(time.time() * 1000)}@opchub.cn"
    test_pwd = "MySecretPassword2026!"

    # 1. Register new maker
    reg_req = UserRegisterRequest(
        email=test_email,
        password=test_pwd,
        nickname="独立开发者小星",
        company_name="小星智能视界工作室",
    )
    reg_resp = await user_service.register_by_email(reg_req)
    assert reg_resp.email == test_email
    assert reg_resp.nickname == "独立开发者小星"
    assert reg_resp.company_name == "小星智能视界工作室"
    assert reg_resp.role == "MAKER"
    assert reg_resp.token is not None
    assert len(reg_resp.token.split(".")) == 2

    # 2. Duplicate registration rejected
    with pytest.raises(ValueError, match="该邮箱已被注册"):
        await user_service.register_by_email(reg_req)

    # 3. Successful Login
    login_resp = await user_service.login_by_email(
        UserLoginRequest(email=test_email, password=test_pwd)
    )
    assert login_resp.email == test_email
    assert login_resp.nickname == "独立开发者小星"
    assert login_resp.token is not None

    # 4. Verify session by token
    session = await user_service.get_session_by_token(login_resp.token)
    assert session is not None
    assert session.email == test_email

    # 5. Wrong password rejected
    with pytest.raises(ValueError, match="邮箱或密码错误"):
        await user_service.login_by_email(
            UserLoginRequest(email=test_email, password="WrongPassword999")
        )

    # 6. Unregistered email rejected
    with pytest.raises(ValueError, match="该邮箱未注册或密码不正确"):
        await user_service.login_by_email(
            UserLoginRequest(email="nonexistent_maker@opchub.cn", password="password123")
        )


@pytest.mark.asyncio
async def test_gateway_auth_scenario_dispatch():
    """Verify unified gateway dispatching for auth.register, auth.login, auth.session."""
    ts = int(time.time() * 1000)
    email = f"gw_user_{ts}@opchub.cn"
    pwd = "GatewayPassword2026"

    # 1. Gateway Register
    reg_req = DispatchRequest(
        scenario="auth.register",
        payload={"email": email, "password": pwd, "nickname": "网关创客"}
    )
    reg_result = await scenario_router.dispatch(reg_req)
    assert reg_result.code == 200
    assert reg_result.data["email"] == email
    assert reg_result.data["nickname"] == "网关创客"
    token = reg_result.data["token"]
    assert token is not None

    # 2. Gateway Login
    login_req = DispatchRequest(
        scenario="auth.login",
        payload={"email": email, "password": pwd}
    )
    login_result = await scenario_router.dispatch(login_req)
    assert login_result.code == 200
    assert login_result.data["email"] == email
    login_token = login_result.data["token"]

    # 3. Gateway Session retrieval
    session_req = DispatchRequest(
        scenario="auth.session",
        payload={"token": login_token}
    )
    session_result = await scenario_router.dispatch(session_req)
    assert session_result.code == 200
    assert session_result.data["email"] == email


def test_fastapi_rest_endpoints():
    """Verify direct REST API endpoints for user authentication."""
    ts = int(time.time() * 1000)
    email = f"rest_maker_{ts}@opchub.cn"
    pwd = "RestPassword2026"

    # POST /api/auth/register
    resp_reg = client.post(
        "/api/auth/register",
        json={"email": email, "password": pwd, "nickname": "REST创客", "company_name": "REST工作室"}
    )
    assert resp_reg.status_code == 201
    data_reg = resp_reg.json()
    assert data_reg["email"] == email
    token = data_reg["token"]

    # POST /api/auth/login
    resp_login = client.post(
        "/api/auth/login",
        json={"email": email, "password": pwd}
    )
    assert resp_login.status_code == 200
    data_login = resp_login.json()
    assert data_login["token"] is not None

    # GET /api/auth/session with token
    resp_sess = client.get(f"/api/auth/session?token={token}")
    assert resp_sess.status_code == 200
    assert resp_sess.json()["email"] == email

    # GET /api/auth/session without token -> 401
    resp_sess_no_token = client.get("/api/auth/session")
    assert resp_sess_no_token.status_code in [400, 401, 422]

    # GET /api/auth/session with invalid token -> 401
    resp_sess_invalid = client.get("/api/auth/session?token=invalid.token.signature")
    assert resp_sess_invalid.status_code == 401
