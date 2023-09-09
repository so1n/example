import asyncio
from redis.asyncio import Redis


class Counter(object):
    def __init__(self, namespace: str, redis: Redis) -> None:
        self._redis = redis
        self.namespace: str = namespace
        self.count: int = 0

    async def login(self) -> None:
        async with self._redis.lock("demo"):
            self.count += 1

    async def logout(self) -> None:
        async with self._redis.lock("demo"):
            self.count -= 1


async def main():
    counter = Counter("demo", Redis())
    await counter.login()
    await counter.logout()


if __name__ == "__main__":
    asyncio.run(main())