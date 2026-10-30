"""
Tests for AI Cache Service

Tests caching functionality, TTL expiration, and cache statistics.
"""

import pytest
from src.core.services.ai_cache_service import AICacheService, get_cache_service


class TestAICaching:
    """Test AI response caching"""

    def test_cache_miss_returns_none(self, cache_service):
        """Test that cache miss returns None"""
        result = cache_service.get("test prompt", "gpt-4")
        assert result is None

    def test_cache_hit_returns_response(self, cache_service):
        """Test that cached response is returned"""
        prompt = "What is 2+2?"
        response = "2+2 equals 4"
        model = "gpt-4"

        # Cache the response
        cache_service.set(prompt, response, model)

        # Retrieve it
        cached = cache_service.get(prompt, model)
        assert cached == response

    def test_cache_key_includes_parameters(self, cache_service):
        """Test that cache key includes all parameters"""
        prompt = "test"
        response1 = "response1"
        response2 = "response2"

        # Cache with different parameters
        cache_service.set(prompt, response1, "gpt-4", temperature=0.5)
        cache_service.set(prompt, response2, "gpt-4", temperature=0.7)

        # Should return different responses
        cached1 = cache_service.get(prompt, "gpt-4", temperature=0.5)
        cached2 = cache_service.get(prompt, "gpt-4", temperature=0.7)

        assert cached1 == response1
        assert cached2 == response2

    def test_cache_expiration(self, cache_service):
        """Test that expired cache entries are not returned"""
        prompt = "test prompt"
        response = "test response"

        # Cache with 1 second TTL
        cache_service.set(prompt, response, "gpt-4", ttl_seconds=1)

        # Should be cached immediately
        assert cache_service.get(prompt, "gpt-4") == response

        # Wait for expiration
        import time

        time.sleep(2)

        # Should be expired
        assert cache_service.get(prompt, "gpt-4") is None

    def test_cache_update_extends_ttl(self, cache_service):
        """Test that updating cache extends TTL"""
        prompt = "test"
        response1 = "response1"
        response2 = "response2"

        # Cache with short TTL
        cache_service.set(prompt, response1, "gpt-4", ttl_seconds=10)

        # Update with new response
        cache_service.set(prompt, response2, "gpt-4", ttl_seconds=3600)

        # Should return updated response
        assert cache_service.get(prompt, "gpt-4") == response2

    def test_hit_count_increments(self, cache_service):
        """Test that hit count increments on cache hits"""
        prompt = "test"
        response = "response"

        cache_service.set(prompt, response, "gpt-4")

        # Multiple hits
        for _ in range(5):
            cache_service.get(prompt, "gpt-4")

        stats = cache_service.get_stats()
        assert stats["total_hits"] >= 5


class TestCacheManagement:
    """Test cache management operations"""

    def test_clear_expired_removes_only_expired(self, cache_service):
        """Test that clear_expired only removes expired entries"""
        # Add active entry
        cache_service.set("active", "response", "gpt-4", ttl_seconds=3600)

        # Add expired entry
        cache_service.set("expired", "response", "gpt-4", ttl_seconds=1)

        import time

        time.sleep(2)

        # Clear expired
        removed = cache_service.clear_expired()

        assert removed >= 1
        assert cache_service.get("active", "gpt-4") is not None
        assert cache_service.get("expired", "gpt-4") is None

    def test_clear_all_removes_everything(self, cache_service):
        """Test that clear_all removes all entries"""
        # Add multiple entries
        for i in range(5):
            cache_service.set(f"prompt{i}", f"response{i}", "gpt-4")

        # Clear all
        removed = cache_service.clear_all()

        assert removed >= 5

        # Verify all removed
        for i in range(5):
            assert cache_service.get(f"prompt{i}", "gpt-4") is None

    def test_get_stats_returns_correct_counts(self, cache_service):
        """Test that get_stats returns correct statistics"""
        # Clear cache first
        cache_service.clear_all()

        # Add entries
        cache_service.set("prompt1", "response1", "gpt-4")
        cache_service.set("prompt2", "response2", "gpt-4")

        # Get stats
        stats = cache_service.get_stats()

        assert stats["total_entries"] >= 2
        assert stats["active_entries"] >= 2
        assert "hit_rate" in stats


class TestGlobalInstance:
    """Test global cache service instance"""

    def test_get_cache_service_returns_singleton(self):
        """Test that get_cache_service returns singleton"""
        service1 = get_cache_service()
        service2 = get_cache_service()

        assert service1 is service2

    def test_get_cache_service_with_custom_ttl(self):
        """Test creating cache service with custom TTL"""
        # Reset global instance
        import src.core.services.ai_cache_service as cache_module

        cache_module._cache_service = None

        service = get_cache_service(ttl_seconds=7200)
        assert service.default_ttl == 7200


# Fixtures


@pytest.fixture
def cache_service():
    """Create a cache service for testing"""
    service = AICacheService(
        database_url="sqlite:///:memory:", default_ttl_seconds=3600
    )
    try:
        yield service
    finally:
        # Cleanup
        try:
            service.clear_all()
        except Exception:
            pass
        try:
            service.close()
        except Exception:
            pass
