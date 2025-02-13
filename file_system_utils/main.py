import asyncio
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


if __name__ == '__main__':
    filepaths = []
    with open('files.csv', 'r') as csv:
        for line in csv:
            filepaths.append(f'.../file_checker/jira/data/attachments/{line.strip()}')
    result = asyncio.run(check_files(filepaths))
    print(result)
