# -*- coding: utf-8 -*-
"""
Learning Analytics Module.

Provides:
- Learning trajectory tracking
- Early warning system
- Student profile generation
"""

from .config import AnalyticsConfig, get_analytics_config
from .early_warning import EarlyWarningSystem
from .models import (
    AnalyticsRequest,
    EarlyWarning,
    LearningActivity,
    LearningTrajectory,
    PerformanceTrend,
    ProfileUpdateRequest,
    StudentProfile,
    TrajectoryPoint,
    WarningLevel,
)
from .student_profile import StudentProfileGenerator
from .trajectory import TrajectoryTracker


__all__ = [
    # Config
    "AnalyticsConfig",
    "get_analytics_config",
    # Services
    "TrajectoryTracker",
    "EarlyWarningSystem",
    "StudentProfileGenerator",
    # Models
    "AnalyticsRequest",
    "EarlyWarning",
    "LearningActivity",
    "LearningTrajectory",
    "PerformanceTrend",
    "ProfileUpdateRequest",
    "StudentProfile",
    "TrajectoryPoint",
    "WarningLevel",
]
