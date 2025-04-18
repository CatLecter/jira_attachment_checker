import abc
import asyncio
import datetime
import os.path
from functools import reduce

from db_utils.connectors import AbstractConnector, SQLiteConnector
from db_utils.models import Attachment
from settings import settings


class AbstractRepository(abc.ABC):
    def __init__(self, connector: AbstractConnector):
        self._connector = connector

    async def close(self):
        await self._connector.close()


class AttachmentPGRepository(AbstractRepository):
    async def get_file_attachments(self, offset: int = None, limit: int = None):
        limit_str = f' limit {limit}' if limit else ''
        offset_str = f' offset {offset}' if offset else ''
        attachments = await self._connector.fetch_all(
            f"""
            select fa.id as attachment_id, fa.filename, fa.filesize, fa.mimetype, ji.issuenum, ji.created, ji.updated,
            p.id as project_id, p.pkey as project_key,p.pname as project_name from fileattachment fa join jiraissue ji
            on ji.id = fa.issueid join project p on p.id = ji.project{limit_str}{offset_str};
            """
        )
        result = []
        for a in attachments:
            issue_num = int(a.get('issuenum'))
            bucket = str((((issue_num - 1) // 10000) + 1) * 10000)
            project_key = str(a.get('project_key'))
            project_name = str(a.get('project_name'))
            issue_key = f'{project_key}-{issue_num}'
            attachment_id = int(a.get('attachment_id'))
            path = os.path.join(project_key, bucket, issue_key, str(attachment_id))
            attachment_filename = a.get('filename')
            project_id = int(a.get('project_id'))
            file_size = int(a.get('filesize'))
            file_mime_type = a.get('mimetype')
            created = a.get('created')
            updated = a.get('updated')
            result.append(
                Attachment(
                    attachment_id,
                    attachment_filename,
                    file_size,
                    file_mime_type,
                    issue_num,
                    created,
                    updated,
                    project_id,
                    project_name,
                    path,
                )
            )
        return result


class SQLiteRepository(AbstractRepository):
    async def save_launch_time(self):
        launch_time = datetime.datetime.now().strftime(settings.time_format)
        await self._connector.execute(f"update parameters set value = '{launch_time}' where name = 'launch_time';")

    async def update_attachments(self, attachments: list[Attachment]):
        values = [(str(a.id),) for a in attachments]
        await self._connector.execute_many(f'update attachments set processed = 1 where attachment_id = ?', values)

    async def get_progress(self) -> str:
        rows = await self._connector.fetch_all('select processed,count(*) from attachments group by processed;')
        count_dict = {}
        if rows:
            for row in rows:
                count_dict[row[0]] = row[1]
            total_items_count = reduce(lambda x, y: x + y, count_dict.values())
            message = (
                f'Обработано {count_dict.get(1, 0)} вложений из {total_items_count}, '
                f'{100 * (count_dict.get(1, 0) / total_items_count):.2f} %'
            )
            return message
        else:
            return 'Во внутренней базе отсутствуют записи о вложениях.'

    async def save_attachment_reports(self, attachments: list[tuple[Attachment, str, dict, str]]):
        values = []
        for a, path, status_dict, message in attachments:
            values.append(
                [
                    a.id,
                    a.filename,
                    path,
                    a.project_name,
                    a.issue_name,
                    a.created.strftime(settings.time_format),
                    a.updated.strftime(settings.time_format),
                    status_dict.get('missing', False),
                    status_dict.get('wrong_uid_gid', False),
                    status_dict.get('wrong_mode', False),
                    status_dict.get('wrong_size', False),
                    message,
                ]
            )
            await self._connector.execute_many(
                f"""
                        insert or ignore into reports(
                            attachment_id,
                            filename,
                            full_path,
                            project_name,
                            issue_name,
                            created,
                            updated,
                            file_missing,
                            wrong_uid_gid,
                            wrong_mode,
                            wrong_size,
                            status
                        ) values (
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?
                        );
                    """,
                values,
            )

    async def get_total_attachments(self):
        result = await self._connector.fetch_one('select count(*) from attachments;')
        return result[0]

    async def seconds_from_last_launch(self) -> int:
        records = await self._connector.fetch_one('select value from parameters where name="launch_time";')
        if records:

            last_launch_time = datetime.datetime.strptime(records[0], settings.time_format)
            time_since_last_launch = datetime.datetime.now() - last_launch_time

            return time_since_last_launch.seconds
        else:
            return -1

    async def save_attachments(self, attachments: list[Attachment]):
        await self._connector.execute_many(
            """
            insert or ignore into attachments (
                attachment_id,
                filename,
                file_size,
                file_mime_type,
                issue_num,
                created,
                updated,
                project_id,
                project_name,
                path,
                processed)
            values (
                ?,?,?,?,?,?,?,?,?,?,?
            );
            """,
            [
                (
                    a.id,
                    a.filename,
                    a.file_size,
                    a.file_mime_type,
                    a.issue_num,
                    a.created.strftime(settings.time_format),
                    a.updated.strftime(settings.time_format),
                    a.project_id,
                    a.project_name,
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

    async def get_reports_full(self):
        rows = await self._connector.fetch_all('select * from reports;')
        return rows

    async def get_report_short(self):
        rows = await self._connector.fetch_all(
            'select * from reports where '
            'file_missing = 1 '
            'or wrong_uid_gid = 1 '
            'or wrong_mode = 1 '
            'or wrong_size = 1;'
        )
        return rows


async def test():
    repo = SQLiteRepository(await SQLiteConnector.create('test.db'))
    time_elapsed = await repo.seconds_from_last_launch()
    print(time_elapsed)

    await repo.close()


if __name__ == '__main__':
    asyncio.run(test())
