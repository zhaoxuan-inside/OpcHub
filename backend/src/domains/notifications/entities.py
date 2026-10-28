"""Declarative entity specifications for the message box (消息箱) domain.

Data only: no business rule and no orchestration lives here. The persisted
family name ``notifications.items`` is inherited from the legacy service so
existing snapshots stay readable. ``notify.emit`` writes ``notification.item``
by default, so that name is part of the platform contract.

``notification.inbox`` is a per-user read-state sidecar (``read_map``:
``notification id -> read_at``). It exists because read state must be updated
for an arbitrary number of messages by a single declarative write; the
notification documents themselves stay the immutable delivery receipts.
"""
from src.core.entity import EntitySpec, entity_store
from src.domains.notifications.models import (
    KIND_PUBLISH_MODERATION,
    STATUS_UNREAD,
    Notification,
)

ENTITY_NOTIFICATION = "notification.item"
ENTITY_INBOX = "notification.inbox"

notification_entity = EntitySpec(
    name=ENTITY_NOTIFICATION,
    family="notifications.items",
    model=Notification,
    key_fields=("id",),
    id_prefix="msg",
    search_fields=("title", "content", "body", "scene"),
    owner_field="user_id",
    default_order="-created_at",
    defaults={
        "kind": KIND_PUBLISH_MODERATION,
        "level": "INFO",
        "content": "",
        "body": "",
        "scene": "",
        "target_type": "",
        "target_id": "",
        "verdict": "",
        "hit_words": [],
        "status": STATUS_UNREAD,
        "read_at": None,
        "link": None,
        "meta": {},
    },
)

# key_fields == ("user_id",): one read-state document per recipient.
inbox_entity = EntitySpec(
    name=ENTITY_INBOX,
    family="notifications.inbox",
    key_fields=("user_id",),
    id_prefix="inb",
    default_order="-updated_at",
    defaults={"user_id": "", "read_map": {}},
)

entity_store.register(notification_entity)
entity_store.register(inbox_entity)
