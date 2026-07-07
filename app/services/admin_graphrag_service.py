import csv
import io
import json
import logging
import time
from typing import Any

from app.core.exceptions import AppError, NotFoundError
from app.graph.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class AdminGraphRAGService:
    """Admin service for Knowledge Graph management via Neo4j."""

    def __init__(self, neo4j: Neo4jClient):
        self.neo4j = neo4j

    # ── Dashboard ──

    async def get_dashboard(self) -> dict[str, Any]:
        """Get comprehensive graph statistics."""
        if self.neo4j.driver is None:
            return self._empty_dashboard()

        start = time.perf_counter()
        try:
            cypher = """
            CALL {
                MATCH (n) RETURN count(n) AS total_nodes
            }
            CALL {
                MATCH ()-[r]->() RETURN count(r) AS total_relationships
            }
            CALL {
                MATCH (n) RETURN count(DISTINCT labels(n)[0]) AS total_labels
            }
            CALL {
                MATCH (h:Herb) RETURN count(h) AS herb_count
            }
            CALL {
                MATCH (c:Compound) RETURN count(c) AS compound_count
            }
            CALL {
                MATCH (t:TraditionalUse) RETURN count(t) AS traditional_use_count
            }
            CALL {
                MATCH (p:PreparationMethod) RETURN count(p) AS preparation_method_count
            }
            CALL {
                MATCH (u:UsageGuideline) RETURN count(u) AS usage_guideline_count
            }
            CALL {
                MATCH (sw:SafetyWarning) RETURN count(sw) AS safety_warning_count
            }
            CALL {
                MATCH (s:Source) RETURN count(s) AS source_count
            }
            CALL {
                MATCH (b:Benefit) RETURN count(b) AS benefit_count
            }
            CALL {
                MATCH (sym:Symptom) RETURN count(sym) AS symptom_count
            }
            CALL {
                MATCH (f:Family) RETURN count(f) AS family_count
            }
            RETURN total_nodes, total_relationships, total_labels,
                   herb_count, compound_count, traditional_use_count,
                   preparation_method_count, usage_guideline_count,
                   safety_warning_count, source_count, benefit_count,
                   symptom_count, family_count
            """
            records = await self.neo4j.read(cypher)
            latency_ms = int((time.perf_counter() - start) * 1000)

            if not records:
                return self._empty_dashboard()

            r = records[0]
            return {
                "status": "running",
                "total_nodes": r.get("total_nodes", 0),
                "total_relationships": r.get("total_relationships", 0),
                "total_labels": r.get("total_labels", 0),
                "herb_count": r.get("herb_count", 0),
                "compound_count": r.get("compound_count", 0),
                "traditional_use_count": r.get("traditional_use_count", 0),
                "preparation_method_count": r.get("preparation_method_count", 0),
                "usage_guideline_count": r.get("usage_guideline_count", 0),
                "safety_warning_count": r.get("safety_warning_count", 0),
                "source_count": r.get("source_count", 0),
                "benefit_count": r.get("benefit_count", 0),
                "symptom_count": r.get("symptom_count", 0),
                "family_count": r.get("family_count", 0),
                "neo4j_latency_ms": latency_ms,
            }
        except Exception as exc:
            logger.error(f"get_dashboard failed: {exc}")
            return self._empty_dashboard()

    def _empty_dashboard(self) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "total_nodes": 0,
            "total_relationships": 0,
            "total_labels": 0,
            "herb_count": 0,
            "compound_count": 0,
            "traditional_use_count": 0,
            "preparation_method_count": 0,
            "usage_guideline_count": 0,
            "safety_warning_count": 0,
            "source_count": 0,
            "benefit_count": 0,
            "symptom_count": 0,
            "family_count": 0,
            "neo4j_latency_ms": 0,
        }

    # ── Schema ──

    async def get_schema(self) -> dict[str, Any]:
        """Get graph schema: labels, relationship types, properties."""
        if self.neo4j.driver is None:
            return {"labels": [], "relationship_types": [], "properties": []}

        try:
            labels_records = await self.neo4j.read("CALL db.labels() YIELD label RETURN label")
            labels = [r["label"] for r in labels_records]

            rel_types_records = await self.neo4j.read("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
            rel_types = [r["relationshipType"] for r in rel_types_records]

            props_records = await self.neo4j.read("CALL db.propertyKeys() YIELD propertyKey RETURN propertyKey")
            properties = [r["propertyKey"] for r in props_records]

            return {
                "labels": sorted(labels),
                "relationship_types": sorted(rel_types),
                "properties": sorted(properties),
            }
        except Exception as exc:
            logger.error(f"get_schema failed: {exc}")
            return {"labels": [], "relationship_types": [], "properties": []}

    # ── Nodes ──

    async def list_nodes(
        self,
        label: str | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
        sort: str = "id",
        sort_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        """List nodes with optional label filter, search, pagination."""
        if self.neo4j.driver is None:
            return [], 0

        try:
            # Count total
            if label:
                safe_label = self._sanitize_label(label)
                count_cypher = f"MATCH (n:`{safe_label}`) RETURN count(n) AS total"
            else:
                count_cypher = "MATCH (n) RETURN count(n) AS total"

            count_records = await self.neo4j.read(count_cypher)
            total = count_records[0]["total"] if count_records else 0

            # Fetch nodes
            if label:
                safe_label = self._sanitize_label(label)
                if search:
                    safe_search = search.replace("'", "").replace('"', "")
                    cypher = f"""
                    MATCH (n:`{safe_label}`)
                    WHERE any(key IN keys(n) WHERE toLower(toString(n[key])) CONTAINS toLower($search))
                    RETURN id(n) AS neo4j_id, labels(n) AS labels, properties(n) AS properties
                    ORDER BY n.{self._sanitize_property(sort)} {sort_dir.upper()}
                    SKIP $offset LIMIT $limit
                    """
                    records = await self.neo4j.read(cypher, {"search": safe_search, "offset": offset, "limit": limit})
                else:
                    cypher = f"""
                    MATCH (n:`{safe_label}`)
                    RETURN id(n) AS neo4j_id, labels(n) AS labels, properties(n) AS properties
                    ORDER BY n.{self._sanitize_property(sort)} {sort_dir.upper()}
                    SKIP $offset LIMIT $limit
                    """
                    records = await self.neo4j.read(cypher, {"offset": offset, "limit": limit})
            else:
                if search:
                    safe_search = search.replace("'", "").replace('"', "")
                    cypher = """
                    MATCH (n)
                    WHERE any(key IN keys(n) WHERE toLower(toString(n[key])) CONTAINS toLower($search))
                    RETURN id(n) AS neo4j_id, labels(n) AS labels, properties(n) AS properties
                    ORDER BY id(n)
                    SKIP $offset LIMIT $limit
                    """
                    records = await self.neo4j.read(cypher, {"search": safe_search, "offset": offset, "limit": limit})
                else:
                    cypher = """
                    MATCH (n)
                    RETURN id(n) AS neo4j_id, labels(n) AS labels, properties(n) AS properties
                    ORDER BY id(n)
                    SKIP $offset LIMIT $limit
                    """
                    records = await self.neo4j.read(cypher, {"offset": offset, "limit": limit})

            nodes = []
            for r in records:
                props = r.get("properties", {})
                props["__neo4j_id"] = r.get("neo4j_id")
                props["__labels"] = r.get("labels", [])
                nodes.append(props)

            return nodes, total
        except Exception as exc:
            logger.error(f"list_nodes failed: {exc}")
            return [], 0

    async def get_node(self, node_id: int) -> dict[str, Any]:
        """Get single node with its relationships."""
        if self.neo4j.driver is None:
            raise NotFoundError("Neo4j tidak tersedia.")

        try:
            cypher = """
            MATCH (n) WHERE id(n) = $node_id
            OPTIONAL MATCH (n)-[r]->(m)
            WITH n, collect({
                rel_id: id(r),
                rel_type: type(r),
                properties: properties(r),
                target_id: id(m),
                target_labels: labels(m),
                target_name: coalesce(m.name, m.commonName, m.title, toString(id(m)))
            }) AS outgoing
            OPTIONAL MATCH (n)<-[r2]-(m2)
            WITH n, outgoing, collect({
                rel_id: id(r2),
                rel_type: type(r2),
                properties: properties(r2),
                source_id: id(m2),
                source_labels: labels(m2),
                source_name: coalesce(m2.name, m2.commonName, m2.title, toString(id(m2)))
            }) AS incoming
            RETURN id(n) AS neo4j_id, labels(n) AS labels, properties(n) AS properties,
                   outgoing, incoming
            """
            records = await self.neo4j.read(cypher, {"node_id": node_id})
            if not records:
                raise NotFoundError(f"Node {node_id} tidak ditemukan.")

            r = records[0]
            props = r.get("properties", {})
            props["__neo4j_id"] = r.get("neo4j_id")
            props["__labels"] = r.get("labels", [])
            props["__outgoing"] = r.get("outgoing", [])
            props["__incoming"] = r.get("incoming", [])
            return props
        except NotFoundError:
            raise
        except Exception as exc:
            logger.error(f"get_node failed: {exc}")
            raise AppError("GRAPH_ERROR", f"Gagal mengambil node: {exc}", 500)

    async def create_node(self, label: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Create a new node with given label and properties."""
        if self.neo4j.driver is None:
            raise AppError("GRAPH_ERROR", "Neo4j tidak tersedia.", 503)

        safe_label = self._sanitize_label(label)
        try:
            # Build SET clauses from properties
            set_clauses = []
            params = {}
            for key, value in properties.items():
                safe_key = self._sanitize_property(key)
                param_name = f"prop_{safe_key}"
                set_clauses.append(f"n.`{safe_key}` = ${param_name}")
                params[param_name] = value

            set_str = ", ".join(set_clauses) if set_clauses else ""
            if set_str:
                cypher = f"CREATE (n:`{safe_label}`) SET {set_str} RETURN id(n) AS neo4j_id, labels(n) AS labels, properties(n) AS properties"
            else:
                cypher = f"CREATE (n:`{safe_label}`) RETURN id(n) AS neo4j_id, labels(n) AS labels, properties(n) AS properties"

            records = await self.neo4j.write(cypher, params)
            if not records:
                raise AppError("GRAPH_ERROR", "Gagal membuat node.", 500)

            r = records[0]
            props = r.get("properties", {})
            props["__neo4j_id"] = r.get("neo4j_id")
            props["__labels"] = r.get("labels", [])
            return props
        except AppError:
            raise
        except Exception as exc:
            logger.error(f"create_node failed: {exc}")
            raise AppError("GRAPH_ERROR", f"Gagal membuat node: {exc}", 500)

    async def update_node(self, node_id: int, properties: dict[str, Any]) -> dict[str, Any]:
        """Update node properties."""
        if self.neo4j.driver is None:
            raise AppError("GRAPH_ERROR", "Neo4j tidak tersedia.", 503)

        try:
            set_clauses = []
            params = {"node_id": node_id}
            for key, value in properties.items():
                safe_key = self._sanitize_property(key)
                param_name = f"prop_{safe_key}"
                set_clauses.append(f"n.`{safe_key}` = ${param_name}")
                params[param_name] = value

            if not set_clauses:
                raise AppError("VALIDATION_ERROR", "Tidak ada property yang diubah.", 400)

            set_str = ", ".join(set_clauses)
            cypher = f"""
            MATCH (n) WHERE id(n) = $node_id
            SET {set_str}
            RETURN id(n) AS neo4j_id, labels(n) AS labels, properties(n) AS properties
            """
            records = await self.neo4j.write(cypher, params)
            if not records:
                raise NotFoundError(f"Node {node_id} tidak ditemukan.")

            r = records[0]
            props = r.get("properties", {})
            props["__neo4j_id"] = r.get("neo4j_id")
            props["__labels"] = r.get("labels", [])
            return props
        except (AppError, NotFoundError):
            raise
        except Exception as exc:
            logger.error(f"update_node failed: {exc}")
            raise AppError("GRAPH_ERROR", f"Gagal mengupdate node: {exc}", 500)

    async def delete_node(self, node_id: int) -> None:
        """Delete a node and all its relationships."""
        if self.neo4j.driver is None:
            raise AppError("GRAPH_ERROR", "Neo4j tidak tersedia.", 503)

        try:
            cypher = "MATCH (n) WHERE id(n) = $node_id DETACH DELETE n"
            await self.neo4j.write(cypher, {"node_id": node_id})
        except Exception as exc:
            logger.error(f"delete_node failed: {exc}")
            raise AppError("GRAPH_ERROR", f"Gagal menghapus node: {exc}", 500)

    async def bulk_delete_nodes(self, node_ids: list[int]) -> int:
        """Bulk delete nodes by IDs."""
        if self.neo4j.driver is None:
            return 0

        try:
            cypher = "MATCH (n) WHERE id(n) IN $node_ids DETACH DELETE n"
            await self.neo4j.write(cypher, {"node_ids": node_ids})
            return len(node_ids)
        except Exception as exc:
            logger.error(f"bulk_delete_nodes failed: {exc}")
            return 0

    # ── Relationships ──

    async def list_relationships(
        self,
        source_id: int | None = None,
        target_id: int | None = None,
        rel_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """List relationships with optional filters."""
        if self.neo4j.driver is None:
            return [], 0

        try:
            conditions = []
            params: dict[str, Any] = {"offset": offset, "limit": limit}

            if source_id is not None:
                conditions.append("id(a) = $source_id")
                params["source_id"] = source_id
            if target_id is not None:
                conditions.append("id(b) = $target_id")
                params["target_id"] = target_id
            if rel_type:
                safe_type = self._sanitize_label(rel_type)
                match_clause = f"MATCH (a)-[r:`{safe_type}`]->(b)"
            else:
                match_clause = "MATCH (a)-[r]->(b)"

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            # Count
            count_cypher = f"{match_clause} {where_clause} RETURN count(r) AS total"
            count_records = await self.neo4j.read(count_cypher, params)
            total = count_records[0]["total"] if count_records else 0

            # Fetch
            cypher = f"""
            {match_clause} {where_clause}
            RETURN id(r) AS rel_id, type(r) AS rel_type, properties(r) AS properties,
                   id(a) AS source_id, labels(a) AS source_labels,
                   coalesce(a.name, a.commonName, a.title, toString(id(a))) AS source_name,
                   id(b) AS target_id, labels(b) AS target_labels,
                   coalesce(b.name, b.commonName, b.title, toString(id(b))) AS target_name
            ORDER BY id(r)
            SKIP $offset LIMIT $limit
            """
            records = await self.neo4j.read(cypher, params)

            rels = []
            for r in records:
                rels.append({
                    "rel_id": r.get("rel_id"),
                    "rel_type": r.get("rel_type"),
                    "properties": r.get("properties", {}),
                    "source_id": r.get("source_id"),
                    "source_labels": r.get("source_labels", []),
                    "source_name": r.get("source_name", ""),
                    "target_id": r.get("target_id"),
                    "target_labels": r.get("target_labels", []),
                    "target_name": r.get("target_name", ""),
                })

            return rels, total
        except Exception as exc:
            logger.error(f"list_relationships failed: {exc}")
            return [], 0

    async def create_relationship(
        self,
        source_id: int,
        target_id: int,
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a relationship between two nodes."""
        if self.neo4j.driver is None:
            raise AppError("GRAPH_ERROR", "Neo4j tidak tersedia.", 503)

        safe_type = self._sanitize_label(rel_type)
        try:
            params: dict[str, Any] = {"source_id": source_id, "target_id": target_id}

            if properties:
                set_clauses = []
                for key, value in properties.items():
                    safe_key = self._sanitize_property(key)
                    param_name = f"prop_{safe_key}"
                    set_clauses.append(f"r.`{safe_key}` = ${param_name}")
                    params[param_name] = value
                set_str = " SET " + ", ".join(set_clauses)
            else:
                set_str = ""

            cypher = f"""
            MATCH (a), (b) WHERE id(a) = $source_id AND id(b) = $target_id
            CREATE (a)-[r:`{safe_type}`]->(b){set_str}
            RETURN id(r) AS rel_id, type(r) AS rel_type, properties(r) AS properties
            """
            records = await self.neo4j.write(cypher, params)
            if not records:
                raise AppError("GRAPH_ERROR", "Gagal membuat relationship.", 500)

            r = records[0]
            return {
                "rel_id": r.get("rel_id"),
                "rel_type": r.get("rel_type"),
                "properties": r.get("properties", {}),
            }
        except AppError:
            raise
        except Exception as exc:
            logger.error(f"create_relationship failed: {exc}")
            raise AppError("GRAPH_ERROR", f"Gagal membuat relationship: {exc}", 500)

    async def delete_relationship(self, rel_id: int) -> None:
        """Delete a relationship."""
        if self.neo4j.driver is None:
            raise AppError("GRAPH_ERROR", "Neo4j tidak tersedia.", 503)

        try:
            cypher = "MATCH ()-[r]->() WHERE id(r) = $rel_id DELETE r"
            await self.neo4j.write(cypher, {"rel_id": rel_id})
        except Exception as exc:
            logger.error(f"delete_relationship failed: {exc}")
            raise AppError("GRAPH_ERROR", f"Gagal menghapus relationship: {exc}", 500)

    # ── Search ──

    async def search_nodes(self, query: str, label: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        """Search nodes by name/content."""
        if self.neo4j.driver is None:
            return []

        safe_query = query.replace("'", "").replace('"', "")
        params = {"search": safe_query, "limit": limit}

        try:
            if label:
                safe_label = self._sanitize_label(label)
                cypher = f"""
                MATCH (n:`{safe_label}`)
                WHERE any(key IN keys(n) WHERE toLower(toString(n[key])) CONTAINS toLower($search))
                RETURN id(n) AS neo4j_id, labels(n) AS labels, properties(n) AS properties
                LIMIT $limit
                """
            else:
                cypher = """
                MATCH (n)
                WHERE any(key IN keys(n) WHERE toLower(toString(n[key])) CONTAINS toLower($search))
                RETURN id(n) AS neo4j_id, labels(n) AS labels, properties(n) AS properties
                LIMIT $limit
                """

            records = await self.neo4j.read(cypher, params)
            nodes = []
            for r in records:
                props = r.get("properties", {})
                props["__neo4j_id"] = r.get("neo4j_id")
                props["__labels"] = r.get("labels", [])
                nodes.append(props)
            return nodes
        except Exception as exc:
            logger.error(f"search_nodes failed: {exc}")
            return []

    # ── Graph Visualization ──

    async def get_graph_data(self, limit: int = 200, label: str | None = None) -> dict[str, Any]:
        """Get nodes and edges for graph visualization.

        Strategy: get a CONNECTED subgraph so we always have edges.
        Uses MATCH (a)-[r]->(b) to get nodes that actually have relationships.
        """
        if self.neo4j.driver is None:
            return {"nodes": [], "edges": []}

        try:
            # Get a connected subgraph: relationships first, then extract nodes
            if label:
                safe_label = self._sanitize_label(label)
                cypher = f"""
                MATCH (a:`{safe_label}`)-[r]->(b)
                WITH a, r, b LIMIT $limit
                RETURN collect(DISTINCT {{
                    id: id(a), labels: labels(a),
                    name: coalesce(a.name, a.commonName, a.title, toString(id(a)))
                }}) +
                collect(DISTINCT {{
                    id: id(b), labels: labels(b),
                    name: coalesce(b.name, b.commonName, b.title, toString(id(b)))
                }}) AS nodes,
                collect(DISTINCT {{
                    id: id(r), source: id(a), target: id(b), type: type(r),
                    source_name: coalesce(a.name, a.commonName, a.title, toString(id(a))),
                    target_name: coalesce(b.name, b.commonName, b.title, toString(id(b)))
                }}) AS edges
                """
            else:
                # Get diverse connected nodes across ALL labels
                cypher = """
                MATCH (a)-[r]->(b)
                WITH a, r, b LIMIT $limit
                WITH collect(DISTINCT {
                    id: id(a), labels: labels(a),
                    name: coalesce(a.name, a.commonName, a.title, toString(id(a)))
                }) AS nodes_a,
                collect(DISTINCT {
                    id: id(b), labels: labels(b),
                    name: coalesce(b.name, b.commonName, b.title, toString(id(b)))
                }) AS nodes_b,
                collect(DISTINCT {
                    id: id(r), source: id(a), target: id(b), type: type(r),
                    source_name: coalesce(a.name, a.commonName, a.title, toString(id(a))),
                    target_name: coalesce(b.name, b.commonName, b.title, toString(id(b)))
                }) AS edges
                RETURN nodes_a + nodes_b AS nodes, edges
                """

            records = await self.neo4j.read(cypher, {"limit": limit})
            if not records:
                return {"nodes": [], "edges": []}

            r = records[0]
            raw_nodes = r.get("nodes", [])
            raw_edges = r.get("edges", [])

            # Deduplicate nodes by id
            seen_ids: set[int] = set()
            nodes = []
            for n in raw_nodes:
                nid = n.get("id")
                if nid is not None and nid not in seen_ids:
                    seen_ids.add(nid)
                    nodes.append(n)

            # Filter edges to only include those with valid source and target
            valid_ids = seen_ids
            edges = [e for e in raw_edges if e.get("source") in valid_ids and e.get("target") in valid_ids]

            logger.info(
                "graph_data_result",
                extra={"node_count": len(nodes), "edge_count": len(edges),
                        "labels": list(set(l for n in nodes for l in n.get("labels", [])))},
            )

            return {"nodes": nodes, "edges": edges}
        except Exception as exc:
            logger.error(f"get_graph_data failed: {exc}")
            return {"nodes": [], "edges": []}

    async def expand_node(self, node_id: int, depth: int = 1) -> dict[str, Any]:
        """Expand a node's neighborhood for visualization."""
        if self.neo4j.driver is None:
            return {"nodes": [], "edges": []}

        try:
            cypher = f"""
            MATCH path = (n)-[*1..{depth}]-(m)
            WHERE id(n) = $node_id
            WITH nodes(path) AS ns, relationships(path) AS rs
            UNWIND ns AS node
            WITH collect(DISTINCT {{
                id: id(node),
                labels: labels(node),
                name: coalesce(node.name, node.commonName, node.title, toString(id(node)))
            }}) AS nodes, rs
            UNWIND rs AS rel
            RETURN nodes, collect(DISTINCT {{
                source: id(startNode(rel)),
                target: id(endNode(rel)),
                type: type(rel)
            }}) AS edges
            """
            records = await self.neo4j.read(cypher, {"node_id": node_id})
            if not records:
                return {"nodes": [], "edges": []}

            r = records[0]
            return {
                "nodes": r.get("nodes", []),
                "edges": r.get("edges", []),
            }
        except Exception as exc:
            logger.error(f"expand_node failed: {exc}")
            return {"nodes": [], "edges": []}

    # ── Export ──

    async def export_json(self, label: str | None = None, limit: int = 1000) -> dict[str, Any]:
        """Export nodes and relationships as JSON."""
        if self.neo4j.driver is None:
            return {"nodes": [], "relationships": []}

        try:
            if label:
                safe_label = self._sanitize_label(label)
                nodes_cypher = f"""
                MATCH (n:`{safe_label}`)
                RETURN id(n) AS id, labels(n) AS labels, properties(n) AS properties
                LIMIT $limit
                """
            else:
                nodes_cypher = """
                MATCH (n)
                RETURN id(n) AS id, labels(n) AS labels, properties(n) AS properties
                LIMIT $limit
                """

            nodes = await self.neo4j.read(nodes_cypher, {"limit": limit})
            node_ids = [n["id"] for n in nodes]

            rels_cypher = """
            MATCH (a)-[r]->(b)
            WHERE id(a) IN $node_ids AND id(b) IN $node_ids
            RETURN id(r) AS id, type(r) AS type, properties(r) AS properties,
                   id(a) AS source, id(b) AS target
            """
            rels = await self.neo4j.read(rels_cypher, {"node_ids": node_ids})

            return {
                "nodes": [{"id": n["id"], "labels": n["labels"], "properties": n["properties"]} for n in nodes],
                "relationships": [{"id": r["id"], "type": r["type"], "properties": r["properties"], "source": r["source"], "target": r["target"]} for r in rels],
            }
        except Exception as exc:
            logger.error(f"export_json failed: {exc}")
            return {"nodes": [], "relationships": []}

    async def export_csv(self, label: str | None = None, limit: int = 1000) -> str:
        """Export nodes as CSV string."""
        data = await self.export_json(label, limit)
        output = io.StringIO()

        if not data["nodes"]:
            return ""

        # Collect all property keys
        all_keys: set[str] = set()
        for node in data["nodes"]:
            all_keys.update(node.get("properties", {}).keys())

        headers = ["id", "labels"] + sorted(all_keys)
        writer = csv.writer(output)
        writer.writerow(headers)

        for node in data["nodes"]:
            props = node.get("properties", {})
            row = [node.get("id", ""), "|".join(node.get("labels", []))]
            for key in sorted(all_keys):
                row.append(props.get(key, ""))
            writer.writerow(row)

        return output.getvalue()

    # ── Helpers ──

    def _sanitize_label(self, label: str) -> str:
        """Sanitize label to prevent Cypher injection."""
        return "".join(c for c in label if c.isalnum() or c == "_")

    def _sanitize_property(self, prop: str) -> str:
        """Sanitize property name to prevent Cypher injection."""
        return "".join(c for c in prop if c.isalnum() or c == "_")
