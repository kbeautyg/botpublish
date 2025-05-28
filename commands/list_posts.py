# commands/list_posts.py
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from storage import supabase_db
from commands import TEXTS

router = Router()

@router.message(Command("list"))
async def cmd_list(message: Message):
    user_id = message.from_user.id
    lang = "ru"
    user = supabase_db.db.get_user(user_id)
    if user:
        lang = user.get("language", "ru")
    posts = supabase_db.db.list_posts(user_id=user_id, only_pending=True)
    if not posts:
        await message.answer(TEXTS[lang]['no_posts'])
    else:
        lines = [TEXTS[lang]['scheduled_posts_title']]
        for post in posts:
            pid = post.get("id")
            channel_name = ""
            chan_id = post.get("channel_id"); chat_id = post.get("chat_id")
            channels = supabase_db.db.list_channels(user_id=user_id)
            for ch in channels:
                if chan_id and ch.get("id") == chan_id:
                    channel_name = ch.get("name") or str(ch.get("chat_id"))
                    break
                if chat_id and ch.get("chat_id") == chat_id:
                    channel_name = ch.get("name") or str(chat_id)
                    break
            if post.get("draft"):
                time_str = "(черновик)" if lang == "ru" else "(draft)"
            else:
                pub_time = post.get("publish_time")
                time_str = str(pub_time)
                try:
                    from datetime import datetime
                    pub_dt = None
                    if isinstance(pub_time, str):
                        try:
                            pub_dt = datetime.fromisoformat(pub_time)
                        except:
                            pub_dt = datetime.strptime(pub_time, "%Y-%m-%dT%H:%M:%S")
                    elif isinstance(pub_time, datetime):
                        pub_dt = pub_time
                    tz_name = user.get("timezone", "UTC") if user else "UTC"
                    from zoneinfo import ZoneInfo
                    tz = ZoneInfo(tz_name)
                    pub_local = pub_dt.astimezone(tz) if pub_dt else None
                    if pub_local:
                        date_fmt = user.get("date_format", "YYYY-MM-DD") if user else "YYYY-MM-DD"
                        time_fmt = user.get("time_format", "HH:MM") if user else "HH:MM"
                        fmt = date_fmt.replace("YYYY", "%Y").replace("YY", "%y")
                        fmt = fmt.replace("MM", "%m").replace("DD", "%d") + " " + time_fmt.replace("HH", "%H").replace("H", "%H").replace("MM", "%M").replace("M", "%M")
                        time_str = pub_local.strftime(fmt)
                    else:
                        time_str = str(pub_time)
                except Exception:
                    time_str = str(pub_time)
            repeat_flag = ""
            if post.get("repeat_interval") and post["repeat_interval"] > 0:
                repeat_flag = " 🔁"
            full_text = (post.get("text") or "").replace("\n", " ")
            preview = full_text[:30]
            if len(full_text) > 30:
                preview += "..."
            line = f"ID {pid}: {channel_name} | {time_str}{repeat_flag} | {preview}"
            lines.append(line)
        await message.answer("\n".join(lines))
