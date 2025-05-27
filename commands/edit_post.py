# commands/edit_post.py
from aiogram import Router, types, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from datetime import datetime
from states import EditPost
from storage import supabase_db
from aiogram import Bot

router = Router()

@router.message(Command("edit"))
async def cmd_edit(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /edit <ID поста>")
        return
    try:
        post_id = int(args[1])
    except:
        await message.answer("Некорректный ID поста.")
        return
    post = supabase_db.db.get_post(post_id)
    if not post:
        await message.answer("Пост с таким ID не найден.")
        return
    if post.get("published"):
        await message.answer("Этот пост уже опубликован, редактирование невозможно.")
        return
    # Save original post data in state
    await state.update_data(orig_post=post)
    # Start edit FSM
    await state.set_state(EditPost.text)
    current_text = post.get("text") or ""
    await message.answer(
        f"Редактирование поста #{post_id}.\nТекущий текст: \"{current_text}\"\nОтправьте новый текст или /skip, чтобы оставить без изменений."
    )

@router.message(EditPost.text)
async def edit_step_text(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    if message.text and message.text.startswith("/skip"):
        # keep original text
        new_text = orig_post.get("text", "")
    else:
        new_text = message.text or ""
    await state.update_data(new_text=new_text)
    # Next: media
    await state.set_state(EditPost.media)
    # If original had media, mention it
    if orig_post.get("media_id"):
        media_info = "фото" if orig_post.get("media_type") == "photo" else "видео" if orig_post.get("media_type") == "video" else "медиа"
        await message.answer(f"Текущее медиа: {media_info} прикреплено. Отправьте новое фото/видео, чтобы заменить, или /skip, чтобы оставить прежнее, или введите 'none' для удаления медиа.")
    else:
        await message.answer("Для поста нет медиа. Отправьте фото/видео, чтобы добавить, или /skip, чтобы продолжить без медиа.")

@router.message(Command("skip"), EditPost.media)
async def skip_edit_media(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    # keep original media
    new_media_id = orig_post.get("media_id")
    new_media_type = orig_post.get("media_type")
    await state.update_data(new_media_id=new_media_id, new_media_type=new_media_type)
    # Next: format
    await state.set_state(EditPost.format)
    current_fmt = orig_post.get("format") or "none"
    await message.answer(
        f"Текущий формат: {current_fmt}. Отправьте 'Markdown', 'HTML' или 'None' для изменения, или /skip для сохранения текущего."
    )

@router.message(EditPost.media, F.photo)
async def edit_receive_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file_id = photo.file_id
    await state.update_data(new_media_id=file_id, new_media_type="photo")
    # Next: format
    await state.set_state(EditPost.format)
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    current_fmt = orig_post.get("format") or "none"
    await message.answer(
        f"Медиа обновлено (фото). Текущий формат: {current_fmt}. Отправьте 'Markdown', 'HTML' или 'None' для изменения, или /skip для сохранения текущего."
    )

@router.message(EditPost.media, F.video)
async def edit_receive_video(message: Message, state: FSMContext):
    video = message.video
    file_id = video.file_id
    await state.update_data(new_media_id=file_id, new_media_type="video")
    # Next: format
    await state.set_state(EditPost.format)
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    current_fmt = orig_post.get("format") or "none"
    await message.answer(
        f"Медиа обновлено (видео). Текущий формат: {current_fmt}. Отправьте 'Markdown', 'HTML' или 'None' для изменения, или /skip для сохранения текущего."
    )

@router.message(EditPost.media)
async def edit_media_text(message: Message, state: FSMContext):
    # If user sent text when media expected
    text = message.text.strip().lower()
    if text in ("none", "нет"):
        # user wants to remove existing media
        await state.update_data(new_media_id=None, new_media_type=None)
        await state.set_state(EditPost.format)
        data = await state.get_data()
        orig_post = data.get("orig_post", {})
        current_fmt = orig_post.get("format") or "none"
        await message.answer(
            f"Медиа будет удалено. Текущий формат: {current_fmt}. Отправьте 'Markdown', 'HTML' или 'None' для изменения, или /skip для сохранения текущего."
        )
    else:
        await message.answer("Пожалуйста, отправьте фото/видео или /skip (или 'none' для удаления медиа).")

@router.message(Command("skip"), EditPost.format)
async def skip_edit_format(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    new_format = orig_post.get("format") or "none"
    await state.update_data(new_format=new_format)
    # Next: buttons
    await state.set_state(EditPost.buttons)
    # Describe current buttons
    buttons = orig_post.get("buttons")
    if buttons:
        try:
            buttons_list = supabase_db.json.loads(buttons) if isinstance(buttons, str) else buttons
        except Exception:
            buttons_list = buttons
        btn_desc = []
        for btn in buttons_list:
            if isinstance(btn, dict):
                btn_desc.append(f"{btn.get('text')} -> {btn.get('url')}")
        current_buttons_text = "\n".join(btn_desc) if btn_desc else "нет"
    else:
        current_buttons_text = "нет"
    await message.answer(
        f"Текущие кнопки:\n{current_buttons_text}\nОтправьте новые кнопки (формат 'Текст | URL' на строку) для замены, или /skip для сохранения текущих, или 'none' для удаления всех кнопок."
    )

@router.message(EditPost.format)
async def edit_step_format(message: Message, state: FSMContext):
    fmt = message.text.strip().lower()
    new_format = None
    if fmt in ("markdown", "html"):
        new_format = fmt
    elif fmt in ("none", "без форматирования", "no"):
        new_format = "none"
    elif fmt.startswith("/skip"):
        # user perhaps typed skip incorrectly here, handle separately
        # In case skip wasn't caught by above filter (should have been)
        orig_post = (await state.get_data()).get("orig_post", {})
        new_format = orig_post.get("format") or "none"
    else:
        await message.answer("Введите 'Markdown', 'HTML' или 'None', или /skip для сохранения текущего формата.")
        return
    await state.update_data(new_format=new_format)
    # Next: buttons
    await state.set_state(EditPost.buttons)
    orig_post = (await state.get_data()).get("orig_post", {})
    buttons = orig_post.get("buttons")
    if buttons:
        try:
            buttons_list = supabase_db.json.loads(buttons) if isinstance(buttons, str) else buttons
        except Exception:
            buttons_list = buttons
        btn_desc = []
        for btn in buttons_list:
            if isinstance(btn, dict):
                btn_desc.append(f"{btn.get('text')} -> {btn.get('url')}")
        current_buttons_text = "\n".join(btn_desc) if btn_desc else "нет"
    else:
        current_buttons_text = "нет"
    await message.answer(
        f"Текущие кнопки:\n{current_buttons_text}\nОтправьте новые кнопки ('Текст | URL' на строку) для замены, или /skip для сохранения текущих, или 'none' для удаления всех."
    )

@router.message(Command("skip"), EditPost.buttons)
async def skip_edit_buttons(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    # keep original buttons (store in new_buttons same as original)
    new_buttons = orig_post.get("buttons")
    # It's possibly a JSON string, just keep it as is in state for later update
    await state.update_data(new_buttons=new_buttons)
    # Next: time
    await state.set_state(EditPost.time)
    current_time = orig_post.get("publish_time")
    await message.answer(f"Текущее время публикации: {current_time}\nВведите новую дату/время в формате YYYY-MM-DD HH:MM, или /skip чтобы оставить без изменений.")

@router.message(EditPost.buttons)
async def edit_step_buttons(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    new_buttons = None
    if text.lower() in ("none", "нет"):
        # remove all buttons
        new_buttons = []
    else:
        if text.startswith("/skip"):
            # if somehow skip not caught by filter, treat as keep
            new_buttons = orig_post.get("buttons")
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
            new_buttons = buttons
    await state.update_data(new_buttons=new_buttons)
    # Next: time
    await state.set_state(EditPost.time)
    current_time = orig_post.get("publish_time")
    await message.answer(f"Текущее время публикации: {current_time}\nВведите новую дату/время в формате YYYY-MM-DD HH:MM, или /skip чтобы оставить прежнее.")

@router.message(Command("skip"), EditPost.time)
async def skip_edit_time(message: Message, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    new_time = orig_post.get("publish_time")
    await state.update_data(new_publish_time=new_time)
    # Next: channel selection
    await state.set_state(EditPost.channel)
    current_channel_id = orig_post.get("channel_id")
    current_channel = None
    channels = supabase_db.db.list_channels()
    for ch in channels:
        if ch.get("id") == current_channel_id or ch.get("chat_id") == orig_post.get("chat_id"):
            current_channel = ch
            break
    current_channel_name = current_channel.get("name") if current_channel else "неизвестен"
    await message.answer(
        f"Текущий канал: {current_channel_name}\nВыберите новый канал, или /skip чтобы оставить без изменений.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            *[[InlineKeyboardButton(text=ch.get('name') or str(ch.get('chat_id')), callback_data=f'ch_edit:{ch.get("chat_id")}')] for ch in channels],
            [InlineKeyboardButton(text="Оставить текущий", callback_data="ch_edit_skip")]
        ])
    )

@router.message(EditPost.time)
async def edit_step_time(message: Message, state: FSMContext):
    time_str = message.text.strip()
    try:
        new_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    except Exception:
        await message.answer("Неверный формат даты/времени. Введите в формате YYYY-MM-DD HH:MM или /skip.")
        return
    await state.update_data(new_publish_time=new_time)
    # Next: channel
    await state.set_state(EditPost.channel)
    # Show channels list for selection
    channels = supabase_db.db.list_channels()
    buttons = [[InlineKeyboardButton(text=ch.get("name") or str(ch.get("chat_id")), callback_data=f"ch_edit:{ch.get('chat_id')}")] for ch in channels]
    buttons.append([InlineKeyboardButton(text="Оставить текущий", callback_data="ch_edit_skip")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выберите новый канал для поста (или нажмите 'Оставить текущий'):", reply_markup=markup)

@router.callback_query(EditPost.channel)
async def edit_channel_select(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data
    if data == "ch_edit_skip":
        # keep original channel
        orig_post = (await state.get_data()).get("orig_post", {})
        new_channel_id = orig_post.get("channel_id")
        new_chat_id = orig_post.get("chat_id") if orig_post.get("chat_id") else None
        new_channel_name = None
        channels = supabase_db.db.list_channels()
        for ch in channels:
            if ch.get("id") == new_channel_id or ch.get("chat_id") == new_chat_id:
                new_channel_name = ch.get("name") or str(ch.get("chat_id"))
                break
        await state.update_data(new_channel_db_id=new_channel_id, new_channel_chat_id=new_chat_id, new_channel_name=new_channel_name)
    elif data and data.startswith("ch_edit:"):
        cid_str = data.split(":", 1)[1]
        try:
            chat_id = int(cid_str)
        except:
            chat_id = cid_str
        channels = supabase_db.db.list_channels()
        channel_id = None
        channel_name = str(chat_id)
        for ch in channels:
            if ch.get("chat_id") == chat_id:
                channel_id = ch.get("id")
                channel_name = ch.get("name") or channel_name
                break
        await state.update_data(new_channel_db_id=channel_id, new_channel_chat_id=chat_id, new_channel_name=channel_name)
    else:
        await callback.answer()
        return
    # Move to confirm
    await state.set_state(EditPost.confirm)
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    # Prepare preview with updated fields
    text = data.get("new_text", orig_post.get("text", "")) or ""
    media_id = data.get("new_media_id", orig_post.get("media_id"))
    media_type = data.get("new_media_type", orig_post.get("media_type"))
    fmt = data.get("new_format", orig_post.get("format") or "none")
    buttons = data.get("new_buttons", orig_post.get("buttons"))
    # If buttons is a JSON string in orig and we didn't change it, parse it for preview
    btn_list = []
    if isinstance(buttons, str):
        try:
            btn_list = supabase_db.json.loads(buttons)
        except Exception:
            btn_list = json.loads(buttons) if buttons else []
    elif isinstance(buttons, list):
        btn_list = buttons
    # Create markup for preview
    markup = None
    if btn_list:
        kb = []
        for btn in btn_list:
            if isinstance(btn, dict):
                btn_text = btn.get("text"); btn_url = btn.get("url")
            elif isinstance(btn, list) or isinstance(btn, tuple):
                if len(btn) >= 2:
                    btn_text = btn[0]; btn_url = btn[1]
                else:
                    continue
            else:
                continue
            if btn_text and btn_url:
                kb.append([InlineKeyboardButton(text=btn_text, url=btn_url)])
        if kb:
            markup = InlineKeyboardMarkup(inline_keyboard=kb)
    # Determine parse_mode
    parse_mode = None
    if fmt and fmt.lower() == "markdown":
        parse_mode = "Markdown"
    elif fmt and fmt.lower() == "html":
        parse_mode = "HTML"
    # Send preview
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
        await callback.message.answer(f"Предпросмотр сообщения недоступен: {e}")
    # Ask for confirmation
    confirm_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Сохранить изменения", callback_data="edit_confirm"),
         InlineKeyboardButton(text="❌ Отменить", callback_data="edit_cancel")]
    ])
    await callback.message.answer("Подтвердите изменение поста.", reply_markup=confirm_markup)
    await callback.answer()

@router.callback_query(F.data == "edit_confirm", EditPost.confirm)
async def confirm_edit(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    orig_post = data.get("orig_post", {})
    post_id = orig_post.get("id")
    # If the post got published during editing, abort
    latest = supabase_db.db.get_post(post_id)
    if latest and latest.get("published"):
        await callback.message.answer("Пост уже был опубликован до завершения редактирования. Изменения не применены.")
        await state.clear()
        await callback.answer()
        return
    updates = {}
    # Determine changes
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
        # If datetime object, format to string
        pub_time = data["new_publish_time"]
        if isinstance(pub_time, datetime):
            updates["publish_time"] = pub_time.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            updates["publish_time"] = pub_time
    if "new_channel_db_id" in data:
        updates["channel_id"] = data["new_channel_db_id"]
    if "new_channel_chat_id" in data:
        updates["chat_id"] = data["new_channel_chat_id"]
    # Apply updates in DB
    supabase_db.db.update_post(post_id, updates)
    await callback.message.answer(f"Изменения сохранены для поста #{post_id}.")
    await state.clear()
    await callback.answer("Обновлено")
    try:
        await callback.message.edit_text("Пост отредактирован ✅")
    except:
        pass

@router.callback_query(F.data == "edit_cancel", EditPost.confirm)
async def cancel_edit(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Редактирование поста отменено.")
    await state.clear()
    await callback.answer("Отменено")
    try:
        await callback.message.edit_text("Редактирование отменено ❌")
    except:
        pass
