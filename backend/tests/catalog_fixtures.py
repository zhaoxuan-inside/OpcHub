"""Test-only catalog fixtures.

Production no longer ships seed catalogs; these files preserve representative
samples so domain behaviour (pagination, graph resolution, RAG, publish flows)
can be exercised without a live PostgreSQL instance.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "catalog"


def load_catalog(name: str) -> Dict[str, Any]:
    with open(FIXTURE_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_products(service: Any, data: Dict[str, Any] | None = None) -> int:
    from src.domains.products.models import ProductResponse

    rows = data if data is not None else load_catalog("products.json")
    for pid, payload in rows.items():
        service._products[pid] = ProductResponse(**payload)
    service.invalidate_cache()
    return len(rows)


def seed_policies(service: Any, data: Dict[str, Any] | None = None) -> int:
    from src.domains.policies.models import PolicyResponse

    rows = data if data is not None else load_catalog("policies.json")
    for pid, payload in rows.items():
        item = dict(payload)
        item.setdefault("is_official", True)
        item.setdefault("author_name", "官方发布")
        service._policies[pid] = PolicyResponse(**item)
    return len(rows)


def seed_demands(service: Any, data: Dict[str, Any] | None = None) -> int:
    from src.domains.demands.models import DemandResponse

    rows = data if data is not None else load_catalog("demands.json")
    for did, payload in rows.items():
        service._demands[did] = DemandResponse(**payload)
        service._bids.setdefault(did, [])
    service.invalidate_cache()
    return len(rows)


def seed_perks(service: Any, data: Dict[str, Any] | None = None) -> int:
    from src.domains.perks.models import PerkResponse

    rows = data if data is not None else load_catalog("perks.json")
    for pid, payload in rows.items():
        item = dict(payload)
        item.setdefault("is_official", True)
        item.setdefault("author_name", "官方发布")
        service._perks[pid] = PerkResponse(**item)
    return len(rows)


def seed_compliance(service: Any, data: Dict[str, Any] | None = None) -> int:
    from src.domains.compliance.models import (
        AuditCheckItem,
        ComplianceCase,
        ComplianceLaw,
    )

    rows = data if data is not None else load_catalog("compliance.json")
    for payload in rows.get("laws", []):
        item = dict(payload)
        item.setdefault("is_official", True)
        item.setdefault("author_name", "官方发布")
        law = ComplianceLaw(**item)
        if not any(existing.id == law.id for existing in service._laws):
            service._laws.append(law)
    for payload in rows.get("cases", []):
        item = dict(payload)
        item.setdefault("is_official", True)
        item.setdefault("author_name", "官方发布")
        case = ComplianceCase(**item)
        if not any(existing.id == case.id for existing in service._cases):
            service._cases.append(case)
    for payload in rows.get("checkpoints", []):
        chk = AuditCheckItem(**payload)
        if not any(existing.id == chk.id for existing in service._checkpoints):
            service._checkpoints.append(chk)
    return (
        len(service._laws) + len(service._cases) + len(service._checkpoints)
    )


def seed_sop(
    service: Any,
    graph_data: Dict[str, Any] | None = None,
    flow_data: Dict[str, Any] | None = None,
) -> int:
    from src.domains.sop.models import (
        SOPEdge,
        SOPFlowTemplate,
        SOPGoal,
        SOPNode,
        SOPStage,
        SOP_NODE_DOCUMENT,
    )

    graph = graph_data if graph_data is not None else load_catalog("sop.json")
    flows = flow_data if flow_data is not None else load_catalog("sop_flows.json")

    stage_codes = {stage.code for stage in service._stages}
    for raw in graph.get("stages") or []:
        stage = SOPStage(**raw)
        if stage.code not in stage_codes:
            service._stages.append(stage)
            stage_codes.add(stage.code)
    for raw in graph.get("nodes") or []:
        node = SOPNode(**raw)
        service._nodes[node.id] = node
        if node.kind == SOP_NODE_DOCUMENT:
            service._register_template_from_node(node)
    edge_keys = {(edge.from_node, edge.to_node) for edge in service._edges}
    for raw in graph.get("edges") or []:
        edge = SOPEdge(**raw)
        if (edge.from_node, edge.to_node) not in edge_keys:
            service._edges.append(edge)
            edge_keys.add((edge.from_node, edge.to_node))
    for raw in graph.get("goals") or []:
        goal = SOPGoal(**raw)
        service._goals[goal.id] = goal
    for raw in flows.values():
        flow = SOPFlowTemplate(**raw)
        service._flow_templates[flow.id] = flow
    return (
        len(service._nodes)
        + len(service._edges)
        + len(service._goals)
        + len(service._flow_templates)
    )
