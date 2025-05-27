# scheduler/auto_post.py
import asyncio
from datetime import datetime
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from storage import supabase_db

async def start_scheduler(bot: Bot, check_interval: int = 5):
    """Background task to publish scheduled posts at the specified time."""
    while True:
        now = datetime.utcnow()
        due_posts = supabase_db.db.get_due_posts(now)
        for post in due_posts:
            chat_id = None
            # Determine channel chat_id: it might be stored as channel internal id or chat_id
            if "chat_id" in post:
                # If posts table has a chat_id field (if storing TG id directly)
                chat_id = post["chat_id"]
            else:
                # Otherwise, posts.channel_id might be foreign key to channels table
                # Look up the channel's chat_id
                chan_id = post.get("channel_id")
                if chan_id:
                    channel = None
                    # Try to get channel by internal id
                    channels = supabase_db.db.list_channels()
                    for ch in channels:
                        if ch.get("id") == chan_id:
                            channel = ch
                            break
                    if channel:
                        chat_id = channel.get("chat_id")
            if not chat_id:
                # Skip if no channel found
                supabase_db.db.mark_post_published(post["id"])
                continue
            text = post.get("text") or ""
            media_id = post.get("media_id")
            media_type = post.get("media_type")
            fmt = post.get("format")
            buttons = []
            markup = None
            # Parse buttons JSON if present
            if post.get("buttons"):
                try:
                    buttons = supabase_db.json.loads(post["buttons"])
                except Exception:
                    buttons = json.loads(post["buttons"]) if isinstance(post["buttons"], str) else post["buttons"]
            if buttons:
                kb = []
                for btn in buttons:
                    if isinstance(btn, dict):
                        btn_text = btn.get("text")
                        btn_url = btn.get("url")
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
            if fmt:
                fmt_low = fmt.lower()
                if fmt_low == "markdown":
                    parse_mode = "Markdown"
                elif fmt_low == "html":
                    parse_mode = "HTML"
            # Send the message to the channel
            try:
                if media_id and media_type:
                    if media_type.lower() == "photo":
                        await bot.send_photo(chat_id, photo=media_id, caption=text, parse_mode=parse_mode, reply_markup=markup)
                    elif media_type.lower() == "video":
                        await bot.send_video(chat_id, video=media_id, caption=text, parse_mode=parse_mode, reply_markup=markup)
                    else:
                        # If other media types needed, handle accordingly (audio, document, etc.)
                        await bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=markup)
                else:
                    # No media, just text
                    await bot.send_message(chat_id, text or "(no text)", parse_mode=parse_mode, reply_markup=markup)
            except Exception as e:
                # Could not send (maybe bot removed or no permission), handle error if needed
                print(f"Failed to send post {post['id']} to channel {chat_id}: {e}")
            # Mark as published in all cases to prevent re-trying
            supabase_db.db.mark_post_published(post["id"])
        # Wait before next check
        await asyncio.sleep(check_interval)
