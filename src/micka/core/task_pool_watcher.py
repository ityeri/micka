import asyncio
import logging
import time

from micka.core.address_status_store import AddressStatusStore, AddressResult
from micka.core.ping_task_pool import MAX_SEQUENCE_ID, PingTaskPool

_logger = logging.getLogger(__name__)


class TaskPoolWatcher:
    def __init__(
            self,
            task_pool: PingTaskPool,
            status_store: AddressStatusStore,
            time_limit: float = 60,
            batch_size: int = 256,
            tick_interval: float = 0.01
    ):
        self.task_pool: PingTaskPool = task_pool
        self.status_store: AddressStatusStore = status_store

        self.time_limit: float = time_limit
        self.batch_size: int = batch_size
        self.tick_interval: float = tick_interval
        self._running: bool = False
        self._current_checking_sequence_id: int = 0

    async def run(self):
        self._running = True

        while self._running:
            current_time = time.time()
            for _ in range(self.batch_size):
                task = self.task_pool.get_task_by_sequence(self._current_checking_sequence_id)

                if task is not None:
                    if task.sent_at + self.time_limit <= current_time:
                        self.task_pool.pop_task(task.sequence_id)
                        await self.status_store.mark_as_done(task.address, AddressResult(responded=False))

                self._current_checking_sequence_id += 1
                if MAX_SEQUENCE_ID <= self._current_checking_sequence_id:
                    self._current_checking_sequence_id = 0

            await asyncio.sleep(self.tick_interval)
