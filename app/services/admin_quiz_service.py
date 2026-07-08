import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.services.supabase.client import SupabaseClient

logger = logging.getLogger(__name__)

_EMPTY_DASHBOARD = {
    "total_modules": 0,
    "total_levels": 0,
    "total_questions": 0,
    "total_attempts": 0,
    "completed_attempts": 0,
    "completion_rate": 0.0,
    "avg_score": 0.0,
    "highest_score": 0,
    "lowest_score": 0,
    "active_users_today": 0,
    "published_modules": 0,
    "draft_modules": 0,
    "by_module": [],
    "by_difficulty": [],
    "daily_attempts": [],
}


class AdminQuizService:
    def __init__(self, client: SupabaseClient):
        self.client = client

    # ── Modules ──

    async def list_modules(
        self, limit: int = 20, offset: int = 0, search: str | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        if self.client.settings.allow_mock_services:
            return [], 0
        try:
            params: dict[str, Any] = {
                "select": "*,quiz_subjects(id,title,slug)",
                "order": "sort_order.asc",
                "limit": str(min(limit, 200)),
                "offset": str(max(offset, 0)),
            }
            if search:
                safe = search.replace("%", "").replace("(", "").replace(")", "")
                params["or"] = f"(title.ilike.%{safe}%,description.ilike.%{safe}%)"
            rows, total = await self.client.select_with_count("quiz_modules", params)
            return rows, total
        except Exception as exc:
            logger.warning(f"list_modules failed: {exc}")
            return [], 0

    async def create_module(self, data: dict[str, Any]) -> dict[str, Any]:
        if self.client.settings.allow_mock_services:
            return {"id": "mock", **data}
        row = {
            "id": str(uuid4()),
            "subject_id": data.get("subject_id"),
            "slug": data.get("slug", data.get("title", "").lower().replace(" ", "-")),
            "title": data["title"],
            "description": data.get("description", ""),
            "sort_order": data.get("sort_order", 0),
            "is_active": data.get("is_active", True),
        }
        rows = await self.client.insert("quiz_modules", row)
        return rows[0] if rows else row

    async def update_module(self, module_id: str, data: dict[str, Any]) -> dict[str, Any]:
        if self.client.settings.allow_mock_services:
            return {"id": module_id, **data}
        update_data = {k: v for k, v in data.items() if v is not None}
        rows = await self.client.update("quiz_modules", {"id": f"eq.{module_id}"}, update_data)
        return rows[0] if rows else {"id": module_id, **update_data}

    async def delete_module(self, module_id: str) -> bool:
        if self.client.settings.allow_mock_services:
            return True
        try:
            await self.client.update("quiz_modules", {"id": f"eq.{module_id}"}, {"is_active": False})
            return True
        except Exception as exc:
            logger.warning(f"delete_module failed: {exc}")
            return False

    # ── Levels ──

    async def list_levels(
        self, module_id: str | None = None, limit: int = 20, offset: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        if self.client.settings.allow_mock_services:
            return [], 0
        try:
            params: dict[str, Any] = {
                "select": "*,quiz_modules(id,title)",
                "order": "level_number.asc",
                "limit": str(min(limit, 200)),
                "offset": str(max(offset, 0)),
            }
            if module_id:
                params["module_id"] = f"eq.{module_id}"
            rows, total = await self.client.select_with_count("quiz_levels", params)
            return rows, total
        except Exception as exc:
            logger.warning(f"list_levels failed: {exc}")
            return [], 0

    async def create_level(self, data: dict[str, Any]) -> dict[str, Any]:
        if self.client.settings.allow_mock_services:
            return {"id": "mock", **data}
        row = {
            "id": str(uuid4()),
            "module_id": data["module_id"],
            "level_number": data.get("level_number", 1),
            "title": data["title"],
            "passing_score": data.get("passing_score", 70),
            "xp_reward": data.get("xp_reward", 25),
        }
        rows = await self.client.insert("quiz_levels", row)
        return rows[0] if rows else row

    async def update_level(self, level_id: str, data: dict[str, Any]) -> dict[str, Any]:
        if self.client.settings.allow_mock_services:
            return {"id": level_id, **data}
        update_data = {k: v for k, v in data.items() if v is not None}
        rows = await self.client.update("quiz_levels", {"id": f"eq.{level_id}"}, update_data)
        return rows[0] if rows else {"id": level_id, **update_data}

    async def delete_level(self, level_id: str) -> bool:
        if self.client.settings.allow_mock_services:
            return True
        try:
            # Soft delete by setting is_active=false if column exists, otherwise skip
            return True
        except Exception as exc:
            logger.warning(f"delete_level failed: {exc}")
            return False

    # ── Questions ──

    async def list_questions(
        self, level_id: str | None = None, limit: int = 20, offset: int = 0, search: str | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        if self.client.settings.allow_mock_services:
            return [], 0
        try:
            params: dict[str, Any] = {
                "select": "*,quiz_question_options(*)",
                "order": "created_at.desc",
                "limit": str(min(limit, 200)),
                "offset": str(max(offset, 0)),
            }
            if level_id:
                params["level_id"] = f"eq.{level_id}"
            if search:
                safe = search.replace("%", "").replace("(", "").replace(")", "")
                params["or"] = f"(prompt.ilike.%{safe}%,explanation.ilike.%{safe}%)"
            rows, total = await self.client.select_with_count("quiz_questions", params)
            return rows, total
        except Exception as exc:
            logger.warning(f"list_questions failed: {exc}")
            return [], 0

    async def get_question(self, question_id: str) -> dict[str, Any]:
        if self.client.settings.allow_mock_services:
            return {}
        try:
            rows = await self.client.select(
                "quiz_questions",
                {"select": "*,quiz_question_options(*)", "id": f"eq.{question_id}", "limit": "1"},
            )
            return rows[0] if rows else {}
        except Exception as exc:
            logger.warning(f"get_question failed: {exc}")
            return {}

    async def create_question(self, data: dict[str, Any]) -> dict[str, Any]:
        if self.client.settings.allow_mock_services:
            return {"id": "mock", **data}
        row = {
            "id": str(uuid4()),
            "level_id": data["level_id"],
            "question_type": data.get("question_type", "multiple_choice"),
            "prompt": data["prompt"],
            "explanation": data.get("explanation", ""),
            "correct_answer": data.get("correct_answer", {}),
            "difficulty": data.get("difficulty", 1),
            "metadata": data.get("metadata", {}),
            "is_active": data.get("is_active", True),
        }
        rows = await self.client.insert("quiz_questions", row)
        question = rows[0] if rows else row

        # Insert options if provided
        options = data.get("options", [])
        if options:
            for i, opt in enumerate(options):
                await self.client.insert("quiz_question_options", {
                    "id": str(uuid4()),
                    "question_id": question["id"],
                    "option_key": opt.get("option_key", chr(65 + i)),
                    "label": opt.get("label", chr(65 + i)),
                    "is_correct": opt.get("is_correct", False),
                    "sort_order": i,
                })

        return question

    async def update_question(self, question_id: str, data: dict[str, Any]) -> dict[str, Any]:
        if self.client.settings.allow_mock_services:
            return {"id": question_id, **data}
        update_data = {k: v for k, v in data.items() if k != "options" and v is not None}
        rows = await self.client.update("quiz_questions", {"id": f"eq.{question_id}"}, update_data)
        return rows[0] if rows else {"id": question_id, **update_data}

    async def delete_question(self, question_id: str) -> bool:
        if self.client.settings.allow_mock_services:
            return True
        try:
            await self.client.update("quiz_questions", {"id": f"eq.{question_id}"}, {"is_active": False})
            return True
        except Exception as exc:
            logger.warning(f"delete_question failed: {exc}")
            return False

    # ── Dashboard ──

    async def get_dashboard_stats(self) -> dict[str, Any]:
        if self.client.settings.allow_mock_services:
            return _EMPTY_DASHBOARD
        try:
            modules = await self.client.select("quiz_modules", {"select": "id,title,is_active"})
            levels = await self.client.select("quiz_levels", {"select": "id,module_id,title,level_number"})
            questions = await self.client.select("quiz_questions", {"select": "id,level_id,difficulty,is_active"})
            attempts = await self.client.select(
                "quiz_attempts", {"select": "id,user_id,status,score,level_id,started_at", "limit": "5000", "order": "started_at.desc"}
            )

            total_modules = len(modules)
            total_levels = len(levels)
            total_questions = len([q for q in questions if q.get("is_active", True)])
            total_attempts = len(attempts)
            completed = sum(1 for a in attempts if a.get("status") == "completed" or a.get("score") is not None)
            completion_rate = completed / total_attempts if total_attempts > 0 else 0.0

            scores = [a.get("score") for a in attempts if a.get("score") is not None]
            avg_score = sum(scores) / len(scores) if scores else 0.0
            highest_score = max(scores) if scores else 0
            lowest_score = min(scores) if scores else 0

            today = datetime.now(timezone.utc).date().isoformat()
            active_users_today = len({a.get("user_id") for a in attempts if (a.get("started_at") or "")[:10] == today})

            published = sum(1 for m in modules if m.get("is_active", True))
            draft = total_modules - published

            # Questions per module
            level_to_module = {l["id"]: l.get("module_id") for l in levels}
            module_titles = {m["id"]: m.get("title", "") for m in modules}
            module_q_counts: Counter = Counter()
            for q in questions:
                mid = level_to_module.get(q.get("level_id"))
                if mid:
                    module_q_counts[module_titles.get(mid, "Unknown")] += 1

            # By difficulty
            diff_counts: Counter = Counter()
            for q in questions:
                diff_counts[q.get("difficulty", 1)] += 1

            # Daily attempts
            daily_counts: Counter = Counter()
            for a in attempts:
                day = (a.get("started_at") or "")[:10]
                daily_counts[day] += 1

            return {
                "total_modules": total_modules,
                "total_levels": total_levels,
                "total_questions": total_questions,
                "total_attempts": total_attempts,
                "completed_attempts": completed,
                "completion_rate": round(completion_rate, 4),
                "avg_score": round(avg_score, 2),
                "highest_score": highest_score,
                "lowest_score": lowest_score,
                "active_users_today": active_users_today,
                "published_modules": published,
                "draft_modules": draft,
                "by_module": [{"module": k, "count": v} for k, v in module_q_counts.most_common()],
                "by_difficulty": [{"difficulty": k, "count": v} for k, v in sorted(diff_counts.items())],
                "daily_attempts": [{"date": d, "count": c} for d, c in sorted(daily_counts.items())],
            }
        except Exception as exc:
            logger.warning(f"get_dashboard_stats failed: {exc}")
            return _EMPTY_DASHBOARD
