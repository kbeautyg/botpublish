# commands/create_post.py
from aiogram import Router, types, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from datetime import datetime
from states import CreatePost
from storage import supabase_db

router = Router()

@router.message(Command("create"))
async def cmd_create(message: Message, state: FSMContext):
    # Check if there are any channels configured
    channels = supabase_db.db.list_channels()
    if not channels:
        await message.answer("Нет доступных каналов. Сначала добавьте канал через команду /channels.")
        return
    # Start the FSM for creating a post
    await state.set_state(CreatePost.text)
    await message.answer("Шаг 1/7: Отправьте текст поста (или /skip для пустого текста).")

@router.message(CreatePost.text)
async def step_text(message: Message, state: FSMContext):
    # Save post text (can be empty string if skipped)
    text = message.text
    if text and text.startswith("/skip"):
        text = ""  # user chose to skip text
    # Save text in FSM context
    await state.update_data(text=text or "")
    # Next step: media
    await state.set_state(CreatePost.media)
    await message.answer("Шаг 2/7: Отправьте фото или видео для поста, или введите /skip, чтобы пропустить.")

@router.message(Command("skip"), CreatePost.media)
async def skip_media(message: Message, state: FSMContext):
    # No media
    await state.update_data(media_id=None, media_type=None)
    # Next step: format
    await state.set_state(CreatePost.format)
    # Provide options for formatting (Markdown/HTML/None)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            ["Markdown", "HTML", "Без форматирования"]
        ],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    await message.answer("Шаг 3/7: Выберите тип форматирования (Markdown, HTML или Без форматирования).", reply_markup=keyboard)

@router.message(F.photo, CreatePost.media)
async def receive_photo(message: Message, state: FSMContext):
    # User sent a photo
    photo = message.photo[-1]
    file_id = photo.file_id
    await state.update_data(media_id=file_id, media_type="photo")
    # Next: format
    await state.set_state(CreatePost.format)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            ["Markdown", "HTML", "Без форматирования"]
        ],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    await message.answer("Шаг 3/7: Выберите тип форматирования (Markdown, HTML или Без форматирования).", reply_markup=keyboard)

@router.message(F.video, CreatePost.media)
async def receive_video(message: Message, state: FSMContext):
    # User sent a video
    video = message.video
    file_id = video.file_id
    await state.update_data(media_id=file_id, media_type="video")
    # Next: format
    await state.set_state(CreatePost.format)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            ["Markdown", "HTML", "Без форматирования"]
        ],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    await message.answer("Шаг 3/7: Выберите тип форматирования (Markdown, HTML или Без форматирования).", reply_markup=keyboard)

@router.message(CreatePost.media)
async def wrong_media_type(message: Message):
    # If user sends something other than photo/video or skip
    await message.answer("Пожалуйста, отправьте фото или видео, либо используйте /skip для пропуска.")

@router.message(CreatePost.format)
async def step_format(message: Message, state: FSMContext):
    fmt = message.text.strip().lower()
    parse_mode = None
    if fmt in ("markdown", "html"):
        parse_mode = fmt
    elif fmt.startswith("без") or fmt == "none" or fmt == "no":
        parse_mode = "none"
    elif fmt.startswith("/skip"):
        # Treat skip as no format
        parse_mode = "none"
    else:
        # Unrecognized input, ask again
        await message.answer("Выберите формат: Markdown, HTML или Без форматирования (введите именно так).")
        return
    # Save format choice
    await state.update_data(format=parse_mode)
    # Remove the selection keyboard
    await message.answer(f"Форматирование: {('без форматирования' if parse_mode == 'none' else parse_mode)}", reply_markup=ReplyKeyboardRemove())
    # Next: inline buttons
    await state.set_state(CreatePost.buttons)
    await message.answer("Шаг 4/7: Отправьте inline-кнопки для поста.\nФормат: одна кнопка на строку в виде 'Текст кнопки | URL'.\nЕсли кнопок нет, введите /skip.")

@router.message(Command("skip"), CreatePost.buttons)
async def skip_buttons(message: Message, state: FSMContext):
    await state.update_data(buttons=[])
    # Next: publish time
    await state.set_state(CreatePost.time)
    await message.answer("Шаг 5/7: Укажите дату и время публикации в формате YYYY-MM-DD HH:MM (24ч).")

@router.message(CreatePost.buttons)
async def receive_buttons(message: Message, state: FSMContext):
    text = message.text
    text = text.strip()
    if text.lower() in ("none", "нет"):
        # interpret "none" as no buttons
        await state.update_data(buttons=[])
    else:
        lines = text.splitlines()
        buttons = []
        for line in lines:
            parts = line.split("|", maxsplit=1)
            if len(parts) == 2:
                btn_text = parts[0].strip()
                btn_url = parts[1].strip()
                if btn_text and btn_url:
                    buttons.append({"text": btn_text, "url": btn_url})
        await state.update_data(buttons=buttons)
    # Next: time
    await state.set_state(CreatePost.time)
    await message.answer("Шаг 5/7: Укажите дату и время публикации в формате YYYY-MM-DD HH:MM (24ч).")

@router.message(CreatePost.time)
async def step_time(message: Message, state: FSMContext):
    time_str = message.text.strip()
    # Parse datetime
    try:
        publish_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    except Exception:
        await message.answer("Некорректный формат даты/времени. Пожалуйста, введите в формате YYYY-MM-DD HH:MM.")
        return
    # If parsed successfully
    await state.update_data(publish_time=publish_time)
    # Next: channel selection
    await state.set_state(CreatePost.channel)
    # Show available channels for selection
    channels = supabase_db.db.list_channels()
    # Build inline keyboard with channels
    buttons = []
    for ch in channels:
        cid = ch.get("chat_id")
        name = ch.get("name") or str(cid)
        # Use chat_id as callback data
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"ch_select:{cid}")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Шаг 6/7: Выберите канал для публикации:", reply_markup=markup)

@router.callback_query(CreatePost.channel)
async def channel_selected(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data
    if data and data.startswith("ch_select:"):
        cid_str = data.split(":", 1)[1]
        try:
            chat_id = int(cid_str)
        except:
            chat_id = cid_str  # if for some reason it's not numeric (should be numeric though)
        # Find channel internal ID as well
        channels = supabase_db.db.list_channels()
        channel_id = None
        channel_name = str(chat_id)
        for ch in channels:
            if ch.get("chat_id") == chat_id:
                channel_id = ch.get("id")
                channel_name = ch.get("name") or channel_name
                break
        # Save chosen channel
        # We store both the actual chat_id and the channel table id for reference
        await state.update_data(channel_chat_id=chat_id, channel_db_id=channel_id, channel_name=channel_name)
        # Move to confirmation
        await state.set_state(CreatePost.confirm)
        # Send a preview of the post
        data = await state.get_data()
        text = data.get("text", "")
        media_id = data.get("media_id")
        media_type = data.get("media_type")
        fmt = data.get("format")
        # Determine parse_mode from fmt
        parse_mode = None
        if fmt and fmt.lower() == "markdown":
            parse_mode = "Markdown"
        elif fmt and fmt.lower() == "html":
            parse_mode = "HTML"
        # Build inline keyboard for preview (if any)
        markup = None
        buttons = data.get("buttons", [])
        if buttons:
            kb = []
            for btn in buttons:
                btn_text = btn.get("text")
                btn_url = btn.get("url")
                if btn_text and btn_url:
                    kb.append([InlineKeyboardButton(text=btn_text, url=btn_url)])
            if kb:
                markup = InlineKeyboardMarkup(inline_keyboard=kb)
        # Send preview to user
        try:
            if media_id and media_type:
                if media_type == "photo":
                    await callback.message.answer_photo(photo=media_id, caption=text or "", parse_mode=parse_mode, reply_markup=markup)
                elif media_type == "video":
                    await callback.message.answer_video(video=media_id, caption=text or "", parse_mode=parse_mode, reply_markup=markup)
                else:
                    await callback.message.answer(text or "(без текста)", parse_mode=parse_mode, reply_markup=markup)
            else:
                await callback.message.answer(text or "(без текста)", parse_mode=parse_mode, reply_markup=markup)
        except Exception as e:
            await callback.message.answer(f"Не удалось создать предпросмотр сообщения: {e}")
        # Ask for confirmation
        confirm_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
             InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")]
        ])
        await callback.message.answer(f"Шаг 7/7: Подтвердите публикацию поста в канале \"{channel_name}\" в {data.get('publish_time')}.", reply_markup=confirm_markup)
        await callback.answer()
    else:
        await callback.answer()

@router.callback_query(F.data == "confirm", CreatePost.confirm)
async def confirm_post(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    # Double-check: ensure post not already published or scheduled in past
    publish_time = data.get("publish_time")
    if publish_time and isinstance(publish_time, datetime):
        now = datetime.utcnow()
        if publish_time <= now:
            # If the scheduled time is in the past or now, we can still schedule (it will post almost immediately)
            pass
    # Prepare post data for DB
    post_data = {
        "channel_id": data.get("channel_db_id"),        # reference to channels table
        "chat_id": data.get("channel_chat_id"),         # actual Telegram chat id
        "text": data.get("text", ""),
        "media_id": data.get("media_id"),
        "media_type": data.get("media_type"),
        "format": data.get("format", "none"),
        "buttons": data.get("buttons", []),
        "publish_time": data.get("publish_time").strftime("%Y-%m-%dT%H:%M:%S"),
        "published": False
    }
    # Insert into database
    inserted = supabase_db.db.add_post(post_data)
    if inserted:
        post_id = inserted.get("id")
        await callback.message.answer(f"Пост #{post_id} запланирован на публикацию.")
    else:
        await callback.message.answer("Ошибка при сохранении поста в базе данных.")
    # End FSM
    await state.clear()
    # Acknowledge callback and edit the confirmation message to avoid duplicate actions
    await callback.answer("Пост запланирован!")
    try:
        await callback.message.edit_text("Пост успешно запланирован ✅")
    except:
        pass

@router.callback_query(F.data == "cancel", CreatePost.confirm)
async def cancel_post(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Создание поста отменено.")
    await state.clear()
    await callback.answer("Отменено")
    try:
        await callback.message.edit_text("Создание поста отменено ❌")
    except:
        pass
