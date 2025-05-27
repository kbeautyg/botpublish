# commands/start.py
from aiogram import Router
from aiogram.types import Message

router = Router()

@router.message(commands=["start"])
async def cmd_start(message: Message):
    await message.answer("Привет! Я бот для отложенного постинга. Используйте /help для списка команд.")

