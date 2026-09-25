from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from ipaddress import IPv4Address


class AddressStatus(Enum):
    PENDING = auto()
    QUEUED = auto()
    PROCESSING = auto()
    DONE = auto()


@dataclass(frozen=True, slots=True)
class AddressResult:
    responded: bool


@dataclass(frozen=True, slots=True)
class AddressRecord:
    address: IPv4Address
    status: AddressStatus = AddressStatus.PENDING
    last_result: AddressResult | None = None


class AddressStatusStore(ABC):
    @abstractmethod
    async def get_status(self, address: IPv4Address) -> AddressStatus: ...

    @abstractmethod
    async def get_last_result(self, address: IPv4Address) -> AddressResult | None: ...

    @abstractmethod
    async def mark_as_pending(self, address: IPv4Address): ...

    @abstractmethod
    async def mark_as_queued(self, address: IPv4Address): ...

    @abstractmethod
    async def mark_as_processing(self, address: IPv4Address): ...

    @abstractmethod
    async def mark_as_done(self, address: IPv4Address, result: AddressResult): ...


class InmemoryAddressStatusStore(AddressStatusStore):
    def __init__(self):
        self._records: dict[IPv4Address, AddressRecord] = dict()

    def _get_or_default(self, address: IPv4Address) -> AddressRecord:
        if address in self._records:
            return self._records[address]
        else:
            return AddressRecord(address=address)

    async def get_status(self, address: IPv4Address) -> AddressStatus:
        return self._get_or_default(address).status

    async def get_last_result(self, address: IPv4Address) -> AddressResult | None:
        return self._get_or_default(address).last_result

    async def mark_as_pending(self, address: IPv4Address):
        record = self._get_or_default(address)
        self._records[address] = AddressRecord(
            address=address,
            status=AddressStatus.PENDING,
            last_result=record.last_result
        )

    async def mark_as_queued(self, address: IPv4Address):
        record = self._get_or_default(address)
        self._records[address] = AddressRecord(
            address=address,
            status=AddressStatus.QUEUED,
            last_result=record.last_result
        )

    async def mark_as_processing(self, address: IPv4Address):
        record = self._get_or_default(address)
        self._records[address] = AddressRecord(
            address=address,
            status=AddressStatus.PROCESSING,
            last_result=record.last_result
        )

    async def mark_as_done(self, address: IPv4Address, result: AddressResult):
        self._records[address] = AddressRecord(
            address=address,
            status=AddressStatus.DONE,
            last_result=result
        )
