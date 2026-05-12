"""
nexus_agent Agent Graph Store — src/memory/graph_store.py
NetworkX-backed knowledge graph for relationships between concepts
"""

import time
import structlog
from typing import Dict, List, Any, Optional, Set
import networkx as nx

logger = structlog.get_logger()


class GraphStore:
    """
    NetworkX-based knowledge graph.
    Nodes = concepts, entities, projects, people
    Edges = relationships between them
    """

    def __init__(self, persist_path: str = "data/memory/graph.json"):
        self.persist_path = persist_path
        self.graph = nx.DiGraph()
        self._load()

    def add_node(
        self,
        node_id: str,
        node_type: str,  # "person", "project", "concept", "fact", "preference"
        label: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a node to the knowledge graph.
        node_type: person | project | concept | fact | preference
        """
        properties = properties or {}
        self.graph.add_node(
            node_id,
            node_type=node_type,
            label=label,
            created_at=time.time(),
            **properties,
        )

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        relationship: str,  # "works_on", "part_of", "knows", "depends_on", "related_to"
        weight: float = 1.0,
        bidirectional: bool = False,
    ) -> None:
        """Add a directed edge between two nodes."""
        self.graph.add_edge(
            from_id,
            to_id,
            relationship=relationship,
            weight=weight,
            created_at=time.time(),
        )
        if bidirectional:
            self.graph.add_edge(
                to_id,
                from_id,
                relationship=relationship,
                weight=weight,
                created_at=time.time(),
            )

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get node data."""
        if node_id not in self.graph:
            return None
        data = dict(self.graph.nodes[node_id])
        data["id"] = node_id
        return data

    def get_neighbors(
        self,
        node_id: str,
        relationship: Optional[str] = None,
        depth: int = 1,
    ) -> List[Dict[str, Any]]:
        """Get all neighbors of a node, optionally filtered by relationship."""
        if node_id not in self.graph:
            return []

        neighbors = []
        for neighbor in self.graph.neighbors(node_id):
            edge_data = self.graph.edges[node_id, neighbor]
            if relationship and edge_data.get("relationship") != relationship:
                continue
            neighbors.append({
                "id": neighbor,
                "relationship": edge_data.get("relationship"),
                "weight": edge_data.get("weight", 1.0),
                **dict(self.graph.nodes[neighbor]),
            })
        return neighbors

    def find_path(self, from_id: str, to_id: str) -> Optional[List[str]]:
        """Find the shortest path between two nodes."""
        if from_id not in self.graph or to_id not in self.graph:
            return None
        try:
            return nx.shortest_path(self.graph, from_id, to_id)
        except nx.NetworkXNoPath:
            return None

    def search_by_type(self, node_type: str) -> List[Dict[str, Any]]:
        """Find all nodes of a specific type."""
        results = []
        for node_id, data in self.graph.nodes(data=True):
            if data.get("node_type") == node_type:
                results.append({"id": node_id, **dict(data)})
        return results

    def search_by_label(self, query: str) -> List[Dict[str, Any]]:
        """Find nodes whose label contains the query string."""
        query_lower = query.lower()
        results = []
        for node_id, data in self.graph.nodes(data=True):
            if query_lower in data.get("label", "").lower():
                results.append({"id": node_id, **dict(data)})
        return results

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and all its edges."""
        if node_id not in self.graph:
            return False
        self.graph.remove_node(node_id)
        return True

    def delete_edge(self, from_id: str, to_id: str) -> bool:
        """Delete an edge between two nodes."""
        try:
            self.graph.remove_edge(from_id, to_id)
            return True
        except nx.NetworkXError:
            return False

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the graph."""
        node_types = {}
        for _, data in self.graph.nodes(data=True):
            nt = data.get("node_type", "unknown")
            node_types[nt] = node_types.get(nt, 0) + 1

        rel_types = {}
        for _, _, data in self.graph.edges(data=True):
            rt = data.get("relationship", "unknown")
            rel_types[rt] = rel_types.get(rt, 0) + 1

        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "node_types": node_types,
            "relationship_types": rel_types,
        }

    def save(self) -> None:
        """Save graph to disk."""
        import json
        import os
        os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)

        data = {
            "nodes": [
                {"id": n, **d}
                for n, d in self.graph.nodes(data=True)
            ],
            "edges": [
                {"from": u, "to": v, **d}
                for u, v, d in self.graph.edges(data=True)
            ],
        }
        with open(self.persist_path, "w") as f:
            json.dump(data, f)
        logger.debug("graph_saved", nodes=self.graph.number_of_nodes())

    def _load(self) -> None:
        """Load graph from disk."""
        import json
        if not os.path.exists(self.persist_path):
            return
        try:
            with open(self.persist_path, "r") as f:
                data = json.load(f)
            for node in data.get("nodes", []):
                node_id = node.pop("id")
                self.graph.add_node(node_id, **node)
            for edge in data.get("edges", []):
                from_id = edge.pop("from")
                to_id = edge.pop("to")
                self.graph.add_edge(from_id, to_id, **edge)
            logger.info("graph_loaded", nodes=self.graph.number_of_nodes())
        except Exception as e:
            logger.warning("graph_load_failed", error=str(e))