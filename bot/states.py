from aiogram.fsm.state import State, StatesGroup


class ParseState(StatesGroup):
    idle = State()
    csv_sqlite = State()
    csv = State()
    sqlite = State()
    csv_too_large = State()
    csv_parts = State()
    work_in_progress = State()
