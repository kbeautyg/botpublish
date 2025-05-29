import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not BOT_TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing BOT_TOKEN or SUPABASE_URL or SUPABASE_KEY in environment")

# Initialize Supabase database interface
from storage import supabase_db
supabase_db.db = supabase_db.SupabaseDB(SUPABASE_URL, SUPABASE_KEY)
supabase_db.db.init_schema()

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN, parse_mode=None)
dp = Dispatcher(storage=MemoryStorage())

# Include routers from command modules
from commands import start, help, channels, create_post, edit_post, list_posts, delete_post, settings, projects
dp.include_router(start.router)
dp.include_router(help.router)
dp.include_router(channels.router)
dp.include_router(create_post.router)
dp.include_router(edit_post.router)
dp.include_router(list_posts.router)
dp.include_router(delete_post.router)
dp.include_router(settings.router)
dp.include_router(projects.router)

# Import and start the scheduler
from scheduler import auto_post

async def main():
    # Start background task for auto-posting
    asyncio.create_task(auto_post.start_scheduler(bot))
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
