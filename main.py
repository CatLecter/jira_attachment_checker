import asyncio
from typing import AsyncGenerator

import aiofiles.os
import arq
from arq import Worker
from arq.connections import RedisSettings, create_pool

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


async def get_unprocessed_attachments(context) -> list[Attachment]:
    sqlite_repo = context.get('sqlite_repo')
    attachments = await sqlite_repo.get_unprocessed_attachments()
    await sqlite_repo.close()
    return attachments


async def on_startup(context):
    context['sqlite_repo'] = SQLiteRepository(await SQLiteConnector.create(context.get('sqlite_dsn')))


async def on_shutdown(context):
    await context.get('sqlite_repo').close


async def main(base_path: str, redis_settings: RedisSettings):
    w = Worker(
        redis_settings=redis_settings,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
    )
    pool = w.pool
    job = await pool.enqueue_job('get_unprocessed_attachements')
    attachments = await job.result(timeout=5)
    statuses = await check_files([f'{base_path}/{a.path}' for a in attachments])
    print(statuses)


if __name__ == '__main__':
    rs = RedisSettings()
    ctx = {
        'sqlite_dsn': './db.sqlite',
    }
    dir_path = '/home/tmpd/Projects/file_checker/jira/data/attachments'

    asyncio.run(main(dir_path, rs))
