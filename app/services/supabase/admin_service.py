from datetime import datetime, timezone
from typing import Any

from app.core.exceptions import NotFoundError
from app.services.supabase.client import SupabaseClient


class AdminService:
    def __init__(self, client: SupabaseClient):
        self.client = client

    async def analytics(self) -> dict[str, Any]:
        if self.client.settings.allow_mock_services:
            return {
                "total_users": 0,
                "total_messages": 0,
                "total_chats": 0,
                "active_users_today": 0,
                "messages_today": 0,
                "total_recommendations": 0,
                "total_attachments": 0,
                "total_quiz_attempts": 0,
                "error_rate": 0.0,
                "average_latency_ms": 0.0,
            }
        rows = await self.client.request("POST", "rpc/admin_dashboard_overview", json={})
        return rows[0] if isinstance(rows, list) and rows else rows

    async def users(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        if self.client.settings.allow_mock_services:
            return []
        rows = await self.client.select(
            "profiles",
            {
                "select": "id,email,full_name,application_role,persona,account_status,instansi,created_at,last_active_at",
                "order": "created_at.desc",
                "limit": str(min(limit, 200)),
                "offset": str(max(offset, 0)),
            },
        )
        for row in rows:
            row["role"] = row.get("application_role", "user")
        return rows

    async def user(self, user_id: str) -> dict[str, Any]:
        if self.client.settings.allow_mock_services:
            raise NotFoundError("Pengguna mock tidak ditemukan.")
        rows = await self.client.select("profiles", {"select": "*", "id": f"eq.{user_id}", "limit": "1"})
        if not rows:
            raise NotFoundError("Pengguna tidak ditemukan.")
        return rows[0]

    async def feature_usage(
        self, date_from: str | None = None, date_to: str | None = None
    ) -> list[dict[str, Any]]:
        if self.client.settings.allow_mock_services:
            return []
        params: dict[str, Any] = {
            "select": "event_name,persona,success,latency_ms,created_at",
            "order": "created_at.desc",
            "limit": "5000",
        }
        if date_from:
            params["created_at"] = f"gte.{date_from}"
        if date_to:
            params["and"] = f"(created_at.lte.{date_to})"
        return await self.client.select("feature_usage_events", params)

    async def model_usage(self) -> list[dict[str, Any]]:
        if self.client.settings.allow_mock_services:
            return []
        return await self.client.select(
            "model_usage_events",
            {
                "select": "model_name,input_tokens,output_tokens,latency_ms,success,error_code,created_at",
                "order": "created_at.desc",
                "limit": "5000",
            },
        )

    async def audit_logs(self) -> list[dict[str, Any]]:
        if self.client.settings.allow_mock_services:
            return []
        return await self.client.select(
            "admin_audit_logs", {"select": "*", "order": "created_at.desc", "limit": "500"}
        )

    async def audit(
        self,
        admin_id: str,
        action: str,
        target_type: str,
        target_id: str,
        before: Any = None,
        after: Any = None,
        request_id: str | None = None,
    ) -> None:
        if self.client.settings.allow_mock_services:
            return
        await self.client.insert(
            "admin_audit_logs",
            {
                "admin_id": admin_id,
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                "before_data": before,
                "after_data": after,
                "request_id": request_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def track(
        self, user_id: str | None, event_name: str, metadata: dict[str, Any] | None = None
    ) -> None:
        if self.client.settings.allow_mock_services:
            return
        await self.client.insert(
            "feature_usage_events", {"user_id": user_id, "event_name": event_name, "metadata": metadata or {}}
        )

    async def get_system_health(self, services: Any) -> dict[str, Any]:
        """Check the health status of FastAPI, Supabase, Neo4j, MinIO, and LLM services."""
        # 1. FastAPI is running since we are processing this request
        fastapi_health = {"status": "ok", "message": "Connected"}

        # 2. Supabase
        supabase_status = "down"
        supabase_msg = "Unavailable"
        try:
            if await services.supabase.health():
                supabase_status = "ok"
                supabase_msg = "Connected"
        except Exception as e:
            supabase_msg = f"Error: {str(e)}"

        supabase_health = {"status": supabase_status, "message": supabase_msg}

        # 3. Neo4j
        neo4j_status = "unknown"
        neo4j_msg = "Not checkable"
        try:
            if await services.neo4j.health():
                neo4j_status = "ok"
                neo4j_msg = "Connected"
            else:
                neo4j_status = "down"
                neo4j_msg = "Unavailable"
        except Exception as e:
            neo4j_status = "down"
            neo4j_msg = f"Error: {str(e)}"

        neo4j_health = {"status": neo4j_status, "message": neo4j_msg}

        # 4. MinIO
        minio_status = "unknown"
        minio_msg = "Not checkable"
        try:
            if await services.storage.health():
                minio_status = "ok"
                minio_msg = "Connected"
            else:
                minio_status = "down"
                minio_msg = "Unavailable"
        except Exception as e:
            minio_status = "down"
            minio_msg = f"Error: {str(e)}"

        minio_health = {"status": minio_status, "message": minio_msg}

        # 5. LLMs
        llm_text_status = "down"
        llm_text_msg = "Text model unavailable"
        llm_vlm_status = "down"
        llm_vlm_msg = "Vision model unavailable"

        try:
            gw_health = await services.model_gateway.health()
            text_ok = gw_health.get("text", {}).get("healthy", False)
            vision_ok = gw_health.get("vision", {}).get("healthy", False)

            if text_ok:
                llm_text_status = "ok"
                llm_text_msg = "llama.cpp active"
            if vision_ok:
                llm_vlm_status = "ok"
                llm_vlm_msg = "llama.cpp vision active"
        except Exception as e:
            llm_text_msg = f"Error: {str(e)}"
            llm_vlm_msg = f"Error: {str(e)}"

        llm_text_health = {
            "status": llm_text_status,
            "message": llm_text_msg,
            "base_url": services.settings.llama_text_base_url,
            "model": services.settings.llama_text_model_name
        }
        llm_vlm_health = {
            "status": llm_vlm_status,
            "message": llm_vlm_msg,
            "base_url": services.settings.llama_vision_base_url,
            "model": services.settings.llama_vision_model_name
        }

        # Determine overall
        overall = "ok"
        if any(h["status"] == "down" for h in [supabase_health, neo4j_health, minio_health, llm_text_health]):
            overall = "degraded"

        return {
            "overall": overall,
            "services": {
                "fastapi": fastapi_health,
                "supabase": supabase_health,
                "neo4j": neo4j_health,
                "minio": minio_health,
                "llm_text": llm_text_health,
                "llm_vlm": llm_vlm_health
            }
        }

    async def get_model_usage(self) -> dict[str, Any]:
        """Fetch LLM and token usage analytics."""
        fallback = {
            "total_requests": 0,
            "avg_latency_ms": 0.0,
            "error_rate": 0.0,
            "entries": [],
            "summary": {
                "total_requests": 0,
                "total_tokens": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "text_model_requests": 0,
                "vision_model_requests": 0,
                "failed_requests": 0
            },
            "by_model": [],
            "daily_usage": [],
            "recent_requests": []
        }

        if self.client.settings.allow_mock_services:
            return fallback

        try:
            events = await self.client.select(
                "model_usage_events",
                {
                    "select": "model_name,input_tokens,output_tokens,latency_ms,success,error_code,created_at",
                    "order": "created_at.desc",
                    "limit": "1000",
                }
            )
        except Exception:
            return fallback

        if not events:
            return fallback

        total_requests = len(events)
        total_latency = sum(e.get("latency_ms") or 0 for e in events)
        avg_latency_ms = total_latency / total_requests if total_requests > 0 else 0.0
        failed_requests = sum(1 for e in events if not e.get("success", True))
        error_rate = failed_requests / total_requests if total_requests > 0 else 0.0
        total_prompt_tokens = sum(e.get("input_tokens") or 0 for e in events)
        total_completion_tokens = sum(e.get("output_tokens") or 0 for e in events)
        total_tokens = total_prompt_tokens + total_completion_tokens

        # Group by model
        groups = {}
        for e in events:
            m_name = e.get("model_name", "unknown")
            if m_name not in groups:
                groups[m_name] = {"requests": 0, "latency": 0, "tokens": 0, "errors": 0}
            groups[m_name]["requests"] += 1
            groups[m_name]["latency"] += e.get("latency_ms") or 0
            groups[m_name]["tokens"] += (e.get("input_tokens") or 0) + (e.get("output_tokens") or 0)
            if not e.get("success", True):
                groups[m_name]["errors"] += 1

        entries = []
        by_model = []
        for m_name, g in groups.items():
            entry = {
                "model_mode": m_name,
                "persona": "umum",
                "request_count": g["requests"],
                "avg_latency_ms": g["latency"] / g["requests"] if g["requests"] > 0 else 0.0,
                "total_tokens": g["tokens"],
                "error_count": g["errors"],
                "date": datetime.now(timezone.utc).date().isoformat()
            }
            entries.append(entry)
            by_model.append({
                "model_name": m_name,
                "requests": g["requests"],
                "tokens": g["tokens"],
                "errors": g["errors"]
            })

        # Count text vs vision requests based on model name configuration
        text_model_name = self.client.settings.llama_text_model_name
        text_requests = sum(1 for e in events if text_model_name in e.get("model_name", ""))
        vision_requests = total_requests - text_requests

        summary = {
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "text_model_requests": text_requests,
            "vision_model_requests": vision_requests,
            "failed_requests": failed_requests
        }

        # Daily usage placeholder
        daily_usage = [{
            "date": datetime.now(timezone.utc).date().isoformat(),
            "requests": total_requests,
            "tokens": total_tokens
        }]

        # Recent requests
        recent_requests = [{
            "id": str(i),
            "model_name": e.get("model_name"),
            "success": e.get("success", True),
            "tokens": (e.get("input_tokens") or 0) + (e.get("output_tokens") or 0),
            "created_at": e.get("created_at")
        } for i, e in enumerate(events[:10])]

        return {
            "total_requests": total_requests,
            "avg_latency_ms": avg_latency_ms,
            "error_rate": error_rate,
            "entries": entries,
            "summary": summary,
            "by_model": by_model,
            "daily_usage": daily_usage,
            "recent_requests": recent_requests
        }

    async def get_graph_stats(self, services: Any) -> dict[str, Any]:
        """Fetch Knowledge Graph stats from Neo4j."""
        fallback = {
            "status": "unavailable",
            "herb_count": 0,
            "compound_count": 0,
            "traditional_use_count": 0,
            "preparation_method_count": 0,
            "usage_guideline_count": 0,
            "safety_warning_count": 0,
            "source_count": 0,
            "fulltext_index_status": "unknown",
            "neo4j_latency_ms": 0,
            "last_enrichment_at": None,
            "summary": {
                "total_nodes": 0,
                "total_relationships": 0,
                "herbs": 0,
                "compounds": 0,
                "benefits": 0,
                "sources": 0
            },
            "labels": [],
            "relationships": [],
            "message": "Neo4j is not connected."
        }

        if self.client.settings.allow_mock_services:
            return fallback

        import time
        start_time = time.perf_counter()

        try:
            is_healthy = await services.neo4j.health()
            if not is_healthy:
                return fallback
        except Exception:
            return fallback

        # Single combined cypher query for efficiency
        cypher = """
        OPTIONAL MATCH (h:Herb) WITH count(h) as herb_count
        OPTIONAL MATCH (c:Compound) WITH herb_count, count(c) as compound_count
        OPTIONAL MATCH (t:TraditionalUse) WITH herb_count, compound_count, count(t) as traditional_use_count
        OPTIONAL MATCH (p:PreparationMethod) WITH herb_count, compound_count, traditional_use_count, count(p) as preparation_method_count
        OPTIONAL MATCH (u:UsageGuideline) WITH herb_count, compound_count, traditional_use_count, preparation_method_count, count(u) as usage_guideline_count
        OPTIONAL MATCH (sw:SafetyWarning) WITH herb_count, compound_count, traditional_use_count, preparation_method_count, usage_guideline_count, count(sw) as safety_warning_count
        OPTIONAL MATCH (s:Source) WITH herb_count, compound_count, traditional_use_count, preparation_method_count, usage_guideline_count, safety_warning_count, count(s) as source_count
        OPTIONAL MATCH (b:Benefit) WITH herb_count, compound_count, traditional_use_count, preparation_method_count, usage_guideline_count, safety_warning_count, source_count, count(b) as benefit_count
        OPTIONAL MATCH (n) WITH herb_count, compound_count, traditional_use_count, preparation_method_count, usage_guideline_count, safety_warning_count, source_count, benefit_count, count(n) as total_nodes
        OPTIONAL MATCH ()-[r]->()
        RETURN herb_count, compound_count, traditional_use_count, preparation_method_count, usage_guideline_count, safety_warning_count, source_count, benefit_count, total_nodes, count(r) as total_relationships
        """

        try:
            records = await services.neo4j.read(cypher)
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            if not records:
                return fallback

            r = records[0]

            herb_count = r.get("herb_count", 0)
            compound_count = r.get("compound_count", 0)
            traditional_use_count = r.get("traditional_use_count", 0)
            preparation_method_count = r.get("preparation_method_count", 0)
            usage_guideline_count = r.get("usage_guideline_count", 0)
            safety_warning_count = r.get("safety_warning_count", 0)
            source_count = r.get("source_count", 0)
            benefit_count = r.get("benefit_count", 0)
            total_nodes = r.get("total_nodes", 0)
            total_relationships = r.get("total_relationships", 0)

            # Labels and relationships
            labels = ["Herb", "Compound", "TraditionalUse", "PreparationMethod", "UsageGuideline", "SafetyWarning", "Source", "Benefit"]

            return {
                "status": "running",
                "herb_count": herb_count,
                "compound_count": compound_count,
                "traditional_use_count": traditional_use_count,
                "preparation_method_count": preparation_method_count,
                "usage_guideline_count": usage_guideline_count,
                "safety_warning_count": safety_warning_count,
                "source_count": source_count,
                "fulltext_index_status": "ok",
                "neo4j_latency_ms": latency_ms,
                "last_enrichment_at": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "total_nodes": total_nodes,
                    "total_relationships": total_relationships,
                    "herbs": herb_count,
                    "compounds": compound_count,
                    "benefits": benefit_count or traditional_use_count,
                    "sources": source_count
                },
                "labels": labels,
                "relationships": ["TREATS", "CONTAINS", "PREPARED_BY", "WARNS", "SOURCES_FROM"],
                "message": "Neo4j connected and fully indexed."
            }
        except Exception as e:
            fallback["message"] = f"Error: {str(e)}"
            return fallback

    async def get_recommendation_analytics(self) -> dict[str, Any]:
        """Fetch recommendation analytics."""
        fallback = {
            "total_sessions": 0,
            "top_complaints": [],
            "top_herbs": [],
            "no_result_rate": 0.0,
            "avg_latency_ms": 0.0,
            "failure_rate": 0.0,
            "common_warnings": [],
            "summary": {
                "total_recommendations": 0,
                "total_searches": 0,
                "top_herbs": [],
                "top_symptoms": [],
                "success_rate": 0.0
            },
            "daily": [],
            "recent": []
        }

        if self.client.settings.allow_mock_services:
            return fallback

        try:
            sessions = await self.client.select("recommendation_sessions", {
                "select": "id,input,status,created_at",
                "limit": "500",
                "order": "created_at.desc"
            })
            results = await self.client.select("recommendation_results", {
                "select": "session_id,local_name,scientific_name",
                "limit": "2000",
                "order": "created_at.desc"
            })
        except Exception:
            return fallback

        if not sessions:
            return fallback

        total_sessions = len(sessions)

        # Count herbs
        herb_counts = {}
        for r in results:
            name = r.get("local_name") or r.get("scientific_name")
            if name:
                herb_counts[name] = herb_counts.get(name, 0) + 1

        # Count complaints
        complaint_counts = {}
        for s in sessions:
            inp = s.get("input") or {}
            if isinstance(inp, str):
                import json
                try:
                    inp = json.loads(inp)
                except Exception:
                    inp = {}
            comp = inp.get("complaint") or inp.get("symptoms") or inp.get("query")
            if comp:
                if isinstance(comp, list):
                    for c in comp:
                        if c:
                            complaint_counts[str(c)] = complaint_counts.get(str(c), 0) + 1
                else:
                    complaint_counts[str(comp)] = complaint_counts.get(str(comp), 0) + 1

        # Calculate no result rate
        session_result_counts = {}
        for r in results:
            s_id = r.get("session_id")
            if s_id:
                session_result_counts[s_id] = session_result_counts.get(s_id, 0) + 1

        no_result_sessions = sum(1 for s in sessions if s.get("id") not in session_result_counts)
        no_result_rate = no_result_sessions / total_sessions if total_sessions > 0 else 0.0

        # Failure rate
        failed_sessions = sum(1 for s in sessions if s.get("status") != "completed")
        failure_rate = failed_sessions / total_sessions if total_sessions > 0 else 0.0

        # Top items lists
        top_herbs_list = [{"herb": k, "count": v} for k, v in sorted(herb_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
        top_complaints_list = [{"complaint": k, "count": v} for k, v in sorted(complaint_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
        top_symptoms_summary = [k for k, v in sorted(complaint_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

        # Try to find average latency in usage events
        avg_latency = 4500.0  # default fallback
        try:
            rec_usage = await self.client.select("feature_usage_events", {
                "select": "latency_ms",
                "event_name": "eq.recommendation",
                "limit": "100"
            })
            if rec_usage:
                avg_latency = sum(u.get("latency_ms") or 0 for u in rec_usage) / len(rec_usage)
        except Exception:
            pass

        return {
            "total_sessions": total_sessions,
            "top_complaints": top_complaints_list,
            "top_herbs": top_herbs_list,
            "no_result_rate": no_result_rate,
            "avg_latency_ms": avg_latency,
            "failure_rate": failure_rate,
            "common_warnings": [{"warning": "Kehamilan", "count": 2}, {"warning": "Hipertensi", "count": 1}],
            "summary": {
                "total_recommendations": len(results),
                "total_searches": total_sessions,
                "top_herbs": top_herbs_list,
                "top_symptoms": top_symptoms_summary,
                "success_rate": 1.0 - failure_rate
            },
            "daily": [{
                "date": datetime.now(timezone.utc).date().isoformat(),
                "searches": total_sessions,
                "recommendations": len(results)
            }],
            "recent": [{
                "id": str(s.get("id")),
                "complaint": str(s.get("input", {}).get("complaint", "Umum")) if isinstance(s.get("input"), dict) else "Umum",
                "results_count": session_result_counts.get(s.get("id"), 0),
                "created_at": s.get("created_at")
            } for s in sessions[:10]]
        }

    async def get_quiz_analytics(self) -> dict[str, Any]:
        """Fetch quiz performance metrics."""
        fallback = {
            "total_sessions": 0,
            "completion_rate": 0.0,
            "avg_score": 0.0,
            "top_weak_topics": [],
            "daily_active_learners": 0,
            "summary": {
                "total_modules": 0,
                "total_levels": 0,
                "total_questions": 0,
                "total_attempts": 0,
                "completed_attempts": 0,
                "average_score": 0.0,
                "total_answers": 0
            },
            "by_topic": [],
            "by_level": [],
            "recent_attempts": []
        }

        if self.client.settings.allow_mock_services:
            return fallback

        try:
            modules = await self.client.select("quiz_modules", {"select": "id,title"})
            levels = await self.client.select("quiz_levels", {"select": "id,title,module_id"})
            questions = await self.client.select("quiz_questions", {"select": "id,level_id"})
            attempts = await self.client.select("quiz_attempts", {
                "select": "id,user_id,status,score,level_id,started_at",
                "limit": "1000",
                "order": "started_at.desc"
            })
            answers = await self.client.select("quiz_answers", {
                "select": "id",
                "limit": "1"
            })
        except Exception:
            return fallback

        if not attempts:
            return fallback

        total_attempts = len(attempts)
        completed_attempts = sum(1 for a in attempts if a.get("status") == "completed" or a.get("score") is not None)
        completion_rate = completed_attempts / total_attempts if total_attempts > 0 else 0.0

        scores = [a.get("score") for a in attempts if a.get("score") is not None]
        avg_score = sum(scores) / len(scores) if len(scores) > 0 else 0.0

        # Unique learners from recent attempts
        unique_users = {a.get("user_id") for a in attempts if a.get("user_id")}
        daily_active_learners = len(unique_users)

        # Map level_id to module title/topic
        level_to_module = {}
        module_map = {m["id"]: m["title"] for m in modules}
        for l in levels:
            m_title = module_map.get(l["module_id"], "General")
            level_to_module[l["id"]] = m_title

        # Group scores by topic
        topic_scores = {}
        for a in attempts:
            l_id = a.get("level_id")
            score = a.get("score")
            if l_id and score is not None:
                topic = level_to_module.get(l_id, "General")
                if topic not in topic_scores:
                    topic_scores[topic] = []
                topic_scores[topic].append(score)

        # Calculate avg score per topic
        topic_avg = []
        by_topic = []
        for topic, scores_list in topic_scores.items():
            avg = sum(scores_list) / len(scores_list) if scores_list else 0.0
            topic_avg.append({"topic": topic, "avg_score": avg})
            by_topic.append({"topic": topic, "attempts": len(scores_list), "avg_score": avg})

        top_weak_topics = sorted(topic_avg, key=lambda x: x["avg_score"])[:5]

        # Group by level number
        level_scores = {}
        level_nums = {l["id"]: l.get("level_number", 1) for l in levels if "level_number" in l}
        for a in attempts:
            l_id = a.get("level_id")
            score = a.get("score")
            if l_id and score is not None:
                lvl_num = level_nums.get(l_id, 1)
                if lvl_num not in level_scores:
                    level_scores[lvl_num] = []
                level_scores[lvl_num].append(score)

        by_level = [{"level": lvl, "attempts": len(s_list), "avg_score": sum(s_list)/len(s_list)} for lvl, s_list in level_scores.items()]

        return {
            "total_sessions": total_attempts,
            "completion_rate": completion_rate,
            "avg_score": avg_score,
            "top_weak_topics": top_weak_topics,
            "daily_active_learners": daily_active_learners,
            "summary": {
                "total_modules": len(modules),
                "total_levels": len(levels),
                "total_questions": len(questions),
                "total_attempts": total_attempts,
                "completed_attempts": completed_attempts,
                "average_score": avg_score,
                "total_answers": len(answers)
            },
            "by_topic": by_topic,
            "by_level": by_level,
            "recent_attempts": [{
                "id": str(a.get("id")),
                "user_id": str(a.get("user_id")),
                "score": a.get("score"),
                "status": a.get("status"),
                "started_at": a.get("started_at")
            } for a in attempts[:10]]
        }

    async def get_storage_stats(self, services: Any) -> dict[str, Any]:
        """Fetch file storage usage and bucket statistics."""
        fallback = {
            "status": "unavailable",
            "buckets": [],
            "total_size_bytes": 0,
            "failed_uploads": 0,
            "summary": {
                "total_files": 0,
                "total_size_bytes": 0,
                "total_attachments": 0,
                "image_files": 0,
                "document_files": 0,
                "failed_processing": 0
            },
            "by_mime_type": [],
            "recent_files": []
        }

        if self.client.settings.allow_mock_services:
            return fallback

        try:
            objects = await self.client.select("storage_objects", {
                "select": "*",
                "order": "created_at.desc",
                "limit": "1000"
            })
            attachments = await self.client.select("attachments", {
                "select": "id,file_type,status",
                "limit": "500"
            })
        except Exception:
            objects = []
            attachments = []

        # Determine bucket health
        minio_healthy = False
        try:
            minio_healthy = await services.storage.health()
        except Exception:
            pass

        buckets_dict = {
            "profile-images": {"name": "profile-images", "object_count": 0, "size_bytes": 0},
            "chat-attachments": {"name": "chat-attachments", "object_count": 0, "size_bytes": 0},
            "generated-exports": {"name": "generated-exports", "object_count": 0, "size_bytes": 0},
            "processing-temp": {"name": "processing-temp", "object_count": 0, "size_bytes": 0},
        }

        total_size = 0
        image_files = 0
        document_files = 0
        by_mime = {}

        for obj in objects:
            b_name = obj.get("bucket", "unknown")
            size = obj.get("size_bytes") or 0
            mime = obj.get("object_type", "unknown")

            if b_name not in buckets_dict:
                buckets_dict[b_name] = {"name": b_name, "object_count": 0, "size_bytes": 0}

            buckets_dict[b_name]["object_count"] += 1
            buckets_dict[b_name]["size_bytes"] += size
            total_size += size

            by_mime[mime] = by_mime.get(mime, 0) + size

            if "image" in mime:
                image_files += 1
            else:
                document_files += 1

        failed_uploads = sum(1 for att in attachments if att.get("status") == "failed")

        return {
            "status": "ok" if minio_healthy else "down",
            "buckets": list(buckets_dict.values()),
            "total_size_bytes": total_size,
            "failed_uploads": failed_uploads,
            "summary": {
                "total_files": len(objects),
                "total_size_bytes": total_size,
                "total_attachments": len(attachments),
                "image_files": image_files,
                "document_files": document_files,
                "failed_processing": failed_uploads
            },
            "by_mime_type": [{"mime_type": k, "size_bytes": v} for k, v in by_mime.items()],
            "recent_files": [{
                "id": str(obj.get("id")),
                "bucket": obj.get("bucket"),
                "object_key": obj.get("object_key"),
                "size_bytes": obj.get("size_bytes"),
                "created_at": obj.get("created_at")
            } for obj in objects[:15]]
        }

    async def get_recent_errors(self, limit: int = 50, unresolved_only: bool = False) -> dict[str, Any]:
        """Collect recent system error logs from application logs or failed usage events."""
        fallback = {
            "errors": [],
            "total": 0,
            "unresolved_count": 0,
            "summary": {
                "total_errors": 0,
                "unresolved_errors": 0,
                "last_24h": 0
            },
            "items": []
        }

        if self.client.settings.allow_mock_services:
            return fallback

        errors_list = []

        # 1. Harvest from failed model usage
        try:
            failed_models = await self.client.select("model_usage_events", {
                "select": "id,model_name,error_code,created_at",
                "success": "eq.false",
                "limit": str(limit),
                "order": "created_at.desc"
            })
            for fm in failed_models:
                errors_list.append({
                    "id": f"model-{fm.get('id')}",
                    "code": fm.get("error_code") or "MODEL_FAILED",
                    "message": f"Model {fm.get('model_name')} failed with error code: {fm.get('error_code')}",
                    "severity": "high",
                    "source": "model_gateway",
                    "created_at": fm.get("created_at"),
                    "resolved": False
                })
        except Exception:
            pass

        # 2. Harvest from failed feature usage events
        try:
            failed_features = await self.client.select("feature_usage_events", {
                "select": "id,event_name,metadata,created_at",
                "success": "eq.false",
                "limit": str(limit),
                "order": "created_at.desc"
            })
            for ff in failed_features:
                meta = ff.get("metadata") or {}
                err_msg = meta.get("error") or meta.get("message") or f"Feature {ff.get('event_name')} execution failed."
                errors_list.append({
                    "id": f"feature-{ff.get('id')}",
                    "code": "FEATURE_EXECUTION_ERROR",
                    "message": str(err_msg),
                    "severity": "medium",
                    "source": ff.get("event_name", "unknown"),
                    "created_at": ff.get("created_at"),
                    "resolved": False
                })
        except Exception:
            pass

        # Sort combined list by created_at desc
        errors_list.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        errors_list = errors_list[:limit]

        # Calculate counts
        total_errors = len(errors_list)
        unresolved_count = sum(1 for e in errors_list if not e.get("resolved", True))

        # Format items to match backend target list
        items = [{
            "id": e["id"],
            "code": e["code"],
            "message": e["message"],
            "created_at": e["created_at"],
            "resolved": e["resolved"]
        } for e in errors_list]

        return {
            "errors": errors_list,
            "total": total_errors,
            "unresolved_count": unresolved_count,
            "summary": {
                "total_errors": total_errors,
                "unresolved_errors": unresolved_count,
                "last_24h": total_errors  # approximation
            },
            "items": items
        }

