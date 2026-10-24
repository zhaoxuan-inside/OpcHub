"""RBAC + ABAC authorization model (opchub_rbac_auth_architecture.md §1.1 / §2).

- RBAC: three-tier roles (ADMIN / USER / GUEST) mapped to the unified permission matrix.
- ABAC: resource-ownership (Owner Check) resolution for modify/delete scenarios.
"""
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Permission matrix (design §1.1)
# ---------------------------------------------------------------------------
P_READ_PUBLIC = "policy:read_public"
P_CALC_EPHEMERAL = "policy:calc_ephemeral"
P_READ_DETAIL = "policy:read_detail"
P_SOP_SAVE = "sop:save_progress"
P_PERK_CLAIM = "perk:claim_coupon"
P_GALLERY_SUBMIT = "gallery:submit"
P_GALLERY_UPVOTE = "gallery:upvote"
P_MARKET_DEMAND = "market:create_demand"
P_MARKET_VENDOR = "market:vendor_apply"
P_FORUM_POST = "forum:post_comment"
P_PAGE_ORCHESTRATE = "page:orchestrate"
P_SCHEMA_MANAGE = "data:schema_manage"
P_SCRIPT_UPLOAD = "script:upload_python"
P_REVIEW_AUDIT = "review:audit_all"
P_CONTENT_INTERACT = "content:interact"
P_CONTENT_COMMENT = "content:comment"
# Unified publish permission: every registered maker may publish content on all
# UGC boards (policies / perks / compliance / products / demands / forum / SOP).
# The platform only runs the sensitive-word gate; authenticity is governed by
# community interaction (likes / dislikes / reports), and ADMIN-authored entries
# are stamped is_official server-side.
P_CONTENT_PUBLISH = "content:publish"
# Message box: every registered user can read and manage their own receipts.
P_NOTIFICATION_READ = "notification:read"

ALL_PERMISSIONS = {
    P_READ_PUBLIC, P_CALC_EPHEMERAL, P_READ_DETAIL, P_SOP_SAVE, P_PERK_CLAIM,
    P_GALLERY_SUBMIT, P_GALLERY_UPVOTE, P_MARKET_DEMAND, P_MARKET_VENDOR,
    P_FORUM_POST, P_PAGE_ORCHESTRATE, P_SCHEMA_MANAGE, P_SCRIPT_UPLOAD, P_REVIEW_AUDIT,
    P_CONTENT_INTERACT, P_CONTENT_COMMENT, P_CONTENT_PUBLISH, P_NOTIFICATION_READ,
}

GUEST_PERMISSIONS = {P_READ_PUBLIC, P_CALC_EPHEMERAL}
USER_PERMISSIONS = GUEST_PERMISSIONS | {
    P_READ_DETAIL, P_SOP_SAVE, P_PERK_CLAIM, P_GALLERY_SUBMIT, P_GALLERY_UPVOTE,
    P_MARKET_DEMAND, P_MARKET_VENDOR, P_FORUM_POST, P_CONTENT_INTERACT, P_CONTENT_COMMENT,
    P_CONTENT_PUBLISH, P_NOTIFICATION_READ,
}

# Permissions blocked while a credential rotation is pending (first-login enforcement).
HIGH_RISK_PERMISSIONS = {P_PAGE_ORCHESTRATE, P_SCHEMA_MANAGE, P_SCRIPT_UPLOAD, P_REVIEW_AUDIT}

# "MAKER" is the persisted role of an authenticated maker in this codebase (== design "USER").
ROLE_PERMISSIONS: Dict[str, Any] = {
    "GUEST": GUEST_PERMISSIONS,
    "USER": USER_PERMISSIONS,
    "MAKER": USER_PERMISSIONS,
    "ADMIN": "*",  # wildcard
}


def normalize_role(role: Optional[str]) -> str:
    return (role or "GUEST").strip().upper()


def has_permission(role: Optional[str], permission: Optional[str]) -> bool:
    """RBAC check. An empty/absent required permission means the scenario is public."""
    if not permission:
        return True
    perms = ROLE_PERMISSIONS.get(normalize_role(role), GUEST_PERMISSIONS)
    if perms == "*":
        return True
    return permission in perms


def parse_identity(token: Optional[str]) -> Dict[str, Any]:
    """Resolve caller identity from a signed session token; invalid/absent => GUEST."""
    from src.core.security import verify_session_token

    payload = verify_session_token(token or "")
    if not payload:
        return {
            "uid": "",
            "role": "GUEST",
            "authenticated": False,
            "must_change_password": False,
        }
    return {
        "uid": payload.get("uid", ""),
        "role": normalize_role(payload.get("role", "USER")),
        "authenticated": True,
        "must_change_password": bool(payload.get("must_change_password", False)),
    }


# ---------------------------------------------------------------------------
# ABAC: resource ownership resolution (design §2 owner check)
# ---------------------------------------------------------------------------
def resolve_resource_owner(resource_type: str, resource_id: str) -> Optional[str]:
    """Return the owner id for a resource, or None if unknown/not found.

    Lazy imports avoid core -> domains import cycles at module load time.
    """
    if not resource_type or not resource_id:
        return None
    try:
        rt = resource_type.strip().lower()
        if rt in ("product", "products", "product_showcase"):
            from src.domains.products.service import product_service
            obj = product_service._products.get(resource_id)
            return obj.author_id if obj else None
        if rt in ("demand", "demands"):
            from src.domains.demands.service import demand_service
            obj = demand_service.get_demand(resource_id)
            return obj.creator_id if obj else None
        if rt in ("thread", "threads", "forum_thread"):
            from src.domains.forum.service import forum_service
            forum_service._ensure_seed_thread(resource_id)
            obj = forum_service._threads.get(resource_id)
            return obj.author_id if obj else None
        if rt in ("comment", "comments", "forum_comment"):
            from src.domains.forum.service import forum_service
            obj = forum_service._comments.get(resource_id)
            return obj.author_id if obj else None
        if rt in ("sop_document", "sop_documents"):
            from src.domains.sop.service import sop_service
            obj = sop_service._documents.get(resource_id)
            return obj.user_id if obj else None
        if rt in ("user", "users", "profile"):
            # A user "owns" their own profile identity.
            return resource_id or None
    except Exception:
        return None
    return None


def is_owner_or_admin(actor_id: str, role: str, resource_type: str, resource_id: str) -> bool:
    """ABAC decision: ADMIN bypasses ownership; otherwise actor must own the resource."""
    if normalize_role(role) == "ADMIN":
        return True
    owner = resolve_resource_owner(resource_type, resource_id)
    if owner is None:
        # Unknown resource: do not leak existence; deny for non-admins.
        return False
    return bool(actor_id) and owner == actor_id
