# commands/edit_post.py
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

def format_to_strptime(date_fmt: str, time_fmt: str):
    fmt = date_fmt.replace("YYYY", "%Y").replace("YY", "%y")
    fmt = fmt.replace("MM", "%m").replace("DD", "%d")
    t_fmt = time_fmt
    t_fmt = t_fmt.replace("HH", "%H").replace("H", "%H")
    if "hh" in t_fmt or "AM" in t_fmt or "PM" in t_fmt or "am" in t_fmt or "pm" in t_fmt:
        t_fmt = t_fmt.replace("hh", "%I").replace("HH", "%I")
        t_fmt = t_fmt.replace("AM", "%p").replace("PM", "%p").replace("am", "%p").replace("pm", "%p")
    else:
        t_fmt = t_fmt.replace("MM", "%M").replace("M", "%M")
        t_fmt = t_fmt.replace("SS", "%S").replace("S", "%S")
    return fmt + " " + t_fmt

def parse_time(user: dict, text: str):
    date_fmt = user.get("date_format", "YYYY-MM-DD")
    time_fmt = user.get("time_format", "HH:MM")
    tz_name = user.get("timezone", "UTC")
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
    time_fmt = user.get("time_format", "HH:MM")
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
    new_text = orig_post.get("text", "") if text_input.startswith("/skip") else text_input
    await state.update_data(new_text=new_text)
    await state.set_state(EditPost.media)
    if orig_post.get("media_id"):
        media_type = orig_post.get("media_type")
        if media_type == "photo":
            info = TEXTS['ru']['media_photo'] if data.get("user_settings", {}).get("language", "ru") == "ru" else TEXTS['en']['media_photo']
        elif media_type == "video":
            info = TEXTS['ru']['media_video'] if data.get("user_settings", {}).get("language", "ru") == "ru" else TEXTS['en']['media_video']
        else:
            info = TEXTS['ru']['media_media'] if data.get("user_settings", {}).get("language", "ru") == "ru" else TEXTS['en']['media_media']
        lang = data.get("user_settings", {}).get("language", "ru")
        await message.answer(TEXTS[lang]['edit_current_media'].format(info=info))
    else:
        lang = data.get("user_settings", {}).get("language", "ru")
        await message.answer(TEXTS[lang]['edit_no_media'])

@router.message(Command("skip"), EditPost.media)
async def skip_edit_media(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    await state.update_data(new_media_id=orig_post.get("media_id"), new_media_type=orig_post.get("media_type"))
    await state.set_state(EditPost.format)
    lang = data.get("user_settings", {}).get("language", "ru")
    current_fmt = orig_post.get("format") or "none"
    none_text = "Без" if lang == "ru" else "None"
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Markdown"), KeyboardButton(text="HTML"), KeyboardButton(text=none_text)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(TEXTS[lang]['edit_current_format'].format(format=current_fmt), reply_markup=kb)

@router.message(EditPost.media, F.photo)
async def edit_new_photo(message: Message, state: FSMContext):
    await state.update_data(new_media_id=message.photo[-1].file_id, new_media_type="photo")
    await state.set_state(EditPost.format)
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    lang = data.get("user_settings", {}).get("language", "ru")
    current_fmt = orig_post.get("format") or "none"
    none_text = "Без" if lang == "ru" else "None"
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Markdown"), KeyboardButton(text="HTML"), KeyboardButton(text=none_text)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(TEXTS[lang]['edit_current_format'].format(format=current_fmt), reply_markup=kb)

@router.message(EditPost.media, F.video)
async def edit_new_video(message: Message, state: FSMContext):
    await state.update_data(new_media_id=message.video.file_id, new_media_type="video")
    await state.set_state(EditPost.format)
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    lang = data.get("user_settings", {}).get("language", "ru")
    current_fmt = orig_post.get("format") or "none"
    none_text = "Без" if lang == "ru" else "None"
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Markdown"), KeyboardButton(text="HTML"), KeyboardButton(text=none_text)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(TEXTS[lang]['edit_current_format'].format(format=current_fmt), reply_markup=kb)

@router.message(EditPost.media)
async def edit_invalid_media(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("user_settings", {}).get("language", "ru")
    if data.get("orig_post", {}).get("media_id"):
        await message.answer(TEXTS[lang]['edit_current_media'].format(info=""))
    else:
        await message.answer(TEXTS[lang]['edit_no_media'])

@router.message(Command("skip"), EditPost.format)
async def skip_edit_format(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    await state.update_data(new_format=orig_post.get("format") or "none")
    await state.set_state(EditPost.buttons)
    lang = data.get("user_settings", {}).get("language", "ru")
    buttons_json = orig_post.get("buttons")
    btn_list = []
    if buttons_json:
        try:
            btn_list = supabase_db.json.loads(buttons_json)
        except Exception:
            btn_list = json.loads(buttons_json) if isinstance(buttons_json, str) else buttons_json
    if btn_list:
        lines = []
        for btn in btn_list:
            if isinstance(btn, dict):
                lines.append(f"{btn.get('text')} -> {btn.get('url')}")
            elif isinstance(btn, (list, tuple)) and len(btn) >= 2:
                lines.append(f"{btn[0]} -> {btn[1]}")
        buttons_list = "\n".join(lines)
        await message.answer(TEXTS[lang]['edit_current_buttons'].format(buttons_list=buttons_list))
    else:
        await message.answer(TEXTS[lang]['edit_no_buttons'])

@router.message(EditPost.format)
async def edit_step_format(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    raw = (message.text or "").strip().lower()
    new_fmt = orig_post.get("format") or "none" if raw.startswith("/skip") else ("markdown" if raw.startswith("markdown") else "html" if raw.startswith("html") else "none")
    await state.update_data(new_format=new_fmt)
    await state.set_state(EditPost.buttons)
    lang = data.get("user_settings", {}).get("language", "ru")
    buttons_json = orig_post.get("buttons")
    btn_list = []
    if buttons_json:
        try:
            btn_list = supabase_db.json.loads(buttons_json)
        except Exception:
            btn_list = json.loads(buttons_json) if isinstance(buttons_json, str) else buttons_json
    if btn_list:
        lines = []
        for btn in btn_list:
            if isinstance(btn, dict):
                lines.append(f"{btn.get('text')} -> {btn.get('url')}")
            elif isinstance(btn, (list, tuple)) and len(btn) >= 2:
                lines.append(f"{btn[0]} -> {btn[1]}")
        buttons_list = "\n".join(lines)
        await message.answer(TEXTS[lang]['edit_current_buttons'].format(buttons_list=buttons_list))
    else:
        await message.answer(TEXTS[lang]['edit_no_buttons'])

@router.message(EditPost.buttons)
async def edit_step_buttons(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    text = message.text.strip()
    if text.lower() in ("none", "нет"):
        new_buttons = []
    elif text.startswith("/skip"):
        new_buttons = orig_post.get("buttons") or []
    else:
        buttons = []
        for line in text.splitlines():
            parts = line.split("|", maxsplit=1)
            if len(parts) == 2:
                btn_text = parts[0].strip(); btn_url = parts[1].strip()
                if btn_text and btn_url:
                    buttons.append({"text": btn_text, "url": btn_url})
        new_buttons = buttons
    await state.update_data(new_buttons=new_buttons)
    await state.set_state(EditPost.time)
    lang = data.get("user_settings", {}).get("language", "ru")
    orig_time = orig_post.get("publish_time")
    current_time_str = "(черновик)" if (not orig_time) and lang == "ru" else "(draft)" if (not orig_time) else str(orig_time)
    fmt_str = f"{data.get('user_settings', {}).get('date_format', 'YYYY-MM-DD')} {data.get('user_settings', {}).get('time_format', 'HH:MM')}"
    await message.answer(TEXTS[lang]['edit_current_time'].format(time=current_time_str, format=fmt_str))

@router.message(Command("skip"), EditPost.time)
async def skip_edit_time(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    await state.update_data(new_publish_time=orig_post.get("publish_time"))
    await state.set_state(EditPost.repeat)
    lang = data.get("user_settings", {}).get("language", "ru")
    orig_interval = orig_post.get("repeat_interval", 0)
    if not orig_interval or orig_interval == 0:
        curr_repeat = "0"
    elif orig_interval % 86400 == 0:
        days = orig_interval // 86400; curr_repeat = f"{days}d"
    elif orig_interval % 3600 == 0:
        hours = orig_interval // 3600; curr_repeat = f"{hours}h"
    else:
        minutes = orig_interval // 60; curr_repeat = f"{minutes}m"
    await message.answer(TEXTS[lang]['edit_current_repeat'].format(repeat=curr_repeat))

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
            await message.answer(TEXTS[lang]['edit_time_error'].format(format=f"{user.get('date_format', 'YYYY-MM-DD')} {user.get('time_format', 'HH:MM')}"))
            example = format_example(user)
            await message.answer("(" + example + ")")
            return
    await state.update_data(new_publish_time=new_time)
    await state.set_state(EditPost.repeat)
    orig_post = data.get("orig_post", {})
    orig_interval = orig_post.get("repeat_interval", 0)
    if not orig_interval or orig_interval == 0:
        curr_repeat = "0"
    elif orig_interval % 86400 == 0:
        days = orig_interval // 86400; curr_repeat = f"{days}d"
    elif orig_interval % 3600 == 0:
        hours = orig_interval // 3600; curr_repeat = f"{hours}h"
    else:
        minutes = orig_interval // 60; curr_repeat = f"{minutes}m"
    await message.answer(TEXTS[lang]['edit_current_repeat'].format(repeat=curr_repeat))

@router.message(Command("skip"), EditPost.repeat)
async def skip_edit_repeat(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    await state.update_data(new_repeat_interval=orig_post.get("repeat_interval", 0))
    await state.set_state(EditPost.channel)
    lang = data.get("user_settings", {}).get("language", "ru")
    channels = supabase_db.db.list_channels(user_id=message.from_user.id)
    current_channel = None
    current_channel_name = "unknown"
    if orig_post:
        chan_id = orig_post.get("channel_id"); chat_id = orig_post.get("chat_id")
        for ch in channels:
            if chan_id and ch.get("id") == chan_id:
                current_channel = ch; break
            if chat_id and ch.get("chat_id") == chat_id:
                current_channel = ch; break
    if current_channel:
        current_channel_name = current_channel.get("name") or str(current_channel.get("chat_id"))
    prompt_text = (f"Текущий канал: {current_channel_name}\nВыберите новый канал или нажмите 'Оставить текущий':"
                   if lang == "ru" else
                   f"Current channel: {current_channel_name}\nChoose a new channel or press 'Keep current':")
    btns = [[InlineKeyboardButton(text=ch.get("name") or str(ch.get("chat_id")), callback_data=f"ch_edit:{ch.get('chat_id')}")] for ch in channels]
    btns.append([InlineKeyboardButton(text=TEXTS[lang]['edit_keep_current_channel'], callback_data="ch_edit_skip")])
    markup = InlineKeyboardMarkup(inline_keyboard=btns)
    await message.answer(prompt_text, reply_markup=markup)

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
    await state.set_state(EditPost.channel)
    orig_post = data.get("orig_post", {})
    channels = supabase_db.db.list_channels(user_id=message.from_user.id)
    current_channel = None
    current_channel_name = "unknown"
    if orig_post:
        chan_id = orig_post.get("channel_id"); chat_id = orig_post.get("chat_id")
        for ch in channels:
            if chan_id and ch.get("id") == chan_id:
                current_channel = ch; break
            if chat_id and ch.get("chat_id") == chat_id:
                current_channel = ch; break
    if current_channel:
        current_channel_name = current_channel.get("name") or str(current_channel.get("chat_id"))
    prompt_text = (f"Текущий канал: {current_channel_name}\nВыберите новый канал или нажмите 'Оставить текущий':"
                   if lang == "ru" else
                   f"Current channel: {current_channel_name}\nChoose a new channel or press 'Keep current':")
    btns = [[InlineKeyboardButton(text=ch.get("name") or str(ch.get("chat_id")), callback_data=f"ch_edit:{ch.get('chat_id')}")] for ch in channels]
    btns.append([InlineKeyboardButton(text=TEXTS[lang]['edit_keep_current_channel'], callback_data="ch_edit_skip")])
    markup = InlineKeyboardMarkup(inline_keyboard=btns)
    await message.answer(prompt_text, reply_markup=markup)

@router.callback_query(EditPost.channel)
async def edit_channel_select(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    cb_data = callback.data
    if cb_data == "ch_edit_skip":
        new_channel_id = orig_post.get("channel_id")
        new_chat_id = orig_post.get("chat_id")
        new_channel_name = None
        channels = supabase_db.db.list_channels(user_id=callback.from_user.id)
        for ch in channels:
            if ch.get("id") == new_channel_id or ch.get("chat_id") == new_chat_id:
                new_channel_name = ch.get("name") or str(ch.get("chat_id"))
                break
        await state.update_data(new_channel_db_id=new_channel_id, new_channel_chat_id=new_chat_id, new_channel_name=new_channel_name)
    elif cb_data.startswith("ch_edit:"):
        cid_str = cb_data.split(":", 1)[1]
        try:
            chat_id = int(cid_str)
        except:
            chat_id = cid_str
        channel_id = None
        channel_name = str(chat_id)
        channels = supabase_db.db.list_channels(user_id=callback.from_user.id)
        for ch in channels:
            if ch.get("chat_id") == chat_id:
                channel_id = ch.get("id")
                channel_name = ch.get("name") or channel_name
                break
        await state.update_data(new_channel_db_id=channel_id, new_channel_chat_id=chat_id, new_channel_name=channel_name)
    else:
        await callback.answer()
        return
    await state.set_state(EditPost.confirm)
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    text = data.get("new_text", orig_post.get("text", "")) or ""
    media_id = data.get("new_media_id", orig_post.get("media_id"))
    media_type = data.get("new_media_type", orig_post.get("media_type"))
    fmt = data.get("new_format", orig_post.get("format") or "none")
    buttons = data.get("new_buttons", orig_post.get("buttons") or [])
    btn_list = []
    import json
    if isinstance(buttons, str):
        try:
            btn_list = supabase_db.json.loads(buttons)
        except Exception:
            btn_list = json.loads(buttons) if buttons else []
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
            if media_type == "photo":
                await callback.message.answer_photo(photo=media_id, caption=text or TEXTS['ru']['no_text'], parse_mode=parse_mode, reply_markup=markup)
            elif media_type == "video":
                await callback.message.answer_video(video=media_id, caption=text or TEXTS['ru']['no_text'], parse_mode=parse_mode, reply_markup=markup)
            else:
                await callback.message.answer(text or TEXTS['ru']['no_text'], parse_mode=parse_mode, reply_markup=markup)
        else:
            await callback.message.answer(text or TEXTS['ru']['no_text'], parse_mode=parse_mode, reply_markup=markup)
    except Exception as e:
        await callback.message.answer(f"Предпросмотр сообщения недоступен: {e}")
    confirm_markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Сохранить изменения" if data.get("user_settings", {}).get("language", "ru") == "ru" else "✅ Save changes", callback_data="edit_confirm"),
        InlineKeyboardButton(text="❌ Отмена" if data.get("user_settings", {}).get("language", "ru") == "ru" else "❌ Cancel", callback_data="edit_cancel")
    ]])
    lang = data.get("user_settings", {}).get("language", "ru")
    confirm_prompt = "Подтвердите изменение поста." if lang == "ru" else "Please confirm the changes."
    await callback.message.answer(confirm_prompt, reply_markup=confirm_markup)
    await callback.answer()

@router.callback_query(F.data == "edit_confirm", EditPost.confirm)
async def confirm_edit(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    post_id = orig_post.get("id")
    latest = supabase_db.db.get_post(post_id)
    if latest and latest.get("published"):
        lang = data.get("user_settings", {}).get("language", "ru")
        await callback.message.answer(TEXTS[lang]['edit_post_published'])
        await state.clear()
        await callback.answer("Cancelled")
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
    await callback.message.answer(TEXTS[lang]['confirm_changes_saved'].format(id=post_id))
    await state.clear()
    await callback.answer("Обновлено" if lang == "ru" else "Updated")
    try:
        await callback.message.edit_text(TEXTS[lang]['edit_saved_notify'])
    except:
        pass

@router.callback_query(F.data == "edit_cancel", EditPost.confirm)
async def cancel_edit(callback: types.CallbackQuery, state: FSMContext):
    lang = "ru"
    data = await state.get_data()
    if data.get("user_settings"):
        lang = data["user_settings"].get("language", "ru")
    await callback.message.answer(TEXTS[lang]['edit_cancelled'])
    await state.clear()
    await callback.answer("Отменено" if lang == "ru" else "Cancelled")
    try:
        await callback.message.edit_text(TEXTS[lang]['edit_cancel_notify'])
    except:
        pass
