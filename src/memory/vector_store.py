"""
nexus_agent Agent Vector Store — src/memory/vector_store.py
ChromaDB-backed semantic memory search
"""

import os
import time
import structlog
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = structlog.get_logger()


@dataclass
class MemoryEntry:
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    importance: float = 1.0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0


class VectorStore:
    """
    ChromaDB-backed vector store for semantic memory.
    Stores embeddings with metadata, supports similarity search.
    """

    def __init__(self, persist_dir: str = "data/memory/vector", embedding_model: str = "nomic-embed-text"):
        self.persist_dir = persist_dir
        self.embedding_model = embedding_model
        self._chroma = None
        self._collection = None
        self._entries: Dict[str, MemoryEntry] = {}  # In-memory fallback
        self._use_chroma = False
        self._connected = False

    def connect(self) -> bool:
        """Connect to ChromaDB. Falls back to in-memory if unavailable."""
        try:
            import chromadb
            os.makedirs(self.persist_dir, exist_ok=True)
            self._chroma = chromadb.PersistentClient(path=self.persist_dir)
            self._collection = self._chroma.get_or_create_collection(
                name="nexus_agent Agent_memory",
                metadata={"model": self.embedding_model}
            )
            self._use_chroma = True
            self._connected = True
            logger.info("chroma_connected", path=self.persist_dir)
            return True
        except ImportError:
            logger.warning("ChromaDB not available, using in-memory fallback")
            self._use_chroma = False
            self._connected = True
            return True
        except Exception as e:
            logger.warning("ChromaDB init failed, using in-memory fallback", error=str(e))
            self._use_chroma = False
            self._connected = True
            return True

    def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 1.0,
        doc_id: Optional[str] = None,
    ) -> str:
        """Add a memory entry. Returns the entry ID."""
        entry_id = doc_id or f"mem_{int(time.time() * 1000)}"
        metadata = metadata or {}

        entry = MemoryEntry(
            id=entry_id,
            content=content,
            metadata=metadata,
            importance=importance,
        )

        if self._use_chroma:
            try:
                self._collection.add(
                    documents=[content],
                    metadatas=[{**metadata, "importance": importance, "id": entry_id}],
                    ids=[entry_id],
                )
            except Exception as e:
                logger.error("chroma_add_error", error=str(e))

        self._entries[entry_id] = entry
        logger.debug("memory_added", id=entry_id, importance=importance)
        return entry_id

    def search(
        self,
        query: str,
        limit: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search across all memories.
        Returns top N results with scores.
        """
        if not self._connected:
            return []

        if self._use_chroma:
            try:
                results = self._collection.query(
                    query_texts=[query],
                    n_results=limit,
                    where=filter_metadata,
                    include=["documents", "metadatas", "distances"],
                )

                search_results = []
                if results and results.get("documents"):
                    docs = results["documents"][0]
                    metas = results.get("metadatas", [[]])[0]
                    dists = results.get("distances", [[]])[0]
                    for i, doc in enumerate(docs):
                        meta = metas[i] if i < len(metas) else {}
                        score = 1.0 - dists[i] if i < len(dists) else 0
                        entry_id = meta.get("id", "unknown") if meta else "unknown"
                        if entry_id in self._entries:
                            self._entries[entry_id].access_count += 1
                            self._entries[entry_id].last_accessed = time.time()
                        search_results.append({
                            "id": entry_id,
                            "content": doc,
                            "score": score,
                            "importance": meta.get("importance", 1.0),
                            "metadata": {k: v for k, v in meta.items() if k not in ("id", "importance")},
                        })
                return search_results
            except Exception as e:
                logger.error("chroma_search_error", error=str(e))

        # In-memory fallback: simple keyword match
        query_lower = query.lower()
        scored = []
        for entry in self._entries.values():
            score = 0
            if query_lower in entry.content.lower():
                score = 0.5 + 0.5 * (len(query_lower) / max(len(entry.content), 1))
            if score > 0:
                scored.append({
                    "id": entry.id,
                    "content": entry.content,
                    "score": min(score, 1.0),
                    "importance": entry.importance,
                    "metadata": entry.metadata,
                })
        scored.sort(key=lambda x: x["score"] * x["importance"], reverse=True)
        return scored[:limit]

    def get(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific memory entry by ID."""
        entry = self._entries.get(entry_id)
        if not entry:
            return None
        entry.access_count += 1
        entry.last_accessed = time.time()
        return {
            "id": entry.id,
            "content": entry.content,
            "metadata": entry.metadata,
            "importance": entry.importance,
            "created_at": entry.created_at,
            "access_count": entry.access_count,
        }

    def delete(self, entry_id: str) -> bool:
        """Delete a memory entry."""
        if entry_id not in self._entries:
            return False
        if self._use_chroma:
            try:
                self._collection.delete(ids=[entry_id])
            except Exception as e:
                logger.error("chroma_delete_error", error=str(e))
        del self._entries[entry_id]
        return True

    def forget_low_value(self, threshold: float = 0.1) -> int:
        """Remove memories with low importance that haven't been accessed recently."""
        now = time.time()
        to_delete = []
        for entry in self._entries.values():
            if entry.importance < threshold and entry.access_count < 2:
                age_days = (now - entry.created_at) / 86400
                if age_days > 7:  # At least 7 days old
                    to_delete.append(entry.id)

        for entry_id in to_delete:
            self.delete(entry_id)

        if to_delete:
            logger.info("forgot_low_value_memories", count=len(to_delete))
        return len(to_delete)

    def count(self) -> int:
        return len(self._entries)

    def get_all_ids(self) -> List[str]:
        return list(self._entries.keys())