from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_unban = State()
    waiting_for_ban = State()
