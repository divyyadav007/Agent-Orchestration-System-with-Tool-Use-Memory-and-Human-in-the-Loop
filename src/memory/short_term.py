import logging
import json
import os
from typing import Optional, Dict, Any
import redis

# Initialize module logger
logger = logging.getLogger(__name__)

class ShortTermMemory:
    """Manages short-term agent states, leveraging Redis with an in-memory dict fallback."""
    
    def __init__(self) -> None:
        self.redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.ttl: int = int(os.getenv("REDIS_TTL", "3600"))
        self._client: Optional[redis.Redis] = None
        self._local_cache: Dict[str, str] = {}
        self._use_fallback: bool = False

    @property
    def client(self) -> Optional[redis.Redis]:
        """Returns the Redis connection client. 
        
        If connection fails or fallback has been flagged, returns None.
        """
        if self._use_fallback:
            return None
            
        if self._client is None:
            try:
                # decoding responses simplifies string manipulations
                self._client = redis.from_url(self.redis_url, decode_responses=True)
                # Test connection immediately
                self._client.ping()
                logger.info(f"Connected to Redis short-term store at {self.redis_url}")
            except Exception as e:
                logger.warning(f"Could not connect to Redis at {self.redis_url} ({e}). Falling back to local in-memory storage.")
                self._use_fallback = True
                self._client = None
                
        return self._client

    def save(self, task_id: str, data: Dict[str, Any]) -> None:
        """Saves task state snapshot to Redis (or fallback local dict).

        Args:
            task_id (str): The unique task configuration ID.
            data (Dict[str, Any]): State data snapshot to serialize and save.
        """
        key = f"task:{task_id}"
        serialized = json.dumps(data)
        client = self.client
        
        if client is not None:
            try:
                client.setex(key, self.ttl, serialized)
                logger.debug(f"Saved state to Redis for '{key}'")
                return
            except Exception as e:
                logger.warning(f"Redis write error ({e}). Falling back to local in-memory storage.")
                self._use_fallback = True
                
        # Local fallback execution
        self._local_cache[key] = serialized
        logger.debug(f"Saved state to local memory for '{key}'")

    def load(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Loads a task state snapshot.

        Args:
            task_id (str): The task ID.

        Returns:
            Optional[Dict[str, Any]]: The parsed state dict if found, else None.
        """
        key = f"task:{task_id}"
        client = self.client
        raw: Optional[str] = None
        
        if client is not None:
            try:
                raw = client.get(key)
                logger.debug(f"Loaded state from Redis for '{key}': {'found' if raw else 'not found'}")
            except Exception as e:
                logger.warning(f"Redis read error ({e}). Falling back to local in-memory storage.")
                self._use_fallback = True
                
        if self._use_fallback or client is None:
            raw = self._local_cache.get(key)
            logger.debug(f"Loaded state from local memory for '{key}': {'found' if raw else 'not found'}")
            
        return json.loads(raw) if raw else None

    def delete(self, task_id: str) -> None:
        """Deletes a task state snapshot.

        Args:
            task_id (str): The task ID.
        """
        key = f"task:{task_id}"
        client = self.client
        
        if client is not None:
            try:
                client.delete(key)
                logger.debug(f"Deleted state from Redis for '{key}'")
                return
            except Exception as e:
                logger.warning(f"Redis delete error ({e}). Falling back to local in-memory storage.")
                self._use_fallback = True
                
        if key in self._local_cache:
            del self._local_cache[key]
        logger.debug(f"Deleted state from local memory for '{key}'")


# Global singleton short-term memory instance
short_term_memory = ShortTermMemory()