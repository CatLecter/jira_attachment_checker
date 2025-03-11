import abc
from typing import Collection

import aiosqlite
import asyncpg
from asyncpg import Connection, Pool
from pydantic import PostgresDsn


class AbstractConnector(abc.ABC):
    @classmethod
    @abc.abstractmethod
    async def create(cls, dsn):
        pass

    @abc.abstractmethod
    async def close(self):
        pass

    @abc.abstractmethod
    async def execute(self, query: str):
        pass

    @abc.abstractmethod
    async def execute_many(self, query: str, rows: Collection):
        pass

    @abc.abstractmethod
    async def fetch_all(self, query: str):
        pass

    @abc.abstractmethod
    async def fetch_one(self, query: str):
        pass


class PGConnector(AbstractConnector):
    async def execute_many(self, query: str, rows: Collection):
        pass

    _con: None | Connection = None
    _pool: None | Pool = None

    @classmethod
    async def create(cls, dsn):
        self = cls()
        if isinstance(dsn, PostgresDsn):
            dsn = str(dsn)
        self._pool = await asyncpg.create_pool(dsn)
        self._con = await self._pool.acquire()
        return self

    async def close(self):
        pass

    async def execute(self, query: str):
        pass

    async def fetch_all(self, query: str):
        result = await self._con.fetch(query)
        return result

    async def fetch_one(self, query: str):
        pass


class SQLiteConnector(AbstractConnector):
    _db: aiosqlite.Connection = None

    @classmethod
    async def create(cls, dsn):
        self = cls()
        self._db = await aiosqlite.connect(dsn)
        return self

    async def close(self):
        await self._db.close()

    async def execute(self, query: str):
        cur = await self._db.execute(query)
        await self._db.commit()
        await cur.close()

    async def execute_many(self, query: str, rows: Collection):
        cur = await self._db.executemany(query, rows)
        await self._db.commit()
        await cur.close()

    async def fetch_all(self, query: str):
        async with self._db.execute(query) as cursor:
            result = await cursor.fetchall()
        return result

    async def fetch_one(self, query: str):
        async with self._db.execute(query) as cursor:
            result = await cursor.fetchone()
        return result
