import asyncio
from asyncio import gather

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from settings import settings

ids = [-4614214898, 376661040]


class TGBot:
    def __init__(self, token):
        self._bot = Bot(token=token)
        self._dp = Dispatcher()
        self.process_message = self._dp.message(Command('get_id'))(self.process_message)

    async def process_message(self, message: Message):
        print(self)
        print(message)
        message_parts = []
        if message.chat.type != 'private':
            message_parts.append(f'id группы - {message.chat.id}')
        message_parts.append(f'Ваш id - {message.from_user.id}')
        await message.reply('\n'.join(message_parts))

    async def _wait(self):
        await asyncio.sleep(10)
        for i in ids:
            await self._bot.send_message(i, 'hello')

    async def main(self):
        await asyncio.gather(self._dp.start_polling(self._bot), self._wait())

    async def send_message(self):
        # await self._bot.send_message()
        ...


if __name__ == '__main__':
    b = TGBot(settings.bot_token)
    asyncio.run(b.main())
