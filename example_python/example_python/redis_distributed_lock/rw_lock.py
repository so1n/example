import asyncio
import time
from uuid import uuid1
import random
import logging
from collections import deque
from redis.asyncio import Redis
from redis.asyncio.lock import LockError, LockNotOwnedError
from typing import Dict, Optional, List, Tuple, Deque


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
            listener = self._manager.listener_dict[listen_name]
            while True:
                if not len(listener):
                    self._manager.listener_dict.pop(listen_name, None)
                    break
                lock_mode, f = listener.popleft()
                if f.done():
                    continue

                f.set_result(True)
                if lock_mode == "read" and listener and listener[0][0] == "read":
                    continue
                else:
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
        self.listener_dict: Dict[str, Deque[Tuple[str, asyncio.Future]]] = {}

    def listen(self, lock_name: str, lock_mode: str) -> asyncio.Future:
        if lock_name not in self.listener_dict:
            self.listener_dict[lock_name] = deque()

        f = asyncio.Future()
        self.listener_dict[lock_name].append((lock_mode, f))
        return f

    def empty(self, lock_name: str) -> bool:
        if lock_name not in self.listener_dict:
            return True
        return len(self.listener_dict[lock_name]) == 0

    def start(self) -> None:
        for proxy in self._proxies:
            proxy.start()

    def stop(self) -> None:
        for proxy in self._proxies:
            proxy.stop()

    def get_random_proxy_name(self) -> str:
        return self._proxies[random.randint(0, len(self._proxies) - 1)].name


class RwLock(object):
    mode: str = ""
    lua_acquire = None
    lua_release = None
    LUA_RELEASE_SCRIPT = None
    LUA_ACQUIRE_SCRIPT = None

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
    # release #
    ###########
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
        raise NotImplementedError()

    ###########
    # acquire #
    ###########
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
                listener = self._manager.listen(self._name, self.mode)

            ttl = ttl / 3 if (ttl / 3) < 1 else 1
            await asyncio.wait([listener])

    async def _do_acquire(self, token: str, proxy_name: str) -> Optional[int]:
        raise NotImplementedError()

    #############
    # watch dog #
    #############
    _watch_dog: Optional[asyncio.Future]
    lua_extend = None
    # KEYS[1] - lock name
    # KEYS[2] - write&read lock prefix       {lock name}
    # ARGV[1] - token
    # ARGV[2] - additional milliseconds
    # return 1 if the locks time was extended, otherwise 0
    LUA_EXTEND_SCRIPT = """
    local counter = redis.call('hget', KEYS[1], ARGV[1]);
    if (counter ~= false) then
        redis.call('pexpire', KEYS[1], ARGV[2]);
        if (redis.call('hlen', KEYS[1]) > 1) then
            local keys = redis.call('hkeys', KEYS[1]);
            for n, key in ipairs(keys) do
                counter = tonumber(redis.call('hget', KEYS[1], key));
                if type(counter) == 'number' then
                    for i=counter, 1, -1 do
                        redis.call('pexpire', KEYS[2] .. ':' .. key .. ':rwlock_timeout:' .. i, ARGV[2]);
                    end;
                end;
            end;
        end;
        return 1;
    end;
    return 0;
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
            keys=[self._name, self._name], args=[token, timeout], client=self._client,
        ))

    def __del__(self) -> None:
        try:
            _old_watch_dog: Optional[asyncio.Future] = getattr(self, "_watch_dog", None)
            if _old_watch_dog and not _old_watch_dog.cancelled():
                _old_watch_dog.cancel()
        except Exception:
            pass


class ReadLock(RwLock):
    mode = "read"
    ###########
    # acquire #
    ###########
    lua_acquire = None
    # KEYS[1] - lock name
    # KEYS[2] - owner's rw lock name      {lock name}:{uuid}:{id}:rwlock_timeout
    # KEYS[3] - write lock name           {lock name}:write
    # ARGV[1] - token
    # ARGV[2] - proxy name
    # ARGV[3] - milliseconds
    # return nil if the locks time was reacquired, otherwise ttl(millisecond)
    #
    # data struct
    # {lock name}: {
    #    "mode": "read",
    #    "proxy": "{proxy name}"
    #    "{uuid}:{id}": 1
    # }
    # {lock name}:{uuid}:{id}:rwlock_timeout:1 1
    LUA_ACQUIRE_SCRIPT = """
    local mode = redis.call('hget', KEYS[1], 'mode');
    local wait_write = redis.call('exists', KEYS[3]);
    if (mode == false) then
        redis.call('hset', KEYS[1], 'mode', 'read');
        redis.call('hset', KEYS[1], ARGV[1], 1);
        redis.call('set', KEYS[2] .. ':1', 1);
        redis.call('pexpire', KEYS[2] .. ':1', ARGV[3]);
        redis.call('pexpire', KEYS[1], ARGV[3]);
        
        redis.call('hset', KEYS[1], 'proxy_name', ARGV[2])
        redis.call('del', ARGV[2]);
        return nil;
    end;
    if (mode == 'read') and (wait_write == 0)then
        local ind = redis.call('hincrby', KEYS[1], ARGV[1], 1);
        local key = KEYS[2] .. ':' .. ind;
        redis.call('set', key, 1);
        redis.call('pexpire', key, ARGV[3]);
        redis.call('pexpire', KEYS[1], ARGV[3]);
        return nil;
    end;
    return redis.call('pttl', KEYS[1])
    """

    async def _do_acquire(self, token: str, proxy_name: str) -> Optional[int]:
        timeout = int(self._timeout * 1000)
        result = await self.lua_acquire(
            keys=[self._name, f"{self._name}:{token}:rwlock_timeout", f"{self._name}:write"],
            args=[token, proxy_name, timeout],
            client=self._client
        )
        if result:
            result = result / 1000
        return result

    ###########
    # release #
    ###########
    lua_release = None
    # KEYS[1] - lock name
    # KEYS[2] - owner's rw lock name      {lock name}:{uuid}:{id}:rwlock_timeout
    # KEYS[3] - rw lock name prefix       {lock name}
    # ARGV[1] - token
    # ARGV[2] - milliseconds
    # return 1 if the lock was released, otherwise 0
    LUA_RELEASE_SCRIPT = """
    local mode = redis.call('hget', KEYS[1], 'mode');
    if (mode ~= 'read') then
        return nil;
    end ;
    if (redis.call('hexists', KEYS[1], ARGV[1]) == 0) then
        return nil;
    end ;
    
    local counter = redis.call('hincrby', KEYS[1], ARGV[1], -1);
    if (counter == 0) then
        redis.call('hdel', KEYS[1], ARGV[1]);
    end;
    redis.call('del', KEYS[2] .. ':' .. (counter+1));
    if (redis.call('hlen', KEYS[1]) > 1) then
        local maxRemainTime = -3;
        local keys = redis.call('hkeys', KEYS[1]);
        for n, key in ipairs(keys) do
            counter = tonumber(redis.call('hget', KEYS[1], key));
            if type(counter) == 'number' then
                for i=counter, 1, -1 do
                    local remainTime = redis.call('pttl', KEYS[3] .. ':' .. key .. ':rwlock_timeout:' .. i);
                    maxRemainTime = math.max(remainTime, maxRemainTime);
                end;
            end;
        end;
        if maxRemainTime > 0 then
            redis.call('pexpire', KEYS[1], maxRemainTime);
            return 0;
        end;
    end;
    
    local proxy_name = redis.call('hget', KEYS[1], 'proxy_name')
    redis.call('lpush', proxy_name, KEYS[1]);
    redis.call('expire', proxy_name, 3)
    redis.call('del', KEYS[1]);
    return 1;
    """

    async def _do_release(self, token: str) -> Optional[int]:
        return await self.lua_release(
            keys=[self._name, f"{self._name}:{token}:rwlock_timeout", self._name],
            args=[token, self._timeout], client=self._client
        )


class WriteLock(RwLock):
    mode = "write"
    ###########
    # acquire #
    ###########
    lua_acquire = None
    # KEYS[1] - lock name
    # KEYS[2] - write lock name           {lock name}:write
    # ARGV[1] - token
    # ARGV[2] - proxy name
    # ARGV[3] - milliseconds
    # return nil if the locks time was reacquired, otherwise ttl(millisecond)
    #
    # data struct
    # {lock name}: {
    #    "mode": "read",
    #    "proxy": "{proxy name}"
    #    "{uuid}:{id}": 1
    # }
    LUA_ACQUIRE_SCRIPT = """
    local mode = redis.call('hget', KEYS[1], 'mode');
    if (mode == false) then
        redis.call('hset', KEYS[1], 'mode', 'write');
        redis.call('hset', KEYS[1], ARGV[1], 1);
        redis.call('pexpire', KEYS[1], ARGV[3]);
        
        redis.call('hset', KEYS[1], 'proxy_name', ARGV[2])
        redis.call('del', ARGV[2]);
        return nil;
    end;
    if (mode == 'read') then
        redis.call('set', KEYS[2], 'wait_write');
    end;
    
    return redis.call('pttl', KEYS[1])
    """

    async def _do_acquire(self, token: str, proxy_name: str) -> Optional[int]:
        timeout = int(self._timeout * 1000)
        result = await self.lua_acquire(
            keys=[self._name, f"{self._name}:write"],
            args=[token, proxy_name, timeout],
            client=self._client
        )
        if result:
            result = result / 1000
        return result

    ###########
    # release #
    ###########
    lua_release = None
    # KEYS[1] - lock name
    # KEYS[2] - write lock name           {lock name}:write
    # ARGV[1] - token                     {uuid}:{id}
    # return 1 if the lock was released, otherwise 0
    LUA_RELEASE_SCRIPT = """
    local mode = redis.call('hget', KEYS[1], 'mode');
    if (mode ~= 'write') then
        return nil;
    end ;
    if (redis.call('hexists', KEYS[1], ARGV[1]) == 0) then
        return nil;
    end ;
    
    local proxy_name = redis.call('hget', KEYS[1], 'proxy_name')
    redis.call('lpush', proxy_name, KEYS[1]);
    redis.call('expire', proxy_name, 3)
    redis.call('del', KEYS[1]);
    redis.call('del', KEYS[2]); 
    return 1;
    """

    async def _do_release(self, token: str) -> Optional[int]:
        return await self.lua_release(
            keys=[self._name, f"{self._name}:write"], args=[token], client=self._client
        )


async def run_read(manager: Manager, client: Redis) -> None:
    print(f"Timestamp:{time.time()} Task:{id(asyncio.current_task())}, wait read")
    async with ReadLock(client, manager, "demo", timeout=1):
        print(f"Timestamp:{time.time()} Task:{id(asyncio.current_task())}, run read")
        await asyncio.sleep(2)
    print(f"Timestamp:{time.time()} Task:{id(asyncio.current_task())}, read done")


async def run_write(manager: Manager, client: Redis) -> None:
    print(f"Timestamp:{time.time()} Task:{id(asyncio.current_task())}, wait writ")
    async with WriteLock(client, manager, "demo", timeout=1):
        print(f"Timestamp:{time.time()} Task:{id(asyncio.current_task())}, run write")
        await asyncio.sleep(2)
    print(f"Timestamp:{time.time()} Task:{id(asyncio.current_task())}, write done")


async def read_and_read(manager: Manager, client: Redis) -> None:
    async def _read_and_read():
        await run_read(manager, client)

    print("-----read and read-----")
    await asyncio.gather(*[_read_and_read() for _ in range(3)])


async def write_and_write(manager: Manager, client: Redis) -> None:
    async def _write_and_write():
        await run_write(manager, client)

    print("-----write and write-----")
    await asyncio.gather(*[_write_and_write() for _ in range(3)])


async def read_and_write(manager: Manager, client: Redis) -> None:
    print("-----read and write-----")

    task = []
    task.append(asyncio.create_task(run_read(manager, client)))
    await asyncio.sleep(0.5)
    task.append(asyncio.create_task(run_write(manager, client)))
    await asyncio.sleep(0.5)
    # more read
    task.append(asyncio.create_task(run_read(manager, client)))
    task.append(asyncio.create_task(run_read(manager, client)))
    task.append(asyncio.create_task(run_read(manager, client)))
    await asyncio.gather(*task)


async def write_and_read(manager: Manager, client: Redis) -> None:
    print("-----write and read-----")

    tasks = []
    tasks.append(asyncio.create_task(run_write(manager, client)))
    await asyncio.sleep(0.1)
    tasks.append(asyncio.create_task(run_read(manager, client)))
    tasks.append(asyncio.create_task(run_read(manager, client)))
    await asyncio.sleep(0.1)
    tasks.append(asyncio.create_task(run_write(manager, client)))
    await asyncio.sleep(0.1)
    tasks.append(asyncio.create_task(run_read(manager, client)))
    await asyncio.gather(*tasks)


async def main():
    _redis = Redis()
    manager = Manager(client=_redis)
    manager.start()
    await read_and_read(manager, _redis)
    await write_and_write(manager, _redis)
    await read_and_write(manager, _redis)
    await write_and_read(manager, _redis)
    manager.stop()


if __name__ == '__main__':
    asyncio.run(main())
