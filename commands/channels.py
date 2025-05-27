# commands/channels.py
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.utils.text_decorations import html_decoration as hd
from storage import supabase_db
from aiogram import Bot

router = Router()

@router.message(Command("channels"))
async def cmd_channels(message: Message, bot: Bot):
    args = message.text.split(maxsplit=2)
    # If no arguments, list channels
    if len(args) == 1:
        channels = supabase_db.db.list_channels()
        if not channels:
            await message.answer("Список каналов пуст. Добавьте канал через '/channels add <channel_id_or_username>'.")
        else:
            text_lines = ["Подключенные каналы:"]
            for ch in channels:
                cid = ch.get("chat_id")
                name = ch.get("name") or ""
                text_lines.append(f"- {name} (ID: {cid})")
            await message.answer("\n".join(text_lines))
    else:
        subcommand = args[1].lower()
        if subcommand == "add":
            if len(args) < 3:
                await message.answer("Использование: /channels add <ID_канала или @username>")
                return
            identifier = args[2]
            try:
                if identifier.startswith("@"):
                    # Use username to get channel info
                    chat = await bot.get_chat(identifier)
                    chat_id = chat.id
                    name = chat.title or chat.username or identifier
                else:
                    # Numeric ID
                    chat_id = int(identifier)
                    chat = await bot.get_chat(chat_id)
                    name = chat.title or chat.username or str(chat_id)
            except Exception as e:
                await message.answer(f"Не удалось получить информацию о канале: {e}")
                return
            # Add to database
            supabase_db.db.add_channel(chat_id, name)
            await message.answer(f"Канал '{name}' добавлен в список.")
        elif subcommand in ("remove", "delete"):
            if len(args) < 3:
                await message.answer("Использование: /channels remove <ID_канала>")
                return
            identifier = args[2]
            success = supabase_db.db.remove_channel(identifier)
            if success:
                await message.answer("Канал удален из списка.")
            else:
                await message.answer("Канал не найден в списке.")
        else:
            await message.answer("Неизвестная команда. Используйте '/channels', '/channels add <id_or_username>' или '/channels remove <id>'.")
