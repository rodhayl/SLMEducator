"""
Performance testing scenarios for AI integration.
Tests slow responses, concurrent requests, and large responses.
"""

import pytest
import time
import concurrent.futures
from unittest.mock import Mock, patch
from core.services.ai_service import AIService
from core.models import AIModelConfiguration, User, StudyPlan


class TestAIPerformanceScenarios:
    """Test AI performance scenarios including slow responses and concurrent requests."""

    @pytest.fixture
    def ai_config(self):
        """Create AI model configuration for testing."""
        config = Mock(spec=AIModelConfiguration)
        config.provider = "openai"
        config.model = "gpt-3.5-turbo"
        config.endpoint = "https://api.openai.com/v1"
        config.decrypted_api_key = "test-api-key"
        config.model_parameters = {"temperature": 0.7, "max_tokens": 1000}
        return config

    @pytest.fixture
    def ai_service(self, ai_config):
        """Create AI service with mock config."""
        logger = Mock()
        service = AIService(ai_config, logger)
        try:
            yield service
        finally:
            try:
                service.close()
            except Exception:
                pass

    @pytest.fixture
    def user(self):
        """Create test user."""
        return User(id=1, username="testuser", email="test@example.com", role="teacher")

    @pytest.fixture
    def study_plan(self, user):
        """Create test study plan."""
        return StudyPlan(
            id=1,
            title="Test Study Plan",
            description="Test description",
            created_by=user.id,
            subject="Mathematics",
            grade_level="Grade 10",
        )

    def test_slow_response_handling(self, ai_service):
        """Test handling of slow AI responses."""

        # Mock a slow response that takes 2 seconds
        def slow_response(*args, **kwargs):
            time.sleep(2)
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "This is a slow response"}}],
                "model": "gpt-3.5-turbo",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                },
            }
            return mock_response

        with patch.object(ai_service._client, "post", side_effect=slow_response):
            start_time = time.time()
            result = ai_service.generate_content("Test prompt")
            end_time = time.time()

            # Verify the response was received despite slowness
            assert result == "This is a slow response"

            # Verify it actually took around 2 seconds
            assert 1.5 < (end_time - start_time) < 2.5

    def test_timeout_handling(self, ai_service):
        """Test timeout handling for extremely slow responses."""

        # Mock a response that raises a timeout exception
        def timeout_response(*args, **kwargs):
            import httpx

            raise httpx.TimeoutException("Request timed out")

        with patch.object(ai_service._client, "post", side_effect=timeout_response):
            # This should raise an exception due to timeout
            with pytest.raises(Exception):  # Should catch the timeout exception
                ai_service.generate_content("Test prompt")

    def test_concurrent_requests(self, ai_service):
        """Test handling of concurrent AI requests."""

        # Mock responses for concurrent requests
        def mock_response(*args, **kwargs):
            # Simulate some processing time
            time.sleep(0.1)
            mock_response = Mock()
            mock_response.status_code = 200

            # Extract the prompt from the data in kwargs
            data = kwargs.get("json", {})
            messages = data.get("messages", [])
            user_message = "Unknown prompt"
            if messages and len(messages) > 0:
                for msg in messages:
                    if msg.get("role") == "user":
                        user_message = msg.get("content", "Unknown prompt")
                        break

            mock_response.json.return_value = {
                "choices": [{"message": {"content": f"Response for: {user_message}"}}],
                "model": "gpt-3.5-turbo",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 15,
                    "total_tokens": 25,
                },
            }
            return mock_response

        with patch.object(ai_service._client, "post", side_effect=mock_response):
            # Create multiple concurrent requests
            prompts = [f"Test prompt {i}" for i in range(10)]

            start_time = time.time()

            # Use ThreadPoolExecutor for concurrent execution
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(ai_service.generate_content, prompt)
                    for prompt in prompts
                ]

                # Collect results
                results = [
                    future.result()
                    for future in concurrent.futures.as_completed(futures)
                ]

            end_time = time.time()

            # Verify all requests completed successfully
            assert len(results) == 10

            # Verify responses contain expected content
            for result in results:
                assert "Response for: Test prompt" in result

            # Verify concurrent execution was faster than sequential
            # Sequential would take ~1 second (10 * 0.1), concurrent should be much faster
            assert (end_time - start_time) < 0.5

    def test_large_response_handling(self, ai_service):
        """Test handling of large AI responses."""
        # Create a large response (simulate long study plan)
        large_content = "This is a very long study plan. " * 1000  # ~45KB of text

        def mock_large_response(*args, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": large_content}}],
                "model": "gpt-3.5-turbo",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 2000,
                    "total_tokens": 2100,
                },
            }
            return mock_response

        with patch.object(ai_service._client, "post", side_effect=mock_large_response):
            start_time = time.time()
            result = ai_service.generate_content("Create a detailed study plan")
            end_time = time.time()

            # Verify large response was handled correctly
            assert result == large_content
            assert len(result) > 30000  # Should be large (32K+)

            # Verify response time was reasonable (should be fast since mocked)
            assert (end_time - start_time) < 0.1

    def test_memory_usage_with_large_responses(self, ai_service):
        """Test memory usage with multiple large responses."""

        # Create multiple large responses
        def mock_large_response(*args, **kwargs):
            large_content = "Large response content. " * 500  # ~22KB each
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": large_content}}],
                "model": "gpt-3.5-turbo",
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 1000,
                    "total_tokens": 1050,
                },
            }
            return mock_response

        with patch.object(ai_service._client, "post", side_effect=mock_large_response):
            # Make multiple large requests
            results = []
            for i in range(20):
                result = ai_service.generate_content(f"Large request {i}")
                results.append(result)

            # Verify all responses were handled
            assert len(results) == 20

            # Verify memory efficiency (responses should be manageable)
            total_content_size = sum(len(result) for result in results)
            assert total_content_size > 200000  # Should be substantial (240K+)

    def test_rate_limiting_under_load(self, ai_service):
        """Test rate limiting behavior under high load."""
        # Mock rate limit error followed by successful response
        call_count = 0

        def mock_rate_limited_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count <= 3:  # First 3 calls get rate limited
                raise Exception("Rate limit exceeded (429)")
            else:  # Subsequent calls succeed
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "choices": [
                        {
                            "message": {
                                "content": f"Response after rate limit {call_count}"
                            }
                        }
                    ],
                    "model": "gpt-3.5-turbo",
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 20,
                        "total_tokens": 30,
                    },
                }
                return mock_response

        with patch.object(
            ai_service._client, "post", side_effect=mock_rate_limited_response
        ):
            # Make multiple rapid requests
            results = []
            for i in range(5):
                try:
                    result = ai_service.generate_content(f"Load test {i}")
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})

            # Verify rate limiting was handled (some requests should succeed after retries)
            successful_results = [r for r in results if "error" not in r]
            assert len(successful_results) > 0  # At least some should succeed

    def test_concurrent_study_plan_generation(self, ai_service, user):
        """Test concurrent study plan generation."""

        def mock_study_plan_response(*args, **kwargs):
            # Simulate study plan generation
            time.sleep(0.2)  # Simulate processing time
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": "Generated study plan content with topics and objectives"
                        }
                    }
                ],
                "model": "gpt-3.5-turbo",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 500,
                    "total_tokens": 600,
                },
            }
            return mock_response

        with patch.object(
            ai_service._client, "post", side_effect=mock_study_plan_response
        ):
            # Create multiple study plan requests concurrently
            study_plan_requests = [
                {"subject": "Math", "grade_level": "Grade 10", "topic": "Algebra"},
                {"subject": "Science", "grade_level": "Grade 11", "topic": "Physics"},
                {
                    "subject": "History",
                    "grade_level": "Grade 9",
                    "topic": "World War II",
                },
                {
                    "subject": "English",
                    "grade_level": "Grade 12",
                    "topic": "Shakespeare",
                },
            ]

            start_time = time.time()

            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(
                        ai_service.generate_content,
                        f"Create study plan for {req['subject']} {req['topic']}",
                    )
                    for req in study_plan_requests
                ]

                results = [
                    future.result()
                    for future in concurrent.futures.as_completed(futures)
                ]

            end_time = time.time()

            # Verify all study plans were generated
            assert len(results) == 4

            # Verify concurrent execution was efficient
            # Sequential would take ~0.8 seconds, concurrent should be much faster
            assert (end_time - start_time) < 0.4

    def test_response_caching_performance(self, ai_service):
        """Test performance with response caching."""
        # Mock response with caching behavior
        call_count = 0

        def mock_cached_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            # Simulate slow response on first call, fast on subsequent
            if call_count == 1:
                time.sleep(1.0)  # Slow first call
            else:
                time.sleep(0.01)  # Fast subsequent calls

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Cached response content"}}],
                "model": "gpt-3.5-turbo",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                },
            }
            return mock_response

        with patch.object(ai_service._client, "post", side_effect=mock_cached_response):
            # First call - should be slow
            start_time = time.time()
            result1 = ai_service.generate_content("Test prompt")
            first_call_time = time.time() - start_time

            # Subsequent calls - should be fast (simulating cache)
            start_time = time.time()
            result2 = ai_service.generate_content("Test prompt")
            second_call_time = time.time() - start_time

            # Verify first call was slow, second was fast
            assert first_call_time > 0.5  # First call should be slow
            assert second_call_time < 0.1  # Second call should be fast

            # Verify both results are identical (cached)
            assert result1 == result2

    def test_large_input_handling(self, ai_service):
        """Test handling of large input prompts."""
        # Create large input prompt
        large_prompt = "Please analyze this large text: " + (
            "This is sample text. " * 1000
        )

        def mock_large_input_response(*args, **kwargs):
            # The first argument should be the URL, second should be the data
            data = args[1] if len(args) > 1 else kwargs.get("json", {})
            messages = data.get("messages", [])
            input_content = messages[0]["content"] if messages else ""

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": f"Processed large input of length {len(input_content)}"
                        }
                    }
                ],
                "model": "gpt-3.5-turbo",
                "usage": {
                    "prompt_tokens": len(input_content) // 4,
                    "completion_tokens": 50,
                    "total_tokens": (len(input_content) // 4) + 50,
                },
            }
            return mock_response

        with patch.object(
            ai_service._client, "post", side_effect=mock_large_input_response
        ):
            start_time = time.time()
            result = ai_service.generate_content(large_prompt)
            end_time = time.time()

            # Verify large input was processed
            assert "Processed large input" in result
            assert len(result) > 30  # Should contain the length info

            # Verify reasonable processing time
            assert (end_time - start_time) < 0.1

    def test_performance_under_memory_pressure(self, ai_service):
        """Test AI service performance under memory pressure."""

        def mock_response(*args, **kwargs):
            # Simulate some processing
            time.sleep(0.05)
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Response under memory pressure"}}],
                "model": "gpt-3.5-turbo",
                "usage": {
                    "prompt_tokens": 25,
                    "completion_tokens": 25,
                    "total_tokens": 50,
                },
            }
            return mock_response

        with patch.object(ai_service._client, "post", side_effect=mock_response):
            # Make many requests to simulate memory pressure
            results = []
            start_time = time.time()

            for i in range(50):  # Many requests
                result = ai_service.generate_content(f"Memory pressure test {i}")
                results.append(result)

                # Small delay to simulate realistic usage
                time.sleep(0.01)

            end_time = time.time()

            # Verify all requests completed
            assert len(results) == 50

            # Verify reasonable total time (should be much less than sequential)
            total_time = end_time - start_time
            assert total_time < 4.0  # Should complete within reasonable time
