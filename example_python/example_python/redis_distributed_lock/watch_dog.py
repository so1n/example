import asyncio
import time
from typing import Optional, Union
from redis.asyncio.lock import Lock
from redis.asyncio import Redis


class WithWatchDogLock(Lock):
    _watch_dog: Optional[asyncio.Future]

    async def _watch(self) -> None:
        while True:
            await self.extend(self.timeout)
            await asyncio.sleep(self.timeout / 3)

    def _cancel_watch_dog(self) -> None:
        _old_watch_dog: Optional[asyncio.Future] = getattr(self, "_watch_dog", None)
        if _old_watch_dog and not _old_watch_dog.cancelled():
            _old_watch_dog.cancel()

    async def acquire(
        self,
        blocking: Optional[bool] = None,
        blocking_timeout: Optional[float] = None,
        token: Optional[Union[str, bytes]] = None,
    ) -> bool:
        result = await super().acquire(blocking, blocking_timeout, token)
        if result:
            self._cancel_watch_dog()
            self._watch_dog = asyncio.create_task(self._watch())
        return result

    async def do_release(self, expected_token: bytes) -> None:
        self._cancel_watch_dog()
        return await super().do_release(expected_token)

    def __del__(self) -> None:
        try:
            self._cancel_watch_dog()
        except Exception:
            pass


async def main():
    _redis = Redis()
    s_t = time.time()
    async with _redis.lock("demo", lock_class=WithWatchDogLock, timeout=3):
        print("lock")
        await asyncio.sleep(5)
    print("ok", time.time() - s_t)


if __name__ == "__main__":
    asyncio.run(main())