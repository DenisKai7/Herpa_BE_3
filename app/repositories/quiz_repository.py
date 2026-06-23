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
    is_answer_correct,
    is_level_unlocked,
)
from app.services.quiz.quiz_seed import QUIZ_SEED_TOPICS
from app.services.supabase.client import SupabaseClient


logger = logging.getLogger(__name__)


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

    @staticmethod
    def _public_question(question: dict[str, Any], include_review: bool = False) -> dict[str, Any]:
        hidden = {"correct_answer", "accepted_answers"}
        public = {k: v for k, v in question.items() if k not in hidden}
        public["options"] = [
            ({k: v for k, v in option.items() if k != "is_correct"} if not include_review else option)
            for option in question.get("options", [])
        ]
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
            # Calculate highest_level_completed based on per-level best_score >= PASSING_SCORE
            highest = 0
            for level in topic["levels"]:
                lp = per_level_progress.get(str(level["id"]), {})
                level_best = int(lp.get("best_accuracy", 0) or 0)
                level_completed = bool(lp.get("completed", False))
                if level_completed and level_best >= PASSING_SCORE:
                    highest = max(highest, int(level["level_number"]))
            levels = []
            for level in topic["levels"]:
                number = int(level["level_number"])
                lp = per_level_progress.get(str(level["id"]), {})
                level_best = int(lp.get("best_accuracy", 0) or 0)
                level_completed = bool(lp.get("completed", False)) and level_best >= PASSING_SCORE
                question_count = len(await self.get_questions_for_level(str(level["id"]), topic["id"]))
                is_unlocked = is_level_unlocked(number, highest)
                levels.append(
                    {
                        **level,
                        "question_type": level.get("quiz_type") or _quiz_type_for_level(number),
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
            "difficulty": str(row.get("difficulty", "easy")),
            "order_index": int(row.get("order_index", metadata.get("order_index", 0)) or 0),
            "xp_reward": int(row.get("xp_reward", 10) or 10),
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
        correct_answer: Any,
        explanation: str | None,
        is_correct: bool,
        score_delta: int,
        duration_ms: int = 0,
    ) -> dict[str, Any]:
        await self.get_session(user_id, session_id)
        row = {
            "id": str(uuid4()),
            "attempt_id": session_id,
            "session_id": session_id,
            "user_id": user_id,
            "question_id": question_id,
            "answer": user_answer,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "is_skipped": False,
            "duration_ms": duration_ms,
            "score_delta": score_delta,
            "xp_delta": 10 if is_correct else 0,
            "explanation_snapshot": explanation,
            "created_at": self._now(),
            "answered_at": self._now(),
        }
        try:
            await self.client.request(
                "POST",
                "quiz_answers",
                params={"on_conflict": "attempt_id,question_id"},
                json=row,
                prefer="resolution=merge-duplicates,return=minimal",
            )
        except Exception:
            pass
        answers = self._answers.setdefault(session_id, [])
        answers[:] = [item for item in answers if item["question_id"] != question_id]
        answers.append(row)
        return row

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
        xp_earned = correct * 10
        if completed and passed:
            xp_earned += 20
        if completed and passed and level_number == 5:
            xp_earned += 50
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
    ) -> dict[str, Any]:
        session = await self.get_session(user_id, session_id)
        if session.get("status") == "completed":
            logger.info("Quiz answer rejected: attempt completed", extra={"attempt_id": session_id, "user_id": user_id})
            raise BadRequestError("Quiz attempt already completed")
        questions = session.get("questions") or []
        allowed_ids = {str(q["id"]) for q in questions}
        if str(question_id) not in allowed_ids:
            logger.info("Quiz answer rejected: question not in attempt", extra={"attempt_id": session_id, "user_id": user_id, "question_id": question_id})
            raise ConflictError(
                message="Question does not belong to this quiz attempt",
                code="QUESTION_NOT_IN_ATTEMPT",
                details={
                    "attempt_level_id": str(session.get("level_id", "")),
                    "question_level_id": question_id,
                    "message": "Question does not belong to this quiz attempt",
                },
            )
        question = next(q for q in questions if str(q["id"]) == str(question_id))
        question_type = question.get("question_type", "multiple_choice")
        option = None
        correct_option = None
        correct_answer = self._display_answer(question.get("correct_answer"))
        if not selected_option_id and user_answer is not None and question_type in {"multiple_choice", "case_based"}:
            selected_option_id = str(user_answer)
        if selected_option_id:
            option = next(
                (
                    opt
                    for opt in question.get("options", [])
                    if str(opt.get("id")) == str(selected_option_id)
                    or str(opt.get("option_key")) == str(selected_option_id)
                ),
                None,
            )
            if not option:
                logger.info(
                    "Quiz answer rejected: selected option not found",
                    extra={"attempt_id": session_id, "user_id": user_id, "question_id": question_id, "selected_option_id": selected_option_id},
                )
                raise NotFoundError("Quiz selected option not found")
        elif question_type in {"multiple_choice", "case_based"}:
            raise NotFoundError("Quiz selected option not found")
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
        if option:
            if not correct_option:
                logger.error("Quiz question has no correct option", extra={"question_id": question_id})
                raise AppError("QUIZ_CORRECT_OPTION_NOT_FOUND", "Soal belum memiliki jawaban benar.", 500)
            correct = str(option["id"]) == str(correct_option["id"])
            if correct_answer in (None, ""):
                correct_answer = correct_option.get("text") or correct_option.get("label")
            normalized_answer = {
                "selected_option_id": str(option["id"]),
                "selected_option_key": option.get("option_key"),
                "text": option.get("text"),
            }
        else:
            correct = is_answer_correct(question_type, question["correct_answer"], user_answer, question.get("accepted_answers"))
            normalized_answer = user_answer
        logger.info(
            "Submitting quiz answer",
            extra={"attempt_id": session_id, "user_id": user_id, "question_id": question_id, "selected_option_id": selected_option_id},
        )
        await self.save_answer(
            user_id,
            session_id,
            question_id,
            normalized_answer,
            correct_answer,
            question.get("explanation"),
            correct,
            10 if correct else 0,
            elapsed_ms,
        )
        completion = await self.complete_session_if_done(user_id, session_id)
        return {
            "attempt_id": session_id,
            "session_id": session_id,
            "question_id": question_id,
            "selected_option_id": str(option["id"]) if option else None,
            "selected_option_key": option.get("option_key") if option else None,
            "is_correct": correct,
            "correct": correct,
            "correct_option_id": str(correct_option["id"]) if correct_option else None,
            "correct_option_key": correct_option.get("option_key") if correct_option else None,
            "correct_answer": correct_answer,
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
