import asyncio
import os
import signal
import traceback
from asyncio import CancelledError, Task
from datetime import datetime

import aiofiles

from bot.bot import TGBot
from db_utils.connectors import PGConnector, SQLiteConnector
from db_utils.repositories import AttachmentPGRepository, SQLiteRepository
from db_utils.utils import init_db
from file_utils.file_utils import attachments_aiter, check_file_status
from settings import logger, settings


class Worker:
    def __init__(
        self, sqlite_dsn: str, pg_dns: str, path: str, stop_at: int, start_at: int, bot_token: str, chat_ids: list[int]
    ):
        logger.debug('Создание экземпляра класса Worker')
        self.pause: bool = True
        self.sqlite_dsn = sqlite_dsn
        self.pg_dsn = pg_dns
        self.path = path
        self.start_at: int = start_at
        self.stop_at: int = stop_at
        self._sqlite_repo: SQLiteRepository | None = None
        self._pg_repo: AttachmentPGRepository | None
        self._file_checker = None
        self._bot_token = bot_token
        self._chat_ids = chat_ids
        self._tg_bot: TGBot | None = None
        self._tasks: list[Task] = []

    async def get_attachments_from_jira_db(self):
        logger.info('получение списка вложений из базы Posgres Jira и помещение их в базу Sqlite')
        attachments = await self._pg_repo.get_file_attachments()
        await self._sqlite_repo.save_attachments(attachments)

    async def check_working_hours(self):
        try:
            while True:
                logger.debug('Проверка запрета на работу (рабочие часы)')
                current_hour = datetime.now().hour
                self.pause = self.stop_at <= current_hour < self.start_at
                logger.debug('Работа разрешена' if not self.pause else 'Работа запрещена')
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info('функция проверки запрета на работу отменена')
            return

    async def run(self):
        await self._init_connections()
        self._tasks.extend(
            (
                asyncio.create_task(self.check_working_hours()),
                asyncio.create_task(self.check_attachments()),
                asyncio.create_task(self._tg_bot.run()),
            )
        )
        await self._tg_bot.send_message('Скрипт начал работу')
        try:
            await asyncio.gather(*self._tasks)
        except Exception as e:
            logger.error(f'Исключение {e}, отмена задач')
            logger.error(traceback.format_exc())
            for t in self._tasks:
                t.cancel()
        finally:
            await self._release_connections()
        await self._tg_bot.send_message('Скрипт закончил работу')

    async def get_progres(self):
        progress = await self._sqlite_repo.get_progress()
        return progress

    async def get_status(self):
        ...

    async def check_attachments(self):
        logger.info('Запуск функции проверки вложений')
        try:
            while True:
                if not self.pause:
                    logger.debug('Итерация')
                    logger.debug('Проверка времени последнего запуска получения вложений из базы postgres')
                    seconds_since_tasks_gathered = await self._sqlite_repo.seconds_from_last_launch()
                    if seconds_since_tasks_gathered < 0 or seconds_since_tasks_gathered > settings.fetch_tasks_period:
                        logger.info(
                            f'Запуск получения вложений из базы postgres'
                            f' и запись их в базу sqlite батчами по {settings.pg_batch_size}'
                        )
                        offset = 0
                        while True:
                            attachments = await self._pg_repo.get_file_attachments(
                                limit=settings.pg_batch_size, offset=offset
                            )
                            if not attachments:
                                logger.info('Завершено')
                                break
                            await self._sqlite_repo.save_attachments(attachments)
                            offset += settings.pg_batch_size
                    else:
                        logger.debug(
                            f'С последнего запуска прошло {seconds_since_tasks_gathered} '
                            f'сек. (<{settings.fetch_tasks_period}'
                        )
                    offset = 0
                    logger.info('Запуск основного цикла проверки вложений на диске')
                    while True:
                        logger.debug(f'Итерация. Размер батча {settings.file_batch_size}, отступ {offset}')
                        logger.debug(f'Получение {settings.file_batch_size} вложений из sqlite с отступом {offset}')
                        attachments = await self._sqlite_repo.get_unprocessed_attachments(
                            limit=settings.file_batch_size, offset=offset
                        )
                        if not attachments:
                            msg = 'В базе отсутствуют необработанные вложения, пауза'
                            logger.info(msg)
                            await asyncio.sleep(60)
                            break
                        attachments_batch = []
                        logger.debug('Проверка на диске батча вложений')
                        async for a in attachments_aiter(attachments):
                            path = os.path.join(
                                '/home/tmpd/Projects/jira_attachment_checker/jira/data/attachments', a.path
                            )
                            status, disclaimer = await check_file_status(
                                a, path, settings.uid, settings.gid, settings.file_mode
                            )
                            logger.debug(f'Вложение {path} проверено, статус {status}')
                            attachments_batch.append((a, path, status, disclaimer))

                        logger.debug('Отметка батча вложений обработанными')
                        await self._sqlite_repo.update_attachments([a[0] for a in attachments_batch])
                        logger.debug('Запись информации о батче вложений в таблицу reports sqlite')
                        await self._sqlite_repo.save_attachment_reports(attachments_batch)
                        offset += settings.file_batch_size
                        logger.debug('Конец итерации')
                else:
                    logger.info('Запрет на работу (рабочие часы)')
                    await asyncio.sleep(60)
        except CancelledError:
            logger.info('Функция проверки вложений отменена')
        except Exception as e:
            logger.error(f'Исключение {e}')
            logger.error(traceback.format_exc())
            raise e

    async def create_report_to_fs(self):
        logger.info('Запись файла отчетов')
        delimiter = ';'
        columns = [
            'id',
            'filename',
            'full_path',
            'project_name',
            'issue_name',
            'created_at',
            'updated_at',
            'is_missing',
            'has_wrong_uid_or_gid',
            'has_wrong_mode',
            'has_wrong_size',
            'summary',
        ]
        reports = await self._sqlite_repo.get_reports()
        async with aiofiles.open('report.csv', 'a') as report_file:
            await report_file.write(f'{delimiter.join(columns)}\n')
            for r in reports:
                await report_file.write(f'{delimiter.join([str(x) for x in r])}\n')
        logger.info('Запись файла отчетов завершена')

    async def get_report(self):
        columns = [
            ('id', 'integer primary key'),
            ('filename', 'text'),
            ('full_path', 'text'),
            ('project_name', 'text'),
            ('issue_name', 'text'),
            ('created_at', 'text'),
            ('updated_at', 'text'),
            ('is_missing', 'bool'),
            ('has_wrong_uid_or_gid', 'bool'),
            ('has_wrong_mode', 'bool'),
            ('has_wrong_size', 'bool'),
            ('summary', 'text'),
        ]
        rows = await self._sqlite_repo.get_reports()
        summary_dict = {
            'total': await self._sqlite_repo.get_total_attachments(),
            'total_processed': len(rows),
            'missing': 0,
            'wrong_uid_gid': 0,
            'wrong_mode': 0,
            'wrong_size': 0,
            'total_with_problems': 0,
        }
        for row in rows:
            if row[7]:
                summary_dict['missing'] += 1
                summary_dict['total_with_problems'] += 1
            if row[8]:
                summary_dict['wrong_uid_gid'] += 1
                summary_dict['total_with_problems'] += 1
            if row[9]:
                summary_dict['wrong_mode'] += 1
                summary_dict['total_with_problems'] += 1
            if row[10]:
                summary_dict['wrong_size'] += 1
                summary_dict['total_with_problems'] += 1
        summary = (
            f"Всего файлов в БД Jira: {summary_dict.get('total')}\n"
            f"Всего файлов обработано: {summary_dict.get('total_processed')}\n"
            f"Всего из обработанных файлов с проблемами: {summary_dict.get('total_with_problems')}\n"
            f"Отсутствует файлов: {summary_dict.get('missing')}\n"
            f"Файлов с неверным владельцем/группой: {summary_dict.get('wrong_uid_gid')}\n"
            f"Файлов с неверными правами доступа: {summary_dict.get('wrong_mode')}\n"
            f"Файлов с неверным размером: {summary_dict.get('wrong_size')}"
        )
        return summary, columns, rows

    async def _init_connections(self):
        logger.info('открытие соединений к базам, создание бота')
        self._sqlite_repo = SQLiteRepository(await SQLiteConnector.create(self.sqlite_dsn))
        self._pg_repo = AttachmentPGRepository(await PGConnector.create(self.pg_dsn))
        self._tg_bot = TGBot(self._bot_token, self._chat_ids)
        self._tg_bot.set_progress_function(self.get_progres)
        self._tg_bot.set_report_function(self.get_report)

    async def _release_connections(self):
        logger.info('Закрытие соединений')
        try:
            await self._sqlite_repo.close()
            await self._pg_repo.close()
        except AttributeError:
            logger.debug('Одно или несколько соединений не было закрыто, пропуск.')

    async def cancel(self):
        msg = 'Завершение работы'
        logger.info(msg)
        await self._tg_bot.send_message(msg)
        for t in self._tasks:
            await t.cancel()
        await self._release_connections()


async def main(worker: Worker):
    try:
        await worker.run()
    except CancelledError:
        print('cancelled')


def test():
    print('test')


if __name__ == '__main__':
    logger.info('Начало работы')
    init_db(settings.sqlite_dsn)
    logger.debug('Запуск главной функции')
    w = Worker(
        settings.sqlite_dsn,
        settings.postgres_dsn,
        settings.jira_files_path,
        settings.stop_at,
        settings.start_at,
        settings.bot_token,
        settings.chat_ids,
    )
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    main_task = asyncio.ensure_future(main(w))
    for sig in [signal.SIGINT, signal.SIGTERM]:
        loop.add_signal_handler(sig, main_task.cancel, ...)
    try:
        loop.run_until_complete(main_task)
    finally:
        loop.close()
