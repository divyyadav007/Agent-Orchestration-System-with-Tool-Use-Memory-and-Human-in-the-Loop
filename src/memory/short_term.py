import redis
import json
import os
from typing import Optional, Dict, Any

class ShortTermMemory:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.ttl = int(os.getenv("REDIS_TTL", 3600))
        self.client = redis.from_url(self.redis_url, decode_responses=True)
    
    def save(self, task_id: str, data: Dict[str, Any]):
        key = f"task:{task_id}"
        self.client.setex(key, self.ttl, json.dumps(data))
    
    def load(self, task_id: str) -> Optional[Dict[str, Any]]:
        key = f"task:{task_id}"
        raw = self.client.get(key)
        return json.loads(raw) if raw else None
    
    def delete(self, task_id: str):
        self.client.delete(f"task:{task_id}")

# Singleton
short_term_memory = ShortTermMemory()