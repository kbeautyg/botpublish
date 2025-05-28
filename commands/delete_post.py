# commands/delete_post.py
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from storage import supabase_db
from commands import TEXTS

router = Router()

@router.message(Command("delete"))
async def cmd_delete(message: Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    lang = "ru"
    user = supabase_db.db.get_user(user_id)
    if user:
        lang = user.get("language", "ru")
    if len(args) < 2:
        await message.answer(TEXTS[lang]['delete_usage'])
        return
    try:
        post_id = int(args[1])
    except:
        await message.answer(TEXTS[lang]['delete_invalid_id'])
        return
    post = supabase_db.db.get_post(post_id)
    if not post or post.get("user_id") != user_id:
        await message.answer(TEXTS[lang]['delete_not_found'])
        return
    if post.get("published"):
        await message.answer(TEXTS[lang]['delete_already_published'])
        return
    supabase_db.db.delete_post(post_id)
    await message.answer(TEXTS[lang]['delete_success'].format(id=post_id))
