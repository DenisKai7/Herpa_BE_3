import time
from typing import Any


class AsyncMemoryTTLCache:
    def __init__(self, max_size: int = 256):
        self.max_size = max_size
        self._cache: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        if key not in self._cache:
            return None
        val, expiry = self._cache[key]
        if time.monotonic() > expiry:
            self._cache.pop(key, None)
            return None
        return val

    def set(self, key: str, val: Any, ttl_seconds: int) -> None:
        if len(self._cache) >= self.max_size:
            # Evict oldest entry
            try:
                first = next(iter(self._cache))
                self._cache.pop(first, None)
            except StopIteration:
                pass
        self._cache[key] = (val, time.monotonic() + ttl_seconds)

    def clear(self) -> None:
        self._cache.clear()
