"""Response cache: Redis in production, an in-memory TTL cache otherwise."""
from __future__ import annotations

import json
import time
from typing import Protocol


class Cache(Protocol):
    def get(self, key: str) -> dict | list | None: ...

    def set(self, key: str, value: dict | list, ttl_seconds: int) -> None: ...

    def clear(self) -> None: ...


class InMemoryCache:
    def __init__(self) -> None:
        self._data: dict[str, tuple[float, str]] = {}

    def get(self, key: str):
        item = self._data.get(key)
        if not item:
            return None
        expires_at, payload = item
        if time.monotonic() > expires_at:
            self._data.pop(key, None)
            return None
        return json.loads(payload)

    def set(self, key: str, value, ttl_seconds: int) -> None:
        self._data[key] = (time.monotonic() + ttl_seconds, json.dumps(value))
    
    def clear(self) -> None:
        self._data.clear()


class RedisCache:
    def __init__(self, url: str) -> None:
        import redis  # imported lazily so tests don't need a server

        self._client = redis.Redis.from_url(url, decode_responses=True)

    def get(self, key: str):
        payload = self._client.get(key)
        return json.loads(payload) if payload else None

    def set(self, key: str, value, ttl_seconds: int) -> None:
        self._client.set(key, json.dumps(value), ex=ttl_seconds)
        
    def clear(self) -> None:
        # Only delete this app's keys, not everything in Redis.
        for key in self._client.scan_iter("nba:*"):
            self._client.delete(key)
