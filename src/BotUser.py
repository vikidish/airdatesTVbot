import sqlite3
import json
from diskcache import Cache

class BotUser:

    def __init__(self, tg_user_id, airdates_user=None, storage_hlp: 'BotUserStorageHelper' = None):
        self._tg_user_id = tg_user_id
        self.storage_hlp = storage_hlp

        self.airdates_user = None
        self.is_admin = False
        self.daily_enabled = False
        self.daily_types = []

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
            self.daily_types = json.loads(db_user['daily_types'])

    @property
    def tg_user_id(self):
        return self._tg_user_id

    @tg_user_id.setter
    def tg_user_id(self, tg_user_id):
        if not tg_user_id or tg_user_id == '':
            raise ValueError('valid telegram user id must be provided')
        self._tg_user_id = tg_user_id

    def save_tg_user(self):
        self.storage_hlp.save_tg_user(self.tg_user_id)

    def register_airdates_user(self, airdates_user, daily_enabled=None):
        self.airdates_user = airdates_user
        if daily_enabled is not None:
            daily_enabled = int(daily_enabled)
        if self.storage_hlp:
            self.storage_hlp.update_airdates_user(self.tg_user_id, airdates_user, daily_enabled)

    def update_daily_enabled(self, daily_enabled):
        self.daily_enabled = daily_enabled
        self.storage_hlp.update_daily_enabled(self.tg_user_id, int(daily_enabled))

    def update_daily_hour(self, hour):
        self.storage_hlp.update_daily_hour(self.tg_user_id, hour)

    def update_daily_types(self, daily_types):
        self.daily_types = daily_types
        self.storage_hlp.update_daily_types(self.tg_user_id, json.dumps(daily_types))

    def get_refresh_count(self):
        return self.storage_hlp.get_cache_refresh_counter(self.tg_user_id)

    def update_refresh_count(self):
        return self.storage_hlp.update_cache_refresh_counter(self.tg_user_id)

    def reset_refresh_count(self):
        return self.storage_hlp.reset_cache_refresh_counter(self.tg_user_id)


def _manage_connection(func):
    def wrapper(self, *args, **kwargs):

        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.set_trace_callback(print)

        ret = func(self, conn, *args, **kwargs)
        conn.close()
        return ret

    return wrapper


def _manage_cache(func):
    def wrapper(self, *args, **kwargs):

        ret = func(self, *args, **kwargs)
        self.cache.close()
        return ret

    return wrapper


class BotUserStorageHelper:

    def __init__(self, db_path, cache_path):
        self.db_path = db_path
        self.cache_path = cache_path
        self._cache = None

    @property
    def cache(self):
        if not self._cache:
            self._cache = Cache(self.cache_path)

        return self._cache

    @_manage_connection
    def update_airdates_user(self, conn, tg_user_id, airdates_user, daily_enabled=None):
        cur = conn.cursor()
        if daily_enabled is not None:
            stmt = f'''
            INSERT INTO Users (tg_user_id, airdates_user, daily_enabled) VALUES (?, ?, ?) 
                ON CONFLICT (tg_user_id) DO UPDATE SET airdates_user=excluded.airdates_user, 
                daily_enabled=excluded.daily_enabled; 
            '''
            cur.execute(stmt, (tg_user_id, airdates_user, daily_enabled))

        else:
            stmt = f'''
            INSERT INTO Users (tg_user_id, airdates_user) VALUES (?, ?) 
                ON CONFLICT (tg_user_id) DO UPDATE SET airdates_user=excluded.airdates_user; 
            '''
            cur.execute(stmt, (tg_user_id, airdates_user))

    @_manage_connection
    def save_tg_user(self, conn, tg_user_id):
        cur = conn.cursor()

        stmt = f'''
        INSERT OR IGNORE INTO Users (tg_user_id) VALUES (?) 
        '''
        cur.execute(stmt, (tg_user_id, ))

    @_manage_connection
    def update_daily_enabled(self, conn, tg_user_id, daily_enabled):
        cur = conn.cursor()
        stmt = f'''
            INSERT INTO Users (tg_user_id, daily_enabled) VALUES (?, ?) 
                ON CONFLICT (tg_user_id) DO UPDATE SET daily_enabled=excluded.daily_enabled;
            '''
        cur.execute(stmt, (tg_user_id, daily_enabled))

    @_manage_connection
    def update_daily_hour(self, conn, tg_user_id, daily_hour):
        cur = conn.cursor()
        stmt = f'''
            INSERT INTO Users (tg_user_id, daily_hour) VALUES (?, ?) 
                ON CONFLICT (tg_user_id) DO UPDATE SET daily_hour=excluded.daily_hour;
            '''
        cur.execute(stmt, (tg_user_id, daily_hour))

    @_manage_connection
    def update_daily_types(self, conn, tg_user_id, daily_types):
        cur = conn.cursor()
        stmt = f'''
            INSERT INTO Users (tg_user_id, daily_types) VALUES (?, ?) 
                ON CONFLICT (tg_user_id) DO UPDATE SET daily_types=excluded.daily_types;
            '''
        cur.execute(stmt, (tg_user_id, daily_types))

    @_manage_connection
    def get_user_by_tg_user_id(self, conn, tg_user_id):
        cur = conn.cursor()
        stmt = f'''
        SELECT airdates_user, daily_enabled, last_sent, is_admin, daily_enabled, daily_types 
        FROM Users 
        WHERE tg_user_id = ?
        '''
        cur.execute(stmt, (tg_user_id, ))
        rows = cur.fetchall()
        user = (rows[0:1] + [None])[0]
        return dict(user) if user else None

    @_manage_connection
    def get_daily_send_by_hour(self, conn, hour):
        cur = conn.cursor()
        stmt = f'''
        SELECT tg_user_id, airdates_user, last_sent as "last_sent [timestamp]", daily_types 
        FROM Users 
        WHERE daily_enabled = ? and daily_hour = ? 
        '''
        cur.execute(stmt, (1, hour))
        rows = cur.fetchall()
        # print(type(rows[0][2]))
        users = [dict(row) for row in rows]
        return users

    @_manage_connection
    def update_last_sent(self, conn, tg_user_id, last_sent):
        cur = conn.cursor()
        stmt = f'''
        UPDATE Users SET last_sent = ? where tg_user_id = ?;
        '''
        cur.execute(stmt, (last_sent, tg_user_id))

    @_manage_cache
    def get_cache_refresh_counter(self, tg_user_id):
        cache_key = f'refresh_count_{tg_user_id}'
        result = self.cache.get(cache_key, default=0, expire_time=True)
        value, expire = result
        return value

    @_manage_cache
    def update_cache_refresh_counter(self, tg_user_id):
        cache_key = f'refresh_count_{tg_user_id}'
        try:
            new_count = self.cache.incr(cache_key, default=None)

        except KeyError:
            self.cache.set(cache_key, 1, expire=60 * 60 * 24)
            # self.cache.set(cache_key, 1, expire=60 * 1)
            new_count = 1

        return new_count

    @_manage_cache
    def reset_cache_refresh_counter(self, tg_user_id):
        cache_key = f'refresh_count_{tg_user_id}'
        self.cache.delete(cache_key)

