import asyncio

from voyo.db.pg import ConnectionPool, set_default_pool, transaction

DSN = "postgres://ai_user:ai_user_123456@114.55.172.16:5432/ai_db"


async def main():
    pool = ConnectionPool(dsn=DSN)
    set_default_pool(pool)

    @transaction()
    async def setup(conn=None):
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS voyo_test_users (
                id   SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                age  INT
            )
            """
        )

    @transaction()
    async def insert_user(name: str, age: int, conn=None):
        return await conn.fetchval(
            "INSERT INTO voyo_test_users (name, age) VALUES ($1, $2) RETURNING id",
            name,
            age,
        )

    @transaction()
    async def list_users(conn=None):
        return await conn.fetch("SELECT id, name, age FROM voyo_test_users ORDER BY id")

    @transaction()
    async def nested_demo(name: str, conn=None):
        uid = await insert_user(name, 0)
        return uid

    await setup()

    uid1 = await insert_user("alice", 30)
    uid2 = await insert_user("bob", 25)
    print(f"inserted: {uid1}, {uid2}")

    users = await list_users()
    print("users:", [dict(r) for r in users])

    uid3 = await nested_demo("carol")
    print(f"nested inserted: {uid3}")

    users = await list_users()
    print("users after nested:", [dict(r) for r in users])

    await pool.close()
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
