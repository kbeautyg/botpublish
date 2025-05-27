# states.py
from aiogram.fsm.state import State, StatesGroup

class CreatePost(StatesGroup):
    text = State()
    media = State()
    format = State()
    buttons = State()
    time = State()
    channel = State()
    confirm = State()

class EditPost(StatesGroup):
    text = State()
    media = State()
    format = State()
    buttons = State()
    time = State()
    channel = State()
    confirm = State()
