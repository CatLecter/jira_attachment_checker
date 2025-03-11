from typing import AsyncGenerator

import aiofiles.os

from db_utils.models.models import Attachment


async def attachments_aiter(attachments: list[Attachment]) -> AsyncGenerator[Attachment, None]:
    for a in attachments:
        yield a


async def check_file_status(attachment: Attachment, full_path: str):
    exists = await aiofiles.os.path.exists(full_path)
    if exists:
        size = await aiofiles.os.path.getsize(full_path)
        if size != attachment.file_size:
            status = 'wrong_size'
        else:
            status = 'ok'
    else:
        status = 'missing'
    return status
