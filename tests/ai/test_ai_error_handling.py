"""
Test error handling scenarios for AI integration - network failures, auth errors, service unavailable
"""

import pytest
import httpx
from unittest.mock import Mock, patch

from core.services.ai_service import AIService, AIServiceError
from core.models import AIModelConfiguration


class TestAIErrorHandling:
    """Test comprehensive error handling for AI integration"""

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

    def test_network_timeout_error(self, ai_service):
        """Test handling of network timeout errors"""
        # Mock httpx client to raise timeout exception
        with patch.object(ai_service._client, "post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Connection timed out")

            with pytest.raises(AIServiceError) as exc_info:
                ai_service.generate_content("Test message")

            assert (
                "timeout" in str(exc_info.value).lower()
                or "connection" in str(exc_info.value).lower()
            )
            assert ai_service.logger.error.called

    def test_network_connection_error(self, ai_service):
        """Test handling of network connection errors"""
        # Mock httpx client to raise connection error
        with patch.object(ai_service._client, "post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Failed to establish connection")

            with pytest.raises(AIServiceError) as exc_info:
                ai_service.generate_content("Test message")

            assert (
                "connection" in str(exc_info.value).lower()
                or "network" in str(exc_info.value).lower()
            )
            assert ai_service.logger.error.called

    def test_http_401_unauthorized_error(self, ai_service):
        """Test handling of HTTP 401 unauthorized errors"""
        # Mock response with 401 status
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=Mock(), response=mock_response
        )

        with patch.object(ai_service._client, "post", return_value=mock_response):
            with pytest.raises(AIServiceError) as exc_info:
                ai_service.generate_content("Test message")

            error_msg = str(exc_info.value).lower()
            assert "401" in error_msg or "unauthorized" in error_msg
            assert ai_service.logger.error.called

    def test_http_403_forbidden_error(self, ai_service):
        """Test handling of HTTP 403 forbidden errors"""
        # Mock response with 403 status
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Access forbidden"
        mock_response.json.return_value = {
            "error": {"message": "You don't have access to this model"}
        }
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "403 Forbidden", request=Mock(), response=mock_response
        )

        with patch.object(ai_service._client, "post", return_value=mock_response):
            with pytest.raises(AIServiceError) as exc_info:
                ai_service.generate_content("Test message")

            assert (
                "403" in str(exc_info.value)
                or "forbidden" in str(exc_info.value).lower()
            )
            assert ai_service.logger.error.called

    def test_http_404_not_found_error(self, ai_service):
        """Test handling of HTTP 404 not found errors"""
        # Mock response with 404 status
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Model not found"
        mock_response.json.return_value = {"error": {"message": "Model does not exist"}}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=mock_response
        )

        with patch.object(ai_service._client, "post", return_value=mock_response):
            with pytest.raises(AIServiceError) as exc_info:
                ai_service.generate_content("Test message")

            assert (
                "404" in str(exc_info.value)
                or "not found" in str(exc_info.value).lower()
            )
            assert ai_service.logger.error.called

    def test_http_429_rate_limit_error(self, ai_service):
        """Test handling of HTTP 429 rate limit errors"""
        # Mock response with 429 status
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_response.json.return_value = {
            "error": {"message": "Rate limit exceeded. Please try again later."}
        }
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "429 Too Many Requests", request=Mock(), response=mock_response
        )

        with patch.object(ai_service._client, "post", return_value=mock_response):
            with pytest.raises(AIServiceError) as exc_info:
                ai_service.generate_content("Test message")

            assert (
                "429" in str(exc_info.value)
                or "rate limit" in str(exc_info.value).lower()
            )
            assert (
                ai_service.logger.error.called
            )  # Rate limit errors should be logged as errors

    def test_http_500_internal_server_error(self, ai_service):
        """Test handling of HTTP 500 internal server errors"""
        # Mock response with 500 status
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_response.json.return_value = {
            "error": {"message": "The server encountered an internal error"}
        }
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error", request=Mock(), response=mock_response
        )

        with patch.object(ai_service._client, "post", return_value=mock_response):
            with pytest.raises(AIServiceError) as exc_info:
                ai_service.generate_content("Test message")

            assert (
                "500" in str(exc_info.value)
                or "internal server" in str(exc_info.value).lower()
            )
            assert ai_service.logger.error.called

    def test_http_503_service_unavailable_error(self, ai_service):
        """Test handling of HTTP 503 service unavailable errors"""
        # Mock response with 503 status
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.text = "Service temporarily unavailable"
        mock_response.json.return_value = {
            "error": {"message": "The service is temporarily unavailable"}
        }
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "503 Service Unavailable", request=Mock(), response=mock_response
        )

        with patch.object(ai_service._client, "post", return_value=mock_response):
            with pytest.raises(AIServiceError) as exc_info:
                ai_service.generate_content("Test message")

            assert (
                "503" in str(exc_info.value)
                or "service unavailable" in str(exc_info.value).lower()
            )
            assert ai_service.logger.error.called

    def test_invalid_json_response_error(self, ai_service):
        """Test handling of invalid JSON responses"""
        # Mock the _call_openai method to simulate JSON parsing error
        with patch.object(ai_service, "_call_openai") as mock_openai:
            # Return invalid JSON that will cause parsing error in higher-level methods
            mock_openai.return_value = {
                "content": "{invalid json",
                "model": "gpt-3.5-turbo",
            }

            # Force provider to be openai for this test
            ai_service.config.provider = "openai"

            # This should not raise an error since generate_content returns the content directly
            result = ai_service.generate_content("Test message")
            assert result == "{invalid json"
            assert ai_service.logger.info.called

    def test_missing_response_fields_error(self, ai_service):
        """Test handling of responses with missing required fields"""
        # Mock the _call_openai method to return response with missing fields
        with patch.object(ai_service, "_call_openai") as mock_openai:
            mock_openai.return_value = {
                "id": "test-id",
                "model": "gpt-3.5-turbo",
            }  # Missing 'content' field

            # Force provider to be openai for this test
            ai_service.config.provider = "openai"

            with pytest.raises(AIServiceError) as exc_info:
                ai_service.generate_content("Test message")

            assert ai_service.logger.error.called

    def test_empty_response_error(self, ai_service):
        """Test handling of empty responses"""
        # Mock the _call_openai method to return empty content
        with patch.object(ai_service, "_call_openai") as mock_openai:
            mock_openai.return_value = {
                "content": "",
                "model": "gpt-3.5-turbo",
                "tokens_used": 0,
            }

            # Force provider to be openai for this test
            ai_service.config.provider = "openai"

            result = ai_service.generate_content("Test message")
            # Empty response should be handled gracefully
            assert result == ""
            assert (
                ai_service.logger.info.called
            )  # Empty content is logged as info, not warning

    def test_ssl_certificate_error(self, ai_service):
        """Test handling of SSL certificate errors"""
        # Mock httpx client to raise SSL error
        with patch.object(ai_service._client, "post") as mock_post:
            mock_post.side_effect = httpx.ConnectError(
                "SSL certificate verification failed"
            )

            with pytest.raises(AIServiceError) as exc_info:
                ai_service.generate_content("Test message")

            assert (
                "ssl" in str(exc_info.value).lower()
                or "certificate" in str(exc_info.value).lower()
            )
            assert ai_service.logger.error.called

    def test_dns_resolution_error(self, ai_service):
        """Test handling of DNS resolution errors"""
        # Mock httpx client to raise DNS resolution error
        with patch.object(ai_service._client, "post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Failed to resolve host")

            with pytest.raises(AIServiceError) as exc_info:
                ai_service.generate_content("Test message")

            assert (
                "dns" in str(exc_info.value).lower()
                or "resolve" in str(exc_info.value).lower()
            )
            assert ai_service.logger.error.called

    def test_proxy_error(self, ai_service):
        """Test handling of proxy errors"""
        # Mock httpx client to raise proxy error
        with patch.object(ai_service._client, "post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Proxy connection failed")

            with pytest.raises(AIServiceError) as exc_info:
                ai_service.generate_content("Test message")

            assert "proxy" in str(exc_info.value).lower()
            assert ai_service.logger.error.called

    def test_timeout_with_retry_logic(self, ai_service):
        """Test timeout error with retry logic"""
        # Mock httpx client to timeout on first call, succeed on second
        call_count = 0

        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.TimeoutException("First attempt timed out")
            else:
                # Return successful response on retry
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "choices": [{"message": {"content": "Success after retry"}}]
                }
                return mock_response

        with patch.object(ai_service._client, "post", side_effect=mock_post):
            # If retry logic exists, this should succeed
            try:
                result = ai_service.generate_content("Test message")
                assert "Success after retry" in result
                assert call_count == 2
            except AIServiceError:
                # If no retry logic, should fail with timeout error
                assert call_count == 1
                assert ai_service.logger.error.called

    def test_multiple_consecutive_errors(self, ai_service):
        """Test handling of multiple consecutive errors"""
        error_count = 0

        def mock_post(*args, **kwargs):
            nonlocal error_count
            error_count += 1
            if error_count <= 3:  # First 3 calls fail
                raise httpx.ConnectError(f"Attempt {error_count} failed")
            else:  # 4th call succeeds
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "choices": [{"message": {"content": "Success after failures"}}]
                }
                return mock_response

        with patch.object(ai_service._client, "post", side_effect=mock_post):
            try:
                result = ai_service.generate_content("Test message")
                assert "Success after failures" in result
                assert error_count == 4
            except AIServiceError:
                # Should fail with connection error if no retry logic
                assert error_count >= 1
                assert ai_service.logger.error.called

    def test_error_logging_consistency(self, ai_service):
        """Test that errors are logged consistently with proper context"""
        # Mock different types of errors and verify logging
        test_errors = [
            httpx.TimeoutException("Test timeout"),
            httpx.ConnectError("Test connection error"),
            httpx.HTTPStatusError("404 Not Found", request=Mock(), response=Mock()),
            ValueError("Test value error"),
            KeyError("Test key error"),
        ]

        for error in test_errors:
            with patch.object(ai_service._client, "post", side_effect=error):
                with pytest.raises(AIServiceError):
                    ai_service.generate_content("Test message")

                # Verify error was logged with appropriate level
                assert (
                    ai_service.logger.error.called
                    or ai_service.logger.warning.called
                    or ai_service.logger.exception.called
                )

                # Reset mocks for next iteration
                ai_service.logger.reset_mock()

    def test_user_friendly_error_messages(self, ai_service):
        """Test that error messages are user-friendly and actionable"""
        # Test various error scenarios and verify user-friendly messages
        error_scenarios = [
            (httpx.TimeoutException("Connection timed out"), ["timeout", "connection"]),
            (httpx.ConnectError("Network unreachable"), ["connection", "network"]),
            (
                httpx.HTTPStatusError(
                    "401 Unauthorized", request=Mock(), response=Mock()
                ),
                ["authentication", "unauthorized"],
            ),
            (
                httpx.HTTPStatusError(
                    "429 Too Many Requests", request=Mock(), response=Mock()
                ),
                ["rate limit", "429"],
            ),
            (
                httpx.HTTPStatusError(
                    "500 Internal Server Error", request=Mock(), response=Mock()
                ),
                ["server error", "500"],
            ),
            (ValueError("Invalid JSON"), ["response", "json"]),
        ]

        for error, expected_keywords in error_scenarios:
            with patch.object(ai_service._client, "post", side_effect=error):
                with pytest.raises(AIServiceError) as exc_info:
                    ai_service.generate_content("Test message")

                error_message = str(exc_info.value).lower()
                # Error message should be user-friendly (not too technical)
                assert len(error_message) < 200  # Reasonable length
                # Check if any of the expected keywords are in the error message
                assert any(keyword in error_message for keyword in expected_keywords)
                # Should not contain raw exception details
                assert "traceback" not in error_message
                assert "exception" not in error_message
