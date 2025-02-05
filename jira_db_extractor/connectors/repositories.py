import abc

from jira_db_extractor.connectors.connectors import AbstractConnector, SQLiteConnector
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
            select fa.id, fa.filename, ji.issuenum, p.id as project_id from fileattachment fa join
            jiraissue ji on ji.id = fa.issueid join project p on p.id = ji.project;
            """
        )
        return [Attachment(int(a.get('id')),
                           a.get('filename'),
                           int(a.get('issuenum')),
                           int(a.get('project_id'))) for a in attachments]


class AttachmentSQLiteRepository(AbstractRepository):

    async def create_table(self):
        await self._connector.execute(
            """create table if not exists attachments (
                id INTEGER PRIMARY KEY,
                filename text NOT NULL,
                issue_num INTEGER,
                project_id INTEGER,
                processed INTEGER
            );"""
        )

    async def save_attachments(self, attachments: list[Attachment]):
        await self.create_table()
        await self._connector.execute_many(
            """
            insert into attachments (id,filename,issue_num,project_id,processed)
            values (?,?,?,?,?);            
            """,
            [(a.id, a.filename, a.issue_num, a.project_id, False) for a in attachments]
        )
