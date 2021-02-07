from typing import Optional, Tuple

import aiomysql
import aioredis
from starlette.applications import Starlette
from starlette.config import Config
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route


config: Config = Config(".env")
mysql_pool: Optional[aiomysql.Pool] = None
redis: Optional[aioredis.Redis] = None


async def on_start_up():
    global mysql_pool
    global redis

    mysql_pool = await aiomysql.create_pool(
        host=config("MYSQL_HOST"),
        port=config("MYSQL_PORT", cast=int),
        user=config("MYSQL_USER"),
        password=config("MYSQL_PW"),
        db=config("MYSQL_DB"),
    )
    redis = aioredis.Redis(
        await aioredis.create_redis_pool(
            config("REDIS_URL"),
            minsize=config("REDIS_POOL_MINSIZE", cast=int),
            maxsize=config("REDIS_POOL_MAXSIZE", cast=int),
            encoding=config("REDIS_ENCODING")
        )
    )


async def on_shutdown():
    await mysql_pool.wait_closed()
    await redis.wait_closed()


def hello_word(request: Request) -> PlainTextResponse:
    return PlainTextResponse("Hello Word!")


async def mysql_demo(request: Request) -> JSONResponse:
    count: int = int(request.query_params.get("count", "0"))
    async with mysql_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT %s;", (count, ))
            mysql_result_tuple: Tuple[int] = await cur.fetchone()
    return JSONResponse({"result": mysql_result_tuple})


async def redis_demo(request: Request) -> JSONResponse:
    count: int = int(request.query_params.get("count", "0"))
    key: str = request.query_params.get("key")
    if not key:
        return JSONResponse("key is empty")
    result: int = await redis.incrby(key, count)
    await redis.expire(key, 60)
    return JSONResponse({"count": result})


app: Starlette = Starlette(
    routes=[
        Route('/', hello_word),
        Route('/mysql', mysql_demo),
        Route('/redis', redis_demo)
    ],
    on_startup=[on_start_up],
    on_shutdown=[on_shutdown]
)

