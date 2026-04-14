# -*- coding: utf-8 -*-
"""
API Router for AI Evaluation endpoints.
"""

from datetime import datetime
from pathlib import Path
import sys

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Add project root for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.evaluation import (
    BatchGradingRequest,
    EvaluationConfig,
    GradingRequest,
    GradingResponse,
    GradingService,
    get_evaluation_config,
)
from src.logging import get_logger


logger = get_logger("EvaluationAPI")

router = APIRouter()

# Initialize service
_grading_service: GradingService | None = None


def get_grading_service() -> GradingService:
    """Get or create grading service singleton."""
    global _grading_service
    if _grading_service is None:
        config = get_evaluation_config()
        _grading_service = GradingService(config)
    return _grading_service


# --- Request/Response Models ---


class SingleGradingRequest(BaseModel):
    """Request to grade a single submission."""
    student_id: str
    assignment_id: str
    items: list
    use_multimodal: bool = False
    scoring_ruleset_id: str | None = None


class SingleGradingResponse(BaseModel):
    """Response for single grading request."""
    submission_id: str
    student_id: str
    assignment_id: str
    status: str
    results: list
    total_score: float
    max_total_score: float
    overall_feedback: str
    graded_at: datetime | None


# --- Endpoints ---


@router.post("/grade", response_model=SingleGradingResponse)
async def grade_submission(request: SingleGradingRequest):
    """
    Grade a student submission.
    
    Accepts a submission with questions and student answers,
    returns detailed grading results.
    """
    service = get_grading_service()
    
    # Convert to grading request
    grading_req = GradingRequest(
        submission_id=f"sub_{datetime.utcnow().timestamp()}",
        student_id=request.student_id,
        assignment_id=request.assignment_id,
        items=request.items,
        use_multimodal=request.use_multimodal,
        scoring_ruleset_id=request.scoring_ruleset_id,
    )
    
    try:
        result = await service.grade_submission(grading_req)
        
        return SingleGradingResponse(
            submission_id=result.submission_id,
            student_id=result.student_id,
            assignment_id=result.assignment_id,
            status=result.status.value,
            results=[
                {
                    "question_id": r.question_id,
                    "score": r.score,
                    "max_score": r.max_score,
                    "feedback": r.feedback,
                    "details": r.details,
                }
                for r in result.results
            ],
            total_score=result.total_score,
            max_total_score=result.max_total_score,
            overall_feedback=result.overall_feedback,
            graded_at=result.graded_at,
        )
        
    except Exception as e:
        logger.error(f"Grading failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/grade/batch")
async def grade_batch(request: BatchGradingRequest):
    """
    Grade multiple submissions in batch.
    
    Returns results for all submissions.
    """
    service = get_grading_service()
    
    try:
        results = await service.grade_batch(request)
        
        return {
            "total": len(results),
            "completed": sum(1 for r in results if r.status == "completed"),
            "failed": sum(1 for r in results if r.status == "failed"),
            "results": [
                {
                    "submission_id": r.submission_id,
                    "status": r.status,
                    "total_score": r.total_score,
                    "max_total_score": r.max_total_score,
                }
                for r in results
            ],
        }
        
    except Exception as e:
        logger.error(f"Batch grading failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/{submission_id}")
async def get_grading_result(submission_id: str):
    """Get a previously saved grading result."""
    service = get_grading_service()
    
    # Try to load from storage
    config = get_evaluation_config()
    filepath = Path(config.grading_results_dir) / f"{submission_id}.json"
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Submission not found")
    
    import json
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    
    return data


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    config = get_evaluation_config()
    return {
        "status": "healthy",
        "llm_provider": config.llm.provider,
        "llm_model": config.llm.model,
        "qdrant_url": config.qdrant.url,
    }
