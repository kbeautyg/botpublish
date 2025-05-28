# storage/supabase_db.py
import json
from supabase import create_client, Client

# Global database instance (to be set in main)
db = None

class SupabaseDB:
    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)
    
    def init_schema(self):
        """Ensure the necessary tables exist (or create them if possible)."""
        try:
            # Check if tables exist by querying a small portion
            self.client.table("channels").select("id").limit(1).execute()
            self.client.table("posts").select("id").limit(1).execute()
            self.client.table("users").select("user_id").limit(1).execute()
        except Exception:
            # Attempt to create missing tables and columns via SQL (if allowed)
            try:
                schema_sql = """
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    timezone TEXT DEFAULT 'UTC',
                    language TEXT DEFAULT 'ru',
                    date_format TEXT DEFAULT 'YYYY-MM-DD',
                    time_format TEXT DEFAULT 'HH:MM',
                    notify_before INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS channels (
                    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    user_id BIGINT,
                    name TEXT,
                    chat_id BIGINT NOT NULL,
                    UNIQUE(user_id, chat_id)
                );
                CREATE TABLE IF NOT EXISTS posts (
                    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    user_id BIGINT,
                    channel_id BIGINT,
                    chat_id BIGINT,
                    text TEXT,
                    media_id TEXT,
                    media_type TEXT,
                    format TEXT,
                    buttons TEXT,
                    publish_time TIMESTAMP WITH TIME ZONE,
                    repeat_interval BIGINT DEFAULT 0,
                    draft BOOLEAN DEFAULT FALSE,
                    published BOOLEAN DEFAULT FALSE,
                    notified BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (channel_id) REFERENCES channels(id)
                );
                """
                self.client.postgrest.rpc("sql", {"sql": schema_sql}).execute()
            except Exception:
                # If unable to create via API (e.g., lacking permissions)
                pass

    # User management
    def get_user(self, user_id: int):
        """Retrieve user settings by Telegram user_id."""
        res = self.client.table("users").select("*").eq("user_id", user_id).execute()
        data = res.data or []
        return data[0] if data else None

    def ensure_user(self, user_id: int, default_lang: str = None):
        """Ensure a user exists in the users table. Creates with defaults if not present."""
        user = self.get_user(user_id)
        if user:
            return user
        lang = default_lang or 'ru'
        new_user = {
            "user_id": user_id,
            "timezone": "UTC",
            "language": lang,
            "date_format": "YYYY-MM-DD",
            "time_format": "HH:MM",
            "notify_before": 0
        }
        res = self.client.table("users").insert(new_user).execute()
        return res.data[0] if res.data else None

    def update_user(self, user_id: int, updates: dict):
        """Update user settings and return the updated record."""
        if not updates:
            return None
        res = self.client.table("users").update(updates).eq("user_id", user_id).execute()
        return res.data[0] if res.data else None

    # Channel management
    def add_channel(self, user_id: int, chat_id: int, name: str):
        """Add a new channel for the user or update its name if it exists."""
        res = self.client.table("channels").select("*").eq("user_id", user_id).eq("chat_id", chat_id).execute()
        if res.data:
            # Update name if channel exists for user
            self.client.table("channels").update({"name": name}).eq("user_id", user_id).eq("chat_id", chat_id).execute()
            return res.data[0]
        data = {"user_id": user_id, "name": name, "chat_id": chat_id}
        res = self.client.table("channels").insert(data).execute()
        return res.data[0] if res.data else None

    def list_channels(self, user_id: int = None):
        """List all channels, optionally filtered by user."""
        query = self.client.table("channels").select("*")
        if user_id is not None:
            query = query.eq("user_id", user_id)
        res = query.execute()
        return res.data or []

    def remove_channel(self, user_id: int, identifier: str):
        """Remove a channel by chat_id or internal id for the given user."""
        channel_to_delete = None
        if identifier.startswith("@"):
            return False  # Removing by username not supported
        try:
            cid = int(identifier)
            # Try as chat_id
            res = self.client.table("channels").select("*").eq("user_id", user_id).eq("chat_id", cid).execute()
            if res.data:
                channel_to_delete = res.data[0]
            else:
                # Try as internal id
                res = self.client.table("channels").select("*").eq("user_id", user_id).eq("id", cid).execute()
                if res.data:
                    channel_to_delete = res.data[0]
        except ValueError:
            return False
        if not channel_to_delete:
            return False
        chan_id = channel_to_delete.get("id")
        # Delete channel and any related posts
        self.client.table("channels").delete().eq("id", chan_id).execute()
        self.client.table("posts").delete().eq("channel_id", chan_id).execute()
        return True

    # Post management
    def add_post(self, post_data: dict):
        """Insert a new post into the database. Returns the inserted record."""
        if "buttons" in post_data and isinstance(post_data["buttons"], list):
            post_data["buttons"] = json.dumps(post_data["buttons"])
        res = self.client.table("posts").insert(post_data).execute()
        return res.data[0] if res.data else None

    def get_post(self, post_id: int):
        """Retrieve a single post by id."""
        res = self.client.table("posts").select("*").eq("id", post_id).execute()
        data = res.data or []
        return data[0] if data else None

    def list_posts(self, user_id: int = None, only_pending: bool = True):
        """List posts, optionally filtered by user and published status."""
        query = self.client.table("posts").select("*")
        if only_pending:
            query = query.eq("published", False)
        if user_id is not None:
            query = query.eq("user_id", user_id)
        # supabase-py ≥ 2.x ⇒ .order(..., desc=bool), «asc» нет
        query = query.order("publish_time", desc=False)   #  ← was asc=True
        res = query.execute()
        return res.data or []

    def update_post(self, post_id: int, updates: dict):
        """Update fields of a post and return the updated record."""
        if "buttons" in updates and isinstance(updates["buttons"], list):
            updates["buttons"] = json.dumps(updates["buttons"])
        res = self.client.table("posts").update(updates).eq("id", post_id).execute()
        return res.data[0] if res.data else None

    def delete_post(self, post_id: int):
        """Delete a post by id."""
        self.client.table("posts").delete().eq("id", post_id).execute()

    def get_due_posts(self, current_time):
        """Get all posts due at or before current_time (not published and not drafts)."""
        now_str = current_time.strftime("%Y-%m-%dT%H:%M:%S%z") if hasattr(current_time, "strftime") else str(current_time)
        res = self.client.table("posts").select("*").eq("published", False).eq("draft", False).lte("publish_time", now_str).execute()
        return res.data or []

    def mark_post_published(self, post_id: int):
        """Mark a post as published."""
        self.client.table("posts").update({"published": True}).eq("id", post_id).execute()
