from abc import ABC, abstractmethod
from ipaddress import IPv4Address


class AddressQue(ABC):
    @abstractmethod
    async def append(self, address: IPv4Address, timeout: int | None = 60) -> bool: ...
