import time
from typing import Optional, Any

class CacheService:
    def __init__(self):
        self._cache: dict = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            val, expire = self._cache[key]
            if time.time() < expire:
                return val
            del self._cache[key]
        return None

    def set(self, key: str, val: Any, ttl: int = 900):
        self._cache[key] = (val, time.time() + ttl)

cache_service = CacheService()