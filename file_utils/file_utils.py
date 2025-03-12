from typing import AsyncGenerator

import aiofiles.os

from db_utils.models.models import Attachment


async def attachments_aiter(attachments: list[Attachment]) -> AsyncGenerator[Attachment, None]:
    for a in attachments:
        yield a


async def check_file_status(attachment: Attachment, full_path: str, uid: int, gid: int, mode: str) -> tuple[dict, str]:
    # ( missing, uid/guid, mode, wrong_size), message
    message_parts = []
    result = {'missing': False, 'wrong_uid_gid': False, 'wrong_mode': False, 'wrong_size': False}
    exists = await aiofiles.os.path.exists(full_path)
    if not exists:
        message_parts.append('missing')
        result['missing'] = True
    else:
        stat = await aiofiles.os.stat(full_path)
        file_uid = stat.st_uid
        file_gid = stat.st_gid
        if file_uid != uid:
            result['wrong_uid_gid'] = True
            message_parts.append(f'expected uid is {uid} but got {file_uid} instead')
        if file_gid != gid:
            result['wrong_uid_gid'] = True
            message_parts.append(f'expected gid is {gid} but got {file_gid} instead')
        perm = oct(stat.st_mode)[-3:]
        if perm != mode:
            result['wrong_mode'] = True
            message_parts.append(f'expected mode is {mode} but got {perm} instead')
        size = await aiofiles.os.path.getsize(full_path)
        if size != attachment.file_size:
            result['wrong_size'] = True
            message_parts.append('wrong_size')
    if not message_parts:
        message = 'ok'
    else:
        message = ','.join(message_parts)
    return result, message
