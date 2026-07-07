import logging
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.api.dependencies.roles import require_admin
from app.api.dependencies.services import Services, get_services
from app.models.auth import CurrentUser
from app.models.graph_admin import (
    GraphBulkDelete,
    GraphNodeCreate,
    GraphNodeUpdate,
    GraphRelationshipCreate,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Admin GraphRAG"])


# ── Dashboard & Schema ──


@router.get("/api/admin/graphrag/dashboard")
async def graphrag_dashboard(
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Get comprehensive graph statistics."""
    return await services.admin_graphrag.get_dashboard()


@router.get("/api/admin/graphrag/schema")
async def graphrag_schema(
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Get graph schema: labels, relationship types, properties."""
    return await services.admin_graphrag.get_schema()


# ── Nodes ──


@router.get("/api/admin/graphrag/nodes")
async def list_nodes(
    label: str | None = Query(None),
    search: str | None = Query(None, max_length=200),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort: str = Query("id"),
    sort_dir: Literal["asc", "desc"] = Query("asc"),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """List nodes with optional label filter, search, pagination."""
    rows, total = await services.admin_graphrag.list_nodes(
        label=label, search=search, limit=limit, offset=offset, sort=sort, sort_dir=sort_dir,
    )
    return {"nodes": rows, "total": total, "limit": limit, "offset": offset}


@router.get("/api/admin/graphrag/nodes/{node_id}")
async def get_node(
    node_id: int,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Get single node with its relationships."""
    return await services.admin_graphrag.get_node(node_id)


@router.post("/api/admin/graphrag/nodes", status_code=201)
async def create_node(
    payload: GraphNodeCreate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Create a new node."""
    result = await services.admin_graphrag.create_node(payload.label, payload.properties)
    await services.admin.audit(
        admin.id, "graphrag.node.created", "neo4j", str(result.get("__neo4j_id")),
        None, {"label": payload.label, "properties": payload.properties},
        request.state.request_id,
    )
    return result


@router.put("/api/admin/graphrag/nodes/{node_id}")
async def update_node(
    node_id: int,
    payload: GraphNodeUpdate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Update node properties."""
    result = await services.admin_graphrag.update_node(node_id, payload.properties)
    await services.admin.audit(
        admin.id, "graphrag.node.updated", "neo4j", str(node_id),
        None, {"properties": payload.properties},
        request.state.request_id,
    )
    return result


@router.delete("/api/admin/graphrag/nodes/{node_id}")
async def delete_node(
    node_id: int,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Delete a node and all its relationships."""
    await services.admin_graphrag.delete_node(node_id)
    await services.admin.audit(
        admin.id, "graphrag.node.deleted", "neo4j", str(node_id),
        None, {"deleted": True},
        request.state.request_id,
    )
    return {"message": f"Node {node_id} berhasil dihapus."}


@router.post("/api/admin/graphrag/nodes/bulk-delete")
async def bulk_delete_nodes(
    payload: GraphBulkDelete,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Bulk delete nodes by IDs."""
    count = await services.admin_graphrag.bulk_delete_nodes(payload.node_ids)
    await services.admin.audit(
        admin.id, "graphrag.nodes.bulk_deleted", "neo4j", "bulk",
        None, {"node_ids": payload.node_ids, "deleted_count": count},
        request.state.request_id,
    )
    return {"message": f"{count} node berhasil dihapus.", "deleted_count": count}


# ── Relationships ──


@router.get("/api/admin/graphrag/relationships")
async def list_relationships(
    source_id: int | None = Query(None),
    target_id: int | None = Query(None),
    rel_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """List relationships with optional filters."""
    rows, total = await services.admin_graphrag.list_relationships(
        source_id=source_id, target_id=target_id, rel_type=rel_type,
        limit=limit, offset=offset,
    )
    return {"relationships": rows, "total": total, "limit": limit, "offset": offset}


@router.post("/api/admin/graphrag/relationships", status_code=201)
async def create_relationship(
    payload: GraphRelationshipCreate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Create a relationship between two nodes."""
    result = await services.admin_graphrag.create_relationship(
        payload.source_id, payload.target_id, payload.rel_type, payload.properties,
    )
    await services.admin.audit(
        admin.id, "graphrag.relationship.created", "neo4j", str(result.get("rel_id")),
        None, {"source": payload.source_id, "target": payload.target_id, "type": payload.rel_type},
        request.state.request_id,
    )
    return result


@router.delete("/api/admin/graphrag/relationships/{rel_id}")
async def delete_relationship(
    rel_id: int,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Delete a relationship."""
    await services.admin_graphrag.delete_relationship(rel_id)
    await services.admin.audit(
        admin.id, "graphrag.relationship.deleted", "neo4j", str(rel_id),
        None, {"deleted": True},
        request.state.request_id,
    )
    return {"message": f"Relationship {rel_id} berhasil dihapus."}


# ── Search ──


@router.get("/api/admin/graphrag/search")
async def search_nodes(
    q: str = Query(min_length=1, max_length=200),
    label: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Search nodes by name/content."""
    return await services.admin_graphrag.search_nodes(q, label=label, limit=limit)


# ── Graph Visualization ──


@router.get("/api/admin/graphrag/debug")
async def graph_debug(
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Debug endpoint to inspect graph state."""
    if services.neo4j.driver is None:
        return {"status": "neo4j_not_connected"}

    try:
        # Count nodes by label
        label_counts = await services.neo4j.read(
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC"
        )

        # Count relationships by type
        rel_counts = await services.neo4j.read(
            "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS count ORDER BY count DESC"
        )

        # Total counts
        total_nodes = await services.neo4j.read("MATCH (n) RETURN count(n) AS total")
        total_rels = await services.neo4j.read("MATCH ()-[r]->() RETURN count(r) AS total")

        return {
            "status": "ok",
            "total_nodes": total_nodes[0]["total"] if total_nodes else 0,
            "total_relationships": total_rels[0]["total"] if total_rels else 0,
            "labels": {r["label"]: r["count"] for r in label_counts},
            "relationship_types": {r["rel_type"]: r["count"] for r in rel_counts},
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@router.get("/api/admin/graphrag/graph")
async def get_graph_data(
    limit: int = Query(200, ge=1, le=1000),
    label: str | None = Query(None),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Get nodes and edges for graph visualization."""
    return await services.admin_graphrag.get_graph_data(limit=limit, label=label)


@router.get("/api/admin/graphrag/graph/expand/{node_id}")
async def expand_node(
    node_id: int,
    depth: int = Query(1, ge=1, le=3),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Expand a node's neighborhood for visualization."""
    return await services.admin_graphrag.expand_node(node_id, depth=depth)


# ── Export ──


@router.get("/api/admin/graphrag/export/json")
async def export_json(
    label: str | None = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Export nodes and relationships as JSON."""
    return await services.admin_graphrag.export_json(label=label, limit=limit)


@router.get("/api/admin/graphrag/export/csv")
async def export_csv(
    label: str | None = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Export nodes as CSV."""
    csv_content = await services.admin_graphrag.export_csv(label=label, limit=limit)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=graphrag_export.csv"},
    )
