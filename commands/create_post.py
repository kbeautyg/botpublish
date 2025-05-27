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
from states import CreatePost
from storage import supabase_db
import json

router = Router()


@router.message(Command("create"))
async def cmd_create(message: Message, state: FSMContext):
    if not supabase_db.db.list_channels():
        await message.answer("Нет каналов. Добавьте через /channels.")
        return
    await state.set_state(CreatePost.text)
    await message.answer("Шаг 1/7: отправьте текст поста (или /skip).")


# ---------- Шаг 1: текст ----------
@router.message(CreatePost.text, Command("skip"))
async def skip_text(message: Message, state: FSMContext):
    await state.update_data(text="")
    await next_media_step(message, state)


@router.message(CreatePost.text)
async def got_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text or "")
    await next_media_step(message, state)


async def next_media_step(message: Message, state: FSMContext):
    await state.set_state(CreatePost.media)
    await message.answer("Шаг 2/7: пришлите фото/видео или /skip.")


# ---------- Шаг 2: медиа ----------
@router.message(CreatePost.media, Command("skip"))
async def skip_media(message: Message, state: FSMContext):
    await state.update_data(media_id=None, media_type=None)
    await ask_format(message, state)


@router.message(CreatePost.media, F.photo)
async def got_photo(message: Message, state: FSMContext):
    await state.update_data(media_id=message.photo[-1].file_id, media_type="photo")
    await ask_format(message, state)


@router.message(CreatePost.media, F.video)
async def got_video(message: Message, state: FSMContext):
    await state.update_data(media_id=message.video.file_id, media_type="video")
    await ask_format(message, state)


@router.message(CreatePost.media)
async def wrong_media(message: Message):
    await message.answer("Отправьте фото/видео или /skip.")


async def ask_format(message: Message, state: FSMContext):
    await state.set_state(CreatePost.format)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Markdown"),
                KeyboardButton(text="HTML"),
                KeyboardButton(text="Без"),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer("Шаг 3/7: формат Markdown / HTML / Без", reply_markup=kb)


# ---------- Шаг 3: формат ----------
@router.message(CreatePost.format, Command("skip"))
async def skip_format(message: Message, state: FSMContext):
    await state.update_data(format="none")
    await ask_buttons(message, state)


@router.message(CreatePost.format)
async def got_format(message: Message, state: FSMContext):
    fmt_raw = (message.text or "").lower()
    fmt = "none"
    if fmt_raw.startswith("markdown"):
        fmt = "markdown"
    elif fmt_raw.startswith("html"):
        fmt = "html"
    await state.update_data(format=fmt)
    await ask_buttons(message, state)


async def ask_buttons(message: Message, state: FSMContext):
    await state.set_state(CreatePost.buttons)
    await message.answer(
        "Шаг 4/7: кнопки.\n"
        "Одна кнопка — одна строка: «Текст | URL».\n"
        "Если не нужны — /skip.",
        reply_markup=ReplyKeyboardRemove(),
    )


# ---------- Шаг 4: кнопки ----------
@router.message(CreatePost.buttons, Command("skip"))
async def skip_buttons(message: Message, state: FSMContext):
    await state.update_data(buttons=[])
    await ask_time(message, state)


@router.message(CreatePost.buttons)
async def got_buttons(message: Message, state: FSMContext):
    buttons = []
    for line in message.text.splitlines():
        if "|" in line:
            t, u = [s.strip() for s in line.split("|", 1)]
            if t and u:
                buttons.append({"text": t, "url": u})
    await state.update_data(buttons=buttons)
    await ask_time(message, state)


async def ask_time(message: Message, state: FSMContext):
    await state.set_state(CreatePost.time)
    await message.answer("Шаг 5/7: дата-время YYYY-MM-DD HH:MM (24ч).")


# ---------- Шаг 5: время ----------
@router.message(CreatePost.time)
async def got_time(message: Message, state: FSMContext):
    try:
        dt = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer("Формат ошибочен, пример: 2025-05-28 15:30")
        return
    await state.update_data(publish_time=dt)
    await ask_channel(message, state)


async def ask_channel(message: Message, state: FSMContext):
    await state.set_state(CreatePost.channel)
    chs = supabase_db.db.list_channels()
    lines = ["Шаг 6/7: введите номер канала:"]
    for i, ch in enumerate(chs, start=1):
        lines.append(f"{i}. {ch['name'] or ch['chat_id']}")
    await message.answer("\n".join(lines))
    await state.update_data(_chan_map=chs)


# ---------- Шаг 6: канал ----------
@router.message(CreatePost.channel)
async def channel_by_text(message: Message, state: FSMContext):
    data = await state.get_data()
    chan_map = data.get("_chan_map", [])
    raw = (message.text or "").strip()

    # номер из списка
    ch = None
    if raw.isdigit() and 1 <= int(raw) <= len(chan_map):
        ch = chan_map[int(raw) - 1]
    else:
        # chat_id/@username
        ch = next(
            (
                c
                for c in chan_map
                if str(c["chat_id"]) == raw or ("@" + (c["name"] or "")) == raw
            ),
            None,
        )

    if not ch:
        await message.answer("Канал не найден. Введите номер из списка или chat_id.")
        return

    await state.update_data(
        channel_chat_id=ch["chat_id"],
        channel_db_id=ch["id"],
        channel_name=ch["name"] or str(ch["chat_id"]),
    )
    await show_preview(message, state)


async def show_preview(msg: Message, state: FSMContext):
    data = await state.get_data()
    text = data["text"]
    fmt = data["format"]
    parse_mode = {"markdown": "Markdown", "html": "HTML"}.get(fmt, None)

    markup = None
    if data["buttons"]:
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(btn["text"], url=btn["url"])]
                for btn in data["buttons"]
            ]
        )

    if data["media_id"] and data["media_type"] == "photo":
        await msg.answer_photo(
            data["media_id"], caption=text or "", parse_mode=parse_mode, reply_markup=markup
        )
    elif data["media_id"] and data["media_type"] == "video":
        await msg.answer_video(
            data["media_id"], caption=text or "", parse_mode=parse_mode, reply_markup=markup
        )
    else:
        await msg.answer(text or "(без текста)", parse_mode=parse_mode, reply_markup=markup)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("✅ Подтвердить", callback_data="ok"),
                InlineKeyboardButton("❌ Отмена", callback_data="no"),
            ]
        ]
    )
    await msg.answer(
        f"Шаг 7/7: подтвердите публикацию в "
        f"«{data['channel_name']}» {data['publish_time']} UTC.",
        reply_markup=kb,
    )
    await state.set_state(CreatePost.confirm)


# ---------- Шаг 7: подтверждение ----------
@router.callback_query(CreatePost.confirm, F.data == "ok")
async def confirm_ok(cb: types.CallbackQuery, state: FSMContext):
    d = await state.get_data()
    supabase_db.db.add_post(
        {
            "channel_id": d["channel_db_id"],
            "chat_id": d["channel_chat_id"],
            "text": d["text"],
            "media_id": d["media_id"],
            "media_type": d["media_type"],
            "format": d["format"],
            "buttons": json.dumps(d["buttons"]),
            "publish_time": d["publish_time"].strftime("%Y-%m-%dT%H:%M:%S"),
            "published": False,
        }
    )
    await cb.message.answer("Пост запланирован ✅")
    await state.clear()
    await cb.answer()


@router.callback_query(CreatePost.confirm, F.data == "no")
async def confirm_no(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("Отменено.")
    await state.clear()
    await cb.answer()
