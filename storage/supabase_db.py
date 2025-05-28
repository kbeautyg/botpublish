# =========================================================
# storage/supabase_db.py  (patched)
# =========================================================
import json as _json
from datetime import datetime
from typing import Optional, List, Dict, Any

from postgrest.exceptions import APIError
from supabase import create_client, Client

json = _json  # allow other modules to import `json` from here

# Global DB instance – will be assigned in main.py
#   from storage import supabase_db; supabase_db.db = SupabaseDB(...)
db: "SupabaseDB | None" = None


class SupabaseDB:
    """Lightweight ORM‑style wrapper over Supabase PostgREST API.

    Важно: мы *не* полагаемся на наличие всех столбцов (например, `draft`).
    Если столбца нет – методы автоматически деградируют без падения.
    """

    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)

    # ------------------------------------------------------------------
    # Initial schema bootstrap / online‑migration helpers
    # ------------------------------------------------------------------
    def init_schema(self) -> None:
        """Ensure required columns exist – «ленивые» online‑migrations.

        Supabase free‑tier часто не даёт выполнять `ALTER TABLE`, однако
        metadata можно проверить через служебную view `pg_catalog` и,
        если привилегий нет, мы хотя бы не упадём при обращении к полям.
        """
        required_columns: Dict[str, Dict[str, str]] = {
            "posts": {
                "draft": "BOOLEAN DEFAULT FALSE",
                "notified": "BOOLEAN DEFAULT FALSE",
            },
        }
        for table, cols in required_columns.items():
            try:
                existing = self.client.table("pg_catalog.pg_attribute") \
                    .select("attname") \
                    .eq("attrelid::regclass::text", table) \
                    .eq("attisdropped", False) \
                    .execute().data or []
                present = {c["attname"] for c in existing}
            except Exception:
                present = set()  # fallback – assume nothing

            missing = {name: ddl for name, ddl in cols.items() if name not in present}
            if not missing:
                continue

            # Try ALTER TABLE … ADD COLUMN IF NOT EXISTS
            for col, ddl in missing.items():
                try:
                    sql = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {ddl};"
                    self.client.postgrest.rpc("sql", {"sql": sql}).execute()
                except Exception:
                    # No rights – silently ignore; runtime code will degrade.
                    pass

    # ------------------------------------------------------------------
    # «helpers» – thin wrappers around PostgREST
    # ------------------------------------------------------------------
    # region USERS ------------------------------------------------------
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        res = self.client.table("users").select("*").eq("user_id", user_id).execute()
        return (res.data or [None])[0]

    def ensure_user(self, user_id: int, default_lang: str = "ru") -> Dict[str, Any]:
        user = self.get_user(user_id)
        if user:
            return user
        data = {
            "user_id": user_id,
            "timezone": "UTC",
            "language": default_lang,
            "date_format": "YYYY-MM-DD",
            "time_format": "HH:MM",
            "notify_before": 0,
        }
        res = self.client.table("users").insert(data).execute()
        return res.data[0]

    def update_user(self, user_id: int, updates: Dict[str, Any]):
        if not updates:
            return None
        res = self.client.table("users").update(updates).eq("user_id", user_id).execute()
        return (res.data or [None])[0]

    # endregion USERS ---------------------------------------------------

    # region CHANNELS ---------------------------------------------------
    def add_channel(self, user_id: int, chat_id: int, name: str):
        sel = self.client.table("channels").select("*") \
            .eq("user_id", user_id).eq("chat_id", chat_id).execute().data
        if sel:
            # update name if exists
            self.client.table("channels").update({"name": name}) \
                .eq("user_id", user_id).eq("chat_id", chat_id).execute()
            return sel[0]
        res = self.client.table("channels").insert({
            "user_id": user_id,
            "chat_id": chat_id,
            "name": name,
        }).execute()
        return res.data[0]

    def list_channels(self, user_id: Optional[int] = None):
        q = self.client.table("channels").select("*")
        if user_id is not None:
            q = q.eq("user_id", user_id)
        return q.order("id").execute().data or []

    def remove_channel(self, user_id: int, ident: str) -> bool:
        try:
            cid = int(ident)
        except ValueError:
            return False
        # try chat_id then internal id
        for field in ("chat_id", "id"):
            res = self.client.table("channels").select("id").eq("user_id", user_id).eq(field, cid).execute().data
            if res:
                ch_id = res[0]["id"]
                self.client.table("channels").delete().eq("id", ch_id).execute()
                self.client.table("posts").delete().eq("channel_id", ch_id).execute()
                return True
        return False

    # endregion CHANNELS -----------------------------------------------

    # region POSTS ------------------------------------------------------
    def add_post(self, data: Dict[str, Any]):
        if isinstance(data.get("buttons"), list):
            data["buttons"] = json.dumps(data["buttons"], ensure_ascii=False)
        res = self.client.table("posts").insert(data).execute()
        return res.data[0]

    def get_post(self, post_id: int):
        res = self.client.table("posts").select("*").eq("id", post_id).execute()
        return (res.data or [None])[0]

    def list_posts(self, *, user_id: Optional[int] = None, only_pending=True):
        q = self.client.table("posts").select("*")
        if user_id is not None:
            q = q.eq("user_id", user_id)
        if only_pending:
            q = q.eq("published", False)
        return q.order("publish_time", asc=True).execute().data or []

    def update_post(self, post_id: int, updates: Dict[str, Any]):
        if "buttons" in updates and isinstance(updates["buttons"], list):
            updates["buttons"] = json.dumps(updates["buttons"], ensure_ascii=False)
        res = self.client.table("posts").update(updates).eq("id", post_id).execute()
        return (res.data or [None])[0]

    def delete_post(self, post_id: int):
        self.client.table("posts").delete().eq("id", post_id).execute()

    def mark_post_published(self, post_id: int):
        self.update_post(post_id, {"published": True})

    # -- patched method -------------------------------------------------
    def get_due_posts(self, current_time: datetime):
        """Return posts with publish_time <= current_time (UTC) that are not published and not drafts.

        Если столбца `draft` нет – игнорируем фильтр, чтобы не падать.
        """
        now_iso = current_time.astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
        base_query = self.client.table("posts").select("*").eq("published", False)
        try:
            res = base_query.eq("draft", False).lte("publish_time", now_iso).execute()
            return res.data or []
        except APIError as e:
            if e.code == "42703" and "draft" in (e.message or ""):
                # column missing – fallback without it
                res = base_query.lte("publish_time", now_iso).execute()
                return res.data or []
            raise  # re‑raise unknown errors

    # endregion POSTS ---------------------------------------------------

# =========================================================
# No code below – all other modules remain unchanged.
# =========================================================
