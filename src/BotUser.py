"""User storage and management for the Telegram bot."""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

from diskcache import Cache

logger = logging.getLogger(__name__)


class BotUser:
    """Represents a bot user with their settings and preferences."""

    def __init__(
        self,
        tg_user_id: int | str,
        airdates_user: str | None = None,
        storage_hlp: BotUserStorageHelper | None = None
    ) -> None:
        self._tg_user_id = tg_user_id
        self.storage_hlp = storage_hlp

        self.airdates_user: str | None = None
        self.is_admin: bool = False
        self.daily_enabled: bool = False
        self.daily_types: list[str] = []

        db_user = None
        if self.storage_hlp:
            db_user = self.storage_hlp.get_user_by_tg_user_id(self.tg_user_id)

        if airdates_user:
            self.airdates_user = airdates_user
        elif db_user:
            self.airdates_user = db_user['airdates_user']

        if db_user:
            self.is_admin = bool(db_user['is_admin'])
            self.daily_enabled = bool(db_user['daily_enabled'])
            self.daily_types = json.loads(db_user['daily_types'] or '[]')

    @property
    def tg_user_id(self) -> int | str:
        return self._tg_user_id

    @tg_user_id.setter
    def tg_user_id(self, tg_user_id: int | str) -> None:
        if not tg_user_id:
            raise ValueError('Valid telegram user id must be provided')
        self._tg_user_id = tg_user_id

    def save_tg_user(self) -> None:
        """Save the user to storage."""
        if self.storage_hlp:
            self.storage_hlp.save_tg_user(self.tg_user_id)

    def register_airdates_user(
        self,
        airdates_user: str,
        daily_enabled: bool | None = None
    ) -> None:
        """Register or update the airdates username."""
        # Basic validation
        if airdates_user:
            airdates_user = airdates_user.strip()
        self.airdates_user = airdates_user

        daily_enabled_int = None
        if daily_enabled is not None:
            daily_enabled_int = int(daily_enabled)

        if self.storage_hlp:
            self.storage_hlp.update_airdates_user(
                self.tg_user_id, airdates_user, daily_enabled_int
            )

    def update_daily_enabled(self, daily_enabled: bool) -> None:
        """Enable or disable daily updates."""
        self.daily_enabled = daily_enabled
        if self.storage_hlp:
            self.storage_hlp.update_daily_enabled(self.tg_user_id, int(daily_enabled))

    def update_daily_hour(self, hour: int) -> None:
        """Set the hour for daily updates (0-23 UTC)."""
        if not 0 <= hour <= 23:
            raise ValueError('Hour must be between 0 and 23')
        if self.storage_hlp:
            self.storage_hlp.update_daily_hour(self.tg_user_id, hour)

    def update_daily_types(self, daily_types: list[str]) -> None:
        """Update the types of daily updates to receive."""
        valid_types = {'today', 'yday', 'tmrw'}
        daily_types = [t for t in daily_types if t in valid_types]
        self.daily_types = daily_types
        if self.storage_hlp:
            self.storage_hlp.update_daily_types(self.tg_user_id, json.dumps(daily_types))

    def get_refresh_count(self) -> int:
        """Get the current refresh count for today."""
        if self.storage_hlp:
            return self.storage_hlp.get_cache_refresh_counter(self.tg_user_id)
        return 0

    def update_refresh_count(self) -> int:
        """Increment and return the refresh count."""
        if self.storage_hlp:
            return self.storage_hlp.update_cache_refresh_counter(self.tg_user_id)
        return 0

    def reset_refresh_count(self) -> None:
        """Reset the refresh count."""
        if self.storage_hlp:
            self.storage_hlp.reset_cache_refresh_counter(self.tg_user_id)


def _manage_connection(func):
    """Decorator to manage SQLite connection lifecycle."""
    def wrapper(self, *args, **kwargs):
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            return func(self, conn, *args, **kwargs)
        finally:
            conn.close()
    return wrapper




class BotUserStorageHelper:
    """Handles database and cache operations for bot users.

    Thread-safe and multiprocess-safe.
    """

    def __init__(self, db_path: str, cache_path: str, refresh_ttl: int = 86400) -> None:
        self.db_path = db_path
        self.cache_path = cache_path
        self.refresh_ttl = refresh_ttl
        self._cache: Cache | None = None

    @property
    def cache(self) -> Cache:
        if not self._cache:
            self._cache = Cache(self.cache_path)
        return self._cache

    def close(self) -> None:
        """Close the cache connection."""
        if self._cache:
            self._cache.close()
            self._cache = None

    @_manage_connection
    def update_airdates_user(
        self,
        conn: sqlite3.Connection,
        tg_user_id: int | str,
        airdates_user: str | None,
        daily_enabled: int | None = None
    ) -> None:
        cur = conn.cursor()
        if daily_enabled is not None:
            stmt = '''
            INSERT INTO Users (tg_user_id, airdates_user, daily_enabled) VALUES (?, ?, ?)
                ON CONFLICT (tg_user_id) DO UPDATE SET airdates_user=excluded.airdates_user,
                daily_enabled=excluded.daily_enabled;
            '''
            cur.execute(stmt, (tg_user_id, airdates_user, daily_enabled))
        else:
            stmt = '''
            INSERT INTO Users (tg_user_id, airdates_user) VALUES (?, ?)
                ON CONFLICT (tg_user_id) DO UPDATE SET airdates_user=excluded.airdates_user;
            '''
            cur.execute(stmt, (tg_user_id, airdates_user))

    @_manage_connection
    def save_tg_user(self, conn: sqlite3.Connection, tg_user_id: int | str) -> None:
        cur = conn.cursor()
        stmt = 'INSERT OR IGNORE INTO Users (tg_user_id) VALUES (?)'
        cur.execute(stmt, (tg_user_id,))

    @_manage_connection
    def update_daily_enabled(
        self,
        conn: sqlite3.Connection,
        tg_user_id: int | str,
        daily_enabled: int
    ) -> None:
        cur = conn.cursor()
        stmt = '''
            INSERT INTO Users (tg_user_id, daily_enabled) VALUES (?, ?)
                ON CONFLICT (tg_user_id) DO UPDATE SET daily_enabled=excluded.daily_enabled;
            '''
        cur.execute(stmt, (tg_user_id, daily_enabled))

    @_manage_connection
    def update_daily_hour(
        self,
        conn: sqlite3.Connection,
        tg_user_id: int | str,
        daily_hour: int
    ) -> None:
        cur = conn.cursor()
        stmt = '''
            INSERT INTO Users (tg_user_id, daily_hour) VALUES (?, ?)
                ON CONFLICT (tg_user_id) DO UPDATE SET daily_hour=excluded.daily_hour;
            '''
        cur.execute(stmt, (tg_user_id, daily_hour))

    @_manage_connection
    def update_daily_types(
        self,
        conn: sqlite3.Connection,
        tg_user_id: int | str,
        daily_types: str
    ) -> None:
        cur = conn.cursor()
        stmt = '''
            INSERT INTO Users (tg_user_id, daily_types) VALUES (?, ?)
                ON CONFLICT (tg_user_id) DO UPDATE SET daily_types=excluded.daily_types;
            '''
        cur.execute(stmt, (tg_user_id, daily_types))

    @_manage_connection
    def get_user_by_tg_user_id(
        self,
        conn: sqlite3.Connection,
        tg_user_id: int | str
    ) -> dict[str, Any] | None:
        cur = conn.cursor()
        stmt = '''
        SELECT airdates_user, daily_enabled, last_sent, is_admin, daily_enabled, daily_types
        FROM Users
        WHERE tg_user_id = ?
        '''
        cur.execute(stmt, (tg_user_id,))
        rows = cur.fetchall()
        user = (rows[0:1] + [None])[0]
        return dict(user) if user else None

    @_manage_connection
    def get_daily_send_by_hour(
        self,
        conn: sqlite3.Connection,
        hour: int
    ) -> list[dict[str, Any]]:
        cur = conn.cursor()
        stmt = '''
        SELECT tg_user_id, airdates_user, last_sent as "last_sent [timestamp]", daily_types
        FROM Users
        WHERE daily_enabled = ? and daily_hour = ?
        '''
        cur.execute(stmt, (1, hour))
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    @_manage_connection
    def update_last_sent(
        self,
        conn: sqlite3.Connection,
        tg_user_id: int | str,
        last_sent: Any
    ) -> None:
        cur = conn.cursor()
        stmt = 'UPDATE Users SET last_sent = ? where tg_user_id = ?;'
        cur.execute(stmt, (last_sent, tg_user_id))

    def get_cache_refresh_counter(self, tg_user_id: int | str) -> int:
        cache_key = f'refresh_count_{tg_user_id}'
        result = self.cache.get(cache_key, default=0, expire_time=True)
        value, _ = result
        return value

    def update_cache_refresh_counter(self, tg_user_id: int | str) -> int:
        """Increment refresh counter."""
        cache_key = f'refresh_count_{tg_user_id}'
        try:
            new_count = self.cache.incr(cache_key, default=None)
        except KeyError:
            self.cache.set(cache_key, 1, expire=self.refresh_ttl)
            new_count = 1
        return new_count

    def reset_cache_refresh_counter(self, tg_user_id: int | str) -> None:
        cache_key = f'refresh_count_{tg_user_id}'
        self.cache.delete(cache_key)
