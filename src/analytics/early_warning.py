# -*- coding: utf-8 -*-
"""
Early Warning System.
Predicts academic risk and generates alerts.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.logging import get_logger

from .config import AnalyticsConfig, get_analytics_config
from .models import (
    EarlyWarning,
    LearningActivity,
    LearningTrajectory,
    PerformanceTrend,
    WarningLevel,
)
from .trajectory import TrajectoryTracker


logger = get_logger(__name__)


class EarlyWarningSystem:
    """
    Early warning system for academic performance.
    
    Features:
    - Multi-factor risk assessment
    - Configurable warning thresholds
    - Subject-specific and overall warnings
    - Actionable recommendations
    """

    def __init__(
        self,
        config: Optional[AnalyticsConfig] = None,
        trajectory_tracker: Optional[TrajectoryTracker] = None,
    ):
        self.config = config or get_analytics_config()
        self._trajectory_tracker = trajectory_tracker or TrajectoryTracker(self.config)
        
        # Ensure directories exist
        Path(self.config.warnings_dir).mkdir(parents=True, exist_ok=True)
        
        # Warning templates
        self._warning_templates = self._init_warning_templates()

    def _init_warning_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize warning templates by level and type."""
        return {
            "declining_performance": {
                WarningLevel.HIGH: {
                    "title": "Declining Performance Alert",
                    "description": "Your recent scores show a consistent downward trend. "
                                  "Consider seeking additional help or adjusting your study habits.",
                    "recommendations": [
                        "Schedule a meeting with your teacher/tutor",
                        "Review recent material for knowledge gaps",
                        "Practice more problems in weak areas",
                        "Consider forming a study group",
                    ],
                },
                WarningLevel.MEDIUM: {
                    "title": "Performance Concern",
                    "description": "Your recent performance is below your usual level.",
                    "recommendations": [
                        "Review recent assignments and identify mistakes",
                        "Spend extra time on challenging topics",
                    ],
                },
            },
            "low_score": {
                WarningLevel.CRITICAL: {
                    "title": "Urgent: Score Below Critical Threshold",
                    "description": "Your recent score is significantly below passing. "
                                  "Immediate intervention is recommended.",
                    "recommendations": [
                        "Schedule immediate meeting with teacher",
                        "Seek tutoring as soon as possible",
                        "Review fundamental concepts in this subject",
                    ],
                },
                WarningLevel.HIGH: {
                    "title": "Low Score Alert",
                    "description": "Your recent score indicates difficulty with the material.",
                    "recommendations": [
                        "Schedule office hours with instructor",
                        "Review related textbook chapters",
                        "Practice with additional exercises",
                    ],
                },
            },
            "inconsistent": {
                WarningLevel.MEDIUM: {
                    "title": "Inconsistent Performance",
                    "description": "Your scores have been highly variable. "
                                  "This may indicate gaps in understanding.",
                    "recommendations": [
                        "Focus on fundamental concepts",
                        "Practice consistently, not just before tests",
                        "Identify which topics cause variability",
                    ],
                },
            },
            "low_engagement": {
                WarningLevel.LOW: {
                    "title": "Low Engagement Notice",
                    "description": "Your activity level has decreased recently.",
                    "recommendations": [
                        "Try to maintain regular study sessions",
                        "Set small, achievable daily goals",
                    ],
                },
            },
            "at_risk": {
                WarningLevel.CRITICAL: {
                    "title": "Academic Risk Warning",
                    "description": "Multiple risk factors detected. "
                                  "Professional intervention strongly recommended.",
                    "recommendations": [
                        "Immediate meeting with academic advisor",
                        "Consider diagnostic assessment",
                        "Intensive tutoring recommended",
                        "Parent/guardian notification may be warranted",
                    ],
                },
            },
        }

    def assess_risk(
        self, student_id: str, subject: Optional[str] = None
    ) -> List[EarlyWarning]:
        """
        Assess academic risk for a student.
        
        Args:
            student_id: Student identifier
            subject: Optional subject filter
            
        Returns:
            List of active warnings
        """
        warnings = []
        
        # Get trajectory
        trajectory = self._trajectory_tracker.get_trajectory(student_id, subject)
        
        # Factor 1: Recent average score
        avg_score, score_factor = self._assess_score(trajectory)
        
        # Factor 2: Trend
        trend_factor, trend_level = self._assess_trend(trajectory)
        
        # Factor 3: Volatility
        volatility_factor, volatility_level = self._assess_volatility(trajectory)
        
        # Combine factors
        overall_risk = self._combine_factors(
            score_factor, trend_factor, volatility_factor
        )
        
        # Generate warnings based on factors
        if overall_risk >= 0.8:
            warnings.append(self._create_warning(
                student_id=student_id,
                subject=subject,
                level=WarningLevel.CRITICAL,
                risk_type="at_risk",
                confidence=min(overall_risk, 1.0),
                risk_factors=self._get_risk_factors(
                    score_factor, trend_factor, volatility_factor
                ),
                additional_data={
                    "avg_score": avg_score,
                    "trend": trajectory.trend.value,
                    "volatility": trajectory.volatility,
                },
            ))
        elif score_factor >= 0.7:
            warnings.append(self._create_warning(
                student_id=student_id,
                subject=subject,
                level=WarningLevel.HIGH,
                risk_type="low_score",
                confidence=score_factor,
                risk_factors=["Recent average score below threshold"],
            ))
        elif trend_factor >= 0.6:
            warnings.append(self._create_warning(
                student_id=student_id,
                subject=subject,
                level=WarningLevel(trend_level),
                risk_type="declining_performance",
                confidence=trend_factor,
                risk_factors=["Consistent downward trend detected"],
            ))
        elif volatility_factor >= 0.5:
            warnings.append(self._create_warning(
                student_id=student_id,
                subject=subject,
                level=WarningLevel.MEDIUM,
                risk_type="inconsistent",
                confidence=volatility_factor,
                risk_factors=["High score variability"],
            ))
        
        return warnings

    def _assess_score(
        self, trajectory: LearningTrajectory
    ) -> Tuple[float, float]:
        """
        Assess risk based on average score.
        
        Returns:
            Tuple of (average_score, risk_factor 0-1)
        """
        if len(trajectory.points) == 0:
            return 100.0, 0.0
        
        recent = trajectory.points[-5:]  # Last 5 activities
        avg_score = sum(p.value for p in recent) / len(recent)
        
        thresholds = self.config.warning_thresholds
        
        if avg_score < thresholds.get("high_score", 50.0):
            risk = 0.9
        elif avg_score < thresholds.get("medium_score", 60.0):
            risk = 0.7
        elif avg_score < thresholds.get("low_score", 70.0):
            risk = 0.4
        else:
            risk = 0.0
        
        return avg_score, risk

    def _assess_trend(
        self, trajectory: LearningTrajectory
    ) -> Tuple[float, str]:
        """
        Assess risk based on performance trend.
        
        Returns:
            Tuple of (risk_factor 0-1, level string)
        """
        trend = trajectory.trend
        slope = trajectory.trend_slope
        
        if trend == PerformanceTrend.DECLINING:
            # Higher slope magnitude = higher risk
            severity = min(abs(slope) / 10, 1.0)  # Normalize
            return severity * 0.8, "HIGH"
        elif trend == PerformanceTrend.VOLATILE:
            return 0.5, "MEDIUM"
        else:
            return 0.0, "NONE"

    def _assess_volatility(
        self, trajectory: LearningTrajectory
    ) -> Tuple[float, str]:
        """
        Assess risk based on score volatility.
        
        Returns:
            Tuple of (risk_factor 0-1, level string)
        """
        volatility = trajectory.volatility
        threshold = self.config.warning_thresholds.get("volatility", 0.3)
        
        if volatility > threshold * 2:
            return 0.7, "HIGH"
        elif volatility > threshold:
            return 0.5, "MEDIUM"
        else:
            return 0.0, "NONE"

    def _combine_factors(
        self, score_factor: float, trend_factor: float, volatility_factor: float
    ) -> float:
        """
        Combine risk factors into overall risk score.
        
        Uses weighted combination with emphasis on score and trend.
        """
        # Weighted average
        weights = {"score": 0.5, "trend": 0.3, "volatility": 0.2}
        
        combined = (
            weights["score"] * score_factor +
            weights["trend"] * trend_factor +
            weights["volatility"] * volatility_factor
        )
        
        # If any single factor is very high, boost overall risk
        if any(f >= 0.9 for f in [score_factor, trend_factor]):
            combined = max(combined, 0.9)
        elif any(f >= 0.7 for f in [score_factor, trend_factor]):
            combined = max(combined, 0.7)
        
        return min(combined, 1.0)

    def _get_risk_factors(
        self, score_factor: float, trend_factor: float, volatility_factor: float
    ) -> List[str]:
        """Get list of active risk factors."""
        factors = []
        if score_factor >= 0.4:
            factors.append("Low recent average")
        if trend_factor >= 0.3:
            factors.append("Declining performance trend")
        if volatility_factor >= 0.3:
            factors.append("Inconsistent scores")
        return factors

    def _create_warning(
        self,
        student_id: str,
        subject: Optional[str],
        level: WarningLevel,
        risk_type: str,
        confidence: float,
        risk_factors: List[str],
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> EarlyWarning:
        """Create a warning from template."""
        templates = self._warning_templates.get(risk_type, {})
        template = templates.get(level, templates.get(WarningLevel.MEDIUM, {}))
        
        title = template.get("title", "Academic Alert")
        description = template.get("description", "")
        recommendations = template.get("recommendations", [])
        
        # Add subject to description if specified
        if subject:
            description = f"[{subject}] {description}"
        
        return EarlyWarning(
            student_id=student_id,
            subject=subject,
            level=level,
            confidence=confidence,
            title=title,
            description=description,
            risk_factors=risk_factors,
            recommendations=recommendations,
            metadata=additional_data or {},
        )

    def generate_recommendations(
        self, student_id: str, subject: Optional[str] = None
    ) -> List[str]:
        """
        Generate personalized recommendations.
        
        Args:
            student_id: Student identifier
            subject: Optional subject filter
            
        Returns:
            List of recommended actions
        """
        warnings = self.assess_risk(student_id, subject)
        
        recommendations = []
        for warning in warnings:
            recommendations.extend(warning.recommendations)
        
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for r in recommendations:
            if r not in seen:
                seen.add(r)
                unique.append(r)
        
        return unique[:5]  # Limit to top 5

    def acknowledge_warning(self, warning_id: str) -> None:
        """Mark a warning as acknowledged."""
        self._update_warning_status(warning_id, "acknowledged")

    def resolve_warning(self, warning_id: str) -> None:
        """Mark a warning as resolved."""
        self._update_warning_status(warning_id, "resolved")

    def _update_warning_status(
        self, warning_id: str, status: str
    ) -> None:
        """Update warning status in storage."""
        # Load all warnings
        warnings_path = Path(self.config.warnings_dir) / "warnings.json"
        
        warnings = []
        if warnings_path.exists():
            try:
                with open(warnings_path, encoding="utf-8") as f:
                    warnings = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load warnings: {e}")
        
        # Update the warning
        for warning in warnings:
            if warning.get("warning_id") == warning_id:
                if status == "acknowledged":
                    warning["acknowledged"] = True
                    warning["acknowledged_at"] = datetime.utcnow().isoformat()
                elif status == "resolved":
                    warning["resolved"] = True
                    warning["resolved_at"] = datetime.utcnow().isoformat()
                break
        
        # Save back
        try:
            with open(warnings_path, "w", encoding="utf-8") as f:
                json.dump(warnings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save warning status: {e}")
