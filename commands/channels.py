from aiogram import Router, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from storage import supabase_db

router = Router()

@router.message(Command("channels"))
async def cmd_channels(message: Message, bot: Bot):
    args = message.text.split(maxsplit=2)

    # без аргументов – вывести список
    if len(args) == 1:
        channels = supabase_db.db.list_channels()
        if not channels:
            await message.answer(
                "Список каналов пуст. Добавьте канал:\n"
                "/channels add <ID_канала или @username>"
            )
            return

        text = ["Подключенные каналы:"]
        for ch in channels:
            cid   = ch["chat_id"]
            title = ch.get("name") or str(cid)
            text.append(f"- {title} (ID: {cid})")
        await message.answer("\n".join(text))
        return

    sub = args[1].lower()

    if sub == "add":
        if len(args) < 3:
            await message.answer("Использование:\n/channels add <ID_канала или @username>")
            return
        ident = args[2]
        try:
            chat = await bot.get_chat(ident)
            supabase_db.db.add_channel(chat.id, chat.title or chat.username or str(chat.id))
            await message.answer(f"Канал «{chat.title or chat.username}» добавлен.")
        except Exception as e:
            await message.answer(f"Не удалось получить канал: {e}")

    elif sub in ("remove", "delete"):
        if len(args) < 3:
            await message.answer("Использование:\n/channels remove <ID_канала>")
            return
        ok = supabase_db.db.remove_channel(args[2])
        await message.answer("Канал удалён." if ok else "Канал не найден.")

    else:
        await message.answer("Неизвестная подкоманда. /channels add | remove")
