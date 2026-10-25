"""Tests for the standard document catalog (标准文书库) and its interactions.

The workbench lists documents only — subgraphs are workflow structures, not
fillable documents. Provenance (author, publisher, official badge, publish date)
and the interaction counters (like / favourite / real usage) come from the
persisted catalog, never from frontend placeholders.
"""
import pytest

from src.domains.sop.models import SOPNode
from src.domains.sop.service import sop_service


def test_catalog_contains_documents_only():
    """Subgraphs must never appear in the standard document catalog."""
    catalog = sop_service.list_document_cards(user_id="usr_catalog_test")
    assert catalog.total > 0
    assert catalog.items, "catalog must not be empty"
    for item in catalog.items:
        assert item.id.startswith("tpl_"), f"{item.id} is not a document node"
    # Every catalog entry resolves to a document-kind node in the graph.
    for item in catalog.items:
        assert sop_service.get_node(item.id).kind == "document"


def test_catalog_exposes_provenance_fields():
    """Each seeded document card carries author, publisher, badge and publish date.

    The provenance contract is asserted against the seeded catalog. Templates
    published at runtime (e.g. by an admin) are admin-authored and are not
    required to ship curated provenance; the UI falls back to platform defaults.
    """
    from src.domains.sop.service import DEFAULT_SOP_SEEDS

    seeded_ids = {raw["id"] for raw in (DEFAULT_SOP_SEEDS.get("nodes") or [])}
    catalog = sop_service.list_document_cards(user_id="usr_catalog_test")
    seeded_items = [i for i in catalog.items if i.id in seeded_ids]
    assert seeded_items, "expected seeded documents in the catalog"

    for item in seeded_items:
        assert item.name, f"{item.id} missing name"
        assert item.summary, f"{item.id} missing summary"
        assert item.author_name, f"{item.id} missing author_name"
        assert item.publisher_org, f"{item.id} missing publisher_org"
        assert item.published_at, f"{item.id} missing published_at"
        assert item.field_count >= 0
        assert item.like_count >= 0
        assert item.favorite_count >= 0
        assert item.usage_count >= 0


def test_catalog_official_badge_is_reflected():
    """The official certification badge is data-driven, not hardcoded per card."""
    catalog = sop_service.list_document_cards(user_id="usr_catalog_test")
    official = [i for i in catalog.items if i.is_official]
    non_official = [i for i in catalog.items if not i.is_official]
    assert official, "expected at least one officially certified document"
    assert non_official, "expected at least one non-certified document"
    for item in official:
        assert sop_service.get_node(item.id).is_official is True


def test_catalog_filters_by_category():
    catalog = sop_service.list_document_cards(user_id="usr_catalog_test", category="IP")
    assert catalog.items
    for item in catalog.items:
        assert item.category == "IP"


def test_catalog_usage_count_combines_baseline_and_live_instances():
    """The real-usage counter is the seeded baseline plus live instances.

    Generated documents are no longer persisted by the UI (the maker downloads a
    PDF instead), so the platform-wide figure comes from the seed baseline; any
    instance still stored on this deployment adds to it.
    """
    usage = sop_service._usage_counts()
    catalog = sop_service.list_document_cards(user_id="usr_catalog_test")
    for item in catalog.items:
        baseline = sop_service.get_node(item.id).usage_count
        assert item.usage_count == baseline + usage.get(item.id, 0)


def test_document_like_via_unified_interactions():
    """喜欢/收藏统一走 content interactions；计数经 _sync_domain 镜像回节点。"""
    from src.domains.interactions.service import content_interaction_service

    node_id = "tpl_invoice_quota"
    baseline_like = sop_service.get_node(node_id).like_count
    baseline_fav = sop_service.get_node(node_id).favorite_count
    try:
        first = content_interaction_service.toggle("usr_like_test", "SOP_DOCUMENT", node_id, "LOVE")
        assert first.active is True
        assert first.viewer.loved is True
        # 统一 LOVE 计数镜像到 SOP 节点的 like_count 字段
        assert sop_service.get_node(node_id).like_count == first.love_count
        assert first.love_count == baseline_like + 1

        second = content_interaction_service.toggle("usr_like_test", "SOP_DOCUMENT", node_id, "LOVE")
        assert second.active is False
        assert sop_service.get_node(node_id).like_count == baseline_like

        fav = content_interaction_service.toggle("usr_like_test", "SOP_DOCUMENT", node_id, "FAVORITE")
        assert fav.active is True
        assert fav.favorite_count == baseline_fav + 1
    finally:
        content_interaction_service.clear()


def test_catalog_counts_reflect_unified_sync():
    """目录卡片的 like_count / favorite_count 来自节点实体（由统一互动镜像）。"""
    from src.domains.interactions.service import content_interaction_service

    node_id = "tpl_soft_copyright_application"
    baseline_like = sop_service.get_node(node_id).like_count
    try:
        content_interaction_service.toggle("usr_mark_test", "SOP_DOCUMENT", node_id, "LOVE")
        catalog = sop_service.list_document_cards()
        target = next(i for i in catalog.items if i.id == node_id)
        assert target.like_count == baseline_like + 1
    finally:
        content_interaction_service.clear()


def test_hydrate_nodes_rebuilds_documents():
    """A persisted node snapshot rebuilds the catalog entry after a restart."""
    original = sop_service.get_node("tpl_bank_account_opening")
    payload = original.model_dump()
    sop_service._nodes.pop("tpl_bank_account_opening", None)
    try:
        count = sop_service.hydrate_nodes([payload])
        assert count == 1
        restored = sop_service.get_node("tpl_bank_account_opening")
        assert restored.name == original.name
        assert restored.publisher_org == original.publisher_org
    finally:
        sop_service._nodes["tpl_bank_account_opening"] = original
        sop_service._register_template_from_node(original)
