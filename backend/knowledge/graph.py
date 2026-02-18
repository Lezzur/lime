"""
Knowledge graph powered by NetworkX with JSON persistence.

The graph is a shared platform resource. Nodes are entities (person, project,
decision, topic) identified by their DB id. Edges carry a RelationType and
optional metadata (weight, meeting_id, timestamp).

Persistence: the graph serializes to a JSON file on every mutation and
rehydrates on startup. The SQLAlchemy tables are the source of truth for
entity attributes; the graph stores *relationships* only.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import networkx as nx
from networkx.readwrite import json_graph

from backend.config.settings import settings
from backend.models.knowledge import RelationType

logger = logging.getLogger(__name__)

GRAPH_FILE = settings.memory_dir / "knowledge_graph.json"


class KnowledgeGraph:
    """NetworkX-backed knowledge graph with typed edges."""

    def __init__(self, path: Optional[Path] = None):
        self._path = path or GRAPH_FILE
        self._graph = nx.MultiDiGraph()
        self._load()

    # ── Node operations ───────────────────────────────────────────────────────

    def add_entity(self, entity_id: str, entity_type: str, label: str):
        """Register an entity as a node. Idempotent."""
        if self._graph.has_node(entity_id):
            self._graph.nodes[entity_id]["label"] = label
        else:
            self._graph.add_node(
                entity_id,
                entity_type=entity_type,
                label=label,
                created_at=_now(),
            )
        self._save()

    def remove_entity(self, entity_id: str):
        if self._graph.has_node(entity_id):
            self._graph.remove_node(entity_id)
            self._save()

    def get_entity(self, entity_id: str) -> Optional[dict]:
        if self._graph.has_node(entity_id):
            return {"id": entity_id, **self._graph.nodes[entity_id]}
        return None

    # ── Edge operations ───────────────────────────────────────────────────────

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation: RelationType,
        meeting_id: str = "",
        weight: float = 1.0,
        metadata: Optional[dict] = None,
    ) -> bool:
        """Add a directed edge. Returns False if either node is missing."""
        if not self._graph.has_node(source_id) or not self._graph.has_node(target_id):
            logger.warning(
                f"Cannot add relation: missing node(s) {source_id} -> {target_id}"
            )
            return False

        # Check for duplicate edge of same type
        for _, _, data in self._graph.edges(source_id, data=True):
            if data.get("relation") == relation.value and _ == target_id:
                # Reinforce: bump weight
                data["weight"] = data.get("weight", 1.0) + weight
                data["last_seen"] = _now()
                if meeting_id:
                    meetings = data.get("meeting_ids", [])
                    if meeting_id not in meetings:
                        meetings.append(meeting_id)
                    data["meeting_ids"] = meetings
                self._save()
                return True

        edge_data = {
            "relation": relation.value,
            "weight": weight,
            "created_at": _now(),
            "last_seen": _now(),
        }
        if meeting_id:
            edge_data["meeting_ids"] = [meeting_id]
        if metadata:
            edge_data["metadata"] = metadata
        self._graph.add_edge(source_id, target_id, **edge_data)
        self._save()
        return True

    def remove_relation(self, source_id: str, target_id: str, relation: Optional[RelationType] = None):
        """Remove edge(s) between two nodes. If relation is None, removes all edges."""
        if not self._graph.has_edge(source_id, target_id):
            return
        if relation is None:
            self._graph.remove_edges_from(
                [(source_id, target_id, k) for k in self._graph[source_id][target_id]]
            )
        else:
            keys_to_remove = [
                k for k, data in self._graph[source_id][target_id].items()
                if data.get("relation") == relation.value
            ]
            for k in keys_to_remove:
                self._graph.remove_edge(source_id, target_id, key=k)
        self._save()

    # ── Query operations ──────────────────────────────────────────────────────

    def get_connections(self, entity_id: str) -> list[dict]:
        """Get all edges (in + out) for an entity."""
        if not self._graph.has_node(entity_id):
            return []
        connections = []
        # Outgoing
        for _, target, data in self._graph.edges(entity_id, data=True):
            connections.append({
                "source": entity_id,
                "target": target,
                "target_label": self._graph.nodes[target].get("label", ""),
                "target_type": self._graph.nodes[target].get("entity_type", ""),
                "direction": "outgoing",
                **data,
            })
        # Incoming
        for source, _, data in self._graph.in_edges(entity_id, data=True):
            connections.append({
                "source": source,
                "source_label": self._graph.nodes[source].get("label", ""),
                "source_type": self._graph.nodes[source].get("entity_type", ""),
                "target": entity_id,
                "direction": "incoming",
                **data,
            })
        return connections

    def get_neighbors(self, entity_id: str, relation: Optional[RelationType] = None) -> list[dict]:
        """Get neighboring nodes, optionally filtered by relation type."""
        if not self._graph.has_node(entity_id):
            return []
        neighbors = []
        seen = set()
        for _, target, data in self._graph.edges(entity_id, data=True):
            if relation and data.get("relation") != relation.value:
                continue
            if target not in seen:
                seen.add(target)
                neighbors.append({"id": target, **self._graph.nodes[target]})
        for source, _, data in self._graph.in_edges(entity_id, data=True):
            if relation and data.get("relation") != relation.value:
                continue
            if source not in seen:
                seen.add(source)
                neighbors.append({"id": source, **self._graph.nodes[source]})
        return neighbors

    def get_entities_by_type(self, entity_type: str) -> list[dict]:
        """List all nodes of a given type."""
        return [
            {"id": nid, **data}
            for nid, data in self._graph.nodes(data=True)
            if data.get("entity_type") == entity_type
        ]

    def get_subgraph_for_meeting(self, meeting_id: str) -> dict:
        """Extract nodes and edges that reference a specific meeting."""
        nodes = set()
        edges = []
        for u, v, data in self._graph.edges(data=True):
            if meeting_id in data.get("meeting_ids", []):
                nodes.add(u)
                nodes.add(v)
                edges.append({"source": u, "target": v, **data})
        return {
            "nodes": [{"id": n, **self._graph.nodes[n]} for n in nodes],
            "edges": edges,
        }

    def stats(self) -> dict:
        return {
            "total_nodes": self._graph.number_of_nodes(),
            "total_edges": self._graph.number_of_edges(),
            "people": len(self.get_entities_by_type("person")),
            "projects": len(self.get_entities_by_type("project")),
            "decisions": len(self.get_entities_by_type("decision")),
            "topics": len(self.get_entities_by_type("topic")),
        }

    def export(self) -> dict:
        """Full graph as serializable dict (for API responses)."""
        return json_graph.node_link_data(self._graph)

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save(self):
        data = json_graph.node_link_data(self._graph)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def _load(self):
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                self._graph = json_graph.node_link_graph(raw, directed=True, multigraph=True)
                logger.info(
                    f"Knowledge graph loaded: {self._graph.number_of_nodes()} nodes, "
                    f"{self._graph.number_of_edges()} edges"
                )
            except (json.JSONDecodeError, Exception) as e:
                logger.error(f"Failed to load knowledge graph: {e}. Starting fresh.")
                self._graph = nx.MultiDiGraph()
        else:
            logger.info("No existing knowledge graph found. Starting fresh.")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# Module-level singleton
knowledge_graph = KnowledgeGraph()
