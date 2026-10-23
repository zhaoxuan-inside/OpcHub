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


def test_like_toggle_is_idempotent_per_user():
    node_id = "tpl_invoice_quota"
    before = sop_service.get_node(node_id).like_count

    first = sop_service.toggle_like("usr_like_test", node_id)
    assert first.liked is True
    assert first.like_count == before + 1

    second = sop_service.toggle_like("usr_like_test", node_id)
    assert second.liked is False
    assert second.like_count == before


def test_like_is_per_user():
    node_id = "tpl_invoice_quota"
    before = sop_service.get_node(node_id).like_count
    try:
        sop_service.toggle_like("usr_like_a", node_id)
        sop_service.toggle_like("usr_like_b", node_id)
        assert sop_service.get_node(node_id).like_count == before + 2
    finally:
        sop_service.toggle_like("usr_like_a", node_id)
        sop_service.toggle_like("usr_like_b", node_id)


def test_favorite_toggle_is_independent_of_like():
    node_id = "tpl_tax_registration"
    try:
        liked = sop_service.toggle_like("usr_fav_test", node_id)
        fav = sop_service.toggle_favorite("usr_fav_test", node_id)
        assert liked.liked is True and liked.favorited is False
        assert fav.liked is True and fav.favorited is True
    finally:
        sop_service.toggle_like("usr_fav_test", node_id)
        sop_service.toggle_favorite("usr_fav_test", node_id)


def test_interaction_rejects_subgraph():
    """Only standard documents can be liked or favourited."""
    with pytest.raises(ValueError):
        sop_service.toggle_like("usr_x", "sub_cross_border")
    with pytest.raises(ValueError):
        sop_service.toggle_favorite("usr_x", "sub_cross_border")


def test_catalog_marks_caller_interactions():
    node_id = "tpl_soft_copyright_application"
    try:
        sop_service.toggle_like("usr_mark_test", node_id)
        sop_service.toggle_favorite("usr_mark_test", node_id)
        catalog = sop_service.list_document_cards(user_id="usr_mark_test")
        target = next(i for i in catalog.items if i.id == node_id)
        assert target.liked is True
        assert target.favorited is True

        # Another user sees the counts but not the flags.
        other = sop_service.list_document_cards(user_id="usr_other_test")
        other_target = next(i for i in other.items if i.id == node_id)
        assert other_target.liked is False
        assert other_target.favorited is False
    finally:
        sop_service.toggle_like("usr_mark_test", node_id)
        sop_service.toggle_favorite("usr_mark_test", node_id)


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
