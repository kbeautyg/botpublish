# commands/channels.py
from aiogram import Router, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from storage import supabase_db
from commands import TEXTS

router = Router()

@router.message(Command("channels"))
async def cmd_channels(message: Message, bot: Bot):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=2)
    lang = "ru"
    user = supabase_db.db.get_user(user_id)
    if user:
        lang = user.get("language", "ru")
    # No arguments: list channels
    if len(args) == 1:
        channels = supabase_db.db.list_channels(user_id=user_id)
        if not channels:
            await message.answer(TEXTS[lang]['channels_no_channels'])
            return
        lines = [TEXTS[lang]['channels_list_title']]
        for ch in channels:
            cid = ch["chat_id"]
            title = ch.get("name") or str(cid)
            lines.append(TEXTS[lang]['channels_item'].format(name=title, id=cid))
        await message.answer("\n".join(lines))
        return
    sub = args[1].lower()
    if sub == "add":
        if len(args) < 3:
            await message.answer(TEXTS[lang]['channels_add_usage'])
            return
        ident = args[2]
        try:
            chat = await bot.get_chat(ident)
            supabase_db.db.add_channel(user_id, chat.id, chat.title or chat.username or str(chat.id))
            await message.answer(TEXTS[lang]['channels_added'].format(name=chat.title or chat.username or chat.id))
        except Exception as e:
            await message.answer(TEXTS[lang]['channels_add_error'].format(error=e))
    elif sub in ("remove", "delete"):
        if len(args) < 3:
            await message.answer(TEXTS[lang]['channels_remove_usage'])
            return
        ok = supabase_db.db.remove_channel(user_id, args[2])
        await message.answer(TEXTS[lang]['channels_removed'] if ok else TEXTS[lang]['channels_not_found'])
    else:
        await message.answer(TEXTS[lang]['channels_unknown_command'])
