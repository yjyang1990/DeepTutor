# -*- coding: utf-8 -*-
"""
Configuration for Learning Analytics module.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnalyticsLLMConfig(BaseModel):
    """LLM configuration for analytics."""
    provider: str = "anthropic"
    model: str = "claude-3-5-haiku-20241022"  # Use faster/cheaper model for analytics
    max_tokens: int = 2048
    temperature: float = 0.3


class AnalyticsQdrantConfig(BaseModel):
    """Qdrant configuration for analytics."""
    url: str = "http://localhost:6333"
    collection_name: str = "student_profiles"
    vector_size: int = 1536
    distance: str = "Cosine"
    api_key: Optional[str] = None


class AnalyticsConfig(BaseModel):
    """Main configuration for Learning Analytics module."""
    # LLM settings
    llm: AnalyticsLLMConfig = Field(default_factory=AnalyticsLLMConfig)
    
    # Qdrant vector DB settings
    qdrant: AnalyticsQdrantConfig = Field(default_factory=AnalyticsQdrantConfig)
    
    # Early warning thresholds
    warning_thresholds: Dict[str, float] = Field(default_factory=lambda: {
        "low_score": 70.0,       # Below this = potential concern
        "medium_score": 60.0,    # Below this = warning
        "high_score": 50.0,      # Below this = critical
        "declining_trend": -5.0,  # Negative slope threshold
        "volatility": 0.3,       # High volatility threshold
    })
    
    # Prediction settings
    prediction_lookback_count: int = 5  # Number of past scores to consider
    prediction_confidence_threshold: float = 0.7
    
    # Trajectory tracking
    trajectory_update_interval: int = 1  # Update after every N activities
    trajectory_min_points: int = 3  # Minimum points before computing trend
    
    # Profile generation
    profile_update_batch: int = 10  # Update profile every N activities
    max_recent_activities: int = 50  # Keep this many recent activities
    
    # Paths
    profiles_dir: str = "./data/analytics/profiles"
    trajectories_dir: str = "./data/analytics/trajectories"
    warnings_dir: str = "./data/analytics/warnings"
    activities_dir: str = "./data/analytics/activities"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()


def get_analytics_config() -> AnalyticsConfig:
    """Load analytics config from environment or return defaults."""
    from src.config.settings import get_settings
    
    settings = get_settings()
    
    # Currently just returns defaults
    # Could load from env vars if needed
    return AnalyticsConfig()
