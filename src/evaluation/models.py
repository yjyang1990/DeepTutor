# -*- coding: utf-8 -*-
"""
Data models for AI Evaluation module.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GradingStatus(str, Enum):
    """Grading job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class QuestionType(str, Enum):
    """Supported question types for grading."""
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    FILL_IN_BLANK = "fill_in_blank"
    TRUE_FALSE = "true_false"
    CODING = "coding"
    MATH = "math"


class SubmissionItem(BaseModel):
    """A single question/answer pair in a submission."""
    question_id: str
    question_type: QuestionType
    question_text: str
    student_answer: Any  # str, list, dict depending on question type
    expected_answer: Optional[Any] = None  # For multiple choice/short answer
    options: Optional[List[str]] = None  # For multiple choice
    max_score: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GradingResult(BaseModel):
    """Grading result for a single question."""
    question_id: str
    score: float
    max_score: float
    feedback: str
    details: Dict[str, Any] = Field(default_factory=dict)
    model_used: Optional[str] = None
    processing_time_ms: Optional[float] = None


class GradingResponse(BaseModel):
    """Full grading response for a submission."""
    submission_id: str
    student_id: str
    assignment_id: str
    status: GradingStatus
    results: List[GradingResult]
    total_score: float
    max_total_score: float
    overall_feedback: str
    graded_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScoringRule(BaseModel):
    """A scoring rule definition."""
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    question_type: QuestionType
    priority: int = 0  # Higher priority rules are evaluated first
    conditions: Dict[str, Any]  # Rule conditions (JSON logic)
    score_modifier: float = 0.0
    partial_credit: bool = False
    partial_credit_config: Optional[Dict[str, Any]] = None
    feedback_template: str = ""


class ScoringRuleSet(BaseModel):
    """A set of scoring rules for a subject/assignment type."""
    ruleset_id: str
    name: str
    description: str
    subject: str
    grade_level: Optional[str] = None
    rules: List[ScoringRule] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Assignment(BaseModel):
    """Assignment/exam definition."""
    assignment_id: str
    title: str
    description: str
    subject: str
    grade_level: Optional[str] = None
    question_types: List[QuestionType]
    scoring_ruleset_id: Optional[str] = None
    rubric: Optional[Dict[str, Any]] = None  # Detailed rubric
    total_score: float = 100.0
    passing_score: float = 60.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SubmissionCreate(BaseModel):
    """Request to create a new grading submission."""
    student_id: str
    assignment_id: str
    items: List[SubmissionItem]
    submitted_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GradingRequest(BaseModel):
    """Request to grade a submission."""
    submission_id: str
    student_id: str
    assignment_id: str
    items: List[SubmissionItem]
    use_multimodal: bool = False  # Use Claude vision for image inputs
    scoring_ruleset_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BatchGradingRequest(BaseModel):
    """Request to grade multiple submissions."""
    submissions: List[GradingRequest]
    parallel: bool = True
    max_parallel_jobs: int = 5
