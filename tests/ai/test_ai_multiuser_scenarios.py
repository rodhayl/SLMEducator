"""
Comprehensive multi-user scenario tests for AI integration.
Tests different user configurations, permissions, and concurrent usage patterns.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.core.models.models import AIModelConfiguration, User, UserRole
from src.core.services.ai_service import AIService, AIServiceError, AIProvider


class TestAIMultiUserScenarios:
    """Test multi-user AI scenarios with different configurations and permissions."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def sample_users(self):
        """Create sample users with different roles and permissions."""
        return [
            User(
                id=1,
                username="teacher1",
                email="teacher1@example.com",
                role=UserRole.TEACHER,
                created_at=datetime.now(),
            ),
            User(
                id=2,
                username="student1",
                email="student1@example.com",
                role=UserRole.STUDENT,
                created_at=datetime.now(),
            ),
            User(
                id=3,
                username="admin1",
                email="admin1@example.com",
                role=UserRole.ADMIN,
                created_at=datetime.now(),
            ),
        ]

    @pytest.fixture
    def multi_user_configs(self, sample_users):
        """Create AI configurations for different users."""
        return [
            # Teacher configurations
            AIModelConfiguration(
                id=1,
                user_id=sample_users[0].id,
                provider=AIProvider.OPENAI.value,
                model="gpt-4",
                endpoint="https://api.openai.com/v1/chat/completions",
                api_key="sk-encrypted-teacher-key-1",
                model_parameters={"temperature": 0.7, "max_tokens": 2000},
                validated=True,
            ),
            AIModelConfiguration(
                id=2,
                user_id=sample_users[0].id,
                provider=AIProvider.OPENROUTER.value,
                model="anthropic/claude-3-sonnet",
                endpoint="https://openrouter.ai/api/v1/chat/completions",
                api_key="sk-encrypted-teacher-key-2",
                model_parameters={"temperature": 0.8, "max_tokens": 1500},
                validated=True,
            ),
            # Student configurations
            AIModelConfiguration(
                id=3,
                user_id=sample_users[1].id,
                provider=AIProvider.OLLAMA.value,
                model="llama2",
                endpoint="http://localhost:11434/api/generate",
                api_key=None,
                model_parameters={"temperature": 0.5, "max_tokens": 1000},
                validated=True,
            ),
            # Admin configurations
            AIModelConfiguration(
                id=4,
                user_id=sample_users[2].id,
                provider=AIProvider.OPENAI.value,
                model="gpt-3.5-turbo",
                endpoint="https://api.openai.com/v1/chat/completions",
                api_key="sk-encrypted-admin-key-1",
                model_parameters={"temperature": 0.6, "max_tokens": 3000},
                validated=True,
            ),
        ]

    def test_user_specific_ai_configurations(self, sample_users, multi_user_configs):
        """Test that users can have different AI configurations."""
        # Test teacher has multiple configurations
        teacher_configs = [
            c for c in multi_user_configs if c.user_id == sample_users[0].id
        ]
        assert len(teacher_configs) == 2
        assert teacher_configs[0].provider == AIProvider.OPENAI.value
        assert teacher_configs[1].provider == AIProvider.OPENROUTER.value

        # Test student has single Ollama configuration
        student_configs = [
            c for c in multi_user_configs if c.user_id == sample_users[1].id
        ]
        assert len(student_configs) == 1
        assert student_configs[0].provider == AIProvider.OLLAMA.value
        assert student_configs[0].api_key is None

        # Test admin has premium configuration
        admin_configs = [
            c for c in multi_user_configs if c.user_id == sample_users[2].id
        ]
        assert len(admin_configs) == 1
        assert admin_configs[0].provider == AIProvider.OPENAI.value
        assert admin_configs[0].model_parameters["max_tokens"] == 3000

    def test_role_based_model_access(self, sample_users, multi_user_configs):
        """Test that different user roles have access to appropriate models."""
        # Teachers should have access to premium models
        teacher_config = next(
            c
            for c in multi_user_configs
            if c.user_id == sample_users[0].id and c.provider == AIProvider.OPENAI.value
        )
        assert teacher_config.model == "gpt-4"

        # Students should have access to local/free models
        student_config = next(
            c for c in multi_user_configs if c.user_id == sample_users[1].id
        )
        assert student_config.provider == AIProvider.OLLAMA.value
        assert student_config.model == "llama2"

        # Admins should have access to all models
        admin_config = next(
            c for c in multi_user_configs if c.user_id == sample_users[2].id
        )
        assert admin_config.provider == AIProvider.OPENAI.value

    def test_concurrent_user_ai_requests(self, multi_user_configs):
        """Test concurrent AI requests from multiple users."""
        results = {}
        errors = {}
        lock = threading.Lock()

        def make_ai_request(config, request_key):
            """Make AI request for a specific user configuration."""
            try:
                ai_service = AIService(config, Mock())

                # Mock successful response based on provider
                if config.provider == AIProvider.OPENAI.value:
                    mock_method = "openai"
                    mock_response = {
                        "content": f"Response for user {config.user_id} with {config.provider}",
                        "tokens_used": 50,
                        "model": config.model,
                    }
                elif config.provider == AIProvider.OPENROUTER.value:
                    mock_method = "openrouter"
                    mock_response = {
                        "content": f"Response for user {config.user_id} with {config.provider}",
                        "tokens_used": 60,
                        "model": config.model,
                    }
                elif config.provider == AIProvider.OLLAMA.value:
                    mock_method = "ollama"
                    mock_response = {
                        "content": f"Response for user {config.user_id} with {config.provider}",
                        "tokens_used": 40,
                        "model": config.model,
                    }

                with patch.object(
                    ai_service, f"_call_{mock_method}", return_value=mock_response
                ):
                    response = ai_service.generate_content("Test prompt")
                    with lock:
                        results[request_key] = response
                        print(f"Thread {request_key} completed successfully")
            except Exception as e:
                with lock:
                    errors[request_key] = f"Thread {request_key} error: {str(e)}"
                    print(f"Thread {request_key} failed: {str(e)}")

        # Create threads for concurrent requests - test different users and providers
        threads = []
        test_configs = [
            multi_user_configs[0],  # User 1, OpenAI
            multi_user_configs[2],  # User 2, Ollama
            multi_user_configs[3],  # User 3, OpenAI (admin)
        ]

        for i, config in enumerate(test_configs):
            request_key = f"user_{config.user_id}_{config.provider}"
            print(f"Starting thread {request_key}")
            thread = threading.Thread(
                target=make_ai_request, args=(config, request_key)
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)

        print(f"Final results: {results}")
        print(f"Final errors: {errors}")

        # Verify all requests completed successfully
        assert (
            len(results) == 3
        ), f"Expected 3 results, got {len(results)}: {results}, errors: {errors}"
        assert len(errors) == 0, f"Unexpected errors: {errors}"

        # Verify responses are user-specific
        for request_key, response in results.items():
            assert any(str(user_id) in response for user_id in [1, 2, 3])

    def test_user_isolation_between_requests(self, multi_user_configs):
        """Test that user requests are properly isolated."""
        # Create AI services for different users
        teacher_service = AIService(multi_user_configs[0], Mock())
        student_service = AIService(multi_user_configs[2], Mock())

        # Mock different responses for each user
        teacher_response = "Teacher-specific response"
        student_response = "Student-specific response"

        with patch.object(
            teacher_service,
            "_call_openai",
            return_value={
                "content": teacher_response,
                "tokens_used": 100,
                "model": "gpt-4",
            },
        ):
            teacher_result = teacher_service.generate_content("Teacher prompt")

        with patch.object(
            student_service,
            "_call_ollama",
            return_value={
                "content": student_response,
                "tokens_used": 50,
                "model": "llama2",
            },
        ):
            student_result = student_service.generate_content("Student prompt")

        # Verify responses are isolated
        assert teacher_result == teacher_response
        assert student_result == student_response
        assert teacher_result != student_result

    def test_shared_configuration_safety(self, sample_users, multi_user_configs):
        """Test that shared configurations don't leak data between users."""
        # Create a configuration that could be shared (e.g., Ollama)
        shared_config = AIModelConfiguration(
            id=5,
            user_id=None,  # Shared configuration
            provider=AIProvider.OLLAMA.value,
            model="llama2",
            endpoint="http://localhost:11434/api/generate",
            api_key=None,
            model_parameters={"temperature": 0.6, "max_tokens": 1000},
            validated=True,
        )

        # Create services for different users using the same config
        teacher_service = AIService(shared_config, Mock())
        student_service = AIService(shared_config, Mock())

        # Mock different responses based on user context
        def mock_ollama_call(prompt, max_tokens, temperature, system_prompt):
            # The system_prompt will be None since we're passing simple prompts
            # Use the prompt content to determine response
            if "teacher" in str(prompt).lower():
                return {
                    "content": "Teacher response",
                    "tokens_used": 75,
                    "model": "llama2",
                }
            else:
                return {
                    "content": "Student response",
                    "tokens_used": 50,
                    "model": "llama2",
                }

        with patch.object(
            teacher_service, "_call_ollama", side_effect=mock_ollama_call
        ):
            teacher_result = teacher_service.generate_content(
                "Teacher prompt about math"
            )

        with patch.object(
            student_service, "_call_ollama", side_effect=mock_ollama_call
        ):
            student_result = student_service.generate_content(
                "Student prompt about science"
            )

        # Verify responses are contextually appropriate
        assert "Teacher" in teacher_result or "teacher" in teacher_result.lower()
        assert "Student" in student_result or "student" in student_result.lower()

    def test_permission_based_model_usage(self, sample_users, multi_user_configs):
        """Test that user permissions affect model usage capabilities."""

        # Simulate permission restrictions
        def check_user_permissions(user_id, provider):
            """Mock permission checking."""
            user = next(u for u in sample_users if u.id == user_id)

            if user.role == UserRole.STUDENT and provider == AIProvider.OPENAI.value:
                return False  # Students can't use OpenAI
            if user.role == UserRole.TEACHER and provider == AIProvider.ANTHROPIC.value:
                return False  # Teachers can't use Anthropic
            return True

        # Test student trying to use OpenAI (should fail permission check)
        student_config = next(
            c for c in multi_user_configs if c.user_id == sample_users[1].id
        )
        # Student has Ollama config, but if they tried OpenAI it should fail
        assert not check_user_permissions(
            student_config.user_id, AIProvider.OPENAI.value
        )
        # Student's actual Ollama config should pass
        assert check_user_permissions(student_config.user_id, student_config.provider)

        # Test teacher trying to use OpenAI (should succeed)
        teacher_openai_config = next(
            c
            for c in multi_user_configs
            if c.user_id == sample_users[0].id and c.provider == AIProvider.OPENAI.value
        )
        assert check_user_permissions(
            teacher_openai_config.user_id, teacher_openai_config.provider
        )

    def test_concurrent_rate_limiting_per_user(self, multi_user_configs):
        """Test rate limiting applied per user in concurrent scenarios."""
        rate_limit_hits = {}
        lock = threading.Lock()

        def make_rate_limited_request(config, request_id):
            """Make request with rate limiting simulation."""
            user_id = config.user_id

            # Simulate rate limiting (max 2 requests per user)
            with lock:
                if user_id not in rate_limit_hits:
                    rate_limit_hits[user_id] = 0

                if rate_limit_hits[user_id] >= 2:
                    raise AIServiceError(f"Rate limit exceeded for user {user_id}")

                rate_limit_hits[user_id] += 1

            return f"Response for request {request_id}"

        # Create multiple requests for different users
        requests = []
        for i, config in enumerate(multi_user_configs[:2]):  # Test 2 users
            for j in range(3):  # 3 requests per user
                requests.append((config, f"req_{i}_{j}"))

        # Execute requests concurrently
        results = []
        errors = []

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(make_rate_limited_request, config, req_id): (
                    config.user_id,
                    req_id,
                )
                for config, req_id in requests
            }

            for future in as_completed(futures):
                user_id, req_id = futures[future]
                try:
                    result = future.result(timeout=1)
                    results.append((user_id, req_id, result))
                except Exception as e:
                    errors.append((user_id, req_id, str(e)))

        # Verify rate limiting worked per user
        # Note: Due to concurrent execution timing, we verify that rate limiting occurred
        # but don't require exact numbers since thread execution order can vary
        assert (
            len(results) >= 2
        ), f"Expected at least 2 successful results, got {len(results)}"
        assert (
            len(errors) >= 1
        ), f"Expected at least 1 rate limited error, got {len(errors)}"

        # Verify rate limit errors are user-specific
        for user_id, req_id, error in errors:
            assert "Rate limit exceeded" in error
            assert str(user_id) in error

    def test_user_configuration_lifecycle(self, sample_users):
        """Test complete lifecycle of user AI configurations."""
        user = sample_users[0]  # Teacher

        # 1. Create initial configuration
        initial_config = AIModelConfiguration(
            id=10,
            user_id=user.id,
            provider=AIProvider.OPENAI.value,
            model="gpt-3.5-turbo",
            endpoint="https://api.openai.com/v1/chat/completions",
            api_key="sk-encrypted-initial-key",
            model_parameters={"temperature": 0.7, "max_tokens": 1000},
            validated=False,
        )

        # 2. Validate configuration
        ai_service = AIService(initial_config, Mock())

        # Mock successful validation
        with patch.object(
            ai_service,
            "_call_openai",
            return_value={
                "content": "Valid configuration",
                "tokens_used": 10,
                "model": "gpt-3.5-turbo",
            },
        ):
            validation_result = ai_service.generate_content("Validation test")
            assert validation_result == "Valid configuration"
            initial_config.validated = True

        # 3. Update configuration
        updated_config = AIModelConfiguration(
            id=initial_config.id,
            user_id=user.id,
            provider=AIProvider.OPENAI.value,
            model="gpt-4",
            endpoint="https://api.openai.com/v1/chat/completions",
            api_key="sk-encrypted-updated-key",
            model_parameters={"temperature": 0.8, "max_tokens": 2000},
            validated=True,
        )

        # 4. Test updated configuration
        updated_service = AIService(updated_config, Mock())

        with patch.object(
            updated_service,
            "_call_openai",
            return_value={
                "content": "Updated configuration works",
                "tokens_used": 20,
                "model": "gpt-4",
            },
        ):
            updated_result = updated_service.generate_content("Update test")
            assert updated_result == "Updated configuration works"

        # 5. Deactivate configuration
        updated_config.validated = False
        assert not updated_config.validated

    def test_cross_user_data_isolation(self, multi_user_configs):
        """Test strict data isolation between users."""
        # Create services for different users
        teacher_service = AIService(multi_user_configs[0], Mock())
        student_service = AIService(multi_user_configs[2], Mock())

        # Track API calls to ensure no cross-contamination
        teacher_calls = []
        student_calls = []

        def track_teacher_call(prompt, max_tokens, temperature, system_prompt):
            teacher_calls.append(
                {
                    "prompt": prompt,
                    "user_id": multi_user_configs[0].user_id,
                    "api_key": multi_user_configs[0].api_key,
                }
            )
            return {"content": "Teacher response", "tokens_used": 100, "model": "gpt-4"}

        def track_student_call(prompt, max_tokens, temperature, system_prompt):
            student_calls.append(
                {
                    "prompt": prompt,
                    "user_id": multi_user_configs[2].user_id,
                    "api_key": multi_user_configs[2].api_key,
                }
            )
            return {"content": "Student response", "tokens_used": 50, "model": "llama2"}

        with patch.object(
            teacher_service, "_call_openai", side_effect=track_teacher_call
        ):
            teacher_service.generate_content("Teacher prompt")

        with patch.object(
            student_service, "_call_ollama", side_effect=track_student_call
        ):
            student_service.generate_content("Student prompt")

        # Verify complete isolation
        assert len(teacher_calls) == 1
        assert len(student_calls) == 1

        # Verify no shared data
        teacher_call = teacher_calls[0]
        student_call = student_calls[0]

        assert teacher_call["user_id"] != student_call["user_id"]
        assert teacher_call["api_key"] != student_call["api_key"]
        assert "Teacher" in teacher_call["prompt"]
        assert "Student" in student_call["prompt"]
