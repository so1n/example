import asyncio
import aiomysql

from demo import install_hook, reset_hook


async def test_mysql() -> None:
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

print("install hook")
install_hook()
asyncio.run(test_mysql())
print("reset hook")
reset_hook()
asyncio.run(test_mysql())
print("end")
