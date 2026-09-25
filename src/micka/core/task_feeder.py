import asyncio
from ipaddress import IPv4Address

from .address_que import AddressQue
from .address_status_store import AddressStatusStore, AddressStatus
from .ping_task_pool import PingTaskPool


class TaskFeeder:
    def __init__(
            self,
            address_que: AddressQue,
            status_store: AddressStatusStore,
            task_pool: PingTaskPool,
            start: IPv4Address,
            end: IPv4Address,
            tick_interval: float = 0.01
    ):
        self.que: AddressQue = address_que
        self.status_store: AddressStatusStore = status_store
        self.task_pool: PingTaskPool = task_pool

        self.start: IPv4Address = start
        self.end: IPv4Address = end
        self.tick_interval: float = tick_interval
        self._running: bool = False

    async def run(self):
        self._running = True

        while self._running:
            for int_address in range(int(self.start), int(self.end) + 1):
                address = IPv4Address(int_address)
                if await self.status_store.get_status(address) == AddressStatus.PENDING:
                    await self.status_store.mark_as_queued(address)
                    await self.que.append(address)

                if not self._running:
                    break

            await asyncio.sleep(self.tick_interval)

    def stop(self):
        self._running = False
