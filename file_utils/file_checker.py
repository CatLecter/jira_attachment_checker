from typing import AsyncGenerator

import aiofiles.os


async def files_aiter(file_paths: list[str]) -> AsyncGenerator[str, None]:
    for f in file_paths:
        yield f


async def check_files(file_paths: list[str]) -> list[tuple[str, bool]]:
    result = []
    async for file_path in files_aiter(file_paths):
        exists = await aiofiles.os.path.exists(file_path)
        result.append((file_path, exists))
    return result
