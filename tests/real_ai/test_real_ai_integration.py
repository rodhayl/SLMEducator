"""
REAL AI Integration Test Suite - BASIC VERSION
================================================

This test suite makes ACTUAL API calls to real AI/LLM services.
Simplified to work without Phase 1-3 models.

⚠️  WARNING:
- These tests are SLOW (network latency)
- These tests COST MONEY (token usage)
- These tests require VALID API credentials
- NO MOCKS are allowed
"""

import pytest


class TestRealAIIntegration:
    """
    Real AI Integration Tests - Basic Version

    NO MOCKS - All tests use actual AI/LLM services
    """

    def test_real_ai_service_initialization(self, real_ai_service, real_ai_config):
        """Test that real AI service initializes correctly"""
        # Verify it's a real service, not a mock
        assert real_ai_service is not None
        assert not hasattr(real_ai_service, "_mock_name"), "Service must not be a mock!"
        assert not hasattr(
            real_ai_service, "return_value"
        ), "Service must not be a mock!"

        # Verify configuration
        assert real_ai_service.config.provider == real_ai_config["provider"]
        assert real_ai_service.config.model == real_ai_config["model"]

        print(
            f"✅ Real AI Service initialized: {real_ai_config['provider']}/{real_ai_config['model']}"
        )

    def test_real_ai_simple_generation(self, real_ai_service):
        """
        Test real AI content generation

        This makes an ACTUAL API call to the configured LLM.
        """
        prompt = "What is 2+2? Answer with just the number."

        print(f"\n📤 Sending to real AI: {prompt}")

        # ACTUAL API CALL - This costs tokens!
        response = real_ai_service.generate_content(prompt)

        print(f"📥 Real AI response: {response[:100]}...")

        # Verify response
        assert response is not None
        assert len(response) > 0
        assert isinstance(response, str)

        # Should contain "4" somewhere in response
        assert "4" in response, f"Expected '4' in response, got: {response}"

        print("✅ Real AI generation successful")

    def test_real_ai_tutoring_basic(self, real_ai_service, test_user):
        """
        Test real AI tutoring with actual LLM

        Makes ACTUAL API call - costs tokens!
        """
        question = "Explain what a variable is in programming in one sentence."

        print(f"\n📤 Tutoring question: {question}")

        # ACTUAL API CALL
        result = real_ai_service.provide_tutoring(
            user=test_user,
            question=question,
            context=None,
            study_plan_context=None,
            content_context=None,
        )

        print(f"📥 Real AI tutoring response: {result.get('answer', '')[:150]}...")

        # Verify response structure
        assert isinstance(result, dict)
        assert "answer" in result
        assert isinstance(result["answer"], str)
        assert len(result["answer"]) > 10

        # Should mention variables or related concepts
        answer_lower = result["answer"].lower()
        variable_terms = ["variable", "store", "value", "data", "hold"]
        assert any(
            term in answer_lower for term in variable_terms
        ), f"Response should mention variables or related concepts: {result['answer']}"

        print("✅ Real AI tutoring successful")

    def test_real_ai_grading(self, real_ai_service):
        """
        Test real AI answer grading

        Makes ACTUAL API call to grade an answer
        """
        question = "What is the capital of France?"
        student_answer = "Paris"
        question_type = "short_answer"

        print(f"\n📤 Grading with real AI:")
        print(f"   Question: {question}")
        print(f"   Answer: {student_answer}")

        # ACTUAL API CALL for grading
        result = real_ai_service.grade_answer(
            question=question,
            answer=student_answer,
            question_type=question_type,
            correct_answer="Paris",
        )

        print(f"📥 Grading result: {result}")

        # Verify grading result
        assert isinstance(result, dict)
        assert "points_earned" in result or "is_correct" in result

        # Should recognize correct answer
        if "is_correct" in result:
            assert (
                result["is_correct"] is True
            ), "Real AI should recognize correct answer"
        if "points_earned" in result and "max_points" in result:
            percentage = (result["points_earned"] / result["max_points"]) * 100
            assert (
                percentage >= 80
            ), f"Should get high score for correct answer: {percentage}%"

        print("✅ Real AI grading successful")

    def test_real_ai_multiple_calls_consistency(self, real_ai_service):
        """
        Test that real AI provides consistent responses

        Makes MULTIPLE ACTUAL API calls
        """
        prompt = "What is 5 multiplied by 3? Answer with just the number."

        print(f"\n📤 Testing consistency with {prompt}")

        responses = []
        for i in range(3):
            print(f"   Call {i + 1}/3...")
            response = real_ai_service.generate_content(prompt)
            responses.append(response)

        print(f"📥 Responses received: {len(responses)}")

        # All should contain "15"
        for response in responses:
            assert "15" in response, f"Expected '15' in response: {response}"

        print("✅ Real AI consistency verified")

    def test_real_ai_token_usage_tracking(self, real_ai_service):
        """
        Test that real AI tracks token usage

        Makes ACTUAL API call and verifies metrics
        """
        prompt = "Count from 1 to 5."

        print(f"\n📤 Testing token tracking: {prompt}")

        # ACTUAL API CALL
        response = real_ai_service._call_ai(prompt, max_tokens=100)

        print(f"📥 Response received")
        print(f"   Tokens used: {response.tokens_used}")
        print(f"   Response time: {response.response_time}s")
        print(f"   Model: {response.model}")

        # Verify metrics
        assert response.tokens_used > 0, "Should track token usage"
        assert response.response_time > 0, "Should track response time"
        assert response.model is not None, "Should track model used"

        print("✅ Real AI metrics tracked successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
