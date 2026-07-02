"""Isolated evaluation API router — admin-only, zero disruption to existing endpoints."""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies.roles import require_admin
from app.api.dependencies.services import Services, get_services
from app.evaluation.ragas_engine import (
    DEFAULT_TEST_CASES,
    EvaluationTestCase,
    run_evaluation,
)
from app.models.auth import CurrentUser

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Evaluation"])


class RagasEvaluationRequest(BaseModel):
    """Optional request body — omit fields to use defaults."""

    test_cases: list[EvaluationTestCase] | None = None


@router.post("/api/admin/evaluate-ragas")
async def evaluate_ragas(
    payload: RagasEvaluationRequest | None = None,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
) -> dict:
    """Run Ragas evaluation on the GraphRAG pipeline.

    Accepts optional curated test cases in the request body.
    Falls back to hardcoded default test cases if none provided.
    """
    test_cases = (payload.test_cases if payload and payload.test_cases else None) or DEFAULT_TEST_CASES

    logger.info(
        "ragas_evaluation_started",
        extra={"admin_id": admin.id, "test_case_count": len(test_cases)},
    )

    result = await run_evaluation(services, test_cases)

    logger.info(
        "ragas_evaluation_completed",
        extra={
            "admin_id": admin.id,
            "elapsed_seconds": result.elapsed_seconds,
            "error": result.error,
        },
    )

    return {
        "success": result.error is None,
        "data": {
            "overall_metrics": result.overall_metrics,
            "per_test_case": result.per_test_case,
            "test_case_count": result.test_case_count,
            "elapsed_seconds": result.elapsed_seconds,
            "csv_path": result.csv_path,
        },
        "error": result.error,
    }
