from typing import AsyncGenerator

import aiofiles.os

from db_utils.models.models import Attachment


async def attachments_aiter(attachments: list[Attachment]) -> AsyncGenerator[Attachment, None]:
    for a in attachments:
        yield a


async def check_file_status(attachment: Attachment, full_path: str, uid: int, gid: int, mode: str):
    exists = await aiofiles.os.path.exists(full_path)
    if not exists:
        return 'missing'
    statuses = []
    stat = await aiofiles.os.stat(full_path)
    file_uid = stat.st_uid
    file_gid = stat.st_gid
    if file_uid != uid:
        statuses.append(f'uid {file_uid} instead of {uid}')
    if file_gid != gid:
        statuses.append(f'gid {file_gid} instead of {gid}')
    perm = oct(stat.st_mode)[-3:]
    if perm != mode:
        statuses.append(f'mode {perm} instead of {mode}')
    size = await aiofiles.os.path.getsize(full_path)
    if size != attachment.file_size:
        statuses.append('wrong_size')
    if not statuses:
        return 'ok'
    return ','.join(statuses)
