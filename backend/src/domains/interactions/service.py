"""Unified content interaction + comment service.

This service is the single source of truth for public-card interactions across
products, policies, demands, forum threads and SOP documents/flows. It keeps a
fast in-memory index and mirrors every mutation into the platform's
``domain_snapshots`` persistence layer, exactly like the other domain services.

Design notes
------------
* ``FORUM_THREAD`` targets: the Zhihu-style mutual UPVOTE/DOWNVOTE ledger lives in
  the forum domain (``forum.vote`` pipeline) and forum comments live in the forum
  domain too. This service only owns FAVORITE (收藏) / LOVE (喜欢) / RATING for
  forum threads, mirroring those counters back via ``_sync_domain``; the comment
  count is always read live from the owning thread so it never goes stale.
* Other target types (products, policies, demands, SOP, perks) own their full
  LIKE/FAVORITE/LOVE counters here, seeded from legacy fields on first touch.
* Aggregate counters live in ``content.interaction_stats``; per-user toggles live
  in ``content.interaction_records``; comments live in ``content.comments``.
* ``LIKE`` and ``FAVORITE`` and ``LOVE`` are independent toggles. ``LIKE`` is
  点赞, ``FAVORITE`` is 收藏 and ``LOVE`` is 喜欢. The legacy SOP ``like`` field is
  mapped to ``LOVE`` (喜欢).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from src.domains.interactions.models import (
    ContentComment,
    ContentCommentListResponse,
    InteractionState,
    InteractionToggleResponse,
    MyInteractionItem,
    MyInteractionResponse,
    INTERACTION_KINDS,
    TARGET_TYPES,
)
from src.infrastructure.database.persistence import domain_persistence

logger = logging.getLogger("opchub.interactions")

STATS_DOMAIN = "content.interaction_stats"
RECORDS_DOMAIN = "content.interaction_records"
COMMENTS_DOMAIN = "content.comments"
RATINGS_DOMAIN = "content.ratings"

KIND_FIELD = {
    "LIKE": "like_count",
    "FAVORITE": "favorite_count",
    "LOVE": "love_count",
    "DISLIKE": "dislike_count",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_target_type(value: str) -> str:
    tt = str(value or "").strip().upper()
    if tt not in TARGET_TYPES:
        raise ValueError(f"Unsupported interaction target_type: {value}")
    return tt


def _normalize_kind(value: str) -> str:
    kind = str(value or "").strip().upper()
    if kind not in INTERACTION_KINDS:
        raise ValueError(f"Unsupported interaction kind: {value}")
    return kind


def _key(target_type: str, target_id: str) -> str:
    return f"{target_type}|{target_id}"


def _record_key(user_id: str, target_type: str, target_id: str, kind: str) -> str:
    return f"{user_id}|{target_type}|{target_id}|{kind}"


def _empty_counts() -> Dict[str, int]:
    return {
        "like_count": 0,
        "favorite_count": 0,
        "love_count": 0,
        "comment_count": 0,
        "dislike_count": 0,
        "rating_sum": 0,
        "rating_count": 0,
    }


def _lookup_target(target_type: str, target_id: str) -> Any:
    """Resolve a domain entity for legacy seeding / counter synchronisation."""
    tid = str(target_id)
    if target_type == "PRODUCT":
        from src.domains.products.service import product_service

        return product_service._products.get(tid)
    if target_type == "POLICY":
        from src.domains.policies.service import policy_service

        return policy_service._policies.get(tid)
    if target_type == "DEMAND":
        from src.domains.demands.service import demand_service

        return demand_service._demands.get(tid)
    if target_type == "FORUM_THREAD":
        from src.domains.forum.service import forum_service

        forum_service._ensure_seed_thread(tid)
        return forum_service._threads.get(tid)
    if target_type == "SOP_DOCUMENT":
        from src.domains.sop.service import sop_service

        return sop_service._nodes.get(tid)
    if target_type == "SOP_FLOW":
        from src.domains.sop.service import sop_service

        return sop_service._flow_templates.get(tid)
    if target_type == "PERK":
        from src.domains.perks.service import perk_service

        return perk_service._perks.get(tid)
    return None


def _legacy_counts(target_type: str, target_id: str) -> Dict[str, int]:
    """Read historical counters from the owning domain (no writes)."""
    obj = _lookup_target(target_type, target_id)
    counts = _empty_counts()
    if obj is None:
        return counts

    if target_type == "PRODUCT":
        counts["like_count"] = int(getattr(obj, "upvote_count", 0) or 0)
        counts["favorite_count"] = int(getattr(obj, "favorite_count", 0) or 0)
        counts["love_count"] = int(getattr(obj, "love_count", 0) or 0)
        counts["comment_count"] = int(getattr(obj, "comment_count", 0) or 0)
    elif target_type == "POLICY":
        counts["like_count"] = int(getattr(obj, "like_count", 0) or 0)
        counts["favorite_count"] = int(getattr(obj, "favorite_count", 0) or 0)
        counts["love_count"] = int(getattr(obj, "love_count", 0) or 0)
        counts["comment_count"] = int(getattr(obj, "comment_count", 0) or 0)
    elif target_type == "DEMAND":
        counts["like_count"] = int(getattr(obj, "like_count", 0) or 0)
        counts["favorite_count"] = int(getattr(obj, "favorite_count", 0) or 0)
        counts["love_count"] = int(getattr(obj, "love_count", 0) or 0)
        counts["comment_count"] = int(getattr(obj, "comment_count", 0) or 0)
    elif target_type == "FORUM_THREAD":
        # 赞同/反对归论坛域投票账本，这里不播种 like_count（论坛卡片不再使用 LIKE）。
        counts["favorite_count"] = int(getattr(obj, "bookmark_count", 0) or 0)
        counts["love_count"] = int(getattr(obj, "love_count", 0) or 0)
        counts["comment_count"] = int(getattr(obj, "comment_count", 0) or 0)
    elif target_type == "SOP_DOCUMENT":
        # Legacy SOP "like" is mapped to LOVE (喜欢), per product decision.
        counts["like_count"] = int(getattr(obj, "praise_count", 0) or 0)
        counts["favorite_count"] = int(getattr(obj, "favorite_count", 0) or 0)
        counts["love_count"] = int(getattr(obj, "like_count", 0) or 0)
        counts["comment_count"] = int(getattr(obj, "comment_count", 0) or 0)
    elif target_type == "SOP_FLOW":
        counts["like_count"] = int(getattr(obj, "praise_count", 0) or 0)
        counts["favorite_count"] = int(getattr(obj, "favorite_count", 0) or 0)
        counts["love_count"] = int(getattr(obj, "like_count", 0) or 0)
        counts["comment_count"] = int(getattr(obj, "comment_count", 0) or 0)
    elif target_type == "PERK":
        counts["like_count"] = int(getattr(obj, "like_count", 0) or 0)
        counts["favorite_count"] = int(getattr(obj, "favorite_count", 0) or 0)
        counts["love_count"] = int(getattr(obj, "love_count", 0) or 0)
        counts["comment_count"] = int(getattr(obj, "comment_count", 0) or 0)
    return counts


def _legacy_viewer(user_id: str, target_type: str, target_id: str) -> Dict[str, bool]:
    """Recover pre-existing per-user toggles from legacy domain services."""
    state = {"liked": False, "favorited": False, "loved": False}
    if not user_id:
        return state
    uid = str(user_id)
    tid = str(target_id)
    return state


class ContentInteractionService:
    """Unified interaction store for all public content targets."""

    def __init__(self) -> None:
        self._stats: Dict[Tuple[str, str], Dict[str, int]] = {}
        self._records: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
        self._comments: Dict[str, ContentComment] = {}
        self._ratings: Dict[Tuple[str, str, str], int] = {}

    # ------------------------------------------------------------------
    # Persistence hydration
    # ------------------------------------------------------------------
    def clear(self) -> None:
        self._stats.clear()
        self._records.clear()
        self._comments.clear()
        self._ratings.clear()

    def hydrate_stats(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows:
            tt = str(row.get("target_type") or "").upper()
            tid = str(row.get("target_id") or "")
            if not tt or not tid:
                continue
            counts = _empty_counts()
            for field in counts:
                counts[field] = int(row.get(field, 0) or 0)
            self._stats[(tt, tid)] = counts
        return len(rows)

    def hydrate_ratings(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows:
            uid = str(row.get("user_id") or "")
            tt = str(row.get("target_type") or "").upper()
            tid = str(row.get("target_id") or "")
            score = int(row.get("score", 0) or 0)
            if not uid or not tt or not tid or score < 1 or score > 5:
                continue
            self._ratings[(uid, tt, tid)] = score
        return len(rows)

    def hydrate_records(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows:
            uid = str(row.get("user_id") or "")
            tt = str(row.get("target_type") or "").upper()
            tid = str(row.get("target_id") or "")
            kind = str(row.get("kind") or "").upper()
            if not uid or not tt or not tid or kind not in INTERACTION_KINDS:
                continue
            self._records[(uid, tt, tid, kind)] = {
                "created_at": row.get("created_at") or utc_now_iso(),
                "target_title": row.get("target_title") or "",
            }
        return len(rows)

    def hydrate_comments(self, rows: List[Dict[str, Any]]) -> int:
        for row in rows:
            try:
                comment = ContentComment(**row)
            except Exception:
                continue
            self._comments[comment.id] = comment
        return len(rows)

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------
    def _ensure_stats(self, target_type: str, target_id: str) -> Dict[str, int]:
        key = (target_type, target_id)
        if key not in self._stats:
            counts = _legacy_counts(target_type, target_id)
            self._stats[key] = counts
            self._persist_stats(target_type, target_id, counts)
        return self._stats[key]

    def _ensure_viewer(self, user_id: str, target_type: str, target_id: str) -> None:
        if not user_id:
            return
        legacy = _legacy_viewer(user_id, target_type, target_id)
        mapping = {"liked": "LIKE", "favorited": "FAVORITE", "loved": "LOVE"}
        for flag, kind in mapping.items():
            if not legacy.get(flag):
                continue
            key = (str(user_id), target_type, str(target_id), kind)
            if key in self._records:
                continue
            self._records[key] = {
                "created_at": utc_now_iso(),
                "target_title": self._target_title(target_type, target_id),
            }
            domain_persistence.write_raw(
                RECORDS_DOMAIN,
                _record_key(str(user_id), target_type, str(target_id), kind),
                {
                    "user_id": str(user_id),
                    "target_type": target_type,
                    "target_id": str(target_id),
                    "kind": kind,
                    "target_title": self._records[key]["target_title"],
                    "created_at": self._records[key]["created_at"],
                },
            )

    def _persist_stats(self, target_type: str, target_id: str, counts: Dict[str, int]) -> None:
        domain_persistence.write_raw(
            STATS_DOMAIN,
            _key(target_type, target_id),
            {
                "target_type": target_type,
                "target_id": str(target_id),
                **{k: int(v or 0) for k, v in counts.items()},
                "updated_at": utc_now_iso(),
            },
        )

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    def _target_title(self, target_type: str, target_id: str) -> str:
        obj = _lookup_target(target_type, target_id)
        if obj is None:
            return ""
        for attr in ("title", "name", "document_title"):
            value = getattr(obj, attr, None)
            if value:
                return str(value)
        return ""

    def _viewer(self, user_id: str, target_type: str, target_id: str) -> Dict[str, bool]:
        if not user_id:
            return {
                "liked": False,
                "favorited": False,
                "loved": False,
                "commented": False,
                "disliked": False,
                "rating": 0,
            }
        uid = str(user_id)
        commented = any(
            c.author_id == uid and c.target_type == target_type and c.target_id == str(target_id)
            for c in self._comments.values()
        )
        return {
            "liked": (uid, target_type, str(target_id), "LIKE") in self._records,
            "favorited": (uid, target_type, str(target_id), "FAVORITE") in self._records,
            "loved": (uid, target_type, str(target_id), "LOVE") in self._records,
            "commented": commented,
            "disliked": (uid, target_type, str(target_id), "DISLIKE") in self._records,
            "rating": self._ratings.get((uid, target_type, str(target_id)), 0),
        }

    @staticmethod
    def _rating_avg(counts: Dict[str, int]) -> float:
        total = int(counts.get("rating_sum", 0) or 0)
        n = int(counts.get("rating_count", 0) or 0)
        if n <= 0:
            return 0.0
        return round(total / n, 1)

    def get_state(self, user_id: Optional[str], target_type: str, target_id: str) -> InteractionState:
        tt = _normalize_target_type(target_type)
        tid = str(target_id)
        counts = self._ensure_stats(tt, tid)
        if tt == "FORUM_THREAD":
            # 论坛评论数以论坛域实时值为准（评论走 forum.comments 域，不经过本服务）。
            obj = _lookup_target(tt, tid)
            if obj is not None:
                counts["comment_count"] = int(getattr(obj, "comment_count", 0) or 0)
        self._ensure_viewer(user_id or "", tt, tid)
        return InteractionState(
            target_type=tt,
            target_id=tid,
            like_count=counts["like_count"],
            favorite_count=counts["favorite_count"],
            love_count=counts["love_count"],
            comment_count=counts["comment_count"],
            dislike_count=counts["dislike_count"],
            rating_avg=self._rating_avg(counts),
            rating_count=counts["rating_count"],
            viewer=self._viewer(user_id or "", tt, tid),
        )

    def batch_state(
        self,
        user_id: Optional[str],
        targets: Iterable[Any],
    ) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = []
        for raw in targets:
            try:
                if isinstance(raw, dict):
                    tt = raw.get("target_type")
                    tid = raw.get("target_id")
                else:
                    tt = getattr(raw, "target_type", None)
                    tid = getattr(raw, "target_id", None)
                if not tt or tid is None:
                    continue
                state = self.get_state(user_id, str(tt), str(tid))
                items.append(state.model_dump())
            except Exception:
                continue
        return {"items": items}

    # ------------------------------------------------------------------
    # Toggles
    # ------------------------------------------------------------------
    def toggle(
        self,
        user_id: str,
        target_type: str,
        target_id: str,
        kind: str,
        target_title: Optional[str] = None,
    ) -> InteractionToggleResponse:
        if not user_id:
            raise PermissionError("请先登录创客账号后再进行互动")
        tt = _normalize_target_type(target_type)
        kind = _normalize_kind(kind)
        tid = str(target_id)
        if _lookup_target(tt, tid) is None:
            raise KeyError(f"Interaction target not found: {tt}/{tid}")

        counts = self._ensure_stats(tt, tid)
        self._ensure_viewer(user_id, tt, tid)
        key = (str(user_id), tt, tid, kind)
        field = KIND_FIELD[kind]

        if key in self._records:
            del self._records[key]
            counts[field] = max(0, counts[field] - 1)
            active = False
            domain_persistence.delete(
                RECORDS_DOMAIN, _record_key(str(user_id), tt, tid, kind)
            )
        else:
            meta = {
                "created_at": utc_now_iso(),
                "target_title": (target_title or self._target_title(tt, tid) or "")[:255],
            }
            self._records[key] = meta
            counts[field] += 1
            active = True
            domain_persistence.write_raw(
                RECORDS_DOMAIN,
                _record_key(str(user_id), tt, tid, kind),
                {
                    "user_id": str(user_id),
                    "target_type": tt,
                    "target_id": tid,
                    "kind": kind,
                    **meta,
                },
            )

        self._persist_stats(tt, tid, counts)
        self._sync_domain(tt, tid, counts)

        viewer = self._viewer(str(user_id), tt, tid)
        return InteractionToggleResponse(
            target_type=tt,
            target_id=tid,
            kind=kind,
            active=active,
            count=counts[field],
            like_count=counts["like_count"],
            favorite_count=counts["favorite_count"],
            love_count=counts["love_count"],
            comment_count=counts["comment_count"],
            dislike_count=counts["dislike_count"],
            rating_avg=self._rating_avg(counts),
            rating_count=counts["rating_count"],
            viewer=viewer,
        )

    def rate(
        self,
        user_id: str,
        target_type: str,
        target_id: str,
        score: int,
    ) -> InteractionState:
        """Submit / update the caller's 1-5 star rating for one public target."""
        if not user_id:
            raise PermissionError("请先登录创客账号后再进行打分")
        tt = _normalize_target_type(target_type)
        tid = str(target_id)
        score = int(score)
        if score < 1 or score > 5:
            raise ValueError("打分范围必须为 1-5 分")
        if _lookup_target(tt, tid) is None:
            raise KeyError(f"Rating target not found: {tt}/{tid}")

        counts = self._ensure_stats(tt, tid)
        self._ensure_viewer(user_id, tt, tid)
        key = (str(user_id), tt, tid)
        previous = self._ratings.get(key, 0)
        if previous:
            counts["rating_sum"] = max(0, counts["rating_sum"] - previous)
        else:
            counts["rating_count"] += 1
        counts["rating_sum"] += score
        self._ratings[key] = score

        domain_persistence.write_raw(
            RATINGS_DOMAIN,
            _record_key(str(user_id), tt, tid, "RATING"),
            {
                "user_id": str(user_id),
                "target_type": tt,
                "target_id": tid,
                "score": score,
                "updated_at": utc_now_iso(),
            },
        )
        self._persist_stats(tt, tid, counts)
        self._sync_domain(tt, tid, counts)
        return self.get_state(str(user_id), tt, tid)

    def _sync_domain(self, target_type: str, target_id: str, counts: Dict[str, int]) -> None:
        """Mirror unified counters back onto the owning domain entity."""
        obj = _lookup_target(target_type, target_id)
        if obj is None:
            return

        if target_type == "PRODUCT":
            obj.upvote_count = counts["like_count"]
            obj.favorite_count = counts["favorite_count"]
            obj.love_count = counts["love_count"]
            obj.comment_count = counts["comment_count"]
            from src.domains.products.service import product_service

            domain_persistence.write("products.items", target_id, obj)
            product_service.invalidate_cache()
        elif target_type == "POLICY":
            obj.like_count = counts["like_count"]
            obj.favorite_count = counts["favorite_count"]
            obj.love_count = counts["love_count"]
            obj.comment_count = counts["comment_count"]
            domain_persistence.write("policies.items", target_id, obj)
        elif target_type == "DEMAND":
            obj.like_count = counts["like_count"]
            obj.favorite_count = counts["favorite_count"]
            obj.love_count = counts["love_count"]
            obj.comment_count = counts["comment_count"]
            from src.domains.demands.service import demand_service

            domain_persistence.write("demands.items", target_id, obj)
            demand_service.invalidate_cache()
        elif target_type == "FORUM_THREAD":
            # 赞同(upvote_count)与评论数(comment_count)归论坛域账本，不在此覆写；
            # 收藏与喜欢由统一互动系统镜像回帖子实体。
            obj.bookmark_count = counts["favorite_count"]
            obj.love_count = counts["love_count"]
            domain_persistence.write("forum.threads", target_id, obj)
        elif target_type == "SOP_DOCUMENT":
            obj.like_count = counts["love_count"]
            obj.favorite_count = counts["favorite_count"]
            obj.praise_count = counts["like_count"]
            obj.comment_count = counts["comment_count"]
            domain_persistence.write("sop.nodes", target_id, obj)
        elif target_type == "SOP_FLOW":
            obj.like_count = counts["love_count"]
            obj.favorite_count = counts["favorite_count"]
            obj.praise_count = counts["like_count"]
            obj.comment_count = counts["comment_count"]
            domain_persistence.write("sop.flow_templates", target_id, obj)
        elif target_type == "PERK":
            obj.like_count = counts["like_count"]
            obj.favorite_count = counts["favorite_count"]
            obj.love_count = counts["love_count"]
            obj.comment_count = counts["comment_count"]
            domain_persistence.write("perks.items", target_id, obj)

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------
    def _persist_comment(self, comment: ContentComment) -> None:
        domain_persistence.write(COMMENTS_DOMAIN, comment.id, comment)

    def list_comments(self, target_type: str, target_id: str) -> ContentCommentListResponse:
        tt = _normalize_target_type(target_type)
        tid = str(target_id)
        items = [
            c for c in self._comments.values()
            if c.target_type == tt and c.target_id == tid
        ]
        items.sort(key=lambda c: c.created_at)
        return ContentCommentListResponse(items=items, total=len(items))

    def create_comment(
        self,
        user_id: str,
        target_type: str,
        target_id: str,
        content: str,
        author_name: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> ContentComment:
        if not user_id:
            raise PermissionError("请先登录创客账号后再发表评论")
        tt = _normalize_target_type(target_type)
        tid = str(target_id)
        if _lookup_target(tt, tid) is None:
            raise KeyError(f"Comment target not found: {tt}/{tid}")
        text = (content or "").strip()
        if not text:
            raise ValueError("评论内容不能为空")

        comment = ContentComment(
            id=f"cmt_{uuid.uuid4().hex[:12]}",
            target_type=tt,
            target_id=tid,
            author_id=str(user_id),
            author_name=(author_name or "创客")[:64],
            content=text[:4000],
            parent_id=parent_id,
            created_at=utc_now_iso(),
        )
        self._comments[comment.id] = comment
        self._persist_comment(comment)

        counts = self._ensure_stats(tt, tid)
        counts["comment_count"] += 1
        self._persist_stats(tt, tid, counts)
        self._sync_domain(tt, tid, counts)
        return comment

    def delete_comment(self, user_id: str, comment_id: str, is_admin: bool = False) -> bool:
        comment = self._comments.get(str(comment_id))
        if comment is None:
            raise KeyError(f"Comment not found: {comment_id}")
        if not is_admin and comment.author_id != str(user_id):
            raise PermissionError("只能删除自己发表的评论")

        del self._comments[comment.id]
        domain_persistence.delete(COMMENTS_DOMAIN, comment.id)
        counts = self._ensure_stats(comment.target_type, comment.target_id)
        counts["comment_count"] = max(0, counts["comment_count"] - 1)
        self._persist_stats(comment.target_type, comment.target_id, counts)
        self._sync_domain(comment.target_type, comment.target_id, counts)
        return True

    # ------------------------------------------------------------------
    # Personal interaction centre
    # ------------------------------------------------------------------
    def mine(self, user_id: str) -> MyInteractionResponse:
        if not user_id:
            return MyInteractionResponse(
                items=[],
                counts={"like": 0, "favorite": 0, "love": 0, "comment": 0, "dislike": 0},
            )
        uid = str(user_id)
        items: List[MyInteractionItem] = []
        kind_label = {"LIKE": "点赞", "FAVORITE": "收藏", "LOVE": "喜欢", "DISLIKE": "踩"}
        tab_map = {
            "PRODUCT": "product",
            "POLICY": "policy",
            "DEMAND": "demand",
            "FORUM_THREAD": "forum",
            "SOP_DOCUMENT": "sop",
            "SOP_FLOW": "sop",
        }

        for (record_uid, tt, tid, kind), meta in self._records.items():
            if record_uid != uid:
                continue
            title = meta.get("target_title") or self._target_title(tt, tid)
            items.append(
                MyInteractionItem(
                    target_type=tt,
                    target_id=tid,
                    kind=kind,
                    title=title,
                    subtitle=kind_label.get(kind, kind),
                    tab=tab_map.get(tt, ""),
                    created_at=meta.get("created_at", ""),
                )
            )

        comment_items: List[MyInteractionItem] = []
        for comment in self._comments.values():
            if comment.author_id != uid:
                continue
            comment_items.append(
                MyInteractionItem(
                    target_type=comment.target_type,
                    target_id=comment.target_id,
                    kind="COMMENT",
                    title=self._target_title(comment.target_type, comment.target_id),
                    subtitle=(comment.content or "")[:80],
                    tab=tab_map.get(comment.target_type, ""),
                    created_at=comment.created_at,
                )
            )

        counts = {
            "like": sum(1 for i in items if i.kind == "LIKE"),
            "favorite": sum(1 for i in items if i.kind == "FAVORITE"),
            "love": sum(1 for i in items if i.kind == "LOVE"),
            "dislike": sum(1 for i in items if i.kind == "DISLIKE"),
            "comment": len(comment_items),
        }
        items.extend(comment_items)
        items.sort(key=lambda i: i.created_at, reverse=True)
        return MyInteractionResponse(items=items, counts=counts)


content_interaction_service = ContentInteractionService()

domain_persistence.register(STATS_DOMAIN, content_interaction_service.hydrate_stats)
domain_persistence.register(RECORDS_DOMAIN, content_interaction_service.hydrate_records)
domain_persistence.register(COMMENTS_DOMAIN, content_interaction_service.hydrate_comments)
domain_persistence.register(RATINGS_DOMAIN, content_interaction_service.hydrate_ratings)
