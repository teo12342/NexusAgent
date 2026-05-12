"""Memory tools for nexus_agent Agent — search, learn, recall, preferences."""

import structlog
from typing import Dict, Any

logger = structlog.get_logger()


def register_memory_tools(registry: Dict):
    from ..memory import MemoryManager

    _memory: MemoryManager = None

    def get_memory() -> MemoryManager:
        nonlocal _memory
        if _memory is None:
            _memory = MemoryManager()
        return _memory

    def memory_search(query: str, limit: int = 5) -> Dict:
        return get_memory().recall(query=query, limit=limit)

    def memory_learn(content: str, importance: float = 1.0) -> str:
        return get_memory().learn(content=content, importance=importance)

    def memory_add(content: str, metadata: Dict = None, importance: float = 1.0) -> str:
        return get_memory().add(content=content, metadata=metadata, importance=importance)

    def memory_store_correction(wrong: str, right: str, context: str) -> str:
        return get_memory().store_correction(wrong=wrong, right=right, context=context)

    def memory_remember_preference(key: str, value: str) -> str:
        return get_memory().remember_preference(key=key, value=value)

    def memory_get_preference(key: str) -> str:
        return get_memory().get_preference(key=key) or ""

    def memory_get_stats() -> Dict:
        return get_memory().get_stats()

    def memory_get_graph_stats() -> Dict:
        return get_memory().graph.get_graph_stats()

    tools = {
        "memory_search": memory_search,
        "memory_learn": memory_learn,
        "memory_add": memory_add,
        "memory_store_correction": memory_store_correction,
        "memory_remember_preference": memory_remember_preference,
        "memory_get_preference": memory_get_preference,
        "memory_stats": memory_get_stats,
        "memory_graph_stats": memory_get_graph_stats,
    }
    registry.update(tools)