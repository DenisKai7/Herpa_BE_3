import time
from collections import defaultdict, deque
from app.core.exceptions import AppError


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        now = time.monotonic()
        events = self._events[key]
        while events and now - events[0] > window_seconds:
            events.popleft()
        if len(events) >= limit:
            raise AppError("RATE_LIMITED", "Batas permintaan tercapai. Coba kembali sebentar lagi.", 429)
        events.append(now)


rate_limiter = InMemoryRateLimiter()
