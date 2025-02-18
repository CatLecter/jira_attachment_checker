import abc
import os.path

from jira_db_extractor.connectors.connectors import AbstractConnector
from jira_db_extractor.models.models import Attachment


class AbstractRepository(abc.ABC):
    def __init__(self, connector: AbstractConnector):
        self._connector = connector

    async def close(self):
        await self._connector.close()


class AttachmentPGRepository(AbstractRepository):
    async def get_file_attachments(self, offset: int = None, limit: int = None):
        attachments = await self._connector.fetch_all(
            """
            select fa.id as attachment_id, fa.filename, fa.filesize, fa.mimetype, ji.issuenum, p.id as project_id,
            p.pkey as project_key from fileattachment fa join jiraissue ji on ji.id = fa.issueid
            join project p on p.id = ji.project;
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
    async def create_table(self):
        await self._connector.execute(
            """create table if not exists attachments (
                attachment_id INTEGER PRIMARY KEY,
                filename text NOT NULL,
                file_size INTEGER,
                file_mime_type text,
                issue_num INTEGER,
                project_id INTEGER,
                path text,
                processed INTEGER
            );"""
        )
        await self._connector.execute(
            """
            create table if not exists launch_time (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            timestamp DATETIME);
            """
        )

    async def save_launch_time(self):
        await self._connector.execute('insert into launch_time(timestamp) values(CURRENT_TIMESTAMP)')

    async def get_latest_launch_time(self):
        result = await self._connector.fetch_one('select timestamp from launch_time order by id desc limit 1;')
        return result

    async def save_attachments(self, attachments: list[Attachment]):
        await self._connector.execute_many(
            """
            insert into attachments (attachment_id,filename,file_size,file_mime_type,issue_num,project_id,path,processed)
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

    async def get_unprocessed_attachments(self) -> list[Attachment]:
        rows = await self._connector.fetch_all('select * from attachments where processed = 0;')
        result = []
        for row in rows:
            result.append(Attachment(*row))
        return result
