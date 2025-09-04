"""
Simple async cache implementation for Sanic app
"""
import asyncio
from typing import Any, Optional


class AsyncSimpleCache:
    """Simple in-memory cache for async operations"""
    
    def __init__(self):
        self._cache = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            return self._cache.get(key)
    
    async def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Set value in cache"""
        async with self._lock:
            self._cache[key] = value
            # Note: timeout handling could be implemented with asyncio.create_task
    
    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        async with self._lock:
            self._cache.pop(key, None)
    
    async def clear(self) -> None:
        """Clear all cache"""
        async with self._lock:
            self._cache.clear()


# Global cache instance
sanic_cache = AsyncSimpleCache()