import asyncio
import logging
import time
from ipaddress import IPv4Address
from typing import override

from icmplib import ICMPRequest
from icmplib.exceptions import ICMPSocketError, SocketBroadcastError
from icmplib.sockets import ICMPSocket

from .address_que import AddressQue
from .address_status_store import AddressStatusStore, AddressStatus, AddressResult
from .ping_task_pool import PingTaskPool

_logger = logging.getLogger(__name__)


class PingSender(AddressQue):
    def __init__(
            self,
            icmp_socket: ICMPSocket,
            status_store: AddressStatusStore,
            task_pool: PingTaskPool,
            max_que_length: int = 2 ** 16,
            ping_batch_size: int = 128,
            tick_interval: float = 0.01
    ):
        self.icmp_socket: ICMPSocket = icmp_socket
        self.status_store: AddressStatusStore = status_store
        self.task_pool: PingTaskPool = task_pool

        self.que: list[int] = list()
        self.max_que_length: int = max_que_length
        self.ping_batch_size: int = ping_batch_size
        self.tick_interval: float = tick_interval

        self._running: bool = False

    @override
    async def append(self, address: IPv4Address, timeout: int | None = 60) -> bool:
        if timeout is not None:
            limit_time = time.time() + timeout
        else:
            limit_time = None
        while True:
            if len(self.que) < self.max_que_length:
                self.que.append(int(address))
                return True

            await asyncio.sleep(0.01)

            if limit_time is not None:
                if limit_time <= time.time():
                    return False

    async def run(self):
        self._running = True
        while self._running:
            for i in range(self.ping_batch_size):
                if not self.que:
                    break

                address = IPv4Address(self.que[0])

                if await self.status_store.get_status(address) == AddressStatus.QUEUED:
                    await self.status_store.mark_as_processing(address)
                    # TODO: how about add a method: PingTaskPool.check_task_creatavility
                    task = self.task_pool.create_new_task(address)

                    if task is not None:
                        request = ICMPRequest(destination=str(task.address), id=1, sequence=task.sequence_id)

                        try:
                            self.icmp_socket.send(request)
                        except SocketBroadcastError:
                            # broadcast addresses can never be sent to; retrying won't help
                            self.que.pop(0)
                            self.task_pool.pop_task(task.sequence_id)
                            await self.status_store.mark_as_done(address, AddressResult(responded=False))
                            _logger.warning(f'Skipping broadcast address: {address}')
                        except ICMPSocketError as error:
                            # e.g. [Errno 11] Resource temporarily unavailable: the socket's
                            # send buffer is full (often unresolved ARP requests piling up for
                            # unreachable hosts)
                            self.que.pop(0)
                            self.task_pool.pop_task(task.sequence_id)
                            await self.status_store.mark_as_pending(address)
                            _logger.warning(f'Ping send failed for {address}, will retry: {error}')
                            break
                        else:
                            self.que.pop(0)
                            _logger.info(f'Ping has sent for IP address: {address}')
                    else:
                        await self.status_store.mark_as_queued(address)
                        # _logger.info('Ping task creation has failed by task pool limit')

            await asyncio.sleep(self.tick_interval)

    def stop(self):
        self._running = False
