"""Pytest global test doubles.

RBAC/ABAC is enforced at the unified gateway (TASK-029): privileged scenarios now
require a valid identity. To keep business-logic tests focused, the test client
injects a built-in ADMIN session token by default.

Tests that specifically exercise unauthenticated / insufficient-privilege paths must
clear the header explicitly via ``client.headers.pop("Authorization", None)``.
"""
import fastapi.testclient as _tc
import pytest

from src.core.security import create_session_token
from src.infrastructure.database.persistence import domain_persistence
from src.infrastructure.database.repository import db_repository

# ---------------------------------------------------------------------------
# Hermetic test isolation.
#
# OpcHub degrades gracefully to in-memory storage when PostgreSQL is unavailable
# (ADR-002 / ADR-003). Unit & integration tests must never bind to a live database:
# state would leak across runs and CI has no infrastructure. Force the repository to
# report "not ready" so every DB code path becomes a deterministic no-op.
#
# Real persistence is exercised by ``tests/test_db_persistence_integration.py`` which
# is opt-in via the ``OPCHUB_IT_DATABASE_URL`` environment variable.
# ---------------------------------------------------------------------------
async def _database_unavailable() -> bool:
    return False


db_repository.is_ready = _database_unavailable

# The default suite has no PostgreSQL, so allow domain services to keep their
# deterministic in-memory state. Production runs with ``strict = True`` and therefore
# refuses to accept content that could not be persisted.
domain_persistence.strict = False

# Representative catalog data is now test-only (production ships no seed files).
# Seed the shared domain singletons once, mirroring the previous import-time behaviour.
from catalog_fixtures import (  # noqa: E402
    seed_compliance,
    seed_demands,
    seed_perks,
    seed_policies,
    seed_products,
    seed_sop,
)
from src.domains.compliance.service import compliance_service  # noqa: E402
from src.domains.demands.service import demand_service  # noqa: E402
from src.domains.perks.service import perk_service  # noqa: E402
from src.domains.policies.service import policy_service  # noqa: E402
from src.domains.products.service import product_service  # noqa: E402
from src.domains.sop.service import sop_service  # noqa: E402

seed_products(product_service)
seed_policies(policy_service)
seed_demands(demand_service)
seed_perks(perk_service)
seed_compliance(compliance_service)
seed_sop(sop_service)


@pytest.fixture(autouse=True)
def _ensure_test_catalogs():
    """Re-hydrate test-only catalogs if an earlier test cleared a shared singleton."""
    if not product_service._products:
        seed_products(product_service)
    if not policy_service._policies:
        seed_policies(policy_service)
    if not demand_service._demands:
        seed_demands(demand_service)
    if not perk_service._perks:
        seed_perks(perk_service)
    if not compliance_service._laws:
        seed_compliance(compliance_service)
    if not sop_service._nodes:
        seed_sop(sop_service)
    yield


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


def dispatch(client, scenario, payload=None, version="v1.0.0", token=None):
    """POST a business request through the unified gateway entrypoint.

    Returns the httpx Response of ``POST /api/welcom/opc_world``; callers assert on the
    standardized envelope's ``code`` field (e.g. ``resp.json()["code"] == 200``).
    """
    body = {"scenario": scenario, "version": version, "payload": payload or {}}
    if token is not None:
        body["token"] = token
    return client.post("/api/welcom/opc_world", json=body)


def gw_data(client, scenario, payload=None, version="v1.0.0"):
    """Convenience wrapper returning the envelope ``data`` (asserts success)."""
    resp = dispatch(client, scenario, payload, version)
    body = resp.json()
    assert body.get("code") == 200, f"{scenario} -> {body}"
    return body.get("data")

