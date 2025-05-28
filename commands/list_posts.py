from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from datetime import datetime
from storage import supabase_db
from commands import TEXTS
from commands.create_post import parse_time, format_example

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
                    from datetime import datetime as dt
                    pub_dt = None
                    if isinstance(pub_time, str):
                        try:
                            pub_dt = dt.fromisoformat(pub_time)
                        except:
                            pub_dt = dt.strptime(pub_time, "%Y-%m-%dT%H:%M:%S")
                    elif isinstance(pub_time, dt):
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

@router.message(Command("view"))
async def cmd_view(message: Message):
    user_id = message.from_user.id
    lang = "ru"
    user = supabase_db.db.get_user(user_id)
    if user:
        lang = user.get("language", "ru")
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(TEXTS[lang]['view_usage'])
        return
    try:
        post_id = int(args[1])
    except:
        await message.answer(TEXTS[lang]['view_invalid_id'])
        return
    post = supabase_db.db.get_post(post_id)
    if not post or post.get("user_id") != user_id:
        await message.answer(TEXTS[lang]['view_not_found'])
        return
    text = post.get("text") or TEXTS[lang]['no_text']
    media_id = post.get("media_id")
    media_type = post.get("media_type")
    fmt = post.get("format") or "none"
    buttons = post.get("buttons") or []
    parse_mode = None
    if fmt.lower() == "markdown":
        parse_mode = "Markdown"
    elif fmt.lower() == "html":
        parse_mode = "HTML"
    # Prepare inline markup for post buttons (if any)
    btn_list = []
    if isinstance(buttons, str):
        try:
            btn_list = __import__("json").loads(buttons) if buttons else []
        except:
            btn_list = []
    elif isinstance(buttons, list):
        btn_list = buttons
    markup = None
    if btn_list:
        kb = []
        for btn in btn_list:
            if isinstance(btn, dict):
                btn_text = btn.get("text"); btn_url = btn.get("url")
            elif isinstance(btn, (list, tuple)) and len(btn) >= 2:
                btn_text, btn_url = btn[0], btn[1]
            else:
                continue
            if btn_text and btn_url:
                kb.append([InlineKeyboardButton(text=btn_text, url=btn_url)])
        if kb:
            markup = InlineKeyboardMarkup(inline_keyboard=kb)
    # Send the post content preview
    try:
        if media_id and media_type:
            if media_type.lower() == "photo":
                await message.answer_photo(media_id, caption=text, parse_mode=parse_mode, reply_markup=markup)
            elif media_type.lower() == "video":
                await message.answer_video(media_id, caption=text, parse_mode=parse_mode, reply_markup=markup)
            else:
                await message.answer(text, parse_mode=parse_mode, reply_markup=markup)
        else:
            await message.answer(text, parse_mode=parse_mode, reply_markup=markup)
    except Exception as e:
        err_msg = f"Не удалось показать пост: {e}" if lang == "ru" else f"Failed to display post: {e}"
        await message.answer(err_msg)

@router.message(Command("reschedule"))
async def cmd_reschedule(message: Message):
    user_id = message.from_user.id
    lang = "ru"
    user = supabase_db.db.get_user(user_id)
    if user:
        lang = user.get("language", "ru")
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(TEXTS[lang]['reschedule_usage'])
        return
    try:
        post_id = int(args[1])
    except:
        await message.answer(TEXTS[lang]['reschedule_invalid_id'])
        return
    time_str = args[2]
    post = supabase_db.db.get_post(post_id)
    if not post or post.get("user_id") != user_id:
        await message.answer(TEXTS[lang]['reschedule_not_found'])
        return
    if post.get("published"):
        await message.answer(TEXTS[lang]['reschedule_post_published'])
        return
    new_time = None
    if time_str.lower() in ("none", "нет"):
        new_time = None
    else:
        try:
            new_time = parse_time(user or {}, time_str)
        except Exception:
            example = format_example(user or {})
            await message.answer(TEXTS[lang]['create_time_error'].format(example=example))
            return
        # Prevent scheduling in the past
        from zoneinfo import ZoneInfo
        if new_time <= datetime.now(ZoneInfo("UTC")):
            await message.answer(TEXTS[lang]['time_past_error'])
            return
    updates = {}
    if new_time is None:
        updates["publish_time"] = None
        updates["draft"] = True
        updates["published"] = False
        updates["repeat_interval"] = 0
    else:
        updates["publish_time"] = new_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        updates["draft"] = False
        updates["published"] = False
    supabase_db.db.update_post(post_id, updates)
    await message.answer(TEXTS[lang]['reschedule_success'].format(id=post_id))
