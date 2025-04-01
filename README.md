## Скрипт для проверки целостности вложений Jira
Данный скрипт предназначен для проверки целостности файлов вложений задач Jira

### Принцип работы

Скрипт подключается к БД Jira и получает информацию о вложениях, записывает данную информацию во внутреннюю базу (sqlite)
и проверяет наличие, соответствие размера, разрешений, владельца файлов в файловой системе. Получение информации о прогрессе
обработки и отчета о состоянии файлов вложений возможно через telegram-бота.

### Порядок работы:

- Локальный запуск:
   - скопировать файл **example.env** в файл **.env**
   - заполнить файл **.env** актуальными параметрами
   - установить зависимости ```pip install -r requirements.txt```
   - запустить скрипт ```python ./main.py```
- Запуск в контейнере
  - скопировать файл **example.env** в файл **.env**
  - заполнить файл **.env** актуальными параметрами
  - выполнить  ```docker compose build```
  - запусить контейнер ```docker compose up -d```

### Описание параметров

    FETCH_TASKS_PERIOD=
    Периодичность получения информации о новых вложениях в БД Jira в секундах

    PG_BATCH_SIZE=
    Количество записей о вложениях, получаемых за одно обращение из БД Jira

    FILE_BATCH_SIZE=
    Количество файлов вложений, проверяемых за одно обращение к файловой системе

    POSTGRES_DSN='postgres://login:pwd@host:port/database'
    Параметры для подключения к БД Jira

    SQLITE_DSN='db.sqlite'
    Параметры для подключения к внутренней базе (путь до базы sqlite)

    JIRA_FILES_PATH='/path/to/jira/directory/ending/with/data/attachments'
    Путь в файловой системе до директории с вложениями Jira, обычно /jira/data/attachments/

    UID=2001
    UID пользователя, который должен являться владельцем файлов вложений

    GID=2001
    GID пользователя, который должен являться владельцем файлов вложений

    FILE_MODE=640
    Права доступа, которые должны быть у файла вложений

    START_AT=18
    Начало работы скрипта (для исключения избыточной нагрузки на сервер в рабочие часы)

    STOP_AT=9
    Конец работы скрипта (начало рабочих часов, в которые скрипт не должен работать для исключения избыточной нагрузки)

    BOT_TOKEN=
    Токен телеграм-бота

    CHAT_IDS=[123, 123]
    Идентификаторы чатов, в которые будут поступать уведомления о работе скрипта. Можно
    указать несколько, поддерживаются как личные сообщения, так и группы. Для получения
    идентификатора группы, нужно при запущенном скрипте добавить его в группу и выполнить
    команду /get_chat_id
