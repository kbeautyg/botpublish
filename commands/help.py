from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Команды:\n"
        "/create – создать пост\n"
        "/list – список отложенных\n"
        "/edit <id> – редактировать\n"
        "/delete <id> – удалить\n"
        "/channels – управление каналами\n"
        "/cancel – отменить ввод"
    )
