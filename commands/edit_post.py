import json
import re
from aiogram import Router, types, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime
from zoneinfo import ZoneInfo
from states import EditPost
from storage import supabase_db
from commands import TEXTS

router = Router()

TOKEN_MAP = {
    "YYYY": "%Y", "YY": "%y",
    "MM": "%m",   "DD": "%d",
    "HH": "%H",   "hh": "%I",
    "mm": "%M",   "SS": "%S",
    "AM": "%p",   "PM": "%p",
    "am": "%p",   "pm": "%p",
}
_rx = re.compile("|".join(sorted(TOKEN_MAP, key=len, reverse=True)))

def format_to_strptime(date_fmt: str, time_fmt: str) -> str:
    return _rx.sub(lambda m: TOKEN_MAP[m.group(0)], f"{date_fmt} {time_fmt}")

def parse_time(user: dict, text: str):
    date_fmt = user.get("date_format", "YYYY-MM-DD")
    time_fmt = user.get("time_format", "HH:mm")
    tz_name = user.get("timezone", "UTC")
    # Adjust time format for correct parsing
    if "MM" in time_fmt:
        time_fmt = time_fmt.replace("MM", "mm")
    fmt = format_to_strptime(date_fmt, time_fmt)
    dt = datetime.strptime(text, fmt)
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    local_dt = dt.replace(tzinfo=tz)
    utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
    return utc_dt

def format_example(user: dict):
    date_fmt = user.get("date_format", "YYYY-MM-DD")
    time_fmt = user.get("time_format", "HH:mm")
    if "MM" in time_fmt:
        time_fmt = time_fmt.replace("MM", "mm")
    fmt = format_to_strptime(date_fmt, time_fmt)
    now = datetime.now()
    try:
        return now.strftime(fmt)
    except Exception:
        return now.strftime("%Y-%m-%d %H:%M")

@router.message(Command("edit"))
async def cmd_edit(message: Message, state: FSMContext):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    lang = "ru"
    user = supabase_db.db.get_user(user_id)
    if user:
        lang = user.get("language", "ru")
    if len(args) < 2:
        await message.answer(TEXTS[lang]['edit_usage'])
        return
    try:
        post_id = int(args[1])
    except:
        await message.answer(TEXTS[lang]['edit_invalid_id'])
        return
    post = supabase_db.db.get_post(post_id)
    if not post or post.get("user_id") != user_id:
        await message.answer(TEXTS[lang]['edit_post_not_found'])
        return
    if post.get("published"):
        await message.answer(TEXTS[lang]['edit_post_published'])
        return
    await state.update_data(orig_post=post, user_settings=(user or supabase_db.db.ensure_user(user_id)))
    await state.set_state(EditPost.text)
    current_text = post.get("text") or ""
    await message.answer(TEXTS[lang]['edit_begin'].format(id=post_id, text=current_text))

@router.message(EditPost.text)
async def edit_step_text(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    text_input = message.text or ""
    new_text = orig_post.get("text", "") if text_input.strip().lower().startswith("/skip") else text_input
    await state.update_data(new_text=new_text)
    await state.set_state(EditPost.media)
    if orig_post.get("media_id"):
        info = TEXTS['ru']['media_photo'] if orig_post.get("media_type") == "photo" else TEXTS['ru']['media_video'] if orig_post.get("media_type") == "video" else TEXTS['ru']['media_media']
        lang = data.get("user_settings", {}).get("language", "ru")
        await message.answer(TEXTS[lang]['edit_current_media'].format(info=info))
    else:
        lang = data.get("user_settings", {}).get("language", "ru")
        await message.answer(TEXTS[lang]['edit_no_media'])

@router.message(Command("skip"), EditPost.media)
async def skip_edit_media(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    # Keep existing media (if any)
    if orig_post.get("media_id"):
        await state.update_data(new_media_id=orig_post.get("media_id"), new_media_type=orig_post.get("media_type"))
    else:
        await state.update_data(new_media_id=None, new_media_type=None)
    await ask_edit_format(message, state)

@router.message(EditPost.media, F.photo)
async def edit_step_media_photo(message: Message, state: FSMContext):
    await state.update_data(new_media_id=message.photo[-1].file_id, new_media_type="photo")
    await ask_edit_format(message, state)

@router.message(EditPost.media, F.video)
async def edit_step_media_video(message: Message, state: FSMContext):
    await state.update_data(new_media_id=message.video.file_id, new_media_type="video")
    await ask_edit_format(message, state)

@router.message(EditPost.media)
async def edit_step_media_invalid(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("user_settings", {}).get("language", "ru")
    await message.answer(TEXTS[lang]['edit_current_media'] if data.get("orig_post", {}).get("media_id") else TEXTS[lang]['edit_no_media'])

async def ask_edit_format(message: Message, state: FSMContext):
    await state.set_state(EditPost.format)
    data = await state.get_data()
    lang = data.get("user_settings", {}).get("language", "ru")
    curr_fmt = data.get("orig_post", {}).get("format") or "none"
    await message.answer(TEXTS[lang]['edit_current_format'].format(format=curr_fmt))

@router.message(Command("skip"), EditPost.format)
async def skip_edit_format(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    new_fmt = orig_post.get("format") or "none"
    await state.update_data(new_format=new_fmt)
    await ask_edit_buttons(message, state)

@router.message(EditPost.format)
async def edit_step_format(message: Message, state: FSMContext):
    raw = (message.text or "").strip().lower()
    new_fmt = "markdown" if raw.startswith("markdown") else "html" if raw.startswith("html") else "none"
    await state.update_data(new_format=new_fmt)
    await ask_edit_buttons(message, state)

async def ask_edit_buttons(message: Message, state: FSMContext):
    await state.set_state(EditPost.buttons)
    data = await state.get_data()
    lang = data.get("user_settings", {}).get("language", "ru")
    orig_post = data.get("orig_post", {})
    if orig_post.get("buttons"):
        # List current buttons
        btns_list = ""
        try:
            current_buttons = json.loads(orig_post["buttons"]) if isinstance(orig_post["buttons"], str) else orig_post["buttons"]
        except Exception:
            current_buttons = orig_post["buttons"] or []
        for btn in current_buttons:
            if isinstance(btn, dict):
                btns_list += f"- {btn.get('text')} | {btn.get('url')}\n"
            elif isinstance(btn, (list, tuple)) and len(btn) >= 2:
                btns_list += f"- {btn[0]} | {btn[1]}\n"
        await message.answer(TEXTS[lang]['edit_current_buttons'].format(buttons_list=btns_list.strip()))
    else:
        await message.answer(TEXTS[lang]['edit_no_buttons'])

@router.message(Command("skip"), EditPost.buttons)
async def skip_edit_buttons(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    new_buttons = orig_post.get("buttons") or []
    await state.update_data(new_buttons=new_buttons)
    await ask_edit_time(message, state)

@router.message(EditPost.buttons)
async def edit_step_buttons(message: Message, state: FSMContext):
    text = message.text or ""
    if text.strip().lower() == "нет" or text.strip().lower() == "none":
        new_buttons = []
    elif text.strip().lower().startswith("/skip"):
        new_buttons = orig_post.get("buttons") or []
    else:
        buttons = []
        for line in text.splitlines():
            if "|" in line:
                parts = line.split("|", 1)
                btn_text = parts[0].strip(); btn_url = parts[1].strip()
                if btn_text and btn_url:
                    buttons.append({"text": btn_text, "url": btn_url})
        new_buttons = buttons
    await state.update_data(new_buttons=new_buttons)
    await ask_edit_time(message, state)

async def ask_edit_time(message: Message, state: FSMContext):
    await state.set_state(EditPost.time)
    data = await state.get_data()
    lang = data.get("user_settings", {}).get("language", "ru")
    orig_post = data.get("orig_post", {})
    orig_time = orig_post.get("publish_time")
    current_time_str = "(черновик)" if (not orig_time) and lang == "ru" else "(draft)" if (not orig_time) else str(orig_time)
    fmt_str = f"{data.get('user_settings', {}).get('date_format', 'YYYY-MM-DD')} {data.get('user_settings', {}).get('time_format', 'HH:MM')}"
    example = format_example(data.get("user_settings", {}))
    await message.answer(TEXTS[lang]['edit_current_time'].format(time=current_time_str, format=fmt_str, example=example))

@router.message(Command("skip"), EditPost.time)
async def skip_edit_time(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    await state.update_data(new_publish_time=orig_post.get("publish_time"))
    # Keep original repeat interval and move to next step
    await state.update_data(new_repeat_interval=orig_post.get("repeat_interval", 0))
    await ask_edit_repeat(message, state)

@router.message(EditPost.time)
async def edit_step_time(message: Message, state: FSMContext):
    data = await state.get_data()
    user = data.get("user_settings", {})
    lang = user.get("language", "ru")
    time_str = message.text.strip()
    if time_str.lower() in ("none", "нет"):
        new_time = None
    else:
        try:
            new_time = parse_time(user, time_str)
        except Exception:
            fmt = f"{user.get('date_format', 'YYYY-MM-DD')} {user.get('time_format', 'HH:MM')}"
            example = format_example(user)
            await message.answer(TEXTS[lang]['edit_time_error'].format(format=fmt, example=example))
            return
        # Prevent scheduling in the past
        if new_time <= datetime.now(ZoneInfo("UTC")):
            await message.answer(TEXTS[lang]['time_past_error'])
            return
    await state.update_data(new_publish_time=new_time)
    # Carry over original repeat interval if unscheduled, otherwise use original until changed
    orig_post = data.get("orig_post", {})
    await state.update_data(new_repeat_interval=orig_post.get("repeat_interval", 0))
    await ask_edit_repeat(message, state)

async def ask_edit_repeat(message: Message, state: FSMContext):
    # After time step, proceed to repeat (or directly to channel if skipped time)
    await state.set_state(EditPost.repeat)
    data = await state.get_data()
    lang = data.get("user_settings", {}).get("language", "ru")
    orig_post = data.get("orig_post", {})
    orig_interval = orig_post.get("repeat_interval", 0)
    curr_repeat = "0"
    if orig_interval:
        if orig_interval % 86400 == 0:
            days = orig_interval // 86400
            curr_repeat = f"{days}d"
        elif orig_interval % 3600 == 0:
            hours = orig_interval // 3600
            curr_repeat = f"{hours}h"
        else:
            minutes = orig_interval // 60
            curr_repeat = f"{minutes}m"
    await message.answer(TEXTS[lang]['edit_current_repeat'].format(repeat=curr_repeat))

@router.message(Command("skip"), EditPost.repeat)
async def skip_edit_repeat(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    await state.update_data(new_repeat_interval=orig_post.get("repeat_interval", 0))
    await ask_edit_channel(message, state)

@router.message(EditPost.repeat)
async def edit_step_repeat(message: Message, state: FSMContext):
    data = await state.get_data()
    user = data.get("user_settings", {})
    lang = user.get("language", "ru")
    raw = message.text.strip().lower()
    interval = None
    if raw in ("0", "none", "нет"):
        interval = 0
    else:
        unit = raw[-1] if raw else ""
        try:
            value = int(raw[:-1])
        except:
            value = None
        if not value or unit not in ("d", "h", "m"):
            await message.answer(TEXTS[lang]['edit_repeat_error'])
            return
        if unit == "d":
            interval = value * 86400
        elif unit == "h":
            interval = value * 3600
        elif unit == "m":
            interval = value * 60
        else:
            interval = 0
    await state.update_data(new_repeat_interval=interval if interval is not None else 0)
    await ask_edit_channel(message, state)

async def ask_edit_channel(message: Message, state: FSMContext):
    await state.set_state(EditPost.channel)
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    lang = data.get("user_settings", {}).get("language", "ru")
    channels = supabase_db.db.list_channels(user_id=message.from_user.id)
    if not channels:
        await message.answer(TEXTS[lang]['channels_no_channels'])
        return
    current_channel_name = "(unknown)"
    if orig_post:
        chan_id = orig_post.get("channel_id"); chat_id = orig_post.get("chat_id")
        for ch in channels:
            if chan_id and ch.get("id") == chan_id:
                current_channel_name = ch.get("name") or str(ch.get("chat_id"))
                break
            if chat_id and ch.get("chat_id") == chat_id:
                current_channel_name = ch.get("name") or str(ch.get("chat_id"))
                break
    # Prompt channel selection with current channel info
    if lang == "ru":
        lines = [f"Текущий канал: {current_channel_name}", "Выберите новый канал или отправьте /skip, чтобы оставить текущий:"]
    else:
        lines = [f"Current channel: {current_channel_name}", "Choose a new channel or send /skip to keep the current one:"]
    for i, ch in enumerate(channels, start=1):
        name = ch.get("name") or str(ch.get("chat_id"))
        lines.append(f"{i}. {name}")
    await state.update_data(_chan_map=channels)
    await message.answer("\n".join(lines))

@router.message(EditPost.channel, Command("skip"))
async def skip_edit_channel(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    # Keep current channel as is
    new_channel_id = orig_post.get("channel_id")
    new_chat_id = orig_post.get("chat_id")
    new_channel_name = None
    channels = supabase_db.db.list_channels(user_id=message.from_user.id)
    for ch in channels:
        if ch.get("id") == new_channel_id or ch.get("chat_id") == new_chat_id:
            new_channel_name = ch.get("name") or str(ch.get("chat_id"))
            break
    await state.update_data(new_channel_db_id=new_channel_id, new_channel_chat_id=new_chat_id, new_channel_name=new_channel_name)
    await show_edit_preview(message, state)

@router.message(EditPost.channel)
async def choose_edit_channel(message: Message, state: FSMContext):
    data = await state.get_data()
    channels = data.get("_chan_map", [])
    raw = (message.text or "").strip()
    chosen = None
    if raw.isdigit():
        idx = int(raw)
        if 1 <= idx <= len(channels):
            chosen = channels[idx - 1]
    else:
        for ch in channels:
            if str(ch["chat_id"]) == raw or (ch["name"] and ("@" + ch["name"]) == raw):
                chosen = ch
                break
    if not chosen:
        lang = data.get("user_settings", {}).get("language", "ru")
        await message.answer(TEXTS[lang]['edit_channel_error'] if 'edit_channel_error' in TEXTS[lang] else TEXTS[lang]['edit_post_not_found'])
        return
    await state.update_data(new_channel_db_id=chosen.get("id"), new_channel_chat_id=chosen.get("chat_id"), new_channel_name=chosen.get("name") or str(chosen.get("chat_id")))
    await show_edit_preview(message, state)

async def show_edit_preview(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    user = data.get("user_settings", {}) or {}
    lang = user.get("language", "ru")
    text = data.get("new_text", orig_post.get("text", "")) or ""
    media_id = data.get("new_media_id", orig_post.get("media_id"))
    media_type = data.get("new_media_type", orig_post.get("media_type"))
    fmt = data.get("new_format", orig_post.get("format") or "none")
    buttons = data.get("new_buttons", orig_post.get("buttons") or [])
    # Prepare markup for buttons
    btn_list = []
    if isinstance(buttons, str):
        try:
            btn_list = json.loads(buttons) if buttons else []
        except Exception:
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
    parse_mode = None
    if fmt and fmt.lower() == "markdown":
        parse_mode = "Markdown"
    elif fmt and fmt.lower() == "html":
        parse_mode = "HTML"
    try:
        if media_id and media_type:
            if media_type.lower() == "photo":
                await message.answer_photo(media_id, caption=text or TEXTS[lang]['no_text'], parse_mode=parse_mode, reply_markup=markup)
            elif media_type.lower() == "video":
                await message.answer_video(media_id, caption=text or TEXTS[lang]['no_text'], parse_mode=parse_mode, reply_markup=markup)
            else:
                await message.answer(text or TEXTS[lang]['no_text'], parse_mode=parse_mode, reply_markup=markup)
        else:
            await message.answer(text or TEXTS[lang]['no_text'], parse_mode=parse_mode, reply_markup=markup)
    except Exception as e:
        await message.answer(f"Предпросмотр сообщения недоступен: {e}")
    confirm_msg = ("Подтвердите изменение поста. Отправьте /confirm для сохранения или /cancel для отмены."
                   if lang == "ru" else
                   "Please confirm the changes. Send /confirm to save or /cancel to cancel.")
    await message.answer(confirm_msg)
    await state.set_state(EditPost.confirm)

@router.message(EditPost.confirm, Command("confirm"))
async def confirm_edit_command(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    post_id = orig_post.get("id")
    # Check if post got published in the meantime
    latest = supabase_db.db.get_post(post_id)
    if latest and latest.get("published"):
        lang = data.get("user_settings", {}).get("language", "ru")
        await message.answer(TEXTS[lang]['edit_post_published'])
        await state.clear()
        return
    updates = {}
    if "new_text" in data:
        updates["text"] = data["new_text"]
    if "new_media_id" in data:
        updates["media_id"] = data["new_media_id"]
        updates["media_type"] = data.get("new_media_type")
    if "new_format" in data:
        updates["format"] = data["new_format"]
    if "new_buttons" in data:
        updates["buttons"] = data["new_buttons"]
    if "new_publish_time" in data:
        pub_time = data["new_publish_time"]
        if isinstance(pub_time, datetime):
            updates["publish_time"] = pub_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            updates["publish_time"] = pub_time
        if pub_time is None:
            updates["draft"] = True
            updates["published"] = False
            updates["repeat_interval"] = 0
        else:
            updates["draft"] = False
    if "new_repeat_interval" in data:
        updates["repeat_interval"] = data["new_repeat_interval"]
    supabase_db.db.update_post(post_id, updates)
    lang = data.get("user_settings", {}).get("language", "ru")
    await message.answer(TEXTS[lang]['confirm_changes_saved'].format(id=post_id))
    await state.clear()
