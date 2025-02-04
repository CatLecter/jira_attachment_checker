import asyncpg


class PGConnector:
    _con = None
    _pool = None

    @classmethod
    async def create(cls, dsn):
        self = cls()
        self._pool = await asyncpg.create_pool(dsn)
        self._con = await self._pool.acquire()
        return self

    async def get_file_attachments(self, offset: int = None, limit: int = None):
        attachments = await self._con.fetch(
            """
            select fa.id, fa.filename, ji.issuenum, p.id from fileattachment fa join
            jiraissue ji on ji.id = fa.issueid join project p on p.id = ji.project;
            """
        )
        return [{k: v for k, v in a.items()} for a in attachments]
