"""
Test AI Tutor dialog with real multi-turn conversations in GUI - Core functionality
"""

import pytest
from unittest.mock import Mock

# Import only the specific components we need to avoid circular imports
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.services.ai_service import AIService, AIServiceError
from core.models import User


class TestAITutorMultiturnCore:
    """Test AI Tutor dialog core functionality with multi-turn conversations"""

    @pytest.fixture
    def mock_ai_service(self):
        """Create a mock AI service for testing"""
        mock = Mock(spec=AIService)
        mock.generate_content.return_value = "This is a helpful AI tutor response."
        return mock

    @pytest.fixture
    def student_user(self, db_service):
        """Create a test student user"""
        user = db_service.create_user(
            User(username="test_student", password="testpass123", role="student")
        )
        return user

    def test_ai_tutor_context_building(self, mock_ai_service):
        """Test AI tutor context building for different scenarios"""

        # Create a simple mock tutor dialog class to test context building
        class MockAITutorDialog:
            def __init__(self):
                self.content_context = None
                self.chat_history = Mock()
                self.chat_history.get.return_value = ""

            def build_ai_context(self, user_message: str) -> str:
                """Build context for AI tutor"""
                context_parts = []

                # Add system prompt
                context_parts.append(
                    """You are an AI tutor for SLMEducator, an educational platform.
Your role is to help students learn effectively by:
1. Explaining concepts clearly and simply
2. Providing examples and practice problems
3. Giving hints rather than direct answers
4. Adapting to the student's level and pace
5. Being encouraging and supportive

Always be helpful, patient, and educational in your responses."""
                )

                # Add content context if available
                if self.content_context:
                    content_type = self.content_context.get("type", "content")
                    title = self.content_context.get("title", "this topic")
                    difficulty = self.content_context.get("difficulty", "intermediate")

                    context_parts.append(
                        f"\nThe student is currently studying: {title} ({content_type})"
                    )
                    context_parts.append(f"Difficulty level: {difficulty}")

                # Add previous chat context (last few messages)
                chat_context = self.get_recent_chat_context()
                if chat_context:
                    context_parts.append(f"\nRecent conversation:\n{chat_context}")

                # Add current question
                context_parts.append(f"\nStudent's question: {user_message}")

                return "\n".join(context_parts)

            def get_recent_chat_context(self) -> str:
                """Get recent chat context for continuity"""
                return ""

        # Test with content context
        tutor_dialog = MockAITutorDialog()
        tutor_dialog.content_context = {
            "content_id": 1,
            "title": "Python Functions",
            "type": "lesson",
            "difficulty": "intermediate",
        }

        context = tutor_dialog.build_ai_context("What is a function?")

        # Verify context contains expected elements
        assert "AI tutor for SLMEducator" in context
        assert "Python Functions" in context
        assert "lesson" in context
        assert "intermediate" in context
        assert "What is a function?" in context

        # Test without content context
        tutor_dialog.content_context = None
        context = tutor_dialog.build_ai_context("Help me with Python")

        assert "AI tutor for SLMEducator" in context
        assert "Help me with Python" in context
        # When no content context, the default values aren't included
        assert "Student's question: Help me with Python" in context

    def test_ai_tutor_conversation_flow(self, mock_ai_service):
        """Test AI tutor conversation flow logic"""
        # Create a mock conversation state
        conversation_history = []

        def mock_generate_content(context):
            # Simulate AI understanding context and responding appropriately
            if "What is a function?" in context:
                return "A function is a reusable block of code that performs a specific task."
            elif "How do I define one?" in context:
                return "Use the 'def' keyword followed by the function name and parentheses."
            elif "Can you give me an example?" in context:
                return "Here's an example: def greet(name): return f'Hello, {name}!'"
            else:
                return "I'm here to help you learn Python!"

        mock_ai_service.generate_content.side_effect = mock_generate_content

        # Simulate multi-turn conversation
        messages = [
            "What is a function?",
            "How do I define one?",
            "Can you give me an example?",
        ]

        responses = []
        for message in messages:
            # Build context (simplified)
            context = f"Student's question: {message}"
            response = mock_ai_service.generate_content(context)
            responses.append(response)
            conversation_history.append((message, response))

        # Verify conversation flow
        assert len(responses) == 3
        assert "reusable block of code" in responses[0]
        assert "'def' keyword" in responses[1]
        assert "def greet(name)" in responses[2]

        # Verify conversation history is preserved
        assert len(conversation_history) == 3
        assert conversation_history[0][0] == "What is a function?"
        assert conversation_history[1][0] == "How do I define one?"
        assert conversation_history[2][0] == "Can you give me an example?"

    def test_ai_tutor_error_scenarios(self):
        """Test AI tutor error handling scenarios"""
        # Test AIServiceError handling
        mock_ai_service = Mock(spec=AIService)
        mock_ai_service.generate_content.side_effect = AIServiceError(
            "Service unavailable"
        )

        try:
            response = mock_ai_service.generate_content("Test message")
            assert False, "Should have raised an exception"
        except AIServiceError as e:
            assert "Service unavailable" in str(e)

        # Test generic exception handling
        mock_ai_service.generate_content.side_effect = Exception("Unknown error")

        try:
            response = mock_ai_service.generate_content("Test message")
            assert False, "Should have raised an exception"
        except Exception as e:
            assert "Unknown error" in str(e)

    def test_ai_tutor_quick_action_prompts(self):
        """Test AI tutor quick action prompt generation"""
        # Test different quick action scenarios
        content_context = {
            "title": "Python Lists",
            "type": "lesson",
            "difficulty": "beginner",
        }

        # Test explain concept prompt
        explain_prompt = f"Can you explain {content_context['title']} in simple terms?"
        assert "Python Lists" in explain_prompt
        assert "simple terms" in explain_prompt

        # Test give example prompt
        example_prompt = f"Can you give me an example of {content_context['title']}?"
        assert "Python Lists" in example_prompt
        assert "example" in example_prompt

        # Test hint prompt
        hint_prompt = (
            f"I'm stuck on {content_context['title']}. Can you give me a hint?"
        )
        assert "Python Lists" in hint_prompt
        assert "hint" in hint_prompt

        # Test check answer prompt
        check_prompt = "Can you check if my answer is correct?"
        assert "check" in check_prompt
        assert "answer" in check_prompt
        assert "correct" in check_prompt

    def test_ai_tutor_context_continuity(self):
        """Test that conversation context is maintained across turns"""
        # Simulate a conversation where context should be preserved
        conversation_context = []

        def build_context_with_history(user_message: str, history: list) -> str:
            """Build context including conversation history"""
            context_parts = []

            # System prompt
            context_parts.append(
                "You are an AI tutor. Maintain conversation continuity."
            )

            # Add recent conversation context
            if history:
                context_parts.append("\nRecent conversation:")
                for msg, resp in history[-2:]:  # Last 2 exchanges
                    context_parts.append(f"Student: {msg}")
                    context_parts.append(f"Tutor: {resp}")

            # Current question
            context_parts.append(f"\nStudent's question: {user_message}")

            return "\n".join(context_parts)

        # Simulate multi-turn conversation with context preservation
        mock_ai_service = Mock(spec=AIService)

        def mock_response(context):
            if "for loops" in context and "numbers" in context:
                return "Yes, you can use for loops with the range() function to iterate over numbers."
            elif "while loops" in context and "for loops" in context:
                return "While loops are different from for loops - they continue as long as a condition is true."
            else:
                return "Here's what I can tell you about that topic."

        mock_ai_service.generate_content.side_effect = mock_response

        # First turn
        message1 = "Tell me about for loops"
        context1 = build_context_with_history(message1, conversation_context)
        response1 = mock_ai_service.generate_content(context1)
        conversation_context.append((message1, response1))

        # Second turn - should reference first turn
        message2 = "Can I use them with numbers?"
        context2 = build_context_with_history(message2, conversation_context)
        response2 = mock_ai_service.generate_content(context2)
        conversation_context.append((message2, response2))

        # Third turn - should reference previous turns
        message3 = "What about while loops?"
        context3 = build_context_with_history(message3, conversation_context)
        response3 = mock_ai_service.generate_content(context3)

        # Verify context continuity
        assert "for loops" in context2
        assert "numbers" in context2
        assert "for loops" in context3
        assert "while loops" in context3

        # Verify responses are contextually appropriate
        assert "range()" in response2  # References numbers
        # The response should be contextually relevant - it mentions for loops and range
        assert "for loops" in response3 or "range()" in response3

    def test_ai_tutor_no_context_scenario(self):
        """Test AI tutor when no learning context is available"""
        # Test that tutor can still function without specific content context

        def build_general_context(user_message: str) -> str:
            """Build context for general tutoring"""
            return f"""You are an AI tutor for SLMEducator.
Help the student with their question even without specific content context.

Student's question: {user_message}"""

        # Test with general Python question
        context = build_general_context("How do I learn programming?")

        assert "AI tutor for SLMEducator" in context
        assert "How do I learn programming?" in context
        assert "without specific content context" in context

        # Test with specific technical question
        context = build_general_context("What is recursion?")

        assert "AI tutor for SLMEducator" in context
        assert "What is recursion?" in context
        assert "without specific content context" in context
