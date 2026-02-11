"""
AI Service for SLMEducator - Handles AI content generation and tutoring functionality.

This module provides AI integration for both local (Ollama/LM Studio) and cloud providers (OpenAI),
implementing the AI requirements from the specification document.
"""

import json
import ast
import re
import weakref
import time
import httpx
from typing import Dict, List, Optional, Any, Protocol
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import logging

from ..models import User, Content, LearningSession, AIModelConfig
from .settings_config_service import get_settings_service
from ..exceptions import AIServiceError, ConfigurationError
from ..security_utils import sanitize_input, sanitize_prompt


class AIProvider(Enum):
    """Supported AI providers."""

    OPENAI = "openai"
    OLLAMA = "ollama"
    LM_STUDIO = "lm_studio"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"


@dataclass
class RuntimeAIConfig:
    """Runtime AI configuration."""

    provider: str
    model: str
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    preprocessing_model: Optional[str] = None
    enable_preprocessing: bool = False


@dataclass
class AIRequest:
    """AI request configuration."""

    prompt: str
    model: str
    max_tokens: int = 1000
    temperature: float = 0.7
    provider: AIProvider = AIProvider.OLLAMA
    system_prompt: Optional[str] = None


@dataclass
class AIResponse:
    """AI response data."""

    content: str
    tokens_used: int
    model: str
    provider: AIProvider
    response_time: float
    timestamp: datetime


class LoggerLike(Protocol):
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> Any: ...

    def info(self, msg: str, *args: Any, **kwargs: Any) -> Any: ...

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> Any: ...

    def error(self, msg: str, *args: Any, **kwargs: Any) -> Any: ...


class AIService:
    """
    AI Service for content generation and tutoring functionality.

    This service handles AI integration for:
    - Study plan generation
    - Content creation and enhancement
    - Exercise and quiz generation
    - Tutoring and explanation
    - Progress assessment
    """

    def __init__(self, config: AIModelConfig, logger: LoggerLike):
        """Initialize AI service with configuration."""
        self.config = config
        self.logger = logger
        self.settings_service = get_settings_service()
        self.model = str(config.model or "unknown")
        self.provider = AIProvider(str(config.provider))
        self._client: httpx.Client
        self._setup_client()

    def _setup_client(self):
        """Setup HTTP client for AI requests."""
        timeout = httpx.Timeout(300.0, connect=30.0)  # Increased for slow local LLMs
        self._client = httpx.Client(timeout=timeout)
        # Ensure client is closed when self is garbage collected
        try:
            weakref.finalize(self, self._client.close)
        except Exception:
            # If finalize fails for some reason, fallback to relying on close()/__del__()
            pass

    def _make_request(self, request: AIRequest) -> AIResponse:
        """Make AI request using AIRequest dataclass."""
        return self._call_ai(
            prompt=request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system_prompt=request.system_prompt,
        )

    def generate_study_plan(
        self,
        user: User,
        subject: str,
        grade_level: str,
        learning_objectives: List[str],
        duration_weeks: int,
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive study plan with AI assistance.

        Args:
            user: The teacher creating the study plan
            subject: Subject area (e.g., 'Mathematics', 'Science')
            grade_level: Target grade level
            learning_objectives: List of learning objectives
            duration_weeks: Duration in weeks

        Returns:
            Generated study plan structure

        Raises:
            AIServiceError: If AI generation fails
        """
        self.logger.info(f"Generating study plan for {subject} (Grade {grade_level})")

        prompt = self._build_study_plan_prompt(
            subject, grade_level, learning_objectives, duration_weeks
        )

        try:
            response = self._call_ai(prompt, max_tokens=2000, temperature=0.8)
            study_plan_data = self._parse_study_plan_response(response.content)

            self.logger.info(
                f"Successfully generated study plan with {len(study_plan_data.get('phases', []))} phases"
            )
            return study_plan_data

        except Exception as e:
            self.logger.error(f"Failed to generate study plan: {e}")
            raise AIServiceError(f"Study plan generation failed: {e}")

    def enhance_content(
        self, content: Content, enhancement_type: str = "explanation"
    ) -> Content:
        """
        Enhance existing content with AI assistance.

        Args:
            content: Content to enhance
            enhancement_type: Type of enhancement ('explanation', 'examples', 'simplification')

        Returns:
            Enhanced content

        Raises:
            AIServiceError: If enhancement fails
        """
        self.logger.info(f"Enhancing content {content.id} with {enhancement_type}")

        prompt = self._build_enhancement_prompt(content, enhancement_type)

        try:
            response = self._call_ai(prompt, max_tokens=1500, temperature=0.6)
            enhanced_data = self._parse_enhancement_response(response.content)

            enhanced_content = enhanced_data.get("enhanced_content")
            enhancement_metadata = {
                "enhancement_type": enhancement_type,
                "enhancement_timestamp": datetime.now().isoformat(),
                "ai_model": response.model,
                "tokens_used": response.tokens_used,
            }
            existing_decrypted = content.decrypted_content_data
            if existing_decrypted is not None and not isinstance(
                existing_decrypted, dict
            ):
                existing_decrypted = None
            if existing_decrypted is None:
                if isinstance(enhanced_content, str):
                    content.content_data = enhanced_content
                else:
                    content.set_encrypted_content_data(
                        {"enhanced_content": enhanced_content}
                    )
            else:
                updated: Dict[str, Any] = dict(existing_decrypted)
                if enhanced_content is not None:
                    updated["enhanced_content"] = enhanced_content
                updated["ai_enhancement"] = enhancement_metadata
                content.set_encrypted_content_data(updated)

            setattr(content, "ai_enhanced", True)
            setattr(content, "ai_metadata", enhancement_metadata)

            self.logger.info(f"Successfully enhanced content {content.id}")
            return content

        except Exception as e:
            self.logger.error(f"Failed to enhance content {content.id}: {e}")
            raise AIServiceError(f"Content enhancement failed: {e}")

    def generate_exercise(
        self, topic: str, difficulty: str, exercise_type: str = "multiple_choice"
    ) -> Dict[str, Any]:
        """
        Generate educational exercises with AI.

        Args:
            topic: Topic for the exercise
            difficulty: Difficulty level ('easy', 'medium', 'hard')
            exercise_type: Type of exercise ('multiple_choice', 'true_false', 'short_answer')

        Returns:
            Generated exercise data

        Raises:
            AIServiceError: If generation fails
        """
        self.logger.info(
            f"Generating {difficulty} {exercise_type} exercise for {topic}"
        )

        prompt = self._build_exercise_prompt(topic, difficulty, exercise_type)

        try:
            response = self._call_ai(prompt, max_tokens=1000, temperature=0.7)
            exercise_data = self._parse_exercise_response(response.content, topic)

            self.logger.info(f"Successfully generated exercise for {topic}")
            return exercise_data

        except Exception as e:
            self.logger.error(f"Failed to generate exercise for {topic}: {e}")
            raise AIServiceError(f"Exercise generation failed: {e}")

    def generate_lesson(
        self,
        topic: str,
        grade_level: str,
        learning_objectives: List[str],
        duration_minutes: int = 30,
        source_material: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a structured lesson with AI assistance.

        Args:
            topic: Topic for the lesson
            grade_level: Target grade level
            learning_objectives: List of learning objectives for this lesson
            duration_minutes: Estimated lesson duration
            source_material: Optional text context from uploaded files

        Returns:
            Generated lesson data with sections, examples, and key points

        Raises:
            AIServiceError: If generation fails
        """
        self.logger.info(f"Generating lesson for topic: {topic} (Grade {grade_level})")

        objectives_str = "\n".join(f"- {obj}" for obj in learning_objectives)

        context_block = ""
        if source_material:
            truncated = (
                source_material[:3000] + "..."
                if len(source_material) > 3000
                else source_material
            )
            context_block = f"\nSOURCE MATERIAL:\nUse the following content as the source of truth:\n{truncated}\n"

        prompt = f"""
        Create a comprehensive educational lesson on the topic: {topic}

        Target Grade Level: {grade_level}
        Estimated Duration: {duration_minutes} minutes
        {context_block}

        Learning Objectives:
        {objectives_str}

        Generate a structured lesson with the following format:
        {{
            "title": "Lesson title",
            "topic": "{topic}",
            "grade_level": "{grade_level}",
            "duration_minutes": {duration_minutes},
            "sections": [
                {{
                    "title": "Section title",
                    "content": "Main content text (detailed)",
                    "key_points": ["point1", "point2"],
                    "examples": ["example1", "example2"]
                }}
            ],
            "summary": "Brief lesson summary",
            "vocabulary": [
                {{"term": "term1", "definition": "definition1"}}
            ],
            "discussion_questions": ["question1", "question2"]
        }}

        Ensure the lesson is:
        - Age-appropriate for grade {grade_level}
        - Engaging and interactive
        - Progressive in complexity
        - Aligned with the learning objectives
        - Derived from the SOURCE MATERIAL if provided

        Return only valid JSON.
        """

        try:
            response = self._call_ai(prompt, max_tokens=2000, temperature=0.7)
            lesson_data = self._parse_json_response(response.content, "lesson")

            self.logger.info(f"Successfully generated lesson for {topic}")
            return lesson_data

        except Exception as e:
            self.logger.error(f"Failed to generate lesson for {topic}: {e}")
            raise AIServiceError(f"Lesson generation failed: {e}")

    def generate_topic_content(
        self,
        subject: str,
        topic_name: str,
        grade_level: str,
        learning_objectives: List[str],
        content_types: Optional[List[str]] = None,
        source_material: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate complete topic content package with AI assistance.

        Args:
            subject: Subject area (e.g., 'Biology', 'Mathematics')
            topic_name: Name of the topic
            grade_level: Target grade level
            learning_objectives: List of learning objectives
            content_types: Types to generate (default: ['lesson', 'exercise'])
            source_material: Optional text context from uploaded files

        Returns:
            Complete topic package with lesson, exercises, and metadata

        Raises:
            AIServiceError: If generation fails
        """
        if content_types is None:
            content_types = ["lesson", "exercise"]

        self.logger.info(f"Generating topic content for: {subject} - {topic_name}")

        objectives_str = "\n".join(f"- {obj}" for obj in learning_objectives)
        types_str = ", ".join(content_types)

        context_block = ""
        if source_material:
            truncated = (
                source_material[:3500] + "..."
                if len(source_material) > 3500
                else source_material
            )
            context_block = f"\nSOURCE MATERIAL:\nUse the following content as the source of truth:\n{truncated}\n"

        prompt = f"""
        Create a complete educational content package for:

        Subject: {subject}
        Topic: {topic_name}
        Grade Level: {grade_level}
        {context_block}

        Learning Objectives:
        {objectives_str}

        Content to generate: {types_str}

        Generate comprehensive content in this format:
        {{
            "topic": "{topic_name}",
            "subject": "{subject}",
            "grade_level": "{grade_level}",
            "learning_objectives": {json.dumps(learning_objectives)},
            "lesson": {{
                "title": "Lesson: {topic_name}",
                "sections": [
                    {{
                        "title": "Section title",
                        "content": "Educational content text",
                        "key_points": ["point1", "point2"]
                    }}
                ],
                "summary": "Brief lesson summary"
            }},
            "exercises": [
                {{
                    "title": "Exercise title",
                    "type": "multiple_choice",
                    "difficulty": "medium",
                    "question": "Question text",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                    "explanation": "Why this is correct"
                }}
            ],
            "vocabulary": [
                {{"term": "term1", "definition": "definition1"}}
            ]
        }}

        Create engaging, age-appropriate content that covers all learning objectives.
        Include at least 2-3 exercises of varying difficulty.
        Derived from the SOURCE MATERIAL if provided.
        Return only valid JSON.
        """

        try:
            response = self._call_ai(prompt, max_tokens=3000, temperature=0.7)
            topic_data = self._parse_json_response(response.content, "topic_content")

            self.logger.info(f"Successfully generated topic content for {topic_name}")
            return topic_data

        except Exception as e:
            self.logger.error(f"Failed to generate topic content for {topic_name}: {e}")
            raise AIServiceError(f"Topic content generation failed: {e}")

    def generate_assessment_questions(
        self,
        topic: str,
        learning_objectives: List[str],
        question_types: Optional[List[str]] = None,
        num_questions: int = 5,
        difficulty: str = "medium",
    ) -> List[Dict[str, Any]]:
        """
        Generate assessment questions with AI assistance.

        Args:
            topic: Topic for the questions
            learning_objectives: Learning objectives to assess
            question_types: Types of questions (default: mixed)
            num_questions: Number of questions to generate
            difficulty: Overall difficulty level ('easy', 'medium', 'hard')

        Returns:
            List of generated questions with answers and metadata

        Raises:
            AIServiceError: If generation fails
        """
        if question_types is None:
            question_types = ["multiple_choice", "true_false", "short_answer"]

        self.logger.info(
            f"Generating {num_questions} assessment questions for: {topic}"
        )

        objectives_str = "\n".join(f"- {obj}" for obj in learning_objectives)
        types_str = ", ".join(question_types)

        prompt = f"""
        Generate {num_questions} assessment questions for the topic: {topic}

        Learning Objectives to assess:
        {objectives_str}

        Question Types: {types_str}
        Overall Difficulty: {difficulty}

        Generate questions in this format:
        {{
            "questions": [
                {{
                    "question_text": "Question text",
                    "question_type": "multiple_choice",
                    "points": 10,
                    "correct_answer": "The correct answer",
                    "options": {{"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}},
                    "explanation": "Why this answer is correct"
                }}
            ]
        }}

        Requirements:
        - Mix of question types from: {types_str}
        - Align with learning objectives
        - Provide clear correct answers and explanations
        - For multiple choice, provide 4 plausible options

        Return only valid JSON.
        """

        try:
            response = self._call_ai(prompt, max_tokens=2500, temperature=0.7)
            parsed = self._parse_json_response(response.content, "assessment_questions")

            questions = parsed.get("questions", [])
            self.logger.info(
                f"Successfully generated {len(questions)} questions for {topic}"
            )
            return questions

        except Exception as e:
            self.logger.error(f"Failed to generate questions for {topic}: {e}")
            raise AIServiceError(f"Assessment question generation failed: {e}")

    def generate_course_outline(
        self,
        subject: str,
        grade_level: str,
        duration_weeks: int = 4,
        source_material: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a hierarchical course outline (Units -> Lessons).

        Args:
            subject: The subject matter (e.g. "Intro to Biology")
            grade_level: Target grade
            duration_weeks: Length of the course
            source_material: Optional text context from uploaded files

        Returns:
            JSON structure with 'units' containing 'lessons'.
        """
        self.logger.info(f"Generating course outline for {subject}")

        context_block = ""
        if source_material:
            # Truncate if too long (approx 4000 chars for safety if using smaller models)
            truncated_material = (
                source_material[:4000] + "..."
                if len(source_material) > 4000
                else source_material
            )
            context_block = (
                f"\n\nSOURCE MATERIAL:\nUse the following material as the primary basis for the outline:\n"
                f"{truncated_material}\n"
            )

        prompt = f"""
        Create a detailed hierarchical course outline for: {subject}

        Target Grade: {grade_level}
        Duration: {duration_weeks} weeks
        {context_block}

        Structure the course into logical "Units" (major themes),
        and break each Unit down into "Lessons" (daily/specific topics).

        Format as JSON:
        {{
            "title": "Course Title",
            "description": "Course description",
            "units": [
                {{
                    "title": "Unit 1: Unit Name",
                    "description": "Unit description",
                    "lessons": [
                        {{
                            "title": "Lesson 1: Lesson Topic",
                            "duration": "45m",
                            "learning_objectives": ["obj1", "obj2"]
                        }}
                    ]
                }}
            ]
        }}

        Requirements:
        - Total {duration_weeks} weeks of content
        - Logical progression
        - Appropriate for {grade_level}
        """

        try:
            response = self._call_ai(prompt, max_tokens=2000, temperature=0.7)
            return self._parse_json_response(response.content, "course_outline")
        except Exception as e:
            self.logger.error(f"Failed to generate outline: {e}")
            raise AIServiceError(f"Outline generation failed: {e}")

    def _parse_json_response(
        self, response: str, context: str = "data"
    ) -> Dict[str, Any]:
        """
        Parse JSON from AI response with error handling.

        Args:
            response: Raw AI response string
            context: Context for error messages

        Returns:
            Parsed JSON as dictionary

        Raises:
            AIServiceError: If parsing fails
        """
        try:
            json_str = None

            if "```" in response:
                blocks = re.findall(
                    r"```(?:json)?\s*(.*?)\s*```", response, re.DOTALL | re.IGNORECASE
                )
                for block in blocks:
                    if "{" in block and "}" in block:
                        json_str = block
                        break

            if not json_str:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response[json_start:json_end]

            if not json_str:
                raise ValueError("No valid JSON found in response")

            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                normalized = (
                    json_str.replace("null", "None")
                    .replace("true", "True")
                    .replace("false", "False")
                )
                parsed = ast.literal_eval(normalized)
                if not isinstance(parsed, dict):
                    raise ValueError("Parsed response was not a JSON object")
                return parsed

        except (json.JSONDecodeError, ValueError, SyntaxError) as e:
            self.logger.error(f"Failed to parse {context} response: {e}")
            raise AIServiceError(f"Failed to parse AI response for {context}: {e}")

    def provide_tutoring(
        self,
        user: User,
        question: str,
        context: Optional[str] = None,
        study_plan_context: Optional[Dict[str, Any]] = None,
        content_context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Provide AI tutoring assistance with Two-LLM pipeline support.

        Args:
            user: Student requesting tutoring
            question: Student's question
            context: Optional context about the topic
            study_plan_context: Optional study plan summary for context
            content_context: Optional content summary for context
            conversation_history: Optional conversation history

        Returns:
            Tutoring response with explanation and guidance

        Raises:
            AIServiceError: If tutoring fails
        """
        self.logger.info(
            f"Providing tutoring for user {user['id'] if isinstance(user, dict) else user.id}"
        )

        # Sanitize user input
        question = sanitize_input(question)

        # Build context data for preprocessing
        context_data = {
            "user_query": question,
            "study_plan": study_plan_context,
            "content": content_context,
            "history": conversation_history or [],
        }

        self.logger.debug(
            f"AIService provide_tutoring - Study Plan: {study_plan_context}"
        )
        self.logger.debug(f"AIService provide_tutoring - Content: {content_context}")

        # Format context (uses Two-LLM if enabled)
        final_context_str = self._format_context(context_data)
        self.logger.debug(
            f"AIService provide_tutoring - Final context length: {len(final_context_str)}"
        )
        self.logger.debug(
            f"AIService provide_tutoring - Final context preview: {final_context_str[:200]}"
        )

        grade_level = (
            user.get("grade_level") if isinstance(user, dict) else user.grade_level
        )
        prompt = self._build_tutoring_prompt(question, final_context_str, grade_level)

        try:
            response = self._call_ai(prompt, max_tokens=1200, temperature=0.5)
            tutoring_data = self._parse_tutoring_response(response.content)

            self.logger.info("Successfully provided tutoring response")
            return tutoring_data

        except Exception as e:
            self.logger.error(f"Failed to provide tutoring: {e}")
            raise AIServiceError(f"Tutoring service failed: {e}")

    def _format_context(self, context_data: Dict[str, Any]) -> str:
        """Format raw context data into a string."""
        parts = []

        if context_data.get("study_plan"):
            plan = context_data["study_plan"]
            parts.append(f"Study Plan: {plan.get('title', 'Untitled')}")
            if plan.get("description"):
                parts.append(f"Description: {plan['description']}")

            # Add current phase info
            if plan.get("current_phase"):
                phase = plan["current_phase"]
                parts.append(f"Current Phase: {phase.get('name', 'Unknown')}")
                if phase.get("objectives"):
                    objs = ", ".join(phase["objectives"])
                    parts.append(f"Learning Objectives: {objs}")

        if context_data.get("content"):
            content = context_data["content"]
            parts.append(f"Current Content: {content.get('title', 'Untitled')}")
            if content.get("content_data"):
                # Truncate content data if too long
                content_text = str(content["content_data"])
                if len(content_text) > 2000:
                    content_text = content_text[:2000] + "... (truncated)"
                parts.append(f"Content Text: {content_text}")

        if context_data.get("history"):
            parts.append("\nConversation History:")
            for msg in context_data["history"][-10:]:  # Last 10 messages
                role = msg.get("role", "unknown")
                text = msg.get("content", "")
                parts.append(f"{role.upper()}: {text}")

        return "\n".join(parts)

    def assess_progress(
        self, user: User, learning_session: LearningSession
    ) -> Dict[str, Any]:
        """
        Assess student progress and provide recommendations.

        Args:
            user: Student to assess
            learning_session: Recent learning session data

        Returns:
            Progress assessment with recommendations

        Raises:
            AIServiceError: If assessment fails
        """
        self.logger.info(
            f"Assessing progress for user {user['id'] if isinstance(user, dict) else user.id}"
        )

        prompt = self._build_progress_assessment_prompt(user, learning_session)

        try:
            response = self._call_ai(prompt, max_tokens=800, temperature=0.4)
            assessment_data = self._parse_progress_assessment_response(response.content)

            self.logger.info(
                f"Successfully assessed progress for user "
                f"{user['id'] if isinstance(user, dict) else user.id}"
            )
            return assessment_data

        except Exception as e:
            self.logger.error(f"Failed to assess progress for user {user.id}: {e}")
            raise AIServiceError(f"Progress assessment failed: {e}")

    def generate_content(
        self, context: str, max_tokens: int = 1000, temperature: float = 0.7
    ) -> str:
        """
        Generate AI content for general tutoring purposes.

        Args:
            context: Full context including system prompt and user message
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated content as string

        Raises:
            AIServiceError: If content generation fails
        """
        # Sanitize context
        context = sanitize_prompt(context)

        try:
            # Extract system prompt and user message from context
            lines = context.strip().split("\n")
            system_prompt = None
            user_message = None

            # Simple parsing - look for system prompt and user question
            for i, line in enumerate(lines):
                if line.strip().startswith("Student's question:"):
                    user_message = line.replace("Student's question:", "").strip()
                    # Get preceding lines as potential system prompt
                    if i > 0:
                        system_prompt = "\n".join(lines[:i]).strip()
                    break

            # If we couldn't parse properly, use the whole context as prompt
            if not user_message:
                user_message = context

            # Use the existing AI call infrastructure
            response = self._call_ai(
                prompt=user_message,
                max_tokens=max_tokens,
                temperature=temperature,
                system_prompt=system_prompt,
            )

            return response.content

        except Exception as e:
            self.logger.error(f"Content generation failed: {e}")
            raise AIServiceError(f"Failed to generate content: {e}")

    def _preprocess_context(self, context: str) -> str:
        """
        Preprocess context using a smaller model before main AI call.

        This method uses the preprocessing_model (if configured) to
        summarize or restructure the context for more efficient processing
        by the main model.

        Args:
            context: The raw context string to preprocess

        Returns:
            Preprocessed context string (or original if preprocessing disabled)
        """
        # Check if preprocessing is enabled
        if not getattr(self.config, "enable_preprocessing", False):
            return context

        # Check if preprocessing model is configured
        preprocessing_model = getattr(self.config, "preprocessing_model", None)
        if not preprocessing_model:
            return context

        try:
            # Store the current model and switch to preprocessing model
            original_model = self.config.model
            self.config.model = preprocessing_model

            # Preprocess the context
            preprocessing_prompt = f"""Summarize and extract key information from the following context
for use in an educational tutoring response. Keep essential facts and questions:

{context}"""

            response = self._call_ai(
                prompt=preprocessing_prompt,
                max_tokens=500,
                temperature=0.3,  # Lower temperature for more focused output
            )

            # Restore original model
            self.config.model = original_model

            self.logger.debug(
                f"Preprocessed context from {len(context)} to {len(response.content)} chars"
            )
            return response.content

        except Exception as e:
            self.logger.warning(f"Context preprocessing failed, using original: {e}")
            # Restore model in case of failure
            if "original_model" in dir():
                self.config.model = original_model
            return context

    def _call_ai(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> AIResponse:
        """
        Make AI API call based on configured provider.

        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_prompt: Optional system prompt

        Returns:
            AI response data

        Raises:
            AIServiceError: If API call fails
        """
        start_time = time.time()

        try:
            if self.config.provider == AIProvider.OPENAI.value:
                response = self._call_openai(
                    prompt, max_tokens, temperature, system_prompt
                )
            elif self.config.provider == AIProvider.OLLAMA.value:
                response = self._call_ollama(
                    prompt, max_tokens, temperature, system_prompt
                )
            elif self.config.provider == AIProvider.LM_STUDIO.value:
                response = self._call_lm_studio(
                    prompt, max_tokens, temperature, system_prompt
                )
            elif self.config.provider == AIProvider.OPENROUTER.value:
                response = self._call_openrouter(
                    prompt, max_tokens, temperature, system_prompt
                )
            else:
                raise ConfigurationError(
                    f"Unsupported AI provider: {self.config.provider}"
                )

            response_time = time.time() - start_time

            ai_response = AIResponse(
                content=response["content"],
                tokens_used=response.get("tokens_used", 0),
                model=str(response.get("model") or self.config.model or "unknown"),
                provider=AIProvider(self.config.provider),
                response_time=response_time,
                timestamp=datetime.now(),
            )

            self.logger.info(
                f"AI call completed in {response_time:.2f}s, {ai_response.tokens_used} tokens used"
            )
            return ai_response

        except Exception as e:
            self.logger.error(f"AI call failed: {e}")
            raise AIServiceError(f"AI service unavailable: {e}")

    def _call_openai(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str],
    ) -> Dict[str, Any]:
        """Call OpenAI API."""
        if not self.config.api_key:
            raise ConfigurationError("OpenAI API key not configured")

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Get OpenAI endpoint from settings
        openai_endpoint = self.settings_service.get(
            "ai", "openai.endpoint", "https://api.openai.com/v1/chat/completions"
        )
        response = self._client.post(
            openai_endpoint, json=data, headers=headers, timeout=300.0
        )
        response.raise_for_status()

        result = response.json()

        # Handle different usage field formats from OpenRouter
        usage = result.get("usage", {})
        if usage and "total_tokens" in usage:
            tokens_used = usage["total_tokens"]
        elif usage and "input_tokens" in usage and "output_tokens" in usage:
            tokens_used = usage["input_tokens"] + usage["output_tokens"]
        else:
            tokens_used = 0

        return {
            "content": result["choices"][0]["message"]["content"],
            "tokens_used": tokens_used,
            "model": result["model"],
        }

    def _call_ollama(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str],
    ) -> Dict[str, Any]:
        """Call Ollama API."""
        # Get Ollama URL from settings
        ollama_url = self.settings_service.get(
            "ai", "ollama.url", "http://localhost:11434"
        )
        base_url = self.config.endpoint or ollama_url

        data = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        if system_prompt:
            data["system"] = system_prompt

        response = self._client.post(
            f"{base_url}/api/generate", json=data, timeout=300.0
        )
        response.raise_for_status()

        result = response.json()
        return {
            "content": result["response"],
            "tokens_used": result.get("prompt_eval_count", 0)
            + result.get("eval_count", 0),
            "model": self.config.model,
        }

    def _call_lm_studio(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str],
    ) -> Dict[str, Any]:
        """Call LM Studio API."""
        # Get LM Studio URL from settings
        lm_studio_url = self.settings_service.get(
            "ai", "lm_studio.url", "http://localhost:1234"
        )
        base_url = self.config.endpoint or lm_studio_url

        # Normalize the base URL - remove trailing /v1 if present to avoid duplication
        base_url = base_url.rstrip("/")
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        response = self._client.post(
            f"{base_url}/v1/chat/completions", json=data, timeout=300.0
        )
        response.raise_for_status()

        result = response.json()
        return {
            "content": result["choices"][0]["message"]["content"],
            "tokens_used": result.get("usage", {}).get("total_tokens", 0),
            "model": result["model"],
        }

    def _call_openrouter(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str],
    ) -> Dict[str, Any]:
        """Call OpenRouter API."""
        if not self.config.api_key:
            raise ConfigurationError("OpenRouter API key not configured")

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/slm-educator/slm-educator",
            "X-Title": "SLMEducator",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Get OpenRouter endpoint from settings
        openrouter_endpoint = self.settings_service.get(
            "ai", "openrouter.url", "https://openrouter.ai/api/v1/chat/completions"
        )
        self.logger.debug(f"Calling OpenRouter endpoint: {openrouter_endpoint}")
        self.logger.debug(
            "OpenRouter request metadata: "
            f"model={self.config.model}, messages={len(messages)}, max_tokens={max_tokens}, temperature={temperature}"
        )

        try:
            response = self._client.post(
                openrouter_endpoint, json=data, headers=headers, timeout=300.0
            )

            # Handle different HTTP status codes
            if response.status_code == 429:
                # Rate limit error
                self.logger.error(
                    f"OpenRouter rate limit exceeded: {response.status_code}"
                )
                retry_after = response.headers.get("retry-after", "60")
                raise AIServiceError(
                    f"Rate limit exceeded. Please try again in {retry_after} seconds."
                )
            elif response.status_code == 401:
                # Authentication error
                self.logger.error(
                    f"OpenRouter authentication failed: {response.status_code}"
                )
                raise AIServiceError(
                    "Authentication failed. Please check your API key."
                )
            elif response.status_code == 403:
                # Forbidden error
                self.logger.error(
                    f"OpenRouter access forbidden: {response.status_code}"
                )
                raise AIServiceError(
                    "Access forbidden. Please check your API permissions."
                )
            elif response.status_code == 503:
                # Service unavailable
                self.logger.error(
                    f"OpenRouter service unavailable: {response.status_code}"
                )
                raise AIServiceError(
                    "OpenRouter service is temporarily unavailable. Please try again later."
                )
            elif response.status_code >= 500:
                # Server errors
                self.logger.error(f"OpenRouter server error: {response.status_code}")
                raise AIServiceError(
                    f"OpenRouter server error ({response.status_code}). Please try again later."
                )
            elif response.status_code >= 400:
                # Client errors
                self.logger.error(f"OpenRouter client error: {response.status_code}")
                error_detail = ""
                try:
                    error_data = response.json()
                    error_detail = f": {error_data.get('error', {}).get('message', 'Unknown error')}"
                except Exception:
                    error_detail = f": {response.text[:200]}"
                raise AIServiceError(
                    f"Request failed ({response.status_code}){error_detail}"
                )

            response.raise_for_status()

            # Debug response
            self.logger.debug(f"OpenRouter response status: {response.status_code}")
            self.logger.debug(
                f"OpenRouter response content length: {len(response.text)}"
            )

            result = response.json()

            # Handle different usage field formats from OpenRouter
            usage = result.get("usage", {})
            if usage and "total_tokens" in usage:
                tokens_used = usage["total_tokens"]
            elif usage and "input_tokens" in usage and "output_tokens" in usage:
                tokens_used = usage["input_tokens"] + usage["output_tokens"]
            else:
                tokens_used = 0

            return {
                "content": result["choices"][0]["message"]["content"],
                "tokens_used": tokens_used,
                "model": result["model"],
            }

        except httpx.TimeoutException:
            self.logger.error("OpenRouter request timed out")
            raise AIServiceError(
                "Request timed out. The AI service is taking too long to respond."
            )
        except httpx.ConnectError as e:
            self.logger.error(f"OpenRouter connection failed: {e}")
            raise AIServiceError(
                "Failed to connect to OpenRouter. Please check your internet connection."
            )
        except httpx.HTTPStatusError as e:
            # This should have been handled above, but as a fallback
            self.logger.error(f"OpenRouter HTTP error: {e}")
            raise AIServiceError(f"HTTP error ({e.response.status_code}): {str(e)}")
        except Exception as e:
            self.logger.error(f"OpenRouter unexpected error: {e}")
            raise AIServiceError(f"Unexpected error: {str(e)}")

    def _build_study_plan_prompt(
        self,
        subject: str,
        grade_level: str,
        learning_objectives: List[str],
        duration_weeks: int,
    ) -> str:
        """Build study plan generation prompt."""
        objectives_str = "\n".join(f"- {obj}" for obj in learning_objectives)

        return f"""
        Create a comprehensive study plan for {subject} at grade level {grade_level}.

        Duration: {duration_weeks} weeks
        Learning Objectives:
        {objectives_str}

        Generate a structured study plan with the following format:
        {{
            "title": "Study plan title",
            "description": "Brief description",
            "phases": [
                {{
                    "title": "Phase title",
                    "description": "Phase description",
                    "weeks": number_of_weeks,
                    "topics": [
                        {{
                            "title": "Topic title",
                            "description": "Topic description",
                            "learning_objectives": ["objective1", "objective2"],
                            "estimated_hours": estimated_time_in_hours
                        }}
                    ]
                }}
            ]
        }}

        Ensure the plan is age-appropriate, engaging, and covers all learning objectives.
        Make it progressive with appropriate difficulty progression.
        Return only valid JSON.
        """

    def _build_enhancement_prompt(self, content: Content, enhancement_type: str) -> str:
        """Build content enhancement prompt."""
        base_prompt = f"""
        Enhance the following educational content for a student:

        Title: {content.title}
        Type: {content.content_type}
        Current Content: {content.content_data}

        Enhancement Type: {enhancement_type}

        Provide enhanced content that is:
        - Age-appropriate and engaging
        - Pedagogically sound
        - Clear and well-structured
        - Interactive where appropriate

        Return the enhanced content in this format:
        {{
            "enhanced_content": "enhanced content here",
            "enhancement_notes": "brief explanation of changes made"
        }}
        """

        if enhancement_type == "explanation":
            base_prompt += (
                "\nFocus on making the explanation clearer and more detailed."
            )
        elif enhancement_type == "examples":
            base_prompt += (
                "\nAdd relevant, practical examples that illustrate the concepts."
            )
        elif enhancement_type == "simplification":
            base_prompt += (
                "\nSimplify the language and concepts while maintaining accuracy."
            )

        return base_prompt

    def _build_exercise_prompt(
        self, topic: str, difficulty: str, exercise_type: str
    ) -> str:
        """Build exercise generation prompt."""
        return f"""
        Create a {difficulty} {exercise_type} exercise for the topic: {topic}

        Generate appropriate content that:
        - Tests understanding of key concepts
        - Is appropriate for the difficulty level
        - Has clear instructions
        - Includes correct answers/explanations

        Return in this format:
        {{
            "topic": "{topic}",
            "question": "Exercise question/prompt",
            "type": "{exercise_type}",
            "difficulty": "{difficulty}",
            "options": ["option1", "option2", "option3", "option4"],  // for multiple_choice
            "correct_answer": "correct answer",
            "explanation": "Explanation of the correct answer"
        }}
        """

    def _build_tutoring_prompt(
        self,
        question: str,
        context: Optional[str],
        grade_level: Optional[str],
        study_plan_context: Optional[Dict[str, Any]] = None,
        content_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build tutoring assistance prompt."""
        prompt = f"""
        You are a helpful educational tutor. Answer the student's question clearly and encouragingly.

        Student Question: {question}
        """

        if context:
            prompt += f"\nContext: {context}"

        if grade_level:
            prompt += f"\nStudent Grade Level: {grade_level}"

        prompt += """

        Provide a response that:
        - Answers the question clearly and accurately
        - Uses age-appropriate language
        - Encourages further learning
        - Suggests related topics to explore

        Return in this format:
        {{
            "answer": "Clear answer to the question",
            "explanation": "Detailed explanation",
            "related_topics": ["topic1", "topic2"],
            "encouragement": "Encouraging message for the student"
        }}
        """

        return prompt

    def _build_progress_assessment_prompt(
        self, user: User, learning_session: LearningSession
    ) -> str:
        """Build progress assessment prompt."""
        return f"""
        Analyze this student's learning session and provide progress assessment:

        Student: {user.get('full_name') if isinstance(user, dict) else user.full_name} \
(Grade {user.get('grade_level') if isinstance(user, dict) else user.grade_level})
        Session Duration: {learning_session.duration_minutes} minutes
        Completion Status: {learning_session.completion_status}
        Score: {learning_session.score or 'N/A'}

        Provide assessment in this format:
        {{
            "progress_summary": "Brief summary of progress",
            "strengths": ["strength1", "strength2"],
            "areas_for_improvement": ["area1", "area2"],
            "recommendations": ["recommendation1", "recommendation2"],
            "next_steps": "Suggested next learning activities"
        }}
        """

    def _parse_study_plan_response(self, response: str) -> Dict[str, Any]:
        """Parse AI study plan response."""
        try:
            # Try to extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("No valid JSON found in response")

        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Failed to parse study plan response: {e}")
            # Return a fallback study plan instead of raising an exception
            return {
                "title": "Generated Study Plan",
                "description": "AI-generated study plan",
                "duration_weeks": 4,
                "phases": [
                    {
                        "title": "Phase 1: Introduction",
                        "description": "Basic concepts and fundamentals",
                        "duration_weeks": 1,
                        "topics": [
                            {
                                "title": "Topic 1",
                                "description": "Introduction to key concepts",
                            },
                            {"title": "Topic 2", "description": "Basic principles"},
                        ],
                    },
                    {
                        "title": "Phase 2: Advanced Topics",
                        "description": "More complex concepts and applications",
                        "duration_weeks": 2,
                        "topics": [
                            {"title": "Topic 3", "description": "Advanced concepts"},
                            {
                                "title": "Topic 4",
                                "description": "Practical applications",
                            },
                        ],
                    },
                ],
                "learning_objectives": [
                    "Understand basic concepts",
                    "Apply knowledge practically",
                ],
                "assessment_methods": ["Quizzes", "Practical exercises"],
                "resources": ["Textbook", "Online materials"],
            }

    def _parse_enhancement_response(self, response: str) -> Dict[str, Any]:
        """Parse AI enhancement response."""
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return {"enhanced_content": response.strip()}

        except json.JSONDecodeError:
            return {"enhanced_content": response.strip()}

    def _parse_exercise_response(self, response: str, topic: str) -> Dict[str, Any]:
        """Parse AI exercise response."""
        try:
            # Look for JSON object in the response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]

                # Handle common JSON issues from AI responses
                # Fix unescaped backslashes in LaTeX expressions
                json_str = json_str.replace("\\", "\\\\")

                # Try to parse the JSON
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    # If parsing fails, try to fix common issues
                    self.logger.warning(
                        f"Initial JSON parsing failed: {e}. Attempting fixes..."
                    )

                    # Try to fix truncated responses by adding missing closing braces/brackets
                    open_braces = json_str.count("{")
                    close_braces = json_str.count("}")
                    if open_braces > close_braces:
                        json_str += "}" * (open_braces - close_braces)

                    open_brackets = json_str.count("[")
                    close_brackets = json_str.count("]")
                    if open_brackets > close_brackets:
                        json_str += "]" * (open_brackets - close_brackets)

                    # Try parsing again
                    return json.loads(json_str)
            else:
                raise ValueError("No valid JSON found in response")

        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Failed to parse exercise response: {e}")
            # Return a fallback response instead of raising an error
            return {
                "topic": topic,  # Include the topic in fallback response
                "question": "Error generating exercise",
                "type": "multiple_choice",
                "difficulty": "medium",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "Option A",
                "explanation": "There was an error generating this exercise. Please try again.",
            }

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation: 4 chars = 1 token)."""
        return len(text) // 4

    def _parse_tutoring_response(self, response: str) -> Dict[str, Any]:
        """Parse AI tutoring response."""
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return {
                    "answer": response.strip(),
                    "explanation": "",
                    "related_topics": [],
                    "encouragement": "Keep up the great work!",
                }

        except json.JSONDecodeError:
            return {
                "answer": response.strip(),
                "explanation": "",
                "related_topics": [],
                "encouragement": "Keep up the great work!",
            }

    def _parse_progress_assessment_response(self, response: str) -> Dict[str, Any]:
        """Parse AI progress assessment response."""
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return {
                    "progress_summary": "Good progress made",
                    "strengths": ["Consistent effort"],
                    "areas_for_improvement": ["Continue practicing"],
                    "recommendations": ["Keep studying regularly"],
                    "next_steps": "Continue with current learning path",
                }

        except json.JSONDecodeError:
            return {
                "progress_summary": "Good progress made",
                "strengths": ["Consistent effort"],
                "areas_for_improvement": ["Continue practicing"],
                "recommendations": ["Keep studying regularly"],
                "next_steps": "Continue with current learning path",
            }

    def close(self):
        """Close HTTP client."""
        if self._client:
            self._client.close()

    def __enter__(self):
        """Enter context manager, return self."""
        return self

    def __exit__(self, exc_type, exc, tb):
        """Exit context manager: close client and swallow nothing."""
        try:
            self.close()
        except Exception:
            # Do not raise from cleanup
            pass

    def __del__(self):
        """Ensure HTTP client is closed when garbage collected."""
        try:
            self.close()
        except Exception:
            # Avoid raising during GC
            pass

    def generate_assessment(
        self,
        topic: str,
        difficulty: str,
        question_types: List[str],
        num_questions: int = 10,
        learning_objectives: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive assessment with AI.

        Args:
            topic: Topic for the assessment
            difficulty: Difficulty level (easy, medium, hard)
            question_types: List of question types to include
            num_questions: Number of questions to generate
            learning_objectives: Optional learning objectives to focus on

        Returns:
            Dict containing assessment data with questions and rubrics

        Raises:
            AIServiceError: If generation fails
        """
        try:
            prompt = self._build_assessment_prompt(
                topic, difficulty, question_types, num_questions, learning_objectives
            )

            ai_request = AIRequest(
                prompt=prompt,
                model=self.model,
                max_tokens=4000,  # Larger for comprehensive assessments
                temperature=0.3,  # Lower for more consistent output
                provider=self.provider,
                system_prompt=(
                    "You are an expert educational assessment creator. "
                    "Generate high-quality, pedagogically sound assessments."
                ),
            )

            response = self._make_request(ai_request)
            return self._parse_assessment_response(response.content)

        except Exception as e:
            logging.error(f"Assessment generation failed: {e}")
            raise AIServiceError(f"Failed to generate assessment: {str(e)}")

    def grade_answer(
        self,
        question: str,
        answer: str,
        question_type: str,
        correct_answer: Optional[str] = None,
        rubric: Optional[Dict[str, Any]] = None,
        max_points: int = 10,
    ) -> Dict[str, Any]:
        """
        Grade a student's answer using AI.

        Args:
            question: The question text
            answer: The student's answer
            question_type: Type of question (multiple_choice, short_answer, etc.)
            correct_answer: Expected correct answer (for objective questions)
            rubric: Grading rubric for subjective questions
            max_points: Maximum points for this question

        Returns:
            Dict containing grade, feedback, and explanation

        Raises:
            AIServiceError: If grading fails
        """
        try:
            prompt = self._build_grading_prompt(
                question, answer, question_type, correct_answer, rubric, max_points
            )

            ai_request = AIRequest(
                prompt=prompt,
                model=self.model,
                max_tokens=1000,
                temperature=0.2,  # Very low for consistent grading
                provider=self.provider,
                system_prompt="You are an expert educational grader. Provide fair, detailed, and constructive feedback.",
            )

            response = self._make_request(ai_request)
            return self._parse_grading_response(response.content, max_points)

        except Exception as e:
            logging.error(f"Answer grading failed: {e}")
            raise AIServiceError(f"Failed to grade answer: {str(e)}")

    def _build_assessment_prompt(
        self,
        topic: str,
        difficulty: str,
        question_types: List[str],
        num_questions: int,
        learning_objectives: Optional[List[str]],
    ) -> str:
        """Build assessment generation prompt."""
        objectives_str = (
            "\n".join(f"- {obj}" for obj in learning_objectives)
            if learning_objectives
            else "General understanding"
        )
        types_str = ", ".join(question_types)

        return f"""
        Create a comprehensive {difficulty} assessment on the topic: {topic}

        Requirements:
        - Generate {num_questions} questions total
        - Include these question types: {types_str}
        - Focus on these learning objectives:
        {objectives_str}

        For each question, provide:
        1. Question text
        2. Question type
        3. Point value (total should sum to 100)
        4. Correct answer with detailed explanation
        5. For multiple choice: 4-5 options with one correct
        6. For subjective questions: grading rubric and expected key points
        7. Difficulty level and estimated time
        8. Hints or scaffolding for struggling students

        Return as JSON with this structure:
        {{
            "title": "Assessment Title",
            "description": "Brief description",
            "instructions": "Student instructions",
            "time_limit_minutes": 60,
            "total_points": 100,
            "passing_score": 70,
            "questions": [
                {{
                    "question_text": "Question text",
                    "question_type": "multiple_choice",
                    "points": 10,
                    "difficulty": "medium",
                    "estimated_time_minutes": 2,
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "B",
                    "explanation": "Why this is correct",
                    "hints": ["Think about...", "Consider..."],
                    "rubric": {{...}}  // For subjective questions
                }}
            ]
        }}
        """

    def _build_grading_prompt(
        self,
        question: str,
        answer: str,
        question_type: str,
        correct_answer: Optional[str],
        rubric: Optional[Dict[str, Any]],
        max_points: int,
    ) -> str:
        """Build grading prompt."""
        rubric_str = json.dumps(rubric, indent=2) if rubric else "No rubric provided"
        correct_str = (
            correct_answer if correct_answer else "Subjective evaluation required"
        )

        return f"""
        Grade this student's answer to the following question:

        Question: {question}
        Question Type: {question_type}
        Student's Answer: {answer}
        Correct Answer: {correct_str}
        Maximum Points: {max_points}
        Rubric: {rubric_str}

        Provide detailed grading with:
        1. Points earned (0-{max_points})
        2. Percentage score
        3. Whether answer is correct (true/false for objective questions)
        4. Detailed feedback explaining the grade
        5. Suggestions for improvement
        6. Identify any misconceptions
        7. Praise for good aspects of the answer

        For objective questions (multiple choice, true/false):
        - Full points for correct answer
        - Zero points for incorrect answer
        - Brief explanation of correct answer

        For subjective questions (short answer, essay):
        - Use rubric to assign partial credit
        - Consider completeness, accuracy, clarity, depth
        - Provide constructive feedback for improvement

        Return as JSON:
        {{
            "points_earned": 8,
            "percentage": 80,
            "is_correct": true,
            "feedback": "Good answer that shows understanding...",
            "explanation": "The correct answer is... because...",
            "improvements": ["Consider adding...", "Expand on..."],
            "misconceptions": [],
            "strengths": ["Clear explanation", "Good examples"]
        }}
        """

    def _parse_assessment_response(self, response: str) -> Dict[str, Any]:
        """Parse AI assessment response."""
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                assessment_data = json.loads(json_str)

                # Validate required fields
                required_fields = ["title", "questions", "total_points"]
                for field in required_fields:
                    if field not in assessment_data:
                        assessment_data[field] = self._get_default_assessment_field(
                            field
                        )

                # Ensure questions array exists and is valid
                if not isinstance(assessment_data.get("questions"), list):
                    assessment_data["questions"] = []

                return assessment_data
            else:
                return self._get_default_assessment()

        except json.JSONDecodeError:
            return self._get_default_assessment()

    def _parse_grading_response(self, response: str, max_points: int) -> Dict[str, Any]:
        """Parse AI grading response."""
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                grade_data = json.loads(json_str)

                # Validate and normalize fields
                grade_data["points_earned"] = min(
                    max(int(grade_data.get("points_earned", 0)), 0), max_points
                )
                grade_data["percentage"] = min(
                    max(int(grade_data.get("percentage", 0)), 0), 100
                )
                grade_data["feedback"] = grade_data.get(
                    "feedback", "No feedback provided"
                )
                grade_data["explanation"] = grade_data.get("explanation", "")
                grade_data["improvements"] = grade_data.get("improvements", [])
                grade_data["misconceptions"] = grade_data.get("misconceptions", [])
                grade_data["strengths"] = grade_data.get("strengths", [])

                return grade_data
            else:
                return self._get_default_grade(max_points)

        except (json.JSONDecodeError, ValueError, TypeError):
            return self._get_default_grade(max_points)

    def _get_default_assessment(self) -> Dict[str, Any]:
        """Get default assessment data when parsing fails."""
        return {
            "title": "Generated Assessment",
            "description": "AI-generated assessment",
            "instructions": "Answer all questions to the best of your ability.",
            "time_limit_minutes": 60,
            "total_points": 100,
            "passing_score": 70,
            "questions": [],
        }

    def _get_default_assessment_field(self, field: str) -> Any:
        """Get default value for assessment field."""
        defaults = {
            "title": "Generated Assessment",
            "description": "AI-generated assessment",
            "instructions": "Answer all questions to the best of your ability.",
            "time_limit_minutes": 60,
            "total_points": 100,
            "passing_score": 70,
            "questions": [],
        }
        return defaults.get(field, "")

    def _get_default_grade(self, max_points: int) -> Dict[str, Any]:
        """Get default grade data when parsing fails."""
        return {
            "points_earned": 0,
            "percentage": 0,
            "is_correct": False,
            "feedback": "Unable to process answer automatically. Please contact your teacher for manual grading.",
            "explanation": "",
            "improvements": [],
            "misconceptions": [],
            "strengths": [],
        }

    def fetch_available_models(
        self, provider: Optional[AIProvider] = None, base_url: Optional[str] = None
    ) -> List[str]:
        """
        Fetch available models from AI providers.

        Args:
            provider: Specific provider to fetch models from. If None, uses current config provider.
            base_url: Custom base URL for the provider. If None, uses configured URL.

        Returns:
            List of available model names

        Raises:
            AIServiceError: If model fetching fails
        """
        target_provider = provider or AIProvider(self.config.provider)

        try:
            if target_provider == AIProvider.OLLAMA:
                return self._fetch_ollama_models(base_url)
            elif target_provider == AIProvider.LM_STUDIO:
                return self._fetch_lm_studio_models(base_url)
            elif target_provider == AIProvider.OPENAI:
                return self._fetch_openai_models(base_url)
            elif target_provider == AIProvider.ANTHROPIC:
                return self._fetch_anthropic_models(base_url)
            elif target_provider == AIProvider.OPENROUTER:
                return self._fetch_openrouter_models(base_url)
            else:
                raise ConfigurationError(f"Unsupported AI provider: {target_provider}")

        except Exception as e:
            self.logger.error(f"Failed to fetch models for {target_provider}: {e}")
            raise AIServiceError(f"Model fetching failed for {target_provider}: {e}")

    def _fetch_ollama_models(self, base_url: Optional[str] = None) -> List[str]:
        """Fetch available models from Ollama."""
        ollama_url = base_url or self.settings_service.get(
            "ai", "ollama.url", "http://localhost:11434"
        )

        try:
            response = self._client.get(f"{ollama_url}/api/tags", timeout=10.0)
            response.raise_for_status()

            data = response.json()
            models = [model.get("name", "") for model in data.get("models", [])]

            self.logger.info(f"Fetched {len(models)} models from Ollama")
            return sorted(models)

        except Exception as e:
            self.logger.error(f"Failed to fetch Ollama models: {e}")
            raise AIServiceError(f"Ollama model fetching failed: {e}")

    def _fetch_lm_studio_models(self, base_url: Optional[str] = None) -> List[str]:
        """Fetch available models from LM Studio."""
        lm_studio_url = base_url or self.settings_service.get(
            "ai", "lm_studio.url", "http://localhost:1234"
        )

        # Normalize the URL - remove trailing /v1 if present to avoid duplication
        lm_studio_url = lm_studio_url.rstrip("/")
        if lm_studio_url.endswith("/v1"):
            lm_studio_url = lm_studio_url[:-3]

        try:
            response = self._client.get(f"{lm_studio_url}/v1/models", timeout=10.0)
            response.raise_for_status()

            data = response.json()
            models = [model.get("id", "") for model in data.get("data", [])]

            self.logger.info(f"Fetched {len(models)} models from LM Studio")
            return sorted(models)

        except Exception as e:
            self.logger.error(f"Failed to fetch LM Studio models: {e}")
            raise AIServiceError(f"LM Studio model fetching failed: {e}")

    def _fetch_openai_models(self, base_url: Optional[str] = None) -> List[str]:
        """Fetch available models from OpenAI."""
        if not self.config.api_key:
            raise AIServiceError("OpenAI API key is required to fetch models")

        openai_endpoint = base_url or self.settings_service.get(
            "ai", "openai.url", "https://api.openai.com"
        )

        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            }

            response = self._client.get(
                f"{openai_endpoint}/v1/models", headers=headers, timeout=10.0
            )
            response.raise_for_status()

            data = response.json()
            models = [model.get("id", "") for model in data.get("data", [])]

            # Filter for GPT models commonly used for chat/completion
            gpt_models = [
                model
                for model in models
                if any(prefix in model for prefix in ["gpt-", "text-"])
            ]

            self.logger.info(f"Fetched {len(gpt_models)} models from OpenAI")
            return sorted(gpt_models)

        except Exception as e:
            self.logger.error(f"Failed to fetch OpenAI models: {e}")
            raise AIServiceError(f"OpenAI model fetching failed: {e}")

    def _fetch_anthropic_models(self, base_url: Optional[str] = None) -> List[str]:
        """Fetch available models from Anthropic."""
        if not self.config.api_key:
            raise AIServiceError("Anthropic API key is required to fetch models")

        # Anthropic doesn't have a public models endpoint, so we cannot fetch real models
        # This is a limitation of the Anthropic API
        raise AIServiceError(
            "Anthropic does not provide a models endpoint. Please manually enter the model name."
        )

    def _fetch_openrouter_models(self, base_url: Optional[str] = None) -> List[str]:
        """Fetch available models from OpenRouter."""
        if not self.config.api_key:
            raise AIServiceError("OpenRouter API key is required to fetch models")

        # Use base URL for models endpoint, not the full chat completions URL
        openrouter_endpoint = base_url or self.settings_service.get(
            "ai", "openrouter.url", "https://openrouter.ai/api/v1"
        )

        # If the URL ends with /chat/completions, remove it to get the base API URL
        if openrouter_endpoint.endswith("/chat/completions"):
            openrouter_endpoint = openrouter_endpoint[
                :-17
            ]  # Remove '/chat/completions'
        elif openrouter_endpoint.endswith("/v1"):
            # Already a base URL, use as-is
            pass
        else:
            # Ensure we have the base API endpoint
            openrouter_endpoint = openrouter_endpoint.rstrip("/")

        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/slm-educator/slm-educator",
                "X-Title": "SLMEducator",
            }

            response = self._client.get(
                f"{openrouter_endpoint}/models", headers=headers, timeout=10.0
            )
            response.raise_for_status()

            data = response.json()
            models = [model.get("id", "") for model in data.get("data", [])]

            self.logger.info(f"Fetched {len(models)} models from OpenRouter")
            return sorted(models)

        except Exception as e:
            self.logger.error(f"Failed to fetch OpenRouter models: {e}")
            raise AIServiceError(f"OpenRouter model fetching failed: {e}")


# Global AI service instance
_ai_service: Optional[AIService] = None


def init_ai_service(config: Optional[AIModelConfig] = None) -> AIService:
    """Initialize the global AI service instance."""
    global _ai_service
    from .logging import get_logger

    logger = get_logger("ai_service")
    if config is None:
        config = get_ai_service().config
    _ai_service = AIService(config, logger)
    return _ai_service


def reset_ai_service() -> None:
    """Reset the global AI service instance to force re-initialization with fresh config."""
    global _ai_service
    _ai_service = None


def build_grade_request(
    question: str,
    answer: str,
    question_type: str,
    correct_answer: str,
    max_points: int,
    **kwargs,
) -> dict:
    """
    Build a standardized grading request for AI service.

    This function eliminates duplication between UI and service layers
    by providing a consistent way to construct grading requests.

    Args:
        question: The question text
        answer: The student's answer
        question_type: Type of question (short_answer, multiple_choice, etc.)
        correct_answer: The correct answer
        max_points: Maximum points for this question
        **kwargs: Additional parameters

    Returns:
        dict: Standardized grading request parameters
    """
    return {
        "question": question,
        "answer": answer,
        "question_type": question_type,
        "correct_answer": correct_answer,
        "max_points": max_points,
        **kwargs,
    }


def normalize_grade_result(result: dict) -> dict:
    """
    Normalize AI grading result to ensure required fields are present.

    This function eliminates inconsistencies in AI grading responses
    by ensuring all required fields are present with appropriate defaults.

    Args:
        result: Raw AI grading result

    Returns:
        dict: Normalized result with guaranteed fields
    """
    # Ensure required fields are present with defaults
    normalized = {
        "points_earned": result.get("points_earned", 0),
        "max_points": result.get("max_points", 10),
        "percentage": result.get("percentage", 0),
        "feedback": result.get("feedback", "Answer evaluated."),
        "explanation": result.get("explanation", "No explanation provided."),
        "improvements": result.get("improvements", []),
        "misconceptions": result.get("misconceptions", []),
        "strengths": result.get("strengths", []),
    }

    # Calculate percentage if not provided
    if normalized["percentage"] == 0 and normalized["max_points"] > 0:
        normalized["percentage"] = int(
            (normalized["points_earned"] / normalized["max_points"]) * 100
        )

    return normalized


def format_grading_feedback(
    points_earned: int,
    max_points: int,
    percentage: Optional[int] = None,
    feedback: Optional[str] = None,
) -> str:
    """
    Format grading feedback consistently across the application.

    This eliminates duplicate feedback formatting logic across
    different parts of the codebase.

    Args:
        points_earned: Points the student earned
        max_points: Maximum possible points
        percentage: Percentage score (calculated if not provided)
        feedback: Base feedback text

    Returns:
        str: Formatted feedback string
    """
    if percentage is None:
        percentage = int((points_earned / max_points) * 100) if max_points > 0 else 0

    score_part = f"Score: {points_earned}/{max_points} ({percentage}%)"

    if feedback:
        return f"{feedback} {score_part}"
    else:
        return f"Answer evaluated. {score_part}"


def get_ai_service() -> AIService:
    """Get the global AI service instance."""
    global _ai_service
    if _ai_service is None:
        # Initialize with default config if not already initialized
        from ..models import AIModelConfig
        from .logging import get_logger

        # Get default AI configuration from settings
        settings_service = get_settings_service()

        # Get provider and model from settings (try both key variations)
        provider = settings_service.get(
            "ai", "default_provider", None
        ) or settings_service.get("ai", "provider", "ollama")
        model = settings_service.get(
            "ai", "default_model", None
        ) or settings_service.get("ai", "model", "llama2")

        # Get API key based on provider
        if provider == "openrouter":
            api_key = settings_service.get("ai", "openrouter.api_key", "")
            endpoint = settings_service.get(
                "ai", "openrouter.url", "https://openrouter.ai/api/v1/chat/completions"
            )
        elif provider == "openai":
            api_key = settings_service.get("ai", "openai.api_key", "")
            endpoint = settings_service.get(
                "ai", "openai.endpoint", "https://api.openai.com/v1/chat/completions"
            )
        elif provider == "ollama":
            api_key = ""
            endpoint = settings_service.get(
                "ai", "ollama.url", "http://localhost:11434"
            )
        elif provider == "lm_studio":
            api_key = ""
            endpoint = settings_service.get(
                "ai", "lm_studio.url", "http://localhost:1234"
            )
        else:
            api_key = settings_service.get("ai", "api_key", "")
            endpoint = settings_service.get("ai", "endpoint", "http://localhost:11434")

        config = AIModelConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            endpoint=endpoint,
            model_parameters={
                "max_tokens": int(
                    settings_service.get("ai", "default_max_tokens", "1000")
                ),
                "temperature": float(
                    settings_service.get("ai", "default_temperature", "0.7")
                ),
            },
        )

        logger = get_logger("ai_service")
        logger.info(
            f"Initializing AI service: provider={provider}, model={model}, endpoint={endpoint}"
        )
        _ai_service = AIService(config, logger)
    return _ai_service
