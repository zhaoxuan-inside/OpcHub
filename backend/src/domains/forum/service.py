"""Forum service managing threads, materialized-path comments, upvotes, and bookmarks."""
import uuid
from datetime import datetime, timezone
import time
from typing import Optional, List, Dict, Set, Tuple, Any, Union

from src.domains.forum.models import (
    ForumThreadCreate,
    ForumThreadResponse,
    ForumCommentCreate,
    ForumCommentResponse,
    CommentTreeNode,
    ThreadDetailResponse,
    UpvoteResponse,
    BookmarkResponse,
)
from src.infrastructure.database.persistence import domain_persistence


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


import json
from pathlib import Path


def _load_forum_seeds() -> Dict[str, Dict[str, Any]]:
    """Load baseline discussion thread seeds from external data file.

    Maintains strict code and data separation: zero article content hardcoded in python source code.
    """
    search_paths = [
        Path("backend/data/seeds/forum_threads.json"),
        Path("data/seeds/forum_threads.json"),
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "seeds" / "forum_threads.json",
    ]
    for p in search_paths:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


DEFAULT_SEEDS_DICT: Dict[str, Dict[str, Any]] = _load_forum_seeds()



class ForumService:
    """Thread, nested comment tree, upvote and bookmark persistence service."""

    def __init__(self):
        self._threads: Dict[str, ForumThreadResponse] = {}
        self._comments: Dict[str, ForumCommentResponse] = {}
        # Key: (user_id, target_type, target_id)
        self._upvotes: Set[Tuple[str, str, str]] = set()
        # Key: (user_id, thread_id)
        self._bookmarks: Dict[Tuple[str, str], str] = {}  # maps to folder_name
        self._deleted_thread_ids: Set[str] = set()
        # Key: cache_key -> (timestamp, data_dict)
        self._feed_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._init_seeds()

    def invalidate_feed_cache(self, category_code: Optional[str] = None) -> int:
        """Invalidate feed cache entries for a specific category or globally."""
        if not category_code or str(category_code).upper() == "ALL":
            count = len(self._feed_cache)
            self._feed_cache.clear()
            return count
        cat_prefix = str(category_code).upper()
        keys_to_del = [k for k in self._feed_cache if k.startswith(cat_prefix) or k.startswith("ALL")]
        for k in keys_to_del:
            self._feed_cache.pop(k, None)
        return len(keys_to_del)

    def get_feed_cache(self, cache_key: str, ttl_seconds: float = 180.0) -> Optional[Dict[str, Any]]:
        """Retrieve cached feed batch if not expired."""
        entry = self._feed_cache.get(cache_key)
        if entry:
            ts, data = entry
            if time.time() - ts <= ttl_seconds:
                return data
            self._feed_cache.pop(cache_key, None)
        return None

    def set_feed_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Store feed batch into cache with current timestamp."""
        self._feed_cache[cache_key] = (time.time(), data)

    def _init_seeds(self) -> None:
        for tid, seed in DEFAULT_SEEDS_DICT.items():
            if tid not in self._deleted_thread_ids and tid not in self._threads:
                self._threads[tid] = ForumThreadResponse(**seed)

    def _ensure_seed_thread(self, thread_id: str) -> None:
        tid = str(thread_id)
        if tid in self._deleted_thread_ids:
            return
        if tid in self._threads:
            return
        if tid in DEFAULT_SEEDS_DICT:
            seed = DEFAULT_SEEDS_DICT[tid]
            self._threads[tid] = ForumThreadResponse(**seed)

    def clear(self) -> None:
        """Reset service state for isolated testing."""
        self._threads.clear()
        self._comments.clear()
        self._upvotes.clear()
        self._bookmarks.clear()
        self._deleted_thread_ids.clear()
        self._feed_cache.clear()

    def create_thread(self, payload: ForumThreadCreate) -> ForumThreadResponse:
        """Publish a new forum discussion thread."""
        thread_id = str(uuid.uuid4())
        now = utc_now_iso()
        thread = ForumThreadResponse(
            id=thread_id,
            category_code=payload.category_code,
            author_id=payload.author_id,
            author_name=payload.author_name,
            is_official=payload.is_official,
            title=payload.title,
            content=payload.content,
            view_count=0,
            upvote_count=0,
            comment_count=0,
            bookmark_count=0,
            is_pinned=False,
            status="PUBLISHED",
            created_at=now,
            updated_at=now,
        )
        self._threads[thread_id] = thread
        domain_persistence.write("forum.threads", thread_id, thread)
        self.invalidate_feed_cache(payload.category_code)
        return thread

    def get_thread(self, thread_id: str, record_view: bool = True) -> ForumThreadResponse:
        """Get thread by ID, optionally incrementing view count."""
        tid = str(thread_id)
        self._ensure_seed_thread(tid)
        if tid not in self._threads:
            raise KeyError(f"Forum thread with ID {thread_id} not found")
        thread = self._threads[tid]
        if record_view:
            thread.view_count += 1
            domain_persistence.write("forum.threads", tid, thread)
        return thread

    def list_threads(self, category_code: Optional[str] = None, id: Optional[str] = None) -> List[ForumThreadResponse]:
        """List threads, optionally filtered by category, sorted by pinned first then created_at desc."""
        target_cat = category_code or id
        threads = [t for t in self._threads.values() if t.id not in self._deleted_thread_ids]
        if target_cat and str(target_cat).upper() != "ALL":
            cat = str(target_cat).upper()
            threads = [t for t in threads if (t.category_code or "").upper() == cat or str(t.id) == target_cat]
        threads.sort(key=lambda t: (t.is_pinned, t.created_at), reverse=True)
        return threads

    def list_threads_paginated(
        self,
        id: Optional[str] = None,
        category_code: Optional[str] = None,
        page: int = 1,
        page_size: Optional[int] = None,
        page_length: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Retrieve paginated threads constrained by id (category/partition), page, and page_length.
        
        Enforces page bounds and max page length to prevent bulk data dumping.
        """
        target_id = id or category_code or "ALL"
        # Determine page size / page length with default 10 and max 50
        raw_size = page_size if page_size is not None else (page_length if page_length is not None else 10)
        size = max(1, min(int(raw_size), 50))
        p = max(1, int(page or 1))

        all_matched = [t for t in self._threads.values() if t.id not in self._deleted_thread_ids]
        if target_id and str(target_id).upper() != "ALL":
            cat = str(target_id).upper()
            all_matched = [t for t in all_matched if (t.category_code or "").upper() == cat or str(t.id) == target_id]

        all_matched.sort(key=lambda t: (t.is_pinned, t.created_at), reverse=True)

        total = len(all_matched)
        start = (p - 1) * size
        end = start + size
        items = all_matched[start:end]
        total_pages = (total + size - 1) // size if total > 0 else 1
        has_more = end < total

        return {
            "id": target_id,
            "page": p,
            "page_size": size,
            "page_length": size,
            "total": total,
            "total_pages": total_pages,
            "has_more": has_more,
            "items": [t.model_dump() for t in items],
        }

    def fetch_feed_stream(
        self,
        category_code: Optional[str] = "ALL",
        cursor: int = 0,
        limit: int = 10,
        sort_by: str = "latest",
    ) -> Dict[str, Any]:
        """Fetch threads as a continuous infinite scroll feed with cursor-based slicing."""
        target_id = str(category_code or "ALL").upper()
        size = max(1, min(int(limit or 10), 50))
        offset = max(0, int(cursor or 0))

        all_matched = [t for t in self._threads.values() if t.id not in self._deleted_thread_ids]
        if target_id != "ALL":
            all_matched = [t for t in all_matched if (t.category_code or "").upper() == target_id or str(t.id) == target_id]

        if sort_by == "hot":
            # Pinned first, then by hot score (upvotes * 3 + comment_count * 5), then creation time
            all_matched.sort(
                key=lambda t: (t.is_pinned, (t.upvote_count * 3 + t.comment_count * 5), t.created_at),
                reverse=True,
            )
        elif sort_by == "replies":
            all_matched.sort(
                key=lambda t: (t.is_pinned, t.comment_count, t.created_at),
                reverse=True,
            )
        else:
            # Latest
            all_matched.sort(key=lambda t: (t.is_pinned, t.created_at), reverse=True)

        total = len(all_matched)
        end = offset + size
        items = all_matched[offset:end]
        has_more = end < total
        next_cursor = end if has_more else None

        return {
            "category_code": target_id,
            "cursor": offset,
            "limit": size,
            "sort_by": sort_by,
            "total": total,
            "has_more": has_more,
            "next_cursor": next_cursor,
            "items": [t.model_dump() for t in items],
        }

    def validate_create_comment_payload(self, inputs: dict) -> dict:
        thread_id = str(inputs.get("thread_id", "")).strip()
        content = inputs.get("content", "").strip()
        parent_id = inputs.get("parent_id")
        if not thread_id:
            raise ValueError("thread_id is required for forum comment")
        if not content:
            raise ValueError("Forum comment content cannot be empty")
        self._ensure_seed_thread(thread_id)
        if thread_id not in self._threads:
            raise KeyError(f"Forum thread with ID {thread_id} not found")
        if parent_id and parent_id not in self._comments:
            raise KeyError(f"Parent comment with ID {parent_id} not found")
        return {
            "guard_passed": True,
            "thread_id": thread_id,
            "content": content,
            "parent_id": parent_id,
            "author_id": inputs.get("author_id", ""),
            "reply_to_user_id": inputs.get("reply_to_user_id"),
        }

    def create_comment(self, thread_id: str, payload: ForumCommentCreate) -> ForumCommentResponse:
        """Post a top-level answer or a nested sub-reply with materialized path computation."""
        tid = str(thread_id)
        self._ensure_seed_thread(tid)
        if tid not in self._threads:
            raise KeyError(f"Forum thread with ID {thread_id} not found")
        
        thread = self._threads[tid]
        comment_id = str(uuid.uuid4())
        now = utc_now_iso()

        if payload.parent_id:
            if payload.parent_id not in self._comments:
                raise KeyError(f"Parent comment with ID {payload.parent_id} not found")
            parent = self._comments[payload.parent_id]
            if parent.thread_id != thread_id:
                raise ValueError("Parent comment does not belong to this thread")
            
            root_id = parent.root_id if parent.root_id else parent.id
            materialized_path = f"{parent.materialized_path}/{comment_id}"
            depth = parent.depth + 1
            reply_to = payload.reply_to_user_id or parent.author_id
        else:
            # Top-level answer
            root_id = comment_id
            materialized_path = f"/{comment_id}"
            depth = 0
            reply_to = payload.reply_to_user_id

        comment = ForumCommentResponse(
            id=comment_id,
            thread_id=thread_id,
            author_id=payload.author_id,
            content=payload.content,
            parent_id=payload.parent_id,
            root_id=root_id,
            reply_to_user_id=reply_to,
            materialized_path=materialized_path,
            depth=depth,
            upvote_count=0,
            is_accepted=False,
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )
        self._comments[comment_id] = comment
        thread.comment_count += 1
        domain_persistence.write("forum.comments", comment_id, comment)
        domain_persistence.write("forum.threads", thread_id, thread)
        return comment

    def build_comment_tree(self, thread_id: str) -> List[CommentTreeNode]:
        """Assemble an O(N) recursive nested comment tree for the given thread."""
        thread_comments = [c for c in self._comments.values() if c.thread_id == thread_id]
        # Sort by creation time to preserve chronological conversation flow
        thread_comments.sort(key=lambda c: c.created_at)

        nodes: Dict[str, CommentTreeNode] = {}
        roots: List[CommentTreeNode] = []

        # Step 1: Create all tree nodes
        for c in thread_comments:
            nodes[c.id] = CommentTreeNode(
                id=c.id,
                thread_id=c.thread_id,
                author_id=c.author_id,
                content=c.content,
                parent_id=c.parent_id,
                root_id=c.root_id,
                reply_to_user_id=c.reply_to_user_id,
                materialized_path=c.materialized_path,
                depth=c.depth,
                upvote_count=c.upvote_count,
                is_accepted=c.is_accepted,
                status=c.status,
                created_at=c.created_at,
                updated_at=c.updated_at,
                children=[],
            )

        # Step 2: Assemble parent-child tree structure
        for c in thread_comments:
            node = nodes[c.id]
            if c.parent_id and c.parent_id in nodes:
                nodes[c.parent_id].children.append(node)
            else:
                roots.append(node)

        return roots

    def get_thread_detail(self, thread_id: str) -> ThreadDetailResponse:
        """Retrieve thread info and assembled recursive comment tree."""
        thread = self.get_thread(thread_id, record_view=True)
        comments_tree = self.build_comment_tree(thread_id)
        return ThreadDetailResponse(thread=thread, comments=comments_tree)

    def toggle_upvote(self, user_id: str, target_type: str, target_id: str) -> UpvoteResponse:
        """Atomically toggle upvote on a thread or comment with deduplication."""
        tid = str(target_id)
        if target_type == "THREAD":
            self._ensure_seed_thread(tid)
            if tid not in self._threads:
                raise KeyError(f"Forum thread {target_id} not found")
            target = self._threads[tid]
        elif target_type == "COMMENT":
            if tid not in self._comments:
                raise KeyError(f"Forum comment {target_id} not found")
            target = self._comments[tid]
        else:
            raise ValueError(f"Invalid target_type: {target_type}")

        key = (user_id, target_type, tid)
        upvote_doc_id = f"{user_id}|{target_type}|{tid}"
        if key in self._upvotes:
            self._upvotes.remove(key)
            target.upvote_count = max(0, target.upvote_count - 1)
            is_upvoted = False
            domain_persistence.delete("forum.upvotes", upvote_doc_id)
        else:
            self._upvotes.add(key)
            target.upvote_count += 1
            is_upvoted = True
            domain_persistence.write_raw("forum.upvotes", upvote_doc_id, {
                "user_id": user_id, "target_type": target_type, "target_id": tid,
            })

        # Persist the recomputed aggregate count on the upvoted target
        if target_type == "THREAD":
            domain_persistence.write("forum.threads", tid, target)
        else:
            domain_persistence.write("forum.comments", tid, target)

        return UpvoteResponse(
            is_upvoted=is_upvoted,
            upvote_count=target.upvote_count,
            target_type=target_type,  # type: ignore
            target_id=tid,
        )

    def toggle_bookmark(self, user_id: str, thread_id: str, folder_name: str = "默认收藏夹") -> BookmarkResponse:
        """Atomically toggle bookmark on a thread with deduplication."""
        tid = str(thread_id)
        self._ensure_seed_thread(tid)
        if tid not in self._threads:
            raise KeyError(f"Forum thread {thread_id} not found")
        thread = self._threads[tid]

        key = (user_id, tid)
        bookmark_doc_id = f"{user_id}|{tid}"
        if key in self._bookmarks:
            del self._bookmarks[key]
            thread.bookmark_count = max(0, thread.bookmark_count - 1)
            is_bookmarked = False
            domain_persistence.delete("forum.bookmarks", bookmark_doc_id)
        else:
            self._bookmarks[key] = folder_name
            thread.bookmark_count += 1
            is_bookmarked = True
            domain_persistence.write_raw("forum.bookmarks", bookmark_doc_id, {
                "user_id": user_id, "thread_id": tid, "folder_name": folder_name,
            })

        domain_persistence.write("forum.threads", tid, thread)

        return BookmarkResponse(
            is_bookmarked=is_bookmarked,
            bookmark_count=thread.bookmark_count,
            thread_id=tid,
            folder_name=folder_name,
        )


    def delete_thread(self, thread_id: str) -> bool:
        """Physically delete thread and its associated comments for Saga compensation or owner/admin deletion."""
        tid = str(thread_id)
        self._ensure_seed_thread(tid)
        self._deleted_thread_ids.add(tid)
        if tid in self._threads:
            del self._threads[tid]
            domain_persistence.delete("forum.threads", tid)
            domain_persistence.write_raw("forum.tombstones", tid, {"id": tid})
            # Cascade delete associated comments
            to_delete = [cid for cid, c in self._comments.items() if c.thread_id == tid]
            for cid in to_delete:
                del self._comments[cid]
                domain_persistence.delete("forum.comments", cid)
            self.invalidate_feed_cache()
            return True
        return False

    def delete_comment(self, comment_id: str) -> bool:
        """Physically delete comment and decrement thread comment count for Saga compensation."""
        if comment_id in self._comments:
            comment = self._comments[comment_id]
            thread_id = comment.thread_id
            del self._comments[comment_id]
            domain_persistence.delete("forum.comments", comment_id)
            if thread_id in self._threads:
                self._threads[thread_id].comment_count = max(0, self._threads[thread_id].comment_count - 1)
                domain_persistence.write("forum.threads", thread_id, self._threads[thread_id])
            return True
        return False

    # ------------------------------------------------------------------
    # Startup hydration (in-memory index rebuild from persisted documents)
    # ------------------------------------------------------------------
    def hydrate_threads(self, rows: List[Dict]) -> int:
        for r in rows:
            if r["id"] not in self._deleted_thread_ids:
                self._threads[r["id"]] = ForumThreadResponse(**r)
        return len(rows)

    def hydrate_tombstones(self, rows: List[Dict]) -> int:
        for r in rows:
            tid = str(r["id"])
            self._deleted_thread_ids.add(tid)
            if tid in self._threads:
                del self._threads[tid]
        return len(rows)

    def hydrate_comments(self, rows: List[Dict]) -> int:
        for r in rows:
            self._comments[r["id"]] = ForumCommentResponse(**r)
        return len(rows)

    def hydrate_upvotes(self, rows: List[Dict]) -> int:
        for r in rows:
            self._upvotes.add((r["user_id"], r["target_type"], r["target_id"]))
        return len(rows)

    def hydrate_bookmarks(self, rows: List[Dict]) -> int:
        for r in rows:
            self._bookmarks[(r["user_id"], r["thread_id"])] = r["folder_name"]
        return len(rows)


# Global singleton instance
forum_service = ForumService()

domain_persistence.register("forum.tombstones", forum_service.hydrate_tombstones)
domain_persistence.register("forum.threads", forum_service.hydrate_threads)
domain_persistence.register("forum.comments", forum_service.hydrate_comments)
domain_persistence.register("forum.upvotes", forum_service.hydrate_upvotes)
domain_persistence.register("forum.bookmarks", forum_service.hydrate_bookmarks)
