import json
import logging
import os
from typing import Any, Dict, Optional

import redis

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """Short-Term Memory Manager: Caches transient subtask state graph snapshots.

    Why Redis with local fallback: Redis provides fast state persistence across
    microservices. If Redis is unavailable locally, it automatically falls back
    to a python dict cache so developers can run the system without Docker setup.
    """

    def __init__(self) -> None:
        self.redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.ttl: int = int(os.getenv("REDIS_TTL", "3600"))
        self._client: Optional[redis.Redis] = None
        self._local_cache: Dict[str, str] = {}
        self._use_fallback: bool = False

    @property
    def client(self) -> Optional[redis.Redis]:
        """Lazy-connects to Redis; switches permanently to local dict fallback if connection fails."""
        if self._use_fallback:
            return None

        if self._client is None:
            try:
                self._client = redis.from_url(self.redis_url, decode_responses=True)
                self._client.ping()
                logger.info(f"Connected to Redis at {self.redis_url}")
            except Exception as e:
                logger.warning(f"Redis unavailable ({e}). Falling back to in-memory dictionary storage.")
                self._use_fallback = True
                self._client = None

        return self._client

    def save(self, task_id: str, data: Dict[str, Any]) -> None:
        """Saves serialized task state snapshot."""
        key = f"task:{task_id}"
        serialized = json.dumps(data)
        client = self.client

        if client is not None:
            try:
                client.setex(key, self.ttl, serialized)
                return
            except Exception as e:
                logger.warning(f"Redis write error ({e}). Using local fallback.")
                self._use_fallback = True

        self._local_cache[key] = serialized

    def load(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Loads and deserializes task state snapshot."""
        key = f"task:{task_id}"
        client = self.client
        raw: Optional[str] = None

        if client is not None:
            try:
                raw = client.get(key)
            except Exception as e:
                logger.warning(f"Redis read error ({e}). Using local fallback.")
                self._use_fallback = True

        if self._use_fallback or client is None:
            raw = self._local_cache.get(key)

        return json.loads(raw) if raw else None

    def delete(self, task_id: str) -> None:
        """Deletes task state snapshot."""
        key = f"task:{task_id}"
        client = self.client

        if client is not None:
            try:
                client.delete(key)
                return
            except Exception as e:
                logger.warning(f"Redis delete error ({e}). Using local fallback.")
                self._use_fallback = True

        self._local_cache.pop(key, None)


short_term_memory = ShortTermMemory()
