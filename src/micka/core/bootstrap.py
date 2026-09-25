import asyncio
import logging
import os
from dataclasses import dataclass
from enum import auto, StrEnum
from ipaddress import IPv4Address

import redis.asyncio as aioredis
import reger
from dependency_injector.containers import DeclarativeContainer
from dependency_injector.providers import Singleton
from dotenv import load_dotenv
from icmplib import AsyncSocket, ICMPv4Socket

from micka.core.address_que import AddressQue
from micka.core.address_status_store import InmemoryAddressStatusStore, AddressStatusStore
from micka.core.ping_receiver import PingReceiver
from micka.core.ping_sender import PingSender
from micka.core.ping_task_pool import PingTaskPool
from micka.core.redis_store import RedisAddressStatusStore
from micka.core.task_feeder import TaskFeeder
from micka.core.task_pool_watcher import TaskPoolWatcher

_logger = logging.getLogger(__name__)


class StoreType(StrEnum):
    INMEMORY = auto()
    REDIS = auto()


@dataclass
class Config:
    store_type: StoreType
    start_address: IPv4Address
    end_address: IPv4Address

    redis_host: str | None
    redis_port: int | None
    redis_password: str | None


def create_config() -> Config:
    load_dotenv()

    return Config(
        store_type=StoreType(os.getenv('STORE_TYPE').lower()),
        start_address=IPv4Address(os.getenv('START_ADDRESS')),
        end_address=IPv4Address(os.getenv('END_ADDRESS')),

        redis_host=os.getenv('REDIS_HOST'),
        redis_port=int(os.getenv('REDIS_PORT')) if os.getenv('REDIS_PORT') is not None else None,
        redis_password=os.getenv('REDIS_PASSWORD')
    )


def create_status_store(config: Config) -> AddressStatusStore:
    if config.store_type == StoreType.INMEMORY:
        return InmemoryAddressStatusStore()
    elif config.store_type == StoreType.REDIS:
        return RedisAddressStatusStore(
            client=aioredis.Redis(host=config.redis_host, port=config.redis_port, password=config.redis_password)
        )
    else:
        raise ValueError('Wrong store type')


def create_task_feeder(
        config: Config,
        address_que: AddressQue,
        status_store: AddressStatusStore,
        task_pool: PingTaskPool
) -> TaskFeeder:
    return TaskFeeder(
        address_que=address_que,
        status_store=status_store,
        task_pool=task_pool,
        start=config.start_address,
        end=config.end_address
    )


class RootContainer(DeclarativeContainer):
    config: Singleton[Config] = Singleton(create_config)

    status_store: Singleton[AddressStatusStore] = Singleton(create_status_store, config=config)
    task_pool: Singleton[PingTaskPool] = Singleton(PingTaskPool)

    icmp_socket: Singleton[ICMPv4Socket] = Singleton(ICMPv4Socket, privileged=False)
    async_socket: Singleton[AsyncSocket] = Singleton(AsyncSocket, icmp_socket)

    sender: Singleton[PingSender] = Singleton(
        PingSender,
        icmp_socket=icmp_socket,
        status_store=status_store,
        task_pool=task_pool,
    )
    receiver: Singleton[PingReceiver] = Singleton(
        PingReceiver,
        async_socket=async_socket,
        status_store=status_store,
        task_pool=task_pool,
    )
    feeder: Singleton[TaskFeeder] = Singleton(
        create_task_feeder,
        config=config,
        address_que=sender,
        status_store=status_store,
        task_pool=task_pool,
    )
    pool_watcher: Singleton[TaskPoolWatcher] = Singleton(
        TaskPoolWatcher,
        task_pool=task_pool,
        status_store=status_store,
        time_limit=10,
    )


class Bootstrapper:
    def __init__(self, container: RootContainer):
        self.container: RootContainer = container

    def run(self):
        asyncio.run(self.arun())

    async def arun(self):
        print(f'{_logger.name}: Setup logging...')
        reger.setup_logging()
        _logger.info('I hope you can see this')

        _logger.info('Creating required instances...')
        sender = self.container.sender()
        receiver = self.container.receiver()
        feeder = self.container.feeder()
        pool_watcher = self.container.pool_watcher()
        _logger.info('Required instances creating done')

        _logger.info('Now running scanner')
        await asyncio.gather(sender.run(), receiver.run(), feeder.run(), pool_watcher.run())
