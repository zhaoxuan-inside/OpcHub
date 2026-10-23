"""Tests for platform flow templates (平台流程模板).

A flow template is the curated, platform-authored counterpart of a user flow:
an ordered set of node references that completes one business outcome. These
power the "流程向导" workspace, which mirrors the standard-document workbench.
"""
import pytest

from src.domains.sop.models import SOPFlowTemplate
from src.domains.sop.service import sop_service


def test_flow_templates_are_seeded():
    templates = sop_service._flow_templates
    assert templates, "flow template seeds must load"
    for flow in templates.values():
        assert flow.node_refs, f"flow {flow.id} has no steps"
        assert flow.outcome, f"flow {flow.id} has no outcome"
        assert flow.summary, f"flow {flow.id} has no summary"


def test_flow_template_catalog_lists_every_template():
    catalog = sop_service.list_flow_template_cards(user_id="usr_flow_test")
    assert catalog.total == len(sop_service._flow_templates)
    for item in catalog.items:
        assert item.step_count > 0
        assert item.doc_count > 0
        assert item.name and item.summary
        assert item.author_name and item.publisher_org


def test_flow_template_catalog_filters_by_category():
    catalog = sop_service.list_flow_template_cards(user_id="usr_flow_test", category="IP")
    assert catalog.items
    for item in catalog.items:
        assert item.category == "IP"


def test_flow_template_steps_expand_subgraphs_into_documents():
    """A flow step pointing at a subgraph resolves to that subgraph's documents."""
    detail = sop_service.get_flow_template_detail("flow_hnte_certification")
    assert not detail.missing_nodes
    assert len(detail.steps) == 3
    for step in detail.steps:
        assert step.kind == "document"
        assert step.required_fields, f"step {step.name} exposes no fillable fields"
    # The order follows the template's declared sequence.
    assert detail.steps[0].name == "计算机软件著作权登记申请表"
    assert detail.steps[-1].name == "高新技术企业认定申报书"


def test_flow_template_steps_are_ordered():
    detail = sop_service.get_flow_template_detail("flow_entity_establishment")
    orders = [s.order for s in detail.steps]
    assert orders == list(range(1, len(orders) + 1))


def test_flow_template_step_carries_the_note():
    detail = sop_service.get_flow_template_detail("flow_hnte_certification")
    assert detail.steps[0].note, "each step should explain what it achieves"


def test_flow_like_toggle_is_idempotent_per_user():
    flow_id = "flow_soft_copyright_only"
    before = sop_service.get_flow_template(flow_id).like_count
    try:
        first = sop_service.toggle_flow_like("usr_like_test", flow_id)
        assert first.liked is True
        assert first.like_count == before + 1

        second = sop_service.toggle_flow_like("usr_like_test", flow_id)
        assert second.liked is False
        assert second.like_count == before
    finally:
        if (("usr_like_test", flow_id)) in sop_service._flow_likes:
            sop_service.toggle_flow_like("usr_like_test", flow_id)


def test_flow_favorite_is_independent_of_like():
    flow_id = "flow_cross_border_settlement"
    try:
        liked = sop_service.toggle_flow_like("usr_fav_test", flow_id)
        fav = sop_service.toggle_flow_favorite("usr_fav_test", flow_id)
        assert liked.liked is True and liked.favorited is False
        assert fav.liked is True and fav.favorited is True
    finally:
        if (("usr_fav_test", flow_id)) in sop_service._flow_likes:
            sop_service.toggle_flow_like("usr_fav_test", flow_id)
        if (("usr_fav_test", flow_id)) in sop_service._flow_favorites:
            sop_service.toggle_flow_favorite("usr_fav_test", flow_id)


def test_flow_catalog_marks_caller_interactions():
    flow_id = "flow_full_lifecycle_compliance"
    try:
        sop_service.toggle_flow_like("usr_mark_test", flow_id)
        sop_service.toggle_flow_favorite("usr_mark_test", flow_id)
        catalog = sop_service.list_flow_template_cards(user_id="usr_mark_test")
        target = next(i for i in catalog.items if i.id == flow_id)
        assert target.liked is True
        assert target.favorited is True

        other = sop_service.list_flow_template_cards(user_id="usr_other_test")
        other_target = next(i for i in other.items if i.id == flow_id)
        assert other_target.liked is False
        assert other_target.favorited is False
    finally:
        if (("usr_mark_test", flow_id)) in sop_service._flow_likes:
            sop_service.toggle_flow_like("usr_mark_test", flow_id)
        if (("usr_mark_test", flow_id)) in sop_service._flow_favorites:
            sop_service.toggle_flow_favorite("usr_mark_test", flow_id)


def test_unknown_flow_template_raises_key_error():
    with pytest.raises(KeyError):
        sop_service.get_flow_template("flow_not_real")
    with pytest.raises(KeyError):
        sop_service.get_flow_template_detail("flow_not_real")


def test_flow_template_hydrate_rebuilds_catalog():
    original = sop_service.get_flow_template("flow_soft_copyright_only")
    payload = original.model_dump()
    sop_service._flow_templates.pop(original.id, None)
    try:
        assert sop_service.hydrate_flow_templates([payload]) == 1
        restored = sop_service.get_flow_template(original.id)
        assert restored.name == original.name
        assert len(restored.node_refs) == len(original.node_refs)
    finally:
        sop_service._flow_templates[original.id] = original
