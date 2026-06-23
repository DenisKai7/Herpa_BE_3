from __future__ import annotations

from datetime import date, datetime, timezone
import json
import logging
from typing import Any
from uuid import uuid4

from app.core.exceptions import AppError, BadRequestError, ConflictError, NotFoundError
from app.services.quiz.quiz_engine import (
    calculate_topic_progress,
    calculate_user_level,
    extract_accepted_answers,
    format_correct_answer,
    is_answer_correct,
    is_level_unlocked,
    normalize_answer,
)
from app.services.quiz.quiz_seed import QUIZ_SEED_TOPICS
from app.services.supabase.client import SupabaseClient


logger = logging.getLogger(__name__)


TYPE_LABEL_MAP = {
    "multiple_choice": "Pilihan Ganda",
    "matching": "Mencocokkan",
    "true_false": "Benar/Salah",
    "short_answer": "Jawaban Singkat",
    "case_based": "Studi Kasus",
    "case_study": "Studi Kasus",
}


def _matching_item(item: Any, key_field: str = "key") -> dict[str, str]:
    if isinstance(item, dict):
        key = item.get(key_field) or item.get("id") or item.get("value") or item.get("label") or item.get("text")
        text = item.get("text") or item.get("label") or item.get("value") or key
        return {"key": str(key), "text": str(text)}
    return {"key": str(item), "text": str(item)}


class QuizRepository:
    """Quiz repository using current Supabase schema with safe in-memory fallback."""

    def __init__(self, client: SupabaseClient):
        self.client = client
        self._sessions: dict[str, dict[str, Any]] = {}
        self._answers: dict[str, list[dict[str, Any]]] = {}
        self._progress: dict[tuple[str, str], dict[str, Any]] = {}
        self._stats: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _today() -> str:
        return date.today().isoformat()

    @staticmethod
    def _safe_json_value(value: Any) -> Any:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (TypeError, json.JSONDecodeError):
                return value
        return value

    @classmethod
    def _display_answer(cls, value: Any) -> Any:
        value = cls._safe_json_value(value)
        if isinstance(value, dict) and "answer" in value:
            return value["answer"]
        return value

    @classmethod
    def _matching_items(cls, question: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        metadata = cls._safe_json_value(question.get("metadata") or {}) or {}
        left_items = cls._safe_json_value(metadata.get("left_items") or []) or []
        right_items = cls._safe_json_value(metadata.get("right_items") or []) or []
        if left_items and right_items:
            return [_matching_item(item, "key") for item in left_items], [_matching_item(item, "key") for item in right_items]

        matching = cls._safe_json_value(metadata.get("matching") or {}) or {}
        if isinstance(matching, dict):
            left_items = matching.get("left_items") or matching.get("left") or []
            right_items = matching.get("right_items") or matching.get("right") or []
            if left_items and right_items:
                return [_matching_item(item, "key") for item in left_items], [_matching_item(item, "key") for item in right_items]

        pairs = cls._safe_json_value(question.get("matching_pairs") or []) or []
        if pairs:
            left_items = []
            right_items = []
            for index, pair in enumerate(pairs, start=1):
                if isinstance(pair, dict):
                    left = pair.get("left_text") or pair.get("left") or pair.get("source")
                    right = pair.get("right_text") or pair.get("right") or pair.get("target")
                    left_key = pair.get("left_key") or pair.get("left_id") or (chr(64 + index) if index <= 26 else str(index))
                    right_key = pair.get("right_key") or pair.get("right_id") or str(index)
                elif isinstance(pair, (list, tuple)) and len(pair) >= 2:
                    left, right = pair[0], pair[1]
                    left_key = chr(64 + index) if index <= 26 else str(index)
                    right_key = str(index)
                else:
                    continue
                left_items.append({"key": str(left_key), "text": str(left)})
                right_items.append({"key": str(right_key), "text": str(right)})
            if left_items and right_items:
                return left_items, right_items

        correct = cls._display_answer(question.get("correct_answer"))
        if isinstance(correct, dict):
            left_items = [{"key": str(key), "text": str(key)} for key in correct]
            right_items = [{"key": str(value), "text": str(value)} for value in dict.fromkeys(correct.values())]
            return left_items, right_items
        return [], []

    @classmethod
    def _public_question(cls, question: dict[str, Any], include_review: bool = False) -> dict[str, Any]:
        hidden = {"correct_answer", "accepted_answers"}
        public = {k: v for k, v in question.items() if k not in hidden}
        public["options"] = [
            ({k: v for k, v in option.items() if k != "is_correct"} if not include_review else option)
            for option in question.get("options", [])
        ]
        if question.get("question_type") == "matching" and not include_review:
            metadata = cls._safe_json_value(question.get("metadata") or {}) or {}
            left_items, right_items = cls._matching_items(question)
            public["prompt"] = metadata.get("matching_prompt") or question.get("matching_prompt") or public.get("prompt")
            public["matching_prompt"] = public["prompt"]
            public["left_items"] = left_items
            public["right_items"] = right_items
            public["matching_pairs"] = {"left_items": left_items, "right_items": right_items}
        return public

    def _fallback_stats(self, user_id: str) -> dict[str, Any]:
        return self._stats.setdefault(
            user_id,
            {
                "user_id": user_id,
                "total_xp": 0,
                "level": 1,
                "completed_topics": 0,
                "completed_levels": 0,
                "current_streak": 0,
                "longest_streak": 0,
            },
        )

    @staticmethod
    def _normalize_module(row: dict[str, Any]) -> dict[str, Any]:
        levels = row.get("quiz_levels") or row.get("levels") or []
        levels.sort(key=lambda item: int(item.get("level_number", 0) or 0))
        return {
            "id": row.get("slug") or str(row.get("id")),
            "module_id": str(row.get("id")),
            "title": row.get("title") or row.get("slug") or "Topik Quiz",
            "description": row.get("description"),
            "order_index": row.get("sort_order", row.get("order_index", 0)) or 0,
            "icon": row.get("icon") or "flask",
            "is_active": row.get("is_active", True),
            "levels": [
                {
                    "id": str(level["id"]),
                    "topic_id": row.get("slug") or str(row.get("id")),
                    "module_id": str(row.get("id")),
                    "level_number": int(level.get("level_number", 1) or 1),
                    "title": level.get("title") or f"Level {level.get('level_number', 1)}",
                    "description": level.get("description"),
                    "quiz_type": level.get("quiz_type") or _quiz_type_for_level(int(level.get("level_number", 1) or 1)),
                    "xp_reward": int(level.get("xp_reward", 20) or 20),
                    "passing_score": int(level.get("passing_score", 70) or 70),
                    "order_index": int(level.get("order_index", level.get("level_number", 1)) or 1),
                }
                for level in levels
            ],
        }

    async def _topic_source(self) -> list[dict[str, Any]]:
        if self.client.settings.allow_mock_services:
            return QUIZ_SEED_TOPICS
        try:
            rows = await self.client.select(
                "quiz_modules",
                {"select": "*,quiz_levels(*)", "is_active": "eq.true", "order": "sort_order.asc"},
            )
        except Exception as exc:
            logger.exception("Failed to fetch quiz modules from database")
            raise AppError("QUIZ_TOPICS_UNAVAILABLE", "Data topik quiz tidak dapat dibaca dari database.", 500) from exc
        if not rows:
            raise NotFoundError("Quiz topics not found.")
        return [self._normalize_module(row) for row in rows]

    async def _find_topic(self, topic_id: str) -> dict[str, Any] | None:
        return next((topic for topic in await self._topic_source() if topic["id"] == topic_id), None)

    async def _find_level(self, topic_id: str, level_id: str | None = None, level_number: int | None = None) -> dict[str, Any] | None:
        topic = await self._find_topic(topic_id)
        if topic:
            for level in topic["levels"]:
                if level_id and str(level["id"]) == str(level_id):
                    return level
                if level_number and int(level["level_number"]) == int(level_number):
                    return level
        return None

    async def find_level_by_id(self, level_id: str | None) -> dict[str, Any] | None:
        if not level_id:
            return None
        for topic in await self._topic_source():
            for level in topic["levels"]:
                if str(level["id"]) == str(level_id):
                    return level | {"topic_id": topic["id"], "topic_title": topic["title"]}
        return None

    async def _level_context(self, level_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        for topic in await self._topic_source():
            for level in topic["levels"]:
                if str(level["id"]) == str(level_id):
                    return topic, level
        raise NotFoundError("Level quiz tidak ditemukan.")

    async def get_progress(self, user_id: str) -> dict[str, Any]:
        if self.client.settings.allow_mock_services:
            return self._fallback_progress(user_id)
        try:
            xp_rows = await self.client.select("user_xp", {"select": "xp", "user_id": f"eq.{user_id}", "limit": "1"})
            streak_rows = await self.client.select(
                "user_streaks", {"select": "current_streak,longest_streak", "user_id": f"eq.{user_id}", "limit": "1"}
            )
            progress_rows = await self.client.select("quiz_progress", {"select": "*", "user_id": f"eq.{user_id}"})
            total_xp = int(xp_rows[0].get("xp", 0) if xp_rows else 0)
            current_streak = int(streak_rows[0].get("current_streak", 0) if streak_rows else 0)
            topic_progress = await self._topic_progress_from_level_rows(progress_rows)
            return {
                "total_xp": total_xp,
                "level": calculate_user_level(total_xp),
                "completed_topics": sum(1 for row in topic_progress if row.get("highest_level_completed", 0) >= 5),
                "completed_levels": sum(1 for row in progress_rows if row.get("completed")),
                "current_streak": current_streak,
                "topic_progress": topic_progress,
            }
        except Exception:
            return self._fallback_progress(user_id)

    def _fallback_progress(self, user_id: str) -> dict[str, Any]:
        stats = self._fallback_stats(user_id)
        return {
            "total_xp": stats["total_xp"],
            "level": stats["level"],
            "completed_topics": stats["completed_topics"],
            "completed_levels": stats["completed_levels"],
            "current_streak": stats["current_streak"],
            "topic_progress": [row for (uid, _), row in self._progress.items() if uid == user_id],
        }

    async def _topic_progress_from_level_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_level = {str(row.get("level_id")): row for row in rows}
        result = []
        for topic in await self._topic_source():
            highest = 0
            total_xp = 0
            completed_sessions = 0
            mastery_score = 0
            active_level_id = None
            for level in topic["levels"]:
                row = by_level.get(str(level["id"]))
                if not row:
                    continue
                completed_sessions += int(row.get("attempts_count", 0) or 0)
                mastery_score = max(mastery_score, int(row.get("best_accuracy", 0) or 0))
                if row.get("completed"):
                    highest = max(highest, int(level["level_number"]))
                    active_level_id = str(level["id"])
            if highest or completed_sessions:
                result.append(
                    {
                        "user_id": None,
                        "topic_id": topic["id"],
                        "level_id": active_level_id,
                        "highest_level_completed": highest,
                        "topic_progress": calculate_topic_progress(highest),
                        "mastery_score": mastery_score,
                        "total_xp": total_xp,
                        "completed_sessions": completed_sessions,
                    }
                )
        return result

    async def get_topics_with_progress(self, user_id: str) -> dict[str, list[dict[str, Any]]]:
        progress = await self.get_progress(user_id)
        by_topic = {row.get("topic_id"): row for row in progress.get("topic_progress", [])}
        # Also fetch per-level progress from DB for accurate best_score per level
        per_level_progress: dict[str, dict[str, Any]] = {}
        try:
            progress_rows = await self.client.select("quiz_progress", {"select": "*", "user_id": f"eq.{user_id}"})
            for row in progress_rows:
                per_level_progress[str(row.get("level_id"))] = row
        except Exception:
            pass
        PASSING_SCORE = 70
        topics = []
        for topic in await self._topic_source():
            row = by_topic.get(topic["id"], {})
            highest = int(row.get("highest_level_completed", 0) or 0)
            if per_level_progress:
                highest_db = 0
                for level in topic["levels"]:
                    lp = per_level_progress.get(str(level["id"]), {})
                    level_best = int(lp.get("best_accuracy", 0) or 0)
                    level_completed = bool(lp.get("completed", False))
                    if level_completed and level_best >= PASSING_SCORE:
                        highest_db = max(highest_db, int(level["level_number"]))
                highest = max(highest, highest_db)
            levels = []
            for level in topic["levels"]:
                number = int(level["level_number"])
                lp = per_level_progress.get(str(level["id"]), {})
                level_best = int(lp.get("best_accuracy", 0) or 0)
                level_completed = bool(lp.get("completed", False)) and level_best >= PASSING_SCORE
                question_count = len(await self.get_questions_for_level(str(level["id"]), topic["id"]))
                is_unlocked = is_level_unlocked(number, highest)
                qtype = level.get("quiz_type") or _quiz_type_for_level(number)
                levels.append(
                    {
                        **level,
                        "question_type": qtype,
                        "type_label": TYPE_LABEL_MAP.get(qtype, "Quiz"),
                        "question_count": question_count,
                        "is_unlocked": is_unlocked,
                        "is_locked": not is_unlocked,
                        "is_completed": level_completed,
                        "best_score": level_best if level_completed else 0,
                        "progress": 100 if level_completed else 0,
                    }
                )
            passed_count = sum(1 for l in levels if l["is_completed"])
            topic_progress_pct = calculate_topic_progress(highest)
            topics.append(
                {
                    "id": topic["id"],
                    "title": topic["title"],
                    "description": topic.get("description"),
                    "sort_order": topic.get("order_index", 0),
                    "icon": topic.get("icon"),
                    "progress": topic_progress_pct,
                    "progress_percent": topic_progress_pct,
                    "is_available": True,
                    "highest_level_completed": highest,
                    "current_level": min(5, highest + 1) if highest < 5 else 5,
                    "status": "completed" if highest >= 5 else "in_progress" if highest else "available",
                    "levels": levels,
                }
            )
        return {"topics": topics}

    async def get_topic_levels(self, topic_id: str, user_id: str) -> list[dict[str, Any]]:
        topics = (await self.get_topics_with_progress(user_id))["topics"]
        topic = next((item for item in topics if item["id"] == topic_id), None)
        if not topic:
            raise NotFoundError("Topik quiz tidak ditemukan.")
        return topic["levels"]

    @classmethod
    def _normalize_question(cls, row: dict[str, Any], topic_id: str | None = None) -> dict[str, Any]:
        raw_options = list(row.get("quiz_question_options") or row.get("options") or [])
        raw_options.sort(key=lambda option: (int(option.get("sort_order", 0) or 0), str(option.get("option_key") or option.get("label") or "")))
        options = []
        for option in raw_options:
            option_id = str(option.get("id") or option.get("option_id") or option.get("option_key") or option.get("label"))
            option_key = str(option.get("option_key") or option.get("label") or "")
            option_label = option.get("label") or option.get("text") or ""
            options.append(
                {
                    "id": option_id,
                    "option_key": option_key,
                    "label": option_label,
                    "text": option_label,
                    "sort_order": int(option.get("sort_order", 0) or 0),
                    "is_correct": bool(option.get("is_correct", False)),
                }
            )
        metadata = row.get("metadata") or {}
        return {
            "id": str(row["id"]),
            "topic_id": topic_id or row.get("topic_id") or "",
            "level_id": str(row["level_id"]),
            "question_type": row.get("question_type", "multiple_choice"),
            "prompt": row.get("prompt", ""),
            "explanation": row.get("explanation"),
            "options": options,
            "correct_answer": cls._safe_json_value(row.get("correct_answer")),
            "accepted_answers": cls._safe_json_value(row.get("accepted_answers") or metadata.get("accepted_answers") or []),
            "matching_pairs": cls._safe_json_value(row.get("matching_pairs") or metadata.get("matching_pairs") or []),
            "metadata": cls._safe_json_value(metadata),
            "difficulty": str(row.get("difficulty", "easy")),
            "order_index": int(row.get("order_index", metadata.get("order_index", 0)) or 0),
            "xp_reward": int(row.get("xp_reward", 10) or 10),
            "case_context": metadata.get("case_context"),
        }

    async def get_questions_for_level(self, level_id: str, topic_id: str | None = None) -> list[dict[str, Any]]:
        if self.client.settings.allow_mock_services:
            from app.services.quiz.quiz_seed import questions_for_level

            return [self._normalize_question(question, topic_id) for question in questions_for_level(level_id)]
        try:
            rows = await self.client.select(
                "quiz_questions",
                {"select": "*,quiz_question_options(*)", "level_id": f"eq.{level_id}", "is_active": "eq.true", "order": "order_index.asc"},
            )
        except Exception as exc:
            logger.exception("Failed to fetch quiz questions", extra={"level_id": level_id})
            raise AppError("QUIZ_QUESTIONS_UNAVAILABLE", "Soal quiz tidak dapat dibaca dari database.", 500) from exc
        return [self._normalize_question(row, topic_id) for row in rows]

    @staticmethod
    def dedupe_questions(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[str, str]] = set()
        unique = []
        for question in questions:
            key = (str(question.get("question_type", "")).lower(), str(question.get("prompt", "")).strip().lower())
            if key in seen:
                continue
            seen.add(key)
            unique.append(question)
        return unique

    def _hydrate_session_questions(self, session: dict[str, Any]) -> dict[str, Any]:
        return session

    async def _is_attempt_valid(self, session: dict[str, Any], level_id: str, topic_id: str) -> bool:
        """Check if an active attempt is still valid against current DB questions."""
        try:
            # level must still exist
            try:
                await self._level_context(level_id)
            except NotFoundError:
                return False
            # fetch current questions for level
            current_questions = await self.get_questions_for_level(level_id, topic_id)
            if len(current_questions) < 10:
                return False
            # every question must have at least 4 options
            for q in current_questions[:10]:
                if len(q.get("options", [])) < 4:
                    return False
            # check if attempt's stored question IDs still match current DB
            metadata = session.get("metadata") or {}
            stored_ids = [str(qid) for qid in metadata.get("questions", [])]
            if stored_ids:
                current_ids = {str(q["id"]) for q in current_questions}
                if not all(qid in current_ids for qid in stored_ids):
                    return False
            return True
        except Exception:
            return False

    async def _abandon_attempt(self, attempt_id: str, user_id: str) -> None:
        """Mark an active attempt as abandoned."""
        try:
            await self.client.update(
                "quiz_attempts",
                {"id": f"eq.{attempt_id}", "user_id": f"eq.{user_id}"},
                {"status": "abandoned", "completed_at": self._now()},
            )
        except Exception:
            pass
        # also clean local cache
        self._sessions.pop(attempt_id, None)
        self._answers.pop(attempt_id, None)

    async def find_active_session(self, user_id: str, topic_id: str, level_id: str) -> dict[str, Any] | None:
        # check in-memory sessions first
        for session in list(self._sessions.values()):
            if (
                session.get("user_id") == user_id
                and str(session.get("level_id")) == str(level_id)
                and session.get("topic_id") == topic_id
                and session.get("status") == "active"
            ):
                if await self._is_attempt_valid(session, str(level_id), topic_id):
                    return self._hydrate_session_questions(session)
                else:
                    await self._abandon_attempt(str(session["id"]), user_id)
                    return None
        try:
            rows = await self.client.select(
                "quiz_attempts",
                {
                    "select": "*",
                    "user_id": f"eq.{user_id}",
                    "level_id": f"eq.{level_id}",
                    "status": "eq.active",
                    "deleted_at": "is.null",
                    "order": "started_at.desc",
                },
            )
        except Exception:
            rows = []
        if not rows:
            return None
        # Abandon ALL stale active attempts (cleanup duplicates from before unique index)
        valid_session = None
        for row in rows:
            if not await self._is_attempt_valid(row, str(level_id), topic_id):
                await self._abandon_attempt(str(row["id"]), user_id)
            elif valid_session is None:
                # Keep the most recent valid one
                valid_session = row
            else:
                # Abandon duplicates — keep only the first valid
                await self._abandon_attempt(str(row["id"]), user_id)
        if not valid_session:
            return None
        session = await self.get_session(user_id, str(valid_session["id"]))
        metadata = session.get("metadata") or {}
        if (metadata.get("topic_id") or topic_id) != topic_id:
            return None
        return self._hydrate_session_questions(session)

    async def create_session(self, user_id: str, topic_id: str, level_id: str, questions: list[dict[str, Any]]) -> dict[str, Any]:
        topic, level = await self._level_context(level_id)
        active = await self.find_active_session(user_id, topic["id"], str(level_id))
        if active:
            return active
        session_id = str(uuid4())
        row = {
            "id": session_id,
            "user_id": user_id,
            "level_id": str(level_id),
            "level_number": int(level["level_number"]),
            "status": "active",
            "score": 0,
            "total_questions": len(questions),
            "correct": 0,
            "incorrect": 0,
            "current_question_index": 0,
            "xp_earned": 0,
            "started_at": self._now(),
            "metadata": {"questions": [q["id"] for q in questions], "topic_id": topic["id"], "quiz_type": level["quiz_type"]},
        }
        try:
            inserted = await self.client.insert("quiz_attempts", row)
            if isinstance(inserted, list) and inserted:
                row = inserted[0] | row
        except Exception:
            pass
        self._sessions[session_id] = row | {"id": session_id, "topic_id": topic["id"], "level_id": str(level_id), "questions": questions}
        self._answers[session_id] = []
        return self._hydrate_session_questions(self._sessions[session_id])

    async def get_session(self, user_id: str, session_id: str) -> dict[str, Any]:
        local = self._sessions.get(session_id)
        if local:
            if local["user_id"] != user_id:
                raise NotFoundError("Quiz attempt not found")
            return local
        try:
            rows = await self.client.select("quiz_attempts", {"select": "*", "id": f"eq.{session_id}", "user_id": f"eq.{user_id}", "limit": "1"})
        except Exception as exc:
            logger.info("Quiz attempt lookup failed", extra={"attempt_id": session_id, "user_id": user_id})
            raise NotFoundError("Quiz attempt not found") from exc
        if not rows:
            logger.info("Quiz attempt not found", extra={"attempt_id": session_id, "user_id": user_id})
            raise NotFoundError("Quiz attempt not found")
        row = rows[0]
        topic, level = await self._level_context(str(row["level_id"]))
        questions = await self.get_questions_for_level(str(row["level_id"]), topic["id"])
        metadata = row.get("metadata") or {}
        question_ids = [str(qid) for qid in metadata.get("questions", [])]
        if question_ids:
            by_id = {q["id"]: q for q in questions}
            questions = [by_id[qid] for qid in question_ids if qid in by_id]
        return row | {"topic_id": topic["id"], "level_id": str(row["level_id"]), "questions": questions, "level_number": int(level["level_number"])}

    async def save_answer(
        self,
        user_id: str,
        session_id: str,
        question_id: str,
        user_answer: Any,
        is_correct: bool,
        duration_ms: int = 0,
        correct_answer: Any = None,
        explanation: str | None = None,
    ) -> dict[str, Any]:
        await self.get_session(user_id, session_id)
        row = {
            "id": str(uuid4()),
            "attempt_id": session_id,
            "question_id": question_id,
            "answer": user_answer,
            "is_correct": bool(is_correct),
            "is_skipped": False,
            "duration_ms": duration_ms,
        }
        try:
            await self.client.request(
                "POST",
                "quiz_answers",
                params={"on_conflict": "attempt_id,question_id"},
                json=row,
                prefer="resolution=merge-duplicates,return=representation",
            )
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            response_text = getattr(exc, "details", {}).get("response") if hasattr(exc, "details") else None
            if not response_text:
                response_text = getattr(exc, "message", None) or str(exc)
            logger.exception(
                "Failed to save quiz answer",
                extra={
                    "attempt_id": session_id,
                    "question_id": question_id,
                    "question_type": user_answer.get("question_type") if isinstance(user_answer, dict) else None,
                    "status_code": status_code,
                    "response_text": response_text,
                    "payload_keys": list(row.keys()),
                },
            )
            raise AppError("QUIZ_ANSWER_SAVE_FAILED", "Jawaban belum tersimpan. Coba lagi.", 500) from exc

        cached_row = row | {
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "explanation_snapshot": explanation,
            "question_type": user_answer.get("question_type") if isinstance(user_answer, dict) else None,
        }
        answers = self._answers.setdefault(session_id, [])
        answers[:] = [item for item in answers if item["question_id"] != question_id]
        answers.append(cached_row)
        return cached_row

    async def _answers_for_session(self, session_id: str) -> list[dict[str, Any]]:
        if session_id in self._answers:
            return self._answers[session_id]
        try:
            rows = await self.client.select("quiz_answers", {"select": "*", "attempt_id": f"eq.{session_id}"})
            self._answers[session_id] = [row | {"question_id": str(row["question_id"]), "user_answer": row.get("answer")} for row in rows]
        except Exception:
            self._answers[session_id] = []
        return self._answers[session_id]

    async def complete_session_if_done(self, user_id: str, session_id: str) -> dict[str, Any]:
        session = await self.get_session(user_id, session_id)
        questions = session.get("questions") or []
        answers = await self._answers_for_session(session_id)
        answered_count = len({str(a["question_id"]) for a in answers})
        correct = sum(1 for answer in answers if answer.get("is_correct"))
        wrong = max(0, answered_count - correct)
        score = int((correct / len(questions)) * 100) if questions else 0
        completed = answered_count >= len(questions)
        was_completed = session.get("status") == "completed"
        topic, level = await self._level_context(str(session["level_id"]))
        level_number = int(level["level_number"])
        passed = score >= int(level.get("passing_score", 70) or 70) if completed else None

        already_completed = False
        if completed:
            try:
                progress_rows = await self.client.select(
                    "quiz_progress",
                    {"select": "completed", "user_id": f"eq.{user_id}", "level_id": f"eq.{session['level_id']}", "limit": "1"}
                )
                if progress_rows and progress_rows[0].get("completed"):
                    already_completed = True
            except Exception:
                key = (user_id, topic["id"])
                if key in self._progress and self._progress[key].get("highest_level_completed", 0) >= level_number:
                    already_completed = True

        xp_earned = correct * 10
        if completed and passed:
            xp_earned += 20
        if completed and passed and level_number == 5:
            xp_earned += 50
        if already_completed:
            xp_earned = 0

        patch = {
            "score": score,
            "correct": correct,
            "incorrect": wrong,
            "current_question_index": answered_count,
            "xp_earned": xp_earned if completed else sum(1 for answer in answers if answer.get("is_correct")) * 10,
        }
        if completed:
            patch.update({"status": "completed", "completed_at": self._now(), "passed": bool(passed)})
        session.update(patch)
        try:
            await self.client.update("quiz_attempts", {"id": f"eq.{session_id}", "user_id": f"eq.{user_id}"}, patch)
        except Exception:
            pass
        if completed and not was_completed:
            await self.update_user_progress(user_id, topic["id"], str(session["level_id"]), score, xp_earned)
        return {
            "completed": completed,
            "score": score,
            "xp_earned": xp_earned if completed else 0,
            "correct_count": correct,
            "wrong_count": wrong,
            "total_questions": len(questions),
            "current_question_index": answered_count,
            "passed": passed,
            "next_level_unlocked": bool(passed) and level_number < 5,
        }

    async def submit_answer(
        self,
        user_id: str,
        session_id: str,
        question_id: str,
        user_answer: Any = None,
        selected_option_id: str | None = None,
        elapsed_ms: int = 0,
        answer_text: str | None = None,
        matching_answer: dict | None = None,
    ) -> dict[str, Any]:
        session = await self.get_session(user_id, session_id)
        if session.get("status") == "completed":
            logger.info("Quiz answer rejected: attempt completed", extra={"attempt_id": session_id, "user_id": user_id})
            raise BadRequestError("Quiz attempt already completed")
        questions = session.get("questions") or []
        question = next((q for q in questions if str(q["id"]) == str(question_id)), None)
        if not question:
            exists = False
            db_question = None
            if self.client.settings.allow_mock_services:
                from app.services.quiz.quiz_seed import QUIZ_SEED_TOPICS, questions_for_level
                for t in QUIZ_SEED_TOPICS:
                    for lvl in t.get("levels", []):
                        for q in questions_for_level(str(lvl["id"])):
                            if str(q["id"]) == str(question_id):
                                exists = True
                                db_question = q
                                break
                        if exists:
                            break
                    if exists:
                        break
            else:
                try:
                    rows = await self.client.select("quiz_questions", {"select": "*", "id": f"eq.{question_id}", "limit": "1"})
                    if rows:
                        exists = True
                        db_question = rows[0]
                except Exception:
                    pass
            if not exists:
                raise NotFoundError("Quiz question not found")
            raise ConflictError(
                message="Question does not belong to this quiz attempt",
                code="QUESTION_NOT_IN_ATTEMPT",
                details={
                    "attempt_level_id": str(session.get("level_id", "")),
                    "question_level_id": str(db_question.get("level_id", "")),
                    "message": "Question does not belong to this quiz attempt",
                },
            )
        orig_question_type = question.get("question_type", "multiple_choice")
        question_type = orig_question_type
        if question_type == "case_study":
            question_type = "case_based"

        # Dispatch user answer and format depending on question type
        resolved_user_answer = user_answer
        if question_type in {"multiple_choice", "true_false"}:
            if selected_option_id is not None:
                resolved_user_answer = selected_option_id
            elif user_answer is not None:
                resolved_user_answer = user_answer
        elif question_type == "matching":
            resolved_user_answer = matching_answer if matching_answer is not None else user_answer
        elif question_type in {"short_answer", "case_based"}:
            if answer_text is not None:
                resolved_user_answer = answer_text
            elif user_answer is not None:
                resolved_user_answer = user_answer
            elif selected_option_id is not None:
                resolved_user_answer = selected_option_id

        option = None
        correct_option = None
        correct_answer = self._display_answer(question.get("correct_answer"))
        accepted_answers: list[Any] = []
        formatted_correct_answer: Any | None = None
        response_answer_text: str | None = None

        if question_type == "short_answer":
            response_answer_text = str(resolved_user_answer or "").strip()
            if not response_answer_text:
                raise BadRequestError("Jawaban singkat tidak boleh kosong.")
            accepted_answers = extract_accepted_answers(question.get("correct_answer"), question.get("accepted_answers"))
            formatted_correct_answer = format_correct_answer(question.get("correct_answer"), question.get("accepted_answers"))
            user_answer_normalized = normalize_answer(response_answer_text)
            normalized_accepted = [normalize_answer(answer) for answer in accepted_answers]
            is_exact_match = user_answer_normalized in normalized_accepted
            is_keyword_match = any(answer and len(answer) >= 3 and answer in user_answer_normalized for answer in normalized_accepted)
            correct = bool(is_exact_match or is_keyword_match)
            correct_answer = formatted_correct_answer
            normalized_answer = {
                "question_type": "short_answer",
                "answer_text": response_answer_text,
            }
            logger.info(
                "short_answer_scoring",
                extra={
                    "event": "short_answer_scoring",
                    "attempt_id": session_id,
                    "question_id": question_id,
                    "topic_title": session.get("topic_title") or session.get("topic_id"),
                    "level_number": session.get("level_number"),
                    "question_type": question_type,
                    "user_answer_raw": response_answer_text,
                    "user_answer_normalized": user_answer_normalized,
                    "accepted_answers": accepted_answers,
                    "normalized_accepted": normalized_accepted,
                    "is_exact_match": is_exact_match,
                    "is_keyword_match": is_keyword_match,
                    "is_correct": correct,
                },
            )
        elif question_type == "matching":
            if not isinstance(resolved_user_answer, dict) or not resolved_user_answer:
                raise BadRequestError("Jawaban mencocokkan belum lengkap.")
            expected = self._display_answer(question.get("correct_answer"))
            expected_keys = {str(key) for key in expected} if isinstance(expected, dict) else set()
            if not expected_keys:
                left_items, _ = self._matching_items(question)
                expected_keys = {str(item["key"]) for item in left_items}
            submitted_keys = {str(key) for key, value in resolved_user_answer.items() if value not in (None, "")}
            if expected_keys and submitted_keys != expected_keys:
                raise BadRequestError("Jawaban mencocokkan belum lengkap.")
            correct = is_answer_correct("matching", expected, resolved_user_answer, question.get("accepted_answers"))
            normalized_answer = {
                "question_type": "matching",
                "matching_answer": {str(key): str(value) for key, value in resolved_user_answer.items()},
            }
        else:
            # Check if we should find matching option record (only MC, TF, or if case_based uses options)
            opt_id = selected_option_id
            if not opt_id and question_type in {"multiple_choice", "true_false", "case_based"} and isinstance(resolved_user_answer, str):
                opt_exists = any(
                    str(opt.get("id")) == str(resolved_user_answer) or str(opt.get("option_key")) == str(resolved_user_answer)
                    for opt in question.get("options", [])
                )
                if opt_exists:
                    opt_id = resolved_user_answer

            if opt_id:
                option = next(
                    (
                        opt
                        for opt in question.get("options", [])
                        if str(opt.get("id")) == str(opt_id)
                        or str(opt.get("option_key")) == str(opt_id)
                    ),
                    None,
                )
                if not option and question_type in {"multiple_choice", "case_based"}:
                    logger.info(
                        "Quiz answer rejected: selected option not found",
                        extra={"attempt_id": session_id, "user_id": user_id, "question_id": question_id, "selected_option_id": opt_id},
                    )
                    raise NotFoundError("Quiz selected option not found")

            if option:
                correct_option = next((opt for opt in question.get("options", []) if opt.get("is_correct")), None)
                if not correct_option:
                    correct_option = next(
                        (
                            opt
                            for opt in question.get("options", [])
                            if str(opt.get("id")) == str(correct_answer)
                            or str(opt.get("option_key")) == str(correct_answer)
                            or str(opt.get("text")) == str(correct_answer)
                            or str(opt.get("label")) == str(correct_answer)
                        ),
                        None,
                    )
                if correct_option:
                    correct = str(option["id"]) == str(correct_option["id"])
                else:
                    correct = is_answer_correct(question_type, question["correct_answer"], option.get("option_key") or option.get("id"), question.get("accepted_answers"))

                if correct_answer in (None, "") and correct_option:
                    correct_answer = correct_option.get("text") or correct_option.get("label")
                stored_qtype = "case_study" if orig_question_type == "case_study" else question_type
                normalized_answer = {
                    "question_type": stored_qtype,
                    "selected_option_id": str(option["id"]),
                    "selected_option_key": option.get("option_key"),
                }
            else:
                correct = is_answer_correct(question_type, question["correct_answer"], resolved_user_answer, question.get("accepted_answers"))
                stored_qtype = "case_study" if orig_question_type == "case_study" else question_type
                if stored_qtype in {"case_study", "case_based"}:
                    normalized_answer = {
                        "question_type": stored_qtype,
                        "answer_text": str(resolved_user_answer or "").strip(),
                    }
                else:
                    normalized_answer = {
                        "question_type": stored_qtype,
                        "selected_option_id": str(resolved_user_answer) if resolved_user_answer is not None else None,
                        "selected_option_key": None,
                    }

        logger.info(
            "Submitting quiz answer",
            extra={"attempt_id": session_id, "user_id": user_id, "question_id": question_id, "selected_option_id": selected_option_id},
        )
        await self.save_answer(
            user_id,
            session_id,
            question_id,
            normalized_answer,
            correct,
            elapsed_ms,
            correct_answer=correct_answer,
            explanation=question.get("explanation"),
        )
        completion = await self.complete_session_if_done(user_id, session_id)
        return {
            "attempt_id": session_id,
            "session_id": session_id,
            "question_id": question_id,
            "selected_option_id": str(option["id"]) if option else None,
            "selected_option_key": option.get("option_key") if option else None,
            "is_correct": bool(correct),
            "correct": bool(correct),
            "correct_option_id": str(correct_option["id"]) if correct_option else None,
            "correct_option_key": correct_option.get("option_key") if correct_option else None,
            "correct_answer": correct_answer,
            "accepted_answers": accepted_answers,
            "formatted_correct_answer": formatted_correct_answer or correct_answer,
            "question_type": question_type,
            "answer_text": response_answer_text,
            "explanation": question.get("explanation"),
            "current_question_index": completion.get("current_question_index"),
            "next_question_index": completion.get("current_question_index"),
            "total_questions": completion.get("total_questions", len(questions)),
            "score": completion["score"],
            "session_score": completion["score"],
            "correct_count": completion.get("correct_count", 0),
            "wrong_count": completion.get("wrong_count", 0),
            "is_completed": completion["completed"],
            "session_completed": completion["completed"],
            "xp_earned": completion.get("xp_earned", 0),
            "xp_delta": 10 if correct else 0,
            "score_delta": 10 if correct else 0,
            "passed": completion.get("passed"),
            "next_level_unlocked": completion.get("next_level_unlocked", False),
        }

    async def update_user_progress(self, user_id: str, topic_id: str, level_id: str, score: int, xp_earned: int) -> None:
        topic, level = await self._level_context(level_id)
        level_number = int(level["level_number"])
        passed = score >= int(level.get("passing_score", 70) or 70)
        key = (user_id, topic_id)
        current = self._progress.get(key, {"user_id": user_id, "topic_id": topic_id, "highest_level_completed": 0, "total_xp": 0, "completed_sessions": 0})
        highest = max(int(current.get("highest_level_completed", 0)), level_number if passed else 0)
        updated = current | {
            "level_id": level_id,
            "highest_level_completed": highest,
            "topic_progress": calculate_topic_progress(highest),
            "mastery_score": max(int(current.get("mastery_score", 0) or 0), score),
            "total_xp": int(current.get("total_xp", 0) or 0) + xp_earned,
            "completed_sessions": int(current.get("completed_sessions", 0) or 0) + 1,
            "last_played_at": self._now(),
            "updated_at": self._now(),
        }
        self._progress[key] = updated
        stats = self._fallback_stats(user_id)
        stats["total_xp"] += xp_earned
        stats["level"] = calculate_user_level(stats["total_xp"])
        stats["completed_levels"] += 1 if passed else 0
        stats["completed_topics"] = sum(1 for (uid, _), row in self._progress.items() if uid == user_id and int(row.get("highest_level_completed", 0)) >= 5)
        try:
            current_xp_rows = await self.client.select("user_xp", {"select": "xp", "user_id": f"eq.{user_id}", "limit": "1"})
            current_xp = int(current_xp_rows[0].get("xp", 0) if current_xp_rows else 0)
            await self.client.request(
                "POST",
                "user_xp",
                params={"on_conflict": "user_id"},
                json={"user_id": user_id, "xp": current_xp + xp_earned, "updated_at": self._now()},
                prefer="resolution=merge-duplicates,return=minimal",
            )
            await self.client.request(
                "POST",
                "user_streaks",
                params={"on_conflict": "user_id"},
                json={"user_id": user_id, "current_streak": 1, "longest_streak": 1, "last_activity_date": self._today(), "updated_at": self._now()},
                prefer="resolution=merge-duplicates,return=minimal",
            )
            await self.client.request(
                "POST",
                "quiz_progress",
                params={"on_conflict": "user_id,level_id"},
                json={"user_id": user_id, "level_id": level_id, "unlocked": True, "completed": passed, "best_accuracy": score, "attempts_count": 1, "updated_at": self._now()},
                prefer="resolution=merge-duplicates,return=minimal",
            )
            next_level = await self._find_level(topic_id, level_number=level_number + 1)
            if passed and next_level:
                await self.client.request(
                    "POST",
                    "quiz_progress",
                    params={"on_conflict": "user_id,level_id"},
                    json={"user_id": user_id, "level_id": next_level["id"], "unlocked": True, "completed": False, "updated_at": self._now()},
                    prefer="resolution=merge-duplicates,return=minimal",
                )
        except Exception:
            pass

    async def _session_history_item(self, session: dict[str, Any]) -> dict[str, Any]:
        topic, level = await self._level_context(str(session["level_id"]))
        score = int(session.get("score", 0) or 0)
        passing_score = int(level.get("passing_score", 70) or 70)
        started_at = session.get("started_at")
        return {
            "session_id": str(session["id"]),
            "attempt_id": str(session["id"]),
            "id": str(session["id"]),
            "topic_id": topic["id"],
            "topic_title": topic["title"],
            "level_id": str(session["level_id"]),
            "level_number": int(level["level_number"]),
            "quiz_type": level["quiz_type"],
            "score": score,
            "total_questions": int(session.get("total_questions", 0) or 0),
            "xp_earned": int(session.get("xp_earned", 0) or 0),
            "status": session.get("status", "active"),
            "passed": bool(session.get("passed", score >= passing_score)),
            "started_at": started_at,
            "created_at": started_at,
            "date": started_at,
            "completed_at": session.get("completed_at"),
        }

    async def get_history(self, user_id: str) -> dict[str, list[dict[str, Any]]]:
        async def clean(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            seen_ids: set[str] = set()
            completed_keys = {
                (item["topic_id"], item["level_id"])
                for item in items
                if item.get("status") == "completed"
            }
            result = []
            for item in items:
                item_id = str(item["id"])
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                key = (item["topic_id"], item["level_id"])
                # Hide empty active attempts that have a completed counterpart
                if item.get("status") == "active" and key in completed_keys and int(item.get("score", 0) or 0) == 0:
                    continue
                # Validate active attempts - abandon stale ones
                if item.get("status") == "active":
                    level_id = str(item.get("level_id", ""))
                    topic_id = str(item.get("topic_id", ""))
                    try:
                        current_questions = await self.get_questions_for_level(level_id, topic_id)
                        if len(current_questions) < 10:
                            await self._abandon_attempt(item_id, user_id)
                            continue
                    except Exception:
                        pass
                result.append(item)
            return result

        local = [
            await self._session_history_item(session)
            for session in self._sessions.values()
            if session["user_id"] == user_id and session.get("status") in {"active", "completed"}
        ]
        try:
            rows = await self.client.select("quiz_attempts", {"select": "*", "user_id": f"eq.{user_id}", "deleted_at": "is.null", "order": "started_at.desc"})
            return {"history": await clean([await self._session_history_item(row) for row in rows] if rows else local)}
        except Exception:
            return {"history": await clean(local)}

    async def get_summary(self, user_id: str, session_id: str) -> dict[str, Any]:
        session = await self.get_session(user_id, session_id)
        answers = await self._answers_for_session(session_id)
        questions = session.get("questions") or []
        answer_by_question = {str(answer["question_id"]): answer for answer in answers}
        topic, level = await self._level_context(str(session["level_id"]))
        score = int(session.get("score", 0) or 0)
        passing_score = int(level.get("passing_score", 70) or 70)
        passed = bool(session.get("passed", score >= passing_score if session.get("status") == "completed" else False))
        explanations = []
        for question in questions:
            answer = answer_by_question.get(str(question["id"]), {})
            user_answer = answer.get("user_answer") or answer.get("answer") or {}
            selected_option_id = user_answer.get("selected_option_id") if isinstance(user_answer, dict) else None
            selected_option = next((opt for opt in question.get("options", []) if str(opt.get("id")) == str(selected_option_id)), None)
            correct_option = next((opt for opt in question.get("options", []) if opt.get("is_correct")), None)
            correct_answer = self._display_answer(answer.get("correct_answer") or question.get("correct_answer"))
            if correct_answer in (None, "") and correct_option:
                correct_answer = correct_option.get("text") or correct_option.get("label")
            explanations.append(
                {
                    "question_id": question["id"],
                    "prompt": question.get("prompt"),
                    "user_answer": user_answer,
                    "selected_option": ({k: v for k, v in selected_option.items() if k != "is_correct"} if selected_option else None),
                    "correct_option": ({k: v for k, v in correct_option.items() if k != "is_correct"} if correct_option else None),
                    "correct_answer": correct_answer,
                    "is_correct": bool(answer.get("is_correct", False)),
                    "explanation": question.get("explanation") or answer.get("explanation_snapshot"),
                }
            )
        return {
            "session_id": session_id,
            "topic_id": topic["id"],
            "topic_title": topic["title"],
            "level_id": str(session["level_id"]),
            "level_number": int(level["level_number"]),
            "quiz_type": level["quiz_type"],
            "status": session.get("status", "active"),
            "score": score,
            "correct_count": session.get("correct", session.get("correct_count", sum(1 for a in answers if a.get("is_correct")))),
            "wrong_count": session.get("incorrect", session.get("wrong_count", sum(1 for a in answers if not a.get("is_correct")))),
            "total_questions": session.get("total_questions", len(questions)),
            "xp_earned": session.get("xp_earned", 0),
            "passed": passed,
            "next_level_unlocked": passed and int(level["level_number"]) < 5,
            "next_level_number": int(level["level_number"]) + 1 if passed and int(level["level_number"]) < 5 else None,
            "explanations": explanations,
        }


def _quiz_type_for_level(level_number: int) -> str:
    return {
        1: "multiple_choice",
        2: "matching",
        3: "true_false",
        4: "short_answer",
        5: "case_based",
    }.get(level_number, "multiple_choice")
