import asyncio
from datetime import datetime

import aiofiles.os

from db_utils.connectors.connectors import PGConnector, SQLiteConnector
from db_utils.connectors.repositories import AttachmentPGRepository, SQLiteRepository
from db_utils.models.models import Attachment
from file_utils.file_checker import attachments_aiter

# parameters todo:move to settings
FETCH_TASKS_PERIOD = 600
PG_BATCH_SIZE = 1000
FILE_BATCH_SIZE = 100


class Worker:
    def __init__(self, sqlite_dsn: str, pg_dns: str, path: str, working_hours: tuple[int, int] | None = None):
        self.running = False
        self.sqlite_dsn = sqlite_dsn
        self.pg_dsn = pg_dns
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
                    self.start_at <= current_hour < self.end_at  # todo инвертировать
                )  # вызов функции, которая отменит основной цикл?
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            return

    async def main_loop(self):
        raise NotImplementedError

    async def run(self):
        await self._init_connections()
        while self.running:
            # get last time when tasks was gathered from jira
            seconds_since_tasks_gathered = await self._sqlite_repo.seconds_from_last_launch()
            # if elapsed time since then is more than parameter:
            if seconds_since_tasks_gathered > FETCH_TASKS_PERIOD:
                # gather tasks from jira again
                offset = 0
                while True:
                    attachments = await self._pg_repo.get_file_attachments(limit=PG_BATCH_SIZE, offset=offset)
                    if not attachments:
                        break
                    await self._sqlite_repo.save_attachments(attachments)
                    offset += PG_BATCH_SIZE

            offset = 0
            while True:
                # get batch of attachments from sqlite repo
                attachments = await self._sqlite_repo.get_unprocessed_attachments(limit=FILE_BATCH_SIZE, offset=offset)
                # for each attachment in batch:
                async for a in attachments_aiter(attachments):
                    #   check if attachment has any problems in filesystem
                    exists = await aiofiles.os.path.exists(a.path)
                    await self._sqlite_repo.save_attachment_report(a, exists)

                    #   if attachment has problems:
                    #       write down to sqlite repo that attachment and reason
                    #   mark attachment as processed in sqlite repo
        await self._release_connections()

    async def create_report(self):
        raise NotImplementedError

    async def _init_connections(self):
        self._sqlite_repo = SQLiteRepository(await SQLiteConnector.create(self.sqlite_dsn))
        self._pg_repo = AttachmentPGRepository(await PGConnector.create(self.pg_dsn))
        self._file_checker = None

    async def _release_connections(self):
        await self._sqlite_repo.close()
        await self._file_checker.close()


async def get_unprocessed_attachments(context) -> list[Attachment]:
    sqlite_repo = context.get('sqlite_repo')
    attachments = await sqlite_repo.get_unprocessed_attachments()
    await sqlite_repo.close()
    return attachments


async def main(base_path: str):
    # attachments = []
    # statuses = await check_files([f'{base_path}/{a.path}' for a in attachments])
    # print(statuses)
    raise NotImplementedError


if __name__ == '__main__':
    dir_path = '/home/tmpd/Projects/file_checker/jira/data/attachments'

    asyncio.run(main(dir_path))
