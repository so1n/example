import asyncio
from typing import Optional, TYPE_CHECKING
from middleware.base import BaseLockMiddleware
from base import BaseLock, lock_ctx


class WithWatchDogLockMiddleware(BaseLockMiddleware):
    _watch_dog: Optional[asyncio.Future]
    _lock: "BaseLock"
    _timeout: float

    def __init__(self) -> None:
        self._cancel_flag: bool = False

    def __post_init__(self, lock: "BaseLock"):
        if getattr(self, "_lock", None):
            raise ValueError("Already bind lock")
        if lock.timeout is None:
            raise ValueError("timeout must not be None")

        self._lock = lock
        self._timeout = self._lock.timeout

    async def acquire(self, result: Optional[bool]) -> None:
        if result:
            self._cancel_flag = False
            if not getattr(self, "_watch_dog", None):
                self._watch_dog = asyncio.create_task(self._watch(), context=lock_ctx)
        print("acquire", self._cancel_flag)

    async def release(self, result: Optional[bool]) -> None:
        self._cancel_flag = True
        print("release", self._cancel_flag)

    async def _watch(self) -> None:
        while True:
            await self._lock.extend(self._timeout)
            await asyncio.sleep(self._timeout / 3)
            if self._cancel_flag:
                break

    def __del__(self) -> None:
        try:
            _old_watch_dog: Optional[asyncio.Future] = getattr(self, "_watch_dog", None)
            if _old_watch_dog and not _old_watch_dog.cancelled():
                _old_watch_dog.cancel()
        except Exception:
            pass
