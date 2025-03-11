from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


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


settings = Settings(_env_file='.env', _env_file_encoding='utf-8')
