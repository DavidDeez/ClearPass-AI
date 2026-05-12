"""
Module 7 — Redis Cache Layer (Layer 4)
========================================
Caches ClearPass verdicts in Redis keyed by SHA-256 hash of the BVN.
TTL is 6 hours (21 600 s). All Redis errors are caught gracefully —
a cache miss simply means the pipeline runs from scratch.
"""

import hashlib
import json
import logging
import os
from typing import Any

import redis

logger = logging.getLogger("clearpass.cache")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = 21_600  # 6 hours in seconds

_pool: redis.ConnectionPool | None = None
_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    """Lazy-initialise Redis client with connection pooling."""
    global _pool, _client
    if _client is None:
        _pool = redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)
        _client = redis.Redis(connection_pool=_pool)
        logger.info("Redis client initialised — %s", REDIS_URL)
    return _client


def _cache_key(bvn: str) -> str:
    """Deterministic cache key from BVN."""
    return f"verdict:{hashlib.sha256(bvn.encode()).hexdigest()}"


def get_cached_verdict(bvn: str) -> dict[str, Any] | None:
    """
    Retrieve a cached verdict for the given BVN.
    Returns None on cache miss or connection error.
    """
    try:
        client = _get_client()
        raw = client.get(_cache_key(bvn))
        if raw is None:
            logger.debug("Cache MISS for BVN %s", bvn[:6])
            return None
        logger.info("Cache HIT for BVN %s", bvn[:6])
        return json.loads(raw)
    except redis.RedisError as exc:
        logger.warning("Redis read error (non-fatal): %s", exc)
        return None
    except Exception as exc:
        logger.warning("Unexpected cache read error: %s", exc)
        return None


def cache_verdict(bvn: str, verdict: dict[str, Any]) -> None:
    """
    Store a verdict in Redis with TTL.
    Silently fails on connection errors.
    """
    try:
        client = _get_client()
        client.setex(
            name=_cache_key(bvn),
            time=CACHE_TTL,
            value=json.dumps(verdict),
        )
        logger.info("Cached verdict for BVN %s (TTL=%ds)", bvn[:6], CACHE_TTL)
    except redis.RedisError as exc:
        logger.warning("Redis write error (non-fatal): %s", exc)
    except Exception as exc:
        logger.warning("Unexpected cache write error: %s", exc)
