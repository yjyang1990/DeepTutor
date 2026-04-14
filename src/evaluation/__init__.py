# -*- coding: utf-8 -*-
"""
AI Evaluation Module.

Provides:
- Automatic grading of assignments and exams
- Multi-modal LLM integration (Claude API)
- Configurable scoring rules engine
"""

from .config import EvaluationConfig, get_evaluation_config
from .grading import GradingService
from .multimodal import MultimodalLLMService
from .scoring_engine import ScoringEngine
from .models import (
    GradingRequest,
    GradingResponse,
    GradingResult,
    GradingStatus,
    QuestionType,
    ScoringRule,
    ScoringRuleSet,
    SubmissionCreate,
    SubmissionItem,
    BatchGradingRequest,
)


__all__ = [
    # Config
    "EvaluationConfig",
    "get_evaluation_config",
    # Services
    "GradingService",
    "MultimodalLLMService",
    "ScoringEngine",
    # Models
    "GradingRequest",
    "GradingResponse",
    "GradingResult",
    "GradingStatus",
    "QuestionType",
    "ScoringRule",
    "ScoringRuleSet",
    "SubmissionCreate",
    "SubmissionItem",
    "BatchGradingRequest",
]
