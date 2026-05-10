from aiogram.fsm.state import State, StatesGroup


class ChannelFSM(StatesGroup):
    waiting_source = State()
    waiting_target = State()
    waiting_delete_id = State()
    waiting_toggle_id = State()


class SettingsFSM(StatesGroup):
    waiting_replacer_old = State()
    waiting_replacer_new = State()
    waiting_deny_word = State()
    waiting_reactions = State()
    waiting_delay_seconds = State()
