"""
Test performance scenarios for AI integration - slow responses, concurrent requests, large responses
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
import httpx

from core.services.ai_service import AIService, AIServiceError
from core.models import AIModelConfiguration


class TestAIPerformance:
    """Test AI service performance under various conditions"""

    @pytest.fixture
    def mock_ai_config(self):
        """Create a mock AI configuration"""
        config = Mock(spec=AIModelConfiguration)
        config.provider = "openai"
        config.model = "gpt-3.5-turbo"
        config.endpoint = "https://api.openai.com/v1"
        config.decrypted_api_key = "test-api-key"
        config.model_parameters = {"temperature": 0.7, "max_tokens": 1000}
        return config

    @pytest.fixture
    def ai_service(self, mock_ai_config):
        """Create AI service with mock config"""
        logger = Mock()
        service = AIService(mock_ai_config, logger)
        try:
            yield service
        finally:
            try:
                service.close()
            except Exception:
                pass

    def test_slow_response_handling(self, ai_service):
        """Test handling of slow AI responses"""

        def slow_response(*args, **kwargs):
            time.sleep(2)  # Simulate slow response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Slow response content"}}],
                "model": "gpt-3.5-turbo",
            }
            return mock_response

        start_time = time.time()
        with patch.object(ai_service._client, "post", side_effect=slow_response):
            result = ai_service.generate_content("Test message")
            elapsed_time = time.time() - start_time

            assert result == "Slow response content"
            assert elapsed_time >= 2.0  # Should take at least 2 seconds
            assert ai_service.logger.info.called

    def test_concurrent_requests(self, ai_service):
        """Test handling of concurrent AI requests"""
        results = []
        errors = []

        def mock_response(*args, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Concurrent response"}}],
                "model": "gpt-3.5-turbo",
            }
            return mock_response

        def make_request():
            try:
                with patch.object(
                    ai_service._client, "post", side_effect=mock_response
                ):
                    result = ai_service.generate_content("Test concurrent message")
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads to simulate concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All requests should succeed
        assert len(results) == 5
        assert len(errors) == 0
        assert all(result == "Concurrent response" for result in results)

    def test_large_response_handling(self, ai_service):
        """Test handling of large AI responses"""
        # Create a large response (simulate 10KB of text)
        large_content = "This is a large response. " * 1000  # ~25KB

        def mock_response(*args, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": large_content}}],
                "model": "gpt-3.5-turbo",
            }
            return mock_response

        with patch.object(ai_service._client, "post", side_effect=mock_response):
            result = ai_service.generate_content("Generate large content")

            assert result == large_content
            assert len(result) > 10000  # Should be a large response
            assert ai_service.logger.info.called

    def test_response_time_measurement(self, ai_service):
        """Test that response times are properly measured and logged"""

        def mock_response(*args, **kwargs):
            time.sleep(0.1)  # Small delay
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Response time test"}}],
                "model": "gpt-3.5-turbo",
            }
            return mock_response

        with patch.object(ai_service._client, "post", side_effect=mock_response):
            result = ai_service.generate_content("Test response time")

            assert result == "Response time test"
            # Check that response time was logged
            log_calls = [
                call
                for call in ai_service.logger.info.call_args_list
                if "AI call completed" in str(call)
            ]
            assert len(log_calls) > 0

    def test_timeout_handling(self, ai_service):
        """Test timeout handling for long-running requests"""
        # Mock httpx client to raise timeout exception
        with patch.object(ai_service._client, "post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(AIServiceError) as exc_info:
                ai_service.generate_content("Test timeout")

            assert (
                "timeout" in str(exc_info.value).lower()
                or "timed out" in str(exc_info.value).lower()
            )
            assert ai_service.logger.error.called

    def test_memory_usage_with_large_requests(self, ai_service):
        """Test memory usage with large request/response data"""
        # Create large input and expect large output
        large_input = "Explain this topic in detail: " + "x" * 5000  # 5KB input
        large_output = "Detailed explanation: " + "y" * 10000  # 10KB output

        def mock_response(*args, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": large_output}}],
                "model": "gpt-3.5-turbo",
            }
            return mock_response

        with patch.object(ai_service._client, "post", side_effect=mock_response):
            result = ai_service.generate_content(large_input)

            assert result == large_output
            assert len(result) > 10000
            assert ai_service.logger.info.called

    def test_request_queueing_behavior(self, ai_service):
        """Test behavior when multiple requests are queued"""
        results = []

        def make_request(index):
            def track_response(*args, **kwargs):
                time.sleep(0.1)  # Small delay
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "choices": [{"message": {"content": f"Response {index + 1}"}}],
                    "model": "gpt-3.5-turbo",
                }
                return mock_response

            with patch.object(ai_service._client, "post", side_effect=track_response):
                result = ai_service.generate_content(f"Request {index}")
                results.append((index, result))

        # Create multiple requests in quick succession
        threads = []
        for i in range(3):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All requests should complete successfully
        assert len(results) == 3
        # Check that all expected responses are present
        response_contents = [result[1] for result in results]
        assert all(
            any(f"Response {i + 1}" in content for content in response_contents)
            for i in range(3)
        )

    def test_performance_under_load(self, ai_service):
        """Test AI service performance under simulated load"""

        def mock_response(*args, **kwargs):
            time.sleep(0.05)  # Small delay to simulate processing
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Load test response"}}],
                "model": "gpt-3.5-turbo",
            }
            return mock_response

        start_time = time.time()
        results = []

        # Make multiple sequential requests to simulate load
        for i in range(10):
            with patch.object(ai_service._client, "post", side_effect=mock_response):
                result = ai_service.generate_content(f"Load test {i}")
                results.append(result)

        total_time = time.time() - start_time

        assert len(results) == 10
        assert all(result == "Load test response" for result in results)
        assert total_time < 2.0  # Should complete within reasonable time

    def test_token_counting_performance(self, ai_service):
        """Test performance of token counting for large inputs"""
        # Create large input to test token counting performance
        large_input = "This is a test input. " * 1000  # ~25KB

        def mock_response(*args, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Token counting test"}}],
                "model": "gpt-3.5-turbo",
                "usage": {"total_tokens": 1500},  # Simulate token usage
            }
            return mock_response

        start_time = time.time()
        with patch.object(ai_service._client, "post", side_effect=mock_response):
            result = ai_service.generate_content(large_input)
        processing_time = time.time() - start_time

        assert result == "Token counting test"
        assert processing_time < 1.0  # Should process quickly
        assert ai_service.logger.info.called

    def test_response_parsing_performance(self, ai_service):
        """Test performance of response parsing for complex responses"""
        # Create complex JSON response
        complex_response = {
            "choices": [{"message": {"content": "Complex response with nested data"}}],
            "model": "gpt-3.5-turbo",
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 150,
                "total_tokens": 200,
            },
            "id": "chatcmpl-12345",
            "created": 1234567890,
        }

        def mock_response(*args, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = complex_response
            return mock_response

        start_time = time.time()
        with patch.object(ai_service._client, "post", side_effect=mock_response):
            result = ai_service.generate_content("Complex parsing test")
        parsing_time = time.time() - start_time

        assert result == "Complex response with nested data"
        assert parsing_time < 0.1  # Parsing should be very fast

    def test_concurrent_error_handling(self, ai_service):
        """Test error handling during concurrent requests"""

        def alternating_response(*args, **kwargs):
            # Alternate between success and failure
            if not hasattr(alternating_response, "call_count"):
                alternating_response.call_count = 0
            alternating_response.call_count += 1

            if alternating_response.call_count % 2 == 0:
                raise httpx.ConnectError("Simulated connection error")
            else:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "choices": [{"message": {"content": "Concurrent success"}}],
                    "model": "gpt-3.5-turbo",
                }
                return mock_response

        results = []
        errors = []

        def make_request():
            try:
                with patch.object(
                    ai_service._client, "post", side_effect=alternating_response
                ):
                    result = ai_service.generate_content("Concurrent test")
                    results.append(result)
            except AIServiceError as e:
                errors.append(e)

        # Create multiple concurrent requests
        threads = []
        for i in range(6):  # Even number to get equal success/failure
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have a mix of successes and failures
        assert len(results) > 0
        assert len(errors) > 0
        assert len(results) + len(errors) == 6
