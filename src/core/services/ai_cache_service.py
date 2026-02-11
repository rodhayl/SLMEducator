"""
AI Response Cache Service

Provides caching for AI responses to reduce API costs and improve performance.
Implements TTL-based expiration and database-backed persistence.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import weakref

Base = declarative_base()


class CachedResponse(Base):
    """Model for cached AI responses"""

    __tablename__ = "ai_response_cache"

    id = Column(Integer, primary_key=True)
    prompt_hash = Column(String(64), unique=True, index=True, nullable=False)
    prompt_text = Column(Text, nullable=False)  # Store for debugging
    response_text = Column(Text, nullable=False)
    model = Column(String(100), nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    hit_count = Column(Integer, default=0, nullable=False)


class AICacheService:
    """Service for caching AI responses"""

    def __init__(
        self,
        database_url: str = "sqlite:///slm_educator.db",
        default_ttl_seconds: int = 3600,
    ):
        """
        Initialize AI cache service

        Args:
            database_url: Database connection URL
            default_ttl_seconds: Default time-to-live for cache entries (default: 1 hour)
        """
        self.logger = logging.getLogger(__name__)
        self.default_ttl = default_ttl_seconds

        # Create engine and session
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        try:
            weakref.finalize(self, self.engine.dispose)
        except Exception:
            pass

        self.logger.info(
            f"AI Cache Service initialized with TTL={default_ttl_seconds}s"
        )

    def _generate_cache_key(self, prompt: str, model: str, **kwargs) -> str:
        """
        Generate a cache key from prompt and parameters

        Args:
            prompt: The AI prompt
            model: Model name
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            SHA-256 hash of the cache key
        """
        # Create a deterministic string from all parameters
        cache_data = {"prompt": prompt, "model": model, **kwargs}

        # Sort keys for deterministic hashing
        cache_str = json.dumps(cache_data, sort_keys=True)

        # Generate SHA-256 hash
        return hashlib.sha256(cache_str.encode("utf-8")).hexdigest()

    def get(self, prompt: str, model: str, **kwargs) -> Optional[str]:
        """
        Get cached response if available and not expired

        Args:
            prompt: The AI prompt
            model: Model name
            **kwargs: Additional parameters

        Returns:
            Cached response text or None if not found/expired
        """
        cache_key = self._generate_cache_key(prompt, model, **kwargs)

        with self.SessionLocal() as session:
            cached = (
                session.query(CachedResponse).filter_by(prompt_hash=cache_key).first()
            )

            if not cached:
                self.logger.debug(f"Cache miss for key: {cache_key[:16]}...")
                return None

            now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
            cached_expires_opt: Optional[datetime] = cached.expires_at
            if cached_expires_opt is None:
                session.delete(cached)
                session.commit()
                return None

            cached_expires = cached_expires_opt
            if cached_expires.tzinfo is not None:
                cached_expires = cached_expires.astimezone(timezone.utc).replace(
                    tzinfo=None
                )

            if now_naive > cached_expires:
                self.logger.debug(f"Cache expired for key: {cache_key[:16]}...")
                session.delete(cached)
                session.commit()
                return None

            hit_count = cached.hit_count or 0
            cached.hit_count = hit_count + 1
            session.commit()

            self.logger.info(
                f"Cache hit for key: {cache_key[:16]}... (hits: {cached.hit_count})"
            )
            return cached.response_text

    def set(
        self,
        prompt: str,
        response: str,
        model: str,
        ttl_seconds: Optional[int] = None,
        **kwargs,
    ) -> None:
        """
        Cache an AI response

        Args:
            prompt: The AI prompt
            response: The AI response to cache
            model: Model name
            ttl_seconds: Time-to-live in seconds (uses default if None)
            **kwargs: Additional parameters
        """
        cache_key = self._generate_cache_key(prompt, model, **kwargs)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).replace(
            tzinfo=None
        )

        with self.SessionLocal() as session:
            # Check if already exists
            existing = (
                session.query(CachedResponse).filter_by(prompt_hash=cache_key).first()
            )

            if existing:
                # Update existing entry
                existing.response_text = response
                existing.expires_at = expires_at
                existing.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
                self.logger.debug(f"Updated cache for key: {cache_key[:16]}...")
            else:
                # Create new entry
                cached = CachedResponse(
                    prompt_hash=cache_key,
                    prompt_text=prompt[:500],  # Store truncated for debugging
                    response_text=response,
                    model=model,
                    expires_at=expires_at,
                )
                session.add(cached)
                self.logger.debug(f"Cached response for key: {cache_key[:16]}...")

            session.commit()

    def clear_expired(self) -> int:
        """
        Remove all expired cache entries

        Returns:
            Number of entries removed
        """
        with self.SessionLocal() as session:
            now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
            count = (
                session.query(CachedResponse)
                .filter(CachedResponse.expires_at < now_naive)
                .delete()
            )
            session.commit()

            if count > 0:
                self.logger.info(f"Cleared {count} expired cache entries")

            return count

    def clear_all(self) -> int:
        """
        Clear all cache entries

        Returns:
            Number of entries removed
        """
        with self.SessionLocal() as session:
            count = session.query(CachedResponse).delete()
            session.commit()

            self.logger.info(f"Cleared all {count} cache entries")
            return count

    def close(self):
        """Close engine and release resources for the cache service."""
        try:
            if hasattr(self, "SessionLocal") and self.SessionLocal:
                # SQLAlchemy sessionmaker doesn't have a close_all; but sessions are closed by context manager
                pass
        except Exception:
            pass
        try:
            if hasattr(self, "engine") and self.engine:
                self.engine.dispose()
        except Exception:
            pass

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache statistics
        """
        with self.SessionLocal() as session:
            total = session.query(CachedResponse).count()
            now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
            expired = (
                session.query(CachedResponse)
                .filter(CachedResponse.expires_at < now_naive)
                .count()
            )

            # Calculate total hits
            total_hits = (
                session.query(CachedResponse)
                .with_entities(CachedResponse.hit_count)
                .all()
            )

            hit_sum = sum(h[0] for h in total_hits)

            return {
                "total_entries": total,
                "active_entries": total - expired,
                "expired_entries": expired,
                "total_hits": hit_sum,
                "hit_rate": f"{(hit_sum / max(total, 1) * 100):.1f}%",
            }


# Global instance
_cache_service: Optional[AICacheService] = None


def get_cache_service(
    database_url: str = "sqlite:///slm_educator.db", ttl_seconds: int = 3600
) -> AICacheService:
    """Get the global cache service instance"""
    global _cache_service
    if _cache_service is None:
        _cache_service = AICacheService(database_url, ttl_seconds)
    return _cache_service
