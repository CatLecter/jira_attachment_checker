import datetime
from typing import Callable

import aiofiles
import aiofiles.os
import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, FSInputFile, InputFile, KeyboardButton, Message, ReplyKeyboardMarkup

from settings import settings


class TGBot:
    def __init__(self, token: str, chats: list[int]):
        self._bot = Bot(token=token)
        self.chats = chats
        self._dp = Dispatcher()
        self._dp.message.register(self.get_chat_id, Command('get_chat_id'))
        self._dp.message.register(self.progress_command, Command('progress'))
        self._dp.message.register(self.report_command, Command('report'))
        self.progress_handler: Callable | None = None
        self.report_handler: Callable | None = None

    def set_progress_function(self, handler):
        self.progress_handler = handler

    def set_report_function(self, handler):
        self.report_handler = handler

    async def progress_command(self, message: Message):
        result = await self.progress_handler()
        await message.reply(result)

    async def report_command(self, message: Message, state: FSMContext):
        await state.set_state('choose_report_format')
        await message.answer(
            'В каком виде нужно предоставить отчет?',
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='csv'), KeyboardButton(text='sqlite')]]),
        )

    async def csv_report(self, message: Message, state: FSMContext):
        summary, columns, rows = await self.report_handler()
        await message.answer(summary)
        f_name = f'report_{datetime.datetime.now().strftime(settings.time_format)}'
        f_name_full = f'{f_name}.csv'
        async with aiofiles.open(f_name_full, 'w') as f:
            await f.write(f'{settings.delimiter.join(columns)}\n')
            for row in rows:
                await f.write(f'{settings.delimiter.join(row)}\n')

        report_size = await aiofiles.os.path.getsize(f_name_full)
        if report_size > 50 * 1024 * 1024:
            await state.set_state('file_too_large')
            await state.update_data(columns=columns, rows=rows, filename=f_name)
            await message.answer(
                f'Файл отчета слишком большой для отправки через Telegram ({report_size} б). '
                f'Обратитесь к системному администратору для получения файла {f_name_full}, '
                f'либо получите файл отчета по частям.\nПолучить файл по частям?',
                reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Да'), KeyboardButton(text='Нет')]]),
            )
        else:
            await state.set_state('idle')
            await message.answer_document(FSInputFile(f_name_full, filename='report.csv'))

    async def send_report_parts(self, message: Message, state: FSMContext):
        columns = await state.get_value('columns')
        rows = await state.get_value('rows')
        filename = await state.get_value('filename')
        ext = 'csv'
        row_index = 0
        report_num = 1
        has_next = True
        while has_next:
            msg_bytes = bytearray(f'{settings.delimiter.join(columns)}\n'.encode('utf-8'))
            while len(msg_bytes) < 50 * 1024 * 1024:
                msg_bytes.extend(f'{settings.delimiter.join(rows[row_index])}\n'.encode('utf-8'))
                row_index += 1
                if row_index >= len(rows):
                    has_next = False
                    break

            part_filename = f'{filename}-{report_num}.{ext}'

            await message.answer_document(BufferedInputFile(bytes(msg_bytes), filename=part_filename))
            report_num += 1
        await state.set_state('idle')

    async def sqlite_report(self, message: Message, state: FSMContext):
        columns = await state.get_value('columns')
        rows = await state.get_value('rows')
        filename = await state.get_value('filename')
        async with aiosqlite.connect(f'{filename}.sqlite') as db:
            # todo types
            ...

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
