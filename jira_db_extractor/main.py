import asyncio

import asyncpg

from jira_db_extractor.connectors.postgres_connector import PGConnector

'''
select fa.id, fa.filename, ji.issuenum from fileattachment fa join jiraissue ji on ji.id = fa.issueid join project p on p.id = ji.project where p.pkey = 'PRG';
select fa.id, fa.filename, ji.issuenum, p.id from fileattachment fa join jiraissue ji on ji.id = fa.issueid join project p on p.id = ji.project;

<JIRA_HOME>/data/attachments/<PROJECT>/<BUCKET>/<ISSUE_KEY>/<ID>

'BUCKET' refers to which group of 10,000 items the file falls into. 
Since the issuenum is 11, it will be in the "10000" bucket.  
(An issuenum between 1 and 10000 would be bucket 10000, 
whereas an issuenum between 10001 and 20000 would be in bucket 20000.)
'''


async def main(dsn):
    connector = await PGConnector.create(dsn)
    attachments = await connector.get_file_attachments()
    print(attachments)


if __name__ == '__main__':
    dsn = 'postgres://admin:admin@127.0.0.1:5432/db'

    asyncio.run(main(dsn))
