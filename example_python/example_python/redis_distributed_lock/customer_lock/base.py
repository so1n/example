from contextvars import ContextVar
from typing import Any, List, Optional, TYPE_CHECKING
from redis.asyncio.lock import LockError

if TYPE_CHECKING:
    from .middleware.base import BaseLockMiddleware

lock_ctx: ContextVar[Optional[str]] = ContextVar("lock_ctx", default=None)

class BaseLock(object):
    def __init__(self, timeout: Optional[float] = None, middleware_list: Optional[List["BaseLockMiddleware"]] = None):

        self.timeout = timeout
        self._middleware_list = middleware_list or []

        for middleware in self._middleware_list:
            middleware.__post_init__(self)

    async def __aenter__(self):
        result = await self.acquire()
        for middleware in self._middleware_list:
            await middleware.acquire(result)
        if result:
            return self
        raise LockError("Unable to acquire lock within the time specified")

    async def __aexit__(self, exc_type, exc_value, traceback):
        result = await self.release()
        for middleware in self._middleware_list:
            await middleware.release(result)

    async def acquire(self) -> None:
        pass

    async def release(self) -> None:
        pass

    async def extend(self, additional_time: float, **kwargs: Any) -> bool:
        pass

