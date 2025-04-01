from dotenv import load_dotenv
from loguru import logger as l
from pydantic import PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    fetch_tasks_period: int = 600
    pg_batch_size: int = 1000
    file_batch_size: int = 100
    sqlite_dsn: str
    postgres_dsn: PostgresDsn
    jira_files_path: str
    uid: int
    gid: int
    file_mode: str
    start_at: int
    stop_at: int
    time_format: str = '%Y-%m-%d %H:%M:%S'
    bot_token: str
    chat_ids: list[int]
    delimiter: str = ';'
    tg_max_file_size: int = 50 * 1024 * 1024


load_dotenv()
settings = Settings()
logger = l
