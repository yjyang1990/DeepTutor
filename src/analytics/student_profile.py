# -*- coding: utf-8 -*-
"""
Student Profile Generation.
Creates and maintains student learning profiles.
"""

from __future__ import annotations

import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.logging import get_logger

from .config import AnalyticsConfig, get_analytics_config
from .models import (
    LearningActivity,
    StudentProfile,
)
from .trajectory import TrajectoryTracker


logger = get_logger(__name__)


class StudentProfileGenerator:
    """
    Generates and maintains student learning profiles.
    
    Features:
    - Aggregates learning activities
    - Identifies strengths and weaknesses
    - Tracks engagement patterns
    - Generates personalized recommendations
    """

    def __init__(
        self,
        config: Optional[AnalyticsConfig] = None,
        trajectory_tracker: Optional[TrajectoryTracker] = None,
    ):
        self.config = config or get_analytics_config()
        self._trajectory_tracker = trajectory_tracker or TrajectoryTracker(self.config)
        self._profiles_cache: Dict[str, StudentProfile] = {}
        
        # Ensure directories exist
        Path(self.config.profiles_dir).mkdir(parents=True, exist_ok=True)

    def generate_profile(
        self,
        student_id: str,
        activities: Optional[List[LearningActivity]] = None,
    ) -> StudentProfile:
        """
        Generate or update a student profile.
        
        Args:
            student_id: Student identifier
            activities: Optional pre-loaded activities (loads from storage if None)
            
        Returns:
            Complete student profile
        """
        # Load activities if not provided
        if activities is None:
            activities = self._trajectory_tracker._load_activities(student_id)
        
        if not activities:
            # Return empty profile
            return StudentProfile(student_id=student_id)
        
        # Sort by timestamp
        activities.sort(key=lambda a: a.completed_at)
        
        # Compute metrics
        subject_scores = self._compute_subject_scores(activities)
        overall_gpa = self._compute_overall_gpa(subject_scores)
        study_time = self._compute_study_time(activities)
        engagement = self._compute_engagement_metrics(activities)
        
        # Identify strengths and weaknesses
        strengths, weaknesses = self._identify_strengths_weaknesses(subject_scores)
        
        # Determine learning style
        learning_style = self._infer_learning_style(activities)
        
        # Generate recommendations
        recommended_topics = self._generate_recommended_topics(weaknesses)
        
        profile = StudentProfile(
            student_id=student_id,
            overall_gpa=overall_gpa,
            subject_scores=subject_scores,
            total_activities=len(activities),
            total_study_time_minutes=study_time,
            preferred_subjects=strengths[:3],
            weak_subjects=weaknesses[:3],
            learning_style=learning_style,
            avg_time_per_activity=engagement.get("avg_time", 0),
            consistency_score=engagement.get("consistency", 0),
            attendance_rate=engagement.get("attendance", 1.0),
            strengths=strengths[:5],
            weaknesses=weaknesses[:5],
            recommended_topics=recommended_topics,
            updated_at=datetime.utcnow(),
        )
        
        # Cache and save
        self._profiles_cache[student_id] = profile
        self._save_profile(profile)
        
        return profile

    def update_profile(
        self,
        student_id: str,
        new_activities: List[LearningActivity],
    ) -> StudentProfile:
        """
        Incrementally update an existing profile with new activities.
        
        Args:
            student_id: Student identifier
            new_activities: New activities to incorporate
            
        Returns:
            Updated student profile
        """
        # Record new activities
        for activity in new_activities:
            self._trajectory_tracker.record_activity(activity)
        
        # Regenerate profile
        return self.generate_profile(student_id)

    def get_profile(self, student_id: str) -> Optional[StudentProfile]:
        """
        Get a student's profile.
        
        Args:
            student_id: Student identifier
            
        Returns:
            Student profile or None if not found
        """
        if student_id in self._profiles_cache:
            return self._profiles_cache[student_id]
        
        filepath = Path(self.config.profiles_dir) / f"{student_id}.json"
        
        if not filepath.exists():
            return None
        
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
                profile = StudentProfile(**data)
                self._profiles_cache[student_id] = profile
                return profile
        except Exception as e:
            logger.error(f"Failed to load profile for {student_id}: {e}")
            return None

    def _compute_subject_scores(
        self, activities: List[LearningActivity]
    ) -> Dict[str, float]:
        """Compute average score per subject."""
        subject_scores: Dict[str, List[float]] = {}
        
        for activity in activities:
            if activity.score is not None and activity.max_score:
                subject = activity.subject
                if subject not in subject_scores:
                    subject_scores[subject] = []
                
                normalized = (activity.score / activity.max_score) * 100
                subject_scores[subject].append(normalized)
        
        # Compute averages
        return {
            subject: sum(scores) / len(scores)
            for subject, scores in subject_scores.items()
        }

    def _compute_overall_gpa(self, subject_scores: Dict[str, float]) -> float:
        """Convert average score to GPA (0-4 scale)."""
        if not subject_scores:
            return 0.0
        
        scores = list(subject_scores.values())
        avg_score = sum(scores) / len(scores)
        
        # Convert to 4.0 scale
        if avg_score >= 93:
            return 4.0
        elif avg_score >= 90:
            return 3.7
        elif avg_score >= 87:
            return 3.3
        elif avg_score >= 83:
            return 3.0
        elif avg_score >= 80:
            return 2.7
        elif avg_score >= 77:
            return 2.3
        elif avg_score >= 73:
            return 2.0
        elif avg_score >= 70:
            return 1.7
        elif avg_score >= 67:
            return 1.3
        elif avg_score >= 63:
            return 1.0
        elif avg_score >= 60:
            return 0.7
        else:
            return 0.0

    def _compute_study_time(
        self, activities: List[LearningActivity]
    ) -> float:
        """Compute total study time in minutes."""
        return sum(
            a.time_spent_minutes or 0
            for a in activities
        )

    def _compute_engagement_metrics(
        self, activities: List[LearningActivity]
    ) -> Dict[str, float]:
        """Compute engagement metrics."""
        metrics: Dict[str, float] = {}
        
        # Average time per activity
        times = [a.time_spent_minutes for a in activities if a.time_spent_minutes]
        metrics["avg_time"] = sum(times) / len(times) if times else 0
        
        # Consistency (based on time gaps)
        if len(activities) >= 2:
            sorted_activities = sorted(activities, key=lambda a: a.completed_at)
            gaps = []
            for i in range(1, len(sorted_activities)):
                gap = (sorted_activities[i].completed_at - sorted_activities[i-1].completed_at).total_seconds() / 3600  # hours
                gaps.append(gap)
            
            if gaps:
                gap_variance = statistics.variance(gaps) if len(gaps) > 1 else 0
                # Lower variance = higher consistency
                metrics["consistency"] = max(0.0, 1.0 - min(gap_variance / 168, 1.0))  # Normalize by week
            else:
                metrics["consistency"] = 1.0
        else:
            metrics["consistency"] = 1.0
        
        # Attendance (assumes 100% if not tracked)
        metrics["attendance"] = 1.0
        
        return metrics

    def _identify_strengths_weaknesses(
        self, subject_scores: Dict[str, float]
    ) -> tuple[List[str], List[str]]:
        """
        Identify student strengths and weaknesses.
        
        Args:
            subject_scores: Average score per subject
            
        Returns:
            Tuple of (strengths, weaknesses)
        """
        if not subject_scores:
            return [], []
        
        avg_overall = sum(subject_scores.values()) / len(subject_scores)
        
        strengths = []
        weaknesses = []
        
        for subject, score in subject_scores.items():
            if score >= avg_overall + 10:  # 10 points above average
                strengths.append(subject)
            elif score <= avg_overall - 10:  # 10 points below average
                weaknesses.append(subject)
        
        # Sort by deviation from average
        strengths.sort(key=lambda s: subject_scores[s], reverse=True)
        weaknesses.sort(key=lambda w: subject_scores[w])
        
        return strengths, weaknesses

    def _infer_learning_style(
        self, activities: List[LearningActivity]
    ) -> Optional[str]:
        """
        Infer learning style from activity patterns.
        
        Currently a simple heuristic based on activity types.
        """
        activity_types: Dict[str, int] = {}
        
        for activity in activities:
            atype = activity.activity_type
            activity_types[atype] = activity_types.get(atype, 0) + 1
        
        if not activity_types:
            return "mixed"
        
        # Most common activity type
        most_common = max(activity_types.items(), key=lambda x: x[1])
        
        style_map = {
            "quiz": "practice",
            "exam": "practice",
            "homework": "practice",
            "practice": "practice",
            "review": "reading",
            "reading": "reading",
            "lecture": "visual",
            "video": "visual",
        }
        
        return style_map.get(most_common[0], "mixed")

    def _generate_recommended_topics(
        self, weak_subjects: List[str]
    ) -> List[str]:
        """Generate recommended topics based on weak areas."""
        return [f"Strengthen {subject}" for subject in weak_subjects]

    def _save_profile(self, profile: StudentProfile) -> None:
        """Save profile to disk."""
        filepath = Path(self.config.profiles_dir) / f"{profile.student_id}.json"
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(profile.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")

    def compare_students(
        self, student_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Compare multiple students.
        
        Args:
            student_ids: List of student identifiers
            
        Returns:
            List of comparison data
        """
        comparisons = []
        
        profiles = []
        for sid in student_ids:
            profile = self.get_profile(sid)
            if profile:
                profiles.append(profile)
        
        if len(profiles) < 2:
            return comparisons
        
        # Compute class averages
        all_subjects = set()
        for p in profiles:
            all_subjects.update(p.subject_scores.keys())
        
        subject_averages = {}
        for subject in all_subjects:
            scores = [p.subject_scores.get(subject, 0) for p in profiles]
            subject_averages[subject] = sum(scores) / len(scores)
        
        class_gpa = sum(p.overall_gpa for p in profiles) / len(profiles)
        
        # Compare each student
        for profile in profiles:
            comparisons.append({
                "student_id": profile.student_id,
                "overall_gpa": profile.overall_gpa,
                "gpa_vs_class": profile.overall_gpa - class_gpa,
                "subject_scores": profile.subject_scores,
                "subject_vs_class": {
                    s: profile.subject_scores.get(s, 0) - subject_averages.get(s, 0)
                    for s in all_subjects
                },
                "total_activities": profile.total_activities,
                "engagement": {
                    "avg_time": profile.avg_time_per_activity,
                    "consistency": profile.consistency_score,
                },
            })
        
        return comparisons
