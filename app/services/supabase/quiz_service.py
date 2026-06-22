import random
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.exceptions import NotFoundError
from app.repositories.quiz_repository import QuizRepository
from app.services.supabase.client import SupabaseClient


class QuizService:
    def __init__(self, client: SupabaseClient):
        self.client = client
        self._attempts: dict[str, dict[str, Any]] = {}
        self.repository = QuizRepository(client)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def subjects(self) -> list[dict[str, Any]]:
        if self.client.settings.allow_mock_services:
            return [
                {
                    "id": "chemistry",
                    "slug": "kimia-dasar",
                    "title": "Kimia dan Fitokimia",
                    "name": "Kimia dan Fitokimia",
                    "description": "Jalur belajar Kimia SMA hingga fitokimia.",
                }
            ]
        return await self.client.select(
            "quiz_subjects", {"select": "*", "is_active": "eq.true", "order": "sort_order.asc"}
        )

    async def modules(self, subject_id: str | None = None) -> list[dict[str, Any]]:
        if self.client.settings.allow_mock_services:
            return [
                {
                    "id": "periodic-table",
                    "subject_id": "chemistry",
                    "slug": "sistem-periodik",
                    "title": "Sistem Periodik Unsur",
                    "sort_order": 1,
                }
            ]
        params: dict[str, Any] = {"select": "*", "is_active": "eq.true", "order": "sort_order.asc"}
        if subject_id:
            params["subject_id"] = f"eq.{subject_id}"
        return await self.client.select("quiz_modules", params)

    async def module(self, module_id: str) -> dict[str, Any]:
        if self.client.settings.allow_mock_services:
            return {
                "id": module_id,
                "title": "Sistem Periodik Unsur",
                "levels": [{"id": "periodic-1", "level_number": 1, "title": "Pengenalan"}],
            }
        rows = await self.client.select(
            "quiz_modules", {"select": "*,quiz_levels(*)", "id": f"eq.{module_id}", "limit": "1"}
        )
        if not rows:
            raise NotFoundError("Modul quiz tidak ditemukan.")
        return rows[0]

    async def level(self, level_id: str) -> dict[str, Any]:
        if self.client.settings.allow_mock_services:
            return {"id": level_id, "module_id": "periodic-table", "level_number": 1, "title": "Pengenalan"}
        rows = await self.client.select("quiz_levels", {"select": "*", "id": f"eq.{level_id}", "limit": "1"})
        if not rows:
            raise NotFoundError("Level quiz tidak ditemukan.")
        return rows[0]

    @staticmethod
    def _public_question(question: dict[str, Any]) -> dict[str, Any]:
        options = question.get("quiz_question_options") or question.get("options") or []
        public_options = [
            {
                "id": str(option.get("id") or option.get("option_key")),
                "label": option.get("option_key") or option.get("label") or "",
                "text": option.get("label") or option.get("text") or "",
            }
            for option in options
        ]
        return {
            "id": str(question["id"]),
            "question": question.get("prompt") or question.get("question") or "",
            "question_type": question.get("question_type", "multiple_choice"),
            "options": public_options,
            "explanation": None,
            "media_url": (question.get("metadata") or {}).get("media_url"),
            "points": int((question.get("metadata") or {}).get("points", 10)),
        }

    async def create_attempt(self, user_id: str, level_id: str, count: int) -> dict[str, Any]:
        if self.client.settings.allow_mock_services:
            questions = [
                {
                    "id": "q1",
                    "question": "Unsur dengan simbol Na adalah?",
                    "question_type": "multiple_choice",
                    "options": [
                        {"id": "o1", "label": "A", "text": "Natrium"},
                        {"id": "o2", "label": "B", "text": "Nitrogen"},
                        {"id": "o3", "label": "C", "text": "Neon"},
                    ],
                    "correct_option_ids": ["o1"],
                    "explanation": "Na berasal dari bahasa Latin natrium.",
                    "topic": "Sistem periodik",
                },
                {
                    "id": "q2",
                    "question": "Golongan 18 dikenal sebagai?",
                    "question_type": "multiple_choice",
                    "options": [
                        {"id": "o4", "label": "A", "text": "Halogen"},
                        {"id": "o5", "label": "B", "text": "Gas mulia"},
                    ],
                    "correct_option_ids": ["o5"],
                    "explanation": "Golongan 18 berisi gas mulia.",
                    "topic": "Sistem periodik",
                },
            ]
        else:
            questions = await self.client.select(
                "quiz_questions",
                {
                    "select": "*,quiz_question_options(*)",
                    "level_id": f"eq.{level_id}",
                    "is_active": "eq.true",
                    "limit": str(count),
                },
            )
            if not questions:
                raise NotFoundError("Level belum memiliki soal aktif.")
        random.shuffle(questions)
        aid = str(uuid4())
        now = self._now()
        row = {
            "id": aid,
            "user_id": user_id,
            "level_id": level_id,
            "status": "started",
            "seed": random.randint(1, 2_147_483_647),
            "started_at": now,
        }
        if self.client.settings.allow_mock_services:
            self._attempts[aid] = row | {"questions": questions, "answers": [], "created_at": now}
        else:
            await self.client.insert("quiz_attempts", row)
        public_questions = [
            (
                {k: v for k, v in q.items() if k != "correct_option_ids"}
                if self.client.settings.allow_mock_services
                else self._public_question(q)
            )
            for q in questions
        ]
        return {"attempt_id": aid, "level_id": level_id, "questions": public_questions}

    async def get_attempt(self, user_id: str, attempt_id: str) -> dict[str, Any]:
        if self.client.settings.allow_mock_services:
            attempt = self._attempts.get(attempt_id)
            if not attempt or attempt["user_id"] != user_id:
                raise NotFoundError("Attempt tidak ditemukan.")
            return {k: v for k, v in attempt.items() if k != "questions"}
        rows = await self.client.select(
            "quiz_attempts",
            {
                "select": "*",
                "id": f"eq.{attempt_id}",
                "user_id": f"eq.{user_id}",
                "deleted_at": "is.null",
                "limit": "1",
            },
        )
        if not rows:
            raise NotFoundError("Attempt tidak ditemukan.")
        return rows[0]

    async def answer(self, user_id: str, attempt_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        await self.get_attempt(user_id, attempt_id)
        if self.client.settings.allow_mock_services:
            attempt = self._attempts[attempt_id]
            attempt["answers"] = [
                a for a in attempt["answers"] if a.get("question_id") != payload["question_id"]
            ]
            attempt["answers"].append(payload)
            return {"saved": True}
        answer_value = {
            "selected_option_ids": payload.get("selected_option_ids", []),
            "text_answer": payload.get("text_answer"),
        }
        row = {
            "attempt_id": attempt_id,
            "question_id": payload["question_id"],
            "answer": answer_value,
            "is_skipped": bool(payload.get("skipped")),
            "duration_ms": int(payload.get("duration_ms", 0)),
        }
        await self.client.request(
            "POST",
            "quiz_answers",
            params={"on_conflict": "attempt_id,question_id"},
            json=row,
            prefer="resolution=merge-duplicates,return=representation",
        )
        return {"saved": True}

    async def complete(self, user_id: str, attempt_id: str) -> dict[str, Any]:
        attempt = await self.get_attempt(user_id, attempt_id)
        if self.client.settings.allow_mock_services:
            questions = self._attempts[attempt_id]["questions"]
            answers = self._attempts[attempt_id]["answers"]
        else:
            questions = await self.client.select(
                "quiz_questions",
                {"select": "*,quiz_question_options(*)", "level_id": f"eq.{attempt['level_id']}"},
            )
            answers = await self.client.select(
                "quiz_answers", {"select": "*", "attempt_id": f"eq.{attempt_id}"}
            )
        answer_map = {a["question_id"]: a for a in answers}
        correct = incorrect = skipped = 0
        details: list[dict[str, Any]] = []
        focus: list[str] = []
        for question in questions:
            qid = str(question["id"])
            answer = answer_map.get(qid)
            if not answer or answer.get("skipped") or answer.get("is_skipped"):
                skipped += 1
                ok = False
            else:
                selected = set(
                    answer.get("selected_option_ids")
                    or (answer.get("answer") or {}).get("selected_option_ids")
                    or []
                )
                if "correct_option_ids" in question:
                    expected = set(question["correct_option_ids"])
                else:
                    expected = {
                        str(o.get("id") or o.get("option_key"))
                        for o in question.get("quiz_question_options", [])
                        if o.get("is_correct")
                    }
                    if not expected:
                        raw = question.get("correct_answer") or []
                        expected = set(raw if isinstance(raw, list) else [str(raw)])
                ok = selected == expected
                correct += int(ok)
                incorrect += int(not ok)
            if not ok:
                focus.append(
                    (question.get("metadata") or {}).get("topic") or question.get("topic") or "Konsep dasar"
                )
            details.append({"question_id": qid, "correct": ok, "explanation": question.get("explanation")})
        total = len(questions)
        accuracy = round(correct / total * 100, 2) if total else 0.0
        xp = correct * 10 + (5 if accuracy >= 80 else 0)
        completed_at = self._now()
        result = {
            "score": correct,
            "total_questions": total,
            "accuracy": accuracy,
            "correct": correct,
            "incorrect": incorrect,
            "skipped": skipped,
            "xp_earned": xp,
            "level_completed": accuracy >= 70,
            "next_level_unlocked": accuracy >= 80,
            "analisis_performa": {
                "sorotan": ["Pemahaman konsep yang dijawab benar sudah baik."] if correct else [],
                "area_fokus": list(dict.fromkeys(focus))[:5],
            },
            "details": details,
        }
        if self.client.settings.allow_mock_services:
            self._attempts[attempt_id].update({"status": "completed", "completed_at": completed_at, **result})
        else:
            await self.client.update(
                "quiz_attempts",
                {"id": f"eq.{attempt_id}", "user_id": f"eq.{user_id}"},
                {
                    "status": "completed",
                    "completed_at": completed_at,
                    **{
                        k: result[k]
                        for k in [
                            "score",
                            "total_questions",
                            "accuracy",
                            "correct",
                            "incorrect",
                            "skipped",
                            "xp_earned",
                        ]
                    },
                },
            )
            xp_rows = await self.client.select(
                "user_xp", {"select": "xp", "user_id": f"eq.{user_id}", "limit": "1"}
            )
            current_xp = int(xp_rows[0]["xp"]) if xp_rows else 0
            await self.client.request(
                "POST",
                "user_xp",
                params={"on_conflict": "user_id"},
                json={"user_id": user_id, "xp": current_xp + xp, "updated_at": completed_at},
                prefer="resolution=merge-duplicates,return=minimal",
            )
            await self.client.request(
                "POST",
                "quiz_progress",
                params={"on_conflict": "user_id,level_id"},
                json={
                    "user_id": user_id,
                    "level_id": attempt["level_id"],
                    "unlocked": True,
                    "completed": accuracy >= 70,
                    "best_accuracy": accuracy,
                    "attempts_count": 1,
                    "updated_at": completed_at,
                },
                prefer="resolution=merge-duplicates,return=minimal",
            )
        return result

    async def new_progress(self, user_id: str) -> dict[str, Any]:
        return await self.repository.get_progress(user_id)

    async def topics(self, user_id: str) -> list[dict[str, Any]]:
        return await self.repository.get_topics_with_progress(user_id)

    async def create_session(self, user_id: str, topic_id: str, level_id: str | None, level_number: int | None):
        from app.services.quiz.quiz_seed import get_fallback_questions, merge_and_dedupe_questions

        level = await self.repository._find_level(topic_id, level_id=level_id, level_number=level_number or None)
        if not level:
            level = await self.repository._find_level(topic_id, level_number=level_number or 1)
        if not level:
            raise NotFoundError("Level quiz tidak ditemukan.")
        level_id = level["id"]
        level_number = int(level["level_number"])
        questions = await self.repository.get_questions_for_level(level_id, topic_id)
        fallback_questions = get_fallback_questions(topic_id, level_number)
        questions = self.repository.dedupe_questions(merge_and_dedupe_questions(questions, fallback_questions))[:10]
        if len(questions) < 10:
            raise NotFoundError("Level belum memiliki minimal 10 soal aktif.")
        return await self.repository.create_session(user_id, topic_id, level_id, questions)

    async def get_session(self, user_id: str, session_id: str):
        return await self.repository.get_session(user_id, session_id)

    async def submit_session_answer(self, user_id: str, session_id: str, question_id: str, answer: Any):
        return await self.repository.submit_answer(user_id, session_id, question_id, answer)

    async def session_summary(self, user_id: str, session_id: str):
        return await self.repository.get_summary(user_id, session_id)

    async def new_history(self, user_id: str):
        return await self.repository.get_history(user_id)

    async def history(self, user_id: str) -> list[dict[str, Any]]:
        if self.client.settings.allow_mock_services:
            return [
                a
                for a in self._attempts.values()
                if a["user_id"] == user_id and a.get("status") == "completed" and not a.get("deleted_at")
            ]
        return await self.client.select(
            "quiz_attempts",
            {"select": "*", "user_id": f"eq.{user_id}", "deleted_at": "is.null", "order": "started_at.desc"},
        )

    async def delete_history(self, user_id: str, attempt_id: str) -> None:
        await self.get_attempt(user_id, attempt_id)
        if self.client.settings.allow_mock_services:
            self._attempts[attempt_id]["deleted_at"] = self._now()
        else:
            await self.client.update(
                "quiz_attempts",
                {"id": f"eq.{attempt_id}", "user_id": f"eq.{user_id}"},
                {"deleted_at": self._now()},
            )

    async def progress(self, user_id: str) -> list[dict[str, Any]]:
        if self.client.settings.allow_mock_services:
            return [
                {
                    "level_id": "periodic-1",
                    "unlocked": True,
                    "completed": False,
                    "best_accuracy": 0,
                    "attempts_count": 0,
                }
            ]
        return await self.client.select(
            "quiz_progress",
            {"select": "*,quiz_levels(*)", "user_id": f"eq.{user_id}", "order": "updated_at.desc"},
        )
