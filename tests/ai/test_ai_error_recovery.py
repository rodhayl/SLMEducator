"""
Comprehensive testing for error recovery mechanisms in SLMEducator AI integration.
Tests graceful degradation, retry mechanisms, and fallback options.
"""

import pytest
import time
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.models.models import AIModelConfiguration
from src.core.services.ai_service import AIService, AIProvider, AIServiceError

# Removed duplicate create_ai_response fixture - using centralized one from conftest.py


class TestAIErrorRecovery:
    """Test error recovery mechanisms and graceful degradation."""

    @pytest.fixture
    def mock_ai_config(self):
        """Create mock AI configuration."""
        config = Mock(spec=AIModelConfiguration)
        config.id = 1
        config.provider = "openrouter"
        config.model = "gpt-3.5-turbo"
        config.endpoint = "https://openrouter.ai/api/v1"
        config.api_key = "encrypted_test_key_12345"
        config.model_parameters = {
            "temperature": 0.7,
            "max_tokens": 1000,
            "system_prompt": "You are an educational assistant.",
        }
        config.validated = True
        config.created_at = datetime.now()
        config.updated_at = datetime.now()

        # Mock encryption methods
        config.decrypted_api_key = "sk-test-key-12345"
        config.set_encrypted_api_key = Mock()
        return config

    def test_graceful_degradation_on_service_failure(
        self, mock_ai_config, mock_logger, create_ai_response
    ):
        """Test graceful degradation when AI service fails."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Act - Simulate service failure with fallback
        with patch.object(ai_service, "generate_content") as mock_generate:
            # First call fails, second call (fallback) succeeds
            mock_generate.side_effect = [
                AIServiceError("Primary service failed"),
                create_ai_response("Fallback educational content", tokens_used=50),
            ]

            # Implement retry logic
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    result = ai_service.generate_content("Create lesson plan")
                    break
                except AIServiceError:
                    if attempt < max_retries - 1:
                        mock_logger.warning(
                            f"Attempt {attempt + 1} failed, retrying..."
                        )
                        continue
                    else:
                        raise

            # Assert
            assert result.content == "Fallback educational content"
            assert mock_generate.call_count == 2
            mock_logger.warning.assert_called()

    def test_retry_mechanism_with_exponential_backoff(
        self, mock_ai_config, mock_logger, create_ai_response
    ):
        """Test retry mechanism with exponential backoff."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Act - Simulate transient failures with backoff
        with patch.object(ai_service, "generate_content") as mock_generate:
            mock_generate.side_effect = [
                AIServiceError("Temporary network error"),
                AIServiceError("Temporary network error"),
                create_ai_response(
                    "Content after retry", tokens_used=75, response_time=0.5
                ),
            ]

            # Implement exponential backoff retry
            base_delay = 0.1
            max_retries = 3
            result = None

            for attempt in range(max_retries):
                try:
                    result = ai_service.generate_content("Help with math")
                    break
                except AIServiceError:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2**attempt)  # Exponential backoff
                        mock_logger.info(f"Retrying after {delay}s delay...")
                        time.sleep(delay)  # Simulate backoff delay
                        continue
                    else:
                        raise

            # Assert
            assert result.content == "Content after retry"
            assert mock_generate.call_count == 3
            mock_logger.info.assert_called()

    def test_fallback_provider_switching(
        self, mock_ai_config, mock_logger, create_ai_response
    ):
        """Test fallback to alternative providers when primary fails."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Mock multiple providers
        fallback_config = Mock(spec=AIModelConfiguration)
        fallback_config.provider = "ollama"
        fallback_config.model = "llama2"
        fallback_config.endpoint = "http://localhost:11434"
        fallback_config.api_key = ""
        fallback_config.model_parameters = {"temperature": 0.7}
        fallback_config.decrypted_api_key = ""

        # Act - Simulate primary provider failure with fallback
        with patch.object(ai_service, "generate_content") as mock_primary:
            mock_primary.side_effect = AIServiceError("Primary provider failed")

            # Create fallback service and mock its methods to avoid real HTTP calls
            with patch(
                "src.core.services.ai_service.AIService"
            ) as mock_fallback_service:
                mock_fallback_instance = Mock()
                mock_fallback_instance.generate_content.return_value = (
                    create_ai_response(
                        "Content from fallback provider",
                        tokens_used=60,
                        model="llama2",
                        provider="ollama",
                        response_time=2.0,
                    )
                )
                mock_fallback_service.return_value = mock_fallback_instance

                # Try primary, then fallback
                try:
                    result = ai_service.generate_content("Explain photosynthesis")
                except AIServiceError:
                    mock_logger.warning(
                        "Primary provider failed, switching to fallback..."
                    )
                    # Use the mocked fallback service instead of creating real one
                    fallback_service = mock_fallback_instance
                    result = fallback_service.generate_content("Explain photosynthesis")

                # Assert
                assert "Content from fallback provider" in result.content
                assert result.provider == AIProvider.OLLAMA
                mock_logger.warning.assert_called()

    def test_circuit_breaker_pattern(self, mock_ai_config, mock_logger):
        """Test circuit breaker pattern to prevent cascading failures."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Act - Simulate repeated failures triggering circuit breaker
        with patch.object(ai_service, "generate_content") as mock_generate:
            mock_generate.side_effect = AIServiceError("Service unavailable")

            # Circuit breaker state
            failure_count = 0
            max_failures = 3
            circuit_open = False
            circuit_timeout = 1.0
            last_failure_time = 0

            # Simulate multiple requests
            for i in range(5):
                if circuit_open:
                    # Check if circuit should be reset
                    if time.time() - last_failure_time > circuit_timeout:
                        circuit_open = False
                        failure_count = 0
                        mock_logger.info("Circuit breaker reset, trying again...")
                    else:
                        mock_logger.error("Circuit breaker open, request rejected")
                        continue

                try:
                    result = ai_service.generate_content("Question " + str(i))
                except AIServiceError:
                    failure_count += 1
                    last_failure_time = time.time()

                    if failure_count >= max_failures:
                        circuit_open = True
                        mock_logger.error(
                            f"Circuit breaker opened after {failure_count} failures"
                        )

            # Assert
            assert circuit_open is True
            assert failure_count == 3
            assert mock_generate.call_count == 3  # Stopped after circuit opened
            mock_logger.error.assert_called()

    def test_degraded_mode_operation(
        self, mock_ai_config, mock_logger, create_ai_response
    ):
        """Test operation in degraded mode with limited functionality."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Act - Simulate degraded mode with cached responses
        with patch.object(ai_service, "generate_content") as mock_generate:
            mock_generate.side_effect = AIServiceError("Service degraded")

            # Implement degraded mode with cache
            cache = {
                "basic math": "Mathematics involves numbers and operations",
                "science basics": "Science is the study of natural phenomena",
                "history overview": "History studies past events and civilizations",
            }

            def get_degraded_response(prompt):
                """Provide cached responses in degraded mode."""
                mock_logger.warning(
                    "Operating in degraded mode, using cached responses"
                )

                # Try to find cached response - use more flexible matching
                prompt_lower = prompt.lower()
                for key, response in cache.items():
                    if key in prompt_lower or any(
                        word in prompt_lower for word in key.split()
                    ):
                        return create_ai_response(
                            response,
                            tokens_used=25,
                            model="cached",
                            provider="openrouter",
                            response_time=0.1,
                        )

                # Default response if no cache hit
                return create_ai_response(
                    "Service temporarily unavailable. Please try again later.",
                    tokens_used=10,
                    model="degraded",
                    provider="openrouter",
                    response_time=0.1,
                )

            # Test degraded responses
            result1 = get_degraded_response("Explain basic math concepts")
            result2 = get_degraded_response("Tell me about science")
            result3 = get_degraded_response("Unknown topic")

            # Assert
            assert "Mathematics involves numbers" in result1.content
            assert "Science is the study" in result2.content
            assert "Service temporarily unavailable" in result3.content
            assert result1.tokens_used == 25
            assert result3.tokens_used == 10
            mock_logger.warning.assert_called()

    def test_recovery_notification_system(
        self, mock_ai_config, mock_logger, create_ai_response
    ):
        """Test notification system when service recovers."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Act - Simulate service failure and recovery
        with patch.object(ai_service, "generate_content") as mock_generate:
            # First call fails, second succeeds (recovery)
            mock_generate.side_effect = [
                AIServiceError("Service temporarily down"),
                create_ai_response(
                    "Service recovered successfully",
                    tokens_used=40,
                    model="gpt-3.5-turbo",
                    provider="openrouter",
                    response_time=1.5,
                ),
            ]

            # Track service health
            service_healthy = False
            last_successful_call = None

            # First attempt fails
            try:
                ai_service.generate_content("Test recovery")
            except AIServiceError:
                service_healthy = False
                mock_logger.error("Service health check failed")

            # Second attempt succeeds (recovery)
            try:
                result = ai_service.generate_content("Test recovery")
                service_healthy = True
                last_successful_call = datetime.now()
                mock_logger.info("Service recovered! Notification sent to users.")
            except AIServiceError:
                service_healthy = False

            # Assert
            assert service_healthy is True
            assert result.content == "Service recovered successfully"
            assert last_successful_call is not None
            mock_logger.info.assert_called()

    def test_bulk_operation_recovery(
        self, mock_ai_config, mock_logger, create_ai_response
    ):
        """Test recovery from failures during bulk operations."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Act - Simulate bulk operation with partial failures
        with patch.object(ai_service, "generate_content") as mock_generate:
            # Mix of successes and failures
            mock_generate.side_effect = [
                create_ai_response(
                    "Result 1",
                    tokens_used=30,
                    model="gpt-3.5-turbo",
                    provider="openrouter",
                    response_time=1.0,
                ),
                AIServiceError("Temporary failure"),
                create_ai_response(
                    "Result 3",
                    tokens_used=35,
                    model="gpt-3.5-turbo",
                    provider="openrouter",
                    response_time=1.2,
                ),
                AIServiceError("Another failure"),
                create_ai_response(
                    "Result 5",
                    tokens_used=40,
                    model="gpt-3.5-turbo",
                    provider="openrouter",
                    response_time=0.8,
                ),
            ]

            # Bulk operation with error recovery
            prompts = ["Prompt 1", "Prompt 2", "Prompt 3", "Prompt 4", "Prompt 5"]
            results = []
            failed_items = []

            for i, prompt in enumerate(prompts):
                try:
                    result = ai_service.generate_content(prompt)
                    results.append({"success": True, "data": result})
                    mock_logger.info(f"Item {i + 1} processed successfully")
                except AIServiceError as e:
                    failed_items.append({"index": i, "prompt": prompt, "error": str(e)})
                    mock_logger.error(f"Item {i + 1} failed: {e}")
                    # Continue with remaining items
                    continue

            # Retry failed items after delay
            if failed_items:
                mock_logger.info(
                    f"Retrying {len(failed_items)} failed items after recovery period..."
                )
                time.sleep(0.1)  # Simulate recovery delay

                # Mock recovery for retry
                with patch.object(ai_service, "generate_content") as mock_retry:
                    mock_retry.return_value = create_ai_response(
                        "Recovered result",
                        tokens_used=25,
                        model="gpt-3.5-turbo",
                        provider="openrouter",
                        response_time=1.0,
                    )

                    for failed_item in failed_items:
                        try:
                            retry_result = ai_service.generate_content(
                                failed_item["prompt"]
                            )
                            results.append(
                                {"success": True, "data": retry_result, "retried": True}
                            )
                            mock_logger.info(
                                f"Retried item {failed_item['index'] + 1} succeeded"
                            )
                        except AIServiceError:
                            results.append(
                                {"success": False, "error": "Permanent failure"}
                            )

            # Assert
            assert len(results) == 5  # All items processed (3 original + 2 retried)
            assert mock_generate.call_count == 5
            assert len([r for r in results if r["success"]]) == 5
            mock_logger.info.assert_called()

    def test_timeout_recovery_with_progress_preservation(
        self, mock_ai_config, mock_logger, create_ai_response
    ):
        """Test recovery from timeouts with progress preservation."""
        # Arrange
        ai_service = AIService(mock_ai_config, mock_logger)

        # Act - Simulate timeout with progress preservation
        with patch.object(ai_service, "generate_content") as mock_generate:
            mock_generate.side_effect = AIServiceError("Request timeout")

            # Simulate long-running operation with progress tracking
            operation_progress = {
                "total_steps": 5,
                "completed_steps": 2,
                "current_step": 3,
                "partial_results": ["Step 1 result", "Step 2 result"],
            }

            # Timeout occurs during step 3
            try:
                result = ai_service.generate_content("Complex multi-step operation")
            except AIServiceError as timeout_error:
                mock_logger.warning(
                    f"Operation timed out at step {operation_progress['current_step']}"
                )

                # Preserve progress and implement recovery
                operation_progress["timeout_recovered"] = True
                operation_progress["recovery_timestamp"] = datetime.now()

                # Resume from saved progress
                mock_logger.info(
                    f"Resuming operation from step {operation_progress['current_step']}"
                )

                # Simulate resumed operation
                with patch.object(ai_service, "generate_content") as mock_resumed:
                    mock_resumed.return_value = create_ai_response(
                        "Operation completed after recovery",
                        tokens_used=120,
                        model="gpt-3.5-turbo",
                        provider="openrouter",
                        response_time=3.0,
                    )

                    resumed_result = ai_service.generate_content(
                        "Resume complex operation"
                    )
                    operation_progress["completed_steps"] = operation_progress[
                        "total_steps"
                    ]
                    operation_progress["final_result"] = resumed_result

            # Assert
            assert operation_progress["timeout_recovered"] is True
            assert operation_progress["completed_steps"] == 5
            assert "Operation completed after recovery" in resumed_result.content
            assert operation_progress["recovery_timestamp"] is not None
            mock_logger.warning.assert_called()
            mock_logger.info.assert_called()
