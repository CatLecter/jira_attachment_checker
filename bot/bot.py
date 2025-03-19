import asyncio

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, InputFile, Message

from settings import settings


class TGBot:
    def __init__(self, token: str, chats: list[int]):
        self._bot = Bot(token=token)
        self.chats = chats
        self._dp = Dispatcher()
        self.get_chat_id = self._dp.message(Command('get_chat_id'))(self.get_chat_id)  # noqa
        self.progress_func = self._dp.message(Command('progress'))(self.get_progress)  # noqa
        self.report_func = self._dp.message(Command('report'))(self.get_report)

    def set_progress_function(self, func):
        self.progress_func = func

    def set_report_function(self, func):
        self.report_func = func

    async def get_progress(self, message: Message):
        result = await self.progress_func()
        await message.reply(result)

    async def get_report(self, message: Message):
        summary, report = await self.report_func()
        await message.answer_document(BufferedInputFile(report.encode('utf-8'), filename='report.csv'), caption=summary)

    async def get_chat_id(self, message: Message):
        message_parts = []
        if message.chat.type != 'private':
            message_parts.append(f'id группы - {message.chat.id}')
        message_parts.append(f'Ваш id - {message.from_user.id}')
        await message.reply('\n'.join(message_parts))

    async def run(self):
        await self._dp.start_polling(self._bot)

    async def send_message(self, message_text: str):
        for chat in self.chats:
            await self._bot.send_message(chat, message_text)

    async def close(self):
        await self._dp.stop_polling()
        await self._bot.close()
