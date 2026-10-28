"""Tests for Admin Dynamic Operator Script Ingestion (RBAC §3.2 four-firewall pipeline)."""
import asyncio
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.security import create_session_token
from src.core.microkernel.registry import registry
from src.core.microkernel.dispatcher import dispatcher
from src.core.microkernel.script_ingestion import script_ingestion_service
from src.core.microkernel.models import DAGConfig, ExecutionGraph, NodeDef
from src.core.microkernel.engine import microkernel_engine

client = TestClient(app)


def _admin_token() -> str:
    return create_session_token({"uid": "admin_test_001", "role": "ADMIN", "nickname": "测试管理员"})


def _maker_token() -> str:
    return create_session_token({"uid": "maker_test_002", "role": "MAKER", "nickname": "普通创客"})


@pytest.fixture(autouse=True)
def clean_dynamic_operators():
    """Ensure no dynamic operator leaks across tests."""
    yield
    for name in list(script_ingestion_service._dynamic_operators.keys()):
        script_ingestion_service.unregister(name, "admin_test_001")
    script_ingestion_service._audit_log.clear()


VALID_SCRIPT = '''
async def action_entry(inputs, context):
    return {"tripled": inputs.get("x", 0) * 3}
'''


def test_upload_registers_operator_into_method_pool():
    """Verify a valid admin script is scanned, loaded and registered into the registry."""
    name = "dynamic.triple"
    resp = client.post("/api/v1/scripts/upload", json={
        "name": name,
        "code": VALID_SCRIPT,
        "token": _admin_token(),
        "description": "测试动态算子",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "REGISTERED"
    assert body["operator_name"] == name
    assert body["entry_function"] == "action_entry"
    assert body["signature_hash"].startswith("sig_sha256_")
    assert body["operator_id"] == "admin_test_001"

    # Registered into the runtime method pool => immediately orchestratable
    assert name in registry.list_handlers()
    assert name in {d.name for d in dispatcher.list_descriptors()}


def test_dynamic_operator_executes_inside_dag():
    """Verify a runtime-registered operator can be orchestrated by a DAG node immediately."""
    name = "dynamic.triple"
    up = client.post("/api/v1/scripts/upload", json={
        "name": name, "code": VALID_SCRIPT, "token": _admin_token(),
    })
    assert up.status_code == 200, up.text

    cfg = DAGConfig(
        scenario_code="dynamic.test.pipeline",
        execution_graph=ExecutionGraph(
            topology="DAG",
            entry_node="n1",
            nodes=[NodeDef(id="n1", action_handler=name, type="BIZ")],
            edges=[],
        ),
    )
    res = asyncio.run(microkernel_engine.execute_dag(cfg, {"x": 14}))
    assert res.status.value == "SUCCESS"
    assert res.final_output.get("tripled") == 42


def test_upload_rejects_non_admin():
    """Verify GUEST and MAKER identities are rejected (endpoint is ADMIN-only)."""
    c = TestClient(app)
    # Unauthenticated (no bearer) => 403
    c.headers.pop("Authorization", None)
    r1 = c.post("/api/v1/scripts/upload", json={"name": "dynamic.x", "code": VALID_SCRIPT})
    assert r1.status_code == 403
    # Authenticated MAKER (USER privileges, lacks ADMIN) => 403
    c.headers["Authorization"] = f"Bearer {_maker_token()}"
    r2 = c.post("/api/v1/scripts/upload", json={"name": "dynamic.x", "code": VALID_SCRIPT})
    assert r2.status_code == 403
    assert "ADMIN" in r2.json()["detail"]
    assert "dynamic.x" not in registry.list_handlers()


def test_reject_forbidden_import():
    """Firewall 1: destructive system imports are rejected."""
    r = client.post("/api/v1/scripts/upload", json={
        "name": "dynamic.evil_import",
        "code": "import os\nasync def action_entry(i, c):\n    return {}",
        "token": _admin_token(),
    })
    assert r.status_code == 400
    assert "Forbidden import" in r.json()["detail"]
    assert "dynamic.evil_import" not in registry.list_handlers()


def test_reject_forbidden_call():
    """Firewall 1: reflection/escape calls (eval/exec/open) are rejected."""
    r = client.post("/api/v1/scripts/upload", json={
        "name": "dynamic.evil_eval",
        "code": "async def action_entry(i, c):\n    return {'x': eval('1+1')}",
        "token": _admin_token(),
    })
    assert r.status_code == 400
    assert "eval" in r.json()["detail"]


def test_reject_reflection_attribute():
    """Firewall 1: dunder reflection escapes (__class__/__bases__) are rejected."""
    r = client.post("/api/v1/scripts/upload", json={
        "name": "dynamic.evil_reflect",
        "code": "async def action_entry(i, c):\n    return {'x': ().__class__.__bases__}",
        "token": _admin_token(),
    })
    assert r.status_code == 400
    assert "reflection attribute" in r.json()["detail"]


def test_reject_non_async_entry():
    """Firewall 2: entry-point convention requires an async function."""
    r = client.post("/api/v1/scripts/upload", json={
        "name": "dynamic.sync_only",
        "code": "def action_entry(i, c):\n    return {}",
        "token": _admin_token(),
    })
    assert r.status_code == 400
    assert "async" in r.json()["detail"].lower()


def test_reject_declared_entry_missing():
    """Firewall 2: a declared entry_function that does not exist is rejected."""
    r = client.post("/api/v1/scripts/upload", json={
        "name": "dynamic.bad_entry",
        "code": VALID_SCRIPT,
        "entry_function": "not_present",
        "token": _admin_token(),
    })
    assert r.status_code == 400
    assert "not found" in r.json()["detail"]


def test_reject_builtin_name_collision():
    """Built-in operators must not be overwritable by dynamic scripts."""
    r = client.post("/api/v1/scripts/upload", json={
        "name": "guard.authn",
        "code": VALID_SCRIPT,
        "token": _admin_token(),
    })
    assert r.status_code == 400
    assert "built-in" in r.json()["detail"]


def test_duplicate_requires_overwrite():
    """Re-uploading the same dynamic name requires explicit overwrite=true."""
    name = "dynamic.dup"
    r1 = client.post("/api/v1/scripts/upload", json={"name": name, "code": VALID_SCRIPT, "token": _admin_token()})
    assert r1.status_code == 200
    r2 = client.post("/api/v1/scripts/upload", json={"name": name, "code": VALID_SCRIPT, "token": _admin_token()})
    assert r2.status_code == 400
    assert "already exists" in r2.json()["detail"]
    r3 = client.post("/api/v1/scripts/upload", json={
        "name": name, "code": VALID_SCRIPT, "token": _admin_token(), "overwrite": True,
    })
    assert r3.status_code == 200


def test_unregister_removes_operator():
    """Verify unregister removes the operator from the pool and 404s when missing."""
    name = "dynamic.temp"
    client.post("/api/v1/scripts/upload", json={"name": name, "code": VALID_SCRIPT, "token": _admin_token()})
    assert name in registry.list_handlers()

    r = client.post(f"/api/v1/scripts/{name}/unregister", json={}, params={"token": _admin_token()})
    assert r.status_code == 200
    assert r.json()["status"] == "UNREGISTERED"
    assert name not in registry.list_handlers()

    r2 = client.post(f"/api/v1/scripts/{name}/unregister", json={}, params={"token": _admin_token()})
    assert r2.status_code == 404


def test_list_dynamic_operators_and_audit_log():
    """Verify listing endpoints expose registered operators and the audit trail."""
    name = "dynamic.listed"
    client.post("/api/v1/scripts/upload", json={"name": name, "code": VALID_SCRIPT, "token": _admin_token()})

    lst = client.get("/api/v1/scripts/operators", params={"token": _admin_token()})
    assert lst.status_code == 200
    names = [o["name"] for o in lst.json()]
    assert name in names

    audit = client.get("/api/v1/scripts/audit", params={"token": _admin_token()})
    assert audit.status_code == 200
    actions = [(a["operator_name"], a["action"], a["status"]) for a in audit.json()]
    assert (name, "REGISTERED", "SUCCESS") in actions
    # Audit records carry the tamper-evident signature hash
    reg = next(a for a in audit.json() if a["operator_name"] == name and a["action"] == "REGISTERED")
    assert reg["signature_hash"].startswith("sig_sha256_")
    assert reg["operator_id"] == "admin_test_001"


def test_list_dynamic_operators_requires_admin():
    """Listing endpoints are ADMIN-only as well."""
    c = TestClient(app)
    c.headers.pop("Authorization", None)
    assert c.get("/api/v1/scripts/operators").status_code == 403
