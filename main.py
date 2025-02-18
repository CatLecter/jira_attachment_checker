import asyncio
from typing import AsyncGenerator

import aiofiles.os

from jira_db_extractor.connectors.connectors import SQLiteConnector
from jira_db_extractor.connectors.repositories import SQLiteRepository
from jira_db_extractor.models.models import Attachment


async def files_aiter(file_paths: list[str]) -> AsyncGenerator[str, None]:
    for f in file_paths:
        yield f


async def check_files(file_paths: list[str]) -> list[tuple[str, bool]]:
    result = []
    async for file_path in files_aiter(file_paths):
        exists = await aiofiles.os.path.exists(file_path)
        result.append((file_path, exists))
    return result


async def get_unprocessed_attachments(sqlite_repo: SQLiteRepository) -> list[Attachment]:
    attachments = await sqlite_repo.get_unprocessed_attachments()
    await sqlite_repo.close()
    return attachments


async def main(sqlite_dsn: str):
    sqlite_repo = SQLiteRepository(await SQLiteConnector.create(sqlite_dsn))
    attachments = await get_unprocessed_attachments(sqlite_repo)
    base_path = '/home/tmpd/Projects/file_checker/jira/data/attachments'
    statuses = await check_files([f'{base_path}/{a.path}' for a in attachments])
    print(statuses)


if __name__ == '__main__':
    result = asyncio.run(main('./db.sqlite'))
