from typing import AsyncGenerator

from db_utils.models.models import Attachment


async def attachments_aiter(attachments: list[Attachment]) -> AsyncGenerator[Attachment, None]:
    for a in attachments:
        yield a
