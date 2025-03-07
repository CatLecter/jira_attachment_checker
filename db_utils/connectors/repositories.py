import abc
import asyncio
import datetime
import os.path

from db_utils.connectors.connectors import AbstractConnector, SQLiteConnector
from db_utils.models.models import Attachment


class AbstractRepository(abc.ABC):
    def __init__(self, connector: AbstractConnector):
        self._connector = connector

    async def close(self):
        await self._connector.close()


class AttachmentPGRepository(AbstractRepository):
    async def get_file_attachments(self, offset: int = None, limit: int = None):
        limit_str = f' limit={limit}' if limit else ''
        offset_str = f' offset={offset}' if offset else ''
        attachments = await self._connector.fetch_all(
            f"""
            select fa.id as attachment_id, fa.filename, fa.filesize, fa.mimetype, ji.issuenum, p.id as project_id,
            p.pkey as project_key from fileattachment fa join jiraissue ji on ji.id = fa.issueid
            join project p on p.id = ji.project{limit_str}{offset_str};
            """
        )
        result = []
        for a in attachments:
            issue_num = int(a.get('issuenum'))
            bucket = str((((issue_num - 1) // 10000) + 1) * 10000)
            project_key = str(a.get('project_key'))
            issue_key = f'{project_key}-{issue_num}'
            attachment_id = int(a.get('attachment_id'))
            path = os.path.join(project_key, bucket, issue_key, str(attachment_id))
            attachment_filename = a.get('filename')
            project_id = int(a.get('project_id'))
            file_size = int(a.get('filesize'))
            file_mime_type = a.get('mimetype')
            result.append(
                Attachment(
                    attachment_id,
                    attachment_filename,
                    file_size,
                    file_mime_type,
                    issue_num,
                    project_id,
                    path,
                )
            )
        return result


class SQLiteRepository(AbstractRepository):
    async def save_launch_time(self):
        await self._connector.execute("insert into launch_time(timestamp) values(datetime('now','localtime'))")

    async def update_attachments(self, attachments: list[Attachment]):
        values = [(str(a.id),) for a in attachments]
        await self._connector.execute_many(f'update attachments set processed = 1 where attachment_id = ?', values)

    async def save_attachment_reports(self, attachments: list[tuple[Attachment, str, str]]):
        values = []
        for a, path, status in attachments:
            values.append([a.id, a.filename, path, status, a.project_id])
            await self._connector.execute_many(
                f"""
                        insert or ignore into reports(
                            attachment_id,
                            filename,
                            full_path,
                            status,
                            project_name
                        ) values (
                            ?,
                            ?,
                            ?,
                            ?,
                            ?
                        );
                    """,
                values,
            )

    async def seconds_from_last_launch(self) -> int:
        records = await self._connector.fetch_one('select timestamp from launch_time order by id desc limit 1;')
        if records:

            last_launch_time = datetime.datetime.strptime(records[0], '%Y-%m-%d %H:%M:%S')
            time_since_last_launch = datetime.datetime.now() - last_launch_time

            return time_since_last_launch.seconds
        else:
            return 0

    async def save_attachments(self, attachments: list[Attachment]):
        await self._connector.execute_many(
            """
            insert or ignore into attachments (attachment_id,filename,file_size,file_mime_type,issue_num,project_id,path,processed)
            values (?,?,?,?,?,?,?,?);
            """,
            [
                (
                    a.id,
                    a.filename,
                    a.file_size,
                    a.file_mime_type,
                    a.issue_num,
                    a.project_id,
                    a.path,
                    False,
                )
                for a in attachments
            ],
        )
        await self.save_launch_time()

    async def get_unprocessed_attachments(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[Attachment]:
        limit_str = f' limit {limit}' if limit else ''
        offset_str = f' offset {offset}' if offset else ''
        rows = await self._connector.fetch_all(f'select * from attachments where processed = 0{limit_str}{offset_str};')
        result = []
        for row in rows:
            result.append(Attachment(*row))
        return result


async def test():
    repo = SQLiteRepository(await SQLiteConnector.create('test.db'))
    time_elapsed = await repo.seconds_from_last_launch()
    print(time_elapsed)

    await repo.close()


if __name__ == '__main__':
    asyncio.run(test())
