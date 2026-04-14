# -*- coding: utf-8 -*-
"""
Learning Trajectory Tracking.
Tracks and analyzes student learning progress over time.
"""

from __future__ import annotations

import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.logging import get_logger

from .config import AnalyticsConfig, get_analytics_config
from .models import (
    LearningActivity,
    LearningTrajectory,
    PerformanceTrend,
    TrajectoryPoint,
)


logger = get_logger(__name__)


class TrajectoryTracker:
    """
    Tracks learning trajectories over time.
    
    Features:
    - Records learning activities
    - Computes performance trends
    - Predicts future performance
    - Detects anomalies
    """

    def __init__(self, config: Optional[AnalyticsConfig] = None):
        self.config = config or get_analytics_config()
        self._activities_cache: Dict[str, List[LearningActivity]] = {}
        
        # Ensure directories exist
        for dir_path in [
            self.config.trajectories_dir,
            self.config.activities_dir,
        ]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    def record_activity(self, activity: LearningActivity) -> None:
        """
        Record a learning activity.
        
        Args:
            activity: The learning activity to record
        """
        student_id = activity.student_id
        
        # Update cache
        if student_id not in self._activities_cache:
            self._activities_cache[student_id] = []
        
        self._activities_cache[student_id].append(activity)
        
        # Keep only recent activities in cache
        if len(self._activities_cache[student_id]) > self.config.max_recent_activities:
            self._activities_cache[student_id] = self._activities_cache[student_id][-self.config.max_recent_activities:]
        
        # Save to disk
        self._save_activity(activity)
        
        logger.debug(f"Recorded activity {activity.activity_id} for student {student_id}")

    def get_trajectory(
        self,
        student_id: str,
        subject: Optional[str] = None,
    ) -> LearningTrajectory:
        """
        Get learning trajectory for a student.
        
        Args:
            student_id: Student identifier
            subject: Optional subject filter
            
        Returns:
            LearningTrajectory with computed trends
        """
        # Load activities
        activities = self._load_activities(student_id)
        
        # Filter by subject if specified
        if subject:
            activities = [a for a in activities if a.subject == subject]
        
        # Sort by timestamp
        activities.sort(key=lambda a: a.completed_at)
        
        # Build trajectory points from score-based activities
        points = []
        for activity in activities:
            if activity.score is not None and activity.max_score:
                # Normalize to 0-100 scale
                normalized_score = (activity.score / activity.max_score) * 100
                points.append(TrajectoryPoint(
                    timestamp=activity.completed_at,
                    subject=activity.subject,
                    metric="score",
                    value=normalized_score,
                    activity_id=activity.activity_id,
                ))
        
        # Compute trend
        trend, slope, volatility = self._compute_trend(points)
        
        # Predict next score
        predicted, confidence = self._predict_next_score(points)
        
        return LearningTrajectory(
            student_id=student_id,
            subject=subject,
            points=points,
            trend=trend,
            trend_slope=slope,
            volatility=volatility,
            predicted_next_score=predicted,
            confidence=confidence,
        )

    def get_subject_trajectories(
        self, student_id: str
    ) -> Dict[str, LearningTrajectory]:
        """
        Get trajectories for all subjects for a student.
        
        Args:
            student_id: Student identifier
            
        Returns:
            Dict mapping subject -> LearningTrajectory
        """
        activities = self._load_activities(student_id)
        subjects = set(a.subject for a in activities if a.subject)
        
        trajectories = {}
        for subject in subjects:
            trajectories[subject] = self.get_trajectory(student_id, subject)
        
        return trajectories

    def _compute_trend(
        self, points: List[TrajectoryPoint]
    ) -> Tuple[PerformanceTrend, float, float]:
        """
        Compute performance trend from trajectory points.
        
        Uses linear regression to determine trend direction and slope.
        """
        if len(points) < self.config.trajectory_min_points:
            return PerformanceTrend.STABLE, 0.0, 0.0
        
        # Extract values
        values = [p.value for p in points]
        
        # Compute volatility (standard deviation)
        volatility = statistics.stdev(values) if len(values) > 1 else 0.0
        mean_val = statistics.mean(values)
        
        # Normalize volatility relative to mean
        normalized_volatility = volatility / mean_val if mean_val > 0 else 0.0
        
        # Linear regression
        n = len(values)
        indices = list(range(n))
        
        sum_x = sum(indices)
        sum_y = sum(values)
        sum_xy = sum(i * v for i, v in zip(indices, values))
        sum_x2 = sum(i * i for i in indices)
        
        # Slope formula: (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x^2)
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            slope = 0.0
        else:
            slope = (n * sum_xy - sum_x * sum_y) / denominator
        
        # Classify trend
        # Slope is per-activity change, scale by mean performance
        slope_pct = slope / mean_val if mean_val > 0 else 0.0
        
        if normalized_volatility > self.config.warning_thresholds.get("volatility", 0.3):
            trend = PerformanceTrend.VOLATILE
        elif slope_pct > 0.02:  # More than 2% improvement per activity
            trend = PerformanceTrend.IMPROVING
        elif slope_pct < -0.02:  # More than 2% decline per activity
            trend = PerformanceTrend.DECLINING
        else:
            trend = PerformanceTrend.STABLE
        
        return trend, slope, volatility

    def _predict_next_score(
        self, points: List[TrajectoryPoint]
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Predict next score using weighted moving average.
        
        More recent scores are weighted more heavily.
        """
        if len(points) < 2:
            return None, None
        
        # Use last N scores
        recent = points[-self.config.prediction_lookback_count:]
        
        if not recent:
            return None, None
        
        # Weighted average (more recent = higher weight)
        weights = list(range(1, len(recent) + 1))
        total_weight = sum(weights)
        
        weighted_sum = sum(p.value * w for p, w in zip(recent, weights))
        predicted = weighted_sum / total_weight
        
        # Confidence based on consistency
        values = [p.value for p in recent]
        if len(values) > 1:
            cv = statistics.stdev(values) / statistics.mean(values) if statistics.mean(values) > 0 else 0
            # Lower coefficient of variation = higher confidence
            confidence = max(0.0, min(1.0, 1.0 - cv))
        else:
            confidence = 0.5
        
        # Only return if confidence meets threshold
        if confidence < self.config.prediction_confidence_threshold:
            return predicted, confidence
        
        return predicted, confidence

    def detect_anomalies(
        self, student_id: str, subject: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalous performance patterns.
        
        Args:
            student_id: Student identifier
            subject: Optional subject filter
            
        Returns:
            List of detected anomalies
        """
        trajectory = self.get_trajectory(student_id, subject)
        anomalies = []
        
        if len(trajectory.points) < 3:
            return anomalies
        
        values = [p.value for p in trajectory.points]
        mean_val = statistics.mean(values)
        stdev_val = statistics.stdev(values) if len(values) > 1 else 0
        
        # Check for sudden drops
        for i in range(1, len(values)):
            drop = values[i - 1] - values[i]
            if drop > 2 * stdev_val:  # Drop more than 2 standard deviations
                anomalies.append({
                    "type": "sudden_drop",
                    "timestamp": trajectory.points[i].timestamp.isoformat(),
                    "from_score": values[i - 1],
                    "to_score": values[i],
                    "severity": "high" if drop > 3 * stdev_val else "medium",
                })
        
        # Check for consistent decline
        if trajectory.trend == PerformanceTrend.DECLINING:
            anomalies.append({
                "type": "consistent_decline",
                "slope": trajectory.trend_slope,
                "severity": "high" if trajectory.volatility < 0.1 else "medium",
            })
        
        # Check for high volatility
        if trajectory.volatility > self.config.warning_thresholds.get("volatility", 0.3):
            anomalies.append({
                "type": "high_volatility",
                "volatility": trajectory.volatility,
                "severity": "medium",
            })
        
        return anomalies

    def _load_activities(self, student_id: str) -> List[LearningActivity]:
        """Load activities for a student."""
        if student_id in self._activities_cache:
            return self._activities_cache[student_id]
        
        filepath = Path(self.config.activities_dir) / f"{student_id}.json"
        
        if not filepath.exists():
            return []
        
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
                activities = [LearningActivity(**a) for a in data]
                self._activities_cache[student_id] = activities
                return activities
        except Exception as e:
            logger.error(f"Failed to load activities for {student_id}: {e}")
            return []

    def _save_activity(self, activity: LearningActivity) -> None:
        """Save activity to disk."""
        filepath = Path(self.config.activities_dir) / f"{activity.student_id}.json"
        
        # Load existing
        activities = self._load_activities(activity.student_id)
        
        # Add new (avoid duplicates)
        existing_ids = {a.activity_id for a in activities}
        if activity.activity_id not in existing_ids:
            activities.append(activity)
        
        # Save
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump([a.model_dump(mode="json") for a in activities], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save activity: {e}")
