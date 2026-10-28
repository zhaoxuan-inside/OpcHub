"""Forum service managing Zhihu-style threads/questions, answers/perspectives, nested comments, and votes.

收藏 (FAVORITE)、喜欢 (LOVE) 与评分 (RATING) 由统一互动域
``src.domains.interactions.service`` 承载；本域只负责知乎式互斥赞同/反对投票体系。
"""
import uuid
from datetime import datetime, timezone
import time
import math
from typing import Optional, List, Dict, Set, Tuple, Any

from src.domains.forum.models import (
    ForumThreadCreate,
    ForumThreadResponse,
    ForumAnswerCreate,
    ForumAnswerResponse,
    ForumCommentCreate,
    ForumCommentResponse,
    CommentTreeNode,
    ThreadDetailResponse,
    VoteResponse,
)
from src.infrastructure.database.persistence import domain_persistence


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ForumService:
    """Thread, in-depth answer, nested comment tree, voting and bookmark persistence service."""

    def __init__(self):
        # Key: thread_id -> ForumThreadResponse
        self._threads: Dict[str, ForumThreadResponse] = {}
        # Key: answer_id -> ForumAnswerResponse
        self._answers: Dict[str, ForumAnswerResponse] = {}
        # Key: comment_id -> ForumCommentResponse
        self._comments: Dict[str, ForumCommentResponse] = {}
        # Key: (user_id, target_type, target_id) -> "UPVOTE" | "DOWNVOTE"
        # Single vote ledger; the UPVOTE subset is derivable by value lookup.
        self._votes: Dict[Tuple[str, str, str], str] = {}
        # Key: (user_id, thread_id)
        self._follows: Set[Tuple[str, str]] = set()
        self._deleted_thread_ids: Set[str] = set()
        self._deleted_answer_ids: Set[str] = set()
        # Key: cache_key -> (timestamp, data_dict)
        self._feed_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}

    def _require_db(self) -> None:
        """Forum content is database-backed; refuse memory-only mutations."""
        domain_persistence.require("forum")

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

    def clear(self) -> None:
        """Reset service state for isolated testing."""
        self._threads.clear()
        self._answers.clear()
        self._comments.clear()
        self._votes.clear()
        self._follows.clear()
        self._deleted_thread_ids.clear()
        self._deleted_answer_ids.clear()
        self._feed_cache.clear()

    # -------------------------------------------------------------------------
    # Thread (Question / Topic) Management
    # -------------------------------------------------------------------------

    def create_thread(self, payload: ForumThreadCreate) -> ForumThreadResponse:
        """Publish a new forum discussion thread or question."""
        self._require_db()
        thread_id = str(uuid.uuid4())
        now = utc_now_iso()
        thread = ForumThreadResponse(
            id=thread_id,
            category_code=payload.category_code,
            author_id=payload.author_id,
            author_name=payload.author_name or "超级个体创客",
            author_title=payload.author_title or "独立创业者",
            is_official=payload.is_official,
            title=payload.title,
            content=payload.content,
            view_count=0,
            upvote_count=0,
            downvote_count=0,
            comment_count=0,
            answer_count=0,
            follow_count=0,
            bookmark_count=0,
            is_pinned=False,
            status="PUBLISHED",
            hot_score=10.0,
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
        if tid not in self._threads or tid in self._deleted_thread_ids:
            raise KeyError(f"Forum thread with ID {thread_id} not found")
        thread = self._threads[tid]
        if record_view:
            thread.view_count += 1
            domain_persistence.write("forum.threads", tid, thread)
        return thread

    def get_thread_detail(self, thread_id: str, user_id: Optional[str] = None) -> Optional[ThreadDetailResponse]:
        """Retrieve thread detail including Zhihu-style answers and nested comments."""
        tid = str(thread_id)
        if tid not in self._threads or tid in self._deleted_thread_ids:
            return None
        
        thread = self.get_thread(tid, record_view=True)
        # Clone thread for response decoration
        th_dict = thread.model_dump()
        if user_id:
            th_dict["user_vote"] = self._votes.get((user_id, "THREAD", tid))
            th_dict["is_following"] = (user_id, tid) in self._follows

        # Gather answers for this thread
        raw_answers = [
            a for a in self._answers.values()
            if a.thread_id == tid and a.id not in self._deleted_answer_ids
        ]
        # Sort answers: accepted first, then by upvotes desc, then created_at desc
        raw_answers.sort(key=lambda a: (a.is_accepted, a.upvote_count, a.created_at), reverse=True)
        decorated_answers: List[ForumAnswerResponse] = []
        for a in raw_answers:
            a_copy = a.model_copy()
            if user_id:
                a_copy.user_vote = self._votes.get((user_id, "ANSWER", a.id))
            decorated_answers.append(a_copy)

        th_dict["answer_count"] = len(decorated_answers)
        th_dict["top_answers"] = decorated_answers[:3]
        dec_thread = ForumThreadResponse(**th_dict)

        # Gather nested comments tree
        comments_tree = self.get_comments_tree(tid, user_id=user_id)

        return ThreadDetailResponse(
            thread=dec_thread,
            answers=decorated_answers,
            comments=comments_tree,
        )

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
        """Retrieve paginated threads constrained by category, page, and size."""
        target_id = id or category_code or "ALL"
        raw_size = page_size if page_size is not None else (page_length if page_length is not None else 10)
        size = max(1, min(int(raw_size), 50))
        page_num = max(1, int(page))
        offset = (page_num - 1) * size

        threads = [t for t in self._threads.values() if t.id not in self._deleted_thread_ids]
        if target_id and str(target_id).upper() != "ALL":
            cat = str(target_id).upper()
            threads = [t for t in threads if (t.category_code or "").upper() == cat or str(t.id) == target_id]
        threads.sort(key=lambda t: (t.is_pinned, t.created_at), reverse=True)

        total = len(threads)
        items = threads[offset:offset + size]

        # Decorate with top answers
        decorated_items = []
        for t in items:
            t_copy = t.model_copy()
            answers = [
                a for a in self._answers.values()
                if a.thread_id == t.id and a.id not in self._deleted_answer_ids
            ]
            answers.sort(key=lambda a: (a.is_accepted, a.upvote_count), reverse=True)
            t_copy.top_answers = answers[:2]
            t_copy.answer_count = len(answers)
            decorated_items.append(t_copy.model_dump())

        return {
            "category_code": target_id,
            "page": page_num,
            "page_size": size,
            "page_length": size,
            "total": total,
            "total_pages": (total + size - 1) // size if total > 0 else 0,
            "has_more": (offset + size < total),
            "items": decorated_items,
        }

    # -------------------------------------------------------------------------
    # Zhihu-style Answer (Perspective) Management
    # -------------------------------------------------------------------------

    def create_answer(self, payload: ForumAnswerCreate) -> ForumAnswerResponse:
        """Post an in-depth answer or perspective to an existing question/thread."""
        self._require_db()
        tid = str(payload.thread_id)
        if tid not in self._threads or tid in self._deleted_thread_ids:
            raise KeyError(f"Forum thread with ID {tid} not found")

        thread = self._threads[tid]
        answer_id = str(uuid.uuid4())
        now = utc_now_iso()
        content = payload.content.strip()
        word_count = len(content)
        read_minutes = max(1, math.ceil(word_count / 300))

        answer = ForumAnswerResponse(
            id=answer_id,
            thread_id=tid,
            author_id=payload.author_id,
            author_name=payload.author_name or "创客探索者",
            author_title=payload.author_title or "超级个体实战家",
            content=content,
            upvote_count=0,
            downvote_count=0,
            comment_count=0,
            is_accepted=False,
            word_count=word_count,
            read_minutes=read_minutes,
            status="PUBLISHED",
            created_at=now,
            updated_at=now,
        )
        self._answers[answer_id] = answer

        # Update thread answer count and recalculate hot score
        answers_count = sum(1 for a in self._answers.values() if a.thread_id == tid and a.id not in self._deleted_answer_ids)
        thread.answer_count = answers_count
        thread.updated_at = now
        self.recalculate_hot_score("THREAD", tid)

        # Write-behind persistence
        domain_persistence.write("forum.answers", answer_id, answer)
        domain_persistence.write("forum.threads", tid, thread)
        self.invalidate_feed_cache(thread.category_code)

        return answer

    def get_answer(self, answer_id: str) -> ForumAnswerResponse:
        aid = str(answer_id)
        if aid not in self._answers or aid in self._deleted_answer_ids:
            raise KeyError(f"Forum answer with ID {aid} not found")
        return self._answers[aid]

    def accept_answer(self, thread_id: str, answer_id: str, operator_user_id: str) -> Tuple[bool, str]:
        """Accept an answer as the best perspective for the question."""
        self._require_db()
        tid = str(thread_id)
        aid = str(answer_id)
        if tid not in self._threads or tid in self._deleted_thread_ids:
            raise KeyError(f"Thread with ID {tid} not found")
        if aid not in self._answers or aid in self._deleted_answer_ids:
            raise KeyError(f"Answer with ID {aid} not found")

        thread = self._threads[tid]
        answer = self._answers[aid]
        if answer.thread_id != tid:
            raise ValueError(f"Answer {aid} does not belong to thread {tid}")

        # Check operator permission (author of question or admin/steward)
        is_author = (thread.author_id == operator_user_id)
        is_admin = operator_user_id.startswith("usr_platform") or operator_user_id.startswith("admin") or operator_user_id == "usr_steward"
        if not (is_author or is_admin):
            raise PermissionError("Only the author of the question or an admin can accept an answer")

        # Toggle or accept
        is_already_accepted = (thread.accepted_answer_id == aid)
        if is_already_accepted:
            # Unaccept
            thread.accepted_answer_id = None
            answer.is_accepted = False
            msg = "UNACCEPTED"
        else:
            # Clear previous accepted answer if any
            if thread.accepted_answer_id and thread.accepted_answer_id in self._answers:
                self._answers[thread.accepted_answer_id].is_accepted = False
                domain_persistence.write("forum.answers", thread.accepted_answer_id, self._answers[thread.accepted_answer_id])
            
            thread.accepted_answer_id = aid
            answer.is_accepted = True
            msg = "ACCEPTED"

        thread.updated_at = utc_now_iso()
        answer.updated_at = utc_now_iso()

        domain_persistence.write("forum.answers", aid, answer)
        domain_persistence.write("forum.threads", tid, thread)
        self.invalidate_feed_cache(thread.category_code)

        return True, msg

    def delete_answer(self, answer_id: str) -> bool:
        """Delete an answer, its attached comments and all related votes."""
        self._require_db()
        aid = str(answer_id)
        answer = self._answers.get(aid)
        if answer is None:
            return False
        self._answers.pop(aid, None)
        self._deleted_answer_ids.add(aid)
        self._purge_votes("ANSWER", aid)

        # Remove comments attached to this answer (and their votes)
        attached_comments = [
            c for c in self._comments.values()
            if c.target_type == "ANSWER" and c.target_id == aid
        ]
        for c in attached_comments:
            self._comments.pop(c.id, None)
            self._purge_votes("COMMENT", c.id)
            domain_persistence.delete("forum.comments", c.id)

        tid = answer.thread_id
        if tid in self._threads:
            thread = self._threads[tid]
            if thread.accepted_answer_id == aid:
                thread.accepted_answer_id = None
            thread.answer_count = sum(1 for a in self._answers.values() if a.thread_id == tid and a.id not in self._deleted_answer_ids)
            thread.comment_count = max(0, thread.comment_count - len(attached_comments))
            domain_persistence.write("forum.threads", tid, thread)
        domain_persistence.delete("forum.answers", aid)
        domain_persistence.write_raw("forum.tombstones", aid, {"id": aid, "type": "ANSWER"})
        return True

    # -------------------------------------------------------------------------
    # Voting & Interactions (知乎式互斥赞同 / 反对)
    # -------------------------------------------------------------------------

    def execute_vote(self, user_id: str, target_type: str, target_id: str, vote_type: str) -> VoteResponse:
        """Execute a Zhihu-style vote: UPVOTE, DOWNVOTE, or CANCEL with mutual exclusivity."""
        self._require_db()
        uid = str(user_id)
        ttype = str(target_type).upper()
        tid = str(target_id)
        vtype = str(vote_type).upper()

        if ttype not in ("THREAD", "ANSWER", "COMMENT"):
            raise ValueError(f"Unsupported target_type: {ttype}")
        if vtype not in ("UPVOTE", "DOWNVOTE", "CANCEL"):
            raise ValueError(f"Unsupported vote_type: {vtype}")

        # Resolve target object
        target_obj = None
        if ttype == "THREAD":
            if tid in self._threads and tid not in self._deleted_thread_ids:
                target_obj = self._threads[tid]
        elif ttype == "ANSWER":
            if tid in self._answers and tid not in self._deleted_answer_ids:
                target_obj = self._answers[tid]
        elif ttype == "COMMENT":
            if tid in self._comments:
                target_obj = self._comments[tid]

        if not target_obj:
            raise KeyError(f"Vote target {ttype} with ID {tid} not found")

        key = (uid, ttype, tid)
        current_vote = self._votes.get(key)
        new_vote: Optional[str] = None

        if vtype == "CANCEL" or current_vote == vtype:
            # Cancel current vote
            if current_vote == "UPVOTE":
                target_obj.upvote_count = max(0, target_obj.upvote_count - 1)
            elif current_vote == "DOWNVOTE":
                target_obj.downvote_count = max(0, target_obj.downvote_count - 1)
            self._votes.pop(key, None)
            new_vote = None
        elif vtype == "UPVOTE":
            if current_vote == "DOWNVOTE":
                target_obj.downvote_count = max(0, target_obj.downvote_count - 1)
            target_obj.upvote_count += 1
            self._votes[key] = "UPVOTE"
            new_vote = "UPVOTE"
        elif vtype == "DOWNVOTE":
            if current_vote == "UPVOTE":
                target_obj.upvote_count = max(0, target_obj.upvote_count - 1)
            target_obj.downvote_count += 1
            self._votes[key] = "DOWNVOTE"
            new_vote = "DOWNVOTE"

        # Recalculate hotness
        self.recalculate_hot_score(ttype, tid)

        # Persistence — single vote ledger (forum.votes carries the vote_type)
        vote_doc_id = f"{uid}_{ttype}_{tid}"
        if new_vote is None:
            domain_persistence.delete("forum.votes", vote_doc_id)
        else:
            domain_persistence.write_raw("forum.votes", vote_doc_id, {
                "user_id": uid,
                "target_type": ttype,
                "target_id": tid,
                "vote_type": new_vote,
                "created_at": utc_now_iso(),
            })

        if ttype == "THREAD":
            domain_persistence.write("forum.threads", tid, target_obj)
            self.invalidate_feed_cache(target_obj.category_code)
        elif ttype == "ANSWER":
            domain_persistence.write("forum.answers", tid, target_obj)
            # Also update parent thread cache
            if target_obj.thread_id in self._threads:
                self.invalidate_feed_cache(self._threads[target_obj.thread_id].category_code)
        elif ttype == "COMMENT":
            domain_persistence.write("forum.comments", tid, target_obj)

        return VoteResponse(
            user_vote=new_vote,
            upvote_count=target_obj.upvote_count,
            downvote_count=target_obj.downvote_count,
            target_type=ttype,
            target_id=tid,
        )

    def toggle_follow(self, user_id: str, thread_id: str) -> Dict[str, Any]:
        """Toggle question/topic follow state."""
        self._require_db()
        uid = str(user_id)
        tid = str(thread_id)
        if tid not in self._threads or tid in self._deleted_thread_ids:
            raise KeyError(f"Forum thread with ID {thread_id} not found")
        
        thread = self._threads[tid]
        key = (uid, tid)
        if key in self._follows:
            self._follows.remove(key)
            thread.follow_count = max(0, thread.follow_count - 1)
            is_following = False
        else:
            self._follows.add(key)
            thread.follow_count += 1
            is_following = True

        domain_persistence.write("forum.threads", tid, thread)
        return {
            "is_following": is_following,
            "follow_count": thread.follow_count,
            "thread_id": tid,
        }

    def recalculate_hot_score(self, target_type: str, target_id: str) -> float:
        """Compute Zhihu Newton-cooling thermal score for ranking."""
        ttype = str(target_type).upper()
        tid = str(target_id)
        if ttype == "THREAD":
            if tid not in self._threads or tid in self._deleted_thread_ids:
                return 0.0
            th = self._threads[tid]
            # Age in hours
            try:
                dt = datetime.fromisoformat(th.created_at.replace("Z", "+00:00"))
                hours = max(0.1, (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0)
            except Exception:
                hours = 1.0

            # Zhihu hot score algorithm
            score = (
                th.upvote_count * 3.5
                - th.downvote_count * 2.0
                + th.answer_count * 6.0
                + th.comment_count * 2.0
                + th.view_count * 0.08
                + (20.0 if th.is_pinned else 0.0)
            ) / ((hours + 2.0) ** 1.15)
            th.hot_score = round(max(0.0, score), 2)
            return th.hot_score
        return 0.0

    # -------------------------------------------------------------------------
    # Stream Feed & Discovery
    # -------------------------------------------------------------------------

    def fetch_feed_stream(
        self,
        category_code: str = "ALL",
        cursor: int = 0,
        limit: int = 10,
        sort_by: str = "latest",
    ) -> Dict[str, Any]:
        """Fetch Zhihu-style streaming feed with hotness ranking and top answers preview.

        The returned payload is viewer-independent (safe for the shared feed cache);
        per-user vote/follow annotation is applied afterwards by ``annotate_viewer_threads``.
        """
        target_cat = str(category_code).upper()
        offset = max(0, int(cursor))
        size = max(1, min(int(limit), 50))
        sort_mode = str(sort_by).lower()

        threads = [t for t in self._threads.values() if t.id not in self._deleted_thread_ids]
        if target_cat != "ALL":
            threads = [t for t in threads if (t.category_code or "").upper() == target_cat]

        # Refresh hot scores
        for t in threads:
            self.recalculate_hot_score("THREAD", t.id)

        if sort_mode == "hot":
            threads.sort(
                key=lambda t: (t.is_pinned, t.hot_score, t.upvote_count, t.answer_count, t.created_at),
                reverse=True,
            )
        elif sort_mode == "replies" or sort_mode == "answers":
            threads.sort(
                key=lambda t: (t.is_pinned, t.answer_count, t.comment_count, t.created_at),
                reverse=True,
            )
        elif sort_mode == "unanswered":
            threads = [t for t in threads if t.answer_count == 0]
            threads.sort(key=lambda t: (t.is_pinned, t.created_at), reverse=True)
        elif sort_mode == "featured":
            threads.sort(
                key=lambda t: (t.is_pinned, t.is_official, t.upvote_count, t.created_at),
                reverse=True,
            )
        else:
            # Latest
            threads.sort(key=lambda t: (t.is_pinned, t.created_at), reverse=True)

        total = len(threads)
        end = offset + size
        items = threads[offset:end]
        has_more = end < total
        next_cursor = end if has_more else None

        decorated_items = []
        for t in items:
            t_copy = t.model_copy()
            # Find answers for this thread
            ans_list = [
                a for a in self._answers.values()
                if a.thread_id == t.id and a.id not in self._deleted_answer_ids
            ]
            ans_list.sort(key=lambda a: (a.is_accepted, a.upvote_count, a.created_at), reverse=True)

            t_copy.top_answers = [a.model_copy() for a in ans_list[:2]]
            t_copy.answer_count = len(ans_list)
            decorated_items.append(t_copy.model_dump())

        return {
            "category_code": target_cat,
            "cursor": offset,
            "limit": size,
            "sort_by": sort_mode,
            "total": total,
            "has_more": has_more,
            "next_cursor": next_cursor,
            "items": decorated_items,
        }

    # -------------------------------------------------------------------------
    # Comments & Materialized Paths
    # -------------------------------------------------------------------------

    def validate_create_comment_payload(self, inputs: dict) -> dict:
        thread_id = str(inputs.get("thread_id", "")).strip()
        content = inputs.get("content", "").strip()
        parent_id = inputs.get("parent_id")
        target_type = str(inputs.get("target_type") or "ANSWER").upper()
        target_id = str(inputs.get("target_id") or "").strip()

        if not thread_id:
            raise ValueError("thread_id is required for forum comment")
        if not content:
            raise ValueError("Forum comment content cannot be empty")

        if thread_id not in self._threads:
            raise KeyError(f"Forum thread with ID {thread_id} not found")
        if parent_id and parent_id not in self._comments:
            raise KeyError(f"Parent comment with ID {parent_id} not found")

        return {
            "guard_passed": True,
            "thread_id": thread_id,
            "target_type": target_type,
            "target_id": target_id or thread_id,
            "content": content,
            "parent_id": parent_id,
            "author_id": inputs.get("author_id", ""),
            "author_name": inputs.get("author_name"),
            "author_title": inputs.get("author_title"),
            "reply_to_user_id": inputs.get("reply_to_user_id"),
        }

    def create_comment(self, thread_id: str, payload: ForumCommentCreate) -> ForumCommentResponse:
        """Post a comment under an answer or question with materialized path computation."""
        self._require_db()
        tid = str(thread_id)
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
            root_id = comment_id
            materialized_path = f"/{comment_id}"
            depth = 0
            reply_to = payload.reply_to_user_id

        target_type = payload.target_type or "ANSWER"
        target_id = payload.target_id or tid

        comment = ForumCommentResponse(
            id=comment_id,
            thread_id=thread_id,
            target_type=target_type,
            target_id=target_id,
            author_id=payload.author_id,
            author_name=payload.author_name or "独立创客",
            author_title=payload.author_title,
            content=payload.content,
            parent_id=payload.parent_id,
            root_id=root_id,
            reply_to_user_id=reply_to,
            materialized_path=materialized_path,
            depth=depth,
            upvote_count=0,
            downvote_count=0,
            is_accepted=False,
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )
        self._comments[comment_id] = comment
        thread.comment_count += 1

        # Also increment answer comment count if attached to an answer
        if target_type == "ANSWER" and target_id in self._answers:
            self._answers[target_id].comment_count += 1
            domain_persistence.write("forum.answers", target_id, self._answers[target_id])

        domain_persistence.write("forum.comments", comment_id, comment)
        domain_persistence.write("forum.threads", thread_id, thread)
        return comment

    def get_comments_tree(self, thread_id: str, target_id: Optional[str] = None, user_id: Optional[str] = None) -> List[CommentTreeNode]:
        """Construct hierarchical tree nodes ordered by materialized path and created_at."""
        comments = [
            c for c in self._comments.values()
            if c.thread_id == thread_id and c.status == "ACTIVE"
        ]
        if target_id:
            comments = [c for c in comments if c.target_id == target_id]

        comments.sort(key=lambda c: (c.depth, c.created_at))

        nodes: Dict[str, CommentTreeNode] = {}
        for c in comments:
            node = CommentTreeNode(
                id=c.id,
                thread_id=c.thread_id,
                target_type=c.target_type,
                target_id=c.target_id,
                author_id=c.author_id,
                author_name=c.author_name,
                author_title=c.author_title,
                content=c.content,
                parent_id=c.parent_id,
                root_id=c.root_id,
                reply_to_user_id=c.reply_to_user_id,
                materialized_path=c.materialized_path,
                depth=c.depth,
                upvote_count=c.upvote_count,
                downvote_count=c.downvote_count,
                is_accepted=c.is_accepted,
                status=c.status,
                created_at=c.created_at,
                updated_at=c.updated_at,
                children=[],
            )
            if user_id:
                node.user_vote = self._votes.get((user_id, "COMMENT", c.id))
            nodes[c.id] = node

        roots: List[CommentTreeNode] = []
        for c in comments:
            node = nodes[c.id]
            if c.parent_id and c.parent_id in nodes:
                nodes[c.parent_id].children.append(node)
            else:
                roots.append(node)

        return roots

    def update_thread(
        self,
        thread_id: str,
        title: str,
        content: str,
        category_code: Optional[str] = None,
        editor_id: str = "",
        is_admin: bool = False,
    ) -> ForumThreadResponse:
        """Edit title/content/category of a thread (author or ADMIN only)."""
        self._require_db()
        tid = str(thread_id)
        thread = self._threads.get(tid)
        if not thread or tid in self._deleted_thread_ids:
            raise KeyError(f"Forum thread with ID {thread_id} not found")
        if not is_admin and (not editor_id or str(thread.author_id) != str(editor_id)):
            raise PermissionError("只能编辑本人发布的讨论帖")

        new_title = str(title or "").strip()
        new_content = str(content or "").strip()
        if len(new_title) < 5:
            raise ValueError("Forum thread title must be at least 5 characters long")
        if len(new_content) < 10:
            raise ValueError("Forum thread content must be at least 10 characters long")

        thread.title = new_title
        thread.content = new_content
        new_category = str(category_code or "").strip().upper()
        if new_category and new_category != thread.category_code:
            thread.category_code = new_category
        thread.updated_at = utc_now_iso()

        domain_persistence.write("forum.threads", tid, thread)
        self.invalidate_feed_cache()
        return thread

    def annotate_viewer_threads(self, items: List[Dict[str, Any]], user_id: Optional[str]) -> None:
        """Decorate feed thread dicts with the caller's vote/follow state.

        Runs after the shared feed cache write so cached payloads stay viewer-independent.
        """
        if not user_id or not items:
            return
        uid = str(user_id)
        for item in items:
            tid = str(item.get("id") or "")
            if not tid:
                continue
            item["user_vote"] = self._votes.get((uid, "THREAD", tid))
            item["is_following"] = (uid, tid) in self._follows
            for answer in (item.get("top_answers") or []):
                aid = str(answer.get("id") or "")
                if aid:
                    answer["user_vote"] = self._votes.get((uid, "ANSWER", aid))

    def delete_thread(self, thread_id: str) -> bool:
        self._require_db()
        tid = str(thread_id)
        if tid in self._threads:
            self._threads.pop(tid, None)
            self._deleted_thread_ids.add(tid)
            domain_persistence.delete("forum.threads", tid)
            domain_persistence.write_raw("forum.tombstones", tid, {"id": tid, "type": "THREAD"})

            # Delete related answers and comments
            ans_to_del = [aid for aid, a in self._answers.items() if a.thread_id == tid]
            for aid in ans_to_del:
                self.delete_answer(aid)

            comments_to_del = [cid for cid, c in self._comments.items() if c.thread_id == tid]
            for cid in comments_to_del:
                self._comments.pop(cid, None)
                domain_persistence.delete("forum.comments", cid)

            self.invalidate_feed_cache()
            return True
        return False

    def _purge_votes(self, target_type: str, target_id: str) -> None:
        """Remove every user's vote records for one target (used on answer/comment deletion)."""
        tt = str(target_type).upper()
        tid = str(target_id)
        doomed = [key for key in self._votes if key[1] == tt and key[2] == tid]
        for key in doomed:
            self._votes.pop(key, None)
            doc_id = f"{key[0]}_{tt}_{tid}"
            domain_persistence.delete("forum.votes", doc_id)

    def delete_comment(self, comment_id: str) -> bool:
        """Delete a comment together with its whole materialized-path subtree."""
        self._require_db()
        cid = str(comment_id)
        comment = self._comments.get(cid)
        if comment is None:
            return False

        prefix = f"{comment.materialized_path}/"
        to_delete = [
            c for c in self._comments.values()
            if c.id == cid or (c.materialized_path or "").startswith(prefix)
        ]

        thread_id = comment.thread_id
        answer_decrements: Dict[str, int] = {}
        for c in to_delete:
            self._comments.pop(c.id, None)
            self._purge_votes("COMMENT", c.id)
            domain_persistence.delete("forum.comments", c.id)
            if c.target_type == "ANSWER" and c.target_id in self._answers:
                answer_decrements[c.target_id] = answer_decrements.get(c.target_id, 0) + 1

        if thread_id in self._threads:
            thread = self._threads[thread_id]
            thread.comment_count = max(0, thread.comment_count - len(to_delete))
            domain_persistence.write("forum.threads", thread_id, thread)
        for aid, removed in answer_decrements.items():
            answer = self._answers[aid]
            answer.comment_count = max(0, answer.comment_count - removed)
            domain_persistence.write("forum.answers", aid, answer)
        return True

    # -------------------------------------------------------------------------
    # Hydration
    # -------------------------------------------------------------------------

    def hydrate_tombstones(self, rows: List[Dict[str, Any]]) -> int:
        for r in rows:
            tid = str(r.get("id"))
            if tid:
                if r.get("type") == "ANSWER":
                    self._deleted_answer_ids.add(tid)
                else:
                    self._deleted_thread_ids.add(tid)
        return len(rows)

    def hydrate_threads(self, rows: List[Dict[str, Any]]) -> int:
        count = 0
        for r in rows:
            tid = str(r.get("id"))
            if tid and tid not in self._deleted_thread_ids:
                try:
                    self._threads[tid] = ForumThreadResponse(**r)
                    count += 1
                except Exception:
                    pass
        return count

    def hydrate_answers(self, rows: List[Dict[str, Any]]) -> int:
        count = 0
        for r in rows:
            aid = str(r.get("id"))
            if aid and aid not in self._deleted_answer_ids:
                try:
                    self._answers[aid] = ForumAnswerResponse(**r)
                    count += 1
                except Exception:
                    pass
        return count

    def hydrate_comments(self, rows: List[Dict[str, Any]]) -> int:
        count = 0
        for r in rows:
            cid = str(r.get("id"))
            if cid:
                try:
                    self._comments[cid] = ForumCommentResponse(**r)
                    count += 1
                except Exception:
                    pass
        return count

    def hydrate_votes(self, rows: List[Dict[str, Any]]) -> int:
        for r in rows:
            uid = r.get("user_id")
            ttype = r.get("target_type")
            tid = r.get("target_id")
            vtype = r.get("vote_type")
            if uid and ttype and tid and vtype:
                self._votes[(str(uid), str(ttype).upper(), str(tid))] = str(vtype).upper()
        return len(rows)


forum_service = ForumService()

# Hydration bindings
domain_persistence.register("forum.tombstones", forum_service.hydrate_tombstones)
domain_persistence.register("forum.threads", forum_service.hydrate_threads)
domain_persistence.register("forum.answers", forum_service.hydrate_answers)
domain_persistence.register("forum.comments", forum_service.hydrate_comments)
domain_persistence.register("forum.votes", forum_service.hydrate_votes)
