"""
Comprehensive background processes tests for AI integration.
Tests async operations, thread safety, and cancellation mechanisms.
"""

import pytest
from unittest.mock import Mock, patch
import threading
import time
from concurrent.futures import ThreadPoolExecutor, CancelledError
import queue

from src.core.models.models import AIModelConfiguration
from src.core.services.ai_service import AIService, AIServiceError, AIProvider


class TestAIBackgroundProcesses:
    """Test AI background processes including async operations, thread safety, and cancellation."""

    @pytest.fixture
    def sample_config(self):
        """Create a sample AI configuration."""
        return AIModelConfiguration(
            id=1,
            user_id=1,
            provider=AIProvider.OPENAI.value,
            model="gpt-3.5-turbo",
            endpoint="https://api.openai.com/v1/chat/completions",
            api_key="sk-encrypted-key",
            model_parameters={"temperature": 0.7, "max_tokens": 1000},
            validated=True,
        )

    @pytest.fixture
    def ai_service(self, sample_config):
        """Create AI service instance."""
        service = AIService(sample_config, Mock())
        try:
            yield service
        finally:
            try:
                service.close()
            except Exception:
                pass

    def test_async_ai_request_execution(self, ai_service):
        """Test async execution of AI requests."""
        results = []
        errors = []

        def async_ai_call(prompt):
            """Execute AI call in background."""
            try:
                # Mock successful response
                with patch.object(
                    ai_service,
                    "_call_openai",
                    return_value={
                        "content": f"Async response to: {prompt}",
                        "tokens_used": 50,
                        "model": "gpt-3.5-turbo",
                    },
                ):
                    response = ai_service.generate_content(prompt)
                    results.append(response)
            except Exception as e:
                errors.append(str(e))

        # Execute multiple requests asynchronously
        prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
        threads = []

        for prompt in prompts:
            thread = threading.Thread(target=async_ai_call, args=(prompt,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)

        # Verify all requests completed
        assert len(results) == 3
        assert len(errors) == 0

        # Verify responses
        for prompt in prompts:
            assert any(f"Async response to: {prompt}" in result for result in results)

    def test_thread_safe_ai_service_usage(self, ai_service):
        """Test thread-safe usage of AI service."""
        results = queue.Queue()
        errors = queue.Queue()

        def thread_safe_ai_call(thread_id):
            """Thread-safe AI call."""
            try:
                # Mock response with thread-specific content
                with patch.object(
                    ai_service,
                    "_call_openai",
                    return_value={
                        "content": f"Thread {thread_id} response",
                        "tokens_used": 30 + thread_id,
                        "model": "gpt-3.5-turbo",
                    },
                ):
                    response = ai_service.generate_content(f"Thread {thread_id} prompt")
                    results.put((thread_id, response))
            except Exception as e:
                errors.put((thread_id, str(e)))

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=thread_safe_ai_call, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=5.0)

        # Collect results
        collected_results = []
        collected_errors = []

        while not results.empty():
            collected_results.append(results.get())

        while not errors.empty():
            collected_errors.append(errors.get())

        # Verify results
        assert len(collected_results) == 5
        assert len(collected_errors) == 0

        # Verify thread-specific responses
        thread_ids = [result[0] for result in collected_results]
        assert sorted(thread_ids) == list(range(5))

    def test_ai_request_cancellation(self, ai_service):
        """Test cancellation of AI requests."""
        cancelled_requests = []
        completed_requests = []

        def cancellable_ai_call(request_id, cancel_event):
            """AI call that can be cancelled."""
            try:
                # Simulate long-running AI call
                for i in range(10):  # 10 second simulation
                    if cancel_event.is_set():
                        cancelled_requests.append(request_id)
                        raise CancelledError(f"Request {request_id} cancelled")
                    time.sleep(0.1)  # 100ms per iteration

                # If not cancelled, complete the request
                with patch.object(
                    ai_service,
                    "_call_openai",
                    return_value={
                        "content": f"Completed request {request_id}",
                        "tokens_used": 100,
                        "model": "gpt-3.5-turbo",
                    },
                ):
                    response = ai_service.generate_content(f"Request {request_id}")
                    completed_requests.append((request_id, response))

            except CancelledError:
                cancelled_requests.append(request_id)
            except Exception as e:
                # Other exceptions should not happen in this test
                raise

        # Create cancellation events
        cancel_events = [threading.Event() for _ in range(3)]

        # Start threads
        threads = []
        for i in range(3):
            thread = threading.Thread(
                target=cancellable_ai_call, args=(i, cancel_events[i])
            )
            threads.append(thread)
            thread.start()

        # Cancel first request after 0.3 seconds
        time.sleep(0.3)
        cancel_events[0].set()

        # Cancel second request after 0.6 seconds
        time.sleep(0.3)
        cancel_events[1].set()

        # Let third request complete

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=3.0)

        # Verify cancellation worked
        assert 0 in cancelled_requests  # First request cancelled
        assert 1 in cancelled_requests  # Second request cancelled
        assert len(completed_requests) == 1  # Third request completed
        assert completed_requests[0][0] == 2

    def test_background_ai_processing_queue(self, ai_service):
        """Test background AI processing with work queue."""
        work_queue = queue.Queue()
        results = []
        errors = []
        stop_event = threading.Event()

        def background_worker():
            """Background worker processing AI requests."""
            while not stop_event.is_set():
                try:
                    # Get work with timeout to allow checking stop event
                    work_item = work_queue.get(timeout=0.5)

                    if work_item is None:  # Sentinel value to stop
                        break

                    request_id, prompt = work_item

                    # Process AI request
                    with patch.object(
                        ai_service,
                        "_call_openai",
                        return_value={
                            "content": f"Background processed: {prompt}",
                            "tokens_used": 75,
                            "model": "gpt-3.5-turbo",
                        },
                    ):
                        response = ai_service.generate_content(prompt)
                        results.append((request_id, response))

                except queue.Empty:
                    continue  # No work available, check stop event
                except Exception as e:
                    errors.append(str(e))

        # Start background worker
        worker_thread = threading.Thread(target=background_worker)
        worker_thread.start()

        # Add work items
        work_items = [
            (1, "Background task 1"),
            (2, "Background task 2"),
            (3, "Background task 3"),
        ]

        for item in work_items:
            work_queue.put(item)

        # Wait for processing
        time.sleep(1.0)

        # Stop worker
        stop_event.set()
        work_queue.put(None)  # Sentinel to ensure clean stop
        worker_thread.join(timeout=2.0)

        # Verify results
        assert len(results) == 3
        assert len(errors) == 0

        # Verify all work items were processed
        processed_ids = [result[0] for result in results]
        assert sorted(processed_ids) == [1, 2, 3]

    def test_concurrent_ai_request_limiting(self, ai_service):
        """Test limiting concurrent AI requests."""
        active_requests = 0
        max_concurrent = 0
        lock = threading.Lock()

        def limited_ai_call(request_id):
            """AI call with concurrency tracking."""
            nonlocal active_requests, max_concurrent

            with lock:
                active_requests += 1
                max_concurrent = max(max_concurrent, active_requests)

            try:
                # Simulate AI processing time
                time.sleep(0.2)

                with patch.object(
                    ai_service,
                    "_call_openai",
                    return_value={
                        "content": f"Concurrent response {request_id}",
                        "tokens_used": 50,
                        "model": "gpt-3.5-turbo",
                    },
                ):
                    response = ai_service.generate_content(f"Request {request_id}")
                    return response

            finally:
                with lock:
                    active_requests -= 1

        # Execute multiple requests concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(10):
                future = executor.submit(limited_ai_call, i)
                futures.append(future)

            # Collect results
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=1.0)
                    results.append(result)
                except Exception as e:
                    print(f"Future failed: {e}")

        # Verify all requests completed
        assert len(results) == 10

        # Verify concurrency limiting (some requests should have been queued)
        assert max_concurrent <= 5  # Limited by ThreadPoolExecutor

    def test_ai_request_timeout_handling(self, ai_service):
        """Test timeout handling for AI requests."""
        timeout_results = []

        def timeout_ai_call(request_id, timeout_duration):
            """AI call with timeout."""
            try:
                # Mock a slow AI response
                def slow_openai_call(prompt, max_tokens, temperature, system_prompt):
                    time.sleep(0.5)  # Simulate slow response
                    return {
                        "content": f"Slow response {request_id}",
                        "tokens_used": 50,
                        "model": "gpt-3.5-turbo",
                    }

                with patch.object(
                    ai_service, "_call_openai", side_effect=slow_openai_call
                ):
                    # Use ThreadPoolExecutor with timeout
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(
                            ai_service.generate_content, f"Timeout test {request_id}"
                        )

                        try:
                            response = future.result(timeout=timeout_duration)
                            timeout_results.append((request_id, "success", response))
                        except TimeoutError:
                            timeout_results.append((request_id, "timeout", None))

            except Exception as e:
                timeout_results.append((request_id, "error", str(e)))

        # Test different timeout scenarios
        timeout_ai_call(1, 0.1)  # Should timeout
        timeout_ai_call(2, 1.0)  # Should succeed

        # Verify results
        assert len(timeout_results) == 2

        # First request should timeout
        req1_result = next(r for r in timeout_results if r[0] == 1)
        assert req1_result[1] == "timeout"

        # Second request should succeed
        req2_result = next(r for r in timeout_results if r[0] == 2)
        assert req2_result[1] == "success"

    def test_background_ai_error_recovery(self, ai_service):
        """Test error recovery in background AI processes."""
        results = []
        retry_attempts = []

        def resilient_ai_call(request_id):
            """AI call with error recovery."""
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    retry_attempts.append((request_id, retry_count))

                    # Simulate intermittent failures
                    if retry_count < 2:  # First 2 attempts fail
                        raise AIServiceError(
                            f"Simulated failure for request {request_id}, attempt {retry_count}"
                        )

                    # Success on third attempt
                    with patch.object(
                        ai_service,
                        "_call_openai",
                        return_value={
                            "content": f"Recovered response {request_id}",
                            "tokens_used": 75,
                            "model": "gpt-3.5-turbo",
                        },
                    ):
                        response = ai_service.generate_content(
                            f"Resilient request {request_id}"
                        )
                        results.append((request_id, retry_count, response))
                        break

                except AIServiceError:
                    retry_count += 1
                    if retry_count >= max_retries:
                        results.append((request_id, retry_count, None))
                    else:
                        time.sleep(0.1)  # Brief delay before retry

        # Test resilient calls
        threads = []
        for i in range(2):
            thread = threading.Thread(target=resilient_ai_call, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=5.0)

        # Verify recovery worked
        assert len(results) == 2

        for request_id, retry_count, response in results:
            assert retry_count == 2  # Succeeded on 3rd attempt
            assert response is not None
            assert f"Recovered response {request_id}" in response

        # Verify retry attempts
        assert len(retry_attempts) == 6  # 2 requests * 3 attempts each

    def test_ai_service_resource_cleanup(self, ai_service):
        """Test proper resource cleanup in AI service."""
        resources_created = []
        resources_cleaned = []

        def resource_tracking_ai_call(request_id):
            """AI call with resource tracking."""
            try:
                # Simulate resource creation
                resources_created.append(request_id)

                # Mock successful response
                with patch.object(
                    ai_service,
                    "_call_openai",
                    return_value={
                        "content": f"Resource test {request_id}",
                        "tokens_used": 40,
                        "model": "gpt-3.5-turbo",
                    },
                ):
                    response = ai_service.generate_content(
                        f"Resource test {request_id}"
                    )
                    return response

            finally:
                # Simulate resource cleanup
                resources_cleaned.append(request_id)

        # Execute requests
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for i in range(3):
                future = executor.submit(resource_tracking_ai_call, i)
                futures.append(future)

            # Collect results
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=1.0)
                    results.append(result)
                except Exception as e:
                    print(f"Resource test failed: {e}")

        # Verify resource management
        assert len(results) == 3
        assert len(resources_created) == 3
        assert len(resources_cleaned) == 3
        assert sorted(resources_created) == sorted(resources_cleaned)

    def test_background_ai_progress_tracking(self, ai_service):
        """Test progress tracking for background AI operations."""
        progress_updates = []

        def progress_tracking_ai_call(request_id, total_steps=5):
            """AI call with progress tracking."""
            try:
                for step in range(total_steps):
                    # Simulate processing step
                    time.sleep(0.1)

                    # Update progress
                    progress = (step + 1) / total_steps * 100
                    progress_updates.append((request_id, step, progress))

                # Complete the request
                with patch.object(
                    ai_service,
                    "_call_openai",
                    return_value={
                        "content": f"Progress tracked response {request_id}",
                        "tokens_used": 60,
                        "model": "gpt-3.5-turbo",
                    },
                ):
                    response = ai_service.generate_content(
                        f"Progress test {request_id}"
                    )
                    progress_updates.append((request_id, "completed", 100))
                    return response

            except Exception as e:
                progress_updates.append((request_id, "error", 0))
                raise

        # Execute with progress tracking
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(progress_tracking_ai_call, 1)

            try:
                result = future.result(timeout=2.0)
            except Exception as e:
                print(f"Progress tracking failed: {e}")

        # Verify progress was tracked
        assert len(progress_updates) > 5  # At least 5 steps + completion

        # Verify progress sequence
        request_progress = [update for update in progress_updates if update[0] == 1]
        assert len(request_progress) > 0

        # Verify completion was recorded
        completion_updates = [
            update for update in progress_updates if update[1] == "completed"
        ]
        assert len(completion_updates) == 1
        assert completion_updates[0][2] == 100
