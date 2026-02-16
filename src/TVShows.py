"""TV show data fetching and formatting from airdates.tv."""

from __future__ import annotations

import json
import logging
import re
from copy import deepcopy
from datetime import date, timedelta, datetime
from typing import Any

import requests
from bs4 import BeautifulSoup
from diskcache import Cache

from src.BotUser import BotUser

logger = logging.getLogger(__name__)

AIRDATES_URL = "https://www.airdates.tv"
AIRDATES_USER_URL = "https://www.airdates.tv/_u/listSeries/"
AIRDATES_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:72.0) Gecko/20100101 Firefox/72.0"

EMOJIS = {
    'user_show': '&#x2705;',
    'new_show': "&#x1F6D1;",
    'return_show': '&#x1F536;'
}

CACHE_KEY_PREFIX_USER = '_user_data'
CACHE_KEY_AIRDATES = 'shows_data'
CACHE_KEY_ENGINES = 'engines_data'


class TVShows:
    """Main interface for TV show data."""

    def __init__(self, airdates_hlp: AirdatesHelper) -> None:
        self.airdates_hlp = airdates_hlp
        self.airdates_data, self._engines_data = self.airdates_hlp.get_airdates_data()

    def refresh_user_data(self, bot_user: BotUser) -> None:
        """Refresh cached data for a user."""
        logger.info(f'Refreshing data for user, is_admin={bot_user.is_admin}')
        if bot_user.is_admin:
            self.airdates_hlp.clear_airdates_data()
            self.airdates_data, self._engines_data = self.airdates_hlp.get_airdates_data()
        if bot_user.airdates_user:
            self.airdates_hlp.clear_user_data(bot_user.airdates_user)

    @property
    def engines_data(self) -> list[dict[str, str]]:
        return self._engines_data

    def get_shows_day(self, day_str: str, bot_user: BotUser) -> dict[str, Any]:
        """Get all shows for a specific date."""
        day_shows: dict[str, Any] = {"date": day_str, "episodes": []}

        day = self.airdates_data.get(day_str)
        if day:
            episodes = deepcopy(day['episodes'])
            episodes = [{**ep, 'episode_date': day_str} for ep in episodes]
            day_shows['episodes'] = episodes

            if bot_user.airdates_user:
                airdates_user_data = self.airdates_hlp.get_airdates_user_data(bot_user.airdates_user)
                if airdates_user_data and day_shows['episodes']:
                    for ep in day_shows['episodes']:
                        if ep['show_id'] in airdates_user_data:
                            ep['is_user_show'] = 1

        return day_shows

    def get_user_shows_day(self, day_str: str, bot_user: BotUser) -> dict[str, Any]:
        """Get only the user's shows for a specific date."""
        shows_day = self.get_shows_day(day_str, bot_user)

        if bot_user.airdates_user:
            episodes = [ep for ep in shows_day['episodes'] if ep.get('is_user_show')]
        else:
            episodes = shows_day['episodes']

        shows_day['episodes'] = episodes
        return shows_day

    def get_shows(
        self,
        day: str,
        bot_user: BotUser,
        user_only: bool = True
    ) -> dict[str, Any]:
        """Get shows for a day (today/yday/tmrw or date string)."""
        day_str = day
        if day == 'today':
            day_str = date.today().strftime("%Y%m%d")
        elif day == 'yday':
            yesterday = date.today() - timedelta(days=1)
            day_str = yesterday.strftime("%Y%m%d")
        elif day == 'tmrw':
            tomorrow = date.today() + timedelta(days=1)
            day_str = tomorrow.strftime("%Y%m%d")

        if user_only:
            return self.get_user_shows_day(day_str, bot_user)
        return self.get_shows_day(day_str, bot_user)

    def get_new_shows(
        self,
        interval: str = 'week',
        new_type: str = 'series',
        bot_user: BotUser | None = None
    ) -> list[dict[str, Any]]:
        """Get new/returning shows for a week interval."""
        show_days = []
        today = datetime.now().date()
        start_day = today - timedelta(days=today.weekday())

        if interval == 'prev':
            start_day = today - timedelta(days=(today.weekday() + 7))
        elif interval == 'next':
            start_day = today - timedelta(days=(today.weekday() - 7))

        for i in range(7):
            show_day = start_day + timedelta(days=i)
            show_days.append(show_day.strftime("%Y%m%d"))

        show_filter = 'series_prem' if new_type != 'season' else 'season_prem'

        shows = []
        for show_day in show_days:
            show_data = self.airdates_data.get(show_day)
            episodes = []
            if show_data:
                episodes = [
                    {**ep, 'episode_date': show_day}
                    for ep in show_data['episodes']
                    if ep.get(show_filter) == 1
                ]

            if bot_user and bot_user.airdates_user:
                airdates_user_data = self.airdates_hlp.get_airdates_user_data(bot_user.airdates_user)
                if airdates_user_data and episodes:
                    for ep in episodes:
                        if ep['show_id'] in airdates_user_data:
                            ep['is_user_show'] = 1

            shows.append({'date': show_day, 'episodes': episodes})

        return shows

    def find_episode_by_episode_id(self, episode_id: str) -> dict[str, Any] | None:
        """Find an episode by its ID."""
        show_id = episode_id.split('_', 1)[0]

        for day_key, day in self.airdates_data.items():
            found_episode = next(
                (x for x in day['episodes'] if x['episode_id'] == episode_id),
                None
            )
            if found_episode:
                return {**found_episode, 'episode_date': day_key}

        return None

    def find_episodes_by_text(self, text: str) -> list[dict[str, Any]]:
        """Search for episodes by text in show name."""
        shows = []
        search_text = text.lower().strip()
        for day_key, day in self.airdates_data.items():
            shows += [
                {**ep, 'episode_date': day_key}
                for ep in day['episodes']
                if search_text in ep['episode_name'].lower()
            ]
        return shows


def _manage_cache(func):
    """Decorator to manage cache lifecycle."""
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        finally:
            self.cache.close()
    return wrapper


class AirdatesHelper:
    """Helper for fetching and caching airdates.tv data."""

    def __init__(
        self,
        data_path: str,
        cache_path: str,
        from_cache: bool = True,
        local_data: bool = False,
        download_if_notfound: bool = False
    ) -> None:
        self.data_path = data_path
        self.cache_path = cache_path
        self.from_cache = from_cache
        self.local_data = local_data
        self.download_if_notfound = download_if_notfound
        self._cache: Cache | None = None

    @property
    def cache(self) -> Cache:
        if not self._cache:
            self._cache = Cache(self.cache_path)
        return self._cache

    @_manage_cache
    def get_airdates_data(self) -> tuple[dict[str, Any], list[dict[str, str]]]:
        """Get airdates data, from cache or fresh download."""
        shows_data = None
        engines_data = None

        if self.from_cache:
            shows_data = self.cache.get(CACHE_KEY_AIRDATES)
            engines_data = self.cache.get(CACHE_KEY_ENGINES)

        if not shows_data or not self.from_cache or not engines_data:
            shows_data_html = self._download_airdates_data()
            if shows_data_html:
                shows_data, engines_data = self._parse_airdates_data(shows_data_html)
                self.cache.set(CACHE_KEY_AIRDATES, shows_data, expire=60 * 60 * 6)
                self.cache.set(CACHE_KEY_ENGINES, engines_data, expire=60 * 60 * 24 * 30)
            else:
                shows_data = {}
                engines_data = []

        return shows_data, engines_data

    @_manage_cache
    def get_airdates_user_data(self, airdates_user: str) -> dict[str, Any] | None:
        """Get user's followed shows from airdates.tv."""
        if not airdates_user:
            return None

        cache_key = f"{CACHE_KEY_PREFIX_USER}{airdates_user}"
        user_data = None

        if self.from_cache:
            user_data = self.cache.get(cache_key)

        if not user_data or not self.from_cache:
            user_data_json = self._download_user_data(airdates_user)
            if user_data_json:
                user_data = json.loads(user_data_json)
                # Convert from list to dict with 'id' as key
                user_data = {str(x['id']): x for x in user_data}
                self.cache.set(cache_key, user_data, expire=60 * 60 * 24)

        return user_data

    @_manage_cache
    def clear_user_data(self, airdates_user: str) -> None:
        """Clear cached user data."""
        if not airdates_user:
            return
        cache_key = f"{CACHE_KEY_PREFIX_USER}{airdates_user}"
        self.cache.delete(cache_key)

    @_manage_cache
    def clear_airdates_data(self) -> None:
        """Clear cached airdates data."""
        self.cache.delete(CACHE_KEY_AIRDATES)
        self.cache.delete(CACHE_KEY_ENGINES)

    def _download_airdates_data(self) -> str | None:
        """Download main page from airdates.tv."""
        filename = f'{self.data_path}/airdates.html'

        if self.local_data:
            try:
                with open(filename, 'rt') as f:
                    return f.read()
            except FileNotFoundError:
                logger.warning('Local airdates file not found')
                if not self.download_if_notfound:
                    return None

        url = AIRDATES_URL
        headers = {'accept': '*/*', 'user-agent': AIRDATES_UA}

        try:
            response = requests.get(url, headers=headers, timeout=30)
            logging.getLogger('ext_requests').info(
                f'Fetching Airdates main page - Status: {response.status_code}'
            )

            if response.status_code == 200:
                _save_to_file(filename, response.content)
                return response.text
            else:
                logger.error(f"Connection Error Code: {response.status_code}")
                return None
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    def _download_user_data(self, airdates_user: str) -> str | None:
        """Download user's show list from airdates.tv."""
        filename = f'{self.data_path}/{airdates_user}_airdates.txt'

        if self.local_data:
            try:
                with open(filename, 'rt') as f:
                    return f.read()
            except FileNotFoundError:
                logger.warning(f'Local user file not found for {airdates_user}')
                if not self.download_if_notfound:
                    return None

        url = AIRDATES_USER_URL + airdates_user
        headers = {'Accept': '*/*', 'User-Agent': AIRDATES_UA}

        try:
            response = requests.get(url, headers=headers, timeout=30)
            logging.getLogger('ext_requests').info(
                f'Fetching Airdates user data for {airdates_user} - Status: {response.status_code}'
            )

            if response.status_code == 200:
                _save_to_file(filename, response.content)
                return response.text
            else:
                logger.error(f"Connection Error Code: {response.status_code}")
                return None
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    def _parse_airdates_data(
        self,
        html_data: str
    ) -> tuple[dict[str, Any], list[dict[str, str]]]:
        """Parse HTML data into structured show data."""
        soup = BeautifulSoup(html_data, 'html.parser')
        days_div = soup.select("div.day")

        days: dict[str, Any] = {}
        for div in days_div:
            day_entries = div.find_all('div', {'class': 'entry'})
            episodes = []
            for x in day_entries:
                ep = {
                    'show_id': str(x['data-series-id']),
                    'show_source': str(x['data-series-source']),
                    'episode_id': _get_episode_id(str(x['data-series-id']), str(x.div.contents[0])),
                    'episode_name': str(x.div.contents[0])
                }

                if 'series-premiere' in x["class"]:
                    ep['series_prem'] = 1
                if 'season-premiere' in x["class"]:
                    ep['season_prem'] = 1

                episodes.append(ep)

            shows_date = str(div['data-date'])
            days[shows_date] = {'episodes': episodes}

        # Parse watch engines
        engines_script = soup.find('script', text=re.compile("engines"))
        engines: list[dict[str, str]] = []
        if engines_script:
            engines_raw = re.findall(r'\{ .*?\ }', engines_script.text)
            engines = [_parse_js_object(i) for i in engines_raw]

        return days, engines


def _parse_js_object(js_str: str) -> dict[str, str]:
    """Parse JavaScript-style object to dict. Handles unquoted keys."""
    # Convert JS object syntax to valid JSON:
    # { name: "value" } -> { "name": "value" }
    # Only match keys after { or , (not colons inside URLs)
    js_str = re.sub(r'([{,])\s*(\w+)\s*:', r'\1 "\2":', js_str)
    js_str = js_str.replace("'", '"')
    return json.loads(js_str)


def _get_episode_id(show_id: str, episode_name: str) -> str:
    """Generate episode ID from show ID and episode name."""
    episode_num = episode_name.split()[-1]
    return f"{show_id}_{episode_num}"


def _save_to_file(filename: str, data_binary: bytes) -> None:
    """Save binary data to file."""
    try:
        with open(filename, 'wb') as f:
            f.write(data_binary)
    except IOError as e:
        logger.error(f'Failed to save file {filename}: {e}')


# Formatting functions

def format_episode_details(
    episode: dict[str, Any],
    engines: list[dict[str, str]]
) -> str:
    """Format episode details with watch links."""
    show_text = f'<b>{episode["episode_name"]}</b> (' + format_date(episode["episode_date"]) + ')'
    if episode.get('is_user_show'):
        show_text = f"{EMOJIS['user_show']}&#160;{show_text}"
    show_text += '\n\n'

    for engine in engines:
        show_name = " ".join(episode['episode_name'].split()[:-1])
        engine_show_url = engine['href'].replace('MONKEY_N', requests.utils.quote(show_name), 1)
        engine_show_url = engine_show_url.replace('MONKEY', requests.utils.quote(episode['episode_name']), 1)
        engine_show_url = engine_show_url.replace('{WIKI_TITLE}', requests.utils.quote(episode['show_source']), 1)
        show_text += f'-- <a href="{engine_show_url}">{engine["name"]}</a>\n'

    return show_text


def format_show_text_header(
    day_param: str,
    airdates_user: str | None,
    date_str: str,
    show_all: bool = False
) -> str:
    """Format the header text for show listings."""
    user_text = f'{airdates_user} ' if airdates_user else ''
    all_text = ' ALL' if show_all else ''
    day_text = get_day_text_by_type(day_param)

    return f'{user_text}{day_text}\'s ({format_date(date_str)}){all_text} TV Shows:\n\n'


def get_day_text_by_type(day_type: str) -> str:
    """Get display text for day type."""
    day_texts = {
        'today': 'Today',
        'yday': 'Yesterday',
        'tmrw': 'Tomorrow'
    }
    return day_texts.get(day_type, '')


def format_show_text_main(show: dict[str, Any], show_date: bool = False) -> str:
    """Format a single show with its episodes."""
    show_text = '<b>' + show['name'] + '</b>'

    if show.get('series_prem'):
        show_text = f"{EMOJIS['new_show']}&#160;{show_text}"
    if show.get('season_prem'):
        show_text = f"{EMOJIS['return_show']}&#160;{show_text}"
    if show.get('is_user_show'):
        show_text = f"{show_text}&#160;{EMOJIS['user_show']}&#160;"

    show_text += '\n'

    for episode in show['episodes']:
        ep_id = _get_episode_id(show['id'], episode['name'])
        show_text += f"{episode['name']} - /details_{ep_id}"
        if show_date:
            show_text += ' (' + format_date(episode['date']) + ')'
        show_text += '\n'

    return show_text


def format_shows_text(episodes: list[dict[str, Any]], show_date: bool = False) -> str:
    """Format a list of episodes grouped by show."""
    shows_episodes = _group_episodes_by_show(episodes)
    shows_text = [format_show_text_main(i, show_date) for i in shows_episodes]
    return "\n".join(shows_text) + '\n'


def format_shows_days_text(show_days: list[dict[str, Any]]) -> str:
    """Format shows grouped by day."""
    shows_days_text = ''

    for show_day in show_days:
        if show_day['episodes']:
            shows_days_text += f'<i>--------  {format_date(show_day["date"])}  --------</i>\n\n'
            shows_episodes = _group_episodes_by_show(show_day['episodes'])
            shows_text = [format_show_text_main(i) for i in shows_episodes]
            shows_days_text += "\n".join(shows_text) + '\n'

    return shows_days_text


def format_date(day_str: str) -> str:
    """Format date string for display."""
    date_obj = datetime.strptime(day_str, '%Y%m%d')
    return date_obj.strftime("%-d %b %Y")


def format_footer(username: str | None = None) -> str:
    """Format the footer with airdates.tv link."""
    if username:
        return f"--------------------------------\nVisit {AIRDATES_URL}/u/{username} for more shows"
    return f"--------------------------------\nVisit {AIRDATES_URL} for more shows"


def _group_episodes_by_show(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group episodes by their show."""
    shows: dict[str, dict[str, Any]] = {}

    for ep in episodes:
        show_id = ep['show_id']
        show_name = " ".join(ep['episode_name'].split()[:-1])

        if show_id not in shows:
            shows[show_id] = {'name': show_name, 'episodes': []}

        if ep.get('series_prem'):
            shows[show_id]['series_prem'] = 1
        if ep.get('season_prem'):
            shows[show_id]['season_prem'] = 1
        if ep.get('is_user_show'):
            shows[show_id]['is_user_show'] = 1

        shows[show_id]['episodes'].append({
            'id': ep['episode_id'],
            'name': ep['episode_name'],
            'date': ep['episode_date']
        })

    # Convert to list with id as first key
    return [{'id': k, **v} for k, v in shows.items()]
