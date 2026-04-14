# -*- coding: utf-8 -*-
"""
Scoring Rules Engine for AI Evaluation.
Supports flexible rule definitions and partial credit scoring.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.logging import get_logger

from .models import (
    QuestionType,
    ScoringRule,
    ScoringRuleSet,
    GradingResult,
)
from .config import EvaluationConfig, get_evaluation_config


logger = get_logger(__name__)


class ScoringEngine:
    """
    Configurable scoring rules engine.
    
    Supports:
    - Exact match rules
    - Keyword/pattern matching rules
    - Partial credit scoring
    - Weighted criteria scoring
    - Custom rule functions
    """

    def __init__(self, config: Optional[EvaluationConfig] = None):
        self.config = config or get_evaluation_config()
        self._custom_rules: Dict[str, Callable] = {}
        
        # Register built-in rule evaluators
        self._rule_evaluators: Dict[str, Callable] = {
            "exact_match": self._eval_exact_match,
            "contains_all": self._eval_contains_all,
            "contains_any": self._eval_contains_any,
            "regex_match": self._eval_regex_match,
            "numeric_range": self._eval_numeric_range,
            "numeric_tolerance": self._eval_numeric_tolerance,
            "keyword_count": self._eval_keyword_count,
            "length_range": self._eval_length_range,
        }

    def register_custom_rule(
        self, rule_name: str, evaluator: Callable[[str, Dict], Tuple[float, str]]
    ) -> None:
        """
        Register a custom rule evaluator.
        
        Args:
            rule_name: Unique name for the rule
            evaluator: Function(student_answer, conditions) -> (score, feedback)
        """
        self._custom_rules[rule_name] = evaluator
        logger.info(f"Registered custom scoring rule: {rule_name}")

    def evaluate(
        self,
        question_id: str,
        student_answer: Any,
        question_type: QuestionType,
        max_score: float,
        ruleset: Optional[ScoringRuleSet] = None,
        rules: Optional[List[ScoringRule]] = None,
    ) -> GradingResult:
        """
        Evaluate a student answer using scoring rules.
        
        Args:
            question_id: Unique question identifier
            student_answer: The student's answer
            question_type: Type of question
            max_score: Maximum possible score
            ruleset: Pre-defined scoring ruleset (optional)
            rules: Individual rules to apply (optional)
            
        Returns:
            GradingResult with score and feedback
        """
        answer_str = self._normalize_answer(student_answer)
        
        # Determine which rules to use
        if rules:
            applicable_rules = [r for r in rules if r.question_type == question_type]
        elif ruleset:
            applicable_rules = [
                r for r in ruleset.rules
                if r.question_type == question_type
            ]
        else:
            # Use default scoring based on question type
            return self._default_scoring(question_id, student_answer, question_type, max_score)
        
        # Sort by priority (higher first)
        applicable_rules.sort(key=lambda r: r.priority, reverse=True)
        
        if not applicable_rules:
            return self._default_scoring(question_id, student_answer, question_type, max_score)
        
        return self._apply_rules(
            question_id, answer_str, student_answer, applicable_rules, max_score
        )

    def _apply_rules(
        self,
        question_id: str,
        answer_str: str,
        student_answer: Any,
        rules: List[ScoringRule],
        max_score: float,
    ) -> GradingResult:
        """Apply scoring rules sequentially."""
        total_score = 0.0
        feedbacks = []
        details = {"rules_applied": []}
        
        for rule in rules:
            try:
                result = self._evaluate_single_rule(rule, answer_str, student_answer)
                
                if rule.partial_credit and rule.partial_credit_config:
                    # Partial credit mode
                    partial = self._calc_partial_credit(result, rule, max_score)
                    total_score += partial["score"]
                    feedbacks.append(partial["feedback"])
                else:
                    # Binary or additive mode
                    total_score += result["score"]
                    feedbacks.append(result["feedback"])
                
                details["rules_applied"].append({
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "matched": result.get("matched", False),
                    "score_contribution": result["score"],
                })
                
            except Exception as e:
                logger.warning(f"Rule {rule.rule_id} evaluation failed: {e}")
                details["rules_applied"].append({
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "error": str(e),
                })
        
        # Cap at max_score
        total_score = min(total_score, max_score)
        
        # Generate overall feedback
        overall_feedback = self._generate_feedback(feedbacks, total_score, max_score)
        
        return GradingResult(
            question_id=question_id,
            score=total_score,
            max_score=max_score,
            feedback=overall_feedback,
            details=details,
        )

    def _evaluate_single_rule(
        self, rule: ScoringRule, answer_str: str, student_answer: Any
    ) -> Dict[str, Any]:
        """Evaluate a single scoring rule."""
        rule_type = rule.conditions.get("type", "exact_match")
        
        if rule_type in self._rule_evaluators:
            evaluator = self._rule_evaluators[rule_type]
            return evaluator(answer_str, student_answer, rule)
        elif rule_type in self._custom_rules:
            return self._custom_rules[rule_type](answer_str, rule.conditions)
        else:
            logger.warning(f"Unknown rule type: {rule_type}")
            return {"score": 0, "feedback": "Rule type unknown", "matched": False}

    def _eval_exact_match(
        self, answer_str: str, student_answer: Any, rule: ScoringRule
    ) -> Dict[str, Any]:
        """Exact match evaluation."""
        expected = str(rule.conditions.get("expected", "")).lower().strip()
        actual = answer_str.lower().strip()
        
        matched = actual == expected
        
        return {
            "score": rule.score_modifier if matched else 0,
            "feedback": rule.feedback_template.format(
                expected=expected, actual=actual
            ) if matched else f"Incorrect. Expected: {expected}",
            "matched": matched,
        }

    def _eval_contains_all(
        self, answer_str: str, student_answer: Any, rule: ScoringRule
    ) -> Dict[str, Any]:
        """Check if answer contains all required keywords."""
        keywords = rule.conditions.get("keywords", [])
        answer_lower = answer_str.lower()
        
        found = [kw for kw in keywords if kw.lower() in answer_lower]
        missing = [kw for kw in keywords if kw.lower() not in answer_lower]
        
        if not missing:
            score = rule.score_modifier
            feedback = rule.feedback_template.format(found=found)
        else:
            score = rule.score_modifier * (len(found) / len(keywords)) if keywords else 0
            feedback = f"Missing concepts: {', '.join(missing)}"
        
        return {"score": score, "feedback": feedback, "matched": len(missing) == 0}

    def _eval_contains_any(
        self, answer_str: str, student_answer: Any, rule: ScoringRule
    ) -> Dict[str, Any]:
        """Check if answer contains any of the keywords."""
        keywords = rule.conditions.get("keywords", [])
        answer_lower = answer_str.lower()
        
        found = [kw for kw in keywords if kw.lower() in answer_lower]
        
        matched = len(found) > 0
        # Proportional scoring
        score = rule.score_modifier * (len(found) / len(keywords)) if keywords else 0
        
        return {
            "score": score,
            "feedback": f"Found keywords: {', '.join(found)}" if found else "No required keywords found",
            "matched": matched,
        }

    def _eval_regex_match(
        self, answer_str: str, student_answer: Any, rule: ScoringRule
    ) -> Dict[str, Any]:
        """Regex pattern matching."""
        pattern = rule.conditions.get("pattern", "")
        
        try:
            matched = bool(re.search(pattern, answer_str, re.IGNORECASE))
            return {
                "score": rule.score_modifier if matched else 0,
                "feedback": "Pattern match found" if matched else f"Pattern not found: {pattern}",
                "matched": matched,
            }
        except re.error as e:
            logger.warning(f"Invalid regex pattern: {pattern}, error: {e}")
            return {"score": 0, "feedback": "Invalid pattern in rule", "matched": False}

    def _eval_numeric_range(
        self, answer_str: str, student_answer: Any, rule: ScoringRule
    ) -> Dict[str, Any]:
        """Numeric range check."""
        try:
            # Try to extract number from answer
            numbers = re.findall(r"-?\d+\.?\d*", answer_str)
            if not numbers:
                return {"score": 0, "feedback": "No numeric answer found", "matched": False}
            
            actual = float(numbers[0])
            min_val = rule.conditions.get("min", float("-inf"))
            max_val = rule.conditions.get("max", float("inf"))
            
            in_range = min_val <= actual <= max_val
            
            return {
                "score": rule.score_modifier if in_range else 0,
                "feedback": f"Answer {actual} is {'in' if in_range else 'outside'} range [{min_val}, {max_val}]",
                "matched": in_range,
            }
        except ValueError:
            return {"score": 0, "feedback": "Could not parse numeric answer", "matched": False}

    def _eval_numeric_tolerance(
        self, answer_str: str, student_answer: Any, rule: ScoringRule
    ) -> Dict[str, Any]:
        """Numeric evaluation with tolerance."""
        try:
            numbers = re.findall(r"-?\d+\.?\d*", answer_str)
            if not numbers:
                return {"score": 0, "feedback": "No numeric answer found", "matched": False}
            
            actual = float(numbers[0])
            expected = float(rule.conditions.get("expected", 0))
            tolerance_pct = rule.conditions.get("tolerance", self.config.default_scoring_tolerance)
            
            tolerance = expected * tolerance_pct
            diff = abs(actual - expected)
            in_tolerance = diff <= tolerance
            
            if in_tolerance:
                # Full credit within tolerance
                score = rule.score_modifier
                feedback = f"Correct! (Answer: {actual}, Expected: {expected})"
            else:
                # Partial credit based on how close
                if diff <= tolerance * 2:
                    score = rule.score_modifier * 0.5
                    feedback = f"Partially correct. Answer {actual} is close but outside tolerance."
                else:
                    score = 0
                    feedback = f"Incorrect. Answer: {actual}, Expected: {expected}"
            
            return {"score": score, "feedback": feedback, "matched": in_tolerance}
            
        except ValueError:
            return {"score": 0, "feedback": "Could not parse numeric answer", "matched": False}

    def _eval_keyword_count(
        self, answer_str: str, student_answer: Any, rule: ScoringRule
    ) -> Dict[str, Any]:
        """Count keyword occurrences."""
        keyword = rule.conditions.get("keyword", "").lower()
        min_count = rule.conditions.get("min_count", 1)
        
        count = answer_str.lower().count(keyword)
        matched = count >= min_count
        
        return {
            "score": rule.score_modifier if matched else 0,
            "feedback": f"Keyword '{keyword}' found {count} time(s) (minimum: {min_count})",
            "matched": matched,
        }

    def _eval_length_range(
        self, answer_str: str, student_answer: Any, rule: ScoringRule
    ) -> Dict[str, Any]:
        """Check answer length."""
        length = len(answer_str)
        min_len = rule.conditions.get("min_length", 0)
        max_len = rule.conditions.get("max_length", float("inf"))
        
        in_range = min_len <= length <= max_len
        
        return {
            "score": rule.score_modifier if in_range else 0,
            "feedback": f"Answer length: {length} chars (range: {min_len}-{max_len})",
            "matched": in_range,
        }

    def _calc_partial_credit(
        self, result: Dict[str, Any], rule: ScoringRule, max_score: float
    ) -> Dict[str, Any]:
        """Calculate partial credit based on rule config."""
        config = rule.partial_credit_config or {}
        base_score = result.get("score", 0)
        
        # Partial credit multipliers
        if "step_multipliers" in config:
            for step, multiplier in config["step_multipliers"].items():
                if base_score >= float(step):
                    return {
                        "score": base_score * multiplier,
                        "feedback": f"{result.get('feedback', '')} (partial credit: {multiplier}x)"
                    }
        
        return {"score": base_score, "feedback": result.get("feedback", "")}

    def _generate_feedback(
        self, feedbacks: List[str], total_score: float, max_score: float
    ) -> str:
        """Generate overall feedback from individual rule feedbacks."""
        if not feedbacks:
            return f"Score: {total_score:.1f}/{max_score}"
        
        # Deduplicate and join
        unique = list(dict.fromkeys(feedbacks))
        feedback_text = " | ".join(unique)
        
        return f"[{total_score:.1f}/{max_score}] {feedback_text}"

    def _default_scoring(
        self,
        question_id: str,
        student_answer: Any,
        question_type: QuestionType,
        max_score: float,
    ) -> GradingResult:
        """Fallback default scoring when no rules are defined."""
        feedback_map = {
            QuestionType.MULTIPLE_CHOICE: "Multiple choice grading requires expected answer",
            QuestionType.SHORT_ANSWER: "Short answer grading requires rubric or expected answer",
            QuestionType.ESSAY: "Essay grading requires LLM evaluation",
            QuestionType.FILL_IN_BLANK: "Fill-in-blank grading requires expected answers",
            QuestionType.TRUE_FALSE: "True/False grading requires expected answers",
            QuestionType.CODING: "Coding evaluation requires rubric",
            QuestionType.MATH: "Math evaluation requires expected answer or rubric",
        }
        
        return GradingResult(
            question_id=question_id,
            score=0,
            max_score=max_score,
            feedback=feedback_map.get(question_type, "No grading rules defined"),
            details={"error": "no_rules_defined"},
        )

    def _normalize_answer(self, answer: Any) -> str:
        """Normalize answer to string for rule evaluation."""
        if isinstance(answer, str):
            return answer.strip()
        elif isinstance(answer, list):
            return ", ".join(str(a) for a in answer)
        elif isinstance(answer, dict):
            return json.dumps(answer, ensure_ascii=False)
        else:
            return str(answer)
