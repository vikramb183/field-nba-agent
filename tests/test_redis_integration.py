"""Runs only when REDIS_TEST_URL is set (GitHub Actions starts a Redis service for it)."""
import os
import time

import pytest

pytestmark = pytest.mark.skipif(not os.getenv("REDIS_TEST_URL"), reason="REDIS_TEST_URL not set")


def test_redis_cache_round_trip_and_ttl():
    from app.cache import RedisCache

    cache = RedisCache(os.environ["REDIS_TEST_URL"])
    cache.set("nba:test:ttl", [{"action_id": "x"}], ttl_seconds=1)
    assert cache.get("nba:test:ttl") == [{"action_id": "x"}]
    time.sleep(1.5)
    assert cache.get("nba:test:ttl") is None
