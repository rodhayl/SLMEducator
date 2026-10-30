"""
Exercise Generator Service - Phase 2
Generates practice exercises and questions using AI
"""

from typing import List, Dict, Any
from enum import Enum
import json
import logging

from .database import get_db_service
from .settings_config_service import SettingsConfigService
from .content_service import get_content_service


class QuestionType(Enum):
    """Types of questions that can be generated"""

    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    FILL_IN_BLANK = "fill_in_blank"


class ExerciseGeneratorService:
    """Service for generating practice exercises"""

    def __init__(self):
        self.db = get_db_service()
        self.settings_service = SettingsConfigService()
        self.content_service = get_content_service()
        self.ai_service = None
        self.logger = logging.getLogger(__name__)

    def _get_ai_service(self):
        """Lazy load AI service"""
        if self.ai_service is None:
            from .ai_service import AIService, RuntimeAIConfig

            ai_defaults = self.settings_service.get_ai_config_defaults()
            config = RuntimeAIConfig(
                provider=ai_defaults.get("default_provider", "openrouter"),
                model=ai_defaults.get(
                    "default_model", "openrouter/sherlock-dash-alpha"
                ),
                api_key=ai_defaults.get("openrouter_api_key"),
            )

            self.ai_service = AIService(
                config, logging.getLogger("ExerciseGeneratorService")
            )

        return self.ai_service

    def generate_exercises(
        self, topic: str, count: int = 5, difficulty_level: str = "medium"
    ) -> List[Dict[str, Any]]:
        """
        Generate practice exercises for a topic using AI

        Args:
            topic: The topic to generate exercises for
            count: Number of exercises to generate
            difficulty_level: Difficulty level (easy, medium, hard)

        Returns:
            List of exercise dictionaries
        """
        ai = self._get_ai_service()

        prompt = f"""Generate {count} {difficulty_level} practice exercises for learning about {topic}.

Return ONLY a JSON array:
[
    {{
        "question": "Exercise question text?",
        "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
        "correct_answer": 0,
        "explanation": "Why this is the correct answer",
        "difficulty": "{difficulty_level}"
    }}
]

Make exercises appropriate for {difficulty_level} level learners."""

        try:
            response = ai.generate_content(context=prompt)
            import re

            json_match = re.search(r"\[.*?\]", response, re.DOTALL)
            if json_match:
                exercises = json.loads(json_match.group())
                return exercises
            # Return default exercises on parse failure
            return [
                {
                    "question": f"What is {topic}?",
                    "options": [
                        "A) Correct answer",
                        "B) Wrong answer",
                        "C) Wrong answer",
                        "D) Wrong answer",
                    ],
                    "correct_answer": 0,
                    "explanation": f"Basic understanding of {topic}",
                    "difficulty": difficulty_level,
                }
            ]
        except Exception:
            return [
                {
                    "question": f"Define {topic}",
                    "options": [
                        "A) Correct",
                        "B) Incorrect",
                        "C) Incorrect",
                        "D) Incorrect",
                    ],
                    "correct_answer": 0,
                    "explanation": f"Testing knowledge of {topic}",
                    "difficulty": difficulty_level,
                }
            ]

    def generate_questions(
        self,
        content_id: int,
        question_type: QuestionType = QuestionType.MULTIPLE_CHOICE,
        num_questions: int = 5,
    ) -> List[Dict[str, Any]]:
        """Generate practice questions for content"""
        content = self.content_service.get_content(content_id)
        if not content:
            return []

        content_data = content.decrypted_content_data or {}
        text = content_data.get("text", "")

        if not text:
            return []

        ai = self._get_ai_service()

        if question_type == QuestionType.MULTIPLE_CHOICE:
            prompt = f"""Generate {num_questions} multiple choice questions based on this content.

Content:
{text[:2000]}

Return ONLY a JSON array:
[
    {{
        "question": "Question text?",
        "options": ["A)", "B)", "C)", "D)"],
        "correct_answer": 0,
        "explanation": "Why this is correct"
    }}
]"""
        else:
            prompt = f"""Generate {num_questions} {question_type.value} questions based on this content.

Content:
{text[:2000]}

Return ONLY a JSON array of question objects."""

        try:
            response = ai.generate_content(context=prompt)
            import re

            json_match = re.search(r"\[.*?\]", response, re.DOTALL)
            if json_match:
                questions = json.loads(json_match.group())
                return questions
            return []
        except Exception as e:
            self.logger.error(f"Failed to generate exercises: {e}")
            return []


# Singleton
_exercise_generator_service = None


def get_exercise_generator_service() -> ExerciseGeneratorService:
    """Get or create exercise generator service singleton"""
    global _exercise_generator_service
    if _exercise_generator_service is None:
        _exercise_generator_service = ExerciseGeneratorService()
    return _exercise_generator_service
