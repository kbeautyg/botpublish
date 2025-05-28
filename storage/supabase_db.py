# storage/supabase_db.py
"""
Supabase database helper with **auto-migration**:
– Проверяет, какие колонки есть в БД, и при отсутствии — добавляет их.
– Ставит publish_time nullable (для черновиков).
Работает на любом анонимном ключе (RLS выключена).
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

# Глобальный экземпляр (инициализируется в main.py)
db: "SupabaseDB" | None = None


class SupabaseDB:
    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)

    # ---------- helpers ---------- #

    def _query(self, q):
        """Safe wrapper around PostgREST .execute() with nice error logs."""
        try:
            return q.execute()
        except Exception as e:
            print("Supabase query error:", e)
            raise

    def _exec_sql(self, sql: str):
        """Выполняем произвольный SQL через функцию rpc sql(). Игнорируем ошибки дублирования."""
        try:
            self.client.postgrest.rpc("sql", {"sql": sql}).execute()
            return True
        except Exception as e:
            print("SQL exec error:", e, "⟵ ignored")
            return False

    def _column_exists(self, table: str, column: str) -> bool:
        query = f"""
        select 1
        from information_schema.columns
        where table_name = '{table}'
          and column_name = '{column}'
        limit 1;
        """
        try:
            res = self.client.postgrest.rpc("sql", {"sql": query}).execute()
            return bool(res.data)
        except Exception:
            # Если у анонимного ключа нет прав – просто считаем, что есть.
            return True

    def _ensure_column(self, table: str, column: str, ddl: str):
        """Добавляет колонку, если её нет."""
        if not self._column_exists(table, column):
            self._exec_sql(f'alter table "{table}" add column if not exists {ddl};')

    # ---------- schema ---------- #

    def init_schema(self):
        """
        – Проверяем наличие таблиц (channels, posts, users).
        – Создаём при необходимости.
        – Добавляем недостающие колонки (draft, repeat_interval, notified и т.д.).
        – Убираем NOT NULL с publish_time, чтобы можно было хранить черновики.
        """
        # Таблицы создаём, только если их явно нет.
        self._exec_sql(
            """
            create table if not exists users (
                user_id       bigint primary key,
                timezone      text    default 'UTC',
                language      text    default 'ru',
                date_format   text    default 'YYYY-MM-DD',
                time_format   text    default 'HH:MM',
                notify_before integer default 0,
                inserted_at   timestamptz default now()
            );

            create table if not exists channels (
                id          bigserial primary key,
                user_id     bigint,
                chat_id     bigint not null unique,
                name        text,
                is_active   boolean default true,
                inserted_at timestamptz default now()
            );

            create table if not exists posts (
                id             bigserial primary key,
                user_id        bigint,
                channel_id     bigint references channels(id) on delete cascade,
                chat_id        bigint,
                text           text,
                media_type     text,
                media_id       text,
                format         text,
                disable_preview boolean default false,
                buttons        jsonb,
                publish_time   timestamptz,
                published      boolean default false,
                repeat_interval bigint  default 0,
                draft          boolean default false,
                notified       boolean default false,
                created_at     timestamptz default now(),
                updated_at     timestamptz default now()
            );
            """
        )

        # add missing columns for legacy schemas
        self._ensure_column("posts", "repeat_interval", "repeat_interval bigint default 0")
        self._ensure_column("posts", "draft", "draft boolean default false")
        self._ensure_column("posts", "notified", "notified boolean default false")
        self._ensure_column("posts", "disable_preview", "disable_preview boolean default false")

        # make publish_time nullable (для черновиков)
        self._exec_sql(
            "alter table posts alter column publish_time drop not null;"
        )

        # индексы
        self._exec_sql(
            """
            create index if not exists idx_posts_publish_time  on posts(publish_time);
            create index if not exists idx_posts_published     on posts(published);
            """
        )

    # ---------- user ---------- #

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        res = self._query(self.client.table("users").select("*").eq("user_id", user_id).limit(1))
        return res.data[0] if res.data else None

    def ensure_user(self, user_id: int, default_lang: str | None = None):
        user = self.get_user(user_id)
        if user:
            return user
        res = self._query(
            self.client.table("users").insert(
                {
                    "user_id": user_id,
                    "timezone": "UTC",
                    "language": default_lang or "ru",
                }
            )
        )
        return res.data[0]

    def update_user(self, user_id: int, updates: Dict[str, Any]):
        if not updates:
            return
        self._query(self.client.table("users").update(updates).eq("user_id", user_id))

    # ---------- channels ---------- #

    def add_channel(self, user_id: int, chat_id: int, name: str):
        existing = (
            self._query(
                self.client.table("channels").select("*").eq("user_id", user_id).eq("chat_id", chat_id)
            ).data
            or []
        )
        if existing:
            self._query(
                self.client.table("channels")
                .update({"name": name})
                .eq("user_id", user_id)
                .eq("chat_id", chat_id)
            )
            return existing[0]
        res = self._query(
            self.client.table("channels").insert({"user_id": user_id, "chat_id": chat_id, "name": name})
        )
        return res.data[0]

    def list_channels(self, user_id: int | None = None) -> List[Dict[str, Any]]:
        q = self.client.table("channels").select("*").eq("is_active", True)
        if user_id is not None:
            q = q.eq("user_id", user_id)
        return self._query(q).data or []

    def remove_channel(self, user_id: int, ident: str) -> bool:
        try:
            cid = int(ident)
        except ValueError:
            return False
        # by chat_id OR internal id
        deleted = self._query(
            self.client.table("channels")
            .delete()
            .eq("user_id", user_id)
            .or_(f"chat_id.eq.{cid},id.eq.{cid}")
        ).data
        return bool(deleted)

    # ---------- posts ---------- #

    def add_post(self, post: Dict[str, Any]):
        # ensure json serialisable
        if isinstance(post.get("buttons"), list):
            post["buttons"] = json.dumps(post["buttons"])
        res = self._query(self.client.table("posts").insert(post))
        return res.data[0]

    def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        res = self._query(self.client.table("posts").select("*").eq("id", post_id).limit(1))
        return res.data[0] if res.data else None

    def list_posts(self, user_id: int | None = None, only_pending: bool = True):
        q = self.client.table("posts").select("*")
        if only_pending:
            q = q.eq("published", False)
        if user_id is not None:
            q = q.eq("user_id", user_id)
        return self._query(q.order("publish_time", asc=True)).data or []

    def update_post(self, post_id: int, changes: Dict[str, Any]):
        if "buttons" in changes and isinstance(changes["buttons"], list):
            changes["buttons"] = json.dumps(changes["buttons"])
        self._query(self.client.table("posts").update(changes).eq("id", post_id))

    def delete_post(self, post_id: int):
        self._query(self.client.table("posts").delete().eq("id", post_id))

    # ---------- scheduler helpers ---------- #

    def get_due_posts(self, now_utc: datetime):
        """
        Вернёт все посты publish_time <= now, которые не опубликованы и не черновики.
        Если в таблице ещё нет поля draft — фильтр опускаем.
        """
        now_iso = now_utc.isoformat(timespec="seconds")
        q = self.client.table("posts").select("*").eq("published", False).lte("publish_time", now_iso)
        try:
            data = self._query(q.eq("draft", False)).data
        except Exception:
            # fallback, если колонки draft нет
            data = self._query(q).data
        return data or []

    def mark_post_published(self, pid: int):
        self._query(self.client.table("posts").update({"published": True}).eq("id", pid))
