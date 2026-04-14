# -*- coding: utf-8 -*-
"""
Data models for Learning Analytics module.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WarningLevel(str, Enum):
    """Academic warning levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PerformanceTrend(str, Enum):
    """Performance trend direction."""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    VOLATILE = "volatile"


class LearningActivity(BaseModel):
    """A single learning activity record."""
    activity_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    activity_type: str  # "homework", "quiz", "exam", "practice", "review"
    subject: str
    assignment_id: Optional[str] = None
    score: Optional[float] = None
    max_score: Optional[float] = None
    time_spent_minutes: Optional[float] = None
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StudentProfile(BaseModel):
    """Student learning profile."""
    student_id: str
    name: Optional[str] = None
    
    # Performance metrics
    overall_gpa: float = 0.0
    subject_scores: Dict[str, float] = Field(default_factory=dict)  # subject -> avg score
    total_activities: int = 0
    total_study_time_minutes: float = 0.0
    
    # Learning patterns
    preferred_subjects: List[str] = Field(default_factory=list)
    weak_subjects: List[str] = Field(default_factory=list)
    learning_style: Optional[str] = None  # "visual", "reading", "practice", "mixed"
    
    # Engagement metrics
    avg_time_per_activity: float = 0.0
    consistency_score: float = 0.0  # 0-1, how consistent
    attendance_rate: float = 1.0  # 0-1
    
    # Strengths and weaknesses (auto-generated)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recommended_topics: List[str] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TrajectoryPoint(BaseModel):
    """A single point in the learning trajectory."""
    timestamp: datetime
    subject: str
    metric: str  # "score", "gpa", "skill_level"
    value: float
    activity_id: Optional[str] = None


class LearningTrajectory(BaseModel):
    """Learning trajectory over time."""
    student_id: str
    subject: Optional[str] = None  # None = overall trajectory
    
    points: List[TrajectoryPoint] = Field(default_factory=list)
    
    # Computed trends
    trend: PerformanceTrend = PerformanceTrend.STABLE
    trend_slope: float = 0.0  # Positive = improving
    volatility: float = 0.0  # Standard deviation of scores
    
    # Predictions
    predicted_next_score: Optional[float] = None
    confidence: Optional[float] = None  # 0-1
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EarlyWarning(BaseModel):
    """Early warning alert for a student."""
    warning_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    subject: Optional[str] = None
    
    level: WarningLevel
    confidence: float = 0.0  # 0-1, confidence in this prediction
    
    # Warning details
    title: str
    description: str
    risk_factors: List[str] = Field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)
    suggested_resources: List[str] = Field(default_factory=list)
    
    # Status
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AnalyticsRequest(BaseModel):
    """Request for analytics."""
    student_id: str
    subject: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    include_predictions: bool = True


class ProfileUpdateRequest(BaseModel):
    """Request to update student profile."""
    student_id: str
    activities: List[LearningActivity]
    metadata: Dict[str, Any] = Field(default_factory=dict)
