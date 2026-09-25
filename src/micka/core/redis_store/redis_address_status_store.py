from ipaddress import IPv4Address

from redis import asyncio as aioredis

from micka.core.address_status_store import AddressStatusStore, AddressStatus, AddressResult

_BINARY_STATUS_MAP = {
    0b00: AddressStatus.PENDING,
    0b01: AddressStatus.QUEUED,
    0b10: AddressStatus.PROCESSING,
    0b11: AddressStatus.DONE
}
_STATUS_BINARY_MAP = {_BINARY_STATUS_MAP[binary]: binary for binary in _BINARY_STATUS_MAP}

_CHUNK_ADDRESS_COUNT = 0x0100_0000  # a chunk covers a /8 range (2 ** 24 addresses)
_FIELD_FORMAT = 'u2'  # each address occupies a 2-bit unsigned field


def _chunk_key(prefix: str, address: IPv4Address) -> str:
    chunk_index = int(address) >> 24
    return f'{prefix}:{chunk_index}'


def _field_offset(address: IPv4Address) -> str:
    # '#N' addresses the N-th u2 field, i.e. bit offset N * 2
    return f'#{int(address) & (_CHUNK_ADDRESS_COUNT - 1)}'


class RedisAddressStatusStore(AddressStatusStore):
    def __init__(self, client: aioredis.Redis):
        self.redis_client: aioredis.Redis = client

    async def get_status(self, address: IPv4Address) -> AddressStatus:
        key = _chunk_key('status', address)
        offset = _field_offset(address)
        value, = await self.redis_client.bitfield(key).get(_FIELD_FORMAT, offset).execute()

        return _BINARY_STATUS_MAP[value]

    async def get_last_result(self, address: IPv4Address) -> AddressResult | None:
        key = _chunk_key('result', address)
        offset = _field_offset(address)
        value, = await self.redis_client.bitfield(key).get(_FIELD_FORMAT, offset).execute()

        if value & 0b10 == 0:
            return None

        return AddressResult(responded=bool(value & 0b01))

    async def _set_status(self, address: IPv4Address, status: AddressStatus):
        key = _chunk_key('status', address)
        offset = _field_offset(address)
        await self.redis_client.bitfield(key).set(_FIELD_FORMAT, offset, _STATUS_BINARY_MAP[status]).execute()

    async def mark_as_pending(self, address: IPv4Address):
        await self._set_status(address, AddressStatus.PENDING)

    async def mark_as_queued(self, address: IPv4Address):
        await self._set_status(address, AddressStatus.QUEUED)

    async def mark_as_processing(self, address: IPv4Address):
        await self._set_status(address, AddressStatus.PROCESSING)

    async def mark_as_done(self, address: IPv4Address, result: AddressResult):
        await self._set_status(address, AddressStatus.DONE)

        key = _chunk_key('result', address)
        offset = _field_offset(address)
        value = 0b10 | int(result.responded)
        await self.redis_client.bitfield(key).set(_FIELD_FORMAT, offset, value).execute()
