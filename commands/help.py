# commands/help.py
from aiogram import Router
from aiogram.types import Message

router = Router()

@router.message(commands=["help"])
async def cmd_help(message: Message):
    help_text = (
        "Доступные команды:\n"
        "/start - начать работу с ботом\n"
        "/create - создать новый отложенный пост\n"
        "/list - показать запланированные посты\n"
        "/edit <id> - отредактировать запланированный пост\n"
        "/delete <id> - удалить запланированный пост\n"
        "/channels - управление списком каналов\n"
    )
    await message.answer(help_text)
