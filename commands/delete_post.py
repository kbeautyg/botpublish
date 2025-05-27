# commands/delete_post.py
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from storage import supabase_db

router = Router()

@router.message(Command("delete"))
async def cmd_delete(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /delete <ID поста>")
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
        await message.answer("Этот пост уже был опубликован, его нельзя удалить.")
        return
    # Delete post
    supabase_db.db.delete_post(post_id)
    await message.answer(f"Пост #{post_id} удалён.")
