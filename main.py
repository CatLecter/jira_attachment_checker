import asyncio
import os
import sqlite3
import traceback
from datetime import datetime

import aiofiles
from loguru import logger

from db_utils.connectors.connectors import PGConnector, SQLiteConnector
from db_utils.connectors.repositories import AttachmentPGRepository, SQLiteRepository
from file_utils.file_utils import attachments_aiter, check_file_status
from settings import settings


class Worker:
    def __init__(self, sqlite_dsn: str, pg_dns: str, path: str, stop_at: int, start_at: int):
        logger.debug('Создание экземпляра класса Worker')
        self.running = False
        self.sqlite_dsn = sqlite_dsn
        self.pg_dsn = pg_dns
        self.path = path
        self.start_at: int = start_at
        self.stop_at: int = stop_at
        self._sqlite_repo: SQLiteRepository | None = None
        self._pg_repo: AttachmentPGRepository | None
        self._file_checker = None

    async def get_attachments_from_jira_db(self):
        logger.info('получение списка вложений из базы Posgres Jira и помещение их в базу Sqlite')
        attachments = await self._pg_repo.get_file_attachments()
        await self._sqlite_repo.save_attachments(attachments)

    async def check_working_hours(self, event: asyncio.Event):
        try:
            while not event.is_set():
                logger.debug('Проверка запрета на работу (рабочие часы)')
                current_hour = datetime.now().hour
                self.running = not (self.stop_at <= current_hour < self.start_at)
                logger.debug('Работа разрешена' if self.running else 'работа запрещена')
                await asyncio.sleep(60)
            logger.debug('Завершение функции запрета на работу')
        except asyncio.CancelledError:
            logger.info('функция проверки запрета на работу отменена')
            return

    async def run(self):
        event = asyncio.Event()
        tasks = (
            asyncio.create_task(self.check_working_hours(event)),
            asyncio.create_task(self.check_attachments(event)),
        )
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f'Исключение {e}, отмена задач')
            logger.error(traceback.format_exc())
            for t in tasks:
                t.cancel()
        finally:
            await self._release_connections()

    async def check_attachments(self, event: asyncio.Event):
        logger.info('Запуск функции проверки вложений')
        await self._init_connections()
        has_unprocessed_attachments = True
        try:
            while has_unprocessed_attachments:
                if self.running:
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
                    offset = 0
                    logger.info('Запуск основного цикла проверки вложений на диске')
                    while True:
                        logger.debug(f'Итерация. Размер батча {settings.file_batch_size}, отступ {offset}')
                        logger.debug(f'Получение {settings.file_batch_size} вложений из sqlite с отступом {offset}')
                        attachments = await self._sqlite_repo.get_unprocessed_attachments(
                            limit=settings.file_batch_size, offset=offset
                        )
                        if not attachments:
                            logger.info('В базе отсутствуют необработанные вложения, работа цикла завершена')
                            has_unprocessed_attachments = False
                            event.set()
                            break
                        attachments_batch = []
                        logger.debug('Проверка на диске батча вложений')
                        async for a in attachments_aiter(attachments):
                            path = os.path.join(
                                '/home/tmpd/Projects/jira_attachment_checker/jira/data/attachments', a.path
                            )
                            status = await check_file_status(a, path, settings.uid, settings.gid, settings.file_mode)
                            logger.debug(f'Вложение {path} проверено, статус {status}')
                            attachments_batch.append((a, path, status))

                        logger.debug('Отметка батча вложений обработанными')
                        await self._sqlite_repo.update_attachments([a[0] for a in attachments_batch])
                        logger.debug('Запись информации о батче вложений в таблицу reports sqlite')
                        await self._sqlite_repo.save_attachment_reports(attachments_batch)
                        logger.debug('Конец итерации')
                else:
                    logger.info('Запрет на работу (рабочие часы)')
                    await asyncio.sleep(60)
            logger.info('Цикл завершен, установка события завершения')
            event.set()
            await self.create_report()
            # todo формирование отчета (краткий, полный)
            # todo отчет в телегу
            # todo запись базы sqlite
        except Exception as e:
            logger.error(f'Исключение {e}')
            logger.error(traceback.format_exc())
            raise e

    async def create_report(self):
        logger.info("Запись файла отчетов")
        delimiter = ';'
        columns = ['id', 'filename', 'full_path', 'status', 'project_name', 'issue_name']
        reports = await self._sqlite_repo.get_reports()
        async with aiofiles.open('report.csv', 'a') as report_file:
            await report_file.write(f'{delimiter.join(columns)}\n')
            for r in reports:
                await report_file.write(f'{delimiter.join([str(x) for x in r])}\n')
        logger.info("Запись файла отчетов завершена")

    async def _init_connections(self):
        logger.info('открытие соединений к базам')
        self._sqlite_repo = SQLiteRepository(await SQLiteConnector.create(self.sqlite_dsn))
        self._pg_repo = AttachmentPGRepository(await PGConnector.create(self.pg_dsn))

    async def _release_connections(self):
        logger.info('Закрытие соединений')
        try:
            await self._sqlite_repo.close()
            await self._pg_repo.close()
        except AttributeError:
            logger.debug('Одно или несколько соединений не было установлено, пропуск.')


def init_db(sqlite_dsn: str):
    logger.debug('Инициализация базы данных (создание таблиц, если не существуют)')
    logger.debug(f'Создание подключения к sqlite по адресу {sqlite_dsn}')
    con = sqlite3.connect(sqlite_dsn)
    with con:
        logger.debug('Создание таблицы attachments')
        con.execute(
            """
            create table if not exists attachments (
                attachment_id INTEGER PRIMARY KEY,
                filename text NOT NULL,
                file_size INTEGER,
                file_mime_type text,
                issue_num INTEGER,
                project_id INTEGER,
                project_name text,
                path text,
                processed INTEGER
            );
            """
        )
        logger.debug('Создание таблицы parameters')
        con.execute(
            """
            create table if not exists parameters (
                name text unique,
                value text default "");
            """
        )
        logger.debug('Создание таблицы reports')
        con.execute(
            """
            create table if not exists reports(
                attachment_id integer primary key,
                filename text,
                full_path text,
                status text,
                project_name text,
                issue_name text
            )
            """
        )


async def main():
    w = Worker(
        settings.sqlite_dsn, settings.postgres_dsn, settings.jira_files_path, settings.stop_at, settings.start_at
    )
    w.running = True
    await w.run()


if __name__ == '__main__':
    logger.info('Начало работы')
    init_db(settings.sqlite_dsn)
    logger.debug('Запуск главной функции')
    asyncio.run(main())
