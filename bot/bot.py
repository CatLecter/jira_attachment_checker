import datetime
import math
from typing import Callable

import aiofiles
import aiofiles.os
import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, FSInputFile, KeyboardButton, Message, ReplyKeyboardMarkup
from aiogram.types import ReplyKeyboardRemove

from bot.states import ParseState
from settings import logger, settings


class TGBot:
    def __init__(self, token: str, chats: list[int]):
        self._bot = Bot(token=token)
        self.chats = chats
        self._dp = Dispatcher()
        self._dp.message.register(self.get_chat_id, Command('get_chat_id'))
        self._dp.message.register(self.progress_command, Command('progress'))
        self._dp.message.register(self.report_command, Command('report'))
        self._dp.message.register(self.cancel, Command('cancel'))
        self._dp.message.register(self.choose_csv_sqlite, ParseState.csv_sqlite)
        self._dp.message.register(self.csv_too_large, ParseState.csv_too_large)
        self._dp.message.register(self.work_in_progress, ParseState.work_in_progress)
        self.progress_handler: Callable | None = None
        self.report_handler: Callable | None = None

    def set_progress_function(self, handler):
        logger.debug(f'Установлена функция обработки прогресса {handler.__name__}')
        self.progress_handler = handler

    def set_report_function(self, handler):
        logger.debug(f'Установлена функция создания отчета {handler.__name__}')
        self.report_handler = handler

    async def progress_command(self, message: Message):
        logger.debug('Введена команда отображения прогресса')
        result = await self.progress_handler()
        await message.reply(result)

    async def cancel(self, message: Message, state: FSMContext):
        logger.debug('Введена команда отмены')
        await state.set_state(ParseState.idle)
        await message.answer('Отмена', reply_markup=ReplyKeyboardRemove())

    async def work_in_progress(self, message: Message, state: FSMContext):
        await message.answer('Отчет генерируется, пожалуйста подождите.', reply_markup=ReplyKeyboardRemove())

    async def report_command(self, message: Message, state: FSMContext):
        cur_state = await state.get_state()
        if not cur_state:
            await state.set_state(ParseState.idle)
            cur_state = await state.get_state()
        logger.debug(f'Введена команда получения отчета, текущее состояние: {cur_state}')
        if cur_state != ParseState.idle:
            await message.answer(
                'Начат процесс получения отчета. Для отмены отправьте команду /cancel',
                reply_markup=ReplyKeyboardRemove(),
            )
            # todo cancel processing
        else:
            await message.answer('Получение данных из базы, пожалуйста подождите.')
            summary, columns, rows = await self.report_handler()
            f_name = f'report_{datetime.datetime.now().strftime(settings.time_format)}'
            await state.update_data(columns=columns, rows=rows, filename=f_name, summary=summary)
            await message.answer(
                'В каком виде нужно предоставить отчет?',
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text='csv'), KeyboardButton(text='sqlite')]]
                ),
            )
            await state.set_state(ParseState.csv_sqlite)

    async def choose_csv_sqlite(self, message: Message, state: FSMContext):
        logger.debug('Выбор типа отчета')
        text = message.text
        if text == 'csv':
            logger.debug('Выбран тип отчета csv')
            await state.set_state(ParseState.csv)
            await message.reply('Выбран тип отчета csv', reply_markup=ReplyKeyboardRemove())
            await self.csv_report(message, state)
        elif text == 'sqlite':
            logger.debug('Выбран тип отчета sqlite')
            await state.set_state(ParseState.sqlite)
            await message.reply('Выбран тип отчета sqlite', reply_markup=ReplyKeyboardRemove())
            await self.sqlite_report(message, state)
        else:
            logger.debug('Ошибка выбора типа отчета')
            await message.answer(
                'Пожалуйста, выберите формат отчета.',
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text='csv'), KeyboardButton(text='sqlite')]]
                ),
            )

    async def csv_report(self, message: Message, state: FSMContext):
        await message.answer('Отчет генерируется, пожалуйста подождите.', reply_markup=ReplyKeyboardRemove())
        await state.set_state(ParseState.work_in_progress)
        logger.debug('Функция формирования отчета csv')
        columns = await state.get_value('columns')
        summary = await state.get_value('summary')
        rows = await state.get_value('rows')
        f_name = await state.get_value('filename')
        await message.answer(summary)
        col_names = (c[0] for c in columns)
        f_name_full = f'{f_name}.csv'
        async with aiofiles.open(f_name_full, 'w') as f:
            await f.write(f'{settings.delimiter.join(col_names)}\n')
            for row in rows:
                await f.write(f'{settings.delimiter.join(map(lambda x: str(x), row))}\n')

        report_size = await aiofiles.os.path.getsize(f_name_full)
        if report_size > settings.tg_max_file_size:
            logger.debug('Отчет csv слишком большой')
            await message.answer(
                f'Файл отчета слишком большой для отправки через '
                f'Telegram ({"%.2f" % (report_size / 1024 / 1024)} Мб). '
                f'Обратитесь к системному администратору для получения файла {f_name_full}, '
                f'либо получите файл отчета по частям.\nПолучить файл по частям?',
                reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Да'), KeyboardButton(text='Нет')]]),
            )
            await state.set_state(ParseState.csv_too_large)
        else:
            logger.debug('Отправка отчета csv')
            await message.answer_document(
                FSInputFile(f_name_full, filename='report.csv'), reply_markup=ReplyKeyboardRemove()
            )
            await state.set_state(ParseState.idle)

    async def csv_too_large(self, message: Message, state: FSMContext):
        message_text = message.text
        if message_text == 'Да':
            await state.set_state(ParseState.work_in_progress)
            logger.debug('Функция отправки отчета csv по частям')
            columns = await state.get_value('columns')
            col_names = (c[0] for c in columns)
            rows = await state.get_value('rows')
            filename = await state.get_value('filename')
            row_bytes = []
            total_size = 0
            for r in rows:
                r_b = f'{settings.delimiter.join(map(lambda x: str(x), r))}\n'.encode('utf-8')
                row_bytes.append(r_b)
                total_size += len(r_b)
            threshold = 15000
            msg_num = math.ceil(total_size / (settings.tg_max_file_size - threshold))
            await message.answer(
                f'Отчет генерируется частями по 50 Мб. Ожидается {msg_num} частей. Пожалуйста подождите',
                reply_markup=ReplyKeyboardRemove(),
            )
            ext = 'csv'
            row_index = 0
            report_num = 1
            has_next = True
            while has_next:
                msg_bytes = bytearray(f'{settings.delimiter.join(col_names)}\n'.encode('utf-8'))
                while len(msg_bytes) < (settings.tg_max_file_size - threshold):
                    msg_bytes.extend(row_bytes[row_index])
                    row_index += 1
                    if row_index >= len(row_bytes):
                        has_next = False
                        break

                part_filename = f'{filename}-{report_num}.{ext}'

                await message.answer_document(BufferedInputFile(bytes(msg_bytes), filename=part_filename))
                report_num += 1
            await state.set_state(ParseState.idle)
            await message.answer('Готово!')
        elif message_text == 'Нет':
            await message.answer('Операция отменена.', reply_markup=ReplyKeyboardRemove())
            await state.set_state(ParseState.idle)
        else:
            await message.answer('Пожалуйста, выберите один из вариантов.')

    async def sqlite_report(self, message: Message, state: FSMContext):
        await state.set_state(ParseState.work_in_progress)
        await message.answer('Генерируется отчет sqlite, пожалуйста подождите.', reply_markup=ReplyKeyboardRemove())
        logger.debug('Функция отправки отчета sqlite')
        columns = await state.get_value('columns')
        rows = await state.get_value('rows')
        filename = await state.get_value('filename')
        db_file = f'{filename}.sqlite'
        async with aiosqlite.connect(db_file) as db:
            q_col_names_with_types = ','.join((f'{c[0]} {c[1]}' for c in columns))
            q_col_names = ','.join((f'{c[0]} ' for c in columns))
            q_values = ','.join(['?'] * len(columns))
            await db.execute(f'create table if not exists reports({q_col_names_with_types})')
            await db.executemany(f'insert into reports ({q_col_names}) values ({q_values});', rows)
            await db.commit()
        db_size = await aiofiles.os.path.getsize(db_file)
        if db_size < settings.tg_max_file_size:
            await message.answer_document(FSInputFile(db_file, filename='db.sqlite'))
        else:
            await message.answer(
                f'Файл базы данных слишком большой для отправки '
                f'через Telegram ({"%.2f" % (db_size / 1024 / 1024)} Мб).'
                f'Обратитесь к системному администратору для получения файла {db_file}',
                reply_markup=ReplyKeyboardRemove(),
            )
        await state.set_state(ParseState.idle)

    async def get_chat_id(self, message: Message):
        message_parts = []
        if message.chat.type != 'private':
            message_parts.append(f'id группы - {message.chat.id}')
        message_parts.append(f'Ваш id - {message.from_user.id}')
        await message.reply('\n'.join(message_parts))

    async def run(self):
        logger.info('Запуск бота')
        await self._dp.start_polling(self._bot)

    async def send_message(self, message_text: str):
        logger.debug(f'Отправка сообщения {message_text}')
        for chat in self.chats:
            await self._bot.send_message(chat, message_text)

    async def close(self):
        logger.info('Завершение работы бота')
        await self._dp.stop_polling()
        await self._bot.close()
