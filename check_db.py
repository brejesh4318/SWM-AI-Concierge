import asyncio

from sqlalchemy import text

from app.db.session import engine


TABLES = text(
    "select tablename from pg_tables "
    "where schemaname = 'public' order by 1"
)

COLUMNS = text(
    "select column_name, data_type from information_schema.columns "
    "where table_name = :t order by ordinal_position"
)


async def main():
    """Print the connected database, its tables and the key table columns.

    Connects with the application's engine, lists the tables in the
    public schema, then prints the column names and types of the
    'complaints' and 'conversation_state' tables.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the database cannot be reached
            or a query fails.
    """
    async with engine.connect() as connection:
        print("CONNECTED:", (
            await connection.execute(text("select current_database()"))
        ).scalar())

        tables = (await connection.execute(TABLES)).scalars().all()
        print("tables:", tables)

        for table in ("complaints", "conversation_state"):
            rows = (
                await connection.execute(COLUMNS, {"t": table})
            ).all()
            print(f"\n{table} ({len(rows)} columns)")
            for name, kind in rows:
                print(f"   {name:<20} {kind}")


asyncio.run(main())
