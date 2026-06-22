from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.exceptions import NotFoundError
from app.services.quiz.quiz_engine import (
    calculate_topic_progress,
    calculate_user_level,
    is_answer_correct,
    is_level_unlocked,
)
from app.services.quiz.quiz_seed import QUIZ_SEED_TOPICS, find_level, questions_for_level
from app.services.supabase.client import SupabaseClient


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
            if rows:
                return [self._normalize_module(row) for row in rows]
        except Exception:
            pass
        return QUIZ_SEED_TOPICS

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
        fallback = find_level(topic_id, level_id=level_id, level_number=level_number)
        return fallback

    async def _level_context(self, level_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        for topic in await self._topic_source():
            for level in topic["levels"]:
                if str(level["id"]) == str(level_id):
                    return topic, level
        for topic in QUIZ_SEED_TOPICS:
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
        topics = []
        for topic in await self._topic_source():
            row = by_topic.get(topic["id"], {})
            highest = int(row.get("highest_level_completed", 0) or 0)
            levels = []
            for level in topic["levels"]:
                number = int(level["level_number"])
                completed = highest >= number
                levels.append({**level, "is_locked": not is_level_unlocked(number, highest), "is_completed": completed, "progress": 100 if completed else 0})
            topics.append(
                {
                    "id": topic["id"],
                    "title": topic["title"],
                    "description": topic.get("description"),
                    "icon": topic.get("icon"),
                    "progress": int(row.get("topic_progress") or calculate_topic_progress(highest)),
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

    @staticmethod
    def _normalize_question(row: dict[str, Any], topic_id: str | None = None) -> dict[str, Any]:
        raw_options = row.get("quiz_question_options") or row.get("options") or []
        options = []
        for option in raw_options:
            options.append(
                {
                    "id": str(option.get("option_key") or option.get("id") or option.get("label")),
                    "label": option.get("option_key") or option.get("label") or "",
                    "text": option.get("text") or option.get("label") or "",
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
            "correct_answer": row.get("correct_answer"),
            "accepted_answers": row.get("accepted_answers") or metadata.get("accepted_answers") or [],
            "matching_pairs": row.get("matching_pairs") or metadata.get("matching_pairs") or [],
            "difficulty": str(row.get("difficulty", "easy")),
            "order_index": int(row.get("order_index", metadata.get("order_index", 0)) or 0),
        }

    async def get_questions_for_level(self, level_id: str, topic_id: str | None = None) -> list[dict[str, Any]]:
        if not self.client.settings.allow_mock_services:
            try:
                rows = await self.client.select(
                    "quiz_questions",
                    {"select": "*,quiz_question_options(*)", "level_id": f"eq.{level_id}", "is_active": "eq.true", "order": "order_index.asc"},
                )
                if rows:
                    return [self._normalize_question(row, topic_id) for row in rows]
            except Exception:
                pass
        return questions_for_level(level_id)

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

    async def create_session(self, user_id: str, topic_id: str, level_id: str, questions: list[dict[str, Any]]) -> dict[str, Any]:
        topic, level = await self._level_context(level_id)
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
        return self._sessions[session_id]

    async def get_session(self, user_id: str, session_id: str) -> dict[str, Any]:
        local = self._sessions.get(session_id)
        if local:
            if local["user_id"] != user_id:
                raise NotFoundError("Sesi quiz tidak ditemukan.")
            return local
        try:
            rows = await self.client.select("quiz_attempts", {"select": "*", "id": f"eq.{session_id}", "user_id": f"eq.{user_id}", "limit": "1"})
        except Exception as exc:
            raise NotFoundError("Sesi quiz tidak ditemukan.") from exc
        if not rows:
            raise NotFoundError("Sesi quiz tidak ditemukan.")
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
        if completed:
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

    async def submit_answer(self, user_id: str, session_id: str, question_id: str, user_answer: Any) -> dict[str, Any]:
        session = await self.get_session(user_id, session_id)
        questions = session.get("questions") or []
        allowed_ids = {str(q["id"]) for q in questions}
        if str(question_id) not in allowed_ids:
            raise NotFoundError("Pertanyaan tidak ditemukan dalam session ini.")
        question = next(q for q in questions if str(q["id"]) == str(question_id))
        correct = is_answer_correct(question["question_type"], question["correct_answer"], user_answer, question.get("accepted_answers"))
        await self.save_answer(user_id, session_id, question_id, user_answer, question["correct_answer"], question.get("explanation"), correct, 10 if correct else 0)
        completion = await self.complete_session_if_done(user_id, session_id)
        return {
            "correct": correct,
            "correct_answer": question["correct_answer"],
            "explanation": question.get("explanation"),
            "score_delta": 10 if correct else 0,
            "xp_delta": 10 if correct else 0,
            "session_completed": completion["completed"],
            "session_score": completion["score"],
            "correct_count": completion.get("correct_count", 0),
            "wrong_count": completion.get("wrong_count", 0),
            "total_questions": completion.get("total_questions", len(questions)),
            "next_question_index": completion.get("current_question_index"),
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
        return {
            "session_id": str(session["id"]),
            "id": str(session["id"]),
            "topic_id": topic["id"],
            "topic_title": topic["title"],
            "level_id": str(session["level_id"]),
            "level_number": int(level["level_number"]),
            "quiz_type": level["quiz_type"],
            "score": score,
            "xp_earned": int(session.get("xp_earned", 0) or 0),
            "status": session.get("status", "active"),
            "passed": bool(session.get("passed", score >= passing_score)),
            "started_at": session.get("started_at"),
            "completed_at": session.get("completed_at"),
        }

    async def get_history(self, user_id: str) -> dict[str, list[dict[str, Any]]]:
        local = [await self._session_history_item(session) for session in self._sessions.values() if session["user_id"] == user_id and session.get("status") == "completed"]
        try:
            rows = await self.client.select("quiz_attempts", {"select": "*", "user_id": f"eq.{user_id}", "deleted_at": "is.null", "order": "started_at.desc"})
            return {"history": [await self._session_history_item(row) for row in rows] if rows else local}
        except Exception:
            return {"history": local}

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
            explanations.append(
                {
                    "question_id": question["id"],
                    "prompt": question.get("prompt"),
                    "user_answer": answer.get("user_answer") or answer.get("answer"),
                    "correct_answer": question.get("correct_answer"),
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
