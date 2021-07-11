import time
from functools import wraps
from typing import Any, Callable, Tuple, cast

import aiomysql


def func_wrapper(func: Callable):
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        start: float = time.time()
        func_result: Any = await func(*args, **kwargs)
        end: float = time.time()
        self: aiomysql.Cursor = args[0]
        sql: str = args[1]
        db: str = self._connection.db
        user: str = self._connection.user
        host: str = self._connection.host
        port: str = self._connection.port
        execute_result: Tuple[Tuple] = self._rows
        print({
            "sql": sql,
            "db": db,
            "user": user,
            "host": host,
            "port": port,
            "result": execute_result,
            "speed time": end - start
        })
        return func_result
    return cast(Callable, wrapper)


_IS_HOOK: bool = False
_query: Callable = aiomysql.Cursor._query


def install_hook() -> None:
    global _IS_HOOK
    if _IS_HOOK:
        return
    aiomysql.Cursor._query = func_wrapper(aiomysql.Cursor._query)
    _IS_HOOK = True


def reset_hook() -> None:
    aiomysql.Cursor._query = _query
    _IS_HOOK = False
