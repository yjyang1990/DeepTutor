# -*- coding: utf-8 -*-
"""
Configuration for AI Evaluation module.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EvaluationLLMConfig(BaseModel):
    """LLM configuration for evaluation tasks."""
    provider: str = "anthropic"  # Use Claude for evaluation
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4096
    temperature: float = 0.3  # Lower temp for consistent grading
    timeout: int = 60


class EvaluationQdrantConfig(BaseModel):
    """Qdrant configuration for evaluation knowledge base."""
    url: str = "http://localhost:6333"
    collection_name: str = "evaluation_rubrics"
    vector_size: int = 1536  # OpenAI embeddings
    distance: str = "Cosine"
    api_key: Optional[str] = None


class EvaluationConfig(BaseModel):
    """Main configuration for AI Evaluation module."""
    # LLM settings
    llm: EvaluationLLMConfig = Field(default_factory=EvaluationLLMConfig)
    
    # Qdrant vector DB settings
    qdrant: EvaluationQdrantConfig = Field(default_factory=EvaluationQdrantConfig)
    
    # Grading settings
    default_max_score: float = 100.0
    partial_credit_enabled: bool = True
    detailed_feedback_enabled: bool = True
    
    # Multimodal settings
    multimodal_enabled: bool = True
    supported_image_types: List[str] = ["image/png", "image/jpeg", "image/gif", "image/webp"]
    max_image_size_mb: float = 10.0
    
    # Scoring engine settings
    rule_evaluation_mode: str = "sequential"  # sequential or parallel
    default_scoring_tolerance: float = 0.05  # 5% tolerance for numeric answers
    
    # Performance settings
    async_grading_enabled: bool = True
    batch_size: int = 10
    max_retries: int = 3
    
    # Paths
    rubrics_dir: str = "./data/evaluation/rubrics"
    grading_results_dir: str = "./data/evaluation/results"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()


def get_evaluation_config() -> EvaluationConfig:
    """Load evaluation config from environment or return defaults."""
    from src.config.settings import get_settings
    
    settings = get_settings()
    
    config_dict = {}
    
    # Override from environment if present
    if settings.llm_api_key:
        config_dict.setdefault("llm", {})["api_key"] = settings.llm_api_key
    
    if settings.llm_base_url:
        config_dict.setdefault("llm", {})["base_url"] = settings.llm_base_url
    
    if config_dict:
        # Merge with defaults
        default_config = EvaluationConfig()
        default_config.llm.api_key = config_dict.get("llm", {}).get("api_key", default_config.llm.api_key)
        default_config.llm.base_url = config_dict.get("llm", {}).get("base_url", default_config.llm.base_url)
        return default_config
    
    return EvaluationConfig()
