"""Tests for the SOP workflow graph: nodes, subgraphs, dependency edges and goal reverse lookup.

The graph is the single source of truth behind the three SOP workspace views:
node workbench, flow guide and goal reverse lookup. These tests lock the
structural contracts that the frontend depends on.
"""
import pytest

from src.domains.sop.models import (
    SOP_EDGE_PREREQUISITE,
    SOP_NODE_DOCUMENT,
    SOP_NODE_SUBGRAPH,
)
from src.domains.sop.service import sop_service


def _seeded_graph():
    return sop_service.get_graph()


def test_graph_exposes_stages_nodes_edges_and_goals():
    graph = _seeded_graph()
    assert len(graph.stages) == 4
    assert graph.stages[0].code == "STAGE_TAX_ENTITY"
    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0
    assert len(graph.goals) > 0


def test_every_edge_references_existing_nodes():
    graph = _seeded_graph()
    node_ids = {n.id for n in graph.nodes}
    for edge in graph.edges:
        assert edge.from_node in node_ids, f"edge source {edge.from_node} missing"
        assert edge.to_node in node_ids, f"edge target {edge.to_node} missing"


def test_every_goal_references_existing_nodes():
    graph = _seeded_graph()
    node_ids = {n.id for n in graph.nodes}
    for goal in graph.goals:
        for node_id in goal.required_nodes + goal.recommended_nodes:
            assert node_id in node_ids, f"goal {goal.id} references unknown node {node_id}"


def test_subgraph_children_all_exist():
    graph = _seeded_graph()
    node_ids = {n.id for n in graph.nodes}
    for node in graph.nodes:
        if node.kind == SOP_NODE_SUBGRAPH:
            assert node.children, f"subgraph {node.id} has no children"
            for child in node.children:
                assert child in node_ids, f"subgraph {node.id} child {child} missing"


def test_seeded_document_nodes_carry_fillable_fields_with_guidance():
    """Every seeded document node must expose fields a maker can actually fill.

    The guidance contract (help / example / pitfalls) is asserted against the
    *seeded* catalog only. Runtime-published templates are admin-authored and are
    not required to ship maker-facing guidance.
    """
    from src.domains.sop.service import DEFAULT_SOP_SEEDS

    seeded_ids = {raw["id"] for raw in (DEFAULT_SOP_SEEDS.get("nodes") or [])}
    assert seeded_ids, "seed file must define nodes"

    graph = _seeded_graph()
    documents = [n for n in graph.nodes if n.kind == SOP_NODE_DOCUMENT and n.id in seeded_ids]
    assert documents, "graph must contain seeded document nodes"
    for node in documents:
        assert node.required_fields, f"document {node.id} has no fields"
        assert node.template_content, f"document {node.id} has no template"
        for field in node.required_fields:
            assert field.key, f"field in {node.id} missing key"
            assert field.label, f"field {field.key} missing label"
            # Plain-language guidance is what makes the form usable by a first-timer.
            assert field.help, f"field {field.key} in {node.id} missing help text"
            assert field.example, f"field {field.key} in {node.id} missing example"
            # Pitfalls are optional per field (a date has nothing to get wrong),
            # but every field must at least declare the key so the UI can render it.
            assert isinstance(field.pitfalls, list)


def test_subgraph_expansion_returns_leaf_documents():
    """A subgraph flattens into the documents it is composed of."""
    graph = _seeded_graph()
    subgraphs = [n for n in graph.nodes if n.kind == SOP_NODE_SUBGRAPH]
    assert subgraphs, "graph must contain at least one subgraph"
    for subgraph in subgraphs:
        expanded = sop_service.expand_subgraph(subgraph.id)
        assert expanded, f"subgraph {subgraph.id} expanded to nothing"
        assert all(n.kind == SOP_NODE_DOCUMENT for n in expanded)
        assert all(n.id in subgraph.children for n in expanded)


def test_nested_subgraph_expansion_is_recursive():
    """A subgraph may itself contain subgraphs; expansion must recurse."""
    graph = _seeded_graph()
    node_ids = {n.id for n in graph.nodes}
    # Build a synthetic nested subgraph to prove recursion without extra seed data.
    parent = next(n for n in graph.nodes if n.kind == SOP_NODE_SUBGRAPH)
    nested_id = "tpl_test_nested_parent"
    sop_service._nodes[nested_id] = type(parent)(
        id=nested_id,
        kind=SOP_NODE_SUBGRAPH,
        code="TEST_NESTED",
        name="测试嵌套子图",
        stage=1,
        category="TAX",
        children=[parent.id],
    )
    try:
        expanded = sop_service.expand_subgraph(nested_id)
        assert expanded, "nested subgraph expanded to nothing"
        assert all(n.kind == SOP_NODE_DOCUMENT for n in expanded)
        assert all(n.id in node_ids for n in expanded)
    finally:
        sop_service._nodes.pop(nested_id, None)


def test_subgraph_expansion_is_cycle_safe():
    """A malformed cyclic subgraph must not hang the expansion."""
    a_id, b_id = "tpl_test_cycle_a", "tpl_test_cycle_b"
    template = next(n for n in _seeded_graph().nodes if n.kind == SOP_NODE_DOCUMENT)
    sop_service._nodes[a_id] = type(template)(
        id=a_id, kind=SOP_NODE_SUBGRAPH, code="CYC_A", name="环 A", stage=1,
        category="TAX", children=[b_id],
    )
    sop_service._nodes[b_id] = type(template)(
        id=b_id, kind=SOP_NODE_SUBGRAPH, code="CYC_B", name="环 B", stage=1,
        category="TAX", children=[a_id],
    )
    try:
        expanded = sop_service.expand_subgraph(a_id)
        assert isinstance(expanded, list)
    finally:
        sop_service._nodes.pop(a_id, None)
        sop_service._nodes.pop(b_id, None)


def test_goal_plan_expands_subgraphs_into_required_documents():
    """Reverse lookup must expand a subgraph goal into its constituent documents."""
    graph = _seeded_graph()
    goal = next(g for g in graph.goals if any(
        node_id in {n.id for n in graph.nodes if n.kind == SOP_NODE_SUBGRAPH}
        for node_id in g.required_nodes
    ))
    plan = sop_service.resolve_goal_plan(goal.id)
    assert plan.goal.id == goal.id
    assert plan.items, f"goal {goal.id} produced an empty plan"
    assert not plan.missing_nodes, f"goal {goal.id} has missing nodes: {plan.missing_nodes}"
    for item in plan.items:
        assert item.kind == SOP_NODE_DOCUMENT
        assert item.name and item.node_id


def test_goal_plan_orders_prerequisites_first():
    """Dependency edges must place prerequisites ahead of their dependents.

    Goals reference subgraphs while edges reference leaf documents, so the
    comparison is made against the *expanded* plan items.
    """
    graph = _seeded_graph()
    prerequisite_edges = [
        e for e in graph.edges if e.relation == SOP_EDGE_PREREQUISITE
    ]
    assert prerequisite_edges, "graph must define prerequisite edges"

    checked = 0
    for goal in graph.goals:
        plan = sop_service.resolve_goal_plan(goal.id)
        order = {item.node_id: item.order for item in plan.items}
        for edge in prerequisite_edges:
            if edge.from_node in order and edge.to_node in order:
                assert order[edge.from_node] < order[edge.to_node], (
                    f"goal {goal.id}: {edge.from_node} must precede {edge.to_node}"
                )
                checked += 1
    assert checked, "no goal plan contained a comparable prerequisite pair"


def test_goal_plan_marks_required_and_recommended_distinctly():
    graph = _seeded_graph()
    goal = next(g for g in graph.goals if g.recommended_nodes)
    plan = sop_service.resolve_goal_plan(goal.id)
    required = {i.node_id for i in plan.items if i.required}
    recommended = {i.node_id for i in plan.items if not i.required}
    assert required, "goal with recommended_nodes must still have required items"
    assert recommended, "recommended items must be flagged as optional"


def test_goal_plan_reports_unknown_node():
    graph = _seeded_graph()
    goal = graph.goals[0]
    original = list(goal.required_nodes)
    goal.required_nodes = original + ["tpl_definitely_missing_node"]
    try:
        plan = sop_service.resolve_goal_plan(goal.id)
        assert "tpl_definitely_missing_node" in plan.missing_nodes
    finally:
        goal.required_nodes = original


def test_node_context_includes_prerequisites_with_rationale():
    graph = _seeded_graph()
    edge = next(e for e in graph.edges if e.rationale)
    ctx = sop_service.get_node_context(edge.to_node)
    assert ctx["node"].id == edge.to_node
    assert ctx["prerequisites"], "prerequisite context must not be empty"
    prereq = ctx["prerequisites"][0]
    assert prereq["rationale"], "prerequisite must explain why the order matters"


def test_node_context_for_subgraph_lists_children():
    graph = _seeded_graph()
    subgraph = next(n for n in graph.nodes if n.kind == SOP_NODE_SUBGRAPH)
    ctx = sop_service.get_node_context(subgraph.id)
    assert len(ctx["children"]) == len(subgraph.children)
    for child in ctx["children"]:
        assert child.id in subgraph.children


def test_unknown_node_raises_key_error():
    with pytest.raises(KeyError):
        sop_service.get_node_context("tpl_not_a_real_node")
    with pytest.raises(KeyError):
        sop_service.resolve_goal_plan("goal_not_real")


def test_document_node_is_also_registered_as_template():
    """Document nodes double as renderable templates."""
    graph = _seeded_graph()
    for node in graph.nodes:
        if node.kind != SOP_NODE_DOCUMENT:
            continue
        template = sop_service.get_template(node.id)
        assert template.name == node.name
        assert len(template.required_fields) == len(node.required_fields)


def test_runtime_published_template_joins_the_graph():
    """A template published at runtime is fillable in the workbench too."""
    from src.domains.sop.models import SOPTemplateCreate

    created = sop_service.create_template(SOPTemplateCreate(
        stage=1,
        code="RUNTIME_PUBLISHED_TEMPLATE",
        name="运行时发布的模板",
        category="TAX",
        description="运行时发布的模板应同步进入图谱，可在工作台直接填写。",
        template_content="模板正文 {name}",
        required_fields=[],
    ))
    try:
        node = sop_service.get_node(created.id)
        assert node.kind == SOP_NODE_DOCUMENT
        assert node.name == created.name
        assert node.code == created.code
    finally:
        sop_service._nodes.pop(created.id, None)
        sop_service._templates.pop(created.id, None)


def test_template_catalog_self_heals_from_graph():
    """The graph is the source of truth: a reset template catalog rebuilds itself."""
    graph = _seeded_graph()
    seeded = next(
        n for n in graph.nodes
        if n.kind == SOP_NODE_DOCUMENT and n.id.startswith("tpl_")
    )
    original = sop_service._templates.pop(seeded.id, None)
    try:
        assert seeded.id not in sop_service._templates
        # Reading through the public accessor must restore the seeded template.
        rebuilt = sop_service.get_template(seeded.id)
        assert rebuilt.name == seeded.name
        assert rebuilt.template_content == seeded.template_content
        assert len(rebuilt.required_fields) == len(seeded.required_fields)
    finally:
        if original is not None:
            sop_service._templates[seeded.id] = original
