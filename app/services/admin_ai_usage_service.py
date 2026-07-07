import csv
import io
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.core.exceptions import NotFoundError
from app.services.supabase.client import SupabaseClient

logger = logging.getLogger(__name__)

# Default empty responses for when tables/columns don't exist yet
_EMPTY_DASHBOARD = {
    "total_requests": 0,
    "total_tokens_input": 0,
    "total_tokens_output": 0,
    "total_tokens": 0,
    "active_users": 0,
    "error_rate": 0.0,
    "avg_latency_ms": 0.0,
    "active_models": 0,
    "active_personas": 0,
}

_EMPTY_CHARTS = {
    "daily_requests": [],
    "daily_tokens": [],
    "by_persona": [],
    "by_model": [],
    "hourly_heatmap": [],
    "top_users": [],
    "top_endpoints": [],
    "error_analytics": {"by_endpoint": [], "by_model": [], "by_day": []},
    "latency_stats": {"min": 0, "max": 0, "avg": 0, "median": 0, "p95": 0},
    "cost_estimation": {"total_tokens": 0, "total_latency_ms": 0, "throughput_tokens_per_sec": 0, "provider": "local"},
}


class AdminAIUsageService:
    def __init__(self, client: SupabaseClient):
        self.client = client

    async def _select_safe(self, table: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Select with fallback if deleted_at column doesn't exist yet."""
        try:
            return await self.client.select(table, params)
        except Exception as exc:
            error_msg = str(exc).lower()
            if "deleted_at" in error_msg or "column" in error_msg:
                # Migration not applied yet - retry without deleted_at filter
                fallback = {k: v for k, v in params.items() if k != "deleted_at"}
                logger.warning("deleted_at column missing, retrying without filter")
                try:
                    return await self.client.select(table, fallback)
                except Exception:
                    return []
            return []

    async def list_logs(
        self,
        limit: int = 20,
        offset: int = 0,
        search: str | None = None,
        user_id: str | None = None,
        persona: str | None = None,
        model_name: str | None = None,
        endpoint: str | None = None,
        provider: str | None = None,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        sort: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        """List AI usage logs with pagination, filtering, and sorting."""
        if self.client.settings.allow_mock_services:
            return [], 0

        params: dict[str, Any] = {
            "select": "id,user_id,request_id,model_name,input_tokens,output_tokens,latency_ms,success,error_code,persona,endpoint,provider,created_at",
            "order": f"{sort}.{sort_dir}",
            "limit": str(min(limit, 200)),
            "offset": str(max(offset, 0)),
            "deleted_at": "is.null",
        }

        if search:
            safe = search.replace("%", "").replace("(", "").replace(")", "")
            params["or"] = f"(model_name.ilike.%{safe}%,persona.ilike.%{safe}%,endpoint.ilike.%{safe}%,error_code.ilike.%{safe}%)"
        if user_id:
            params["user_id"] = f"eq.{user_id}"
        if persona:
            params["persona"] = f"eq.{persona}"
        if model_name:
            params["model_name"] = f"eq.{model_name}"
        if endpoint:
            params["endpoint"] = f"eq.{endpoint}"
        if provider:
            params["provider"] = f"eq.{provider}"
        if status:
            if status == "success":
                params["success"] = "eq.true"
            elif status == "error":
                params["success"] = "eq.false"
        if date_from:
            params["created_at"] = f"gte.{date_from}"
        if date_to:
            # Use PostgREST and filter for date_to
            existing = params.get("and", "")
            date_filter = f"(created_at.lte.{date_to})"
            params["and"] = f"{existing},{date_filter}" if existing else date_filter

        try:
            rows, total = await self.client.select_with_count("model_usage_events", params)
            return rows, total
        except Exception as exc:
            logger.warning(f"list_logs failed (migration may not be applied): {exc}")
            return [], 0

    async def get_log(self, log_id: int) -> dict[str, Any]:
        """Get single AI usage log detail."""
        if self.client.settings.allow_mock_services:
            raise NotFoundError("Log tidak ditemukan.")

        try:
            rows = await self._select_safe(
                "model_usage_events",
                {"select": "*", "id": f"eq.{log_id}", "deleted_at": "is.null", "limit": "1"},
            )
        except Exception:
            rows = []
        if not rows:
            raise NotFoundError("Log tidak ditemukan.")
        return rows[0]

    async def soft_delete(self, log_id: int, admin_id: str) -> dict[str, Any]:
        """Soft delete a single AI usage log."""
        if self.client.settings.allow_mock_services:
            return {"id": log_id, "deleted": True}

        log = await self.get_log(log_id)
        now = datetime.now(timezone.utc).isoformat()
        rows = await self.client.update(
            "model_usage_events",
            {"id": f"eq.{log_id}"},
            {"deleted_at": now, "deleted_by": admin_id},
        )
        return rows[0] if rows else log

    async def bulk_delete(self, ids: list[int], admin_id: str) -> int:
        """Bulk soft delete AI usage logs by IDs."""
        if self.client.settings.allow_mock_services:
            return len(ids)

        now = datetime.now(timezone.utc).isoformat()
        count = 0
        for log_id in ids:
            try:
                await self.client.update(
                    "model_usage_events",
                    {"id": f"eq.{log_id}", "deleted_at": "is.null"},
                    {"deleted_at": now, "deleted_by": admin_id},
                )
                count += 1
            except Exception as exc:
                logger.warning(f"Failed to delete log {log_id}: {exc}")
        return count

    async def delete_by_filter(
        self,
        admin_id: str,
        user_id: str | None = None,
        persona: str | None = None,
        model_name: str | None = None,
        endpoint: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        status: str | None = None,
    ) -> int:
        """Delete AI usage logs by filter criteria."""
        if self.client.settings.allow_mock_services:
            return 0

        params: dict[str, Any] = {"select": "id", "deleted_at": "is.null", "limit": "10000"}
        if user_id:
            params["user_id"] = f"eq.{user_id}"
        if persona:
            params["persona"] = f"eq.{persona}"
        if model_name:
            params["model_name"] = f"eq.{model_name}"
        if endpoint:
            params["endpoint"] = f"eq.{endpoint}"
        if status:
            if status == "success":
                params["success"] = "eq.true"
            elif status == "error":
                params["success"] = "eq.false"
        if date_from:
            params["created_at"] = f"gte.{date_from}"
        if date_to:
            existing = params.get("and", "")
            params["and"] = f"{existing},(created_at.lte.{date_to})" if existing else f"(created_at.lte.{date_to})"

        try:
            rows = await self._select_safe("model_usage_events", params)
        except Exception as exc:
            logger.warning(f"delete_by_filter query failed: {exc}")
            return 0
        ids = [r["id"] for r in rows]
        if not ids:
            return 0
        return await self.bulk_delete(ids, admin_id)

    async def get_dashboard_stats(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict[str, Any]:
        """Get dashboard statistics for AI usage."""
        if self.client.settings.allow_mock_services:
            return _EMPTY_DASHBOARD

        params: dict[str, Any] = {
            "select": "user_id,model_name,persona,input_tokens,output_tokens,latency_ms,success,created_at",
            "deleted_at": "is.null",
            "limit": "10000",
        }
        if date_from:
            params["created_at"] = f"gte.{date_from}"
        if date_to:
            existing = params.get("and", "")
            params["and"] = f"{existing},(created_at.lte.{date_to})" if existing else f"(created_at.lte.{date_to})"

        try:
            rows = await self._select_safe("model_usage_events", params)
        except Exception as exc:
            logger.warning(f"get_dashboard_stats query failed: {exc}")
            return _EMPTY_DASHBOARD

        total = len(rows)
        if total == 0:
            return {
                "total_requests": 0,
                "total_tokens_input": 0,
                "total_tokens_output": 0,
                "total_tokens": 0,
                "active_users": 0,
                "error_rate": 0.0,
                "avg_latency_ms": 0.0,
                "active_models": 0,
                "active_personas": 0,
            }

        total_input = sum(r.get("input_tokens") or 0 for r in rows)
        total_output = sum(r.get("output_tokens") or 0 for r in rows)
        errors = sum(1 for r in rows if not r.get("success", True))
        total_latency = sum(r.get("latency_ms") or 0 for r in rows)
        unique_users = len(set(r.get("user_id") for r in rows if r.get("user_id")))
        unique_models = len(set(r.get("model_name") for r in rows if r.get("model_name")))
        unique_personas = len(set(r.get("persona") for r in rows if r.get("persona")))

        return {
            "total_requests": total,
            "total_tokens_input": total_input,
            "total_tokens_output": total_output,
            "total_tokens": total_input + total_output,
            "active_users": unique_users,
            "error_rate": round(errors / total, 4) if total > 0 else 0.0,
            "avg_latency_ms": round(total_latency / total, 2) if total > 0 else 0.0,
            "active_models": unique_models,
            "active_personas": unique_personas,
        }

    async def get_charts_data(
        self,
        days: int = 30,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict[str, Any]:
        """Get charts data for AI usage dashboard."""
        if self.client.settings.allow_mock_services:
            return _EMPTY_CHARTS

        params: dict[str, Any] = {
            "select": "user_id,model_name,persona,endpoint,input_tokens,output_tokens,latency_ms,success,error_code,created_at",
            "deleted_at": "is.null",
            "limit": "10000",
            "order": "created_at.desc",
        }
        if date_from:
            params["created_at"] = f"gte.{date_from}"
        if date_to:
            existing = params.get("and", "")
            params["and"] = f"{existing},(created_at.lte.{date_to})" if existing else f"(created_at.lte.{date_to})"

        try:
            rows = await self._select_safe("model_usage_events", params)
        except Exception as exc:
            logger.warning(f"get_charts_data query failed: {exc}")
            return _EMPTY_CHARTS

        # Daily requests (last N days)
        daily_req: Counter[str] = Counter()
        daily_tok: Counter[str] = Counter()
        persona_counter: Counter[str] = Counter()
        model_counter: Counter[str] = Counter()
        hourly: Counter[int] = Counter()
        user_counter: Counter[str] = Counter()
        endpoint_counter: Counter[str] = Counter()
        errors_by_endpoint: Counter[str] = Counter()
        errors_by_model: Counter[str] = Counter()
        errors_by_day: Counter[str] = Counter()
        latencies: list[int] = []

        for r in rows:
            day = (r.get("created_at") or "")[:10]
            daily_req[day] += 1
            daily_tok[day] += (r.get("input_tokens") or 0) + (r.get("output_tokens") or 0)
            persona_counter[r.get("persona") or "unknown"] += 1
            model_counter[r.get("model_name") or "unknown"] += 1
            endpoint_counter[r.get("endpoint") or "unknown"] += 1

            if r.get("user_id"):
                user_counter[r["user_id"]] += 1

            lat = r.get("latency_ms") or 0
            latencies.append(lat)

            if not r.get("success", True):
                errors_by_endpoint[r.get("endpoint") or "unknown"] += 1
                errors_by_model[r.get("model_name") or "unknown"] += 1
                errors_by_day[day] += 1

            # Extract hour from created_at
            try:
                dt = datetime.fromisoformat(r.get("created_at", "").replace("Z", "+00:00"))
                hourly[dt.hour] += 1
            except Exception:
                pass

        # Format daily requests
        daily_requests = [{"date": d, "requests": c} for d, c in sorted(daily_req.items())]
        daily_tokens = [{"date": d, "tokens": c} for d, c in sorted(daily_tok.items())]

        # Format by persona
        by_persona = [{"persona": p, "count": c} for p, c in persona_counter.most_common()]
        by_model = [{"model": m, "count": c} for m, c in model_counter.most_common()]

        # Format hourly heatmap
        hourly_heatmap = [{"hour": h, "count": hourly.get(h, 0)} for h in range(24)]

        # Top users
        top_users = [{"user_id": u, "count": c} for u, c in user_counter.most_common(10)]

        # Top endpoints
        top_endpoints = [{"endpoint": e, "count": c} for e, c in endpoint_counter.most_common()]

        # Error analytics
        error_analytics = {
            "by_endpoint": [{"endpoint": e, "errors": c} for e, c in errors_by_endpoint.most_common()],
            "by_model": [{"model": m, "errors": c} for m, c in errors_by_model.most_common()],
            "by_day": [{"date": d, "errors": c} for d, c in sorted(errors_by_day.items())],
        }

        # Latency stats
        latencies.sort()
        n = len(latencies)
        latency_stats = {
            "min": latencies[0] if n > 0 else 0,
            "max": latencies[-1] if n > 0 else 0,
            "avg": round(sum(latencies) / n, 2) if n > 0 else 0,
            "median": latencies[n // 2] if n > 0 else 0,
            "p95": latencies[int(n * 0.95)] if n > 0 else 0,
        }

        # Cost estimation (local LLM: token throughput)
        total_tokens = sum((r.get("input_tokens") or 0) + (r.get("output_tokens") or 0) for r in rows)
        total_latency = sum(r.get("latency_ms") or 0 for r in rows)
        cost_estimation = {
            "total_tokens": total_tokens,
            "total_latency_ms": total_latency,
            "throughput_tokens_per_sec": round(total_tokens / (total_latency / 1000), 2) if total_latency > 0 else 0,
            "provider": "local",
        }

        return {
            "daily_requests": daily_requests,
            "daily_tokens": daily_tokens,
            "by_persona": by_persona,
            "by_model": by_model,
            "hourly_heatmap": hourly_heatmap,
            "top_users": top_users,
            "top_endpoints": top_endpoints,
            "error_analytics": error_analytics,
            "latency_stats": latency_stats,
            "cost_estimation": cost_estimation,
        }

    async def export_csv(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        user_id: str | None = None,
        persona: str | None = None,
        model_name: str | None = None,
        endpoint: str | None = None,
        status: str | None = None,
    ) -> str:
        """Export AI usage logs as CSV string."""
        params: dict[str, Any] = {
            "select": "id,user_id,request_id,model_name,input_tokens,output_tokens,latency_ms,success,error_code,persona,endpoint,provider,created_at",
            "deleted_at": "is.null",
            "limit": "10000",
            "order": "created_at.desc",
        }
        if user_id:
            params["user_id"] = f"eq.{user_id}"
        if persona:
            params["persona"] = f"eq.{persona}"
        if model_name:
            params["model_name"] = f"eq.{model_name}"
        if endpoint:
            params["endpoint"] = f"eq.{endpoint}"
        if status:
            if status == "success":
                params["success"] = "eq.true"
            elif status == "error":
                params["success"] = "eq.false"
        if date_from:
            params["created_at"] = f"gte.{date_from}"
        if date_to:
            existing = params.get("and", "")
            params["and"] = f"{existing},(created_at.lte.{date_to})" if existing else f"(created_at.lte.{date_to})"

        rows = await self.client.select("model_usage_events", params)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "User ID", "Request ID", "Model", "Input Tokens", "Output Tokens",
            "Total Tokens", "Latency (ms)", "Status", "Error Code", "Persona",
            "Endpoint", "Provider", "Created At",
        ])
        for r in rows:
            total = (r.get("input_tokens") or 0) + (r.get("output_tokens") or 0)
            writer.writerow([
                r.get("id"),
                r.get("user_id", ""),
                r.get("request_id", ""),
                r.get("model_name", ""),
                r.get("input_tokens", 0),
                r.get("output_tokens", 0),
                total,
                r.get("latency_ms", 0),
                "success" if r.get("success", True) else "error",
                r.get("error_code", ""),
                r.get("persona", ""),
                r.get("endpoint", ""),
                r.get("provider", "local"),
                r.get("created_at", ""),
            ])
        return output.getvalue()

    async def export_excel(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        user_id: str | None = None,
        persona: str | None = None,
        model_name: str | None = None,
        endpoint: str | None = None,
        status: str | None = None,
    ) -> bytes:
        """Export AI usage logs as Excel bytes."""
        try:
            import openpyxl
        except ImportError:
            raise ImportError("openpyxl is required for Excel export. Install with: pip install openpyxl")

        params: dict[str, Any] = {
            "select": "id,user_id,request_id,model_name,input_tokens,output_tokens,latency_ms,success,error_code,persona,endpoint,provider,created_at",
            "deleted_at": "is.null",
            "limit": "10000",
            "order": "created_at.desc",
        }
        if user_id:
            params["user_id"] = f"eq.{user_id}"
        if persona:
            params["persona"] = f"eq.{persona}"
        if model_name:
            params["model_name"] = f"eq.{model_name}"
        if endpoint:
            params["endpoint"] = f"eq.{endpoint}"
        if status:
            if status == "success":
                params["success"] = "eq.true"
            elif status == "error":
                params["success"] = "eq.false"
        if date_from:
            params["created_at"] = f"gte.{date_from}"
        if date_to:
            existing = params.get("and", "")
            params["and"] = f"{existing},(created_at.lte.{date_to})" if existing else f"(created_at.lte.{date_to})"

        rows = await self.client.select("model_usage_events", params)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "AI Usage Logs"
        ws.append([
            "ID", "User ID", "Request ID", "Model", "Input Tokens", "Output Tokens",
            "Total Tokens", "Latency (ms)", "Status", "Error Code", "Persona",
            "Endpoint", "Provider", "Created At",
        ])
        for r in rows:
            total = (r.get("input_tokens") or 0) + (r.get("output_tokens") or 0)
            ws.append([
                r.get("id"),
                r.get("user_id", ""),
                r.get("request_id", ""),
                r.get("model_name", ""),
                r.get("input_tokens", 0),
                r.get("output_tokens", 0),
                total,
                r.get("latency_ms", 0),
                "success" if r.get("success", True) else "error",
                r.get("error_code", ""),
                r.get("persona", ""),
                r.get("endpoint", ""),
                r.get("provider", "local"),
                r.get("created_at", ""),
            ])

        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    async def export_pdf(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        user_id: str | None = None,
        persona: str | None = None,
        model_name: str | None = None,
        endpoint: str | None = None,
        status: str | None = None,
    ) -> bytes:
        """Export AI usage logs as PDF bytes."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        except ImportError:
            raise ImportError("reportlab is required for PDF export. Install with: pip install reportlab")

        params: dict[str, Any] = {
            "select": "id,user_id,request_id,model_name,input_tokens,output_tokens,latency_ms,success,error_code,persona,endpoint,provider,created_at",
            "deleted_at": "is.null",
            "limit": "5000",
            "order": "created_at.desc",
        }
        if user_id:
            params["user_id"] = f"eq.{user_id}"
        if persona:
            params["persona"] = f"eq.{persona}"
        if model_name:
            params["model_name"] = f"eq.{model_name}"
        if endpoint:
            params["endpoint"] = f"eq.{endpoint}"
        if status:
            if status == "success":
                params["success"] = "eq.true"
            elif status == "error":
                params["success"] = "eq.false"
        if date_from:
            params["created_at"] = f"gte.{date_from}"
        if date_to:
            existing = params.get("and", "")
            params["and"] = f"{existing},(created_at.lte.{date_to})" if existing else f"(created_at.lte.{date_to})"

        rows = await self.client.select("model_usage_events", params)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("HERPA - AI Usage Report", styles["Title"]))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
        elements.append(Spacer(1, 12))

        data = [["ID", "User ID", "Model", "Tokens", "Latency", "Status", "Persona", "Endpoint", "Created At"]]
        for r in rows:
            total = (r.get("input_tokens") or 0) + (r.get("output_tokens") or 0)
            data.append([
                str(r.get("id", "")),
                str(r.get("user_id", ""))[:8] + "..." if r.get("user_id") else "",
                str(r.get("model_name", "")),
                str(total),
                f"{r.get('latency_ms', 0)}ms",
                "OK" if r.get("success", True) else "ERR",
                str(r.get("persona", "")),
                str(r.get("endpoint", "")),
                str(r.get("created_at", ""))[:19],
            ])

        table = Table(data)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
        ]))
        elements.append(table)

        doc.build(elements)
        return buffer.getvalue()
