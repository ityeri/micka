import asyncio
import time


class AsyncClock:
    """Async counterpart of pygame.time.Clock, used to cap a render loop's frame rate."""

    def __init__(self) -> None:
        self._last_tick: float = time.perf_counter()
        self._raw_time_ms: float = 0.0
        self._time_ms: float = 0.0

        self._fps: float = 0.0
        self._fps_count: int = 0
        self._fps_tick: float = self._last_tick

    async def tick(self, fps: float = 0) -> float:
        now = time.perf_counter()
        self._raw_time_ms = (now - self._last_tick) * 1000

        if fps > 0:
            remaining = 1 / fps - (now - self._last_tick)
            if remaining > 0:
                await asyncio.sleep(remaining)
                now = time.perf_counter()

        self._time_ms = (now - self._last_tick) * 1000
        self._last_tick = now

        self._fps_count += 1
        elapsed_since_fps_tick = now - self._fps_tick
        if elapsed_since_fps_tick >= 1:
            self._fps = self._fps_count / elapsed_since_fps_tick
            self._fps_count = 0
            self._fps_tick = now

        return self._time_ms

    def get_time(self) -> float:
        return self._time_ms

    def get_rawtime(self) -> float:
        return self._raw_time_ms

    def get_fps(self) -> float:
        return self._fps
