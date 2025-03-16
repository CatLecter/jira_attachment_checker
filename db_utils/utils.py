import sqlite3

from loguru import logger


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
                created text,
                updated text,
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
                project_name text,
                issue_name text,
                created text,
                updated text,
                file_missing integer,
                wrong_uid_gid integer,
                wrong_mode integer,
                wrong_size integer,
                status text
            )
            """
        )
