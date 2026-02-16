# Tests for original TVShows.py (master branch)
# Run: python3 -m unittest discover tests/ -v

import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'src'))

from TVShows import (
    TVShows, AirdatesHelper,
    _get_episode_id, format_date, get_day_text_by_type,
    _group_episodes_by_show, format_footer, format_shows_text,
    format_show_text_header, format_episode_details
)
from BotUser import BotUser

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class TestGetEpisodeId(unittest.TestCase):
    """Tests for _get_episode_id() helper function (private, but tested for behavior)"""

    def test_basic_episode_id(self):
        result = _get_episode_id('123', 'Show Name S01E01')
        self.assertEqual(result, '123_S01E01')

    def test_episode_with_spaces(self):
        result = _get_episode_id('456', 'The Big Show S02E10')
        self.assertEqual(result, '456_S02E10')

    def test_single_word_show(self):
        result = _get_episode_id('789', 'Lost S05E03')
        self.assertEqual(result, '789_S05E03')


class TestFormatDate(unittest.TestCase):
    """Tests for format_date() helper function"""

    def test_format_date_january(self):
        result = format_date('20200110')
        self.assertEqual(result, '10 Jan 2020')

    def test_format_date_december(self):
        result = format_date('20191225')
        self.assertEqual(result, '25 Dec 2019')

    def test_format_date_single_digit_day(self):
        result = format_date('20200101')
        self.assertEqual(result, '1 Jan 2020')


class TestGetDayTextByType(unittest.TestCase):
    """Tests for get_day_text_by_type() helper function"""

    def test_today(self):
        self.assertEqual(get_day_text_by_type('today'), 'Today')

    def test_yesterday(self):
        self.assertEqual(get_day_text_by_type('yday'), 'Yesterday')

    def test_tomorrow(self):
        self.assertEqual(get_day_text_by_type('tmrw'), 'Tomorrow')

    def test_unknown_returns_empty(self):
        self.assertEqual(get_day_text_by_type('other'), '')


class TestGroupEpisodesByShow(unittest.TestCase):
    """Tests for _group_episodes_by_show() helper function"""

    def test_single_episode(self):
        episodes = [{
            'show_id': '100',
            'episode_id': '100_S01E01',
            'episode_name': 'Test Show S01E01',
            'episode_date': '20200110'
        }]
        result = _group_episodes_by_show(episodes)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], '100')
        self.assertEqual(result[0]['name'], 'Test Show')
        self.assertEqual(len(result[0]['episodes']), 1)

    def test_multiple_episodes_same_show(self):
        episodes = [
            {'show_id': '100', 'episode_id': '100_S01E01', 'episode_name': 'Test Show S01E01', 'episode_date': '20200110'},
            {'show_id': '100', 'episode_id': '100_S01E02', 'episode_name': 'Test Show S01E02', 'episode_date': '20200110'},
        ]
        result = _group_episodes_by_show(episodes)

        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]['episodes']), 2)

    def test_multiple_shows(self):
        episodes = [
            {'show_id': '100', 'episode_id': '100_S01E01', 'episode_name': 'Show A S01E01', 'episode_date': '20200110'},
            {'show_id': '200', 'episode_id': '200_S02E05', 'episode_name': 'Show B S02E05', 'episode_date': '20200110'},
        ]
        result = _group_episodes_by_show(episodes)

        self.assertEqual(len(result), 2)

    def test_series_premiere_flag_preserved(self):
        episodes = [{
            'show_id': '100',
            'episode_id': '100_S01E01',
            'episode_name': 'New Show S01E01',
            'episode_date': '20200110',
            'series_prem': 1
        }]
        result = _group_episodes_by_show(episodes)

        self.assertEqual(result[0].get('series_prem'), 1)

    def test_season_premiere_flag_preserved(self):
        episodes = [{
            'show_id': '100',
            'episode_id': '100_S02E01',
            'episode_name': 'Returning Show S02E01',
            'episode_date': '20200110',
            'season_prem': 1
        }]
        result = _group_episodes_by_show(episodes)

        self.assertEqual(result[0].get('season_prem'), 1)

    def test_user_show_flag_preserved(self):
        episodes = [{
            'show_id': '100',
            'episode_id': '100_S01E05',
            'episode_name': 'My Show S01E05',
            'episode_date': '20200110',
            'is_user_show': 1
        }]
        result = _group_episodes_by_show(episodes)

        self.assertEqual(result[0].get('is_user_show'), 1)


class TestFormatFooter(unittest.TestCase):
    """Tests for format_footer() helper function"""

    def test_footer_with_username(self):
        result = format_footer('testuser')
        self.assertIn('testuser', result)
        self.assertIn('airdates.tv/u/testuser', result)

    def test_footer_without_username(self):
        result = format_footer(None)
        self.assertIn('airdates.tv', result)
        self.assertNotIn('/u/', result)


class TestFormatShowTextHeader(unittest.TestCase):
    """Tests for format_show_text_header() helper function"""

    def test_header_today_with_user(self):
        result = format_show_text_header('today', 'testuser', '20200110', show_all=False)
        self.assertIn('testuser', result)
        self.assertIn('Today', result)
        self.assertIn('10 Jan 2020', result)

    def test_header_all_shows(self):
        result = format_show_text_header('today', None, '20200110', show_all=True)
        self.assertIn('ALL', result)


class TestAirdatesHelperParsing(unittest.TestCase):
    """Tests for AirdatesHelper parsing functionality"""

    @classmethod
    def setUpClass(cls):
        cls.helper = AirdatesHelper(
            ROOT_DIR + "/data",
            ROOT_DIR + "/data/cache",
            from_cache=False,
            local_data=True,
            download_if_notfound=False
        )
        # Load and parse test HTML
        with open(ROOT_DIR + "/data/airdates.html", 'rt') as f:
            html_data = f.read()
        cls.shows_data, cls.engines_data = cls.helper._parse_airdates_data(html_data)

    def test_parse_returns_dict(self):
        self.assertIsInstance(self.shows_data, dict)

    def test_parse_returns_engines(self):
        self.assertIsInstance(self.engines_data, list)
        self.assertGreater(len(self.engines_data), 0)

    def test_engines_have_required_keys(self):
        for engine in self.engines_data:
            self.assertIn('name', engine)
            self.assertIn('href', engine)

    def test_days_have_episodes(self):
        for day_key, day_data in self.shows_data.items():
            self.assertIn('episodes', day_data)
            self.assertIsInstance(day_data['episodes'], list)

    def test_episodes_have_required_fields(self):
        for day_key, day_data in self.shows_data.items():
            for episode in day_data['episodes']:
                self.assertIn('show_id', episode)
                self.assertIn('show_source', episode)
                self.assertIn('episode_id', episode)
                self.assertIn('episode_name', episode)


class TestTVShowsClass(unittest.TestCase):
    """Tests for TVShows class with local test data"""

    @classmethod
    def setUpClass(cls):
        cls.bot_user = BotUser('111')
        cls.tv = TVShows(
            AirdatesHelper(
                ROOT_DIR + "/data",
                ROOT_DIR + "/data/cache",
                from_cache=False,
                local_data=True,
                download_if_notfound=False
            )
        )

    def test_get_shows_returns_dict_with_episodes(self):
        shows = self.tv.get_shows('20200110', self.bot_user, user_only=False)
        self.assertIn('episodes', shows)
        self.assertIsInstance(shows['episodes'], list)

    def test_get_shows_all_shows_count(self):
        """Test data has 46 episodes on 2020-01-10"""
        shows = self.tv.get_shows('20200110', self.bot_user, user_only=False)
        self.assertEqual(len(shows['episodes']), 46)

    def test_get_shows_user_only_without_airdates_user(self):
        """Without airdates user, user_only returns all shows"""
        self.bot_user.airdates_user = None
        shows = self.tv.get_shows('20200110', self.bot_user, user_only=True)
        self.assertEqual(len(shows['episodes']), 46)

    def test_get_shows_user_only_with_airdates_user(self):
        """With airdates user 'v8i8k', should return only user's shows"""
        self.bot_user.airdates_user = 'v8i8k'
        shows = self.tv.get_shows('20200110', self.bot_user, user_only=True)
        self.assertEqual(len(shows['episodes']), 4)

    def test_get_shows_invalid_date_returns_empty(self):
        shows = self.tv.get_shows('20991231', self.bot_user, user_only=False)
        self.assertEqual(len(shows['episodes']), 0)

    def test_get_shows_episodes_have_date(self):
        """Episodes should have episode_date added"""
        shows = self.tv.get_shows('20200110', self.bot_user, user_only=False)
        if shows['episodes']:
            self.assertIn('episode_date', shows['episodes'][0])
            self.assertEqual(shows['episodes'][0]['episode_date'], '20200110')

    def test_find_episode_by_episode_id_found(self):
        episode = self.tv.find_episode_by_episode_id('4316_S01E01')
        self.assertIsNotNone(episode)
        self.assertEqual(episode['show_id'], '4316')
        self.assertEqual(episode['show_source'], 'Medical Police')

    def test_find_episode_by_episode_id_not_found(self):
        episode = self.tv.find_episode_by_episode_id('99999_S99E99')
        self.assertIsNone(episode)

    def test_find_episodes_by_text_found(self):
        episodes = self.tv.find_episodes_by_text('you')
        self.assertGreater(len(episodes), 0)
        # All results should contain 'you' (case insensitive)
        for ep in episodes:
            self.assertIn('you', ep['episode_name'].lower())

    def test_find_episodes_by_text_not_found(self):
        episodes = self.tv.find_episodes_by_text('zzzzzzzzz')
        self.assertEqual(len(episodes), 0)

    def test_find_episodes_by_text_case_insensitive(self):
        episodes_lower = self.tv.find_episodes_by_text('you')
        episodes_upper = self.tv.find_episodes_by_text('YOU')
        self.assertEqual(len(episodes_lower), len(episodes_upper))

    def test_engines_data_available(self):
        """Engines data should be parsed and available"""
        self.assertIsNotNone(self.tv.engines_data)
        self.assertGreater(len(self.tv.engines_data), 0)


class TestTVShowsUserShows(unittest.TestCase):
    """Tests for user-specific show filtering"""

    @classmethod
    def setUpClass(cls):
        cls.tv = TVShows(
            AirdatesHelper(
                ROOT_DIR + "/data",
                ROOT_DIR + "/data/cache",
                from_cache=False,
                local_data=True,
                download_if_notfound=False
            )
        )

    def test_user_shows_marked_with_flag(self):
        """User's shows should have is_user_show flag"""
        bot_user = BotUser('111')
        bot_user.airdates_user = 'v8i8k'

        shows = self.tv.get_shows('20200110', bot_user, user_only=False)
        user_shows = [ep for ep in shows['episodes'] if ep.get('is_user_show')]

        self.assertEqual(len(user_shows), 4)

    def test_get_shows_day_marks_user_shows(self):
        """get_shows_day should mark user's shows"""
        bot_user = BotUser('111')
        bot_user.airdates_user = 'v8i8k'

        shows = self.tv.get_shows_day('20200110', bot_user)
        user_shows = [ep for ep in shows['episodes'] if ep.get('is_user_show')]

        self.assertGreater(len(user_shows), 0)


class TestTVShowsNewShows(unittest.TestCase):
    """Tests for get_new_shows() method"""

    @classmethod
    def setUpClass(cls):
        cls.tv = TVShows(
            AirdatesHelper(
                ROOT_DIR + "/data",
                ROOT_DIR + "/data/cache",
                from_cache=False,
                local_data=True,
                download_if_notfound=False
            )
        )
        cls.bot_user = BotUser('111')

    def test_get_new_shows_returns_list(self):
        shows = self.tv.get_new_shows('week', 'series', self.bot_user)
        self.assertIsInstance(shows, list)

    def test_get_new_shows_returns_seven_days(self):
        shows = self.tv.get_new_shows('week', 'series', self.bot_user)
        self.assertEqual(len(shows), 7)

    def test_get_new_shows_each_day_has_structure(self):
        shows = self.tv.get_new_shows('week', 'series', self.bot_user)
        for day in shows:
            self.assertIn('date', day)
            self.assertIn('episodes', day)


if __name__ == '__main__':
    unittest.main()
