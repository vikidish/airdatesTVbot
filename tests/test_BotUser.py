# Tests for original BotUser.py (master branch)
# Run: python3 -m unittest discover tests/ -v

import os
import sys
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'src'))

from BotUser import BotUser, BotUserStorageHelper


class TestBotUserBasic(unittest.TestCase):
    """Tests for BotUser class without storage"""

    def test_init_with_tg_user_id(self):
        user = BotUser('12345')
        self.assertEqual(user.tg_user_id, '12345')

    def test_init_defaults(self):
        user = BotUser('12345')
        self.assertIsNone(user.airdates_user)
        self.assertFalse(user.is_admin)
        self.assertFalse(user.daily_enabled)
        self.assertEqual(user.daily_types, [])

    def test_init_with_airdates_user(self):
        user = BotUser('12345', airdates_user='testuser')
        self.assertEqual(user.airdates_user, 'testuser')

    def test_tg_user_id_property_getter(self):
        user = BotUser('12345')
        self.assertEqual(user.tg_user_id, '12345')

    def test_tg_user_id_property_setter(self):
        user = BotUser('12345')
        user.tg_user_id = '67890'
        self.assertEqual(user.tg_user_id, '67890')

    def test_tg_user_id_setter_rejects_none(self):
        user = BotUser('12345')
        with self.assertRaises(ValueError):
            user.tg_user_id = None

    def test_tg_user_id_setter_rejects_empty(self):
        user = BotUser('12345')
        with self.assertRaises(ValueError):
            user.tg_user_id = ''


class TestBotUserWithStorage(unittest.TestCase):
    """Tests for BotUser class with storage helper"""

    @classmethod
    def setUpClass(cls):
        # Create temp directory for test database
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.temp_dir, 'test.db')
        cls.cache_path = os.path.join(cls.temp_dir, 'cache')

        # Create test database schema
        conn = sqlite3.connect(cls.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                tg_user_id TEXT PRIMARY KEY,
                airdates_user TEXT,
                daily_enabled INTEGER DEFAULT 0,
                daily_hour INTEGER DEFAULT 9,
                daily_types TEXT DEFAULT '[]',
                last_sent TIMESTAMP,
                is_admin INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()

    def setUp(self):
        # Clear users table before each test
        conn = sqlite3.connect(self.db_path)
        conn.execute('DELETE FROM Users')
        conn.commit()
        conn.close()

        self.storage = BotUserStorageHelper(self.db_path, self.cache_path)

    def test_init_with_storage_new_user(self):
        """New user should have defaults when not in database"""
        user = BotUser('12345', storage_hlp=self.storage)
        self.assertEqual(user.tg_user_id, '12345')
        self.assertIsNone(user.airdates_user)
        self.assertFalse(user.is_admin)

    def test_init_with_storage_existing_user(self):
        """Existing user should load from database"""
        # Insert user into database
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO Users (tg_user_id, airdates_user, daily_enabled, is_admin, daily_types) VALUES (?, ?, ?, ?, ?)",
            ('12345', 'myairuser', 1, 1, '["today"]')
        )
        conn.commit()
        conn.close()

        user = BotUser('12345', storage_hlp=self.storage)

        self.assertEqual(user.airdates_user, 'myairuser')
        self.assertTrue(user.daily_enabled)
        self.assertTrue(user.is_admin)
        self.assertEqual(user.daily_types, ['today'])

    def test_init_airdates_user_param_overrides_db(self):
        """airdates_user parameter should override database value"""
        # Insert user into database
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO Users (tg_user_id, airdates_user) VALUES (?, ?)",
            ('12345', 'dbuser')
        )
        conn.commit()
        conn.close()

        user = BotUser('12345', airdates_user='paramuser', storage_hlp=self.storage)
        self.assertEqual(user.airdates_user, 'paramuser')


class TestBotUserStorageHelper(unittest.TestCase):
    """Tests for BotUserStorageHelper class"""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.temp_dir, 'test.db')
        cls.cache_path = os.path.join(cls.temp_dir, 'cache')

        # Create test database schema
        conn = sqlite3.connect(cls.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                tg_user_id TEXT PRIMARY KEY,
                airdates_user TEXT,
                daily_enabled INTEGER DEFAULT 0,
                daily_hour INTEGER DEFAULT 9,
                daily_types TEXT DEFAULT '[]',
                last_sent TIMESTAMP,
                is_admin INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()

    def setUp(self):
        # Clear users table before each test
        conn = sqlite3.connect(self.db_path)
        conn.execute('DELETE FROM Users')
        conn.commit()
        conn.close()

        self.storage = BotUserStorageHelper(self.db_path, self.cache_path)

    def test_save_tg_user_creates_user(self):
        """save_tg_user should create new user record"""
        self.storage.save_tg_user('12345')

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM Users WHERE tg_user_id = ?", ('12345',))
        row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row['tg_user_id'], '12345')

    def test_save_tg_user_ignores_duplicate(self):
        """save_tg_user should not fail on duplicate"""
        self.storage.save_tg_user('12345')
        self.storage.save_tg_user('12345')  # Should not raise

    def test_update_airdates_user(self):
        """update_airdates_user should upsert user record"""
        self.storage.update_airdates_user('12345', 'newuser')

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT airdates_user FROM Users WHERE tg_user_id = ?", ('12345',))
        row = cur.fetchone()
        conn.close()

        self.assertEqual(row['airdates_user'], 'newuser')

    def test_update_airdates_user_with_daily_enabled(self):
        """update_airdates_user should set daily_enabled if provided"""
        self.storage.update_airdates_user('12345', 'newuser', daily_enabled=1)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT daily_enabled FROM Users WHERE tg_user_id = ?", ('12345',))
        row = cur.fetchone()
        conn.close()

        self.assertEqual(row['daily_enabled'], 1)

    def test_update_daily_enabled(self):
        """update_daily_enabled should update the flag"""
        self.storage.save_tg_user('12345')
        self.storage.update_daily_enabled('12345', 1)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT daily_enabled FROM Users WHERE tg_user_id = ?", ('12345',))
        row = cur.fetchone()
        conn.close()

        self.assertEqual(row['daily_enabled'], 1)

    def test_update_daily_hour(self):
        """update_daily_hour should update the hour"""
        self.storage.save_tg_user('12345')
        self.storage.update_daily_hour('12345', 15)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT daily_hour FROM Users WHERE tg_user_id = ?", ('12345',))
        row = cur.fetchone()
        conn.close()

        self.assertEqual(row['daily_hour'], 15)

    def test_update_daily_types(self):
        """update_daily_types should update the types JSON"""
        self.storage.save_tg_user('12345')
        types_json = json.dumps(['today', 'new'])
        self.storage.update_daily_types('12345', types_json)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT daily_types FROM Users WHERE tg_user_id = ?", ('12345',))
        row = cur.fetchone()
        conn.close()

        self.assertEqual(json.loads(row['daily_types']), ['today', 'new'])

    def test_get_user_by_tg_user_id_found(self):
        """get_user_by_tg_user_id should return user dict"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO Users (tg_user_id, airdates_user, daily_enabled, is_admin, daily_types) VALUES (?, ?, ?, ?, ?)",
            ('12345', 'testuser', 1, 0, '["today"]')
        )
        conn.commit()
        conn.close()

        user = self.storage.get_user_by_tg_user_id('12345')

        self.assertIsNotNone(user)
        self.assertEqual(user['airdates_user'], 'testuser')
        self.assertEqual(user['daily_enabled'], 1)

    def test_get_user_by_tg_user_id_not_found(self):
        """get_user_by_tg_user_id should return None if not found"""
        user = self.storage.get_user_by_tg_user_id('99999')
        self.assertIsNone(user)

    def test_get_daily_send_by_hour(self):
        """get_daily_send_by_hour should return users for that hour"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO Users (tg_user_id, airdates_user, daily_enabled, daily_hour, daily_types, last_sent) VALUES (?, ?, ?, ?, ?, ?)",
            ('111', 'user1', 1, 9, '["today"]', '2024-01-15 10:00:00.000000')
        )
        conn.execute(
            "INSERT INTO Users (tg_user_id, airdates_user, daily_enabled, daily_hour, daily_types) VALUES (?, ?, ?, ?, ?)",
            ('222', 'user2', 1, 9, '[]')
        )
        conn.execute(
            "INSERT INTO Users (tg_user_id, airdates_user, daily_enabled, daily_hour, daily_types) VALUES (?, ?, ?, ?, ?)",
            ('333', 'user3', 1, 10, '[]')
        )
        conn.execute(
            "INSERT INTO Users (tg_user_id, airdates_user, daily_enabled, daily_hour, daily_types) VALUES (?, ?, ?, ?, ?)",
            ('444', 'user4', 0, 9, '[]')  # daily_enabled = 0
        )
        conn.commit()
        conn.close()

        users = self.storage.get_daily_send_by_hour(9)

        self.assertEqual(len(users), 2)
        user_ids = [u['tg_user_id'] for u in users]
        self.assertIn('111', user_ids)
        self.assertIn('222', user_ids)

        # Verify all expected keys are present (catches column alias bugs)
        for user in users:
            self.assertIn('tg_user_id', user)
            self.assertIn('airdates_user', user)
            self.assertIn('last_sent', user)
            self.assertIn('daily_types', user)

    def test_update_last_sent(self):
        """update_last_sent should update the timestamp"""
        self.storage.save_tg_user('12345')
        self.storage.update_last_sent('12345', '2024-01-15 10:00:00')

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT last_sent FROM Users WHERE tg_user_id = ?", ('12345',))
        row = cur.fetchone()
        conn.close()

        self.assertEqual(row['last_sent'], '2024-01-15 10:00:00')

    def test_update_last_sent_with_datetime_object(self):
        """update_last_sent with datetime object should be retrievable via get_daily_send_by_hour"""
        # This tests the actual usage pattern in dailysendtask.py:
        # botdbsql.update_last_sent(tg_user_id, datetime.utcnow())
        now = datetime.utcnow()

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO Users (tg_user_id, airdates_user, daily_enabled, daily_hour, daily_types) VALUES (?, ?, ?, ?, ?)",
            ('12345', 'testuser', 1, 9, '["today"]')
        )
        conn.commit()
        conn.close()

        # Update with datetime object (like dailysendtask.py does)
        self.storage.update_last_sent('12345', now)

        # Retrieve via get_daily_send_by_hour (like dailysendtask.py does)
        users = self.storage.get_daily_send_by_hour(9)
        self.assertEqual(len(users), 1)

        last_sent = users[0]['last_sent']

        # The value should be usable as datetime - either already a datetime or parseable
        if isinstance(last_sent, datetime):
            last_sent_dt = last_sent
        else:
            last_sent_dt = datetime.strptime(last_sent, '%Y-%m-%d %H:%M:%S.%f')

        # Verify the datetime is close to what we stored
        self.assertEqual(last_sent_dt.year, now.year)
        self.assertEqual(last_sent_dt.month, now.month)
        self.assertEqual(last_sent_dt.day, now.day)
        self.assertEqual(last_sent_dt.hour, now.hour)


class TestBotUserMethods(unittest.TestCase):
    """Tests for BotUser instance methods that use storage"""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.temp_dir, 'test.db')
        cls.cache_path = os.path.join(cls.temp_dir, 'cache')

        conn = sqlite3.connect(cls.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                tg_user_id TEXT PRIMARY KEY,
                airdates_user TEXT,
                daily_enabled INTEGER DEFAULT 0,
                daily_hour INTEGER DEFAULT 9,
                daily_types TEXT DEFAULT '[]',
                last_sent TIMESTAMP,
                is_admin INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()

    def setUp(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('DELETE FROM Users')
        conn.commit()
        conn.close()

        self.storage = BotUserStorageHelper(self.db_path, self.cache_path)

    def test_save_tg_user(self):
        """BotUser.save_tg_user should save to storage"""
        user = BotUser('12345', storage_hlp=self.storage)
        user.save_tg_user()

        db_user = self.storage.get_user_by_tg_user_id('12345')
        self.assertIsNotNone(db_user)

    def test_register_airdates_user(self):
        """BotUser.register_airdates_user should update storage"""
        user = BotUser('12345', storage_hlp=self.storage)
        user.register_airdates_user('myairdates')

        self.assertEqual(user.airdates_user, 'myairdates')
        db_user = self.storage.get_user_by_tg_user_id('12345')
        self.assertEqual(db_user['airdates_user'], 'myairdates')

    def test_register_airdates_user_with_daily_enabled(self):
        """BotUser.register_airdates_user should set daily_enabled"""
        user = BotUser('12345', storage_hlp=self.storage)
        user.register_airdates_user('myairdates', daily_enabled=True)

        db_user = self.storage.get_user_by_tg_user_id('12345')
        self.assertEqual(db_user['daily_enabled'], 1)

    def test_update_daily_enabled(self):
        """BotUser.update_daily_enabled should update storage"""
        user = BotUser('12345', storage_hlp=self.storage)
        user.save_tg_user()
        user.update_daily_enabled(True)

        self.assertTrue(user.daily_enabled)
        db_user = self.storage.get_user_by_tg_user_id('12345')
        self.assertEqual(db_user['daily_enabled'], 1)

    def test_update_daily_hour(self):
        """BotUser.update_daily_hour should update storage"""
        user = BotUser('12345', storage_hlp=self.storage)
        user.save_tg_user()
        user.update_daily_hour(14)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT daily_hour FROM Users WHERE tg_user_id = ?", ('12345',))
        row = cur.fetchone()
        conn.close()

        self.assertEqual(row['daily_hour'], 14)

    def test_update_daily_types(self):
        """BotUser.update_daily_types should update storage"""
        user = BotUser('12345', storage_hlp=self.storage)
        user.save_tg_user()
        user.update_daily_types(['today', 'yday'])

        self.assertEqual(user.daily_types, ['today', 'yday'])
        db_user = self.storage.get_user_by_tg_user_id('12345')
        self.assertEqual(json.loads(db_user['daily_types']), ['today', 'yday'])

    def test_update_daily_types_filters_invalid(self):
        """BotUser.update_daily_types should filter invalid types"""
        user = BotUser('12345', storage_hlp=self.storage)
        user.save_tg_user()
        user.update_daily_types(['today', 'invalid', 'tmrw'])

        # 'invalid' should be filtered out
        self.assertEqual(user.daily_types, ['today', 'tmrw'])


if __name__ == '__main__':
    unittest.main()
