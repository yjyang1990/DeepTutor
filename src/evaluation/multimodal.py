# -*- coding: utf-8 -*-
"""
Multimodal LLM integration for AI Evaluation.
Uses Claude API for vision + text processing.
"""

from __future__ import annotations

import base64
import time
from io import BytesIO
from typing import Any, Dict, List, Optional, Union

from PIL import Image

from src.logging import get_logger

from .config import EvaluationConfig, get_evaluation_config


logger = get_logger(__name__)


class MultimodalLLMService:
    """
    Multimodal LLM service for evaluation tasks.
    
    Uses Claude API with vision capabilities to process:
    - Student answer images (handwritten or printed)
    - Scanned answer sheets
    - Diagrams and figures in answers
    """

    def __init__(self, config: Optional[EvaluationConfig] = None):
        self.config = config or get_evaluation_config()
        self._client = None

    @property
    def client(self):
        """Lazy-load the Anthropic client."""
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(
                api_key=self.config.llm.api_key,
                base_url=self.config.llm.base_url if hasattr(self.config.llm, 'base_url') else None,
            )
        return self._client

    async def grade_with_vision(
        self,
        question_text: str,
        student_answer_image: Union[str, bytes, Image.Image],
        rubric: str,
        max_score: float,
    ) -> Dict[str, Any]:
        """
        Grade a student answer from an image using Claude vision.
        
        Args:
            question_text: The question being answered
            student_answer_image: The student's answer as image (path, bytes, or PIL Image)
            rubric: The grading rubric/criteria
            max_score: Maximum possible score
            
        Returns:
            Dict with 'score', 'feedback', and 'details'
        """
        start_time = time.time()
        
        # Convert image to base64
        if isinstance(student_answer_image, Image.Image):
            image_bytes = self._pil_to_bytes(student_answer_image)
        elif isinstance(student_answer_image, str):
            with open(student_answer_image, "rb") as f:
                image_bytes = f.read()
        else:
            image_bytes = student_answer_image
        
        media_type = self._detect_media_type(image_bytes)
        image_data = base64.b64encode(image_bytes).decode("utf-8")
        
        prompt = self._build_vision_prompt(question_text, rubric, max_score)
        
        try:
            response = await self.client.messages.create(
                model=self.config.llm.model,
                max_tokens=self.config.llm.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt,
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                        ],
                    }
                ],
            )
            
            content = response.content[0].text if response.content else ""
            
            # Parse the response
            result = self._parse_vision_response(content, max_score)
            result["processing_time_ms"] = (time.time() - start_time) * 1000
            result["model_used"] = self.config.llm.model
            
            return result
            
        except Exception as e:
            logger.error(f"Vision grading failed: {e}")
            return {
                "score": 0,
                "feedback": f"Grading failed: {str(e)}",
                "details": {"error": str(e)},
                "processing_time_ms": (time.time() - start_time) * 1000,
                "model_used": self.config.llm.model,
            }

    async def grade_text_answer(
        self,
        question_text: str,
        student_answer: str,
        rubric: str,
        max_score: float,
        question_type: str = "short_answer",
    ) -> Dict[str, Any]:
        """
        Grade a text-based answer using Claude.
        
        Args:
            question_text: The question being answered
            student_answer: The student's text answer
            rubric: The grading rubric
            max_score: Maximum possible score
            question_type: Type of question (short_answer, essay, etc.)
            
        Returns:
            Dict with 'score', 'feedback', and 'details'
        """
        start_time = time.time()
        
        prompt = self._build_text_prompt(
            question_text, student_answer, rubric, max_score, question_type
        )
        
        try:
            response = await self.client.messages.create(
                model=self.config.llm.model,
                max_tokens=self.config.llm.max_tokens,
                temperature=self.config.llm.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            
            content = response.content[0].text if response.content else ""
            result = self._parse_text_response(content, max_score)
            result["processing_time_ms"] = (time.time() - start_time) * 1000
            result["model_used"] = self.config.llm.model
            
            return result
            
        except Exception as e:
            logger.error(f"Text grading failed: {e}")
            return {
                "score": 0,
                "feedback": f"Grading failed: {str(e)}",
                "details": {"error": str(e)},
                "processing_time_ms": (time.time() - start_time) * 1000,
                "model_used": self.config.llm.model,
            }

    async def grade_multiple_choice(
        self,
        question_text: str,
        options: List[str],
        student_answer: Union[str, int],  # Option letter or index
        correct_answer: Union[str, int],
    ) -> Dict[str, Any]:
        """
        Grade a multiple choice question (can use simple matching).
        
        Args:
            question_text: The question text
            options: List of answer options
            student_answer: Student's selected option (letter or index)
            correct_answer: Correct option (letter or index)
            
        Returns:
            Dict with 'score', 'feedback', and 'details'
        """
        # Normalize answers to indices
        def normalize(ans):
            if isinstance(ans, int):
                return ans
            if isinstance(ans, str) and len(ans) == 1 and ans.isalpha():
                return ord(ans.upper()) - ord("A")
            return 0
        
        student_idx = normalize(student_answer)
        correct_idx = normalize(correct_answer)
        
        is_correct = student_idx == correct_idx
        max_score = 1.0
        
        return {
            "score": max_score if is_correct else 0.0,
            "feedback": f"{'Correct! ✓' if is_correct else f'Incorrect. The correct answer was {correct_answer}.'}",
            "details": {
                "is_correct": is_correct,
                "student_answer": student_idx,
                "correct_answer": correct_idx,
                "max_score": max_score,
            },
            "model_used": "rule_based",  # MCQ doesn't need LLM
        }

    def _build_vision_prompt(
        self, question_text: str, rubric: str, max_score: float
    ) -> str:
        """Build the prompt for vision-based grading."""
        return f"""You are an AI teaching assistant grading a student's answer.

## Question
{question_text}

## Grading Rubric
{rubric}

## Maximum Score
{max_score} points

## Instructions
1. Analyze the student's handwritten or printed answer in the image.
2. Compare it carefully against the rubric.
3. Award partial credit where appropriate.
4. Provide specific, constructive feedback.

## Output Format
Provide your grading in this exact format:
SCORE: [numeric score]
FEEDBACK: [Your constructive feedback explaining the grade]
DETAILS: [Any additional observations]"""

    def _build_text_prompt(
        self,
        question_text: str,
        student_answer: str,
        rubric: str,
        max_score: float,
        question_type: str,
    ) -> str:
        """Build the prompt for text-based grading."""
        type_specific = {
            "short_answer": "Provide precise feedback identifying what is correct/incorrect.",
            "essay": "Evaluate for content accuracy, organization, depth, and clarity.",
            "math": "Check each step for mathematical correctness. Show your work analysis.",
            "coding": "Evaluate for correctness, efficiency, and code quality.",
        }.get(question_type, "Provide balanced and fair feedback.")
        
        return f"""You are an AI teaching assistant grading a student's answer.

## Question
{question_text}

## Student's Answer
{student_answer}

## Grading Rubric
{rubric}

## Maximum Score
{max_score} points

## Question Type
{question_type}

## Instructions
{type_specific}
Be generous with partial credit when the answer shows understanding.
Provide specific examples from the answer in your feedback.

## Output Format
Provide your grading in this exact format:
SCORE: [numeric score between 0 and {max_score}]
FEEDBACK: [Your constructive feedback explaining the grade, 2-3 sentences]
DETAILS: [Key observations about the answer]"""

    def _parse_vision_response(self, content: str, max_score: float) -> Dict[str, Any]:
        """Parse Claude's vision grading response."""
        result = {"score": 0, "feedback": "", "details": {}}
        
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("SCORE:"):
                try:
                    score_str = line.replace("SCORE:", "").strip()
                    # Handle fractions like "8/10"
                    if "/" in score_str:
                        parts = score_str.split("/")
                        result["score"] = float(parts[0]) / float(parts[1]) * max_score
                    else:
                        result["score"] = float(score_str)
                except ValueError:
                    result["score"] = 0
            elif line.startswith("FEEDBACK:"):
                result["feedback"] = line.replace("FEEDBACK:", "").strip()
            elif line.startswith("DETAILS:"):
                result["details"]["observations"] = line.replace("DETAILS:", "").strip()
        
        # Fallback: if we couldn't parse, use the whole content as feedback
        if not result["feedback"]:
            result["feedback"] = content[:500]
        
        return result

    def _parse_text_response(self, content: str, max_score: float) -> Dict[str, Any]:
        """Parse Claude's text grading response."""
        return self._parse_vision_response(content, max_score)

    def _pil_to_bytes(self, image: Image.Image) -> bytes:
        """Convert PIL Image to bytes."""
        buffer = BytesIO()
        # Convert to RGB if necessary
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()

    def _detect_media_type(self, image_bytes: bytes) -> str:
        """Detect image media type from bytes."""
        if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        elif image_bytes[:2] == b"\xff\xd8":
            return "image/jpeg"
        elif image_bytes[:6] in (b"GIF87a", b"GIF89a"):
            return "image/gif"
        elif image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
            return "image/webp"
        return "image/jpeg"  # Default to JPEG
