import logging

from icmplib import AsyncSocket, TimeoutExceeded

from micka.core.address_status_store import AddressStatusStore, AddressResult
from micka.core.ping_task_pool import PingTaskPool

_logger = logging.getLogger(__name__)


class PingReceiver:
    def __init__(self, async_socket: AsyncSocket, status_store: AddressStatusStore, task_pool: PingTaskPool):
        self.socket: AsyncSocket = async_socket
        self.status_store: AddressStatusStore = status_store
        self.task_pool: PingTaskPool = task_pool
        self._running: bool = False

    async def run(self):
        self._running = True

        while self._running:
            try:
                reply = await self.socket.receive()
                task = self.task_pool.pop_task(reply.sequence)

                if task is not None:
                    _logger.info(f'Ping result has received for address: {task.address}')

                    if reply.type == 0:  # for IPv6, it should be 129
                        result = AddressResult(responded=True)
                    else:
                        result = AddressResult(responded=False)
                    await self.status_store.mark_as_done(task.address, result)

            except TimeoutExceeded:
                pass
