"""M1-1: scenario version rollback and second-person publish approvals."""
import pytest

from src.domains.orchestration.catalog import catalog_service
from src.domains.orchestration.service import orchestration_service


def _graph(nodes):
    return {
        "entry_node": nodes[0]["id"],
        "exit_node": nodes[-1]["id"],
        "enable_saga_compensation": False,
        "nodes": nodes,
        "edges": [
            {"from_node": a["id"], "to_node": b["id"]} for a, b in zip(nodes, nodes[1:])
        ],
    }


def _save_version(code: str, version: str, actor: str):
    catalog_service.save_scenario_version(
        {
            "code": code,
            "version": version,
            "changelog": f"v{version}",
            "graph": _graph([
                {"id": "auth", "operator": "guard.authn", "type": "GUARD"},
                {"id": "load", "operator": "entity.list", "type": "BIZ",
                 "params": {"entity": "forum.thread"}, "inputs": {}},
            ]),
        },
        {"user_id": actor, "user_role": "ADMIN"},
    )


@pytest.fixture()
def two_version_scenario():
    from src.domains.orchestration.locks import lock_manager

    code = "OPC_M11_ROLLBACK_DEMO"
    # every catalog mutation (even create) runs under the exclusive edit lock
    lock_manager.acquire("scenario", code, "usr_admin_a")
    catalog_service.create_scenario(
        {"code": code, "display_name": "回滚演示", "description": "M1-1"},
        {"user_id": "usr_admin_a", "user_role": "ADMIN"},
    )
    _save_version(code, "v1.0.0", "usr_admin_a")
    catalog_service.publish_scenario(
        {"code": code, "version": "v1.0.0"}, {"user_id": "usr_admin_a", "user_role": "ADMIN"}
    )
    _save_version(code, "v1.0.1", "usr_admin_a")
    catalog_service.publish_scenario(
        {"code": code, "version": "v1.0.1"}, {"user_id": "usr_admin_a", "user_role": "ADMIN"}
    )
    yield code
    catalog_service._scenarios.pop(code, None)
    for key in [k for k in orchestration_service._dag_configs if k[0] == code]:
        orchestration_service._dag_configs.pop(key, None)


def test_rollback_reactivates_prior_version(two_version_scenario):
    code = two_version_scenario
    assert orchestration_service.get_dag_config(code, "v1.0.1").status == "ACTIVE"

    result = catalog_service.rollback_scenario(
        {"code": code, "version": "v1.0.0"}, {"user_id": "usr_admin_a", "user_role": "ADMIN"}
    )
    assert result["current_version"] == "v1.0.0"
    assert result["deployed_dag"]["version"] == "v1.0.0"
    # DAG config: v1 ACTIVE again, v1.0.1 superseded
    assert orchestration_service.get_dag_config(code, "v1.0.0").status == "ACTIVE"
    assert orchestration_service.get_dag_config(code, "v1.0.1").status == "SUPERSEDED"
    # version states follow
    asset = catalog_service._scenarios[code]
    statuses = {v.version: v.status.value for v in asset.versions}
    assert statuses == {"v1.0.0": "PUBLISHED", "v1.0.1": "SUPERSEDED"}


def test_rollback_rejects_draft_version(two_version_scenario):
    code = two_version_scenario
    _save_version(code, "v1.0.2-draft", "usr_admin_a")
    with pytest.raises(ValueError, match="草稿"):
        catalog_service.rollback_scenario(
            {"code": code, "version": "v1.0.2-draft"},
            {"user_id": "usr_admin_a", "user_role": "ADMIN"},
        )


def test_second_person_approval_flow(two_version_scenario):
    code = two_version_scenario
    _save_version(code, "v1.0.2", "usr_admin_a")  # draft awaiting publish
    approval = catalog_service.request_release_approval(
        {"asset_kind": "scenario", "code": code, "version": "v1.0.2", "note": "新版本发布"},
        {"user_id": "usr_admin_a", "user_role": "ADMIN"},
    )
    assert approval["status"] == "PENDING"

    # requester cannot self-approve
    with pytest.raises(ValueError, match="第二人"):
        catalog_service.approve_release(
            {"approval_id": approval["id"]}, {"user_id": "usr_admin_a", "user_role": "ADMIN"}
        )

    result = catalog_service.approve_release(
        {"approval_id": approval["id"]}, {"user_id": "usr_admin_b", "user_role": "ADMIN"}
    )
    assert result["approval"]["status"] == "APPROVED"
    assert result["approval"]["approver"] == "usr_admin_b"
    # the approved draft publishes and supersedes v1.0.1
    assert orchestration_service.get_dag_config(code, "v1.0.2").status == "ACTIVE"

    listing = catalog_service.list_release_approvals({"status": "APPROVED"}, {})
    assert any(a["id"] == approval["id"] for a in listing["approvals"])


def test_reject_release_by_requester_cancels(two_version_scenario):
    code = two_version_scenario
    approval = catalog_service.request_release_approval(
        {"asset_kind": "scenario", "code": code, "version": "v1.0.0"},
        {"user_id": "usr_admin_a", "user_role": "ADMIN"},
    )
    rejected = catalog_service.reject_release(
        {"approval_id": approval["id"], "note": "撤回"},
        {"user_id": "usr_admin_a", "user_role": "ADMIN"},
    )
    assert rejected["status"] == "REJECTED"
    with pytest.raises(ValueError, match="状态为 REJECTED"):
        catalog_service.approve_release(
            {"approval_id": approval["id"]}, {"user_id": "usr_admin_b", "user_role": "ADMIN"}
        )


def test_duplicate_pending_request_refused(two_version_scenario):
    code = two_version_scenario
    catalog_service.request_release_approval(
        {"asset_kind": "scenario", "code": code, "version": "v1.0.0"},
        {"user_id": "usr_admin_a", "user_role": "ADMIN"},
    )
    with pytest.raises(ValueError, match="待审批"):
        catalog_service.request_release_approval(
            {"asset_kind": "scenario", "code": code, "version": "v1.0.0"},
            {"user_id": "usr_admin_b", "user_role": "ADMIN"},
        )
