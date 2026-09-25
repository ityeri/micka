from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from ipaddress import IPv4Address

from bitarray import bitarray
from bitarray.util import ba2int, int2ba


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


_BINARY_STATUS_MAP = {
    0b00: AddressStatus.PENDING,
    0b01: AddressStatus.QUEUED,
    0b10: AddressStatus.PROCESSING,
    0b11: AddressStatus.DONE
}
_STATUS_BINARY_MAP = {_BINARY_STATUS_MAP[binary]: binary for binary in _BINARY_STATUS_MAP}

_CHUNK_ADDRESS_COUNT = 0x0100_0000  # a chunk covers a /8 range (2 ** 24 addresses)
_CHUNK_BIT_LENGTH = _CHUNK_ADDRESS_COUNT * 2  # each address occupies 2 bits


def _to_bit_offset(address: IPv4Address) -> int:
    return (int(address) & 0x00ff_ffff) * 2


class InmemoryAddressStatusStore(AddressStatusStore):
    def __init__(self):
        self._status_chunks: dict[int, bitarray] = dict()
        self._result_chunks: dict[int, bitarray] = dict()

    def _get_status_chunk(self, index: int) -> bitarray:
        if index not in self._status_chunks:
            self._status_chunks[index] = bitarray(_CHUNK_BIT_LENGTH)
        return self._status_chunks[index]

    def _get_result_chunk(self, index: int) -> bitarray:
        if index not in self._result_chunks:
            self._result_chunks[index] = bitarray(_CHUNK_BIT_LENGTH)
        return self._result_chunks[index]

    async def get_status(self, address: IPv4Address) -> AddressStatus:
        chunk_index = int(address) >> 24
        if chunk_index in self._status_chunks:
            chunk = self._status_chunks[chunk_index]
            offset = _to_bit_offset(address)
            value = ba2int(chunk[offset:offset + 2])

            return _BINARY_STATUS_MAP[value]
        else:
            return AddressStatus.PENDING

    async def get_last_result(self, address: IPv4Address) -> AddressResult | None:
        chunk_index = int(address) >> 24
        if chunk_index in self._result_chunks:
            chunk = self._result_chunks[chunk_index]
            offset = _to_bit_offset(address)
            raw_result = chunk[offset:offset + 2]

            if raw_result[0] == 0:
                return None
            else:
                return AddressResult(responded=bool(raw_result[1]))
        else:
            return None

    def _set_status(self, address: IPv4Address, status: AddressStatus):
        chunk_index = int(address) >> 24
        offset = _to_bit_offset(address)

        status_chunk = self._get_status_chunk(chunk_index)
        status_chunk[offset:offset + 2] = int2ba(_STATUS_BINARY_MAP[status], length=2)

    async def mark_as_pending(self, address: IPv4Address):
        self._set_status(address, AddressStatus.PENDING)

    async def mark_as_queued(self, address: IPv4Address):
        self._set_status(address, AddressStatus.QUEUED)

    async def mark_as_processing(self, address: IPv4Address):
        self._set_status(address, AddressStatus.PROCESSING)

    async def mark_as_done(self, address: IPv4Address, result: AddressResult):
        self._set_status(address, AddressStatus.DONE)

        chunk_index = int(address) >> 24
        offset = _to_bit_offset(address)

        result_chunk = self._get_result_chunk(chunk_index)
        result_chunk[offset] = 1
        result_chunk[offset + 1] = int(result.responded)
