# commands/edit_post.py
import json
from aiogram import Router, types, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime
from zoneinfo import ZoneInfo

from states import EditPost
from storage import supabase_db
from commands import TEXTS

router = Router()


# ───────────────────────── date / time helpers ──────────────────────────
def format_to_strptime(date_fmt: str, time_fmt: str) -> str:
    fmt = date_fmt.replace("YYYY", "%Y").replace("YY", "%y")
    fmt = fmt.replace("MM", "%m").replace("DD", "%d")
    t_fmt = time_fmt.replace("HH", "%H").replace("H", "%H")
    if any(x in t_fmt for x in ("hh", "AM", "PM", "am", "pm")):
        t_fmt = (
            t_fmt.replace("hh", "%I")
            .replace("HH", "%I")
            .replace("AM", "%p")
            .replace("PM", "%p")
            .replace("am", "%p")
            .replace("pm", "%p")
        )
    else:
        t_fmt = (
            t_fmt.replace("MM", "%M")
            .replace("M", "%M")
            .replace("SS", "%S")
            .replace("S", "%S")
        )
    return f"{fmt} {t_fmt}"


def parse_time(user: dict, text: str) -> datetime:
    date_fmt = user.get("date_format", "YYYY-MM-DD")
    time_fmt = user.get("time_format", "HH:MM")
    tz_name = user.get("timezone", "UTC")
    fmt = format_to_strptime(date_fmt, time_fmt)
    dt = datetime.strptime(text, fmt)
    tz = ZoneInfo(tz_name) if tz_name else ZoneInfo("UTC")
    return dt.replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))


def format_example(user: dict) -> str:
    date_fmt = user.get("date_format", "YYYY-MM-DD")
    time_fmt = user.get("time_format", "HH:MM")
    fmt = format_to_strptime(date_fmt, time_fmt)
    try:
        return datetime.now().strftime(fmt)
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M")


# ─────────────────────────── command entry ──────────────────────────────
@router.message(Command("edit"))
async def cmd_edit(message: Message, state: FSMContext):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)

    user = supabase_db.db.get_user(user_id) or supabase_db.db.ensure_user(user_id)
    lang = user.get("language", "ru")

    if len(args) < 2:
        await message.answer(TEXTS[lang]["edit_usage"])
        return

    try:
        post_id = int(args[1])
    except ValueError:
        await message.answer(TEXTS[lang]["edit_invalid_id"])
        return

    post = supabase_db.db.get_post(post_id)
    if not post or post.get("user_id") != user_id:
        await message.answer(TEXTS[lang]["edit_post_not_found"])
        return
    if post.get("published"):
        await message.answer(TEXTS[lang]["edit_post_published"])
        return

    await state.update_data(orig_post=post, user_settings=user)
    await state.set_state(EditPost.text)
    await message.answer(
        TEXTS[lang]["edit_begin"].format(id=post_id, text=post.get("text") or "")
    )


# ───────────────────────── step 1: text ────────────────────────────────
@router.message(EditPost.text)
async def edit_step_text(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data["orig_post"]
    lang = data["user_settings"]["language"]

    text_input = message.text or ""
    new_text = orig_post["text"] if text_input.startswith("/skip") else text_input

    await state.update_data(new_text=new_text)
    await state.set_state(EditPost.media)

    if orig_post.get("media_id"):
        media_type = orig_post.get("media_type")
        info_key = {
            "photo": "media_photo",
            "video": "media_video",
        }.get(media_type, "media_media")
        await message.answer(TEXTS[lang]["edit_current_media"].format(info=TEXTS[lang][info_key]))
    else:
        await message.answer(TEXTS[lang]["edit_no_media"])


# ───────────────────────── step 2: media ───────────────────────────────
@router.message(Command("skip"), EditPost.media)
async def skip_edit_media(message: Message, state: FSMContext):
    data = await state.get_data()
    orig = data["orig_post"]
    lang = data["user_settings"]["language"]

    await state.update_data(
        new_media_id=orig.get("media_id"), new_media_type=orig.get("media_type")
    )
    await state.set_state(EditPost.format)

    none_text = "Без" if lang == "ru" else "None"
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t) for t in ("Markdown", "HTML", none_text)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(
        TEXTS[lang]["edit_current_format"].format(format=orig.get("format") or "none"),
        reply_markup=kb,
    )


@router.message(EditPost.media, F.photo)
async def edit_new_photo(message: Message, state: FSMContext):
    await state.update_data(
        new_media_id=message.photo[-1].file_id, new_media_type="photo"
    )
    await ask_format(message, state)


@router.message(EditPost.media, F.video)
async def edit_new_video(message: Message, state: FSMContext):
    await state.update_data(
        new_media_id=message.video.file_id, new_media_type="video"
    )
    await ask_format(message, state)


@router.message(EditPost.media)
async def edit_invalid_media(message: Message, state: FSMContext):
    lang = (await state.get_data())["user_settings"]["language"]
    await message.answer(TEXTS[lang]["edit_no_media"])


async def ask_format(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data["user_settings"]["language"]
    none_text = "Без" if lang == "ru" else "None"

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t) for t in ("Markdown", "HTML", none_text)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await state.set_state(EditPost.format)
    await message.answer(TEXTS[lang]["edit_current_format"].format(format=data["orig_post"].get("format") or "none"), reply_markup=kb)


# ───────────────────────── step 3: format ──────────────────────────────
@router.message(Command("skip"), EditPost.format)
async def skip_edit_format(message: Message, state: FSMContext):
    data = await state.get_data()
    orig = data["orig_post"]
    lang = data["user_settings"]["language"]

    await state.update_data(new_format=orig.get("format") or "none")
    await state.set_state(EditPost.buttons)
    await send_buttons_prompt(message, state, lang, orig)


@router.message(EditPost.format)
async def edit_step_format(message: Message, state: FSMContext):
    data = await state.get_data()
    orig = data["orig_post"]
    lang = data["user_settings"]["language"]

    raw = (message.text or "").strip().lower()
    new_fmt = (
        orig.get("format") or "none"
        if raw.startswith("/skip")
        else "markdown"
        if raw.startswith("markdown")
        else "html"
        if raw.startswith("html")
        else "none"
    )
    await state.update_data(new_format=new_fmt)
    await state.set_state(EditPost.buttons)
    await send_buttons_prompt(message, state, lang, orig)


async def send_buttons_prompt(message: Message, state: FSMContext, lang: str, orig_post: dict):
    buttons_json = orig_post.get("buttons")
    btn_list = []
    if buttons_json:
        btn_list = json.loads(buttons_json) if isinstance(buttons_json, str) else buttons_json

    if btn_list:
        lines = [
            f"{btn.get('text')} -> {btn.get('url')}"
            if isinstance(btn, dict)
            else f"{btn[0]} -> {btn[1]}"
            for btn in btn_list
        ]
        await message.answer(
            TEXTS[lang]["edit_current_buttons"].format(buttons_list="\n".join(lines))
        )
    else:
        await message.answer(TEXTS[lang]["edit_no_buttons"])


# ───────────────────────── step 4: buttons ─────────────────────────────
@router.message(EditPost.buttons)
async def edit_step_buttons(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data["orig_post"]
    lang = data["user_settings"]["language"]

    text = message.text.strip()
    if text.lower() in ("none", "нет"):
        new_buttons = []
    elif text.startswith("/skip"):
        new_buttons = orig_post.get("buttons") or []
    else:
        buttons = []
        for line in text.splitlines():
            if "|" in line:
                t, u = line.split("|", 1)
                buttons.append({"text": t.strip(), "url": u.strip()})
        new_buttons = buttons

    await state.update_data(new_buttons=new_buttons)
    await state.set_state(EditPost.time)

    publish_time = orig_post.get("publish_time")
    current_time_str = (
        "(черновик)" if not publish_time and lang == "ru" else "(draft)"
        if not publish_time
        else str(publish_time)
    )
    fmt_str = f"{data['user_settings'].get('date_format', 'YYYY-MM-DD')} {data['user_settings'].get('time_format', 'HH:MM')}"
    await message.answer(
        TEXTS[lang]["edit_current_time"].format(time=current_time_str, format=fmt_str)
    )


# ───────────────────────── step 5: time ────────────────────────────────
@router.message(Command("skip"), EditPost.time)
async def skip_edit_time(message: Message, state: FSMContext):
    data = await state.get_data()
    orig = data["orig_post"]
    await state.update_data(new_publish_time=orig.get("publish_time"))
    await ask_repeat(message, state)


@router.message(EditPost.time)
async def edit_step_time(message: Message, state: FSMContext):
    data = await state.get_data()
    user = data["user_settings"]
    lang = user["language"]

    text = message.text.strip()
    if text.lower() in ("none", "нет"):
        new_time = None
    else:
        try:
            new_time = parse_time(user, text)
        except Exception:
            await message.answer(
                TEXTS[lang]["edit_time_error"].format(
                    format=f"{user.get('date_format', 'YYYY-MM-DD')} {user.get('time_format', 'HH:MM')}"
                )
            )
            await message.answer("(" + format_example(user) + ")")
            return
    await state.update_data(new_publish_time=new_time)
    await ask_repeat(message, state)


async def ask_repeat(message: Message, state: FSMContext):
    data = await state.get_data()
    orig = data["orig_post"]
    lang = data["user_settings"]["language"]

    await state.set_state(EditPost.repeat)
    repeat_interval = orig.get("repeat_interval", 0)
    if repeat_interval == 0:
        curr_repeat = "0"
    elif repeat_interval % 86400 == 0:
        curr_repeat = f"{repeat_interval // 86400}d"
    elif repeat_interval % 3600 == 0:
        curr_repeat = f"{repeat_interval // 3600}h"
    else:
        curr_repeat = f"{repeat_interval // 60}m"

    await message.answer(
        TEXTS[lang]["edit_current_repeat"].format(repeat=curr_repeat)
    )


# ───────────────────────── step 6: repeat ──────────────────────────────
@router.message(Command("skip"), EditPost.repeat)
async def skip_edit_repeat(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(new_repeat_interval=data["orig_post"].get("repeat_interval", 0))
    await ask_channel(message, state)


@router.message(EditPost.repeat)
async def edit_step_repeat(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data["user_settings"]["language"]

    raw = message.text.strip().lower()
    if raw in ("0", "none", "нет"):
        interval = 0
    else:
        unit = raw[-1]
        try:
            value = int(raw[:-1])
        except ValueError:
            value = None
        if not value or unit not in ("d", "h", "m"):
            await message.answer(TEXTS[lang]["edit_repeat_error"])
            return
        interval = value * {"d": 86400, "h": 3600, "m": 60}[unit]

    await state.update_data(new_repeat_interval=interval)
    await ask_channel(message, state)


# ───────────────────────── step 7: channel ─────────────────────────────
async def ask_channel(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data["user_settings"]["language"]
    user_id = message.from_user.id
    channels = supabase_db.db.list_channels(user_id=user_id)

    current_channel_name = "unknown"
    chan_id, chat_id = data["orig_post"].get("channel_id"), data["orig_post"].get("chat_id")
    for ch in channels:
        if ch.get("id") == chan_id or ch.get("chat_id") == chat_id:
            current_channel_name = ch.get("name") or str(ch.get("chat_id"))
            break

    prompt = (
        f"Текущий канал: {current_channel_name}\nВыберите новый канал или нажмите 'Оставить текущий':"
        if lang == "ru"
        else f"Current channel: {current_channel_name}\nChoose a new channel or press 'Keep current':"
    )

    kb = [
        [InlineKeyboardButton(text=ch.get("name") or str(ch["chat_id"]), callback_data=f"ch_edit:{ch['chat_id']}")]
        for ch in channels
    ]
    kb.append([InlineKeyboardButton(text=TEXTS[lang]["edit_keep_current_channel"], callback_data="ch_edit_skip")])

    await state.set_state(EditPost.channel)
    await message.answer(prompt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(EditPost.channel)
async def edit_channel_select(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cb_data = callback.data
    lang = data["user_settings"]["language"]

    if cb_data == "ch_edit_skip":
        new_channel_id = data["orig_post"].get("channel_id")
        new_chat_id = data["orig_post"].get("chat_id")
        new_name = _find_channel_name(callback.from_user.id, new_chat_id, new_channel_id)
    elif cb_data.startswith("ch_edit:"):
        chat_id = int(cb_data.split(":", 1)[1])
        new_channel_id, new_name = _channel_id_and_name(callback.from_user.id, chat_id)
        new_chat_id = chat_id
    else:
        await callback.answer()
        return

    await state.update_data(
        new_channel_db_id=new_channel_id,
        new_channel_chat_id=new_chat_id,
        new_channel_name=new_name,
    )
    await state.set_state(EditPost.confirm)
    await show_preview(callback, state, lang)
    await callback.answer()


def _find_channel_name(user_id: int, chat_id: int | None, chan_id: int | None) -> str:
    channels = supabase_db.db.list_channels(user_id=user_id)
    for ch in channels:
        if ch.get("id") == chan_id or ch.get("chat_id") == chat_id:
            return ch.get("name") or str(ch.get("chat_id"))
    return str(chat_id) if chat_id else "unknown"


def _channel_id_and_name(user_id: int, chat_id: int):
    channels = supabase_db.db.list_channels(user_id=user_id)
    for ch in channels:
        if ch.get("chat_id") == chat_id:
            return ch.get("id"), ch.get("name") or str(chat_id)
    return None, str(chat_id)


# ───────────────────────── step 8: preview & confirm ───────────────────
async def show_preview(callback: types.CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    orig_post = data["orig_post"]

    text = data.get("new_text", orig_post.get("text") or "") or ""
    media_id = data.get("new_media_id", orig_post.get("media_id"))
    media_type = data.get("new_media_type", orig_post.get("media_type"))
    fmt = data.get("new_format", orig_post.get("format") or "none")

    buttons = data.get("new_buttons", orig_post.get("buttons") or [])
    btn_list = (
        json.loads(buttons) if isinstance(buttons, str) else buttons
    )
    markup = None
    if btn_list:
        kb = [
            [InlineKeyboardButton(text=b["text"], url=b["url"])]
            for b in btn_list
            if isinstance(b, dict)
        ]
        markup = InlineKeyboardMarkup(inline_keyboard=kb)

    parse_mode = {"markdown": "Markdown", "html": "HTML"}.get(fmt.lower())

    try:
        if media_id and media_type == "photo":
            await callback.message.answer_photo(
                media_id, caption=text or TEXTS[lang]["no_text"], parse_mode=parse_mode, reply_markup=markup
            )
        elif media_id and media_type == "video":
            await callback.message.answer_video(
                media_id, caption=text or TEXTS[lang]["no_text"], parse_mode=parse_mode, reply_markup=markup
            )
        else:
            await callback.message.answer(
                text or TEXTS[lang]["no_text"], parse_mode=parse_mode, reply_markup=markup
            )
    except Exception as e:
        await callback.message.answer(f"Предпросмотр недоступен: {e}")

    confirm_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Сохранить изменения" if lang == "ru" else "✅ Save changes",
                    callback_data="edit_confirm",
                ),
                InlineKeyboardButton(
                    text="❌ Отмена" if lang == "ru" else "❌ Cancel",
                    callback_data="edit_cancel",
                ),
            ]
        ]
    )
    prompt = "Подтвердите изменение поста." if lang == "ru" else "Please confirm the changes."
    await callback.message.answer(prompt, reply_markup=confirm_kb)


# ───────────────────────── confirm / cancel ────────────────────────────
@router.callback_query(F.data == "edit_confirm", EditPost.confirm)
async def confirm_edit(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    orig_post = data["orig_post"]
    post_id = orig_post["id"]

    latest = supabase_db.db.get_post(post_id)
    lang = data["user_settings"]["language"]
    if latest and latest.get("published"):
        await callback.message.answer(TEXTS[lang]["edit_post_published"])
        await state.clear()
        await callback.answer()
        return

    updates = {}
    if "new_text" in data:
        updates["text"] = data["new_text"]
    if "new_media_id" in data:
        updates["media_id"] = data["new_media_id"]
        updates["media_type"] = data["new_media_type"]
    if "new_format" in data:
        updates["format"] = data["new_format"]
    if "new_buttons" in data:
        updates["buttons"] = data["new_buttons"]
    if "new_publish_time" in data:
        pt = data["new_publish_time"]
        updates["publish_time"] = pt.strftime("%Y-%m-%dT%H:%M:%SZ") if isinstance(pt, datetime) else pt
        updates["draft"] = pt is None
        if pt is None:
            updates["repeat_interval"] = 0
    if "new_repeat_interval" in data:
        updates["repeat_interval"] = data["new_repeat_interval"]
    if "new_channel_db_id" in data:
        updates["channel_id"] = data["new_channel_db_id"]
        updates["chat_id"] = data["new_channel_chat_id"]

    supabase_db.db.update_post(post_id, updates)

    await callback.message.answer(TEXTS[lang]["confirm_changes_saved"].format(id=post_id))
    await state.clear()
    try:
        await callback.message.edit_text(TEXTS[lang]["edit_saved_notify"])
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "edit_cancel", EditPost.confirm)
async def cancel_edit(callback: types.CallbackQuery, state: FSMContext):
    lang = (await state.get_data())["user_settings"]["language"]
    await callback.message.answer(TEXTS[lang]["edit_cancelled"])
    await state.clear()
    try:
        await callback.message.edit_text(TEXTS[lang]["edit_cancel_notify"])
    except Exception:
        pass
    await callback.answer()
