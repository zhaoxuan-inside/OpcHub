"""Forum service managing threads, materialized-path comments, upvotes, and bookmarks."""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Set, Tuple

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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ForumService:
    """Thread, nested comment tree, upvote and bookmark persistence service."""

    def __init__(self):
        self._threads: Dict[str, ForumThreadResponse] = {}
        self._comments: Dict[str, ForumCommentResponse] = {}
        # Key: (user_id, target_type, target_id)
        self._upvotes: Set[Tuple[str, str, str]] = set()
        # Key: (user_id, thread_id)
        self._bookmarks: Dict[Tuple[str, str], str] = {}  # maps to folder_name

    def clear(self) -> None:
        """Reset service state for isolated testing."""
        self._threads.clear()
        self._comments.clear()
        self._upvotes.clear()
        self._bookmarks.clear()

    def create_thread(self, payload: ForumThreadCreate) -> ForumThreadResponse:
        """Publish a new forum discussion thread."""
        thread_id = str(uuid.uuid4())
        now = utc_now_iso()
        thread = ForumThreadResponse(
            id=thread_id,
            category_code=payload.category_code,
            author_id=payload.author_id,
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
        return thread

    def get_thread(self, thread_id: str, record_view: bool = True) -> ForumThreadResponse:
        """Get thread by ID, optionally incrementing view count."""
        if thread_id not in self._threads:
            raise KeyError(f"Forum thread with ID {thread_id} not found")
        thread = self._threads[thread_id]
        if record_view:
            thread.view_count += 1
        return thread

    def list_threads(self, category_code: Optional[str] = None) -> List[ForumThreadResponse]:
        """List threads, optionally filtered by category, sorted by pinned first then created_at desc."""
        threads = list(self._threads.values())
        if category_code:
            threads = [t for t in threads if t.category_code == category_code]
        threads.sort(key=lambda t: (t.is_pinned, t.created_at), reverse=True)
        return threads

    def create_comment(self, thread_id: str, payload: ForumCommentCreate) -> ForumCommentResponse:
        """Post a top-level answer or a nested sub-reply with materialized path computation."""
        if thread_id not in self._threads:
            raise KeyError(f"Forum thread with ID {thread_id} not found")
        
        thread = self._threads[thread_id]
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
        if target_type == "THREAD":
            if target_id not in self._threads:
                raise KeyError(f"Forum thread {target_id} not found")
            target = self._threads[target_id]
        elif target_type == "COMMENT":
            if target_id not in self._comments:
                raise KeyError(f"Forum comment {target_id} not found")
            target = self._comments[target_id]
        else:
            raise ValueError(f"Invalid target_type: {target_type}")

        key = (user_id, target_type, target_id)
        if key in self._upvotes:
            self._upvotes.remove(key)
            target.upvote_count = max(0, target.upvote_count - 1)
            is_upvoted = False
        else:
            self._upvotes.add(key)
            target.upvote_count += 1
            is_upvoted = True

        return UpvoteResponse(
            is_upvoted=is_upvoted,
            upvote_count=target.upvote_count,
            target_type=target_type,  # type: ignore
            target_id=target_id,
        )

    def toggle_bookmark(self, user_id: str, thread_id: str, folder_name: str = "默认收藏夹") -> BookmarkResponse:
        """Atomically toggle bookmark on a thread with deduplication."""
        if thread_id not in self._threads:
            raise KeyError(f"Forum thread {thread_id} not found")
        thread = self._threads[thread_id]

        key = (user_id, thread_id)
        if key in self._bookmarks:
            del self._bookmarks[key]
            thread.bookmark_count = max(0, thread.bookmark_count - 1)
            is_bookmarked = False
        else:
            self._bookmarks[key] = folder_name
            thread.bookmark_count += 1
            is_bookmarked = True

        return BookmarkResponse(
            is_bookmarked=is_bookmarked,
            bookmark_count=thread.bookmark_count,
            thread_id=thread_id,
            folder_name=folder_name,
        )


# Global singleton instance
forum_service = ForumService()
