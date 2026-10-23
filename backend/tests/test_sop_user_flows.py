"""Tests for user-authored SOP flows: creation, resolution, editing and deletion.

A flow is a maker-owned document set. It references nodes (documents or
subgraphs) and is resolved into an ordered document list, exactly like the
goal reverse lookup does.
"""
import pytest

from src.domains.sop.models import (
    SOP_FLOW_STATUS_ACTIVE,
    SOPFlowCreate,
    SOPFlowNodeRef,
)
from src.domains.sop.service import sop_service


def _make_flow(name="单元测试流程", node_refs=None, owner="usr_test_flow", goal_id=None):
    return sop_service.create_flow(SOPFlowCreate(
        name=name,
        description="流程测试",
        owner_id=owner,
        goal_id=goal_id,
        node_refs=node_refs or [
            SOPFlowNodeRef(node_id="tpl_oneperson_company_reg"),
            SOPFlowNodeRef(node_id="tpl_company_articles"),
        ],
    ))


def test_create_flow_persists_and_is_listed():
    flow = _make_flow(name="列出测试流程", owner="usr_list_owner")
    try:
        assert flow.id.startswith("flow_")
        assert flow.name == "列出测试流程"
        assert flow.status == SOP_FLOW_STATUS_ACTIVE
        listed = sop_service.list_flows("usr_list_owner")
        assert any(f.id == flow.id for f in listed)
    finally:
        sop_service.delete_flow(flow.id)


def test_flow_is_filtered_by_owner():
    mine = _make_flow(name="归属测试A", owner="usr_owner_a")
    theirs = _make_flow(name="归属测试B", owner="usr_owner_b")
    try:
        a_ids = {f.id for f in sop_service.list_flows("usr_owner_a")}
        b_ids = {f.id for f in sop_service.list_flows("usr_owner_b")}
        assert mine.id in a_ids and mine.id not in b_ids
        assert theirs.id in b_ids and theirs.id not in a_ids
    finally:
        sop_service.delete_flow(mine.id)
        sop_service.delete_flow(theirs.id)


def test_resolve_flow_expands_subgraph_into_documents():
    """A flow referencing a subgraph resolves to that subgraph's documents."""
    flow = _make_flow(name="子图解析测试", node_refs=[
        SOPFlowNodeRef(node_id="sub_cross_border"),
    ])
    try:
        resolved = sop_service.resolve_flow(flow.id)
        assert not resolved.missing_nodes
        assert len(resolved.items) == 2, "cross-border subgraph has two documents"
        for item in resolved.items:
            assert item.kind == "document"
            assert item.parent_id == "sub_cross_border"
    finally:
        sop_service.delete_flow(flow.id)


def test_resolve_flow_orders_by_dependency():
    """The dependency edges determine the execution order inside a flow."""
    flow = _make_flow(name="顺序测试", node_refs=[
        SOPFlowNodeRef(node_id="tpl_tax_registration"),
        SOPFlowNodeRef(node_id="tpl_oneperson_company_reg"),
        SOPFlowNodeRef(node_id="tpl_company_articles"),
    ])
    try:
        resolved = sop_service.resolve_flow(flow.id)
        order = {item.node_id: item.order for item in resolved.items}
        assert order["tpl_oneperson_company_reg"] < order["tpl_company_articles"]
        assert order["tpl_company_articles"] < order["tpl_tax_registration"]
    finally:
        sop_service.delete_flow(flow.id)


def test_resolve_flow_reports_unknown_node():
    flow = _make_flow(name="缺失节点测试", node_refs=[
        SOPFlowNodeRef(node_id="tpl_does_not_exist"),
    ])
    try:
        resolved = sop_service.resolve_flow(flow.id)
        assert "tpl_does_not_exist" in resolved.missing_nodes
    finally:
        sop_service.delete_flow(flow.id)


def test_resolve_flow_exposes_edges_for_the_diagram():
    flow = _make_flow(name="连线测试", node_refs=[
        SOPFlowNodeRef(node_id="tpl_oneperson_company_reg"),
        SOPFlowNodeRef(node_id="tpl_company_articles"),
    ])
    try:
        resolved = sop_service.resolve_flow(flow.id)
        pairs = {(e.from_node, e.to_node) for e in resolved.edges}
        assert ("tpl_oneperson_company_reg", "tpl_company_articles") in pairs
    finally:
        sop_service.delete_flow(flow.id)


def test_update_flow_replaces_content():
    flow = _make_flow(name="更新前名称")
    try:
        updated = sop_service.update_flow(flow.id, SOPFlowCreate(
            name="更新后名称",
            description="新的描述",
            node_refs=[SOPFlowNodeRef(node_id="tpl_soft_copyright_application")],
        ))
        assert updated.id == flow.id
        assert updated.name == "更新后名称"
        assert updated.description == "新的描述"
        assert len(updated.node_refs) == 1
        resolved = sop_service.resolve_flow(flow.id)
        assert [i.node_id for i in resolved.items] == ["tpl_soft_copyright_application"]
    finally:
        sop_service.delete_flow(flow.id)


def test_delete_flow_removes_it():
    flow = _make_flow(name="待删除流程")
    assert sop_service.delete_flow(flow.id) is True
    assert all(f.id != flow.id for f in sop_service.list_flows())
    assert sop_service.delete_flow(flow.id) is False


def test_unknown_flow_raises_key_error():
    with pytest.raises(KeyError):
        sop_service.get_flow("flow_not_real")
    with pytest.raises(KeyError):
        sop_service.resolve_flow("flow_not_real")


def test_flow_required_flag_is_preserved():
    flow = _make_flow(name="必办标记测试", node_refs=[
        SOPFlowNodeRef(node_id="tpl_oneperson_company_reg", required=True),
        SOPFlowNodeRef(node_id="tpl_soft_copyright_application", required=False),
    ])
    try:
        resolved = sop_service.resolve_flow(flow.id)
        flags = {i.node_id: i.required for i in resolved.items}
        assert flags["tpl_oneperson_company_reg"] is True
        assert flags["tpl_soft_copyright_application"] is False
    finally:
        sop_service.delete_flow(flow.id)
