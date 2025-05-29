from aiogram import Router, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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
    # Determine current project
    project_id = user.get("current_project") if user else None

    # If just /channels, list channels in current project
    if len(args) == 1:
        if not project_id:
            await message.answer(TEXTS[lang]['channels_no_channels'])
            return
        channels = supabase_db.db.list_channels(project_id=project_id)
        if not channels:
            await message.answer(TEXTS[lang]['channels_no_channels'])
            return
        # List each channel with a remove button
        await message.answer(TEXTS[lang]['channels_list_title'])
        for ch in channels:
            cid = ch["chat_id"]
            title = ch.get("name") or str(cid)
            text = TEXTS[lang]['channels_item'].format(name=title, id=cid)
            # Inline keyboard with Remove button
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗑️ Remove", callback_data=f"remove_channel:{ch['id']}")]
            ])
            await message.answer(text, reply_markup=kb)
        return

    sub = args[1].lower()
    if sub == "add":
        if len(args) < 3:
            await message.answer(TEXTS[lang]['channels_add_usage'])
            return
        if not project_id:
            await message.answer(TEXTS[lang]['channels_add_error'].format(error="No active project"))
            return
        ident = args[2]
        try:
            chat = await bot.get_chat(ident)
            # Verify that user is admin in the channel
            member = await bot.get_chat_member(chat.id, user_id)
            if member.status not in ("administrator", "creator"):
                await message.answer("❌ Вы должны быть администратором канала." if lang == "ru" else "❌ You must be an administrator of that channel.")
                return
            # Verify bot is an admin in the channel
            bot_member = await bot.get_chat_member(chat.id, (await bot.get_me()).id)
            if bot_member.status not in ("administrator", "creator"):
                await message.answer("❌ Бот не является администратором этого канала." if lang == "ru" else "❌ The bot is not an admin in that channel.")
                return
            supabase_db.db.add_channel(user_id, chat.id, chat.title or chat.username or str(chat.id), project_id)
            await message.answer(TEXTS[lang]['channels_added'].format(name=chat.title or chat.username or chat.id))
        except Exception as e:
            await message.answer(TEXTS[lang]['channels_add_error'].format(error=e))
    elif sub in ("remove", "delete"):
        if len(args) < 3:
            await message.answer(TEXTS[lang]['channels_remove_usage'])
            return
        if not project_id:
            await message.answer(TEXTS[lang]['channels_not_found'])
            return
        identifier = args[2]
        # Find channel for confirmation prompt
        chan = None
        if identifier.isdigit():
            # Try by chat_id or internal ID
            chan_list = supabase_db.db.list_channels(project_id=project_id)
            for ch in chan_list:
                if ch.get("chat_id") == int(identifier) or ch.get("id") == int(identifier):
                    chan = ch
                    break
        # If channel not found in this project
        if not chan:
            await message.answer(TEXTS[lang]['channels_not_found'])
            return
        title = chan.get("name") or str(chan.get("chat_id"))
        # Ask for confirmation via inline buttons
        confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=TEXTS[lang]['yes_btn'], callback_data=f"confirm_remove_channel:{chan['id']}"),
                InlineKeyboardButton(text=TEXTS[lang]['no_btn'], callback_data=f"cancel_remove_channel_text:{chan['id']}")
            ]
        ])
        await message.answer(TEXTS[lang]['channels_remove_confirm'].format(name=title), reply_markup=confirm_kb)
    else:
        await message.answer(TEXTS[lang]['channels_unknown_command'])

@router.callback_query(lambda c: c.data and c.data.startswith("remove_channel:"))
async def on_remove_channel_button(callback: CallbackQuery):
    user_id = callback.from_user.id
    # Extract channel id from callback data
    try:
        chan_id = int(callback.data.split(":", 1)[1])
    except:
        await callback.answer()  # no action
        return
    user = supabase_db.db.get_user(user_id)
    lang = user.get("language", "ru") if user else "ru"
    channel = supabase_db.db.get_channel(chan_id)
    if not channel or not user or not supabase_db.db.is_user_in_project(user_id, channel.get("project_id")):
        await callback.answer(TEXTS[lang]['channels_not_found'], show_alert=True)
        return
    title = channel.get("name") or str(channel.get("chat_id"))
    # Edit the channel message to confirmation question
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=TEXTS[lang]['yes_btn'], callback_data=f"confirm_remove_channel:{chan_id}"),
            InlineKeyboardButton(text=TEXTS[lang]['no_btn'], callback_data=f"cancel_remove_channel:{chan_id}")
        ]
    ])
    try:
        await callback.message.edit_text(TEXTS[lang]['channels_remove_confirm'].format(name=title), reply_markup=kb)
    except:
        pass
    await callback.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("confirm_remove_channel:"))
async def on_confirm_remove_channel(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        chan_id = int(callback.data.split(":", 1)[1])
    except:
        await callback.answer()
        return
    user = supabase_db.db.get_user(user_id)
    lang = user.get("language", "ru") if user else "ru"
    channel = supabase_db.db.get_channel(chan_id)
    project_id = channel.get("project_id") if channel else None
    success = False
    if project_id and user and supabase_db.db.is_user_in_project(user_id, project_id):
        # Remove channel from project
        success = supabase_db.db.remove_channel(project_id, str(chan_id))
    # Edit message to indicate result
    if success:
        await callback.message.edit_text(TEXTS[lang]['channels_removed'])
    else:
        await callback.message.edit_text(TEXTS[lang]['channels_not_found'])
    await callback.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("cancel_remove_channel:"))
async def on_cancel_remove_channel(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        chan_id = int(callback.data.split(":", 1)[1])
    except:
        await callback.answer()
        return
    user = supabase_db.db.get_user(user_id)
    lang = user.get("language", "ru") if user else "ru"
    channel = supabase_db.db.get_channel(chan_id)
    if channel:
        # Restore original channel listing text with Remove button
        cid = channel.get("chat_id")
        title = channel.get("name") or str(cid)
        text = TEXTS[lang]['channels_item'].format(name=title, id=cid)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑️ Remove", callback_data=f"remove_channel:{channel['id']}")]
        ])
        await callback.message.edit_text(text, reply_markup=kb)
    else:
        # If channel not found, just indicate cancellation
        await callback.message.edit_text(TEXTS[lang]['confirm_post_cancel'])
    await callback.answer(TEXTS[lang]['confirm_post_cancel'])
