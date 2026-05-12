"""
nexus_agent Agent Memory Manager — src/memory/memory_manager.py
Unified memory interface: search + graph + auto-learn
"""

import time
import structlog
from typing import Dict, List, Any, Optional
from .vector_store import VectorStore
from .graph_store import GraphStore

logger = structlog.get_logger()


class MemoryManager:
    """
    Unified memory interface combining vector search and knowledge graph.
    - add() stores in both vector and graph
    - search() queries vector store
    - learn() automatically extracts relationships and stores in graph
    - recall() fetches context-relevant memories for the agent
    """

    def __init__(
        self,
        persist_dir: str = "data/memory",
        embedding_model: str = "nomic-embed-text",
    ):
        self.persist_dir = persist_dir
        self.vector = VectorStore(
            persist_dir=f"{persist_dir}/vector",
            embedding_model=embedding_model,
        )
        self.graph = GraphStore(persist_path=f"{persist_dir}/graph.json")
        self._session_context: List[Dict[str, Any]] = []
        self._connect()

    def _connect(self) -> None:
        self.vector.connect()
        logger.info("memory_manager_ready", vector_count=self.vector.count())

    def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 1.0,
        node_id: Optional[str] = None,
        node_type: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> str:
        """
        Add a memory to both vector store and optionally graph.
        metadata keys: 'source' (session/file/manual), 'tags', 'project', etc.
        """
        metadata = dict(metadata or {})
        entry_id = self.vector.add(content=content, metadata=metadata, importance=importance, doc_id=node_id)

        # Also add to graph if node_type specified
        if node_type:
            labels = labels or []
            self.graph.add_node(
                node_id=entry_id,
                node_type=node_type,
                label=content[:200],  # truncated label
                properties={"importance": importance, "labels": labels, **metadata},
            )
            # Connect related concepts via project tag
            project = metadata.get("project")
            if project:
                self.graph.add_edge(
                    from_id=entry_id,
                    to_id=f"project:{project}",
                    relationship="part_of",
                    weight=importance,
                )

        logger.debug("memory_added", id=entry_id, importance=importance)
        return entry_id

    def learn(
        self,
        content: str,
        source: str = "auto",
        importance: float = 0.8,
    ) -> str:
        """
        Auto-learn from a statement. Extracts entities and relationships.
        Called automatically when agent makes a correction or learns something.
        """
        # Simple entity extraction — in a full implementation, use NER
        words = content.split()
        entry_id = self.add(
            content=content,
            metadata={"source": source, "type": "learned"},
            importance=importance,
            node_type="fact",
        )
        logger.debug("learned", content=content[:100])
        return entry_id

    def recall(
        self,
        query: str,
        limit: int = 5,
        include_graph: bool = True,
    ) -> Dict[str, Any]:
        """
        Main recall function — semantic search + graph context.
        Returns both vector results and related graph nodes.
        """
        vector_results = self.vector.search(query=query, limit=limit)

        graph_context = []
        if include_graph:
            graph_nodes = self.graph.search_by_label(query)
            graph_context = [
                {"id": n["id"], "label": n.get("label", ""), "type": n.get("node_type", "")}
                for n in graph_nodes[:5]
            ]

        return {
            "query": query,
            "vector_results": vector_results,
            "graph_context": graph_context,
            "total_results": len(vector_results),
        }

    def add_session_message(self, role: str, content: str, session_id: str) -> None:
        """Add a message to the rolling session context."""
        self._session_context.append({
            "role": role,
            "content": content,
            "session_id": session_id,
            "timestamp": time.time(),
        })
        # Keep last 100 messages
        if len(self._session_context) > 100:
            self._session_context = self._session_context[-100:]

    def get_session_context(self, session_id: str, lines: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages for a specific session for context injection."""
        session_msgs = [m for m in self._session_context if m["session_id"] == session_id]
        return session_msgs[-lines:]

    def remember_preference(self, key: str, value: str) -> None:
        """Store a user preference permanently."""
        self.add(
            content=f"User preference: {key} = {value}",
            metadata={"source": "preference", "key": key, "value": value},
            importance=2.0,  # High importance — never forget
            node_type="preference",
            labels=["preference"],
        )

    def get_preference(self, key: str) -> Optional[str]:
        """Retrieve a stored preference."""
        results = self.vector.search(query=f"preference {key}", limit=3)
        for r in results:
            meta = r.get("metadata", {})
            if meta.get("key") == key:
                return meta.get("value")
        return None

    def store_correction(self, wrong: str, right: str, context: str) -> str:
        """Store a correction so the agent doesn't repeat the mistake."""
        entry_id = self.add(
            content=f"Correction: instead of '{wrong}', use '{right}'. Context: {context}",
            metadata={"source": "correction", "wrong": wrong, "right": right, "context": context},
            importance=2.5,  # Very high importance — critical to remember
            node_type="fact",
        )
        # Also mark as connected in graph
        self.graph.add_node(
            node_id=entry_id,
            node_type="correction",
            label=f"Don't use '{wrong}'",
            properties={"wrong": wrong, "right": right},
        )
        self.graph.add_edge(entry_id, "corrections", "is_a", weight=2.5)
        return entry_id

    def get_stats(self) -> Dict[str, Any]:
        return {
            "vector_entries": self.vector.count(),
            "graph_stats": self.graph.get_graph_stats(),
            "session_context_messages": len(self._session_context),
        }


# Singleton
memory_manager = MemoryManager()