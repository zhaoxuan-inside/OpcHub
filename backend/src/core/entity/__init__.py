"""Generic entity runtime: declarative specs + a domain-free store."""
from src.core.entity.spec import EntityAdapter, EntitySpec
from src.core.entity.store import EntityStore, SnapshotAdapter, entity_store

__all__ = [
    "EntityAdapter",
    "EntitySpec",
    "EntityStore",
    "SnapshotAdapter",
    "entity_store",
]
