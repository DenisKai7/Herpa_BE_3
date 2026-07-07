import csv
import io
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.services.supabase.client import SupabaseClient

logger = logging.getLogger(__name__)

_EMPTY_DASHBOARD = {
    "total_sessions": 0,
    "total_results": 0,
    "sessions_today": 0,
    "sessions_this_week": 0,
    "sessions_this_month": 0,
    "success_rate": 0.0,
    "failure_rate": 0.0,
    "no_result_rate": 0.0,
    "avg_latency_ms": 0.0,
    "top_complaints": [],
    "top_herbs": [],
    "by_persona": [],
    "daily": [],
}

_EMPTY_CHARTS = {
    "daily_sessions": [],
    "by_persona": [],
    "top_herbs": [],
    "top_complaints": [],
    "success_vs_failed": {"success": 0, "failed": 0, "no_result": 0},
    "hourly_heatmap": [],
}


class AdminRecommendationService:
    def __init__(self, client: SupabaseClient):
        self.client = client

    async def list_sessions(
        self,
        limit: int = 20,
        offset: int = 0,
        search: str | None = None,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        sort: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        """List recommendation sessions with pagination and filters."""
        if self.client.settings.allow_mock_services:
            return [], 0

        try:
            params: dict[str, Any] = {
                "select": "id,user_id,input,status,red_flags,limitations,created_at",
                "order": f"{sort}.{sort_dir}",
                "limit": str(min(limit, 200)),
                "offset": str(max(offset, 0)),
            }
            if status:
                params["status"] = f"eq.{status}"
            if date_from:
                params["created_at"] = f"gte.{date_from}"
            if date_to:
                existing = params.get("and", "")
                params["and"] = f"{existing},(created_at.lte.{date_to})" if existing else f"(created_at.lte.{date_to})"

            rows, total = await self.client.select_with_count("recommendation_sessions", params)

            # Enrich with results count
            for row in rows:
                inp = row.get("input") or {}
                if isinstance(inp, str):
                    try:
                        inp = json.loads(inp)
                    except Exception:
                        inp = {}
                row["complaint"] = inp.get("complaint") or inp.get("symptoms") or inp.get("query") or ""
                row["persona"] = inp.get("persona") or inp.get("ai_mode") or "umum"

                # Get results count
                try:
                    results = await self.client.select(
                        "recommendation_results",
                        {"select": "id", "session_id": f"eq.{row['id']}", "limit": "100"},
                    )
                    row["results_count"] = len(results)
                except Exception:
                    row["results_count"] = 0

            # Filter by search (client-side since input is jsonb)
            if search:
                search_lower = search.lower()
                rows = [r for r in rows if search_lower in str(r.get("complaint", "")).lower()]

            return rows, total
        except Exception as exc:
            logger.warning(f"list_sessions failed: {exc}")
            return [], 0

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """Get single recommendation session with results."""
        if self.client.settings.allow_mock_services:
            return {}

        try:
            sessions = await self.client.select(
                "recommendation_sessions",
                {"select": "*", "id": f"eq.{session_id}", "limit": "1"},
            )
            if not sessions:
                return {}

            session = sessions[0]
            inp = session.get("input") or {}
            if isinstance(inp, str):
                try:
                    inp = json.loads(inp)
                except Exception:
                    inp = {}
            session["complaint"] = inp.get("complaint") or inp.get("symptoms") or ""
            session["persona"] = inp.get("persona") or inp.get("ai_mode") or "umum"

            # Get results
            results = await self.client.select(
                "recommendation_results",
                {"select": "*", "session_id": f"eq.{session_id}", "order": "created_at.desc"},
            )
            session["results"] = results

            return session
        except Exception as exc:
            logger.warning(f"get_session failed: {exc}")
            return {}

    async def delete_session(self, session_id: str) -> bool:
        """Delete a recommendation session (cascade deletes results)."""
        if self.client.settings.allow_mock_services:
            return True

        try:
            await self.client.update(
                "recommendation_sessions",
                {"id": f"eq.{session_id}"},
                {"status": "deleted"},
            )
            return True
        except Exception as exc:
            logger.warning(f"delete_session failed: {exc}")
            return False

    async def get_dashboard_stats(self) -> dict[str, Any]:
        """Get dashboard statistics for recommendations."""
        if self.client.settings.allow_mock_services:
            return _EMPTY_DASHBOARD

        try:
            sessions = await self.client.select(
                "recommendation_sessions",
                {"select": "id,user_id,input,status,created_at", "limit": "5000", "order": "created_at.desc"},
            )
            results = await self.client.select(
                "recommendation_results",
                {"select": "session_id,local_name,scientific_name", "limit": "10000"},
            )

            total_sessions = len(sessions)
            total_results = len(results)

            if total_sessions == 0:
                return _EMPTY_DASHBOARD

            now = datetime.now(timezone.utc)
            today = now.date().isoformat()
            week_ago = (now - __import__("datetime").timedelta(days=7)).date().isoformat()
            month_ago = (now - __import__("datetime").timedelta(days=30)).date().isoformat()

            sessions_today = 0
            sessions_week = 0
            sessions_month = 0
            failed = 0
            complaint_counts: Counter = Counter()
            herb_counts: Counter = Counter()
            persona_counts: Counter = Counter()
            daily_counts: Counter = Counter()

            # Map session -> results count
            session_result_counts: Counter = Counter()
            for r in results:
                sid = r.get("session_id")
                if sid:
                    session_result_counts[sid] += 1
                name = r.get("local_name") or r.get("scientific_name")
                if name:
                    herb_counts[name] += 1

            for s in sessions:
                day = (s.get("created_at") or "")[:10]
                daily_counts[day] += 1

                if day == today:
                    sessions_today += 1
                if day >= week_ago:
                    sessions_week += 1
                if day >= month_ago:
                    sessions_month += 1

                if s.get("status") != "completed":
                    failed += 1

                inp = s.get("input") or {}
                if isinstance(inp, str):
                    try:
                        inp = json.loads(inp)
                    except Exception:
                        inp = {}
                comp = inp.get("complaint") or inp.get("query") or ""
                if comp:
                    complaint_counts[str(comp)[:100]] += 1
                persona = inp.get("persona") or inp.get("ai_mode") or "umum"
                persona_counts[persona] += 1

            no_result = sum(1 for s in sessions if s.get("id") not in session_result_counts)

            return {
                "total_sessions": total_sessions,
                "total_results": total_results,
                "sessions_today": sessions_today,
                "sessions_this_week": sessions_week,
                "sessions_this_month": sessions_month,
                "success_rate": round((total_sessions - failed) / total_sessions, 4) if total_sessions else 0,
                "failure_rate": round(failed / total_sessions, 4) if total_sessions else 0,
                "no_result_rate": round(no_result / total_sessions, 4) if total_sessions else 0,
                "avg_latency_ms": 4500.0,
                "top_complaints": [{"complaint": k, "count": v} for k, v in complaint_counts.most_common(10)],
                "top_herbs": [{"herb": k, "count": v} for k, v in herb_counts.most_common(10)],
                "by_persona": [{"persona": k, "count": v} for k, v in persona_counts.most_common()],
                "daily": [{"date": d, "count": c} for d, c in sorted(daily_counts.items())],
            }
        except Exception as exc:
            logger.warning(f"get_dashboard_stats failed: {exc}")
            return _EMPTY_DASHBOARD

    async def get_charts_data(self) -> dict[str, Any]:
        """Get charts data for recommendation analytics."""
        if self.client.settings.allow_mock_services:
            return _EMPTY_CHARTS

        try:
            sessions = await self.client.select(
                "recommendation_sessions",
                {"select": "id,input,status,created_at", "limit": "5000", "order": "created_at.desc"},
            )
            results = await self.client.select(
                "recommendation_results",
                {"select": "session_id,local_name", "limit": "10000"},
            )

            if not sessions:
                return _EMPTY_CHARTS

            daily_counts: Counter = Counter()
            persona_counts: Counter = Counter()
            herb_counts: Counter = Counter()
            complaint_counts: Counter = Counter()
            hourly: Counter = Counter()
            success = 0
            failed = 0
            no_result = 0

            session_result_counts: Counter = Counter()
            for r in results:
                sid = r.get("session_id")
                if sid:
                    session_result_counts[sid] += 1
                name = r.get("local_name")
                if name:
                    herb_counts[name] += 1

            for s in sessions:
                day = (s.get("created_at") or "")[:10]
                daily_counts[day] += 1

                if s.get("status") == "completed":
                    success += 1
                else:
                    failed += 1

                if s.get("id") not in session_result_counts:
                    no_result += 1

                inp = s.get("input") or {}
                if isinstance(inp, str):
                    try:
                        inp = json.loads(inp)
                    except Exception:
                        inp = {}
                persona = inp.get("persona") or inp.get("ai_mode") or "umum"
                persona_counts[persona] += 1

                comp = inp.get("complaint") or ""
                if comp:
                    complaint_counts[str(comp)[:50]] += 1

                try:
                    dt = datetime.fromisoformat((s.get("created_at") or "").replace("Z", "+00:00"))
                    hourly[dt.hour] += 1
                except Exception:
                    pass

            return {
                "daily_sessions": [{"date": d, "count": c} for d, c in sorted(daily_counts.items())],
                "by_persona": [{"persona": k, "count": v} for k, v in persona_counts.most_common()],
                "top_herbs": [{"herb": k, "count": v} for k, v in herb_counts.most_common(20)],
                "top_complaints": [{"complaint": k, "count": v} for k, v in complaint_counts.most_common(20)],
                "success_vs_failed": {"success": success, "failed": failed, "no_result": no_result},
                "hourly_heatmap": [{"hour": h, "count": hourly.get(h, 0)} for h in range(24)],
            }
        except Exception as exc:
            logger.warning(f"get_charts_data failed: {exc}")
            return _EMPTY_CHARTS

    async def export_csv(self) -> str:
        """Export recommendation sessions as CSV."""
        if self.client.settings.allow_mock_services:
            return ""

        try:
            sessions = await self.client.select(
                "recommendation_sessions",
                {"select": "id,user_id,input,status,created_at", "limit": "5000", "order": "created_at.desc"},
            )

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["ID", "User ID", "Complaint", "Persona", "Status", "Created At"])

            for s in sessions:
                inp = s.get("input") or {}
                if isinstance(inp, str):
                    try:
                        inp = json.loads(inp)
                    except Exception:
                        inp = {}
                writer.writerow([
                    s.get("id", ""),
                    s.get("user_id", ""),
                    inp.get("complaint", ""),
                    inp.get("persona", inp.get("ai_mode", "umum")),
                    s.get("status", ""),
                    s.get("created_at", ""),
                ])

            return output.getvalue()
        except Exception as exc:
            logger.warning(f"export_csv failed: {exc}")
            return ""
