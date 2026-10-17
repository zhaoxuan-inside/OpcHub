"""Pytest global test doubles.

RBAC/ABAC is enforced at the unified gateway (TASK-029): privileged scenarios now
require a valid identity. To keep business-logic tests focused, the test client
injects a built-in ADMIN session token by default.

Tests that specifically exercise unauthenticated / insufficient-privilege paths must
clear the header explicitly via ``client.headers.pop("Authorization", None)``.
"""
import fastapi.testclient as _tc

from src.core.security import create_session_token

DEFAULT_ADMIN_TOKEN = create_session_token({
    "uid": "usr_admin_builtin",
    "email": "admin@opchub.cn",
    "nickname": "平台超级管理员",
    "role": "ADMIN",
    "must_change_password": False,
})

_OriginalTestClient = _tc.TestClient


class _AuthedTestClient(_OriginalTestClient):
    """TestClient that carries an ADMIN bearer token unless one is explicitly set."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "Authorization" not in self.headers:
            self.headers["Authorization"] = f"Bearer {DEFAULT_ADMIN_TOKEN}"


_tc.TestClient = _AuthedTestClient
