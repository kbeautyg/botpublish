# commands/list_posts.py
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from storage import supabase_db

router = Router()

@router.message(Command("list"))
async def cmd_list(message: Message):
    posts = supabase_db.db.list_posts(only_pending=True)
    if not posts:
        await message.answer("Нет запланированных постов.")
    else:
        lines = ["Запланированные посты:"]
        for post in posts:
            pid = post.get("id")
            pub_time = post.get("publish_time")
            # Determine channel name
            chan_name = ""
            chan_id = post.get("channel_id")
            # We might have stored chat_id as well
            chat_id = post.get("chat_id")
            channels = supabase_db.db.list_channels()
            for ch in channels:
                if chan_id and ch.get("id") == chan_id:
                    chan_name = ch.get("name") or str(ch.get("chat_id"))
                    break
                if chat_id and ch.get("chat_id") == chat_id:
                    chan_name = ch.get("name") or str(chat_id)
                    break
            text_preview = (post.get("text") or "")
            if text_preview:
                text_preview = text_preview.replace("\n", " ")[:30]
                if len(text_preview) == 30:
                    text_preview += "..."
            else:
                text_preview = "(без текста)"
            lines.append(f"ID {pid}: канал \"{chan_name}\" | время: {pub_time} | текст: {text_preview}")
        await message.answer("\n".join(lines))
