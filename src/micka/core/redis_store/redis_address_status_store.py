from ipaddress import IPv4Address

from redis import asyncio as aioredis

from micka.core.address_status_store import AddressStatusStore, AddressStatus, AddressResult

_STRING_STATUS_MAP = {
    'PE': AddressStatus.PENDING,
    'QU': AddressStatus.QUEUED,
    'PR': AddressStatus.PROCESSING,
    'DO': AddressStatus.DONE
}
_STATUS_STRING_MAP = {
    AddressStatus.PENDING: 'PE',
    AddressStatus.QUEUED: 'QU',
    AddressStatus.PROCESSING: 'PR',
    AddressStatus.DONE: 'DO'
}


def _to_status(value: str | bytes | None) -> AddressStatus | None:
    if value is None:
        return None
    else:
        if isinstance(value, bytes):
            string = value.decode()
        else:
            string = value

        return _STRING_STATUS_MAP[string]


def _to_string(status: AddressStatus | None) -> str | None:
    if status is None:
        return None
    else:
        return _STATUS_STRING_MAP[status]


class RedisAddressStatusStore(AddressStatusStore):
    def __init__(self, client: aioredis.Redis):
        self.redis_client: aioredis.Redis = client

    async def get_status(self, address: IPv4Address) -> AddressStatus:
        return _to_status(await self.redis_client.get(str(address))) or AddressStatus.PENDING

    async def get_last_result(self, address: IPv4Address) -> AddressResult | None:
        value = await self.redis_client.get(f'{str(address)}:responded')

        if value is not None:
            return AddressResult(responded=bool(int(value)))
        else:
            return None

    async def mark_as_pending(self, address: IPv4Address):
        await self.redis_client.set(str(address), _to_string(AddressStatus.PENDING))

    async def mark_as_queued(self, address: IPv4Address):
        await self.redis_client.set(str(address), _to_string(AddressStatus.QUEUED))

    async def mark_as_processing(self, address: IPv4Address):
        await self.redis_client.set(str(address), _to_string(AddressStatus.PROCESSING))

    async def mark_as_done(self, address: IPv4Address, result: AddressResult):
        await self.redis_client.set(str(address), _to_string(AddressStatus.DONE))
        await self.redis_client.set(f'{str(address)}:responded', '1' if result.responded else '0')
