import asyncio
from datetime import datetime
from typing import AsyncGenerator

import aiofiles.os

from jira_db_extractor.connectors.connectors import SQLiteConnector
from jira_db_extractor.connectors.repositories import SQLiteRepository
from jira_db_extractor.models.models import Attachment


class Worker:
    def __init__(self, sqlite_dsn: str, path: str, working_hours: tuple[int, int] | None = None):
        self.running = False
        self.sqlite_dsn = sqlite_dsn
        self.path = path
        if working_hours:
            self.start_at: int = working_hours[0]
            self.end_at: int = working_hours[1]
        self._sqlite_repo: SQLiteRepository | None = None
        self._file_checker = None

    async def check_working_hours(self):
        try:
            while True:
                current_hour = datetime.now().hour
                self.running = (
                    self.start_at <= current_hour < self.end_at
                )  # вызов функции, которая отменит основной цикл?
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            return

    async def run(self):
        await self._init_connections()
        while self.running:
            ...  # run
        await self._release_connections()

    async def _init_connections(self):
        self._sqlite_repo = SQLiteRepository(await SQLiteConnector.create(self.sqlite_dsn))
        self._file_checker = ...

    async def _release_connections(self):
        await self._sqlite_repo.close()
        await self._file_checker.close()


async def files_aiter(file_paths: list[str]) -> AsyncGenerator[str, None]:
    for f in file_paths:
        yield f


async def check_files(file_paths: list[str]) -> list[tuple[str, bool]]:
    result = []
    async for file_path in files_aiter(file_paths):
        exists = await aiofiles.os.path.exists(file_path)
        result.append((file_path, exists))
    return result


async def get_unprocessed_attachments(context) -> list[Attachment]:
    sqlite_repo = context.get('sqlite_repo')
    attachments = await sqlite_repo.get_unprocessed_attachments()
    await sqlite_repo.close()
    return attachments


async def main(base_path: str):
    # attachments = []
    # statuses = await check_files([f'{base_path}/{a.path}' for a in attachments])
    # print(statuses)
    ...


if __name__ == '__main__':
    dir_path = '/home/tmpd/Projects/file_checker/jira/data/attachments'

    asyncio.run(main(dir_path))
