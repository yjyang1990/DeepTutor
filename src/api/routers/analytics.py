# -*- coding: utf-8 -*-
"""
API Router for Learning Analytics endpoints.
"""

from datetime import datetime
from pathlib import Path
import sys

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Add project root for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analytics import (
    AnalyticsConfig,
    AnalyticsRequest,
    EarlyWarning,
    EarlyWarningSystem,
    LearningActivity,
    LearningTrajectory,
    ProfileUpdateRequest,
    StudentProfile,
    StudentProfileGenerator,
    TrajectoryTracker,
    get_analytics_config,
)
from src.logging import get_logger


logger = get_logger("AnalyticsAPI")

router = APIRouter()

# Initialize services
_trajectory_tracker: TrajectoryTracker | None = None
_early_warning: EarlyWarningSystem | None = None
_profile_generator: StudentProfileGenerator | None = None


def get_trajectory_tracker() -> TrajectoryTracker:
    """Get or create trajectory tracker singleton."""
    global _trajectory_tracker
    if _trajectory_tracker is None:
        config = get_analytics_config()
        _trajectory_tracker = TrajectoryTracker(config)
    return _trajectory_tracker


def get_early_warning_system() -> EarlyWarningSystem:
    """Get or create early warning system singleton."""
    global _early_warning
    if _early_warning is None:
        config = get_analytics_config()
        tracker = get_trajectory_tracker()
        _early_warning = EarlyWarningSystem(config, tracker)
    return _early_warning


def get_profile_generator() -> StudentProfileGenerator:
    """Get or create profile generator singleton."""
    global _profile_generator
    if _profile_generator is None:
        config = get_analytics_config()
        tracker = get_trajectory_tracker()
        _profile_generator = StudentProfileGenerator(config, tracker)
    return _profile_generator


# --- Request/Response Models ---


class RecordActivityRequest(BaseModel):
    """Request to record a learning activity."""
    student_id: str
    activity_type: str
    subject: str
    assignment_id: str | None = None
    score: float | None = None
    max_score: float | None = None
    time_spent_minutes: float | None = None
    metadata: dict = {}


class RecordActivityResponse(BaseModel):
    """Response after recording activity."""
    activity_id: str
    recorded: bool


class TrajectoryResponse(BaseModel):
    """Response with trajectory data."""
    student_id: str
    subject: str | None
    points: list
    trend: str
    trend_slope: float
    volatility: float
    predicted_next_score: float | None
    confidence: float | None


class WarningResponse(BaseModel):
    """Response with warning data."""
    warning_id: str
    student_id: str
    subject: str | None
    level: str
    confidence: float
    title: str
    description: str
    risk_factors: list
    recommendations: list


class ProfileResponse(BaseModel):
    """Response with student profile."""
    student_id: str
    name: str | None
    overall_gpa: float
    subject_scores: dict
    total_activities: int
    preferred_subjects: list
    weak_subjects: list
    learning_style: str | None
    strengths: list
    weaknesses: list
    recommended_topics: list
    updated_at: datetime


# --- Endpoints ---


@router.post("/activity/record", response_model=RecordActivityResponse)
async def record_activity(request: RecordActivityRequest):
    """
    Record a learning activity for a student.
    
    This is used to track homework, quizzes, exams, etc.
    """
    tracker = get_trajectory_tracker()
    
    activity = LearningActivity(
        student_id=request.student_id,
        activity_type=request.activity_type,
        subject=request.subject,
        assignment_id=request.assignment_id,
        score=request.score,
        max_score=request.max_score,
        time_spent_minutes=request.time_spent_minutes,
    )
    
    tracker.record_activity(activity)
    
    return RecordActivityResponse(
        activity_id=activity.activity_id,
        recorded=True,
    )


@router.post("/activities/batch")
async def record_activities(requests: list[RecordActivityRequest]):
    """Record multiple learning activities."""
    tracker = get_trajectory_tracker()
    
    activity_ids = []
    for req in requests:
        activity = LearningActivity(
            student_id=req.student_id,
            activity_type=req.activity_type,
            subject=req.subject,
            assignment_id=req.assignment_id,
            score=req.score,
            max_score=req.max_score,
            time_spent_minutes=req.time_spent_minutes,
        )
        tracker.record_activity(activity)
        activity_ids.append(activity.activity_id)
    
    return {"recorded": len(activity_ids), "activity_ids": activity_ids}


@router.get("/trajectory/{student_id}", response_model=TrajectoryResponse)
async def get_trajectory(student_id: str, subject: str | None = None):
    """Get learning trajectory for a student."""
    tracker = get_trajectory_tracker()
    
    trajectory = tracker.get_trajectory(student_id, subject)
    
    return TrajectoryResponse(
        student_id=trajectory.student_id,
        subject=trajectory.subject,
        points=[
            {
                "timestamp": p.timestamp.isoformat(),
                "subject": p.subject,
                "metric": p.metric,
                "value": p.value,
            }
            for p in trajectory.points
        ],
        trend=trajectory.trend.value,
        trend_slope=trajectory.trend_slope,
        volatility=trajectory.volatility,
        predicted_next_score=trajectory.predicted_next_score,
        confidence=trajectory.confidence,
    )


@router.get("/trajectory/{student_id}/subjects")
async def get_all_subject_trajectories(student_id: str):
    """Get trajectories for all subjects."""
    tracker = get_trajectory_tracker()
    
    trajectories = tracker.get_subject_trajectories(student_id)
    
    return {
        "student_id": student_id,
        "subjects": {
            subject: {
                "trend": t.trend.value,
                "trend_slope": t.trend_slope,
                "volatility": t.volatility,
                "point_count": len(t.points),
            }
            for subject, t in trajectories.items()
        },
    }


@router.get("/warnings/{student_id}")
async def get_warnings(student_id: str, subject: str | None = None):
    """Get active warnings for a student."""
    warning_system = get_early_warning_system()
    
    warnings = warning_system.assess_risk(student_id, subject)
    
    return {
        "student_id": student_id,
        "warning_count": len(warnings),
        "warnings": [
            {
                "warning_id": w.warning_id,
                "level": w.level.value,
                "title": w.title,
                "description": w.description,
                "confidence": w.confidence,
                "risk_factors": w.risk_factors,
                "recommendations": w.recommendations,
            }
            for w in warnings
        ],
    }


@router.post("/warnings/{warning_id}/acknowledge")
async def acknowledge_warning(warning_id: str):
    """Acknowledge a warning."""
    warning_system = get_early_warning_system()
    warning_system.acknowledge_warning(warning_id)
    return {"acknowledged": True}


@router.post("/warnings/{warning_id}/resolve")
async def resolve_warning(warning_id: str):
    """Resolve a warning."""
    warning_system = get_early_warning_system()
    warning_system.resolve_warning(warning_id)
    return {"resolved": True}


@router.get("/profile/{student_id}", response_model=ProfileResponse)
async def get_profile(student_id: str):
    """Get student profile."""
    generator = get_profile_generator()
    
    profile = generator.get_profile(student_id)
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return ProfileResponse(
        student_id=profile.student_id,
        name=profile.name,
        overall_gpa=profile.overall_gpa,
        subject_scores=profile.subject_scores,
        total_activities=profile.total_activities,
        preferred_subjects=profile.preferred_subjects,
        weak_subjects=profile.weak_subjects,
        learning_style=profile.learning_style,
        strengths=profile.strengths,
        weaknesses=profile.weaknesses,
        recommended_topics=profile.recommended_topics,
        updated_at=profile.updated_at,
    )


@router.post("/profile/generate")
async def generate_profile(student_id: str):
    """Generate or regenerate a student profile from activities."""
    generator = get_profile_generator()
    
    profile = generator.generate_profile(student_id)
    
    return ProfileResponse(
        student_id=profile.student_id,
        name=profile.name,
        overall_gpa=profile.overall_gpa,
        subject_scores=profile.subject_scores,
        total_activities=profile.total_activities,
        preferred_subjects=profile.preferred_subjects,
        weak_subjects=profile.weak_subjects,
        learning_style=profile.learning_style,
        strengths=profile.strengths,
        weaknesses=profile.weaknesses,
        recommended_topics=profile.recommended_topics,
        updated_at=profile.updated_at,
    )


@router.get("/recommendations/{student_id}")
async def get_recommendations(student_id: str, subject: str | None = None):
    """Get personalized recommendations for a student."""
    warning_system = get_early_warning_system()
    
    recommendations = warning_system.generate_recommendations(student_id, subject)
    
    return {
        "student_id": student_id,
        "recommendations": recommendations,
    }


@router.get("/analytics/{student_id}/overview")
async def get_overview(student_id: str):
    """Get a complete analytics overview for a student."""
    tracker = get_trajectory_tracker()
    warning_system = get_early_warning_system()
    profile_gen = get_profile_generator()
    
    # Get profile
    profile = profile_gen.get_profile(student_id)
    
    # Get trajectory
    trajectory = tracker.get_trajectory(student_id)
    
    # Get warnings
    warnings = warning_system.assess_risk(student_id)
    
    # Get anomalies
    anomalies = tracker.detect_anomalies(student_id)
    
    return {
        "student_id": student_id,
        "profile": {
            "overall_gpa": profile.overall_gpa if profile else None,
            "subject_scores": profile.subject_scores if profile else {},
            "total_activities": profile.total_activities if profile else 0,
            "strengths": profile.strengths if profile else [],
            "weaknesses": profile.weaknesses if profile else [],
        },
        "trajectory": {
            "trend": trajectory.trend.value if trajectory else "unknown",
            "volatility": trajectory.volatility if trajectory else 0,
            "point_count": len(trajectory.points) if trajectory else 0,
        },
        "warnings": {
            "count": len(warnings),
            "levels": [w.level.value for w in warnings],
        },
        "anomalies": anomalies,
    }


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    config = get_analytics_config()
    return {
        "status": "healthy",
        "qdrant_url": config.qdrant.url,
        "trajectories_dir": config.trajectories_dir,
        "profiles_dir": config.profiles_dir,
    }
