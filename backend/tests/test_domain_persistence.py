"""Unit tests for the write-behind domain persistence layer (no live database).

The default suite runs hermetically (see ``tests/conftest.py``); these tests inject a
fake repository to exercise hydration, write-behind scheduling, deletes and the
graceful disabled path without requiring PostgreSQL.
"""
import pytest

from src.infrastructure.database import persistence as persistence_mod
from src.infrastructure.database.persistence import DomainPersistence, snapshot


class FakeRepo:
    """In-memory stand-in for ``db_repository`` recording all persistence calls."""

    def __init__(self, ready: bool = True):
        self.ready = ready
        self.store = {}
        self.upserts = []
        self.deletes = []

    async def is_ready(self):
        return self.ready

    async def load_domain_snapshots(self, domain):
        return [dict(v) for v in self.store.get(domain, {}).values()]

    async def upsert_domain_snapshot(self, domain, entity_id, payload):
        self.upserts.append((domain, entity_id, dict(payload)))
        self.store.setdefault(domain, {})[entity_id] = dict(payload)

    async def delete_domain_snapshot(self, domain, entity_id):
        self.deletes.append((domain, entity_id))
        self.store.get(domain, {}).pop(entity_id, None)


class _Model:
    def __init__(self, id, value):
        self.id = id
        self.value = value

    def model_dump(self, mode="json"):
        return {"id": self.id, "value": self.value}


def test_snapshot_serializes_models_and_mappings():
    assert snapshot(_Model("a", 1)) == {"id": "a", "value": 1}
    assert snapshot({"id": "b"}) == {"id": "b"}
    with pytest.raises(TypeError):
        snapshot(42)


@pytest.mark.asyncio
async def test_initialize_hydrates_registered_domains(monkeypatch):
    fake = FakeRepo()
    fake.store["things.items"] = {"a": {"id": "a", "v": 1}, "b": {"id": "b", "v": 2}}
    monkeypatch.setattr(persistence_mod, "db_repository", fake)

    seen = {}
    dp = DomainPersistence()
    dp.register("things.items", lambda rows: seen.update({r["id"]: r for r in rows}) or len(rows))

    counts = await dp.initialize()
    assert dp.enabled is True
    assert counts == {"things.items": 2}
    assert seen["a"] == {"id": "a", "v": 1}
    assert seen["b"] == {"id": "b", "v": 2}


@pytest.mark.asyncio
async def test_initialize_hydration_is_idempotent(monkeypatch):
    fake = FakeRepo()
    fake.store["things.items"] = {"a": {"id": "a"}}
    monkeypatch.setattr(persistence_mod, "db_repository", fake)

    target = {}
    dp = DomainPersistence()
    dp.register("things.items", lambda rows: target.update({r["id"]: r for r in rows}) or len(rows))

    await dp.initialize()
    await dp.initialize()
    assert list(target.keys()) == ["a"]


@pytest.mark.asyncio
async def test_write_behind_and_delete_flush(monkeypatch):
    fake = FakeRepo()
    monkeypatch.setattr(persistence_mod, "db_repository", fake)

    dp = DomainPersistence()
    dp.register("things.items", lambda rows: len(rows))
    await dp.initialize()

    dp.write("things.items", "a", {"id": "a", "v": 9})
    dp.write_raw("things.items", "b", {"id": "b", "v": 1})
    dp.delete("things.items", "c")
    await dp.flush()

    assert ("things.items", "a", {"id": "a", "v": 9}) in fake.upserts
    assert ("things.items", "b", {"id": "b", "v": 1}) in fake.upserts
    assert fake.deletes == [("things.items", "c")]
    assert fake.store["things.items"]["a"] == {"id": "a", "v": 9}


@pytest.mark.asyncio
async def test_disabled_layer_is_a_noop(monkeypatch):
    fake = FakeRepo(ready=False)
    monkeypatch.setattr(persistence_mod, "db_repository", fake)

    dp = DomainPersistence()
    dp.register("things.items", lambda rows: len(rows))

    counts = await dp.initialize()
    assert dp.enabled is False
    assert counts == {}

    dp.write("things.items", "a", {"id": "a"})
    dp.write_raw("things.items", "b", {"id": "b"})
    dp.delete("things.items", "a")
    await dp.flush()

    assert fake.upserts == []
    assert fake.deletes == []


def test_all_domain_services_register_their_document_families():
    """Every mutable domain service must register its persistence families."""
    # Importing the service modules performs registration at import time.
    import importlib

    for module in (
        "forum", "products", "policies", "demands",
        "perks", "sop", "moderation", "orchestration",
    ):
        importlib.import_module(f"src.domains.{module}.service")

    expected = {
        "forum.threads", "forum.comments", "forum.votes",
        "products.items", "policies.items", "demands.items", "demands.bids",
        "perks.items", "perks.claims", "sop.templates", "sop.documents",
        "moderation.items", "orchestration.dag_configs", "orchestration.layouts",
    }
    registered = set(persistence_mod.domain_persistence.domains)
    assert expected.issubset(registered), f"missing: {expected - registered}"


@pytest.mark.asyncio
async def test_hydrator_rebuilds_service_indexes(monkeypatch):
    """Registered hydrators reconstruct the exact in-memory record shape."""
    fake = FakeRepo()
    monkeypatch.setattr(persistence_mod, "db_repository", fake)

    from src.domains.products.service import product_service
    from src.domains.forum.service import forum_service

    fake.store["products.items"] = {
        "p1": {
            "id": "p1", "author_id": "u", "title": "重建产品", "tagline": "tl",
            "description": "desc", "category": "AI", "pricing_model": "FREE",
            "price_cny": 0.0, "demo_url": None, "upvote_count": 3,
            "status": "PUBLISHED", "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
    }
    fake.store["forum.votes"] = {
        "u|THREAD|t1": {
            "user_id": "u", "target_type": "THREAD", "target_id": "t1", "vote_type": "UPVOTE",
        }
    }

    product_service._products.clear()
    forum_service._votes.clear()
    await persistence_mod.domain_persistence.initialize()

    assert product_service._products["p1"].title == "重建产品"
    assert product_service._products["p1"].upvote_count == 3
    assert forum_service._votes[("u", "THREAD", "t1")] == "UPVOTE"

    product_service._products.clear()
    forum_service._votes.clear()
    # Restore the hermetic default: later tests must see persistence disabled.
    persistence_mod.domain_persistence.enabled = False
    persistence_mod.domain_persistence._tail = None
