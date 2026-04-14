# -*- coding: utf-8 -*-
"""
AI Grading Service.
Main service for auto-grading assignments and exams.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.logging import get_logger

from .config import EvaluationConfig, get_evaluation_config
from .models import (
    GradingRequest,
    GradingResponse,
    GradingResult,
    GradingStatus,
    QuestionType,
    ScoringRuleSet,
    SubmissionCreate,
    SubmissionItem,
    BatchGradingRequest,
)
from .multimodal import MultimodalLLMService
from .scoring_engine import ScoringEngine


logger = get_logger(__name__)


class GradingService:
    """
    AI-powered grading service.
    
    Features:
    - Multi-modal grading (text, images, PDFs)
    - Configurable scoring rules
    - Batch processing
    - Detailed feedback generation
    - Progress tracking
    """

    def __init__(self, config: Optional[EvaluationConfig] = None):
        self.config = config or get_evaluation_config()
        self._llm_service: Optional[MultimodalLLMService] = None
        self._scoring_engine = ScoringEngine(self.config)
        self._rulesets: Dict[str, ScoringRuleSet] = {}
        
        # Ensure directories exist
        Path(self.config.rubrics_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.grading_results_dir).mkdir(parents=True, exist_ok=True)

    @property
    def llm_service(self) -> MultimodalLLMService:
        """Lazy-load multimodal LLM service."""
        if self._llm_service is None:
            self._llm_service = MultimodalLLMService(self.config)
        return self._llm_service

    async def grade_submission(
        self, request: GradingRequest
    ) -> GradingResponse:
        """
        Grade a complete submission.
        
        Args:
            request: Grading request with submission details
            
        Returns:
            Complete grading response with per-question results
        """
        submission_id = request.submission_id
        logger.info(f"Starting grading for submission {submission_id}")
        
        results: List[GradingResult] = []
        total_score = 0.0
        max_total_score = 0.0
        
        # Load ruleset if specified
        ruleset = None
        if request.scoring_ruleset_id:
            ruleset = self._load_ruleset(request.scoring_ruleset_id)
        
        for item in request.items:
            start_time = time.time()
            max_total_score += item.max_score
            
            try:
                result = await self._grade_item(
                    item=item,
                    student_id=request.student_id,
                    ruleset=ruleset,
                    use_multimodal=request.use_multimodal,
                )
                result.processing_time_ms = (time.time() - start_time) * 1000
                
            except Exception as e:
                logger.error(f"Failed to grade question {item.question_id}: {e}")
                result = GradingResult(
                    question_id=item.question_id,
                    score=0,
                    max_score=item.max_score,
                    feedback=f"Grading failed: {str(e)}",
                    details={"error": str(e)},
                )
            
            results.append(result)
            total_score += result.score
        
        # Generate overall feedback
        overall_feedback = self._generate_overall_feedback(results, total_score, max_total_score)
        
        response = GradingResponse(
            submission_id=submission_id,
            student_id=request.student_id,
            assignment_id=request.assignment_id,
            status=GradingStatus.COMPLETED,
            results=results,
            total_score=total_score,
            max_total_score=max_total_score,
            overall_feedback=overall_feedback,
            graded_at=datetime.utcnow(),
        )
        
        # Save results
        await self._save_grading_result(response)
        
        logger.info(
            f"Completed grading for submission {submission_id}: "
            f"{total_score:.1f}/{max_total_score}"
        )
        
        return response

    async def grade_batch(
        self, batch_request: BatchGradingRequest
    ) -> List[GradingResponse]:
        """
        Grade multiple submissions in batch.
        
        Args:
            batch_request: Batch of grading requests
            
        Returns:
            List of grading responses
        """
        if batch_request.parallel:
            tasks = [
                self.grade_submission(req)
                for req in batch_request.submissions
            ]
            
            # Process with semaphore to limit concurrency
            semaphore = asyncio.Semaphore(batch_request.max_parallel_jobs)
            
            async def bounded_grade(req):
                async with semaphore:
                    return await self.grade_submission(req)
            
            results = await asyncio.gather(
                *[bounded_grade(req) for req in batch_request.submissions],
                return_exceptions=True,
            )
            
            # Filter out exceptions
            responses = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Batch item {i} failed: {result}")
                    responses.append(
                        GradingResponse(
                            submission_id=batch_request.submissions[i].submission_id,
                            student_id=batch_request.submissions[i].student_id,
                            assignment_id=batch_request.submissions[i].assignment_id,
                            status=GradingStatus.FAILED,
                            results=[],
                            total_score=0,
                            max_total_score=0,
                            overall_feedback=f"Batch processing failed: {str(result)}",
                        )
                    )
                else:
                    responses.append(result)
            
            return responses
        else:
            # Sequential processing
            responses = []
            for req in batch_request.submissions:
                response = await self.grade_submission(req)
                responses.append(response)
            return responses

    async def _grade_item(
        self,
        item: SubmissionItem,
        student_id: str,
        ruleset: Optional[ScoringRuleSet],
        use_multimodal: bool,
    ) -> GradingResult:
        """Grade a single question/item."""
        
        # Load rules for this question type
        rules = []
        if ruleset:
            rules = [r for r in ruleset.rules if r.question_type == item.question_type]
        
        # Handle based on question type
        if item.question_type == QuestionType.MULTIPLE_CHOICE:
            return await self._grade_multiple_choice(item)
        
        elif item.question_type == QuestionType.TRUE_FALSE:
            return await self._grade_true_false(item)
        
        elif item.question_type in (QuestionType.SHORT_ANSWER, QuestionType.FILL_IN_BLANK):
            # Use scoring engine first, fall back to LLM if no rules
            if rules:
                return self._scoring_engine.evaluate(
                    question_id=item.question_id,
                    student_answer=item.student_answer,
                    question_type=item.question_type,
                    max_score=item.max_score,
                    rules=rules,
                )
            elif item.expected_answer:
                # Simple exact match fallback
                is_correct = str(item.student_answer).strip().lower() == str(item.expected_answer).strip().lower()
                return GradingResult(
                    question_id=item.question_id,
                    score=item.max_score if is_correct else 0,
                    max_score=item.max_score,
                    feedback="Correct!" if is_correct else f"Incorrect. Expected: {item.expected_answer}",
                    details={"is_correct": is_correct},
                )
            else:
                # Use LLM evaluation
                return await self._grade_with_llm(item)
        
        elif item.question_type == QuestionType.ESSAY:
            return await self._grade_essay(item)
        
        elif item.question_type == QuestionType.MATH:
            return await self._grade_math(item, rules)
        
        elif item.question_type == QuestionType.CODING:
            return await self._grade_coding(item)
        
        else:
            return await self._grade_with_llm(item)

    async def _grade_multiple_choice(self, item: SubmissionItem) -> GradingResult:
        """Grade multiple choice question."""
        if not item.expected_answer:
            return GradingResult(
                question_id=item.question_id,
                score=0,
                max_score=item.max_score,
                feedback="No correct answer provided in rubric",
                details={"error": "missing_expected_answer"},
            )
        
        is_correct = False
        
        # Handle both letter (A, B, C, D) and index (0, 1, 2, 3) formats
        if isinstance(item.student_answer, int):
            # Index format
            if item.options and 0 <= item.student_answer < len(item.options):
                is_correct = item.student_answer == item.expected_answer
        else:
            # Letter format
            is_correct = str(item.student_answer).strip().upper() == str(item.expected_answer).strip().upper()
        
        feedback = (
            "Correct! ✓" if is_correct 
            else f"Incorrect. The correct answer was {item.expected_answer}."
        )
        
        return GradingResult(
            question_id=item.question_id,
            score=item.max_score if is_correct else 0,
            max_score=item.max_score,
            feedback=feedback,
            details={
                "is_correct": is_correct,
                "student_answer": item.student_answer,
                "expected_answer": item.expected_answer,
            },
        )

    async def _grade_true_false(self, item: SubmissionItem) -> GradingResult:
        """Grade true/false question."""
        if item.expected_answer is None:
            return GradingResult(
                question_id=item.question_id,
                score=0,
                max_score=item.max_score,
                feedback="No correct answer provided",
                details={"error": "missing_expected_answer"},
            )
        
        is_correct = str(item.student_answer).strip().lower() in ("true", "1", "yes", "correct")
        expected = item.expected_answer
        
        # Normalize expected
        expected_bool = str(expected).strip().lower() in ("true", "1", "yes", "correct")
        is_correct = is_correct == expected_bool
        
        return GradingResult(
            question_id=item.question_id,
            score=item.max_score if is_correct else 0,
            max_score=item.max_score,
            feedback="Correct! ✓" if is_correct else f"Incorrect. The correct answer was {expected}.",
            details={"is_correct": is_correct, "expected": expected},
        )

    async def _grade_math(self, item: SubmissionItem, rules: List) -> GradingResult:
        """Grade math question with numeric tolerance."""
        if rules:
            return self._scoring_engine.evaluate(
                question_id=item.question_id,
                student_answer=item.student_answer,
                question_type=item.question_type,
                max_score=item.max_score,
                rules=rules,
            )
        elif item.expected_answer:
            # Default: exact match with small tolerance
            try:
                student_num = float(item.student_answer)
                expected_num = float(item.expected_answer)
                tolerance = abs(expected_num) * self.config.default_scoring_tolerance
                is_correct = abs(student_num - expected_num) <= tolerance
                
                return GradingResult(
                    question_id=item.question_id,
                    score=item.max_score if is_correct else 0,
                    max_score=item.max_score,
                    feedback=f"{'Correct!' if is_correct else f'Incorrect. Expected: {expected_num}'}",
                    details={"is_correct": is_correct, "expected": expected_num},
                )
            except ValueError:
                return await self._grade_with_llm(item)
        else:
            return await self._grade_with_llm(item)

    async def _grade_essay(self, item: SubmissionItem) -> GradingResult:
        """Grade essay using LLM."""
        rubric = item.metadata.get("rubric", "Provide a fair grade based on content, organization, and clarity.")
        
        result = await self.llm_service.grade_text_answer(
            question_text=item.question_text,
            student_answer=str(item.student_answer),
            rubric=rubric,
            max_score=item.max_score,
            question_type="essay",
        )
        
        return GradingResult(
            question_id=item.question_id,
            score=result.get("score", 0),
            max_score=item.max_score,
            feedback=result.get("feedback", ""),
            details=result.get("details", {}),
            model_used=result.get("model_used"),
            processing_time_ms=result.get("processing_time_ms"),
        )

    async def _grade_coding(self, item: SubmissionItem) -> GradingResult:
        """Grade coding question."""
        rubric = item.metadata.get(
            "rubric",
            "Evaluate for correctness, efficiency, code quality, and edge cases."
        )
        
        result = await self.llm_service.grade_text_answer(
            question_text=item.question_text,
            student_answer=str(item.student_answer),
            rubric=rubric,
            max_score=item.max_score,
            question_type="coding",
        )
        
        return GradingResult(
            question_id=item.question_id,
            score=result.get("score", 0),
            max_score=item.max_score,
            feedback=result.get("feedback", ""),
            details=result.get("details", {}),
            model_used=result.get("model_used"),
            processing_time_ms=result.get("processing_time_ms"),
        )

    async def _grade_with_llm(self, item: SubmissionItem) -> GradingResult:
        """Fallback grading using LLM for unknown question types."""
        rubric = item.metadata.get("rubric", "Grade this answer fairly and provide constructive feedback.")
        
        result = await self.llm_service.grade_text_answer(
            question_text=item.question_text,
            student_answer=str(item.student_answer),
            rubric=rubric,
            max_score=item.max_score,
            question_type="short_answer",
        )
        
        return GradingResult(
            question_id=item.question_id,
            score=result.get("score", 0),
            max_score=item.max_score,
            feedback=result.get("feedback", ""),
            details=result.get("details", {}),
            model_used=result.get("model_used"),
            processing_time_ms=result.get("processing_time_ms"),
        )

    def _generate_overall_feedback(
        self,
        results: List[GradingResult],
        total_score: float,
        max_total_score: float,
    ) -> str:
        """Generate overall feedback for the submission."""
        pct = (total_score / max_total_score * 100) if max_total_score > 0 else 0
        
        if pct >= 90:
            grade = "Excellent"
        elif pct >= 80:
            grade = "Good"
        elif pct >= 70:
            grade = "Satisfactory"
        elif pct >= 60:
            grade = "Needs Improvement"
        else:
            grade = "Unsatisfactory"
        
        # Find weakest areas
        low_scoring = [
            r for r in results 
            if r.max_score > 0 and (r.score / r.max_score) < 0.5
        ]
        
        feedback_parts = [
            f"Overall Grade: {grade} ({pct:.1f}%)",
            f"Total Score: {total_score:.1f}/{max_total_score}",
        ]
        
        if low_scoring:
            feedback_parts.append(
                f"Areas to improve: {', '.join(r.question_id for r in low_scoring[:3])}"
            )
        
        return " | ".join(feedback_parts)

    def _load_ruleset(self, ruleset_id: str) -> Optional[ScoringRuleSet]:
        """Load a ruleset from storage or cache."""
        if ruleset_id in self._rulesets:
            return self._rulesets[ruleset_id]
        
        # Try to load from file
        filepath = Path(self.config.rubrics_dir) / f"{ruleset_id}.json"
        if filepath.exists():
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                    ruleset = ScoringRuleSet(**data)
                    self._rulesets[ruleset_id] = ruleset
                    return ruleset
            except Exception as e:
                logger.error(f"Failed to load ruleset {ruleset_id}: {e}")
        
        return None

    async def _save_grading_result(self, response: GradingResponse) -> None:
        """Save grading result to file."""
        filepath = Path(self.config.grading_results_dir) / f"{response.submission_id}.json"
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(response.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save grading result: {e}")

    def create_submission(
        self,
        student_id: str,
        assignment_id: str,
        items: List[SubmissionItem],
    ) -> GradingRequest:
        """Create a new grading request from a submission."""
        return GradingRequest(
            submission_id=str(uuid.uuid4()),
            student_id=student_id,
            assignment_id=assignment_id,
            items=items,
        )
