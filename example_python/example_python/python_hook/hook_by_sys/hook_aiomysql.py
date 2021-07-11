import importlib
import time
import sys
from functools import wraps

from typing import cast, Any, Callable, Optional, Tuple, TYPE_CHECKING
from types import ModuleType
if TYPE_CHECKING:
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


class MetaPathFinder:

    @staticmethod
    def find_module(fullname: str, path: Optional[str] = None) -> Optional["MetaPathLoader"]:
        if fullname == 'aiomysql':
            return MetaPathLoader()
        else:
            return None


class MetaPathLoader:

    @staticmethod
    def load_module(fullname: str):
        if fullname in sys.modules:
            return sys.modules[fullname]
        # 防止递归调用
        finder: "MetaPathFinder" = sys.meta_path.pop(0)
        # 导入 module
        module: ModuleType = importlib.import_module(fullname)
        module.Cursor._query = func_wrapper(module.Cursor._query)
        sys.meta_path.insert(0, finder)
        return module


async def test_mysql() -> None:
    import aiomysql
    pool: aiomysql.Pool = await aiomysql.create_pool(
        host='127.0.0.1', port=3306, user='root', password='', db='mysql'
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 42;")
            (r,) = await cur.fetchone()
            assert r == 42
    pool.close()
    await pool.wait_closed()

if __name__ == '__main__':
    sys.meta_path.insert(0, MetaPathFinder())
    import asyncio

    asyncio.run(test_mysql())
