"""SQLite-backed lightweight Vector Store for OPC Hub RAG."""
import json
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.config import settings
from .embeddings import cosine_similarity


@dataclass
class VectorDocument:
    """Represents a text chunk and associated embedding vector."""
    doc_id: str
    collection: str
    title: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    vector: List[float] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SQLiteVectorStore:
    """Zero-dependency SQLite vector store supporting cosine similarity ranking and metadata filtering."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or getattr(settings, "rag_db_path", "data/rag_vectors.sqlite")
        self._mem_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._mem_conn.row_factory = sqlite3.Row
        self._ensure_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self.db_path == ":memory:":
            return self._mem_conn
        p = Path(self.db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _close_connection(self, conn: sqlite3.Connection):
        if self.db_path != ":memory:":
            conn.close()

    def _ensure_db(self):
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS rag_vectors (
                        collection TEXT NOT NULL,
                        doc_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        metadata_json TEXT NOT NULL,
                        vector_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        PRIMARY KEY (collection, doc_id)
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_rag_vectors_collection 
                    ON rag_vectors (collection)
                """)
        finally:
            self._close_connection(conn)

    def upsert(self, doc: VectorDocument) -> None:
        """Insert or replace a vector document."""
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("""
                    INSERT OR REPLACE INTO rag_vectors 
                    (collection, doc_id, title, content, metadata_json, vector_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc.collection,
                    doc.doc_id,
                    doc.title,
                    doc.content,
                    json.dumps(doc.metadata, ensure_ascii=False),
                    json.dumps(doc.vector),
                    doc.created_at,
                ))
        finally:
            self._close_connection(conn)

    def upsert_batch(self, docs: List[VectorDocument]) -> int:
        """Insert or replace multiple vector documents in transaction."""
        if not docs:
            return 0
        conn = self._get_connection()
        try:
            with conn:
                for doc in docs:
                    conn.execute("""
                        INSERT OR REPLACE INTO rag_vectors 
                        (collection, doc_id, title, content, metadata_json, vector_json, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        doc.collection,
                        doc.doc_id,
                        doc.title,
                        doc.content,
                        json.dumps(doc.metadata, ensure_ascii=False),
                        json.dumps(doc.vector),
                        doc.created_at,
                    ))
            return len(docs)
        finally:
            self._close_connection(conn)

    def count(self, collection: Optional[str] = None) -> int:
        """Return total document count in collection."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            if collection:
                cur.execute("SELECT COUNT(*) FROM rag_vectors WHERE collection = ?", (collection,))
            else:
                cur.execute("SELECT COUNT(*) FROM rag_vectors")
            return cur.fetchone()[0]
        finally:
            self._close_connection(conn)

    def get(self, collection: str, doc_id: str) -> Optional[VectorDocument]:
        """Fetch document by collection and ID."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT collection, doc_id, title, content, metadata_json, vector_json, created_at FROM rag_vectors WHERE collection = ? AND doc_id = ?",
                (collection, doc_id)
            )
            row = cur.fetchone()
            if not row:
                return None
            return VectorDocument(
                doc_id=row["doc_id"],
                collection=row["collection"],
                title=row["title"],
                content=row["content"],
                metadata=json.loads(row["metadata_json"]),
                vector=json.loads(row["vector_json"]),
                created_at=row["created_at"],
            )
        finally:
            self._close_connection(conn)

    def search_similarity(
        self,
        collection: str,
        query_vector: List[float],
        top_k: int = 5,
        filter_meta: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[VectorDocument, float]]:
        """Search top-k most similar documents in collection using cosine similarity."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT collection, doc_id, title, content, metadata_json, vector_json, created_at FROM rag_vectors WHERE collection = ?",
                (collection,)
            )
            rows = cur.fetchall()
            scored: List[Tuple[VectorDocument, float]] = []

            for row in rows:
                meta = json.loads(row["metadata_json"])
                # Apply metadata filtering if specified
                if filter_meta:
                    match = True
                    for k, v in filter_meta.items():
                        if meta.get(k) != v:
                            match = False
                            break
                    if not match:
                        continue

                vec = json.loads(row["vector_json"])
                sim = cosine_similarity(query_vector, vec)
                doc = VectorDocument(
                    doc_id=row["doc_id"],
                    collection=row["collection"],
                    title=row["title"],
                    content=row["content"],
                    metadata=meta,
                    vector=vec,
                    created_at=row["created_at"],
                )
                scored.append((doc, sim))

            # Sort descending by similarity
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k]
        finally:
            self._close_connection(conn)

    def clear(self, collection: Optional[str] = None) -> None:
        """Clear documents in collection or all documents."""
        conn = self._get_connection()
        try:
            with conn:
                if collection:
                    conn.execute("DELETE FROM rag_vectors WHERE collection = ?", (collection,))
                else:
                    conn.execute("DELETE FROM rag_vectors")
        finally:
            self._close_connection(conn)


# Default singleton instance
default_vector_store = SQLiteVectorStore()
