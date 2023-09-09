from typing import Optional
class BaseLockMiddleware(object):
    def __post_init__(self, lock: "BaseLock"):
        pass

    async def acquire(self, result: Optional[bool]) -> None:
        pass

    async def release(self, result: Optional[bool]) -> None:
        pass
