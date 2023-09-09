import asyncio
from uuid import uuid1
import random
import logging
from redis.asyncio import Redis
from redis.asyncio.lock import LockError, LockNotOwnedError
from typing import Dict, Optional, List


class Proxy(object):
    def __init__(self, name: str, manager: "Manager") -> None:
        self.name = name
        self._manager = manager
        self._task: Optional[asyncio.Task] = None

    async def run(self) -> None:
        while True:
            result: Optional[List[bytes]] = await self._manager.client.blpop([self.name], self._manager.timeout)
            if result is None:
                continue
            listen_name = result[1].decode()
            if listen_name not in self._manager.listener_dict:
                logging.error(f"{listen_name} not in listener_dict")
                continue

            while True:
                if self._manager.listener_dict[listen_name].empty():
                    self._manager.listener_dict.pop(listen_name, None)
                    break
                f = await self._manager.listener_dict[listen_name].get()
                if f.done():
                    continue
                f.set_result(True)
                break

    def start(self) -> None:
        if self._task:
            raise RuntimeError(f"{self.name} already started")
        self._task = asyncio.create_task(self.run())

    def stop(self) -> None:
        if not self._task or self._task.done():
            raise RuntimeError(f"{self.name} not started")
        self._task.cancel()


class Manager(object):
    def __init__(self, client: Redis, proxy_num: int = 8, timeout: int = 5):
        self._proxy_num = proxy_num
        self._proxies: List[Proxy] = [Proxy(str(i), self) for i in range(proxy_num)]

        self.client = client
        self.timeout = timeout
        self.listener_dict: Dict[str, asyncio.Queue[asyncio.Future]] = {}

    def listen(self, lock_name: str) -> asyncio.Future:
        if lock_name not in self.listener_dict:
            self.listener_dict[lock_name] = asyncio.Queue()

        f = asyncio.Future()
        self.listener_dict[lock_name].put_nowait(f)
        return f

    def empty(self, lock_name: str) -> bool:
        if lock_name not in self.listener_dict:
            return True
        return self.listener_dict[lock_name].empty()

    def start(self) -> None:
        for proxy in self._proxies:
            proxy.start()

    def stop(self) -> None:
        for proxy in self._proxies:
            proxy.stop()

    def get_random_proxy_name(self) -> str:
        return self._proxies[random.randint(0, len(self._proxies) - 1)].name


class BaseLock(object):
    def __init__(
            self,
            client: Redis,
            manager: Manager,
            name: str,
            timeout: int = 9,
    ) -> None:
        self._name = name
        self._manager = manager
        self._client = client
        self._timeout = timeout
        self.register_scripts()

    def register_scripts(self):
        cls = self.__class__
        client = self._client
        if cls.lua_release is None:
            cls.lua_release = client.register_script(cls.LUA_RELEASE_SCRIPT)
        if cls.lua_extend is None:
            cls.lua_extend = client.register_script(cls.LUA_EXTEND_SCRIPT)
        if cls.lua_acquire is None:
            cls.lua_acquire = client.register_script(cls.LUA_ACQUIRE_SCRIPT)

    async def __aenter__(self):
        if await self.acquire():
            self._cancel_watch_dog()
            self._watch_dog = asyncio.create_task(self._watch())
            return self
        raise LockError("Unable to acquire lock within the time specified")

    async def __aexit__(self, exc_type, exc_value, traceback):
        self._cancel_watch_dog()
        await self._release()

    #########
    # token #
    #########
    @staticmethod
    def _new_token() -> str:
        return str(uuid1().hex) + str(id(asyncio.current_task()))

    @property
    def _token(self) -> Optional[str]:
        return getattr(self, "_token_var", None)

    @_token.setter
    def _token(self, token: Optional[str]) -> None:
        self._token_var = token

    ###########
    # acquire #
    ###########
    lua_acquire = None
    # KEYS[1] - lock name
    # ARGV[1] - token
    # ARGV[2] - proxy name
    # ARGV[3] - milliseconds
    # return nil if the locks time was reacquired, otherwise ttl(millisecond)
    LUA_ACQUIRE_SCRIPT = """
    if (redis.call('exists', KEYS[1]) == 0) then
        redis.call('hset', KEYS[1], ARGV[1], 0);
        redis.call('pexpire', KEYS[1], ARGV[3]);
        redis.call('hset', KEYS[1], 'proxy_name', ARGV[2]);
        redis.call('del', ARGV[2]);
        return nil;
    end ;
    return redis.call('pttl', KEYS[1]);
    """

    async def acquire(self) -> bool:
        if self._token:
            raise LockError("Lock already acquired")
        token = self._new_token()
        proxy_name = self._manager.get_random_proxy_name()
        listener: Optional[asyncio.Future] = None
        ttl: Optional[int] = self._timeout

        while True:
            if listener or self._manager.empty(self._name):
                ttl = await self._do_acquire(token, proxy_name)
                if not ttl:
                    self._token = token
                    if listener and not listener.done():
                        listener.set_result(True)
                    return True
            if not listener or listener.done():
                listener = self._manager.listen(self._name)
            ttl = ttl / 3 if (ttl / 3) < 1 else 1
            await asyncio.wait([listener], timeout=ttl)

    async def _do_acquire(self, token: str, proxy_name: str) -> Optional[int]:
        timeout = int(self._timeout * 1000)
        return await self.lua_acquire(
            keys=[self._name], args=[token, proxy_name, timeout], client=self._client
        )

    ###########
    # release #
    ###########
    lua_release = None
    # KEYS[1] - lock name
    # ARGV[1] - token
    # return 1 if the lock was released, otherwise 0
    LUA_RELEASE_SCRIPT = """
    if (redis.call('hexists', KEYS[1], ARGV[1]) == 0) then
        return nil;
    end ;
    local proxy_name = redis.call('hget', KEYS[1], 'proxy_name')
    
    redis.call('del', KEYS[1]);
    redis.call('del', proxy_name);
    redis.call('lpush', proxy_name, KEYS[1])
    redis.call('expire', proxy_name, 3)
    
    return 1;
    """

    async def _release(self) -> None:
        token = self._token
        if token is None:
            raise LockError("Cannot release an unlocked lock")

        result: Optional[int] = await self._do_release(token)
        if result != 0:
            self._token = None
        if result is None:
            raise LockNotOwnedError("Cannot release a lock that's no longer owned")

    async def _do_release(self, token: str) -> Optional[int]:
        return await self.lua_release(
            keys=[self._name], args=[token], client=self._client
        )

    #############
    # watch dog #
    #############
    _watch_dog: Optional[asyncio.Future]
    lua_extend = None
    # KEYS[1] - lock name
    # ARGV[1] - token
    # ARGV[2] - additional milliseconds
    # return 1 if the locks time was extended, otherwise 0
    LUA_EXTEND_SCRIPT = """
    if (redis.call('hexists', KEYS[1], ARGV[1]) ~= 1) then
        return 0
    end
    local expiration = redis.call('pttl', KEYS[1])
    if not expiration then
        expiration = 0
    end
    if expiration < 0 then
        return 0
    end
    redis.call('pexpire', KEYS[1], ARGV[2])
    return 1
    """

    async def _watch(self) -> None:
        while True:
            if not await self._extend():
                logging.error(f"Failed to extend the lock:{self._name}")
            await asyncio.sleep(self._timeout / 3)

    def _cancel_watch_dog(self) -> None:
        _old_watch_dog: Optional[asyncio.Future] = getattr(self, "_watch_dog", None)
        if _old_watch_dog and not _old_watch_dog.cancelled():
            _old_watch_dog.cancel()

    async def _extend(self) -> bool:
        token = self._token
        if token is None:
            raise LockError("Cannot extend an unlocked lock")
        if self._timeout is None:
            raise LockError("Cannot extend a lock with no timeout")
        timeout = int(self._timeout * 1000)
        return bool(await self.lua_extend(
            keys=[self._name], args=[token, timeout], client=self._client,
        ))

    def __del__(self) -> None:
        try:
            _old_watch_dog: Optional[asyncio.Future] = getattr(self, "_watch_dog", None)
            if _old_watch_dog and not _old_watch_dog.cancelled():
                _old_watch_dog.cancel()
        except Exception:
            pass


async def print_info(cnt: int) -> None:
    print(f"Task:{id(asyncio.current_task())}, run cnt:{cnt}")


async def demo(manager: Manager, client: Redis) -> None:
    await print_info(0)
    async with BaseLock(client, manager, "demo", timeout=1):
        await print_info(1)
        await asyncio.sleep(1)


async def main():
    _redis = Redis()
    manager = Manager(client=_redis)
    manager.start()
    await asyncio.gather(*[demo(manager, _redis) for _ in range(3)])
    manager.stop()


if __name__ == '__main__':
    asyncio.run(main())
