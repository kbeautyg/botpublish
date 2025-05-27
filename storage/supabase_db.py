# storage/supabase_db.py
import json
from supabase import create_client, Client

# Global database instance (to be set in main)
db = None

class SupabaseDB:
    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)
    
    def init_schema(self):
        """Ensure the necessary tables exist (if possible)."""
        try:
            # Check if tables exist by attempting a simple query
            res = self.client.table("channels").select("id").limit(1).execute()
            res2 = self.client.table("posts").select("id").limit(1).execute()
        except Exception as e:
            # If an error occurred, you may create tables via SQL if using service role key.
            # (This requires a service key; if using anon key, ensure tables are created manually.)
            try:
                # Attempt to create tables using an RPC or direct SQL (if allowed)
                self.client.postgrest.rpc("sql", {
                    "sql": """
                    CREATE TABLE IF NOT EXISTS channels (
                        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        name TEXT,
                        chat_id BIGINT UNIQUE NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS posts (
                        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        channel_id BIGINT NOT NULL,
                        text TEXT,
                        media_id TEXT,
                        media_type TEXT,
                        format TEXT,
                        buttons TEXT,
                        publish_time TIMESTAMP WITH TIME ZONE NOT NULL,
                        published BOOLEAN DEFAULT FALSE,
                        FOREIGN KEY (channel_id) REFERENCES channels(id)
                    );
                    """
                }).execute()
            except Exception:
                pass  # If cannot create via API, assume manual setup required
    
    # Channel management
    def add_channel(self, chat_id: int, name: str):
        """Add a new channel to the database or update name if exists."""
        # Check if channel already exists
        res = self.client.table("channels").select("*").eq("chat_id", chat_id).execute()
        if res.data:
            # Already exists, update name if changed
            self.client.table("channels").update({"name": name}).eq("chat_id", chat_id).execute()
            return res.data[0]  # return existing
        # Insert new channel
        data = {"name": name, "chat_id": chat_id}
        res = self.client.table("channels").insert(data).execute()
        if res.data:
            return res.data[0]
        return None

    def list_channels(self):
        """List all channels."""
        res = self.client.table("channels").select("*").execute()
        return res.data or []

    def remove_channel(self, identifier: str):
        """Remove a channel by username or chat_id or internal id."""
        # Try to find by chat_id or name
        # If identifier is numeric (possibly as string), treat as chat_id
        channel_to_delete = None
        if identifier.startswith("@"):
            # Lookup by username (username not stored, so cannot remove by username directly)
            return False
        try:
            # Try as chat_id (int)
            cid = int(identifier)
            # Chat IDs in Telegram can be negative; int() will handle '-' sign
            res = self.client.table("channels").select("*").eq("chat_id", cid).execute()
            if res.data:
                channel_to_delete = res.data[0]
        except ValueError:
            # Not a numeric id
            # Try by internal id (identity)
            try:
                internal_id = int(identifier)
                res = self.client.table("channels").select("*").eq("id", internal_id).execute()
                if res.data:
                    channel_to_delete = res.data[0]
            except ValueError:
                channel_to_delete = None
        if not channel_to_delete:
            return False
        # Delete channel by chat_id
        cid = channel_to_delete["chat_id"]
        self.client.table("channels").delete().eq("chat_id", cid).execute()
        # Also delete any scheduled posts for this channel (cleanup)
        self.client.table("posts").delete().eq("channel_id", channel_to_delete.get("id", None)).execute()
        return True

    # Post management
    def add_post(self, post_data: dict):
        """Insert a new post into the database. Returns the inserted post record."""
        # If buttons list is present, convert to JSON string for storage
        if "buttons" in post_data and isinstance(post_data["buttons"], list):
            post_data["buttons"] = json.dumps(post_data["buttons"])
        res = self.client.table("posts").insert(post_data).execute()
        if res.data:
            return res.data[0]
        return None

    def get_post(self, post_id: int):
        """Retrieve a single post by id."""
        res = self.client.table("posts").select("*").eq("id", post_id).execute()
        data = res.data or []
        return data[0] if data else None

    def list_posts(self, only_pending=True):
        """List posts (pending or all)."""
        query = self.client.table("posts").select("*")
        if only_pending:
            query = query.eq("published", False)
        query = query.order("publish_time", asc=True)
        res = query.execute()
        return res.data or []

    def update_post(self, post_id: int, updates: dict):
        """Update fields of a post."""
        # If buttons in updates is list, convert to JSON string
        if "buttons" in updates and isinstance(updates["buttons"], list):
            updates["buttons"] = json.dumps(updates["buttons"])
        res = self.client.table("posts").update(updates).eq("id", post_id).execute()
        if res.data:
            return res.data[0]
        return None

    def delete_post(self, post_id: int):
        """Delete a post by id."""
        self.client.table("posts").delete().eq("id", post_id).execute()

    def get_due_posts(self, current_time):
        """Get all posts that should be published at or before current_time (and not yet published)."""
        # Ensure current_time is string in ISO format for comparison
        if hasattr(current_time, "isoformat"):
            now_str = current_time.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            now_str = str(current_time)
        res = self.client.table("posts").select("*").eq("published", False).lte("publish_time", now_str).execute()
        return res.data or []

    def mark_post_published(self, post_id: int):
        """Mark a post as published."""
        self.client.table("posts").update({"published": True}).eq("id", post_id).execute()
