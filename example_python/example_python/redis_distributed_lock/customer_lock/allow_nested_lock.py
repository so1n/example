import asyncio

from uuid import uuid1
from redis.asyncio import Redis, RedisCluster
from redis.asyncio.lock import Lock, LockError, LockNotOwnedError
from typing import Union, Optional, cast, Type, List
from base import BaseLock, lock_ctx
from middleware.base import BaseLockMiddleware



class AllowNestedLock(BaseLock):
    lua_release = None
    lua_extend = None
    lua_acquire = None

    # KEYS[1] - lock name
    # ARGV[1] - token
    # return 1 if the lock was released, otherwise 0
    LUA_RELEASE_SCRIPT = """
    if (redis.call('hexists', KEYS[1], ARGV[1]) == 0) then
        return nil;
    end ;
    local counter = redis.call('hincrby', KEYS[1], ARGV[1], -1);
    if (counter > 0) then
        return 0;
    else
        redis.call('del', KEYS[1]);
        return 1;
    end ;
    return nil;
    """

    # KEYS[1] - lock name
    # ARGV[1] - token
    # ARGV[2] - additional milliseconds
    # ARGV[3] - "0" if the additional time should be added to the lock's
    #           existing ttl or "1" if the existing ttl should be replaced
    # return 1 if the locks time was extended, otherwise 0
    LUA_EXTEND_SCRIPT = """
            if (redis.call('hexists', KEYS[1], ARGV[1]) == 0) then
                return 0
            end
            local expiration = redis.call('pttl', KEYS[1])
            if not expiration then
                expiration = 0
            end
            if expiration < 0 then
                return 0
            end

            local newttl = ARGV[2]
            if ARGV[3] == "0" then
                newttl = ARGV[2] + expiration
            end
            redis.call('pexpire', KEYS[1], newttl)
            return 1
        """

    # KEYS[1] - lock name
    # ARGV[1] - milliseconds
    # ARGV[2] - token
    # return 1 if the locks time was reacquired, otherwise 0
    LUA_ACQUIRE_SCRIPT = """
        if (redis.call('exists', KEYS[1]) == 0) then
            redis.call('hincrby', KEYS[1], ARGV[2], 1);
            redis.call('pexpire', KEYS[1], ARGV[1]);
            return 1;
        end ;

        if (redis.call('hexists', KEYS[1], ARGV[2]) == 1) then
            redis.call('hincrby', KEYS[1], ARGV[2], 1);
            redis.call('pexpire', KEYS[1], ARGV[1]);
            return 1;
        end ;
        return 0;
        """

    def __init__(
            self,
            redis: Union["Redis", "RedisCluster"],
            name: Union[str, bytes, memoryview],
            timeout: Optional[float] = None,
            sleep: float = 0.1,
            blocking: bool = True,
            blocking_timeout: Optional[float] = None,
            middleware_list: Optional[List["BaseLockMiddleware"]] = None
    ):
        self.redis = redis
        self.name = name
        self.sleep = sleep
        self.blocking = blocking
        self.blocking_timeout = blocking_timeout
        self.register_scripts()
        super().__init__(timeout, middleware_list)

    def register_scripts(self):
        cls = self.__class__
        client = self.redis
        if cls.lua_release is None:
            cls.lua_release = client.register_script(cls.LUA_RELEASE_SCRIPT)
        if cls.lua_extend is None:
            cls.lua_extend = client.register_script(cls.LUA_EXTEND_SCRIPT)
        if cls.lua_acquire is None:
            cls.lua_acquire = client.register_script(cls.LUA_ACQUIRE_SCRIPT)

    async def acquire(
            self,
            blocking: Optional[bool] = None,
            blocking_timeout: Optional[float] = None,
            token: Optional[Union[str, bytes]] = None,
    ) -> bool:
        sleep = self.sleep

        if not token:
            token = lock_ctx.get()
            if not token:
                token = uuid1().hex.encode()
        use_token = f"{token}:{id(asyncio.current_task())}"

        if blocking is None:
            blocking = self.blocking
        if blocking_timeout is None:
            blocking_timeout = self.blocking_timeout
        stop_trying_at = None
        if blocking_timeout is not None:
            stop_trying_at = asyncio.get_running_loop().time() + blocking_timeout
        while True:
            if await self.do_acquire(use_token):
                lock_ctx.set(token)
                return True
            if not blocking:
                return False
            next_try_at = asyncio.get_running_loop().time() + sleep
            if stop_trying_at is not None and next_try_at > stop_trying_at:
                return False
            await asyncio.sleep(sleep)

    async def do_acquire(self, token: Union[str, bytes]) -> bool:
        timeout = int(self.timeout * 1000) if self.timeout else None
        if await self.lua_acquire(
                keys=[self.name], args=[timeout, token], client=self.redis
        ):
            return True
        return False

    async def locked(self) -> bool:
        return await self.redis.get(self.name) is not None

    async def owned(self) -> bool:
        token = lock_ctx.get()
        if not token:
            return False
        use_token = f"{token}:{id(asyncio.current_task())}"
        return await self.redis.hexists(self.name, use_token)

    async def release(self) -> None:
        token = lock_ctx.get()
        if token is None:
            raise LockError("Cannot release an unlocked lock")

        use_token = f"{token}:{id(asyncio.current_task())}"
        result: Optional[int] = await self.lua_release(
            keys=[self.name], args=[use_token], client=self.redis
        )
        if result != 0:
            lock_ctx.set(None)
        if result is None:
            raise LockNotOwnedError("Cannot release a lock that's no longer owned")

    async def extend(self, additional_time: float, replace_ttl: bool = False) -> bool:
        token = lock_ctx.get()
        if token is None:
            raise LockError("Cannot extend an unlocked lock")
        if self.timeout is None:
            raise LockError("Cannot extend a lock with no timeout")
        additional_time = int(additional_time * 1000)
        result = await self.lua_extend(
            keys=[self.name],
            args=[token, additional_time, replace_ttl and "1" or "0"],
            client=self.redis,
        )
        print("extend", result)
        if not bool(result):
            raise LockNotOwnedError("Cannot extend a lock that's no longer owned")
        return True


from middleware.watch_dog import WithWatchDogLockMiddleware

async def print_info(cnt: int) -> None:
    print(f"Task:{id(asyncio.current_task())}, run cnt:{cnt}")


async def demo(_redis: Redis) -> None:
    await print_info(0)
    async with AllowNestedLock(_redis, "demo", timeout=2, sleep=1, middleware_list=[WithWatchDogLockMiddleware()]):
        await print_info(1)
        async with AllowNestedLock(_redis, "demo", timeout=2, sleep=1, middleware_list=[WithWatchDogLockMiddleware()]):
            await print_info(2)
            await asyncio.sleep(1)


async def main():
    _redis = Redis()
    await asyncio.gather(*[demo(_redis) for _ in range(3)])


if __name__ == '__main__':
    asyncio.run(main())
