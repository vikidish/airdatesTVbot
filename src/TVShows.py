import json
import re
from datetime import date, timedelta, datetime
from copy import deepcopy

import logging
from diskcache import Cache

import demjson
import requests
from bs4 import BeautifulSoup

# from config import *


import os
import sys
# csfp = os.path.abspath(os.path.dirname(__file__))
# if csfp not in sys.path:
#     sys.path.insert(0, csfp)

from src.BotUser import BotUser

AIRDATES_URL = "https://www.airdates.tv"
AIRDATES_USER_URL = "https://www.airdates.tv/_u/listSeries/"
AIRDATES_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:72.0) Gecko/20100101 Firefox/72.0"

# EMOJIS = {'green_check': '&#x2705;',
#           'back': '&#x1F519;',
#           'fire': '&#x1f525;',
#           'eyes': '&#x1F440;',
#           'red_circle': '&#x1F534;',
#           'red_triangle_down': "&#x1F53B;",
#           'collision': "&#x1F4A5;",
#           'stop_sign': "&#x1F6D1;",
#           'orange_diamond': '&#x1F536;'}

EMOJIS = {'user_show': '&#x2705;',
          'new_show': "&#x1F6D1;",
          'return_show': '&#x1F536;'}


CACHE_KEY_PREFIX_USER = '_user_data'
CACHE_KEY_AIRDATES = 'shows_data'
CACHE_KEY_ENGINES = 'engines_data'


class TVShows:

    def __init__(self, airdates_hlp: 'AirdatesHelper'):
        self.airdates_hlp = airdates_hlp
        self.airdates_data, self.engines_data = self.airdates_hlp.get_airdates_data()

    def refresh_user_data(self, bot_user: BotUser):
        # self.airdates_data, self.engines_data = self.airdates_hlp.get_airdates_data()
        if bot_user.airdates_user:
            # self.airdates_hlp.get_airdates_user_data(bot_user.airdates_user)
            self.airdates_hlp.clear_user_data(bot_user.airdates_user)



    def get_engines(self):
        return self.engines_data

    def get_all_shows(self):
        return self.airdates_data

    def get_shows_day(self, day_str, bot_user: BotUser):
        """
        Get all shows of the specific date

        :param bot_user:
        :param day_str:
        """
        day_shows = {"date": day_str, "episodes": []}

        day = self.airdates_data.get(day_str, None)
        if day:
            episodes = deepcopy(day['episodes'])
            episodes = [{**ep, 'episode_date': day_str} for ep in episodes]
            day_shows['episodes'] = episodes

            if bot_user.airdates_user:
                airdates_user_data = self.airdates_hlp.get_airdates_user_data(bot_user.airdates_user)
                if day_shows['episodes']:
                    for ep in day_shows['episodes']:
                        if ep['show_id'] in airdates_user_data:
                            ep['is_user_show'] = 1

        return day_shows

    def get_user_shows_day(self, day_str, bot_user: BotUser):
        shows_day = self.get_shows_day(day_str, bot_user)

        if bot_user.airdates_user:
            episodes = [ep for ep in shows_day['episodes'] if ep.get('is_user_show', None)]
        else:
            episodes = [ep for ep in shows_day['episodes']]

        shows_day['episodes'] = episodes

        return shows_day

    def get_shows(self, day, bot_user: BotUser, user_only=True):
        day_str = day
        if day == 'today':
            day_str = date.today().strftime("%Y%m%d")
        elif day == 'yday':
            yesterday = date.today() - timedelta(days=1)
            day_str = yesterday.strftime("%Y%m%d")
        elif day == 'tmrw':
            tomorrow = date.today() + timedelta(days=1)
            day_str = tomorrow.strftime("%Y%m%d")
        else:
            pass

        if user_only:
            shows = self.get_user_shows_day(day_str, bot_user)
        else:
            shows = self.get_shows_day(day_str, bot_user)

        return shows

    def find_episode_by_episode_id(self, episode_id):
        show_id = episode_id.split('_', 1)[0]

        for day_key, day in self.airdates_data.items():
            found_episode = next((x for x in day['episodes'] if x['episode_id'] == episode_id), None)
            if found_episode:
                return {**found_episode, 'episode_date': day_key}

        return None

    def find_episodes_by_text(self, text):
        shows = []
        for day_key, day in self.airdates_data.items():
            shows += [{**ep, 'episode_date': day_key} for ep in day['episodes'] if text.lower() in ep['episode_name'].lower()]

        return shows



def manage_cache(func):
    def wrapper(self, *args, **kwargs):

        ret = func(self, *args, **kwargs)
        self.cache.close()
        return ret

    return wrapper


class AirdatesHelper:

    def __init__(self, data_path, cache_path, from_cache=True, local_data=False, download_if_notfound=False):
        self.data_path = data_path
        self.cache_path = cache_path
        self.from_cache = from_cache
        self.local_data = local_data
        self.download_if_notfound = download_if_notfound
        self._cache = None


    @property
    def cache(self):
        if not self._cache:
            self._cache = Cache(self.cache_path)

        return self._cache

    @manage_cache
    def get_airdates_data(self):
        shows_data = None
        engines_data = None

        if self.from_cache:
            shows_data = self.cache.get(CACHE_KEY_AIRDATES)
            engines_data = self.cache.get(CACHE_KEY_ENGINES)

        if not shows_data or not self.from_cache or not engines_data:
            shows_data_html = self._download_airdates_data()
            shows_data, engines_data = self._parse_airdates_data(shows_data_html)

            self.cache.set(CACHE_KEY_AIRDATES, shows_data, expire=60 * 60 * 24)
            self.cache.set(CACHE_KEY_ENGINES, engines_data, expire=60 * 60 * 24 * 30)

        return shows_data, engines_data

    @manage_cache
    def get_airdates_user_data(self, airdates_user):
        """
        same as function above
        :return:
        """
        if not airdates_user:
            return None

        cache_key = f"{CACHE_KEY_PREFIX_USER}{airdates_user}"
        user_data = None

        if self.from_cache:
            user_data = self.cache.get(cache_key)

        if not user_data or not self.from_cache:
            user_data_json = self._download_user_data(airdates_user)
            user_data = json.loads(user_data_json)

            # convert from list of objects to dict, 'id' will be the key (leaves id as attribute as well)
            user_data = {str(x['id']): x for x in user_data}

            self.cache.set(cache_key, user_data, expire=60 * 60 * 24)

        return user_data

    @manage_cache
    def clear_user_data(self, airdates_user):
        if not airdates_user:
            return None

        cache_key = f"{CACHE_KEY_PREFIX_USER}{airdates_user}"
        self.cache.delete(cache_key)


    def _download_airdates_data(self):
        filename = self.data_path + '/airdates.html'

        download_and_save = True

        if self.local_data:
            try:
                with open(filename, 'rt') as f:
                    return f.read()

            except Exception:
                print('file not found')
                download_and_save = self.download_if_notfound

        if download_and_save:
            url = AIRDATES_URL
            headers = {'accept': '*/*', 'user-agent': AIRDATES_UA}

            response = requests.get(url, headers=headers)

            logging.getLogger('ext_requests').info('Fetching Airdates main page\n' +
                                                   'Headers: ' + str(response.request.headers) + '\n' +
                                                   'URL: ' + str(response.request.url) + '\n')

            if response.status_code == 200:
                save_to_file(filename, response.content)
                return response.text
            else:
                logging.error("Connection Error Code: " + response.status_code)
                return None

        return None

    def _download_user_data(self, airdates_user):
        filename = self.data_path + "/" + airdates_user + '_airdates.txt'

        download_and_save = True

        if self.local_data:
            try:
                with open(filename, 'rt') as f:
                    return f.read()

            except Exception:
                print('file not found')
                download_and_save = self.download_if_notfound

        if download_and_save:
            url = AIRDATES_USER_URL + airdates_user
            headers = {'Accept': '*/*', 'User-Agent': AIRDATES_UA}

            response = requests.get(url, headers=headers)

            logging.getLogger('ext_requests').info(f'Fetching Airdates user data for {airdates_user}\n' +
                                                   'Headers: ' + str(response.request.headers) + '\n' +
                                                   'URL: ' + str(response.request.url) + '\n')

            if response.status_code == 200:
                save_to_file(filename, response.content)
                return response.text

            else:
                logging.error("Connection Error Code: " + response.status_code)
                return None

        return None

    def _parse_airdates_data(self, html_data):
        '''
        parse data into the array of dates, each item is date dictionary with the episodes of that date

        :param str html_data: main page html
        :return:
        '''

        soup = BeautifulSoup(html_data, 'html.parser')
        days_div = soup.select("div.day")

        days = {}
        for div in days_div:

            day_entries = div.find_all('div', {'class': 'entry'})
            episodes = []
            for x in day_entries:
                ep = {'show_id': str(x['data-series-id']),
                      'show_source': str(x['data-series-source']),
                      'episode_id': get_episode_id(str(x['data-series-id']), str(x.div.contents[0])),
                      'episode_name': str(x.div.contents[0])}

                if 'series-premiere' in x["class"]:
                    ep['series_prem'] = 1
                if 'season-premiere' in x["class"]:
                    ep['season_prem'] = 1

                episodes.append(ep)

            shows_date = str(div['data-date'])
            day = {'episodes': episodes}
            days[shows_date] = day

        engines = soup.find('script', text=re.compile("engines"))
        engines = re.findall(r'\{ .*?\ }', engines.text)
        engines = [demjson.decode(i) for i in engines]

        return days, engines


def get_episode_id(show_id, episode_name):
    episode_num = episode_name.split()[-1]
    return f"{show_id}_{episode_num}"


def format_episode_details(episode, engines):
    show_text = f'<b>{episode["episode_name"]}</b> (' + format_date(episode["episode_date"]) + ')'
    if episode.get('is_user_show', None):
        show_text = f"{EMOJIS['user_show']}&#160;{show_text}"
    show_text += '\n\n'

    for engine in engines:
        engine_show_url = engine['href'].replace('MONKEY', requests.utils.quote(episode['episode_name']), 1)
        engine_show_url = engine_show_url.replace('{WIKI_TITLE}', requests.utils.quote(episode['show_source']), 1)
        show_text += f'-- <a href="{engine_show_url}">{engine["name"]}</a>\n'

    return show_text


def format_show_text_main(show, show_date=False):
    show_text = '<b>' + show['name'] + '</b>'
    if show.get('series_prem', None):
        # show_text = f"{EMOJIS['new_show']}&#160;{show_text}&#160;{EMOJIS['new_show']}"
        show_text = f"{EMOJIS['new_show']}&#160;{show_text}"

    if show.get('season_prem', None):
        # show_text = f"{EMOJIS['return_show']}&#160;{show_text}&#160;{EMOJIS['return_show']}"
        show_text = f"{EMOJIS['return_show']}&#160;{show_text}"

    if show.get('is_user_show', None):
        # show_text = f"{EMOJIS['user_show']}&#160;{show_text}"
        show_text = f"{show_text}&#160;{EMOJIS['user_show']}&#160;"

    show_text += '\n'

    for episode in show['episodes']:
        ep_id = get_episode_id(show['id'], episode['name'])
        # show_text += f"<i>{episode['name']}</i> - /details_{ep_id}"
        show_text += f"{episode['name']} - /details_{ep_id}"

        if show_date:
            show_text += ' (' + format_date(episode['date']) + ')'
        show_text += '\n'

    return show_text


def format_shows_text(tv: TVShows, episodes, show_date=False):
    shows_episodes = group_episodes_by_show(episodes)
    shows_text = [format_show_text_main(i, show_date) for i in shows_episodes]

    return "\n".join(shows_text)


def format_date(day_str):
    date_obj = datetime.strptime(day_str, '%Y%m%d')
    return date_obj.strftime("%-d %b %Y")


def save_to_file(filename, data_binary):
    try:
        with open(filename, 'wb') as f:
            f.write(data_binary)
            f.close()

    except Exception:
        print('not found')


def format_footer(username):
    if username:
        return f"\n--------------------------------\nVisit {AIRDATES_URL}/u/{username} for more shows"
    else:
        return f"\n--------------------------------\nVisit {AIRDATES_URL} for more shows"


def group_episodes_by_show(episodes):
    shows = {}
    for ep in episodes:
        show_id = ep['show_id']
        show_name = " ".join(ep['episode_name'].split()[:-1])
        if not (show_id in shows):
            shows[show_id] = {'name': show_name, 'episodes': []}
            # shows[show_id] = {'name': ep['show_source'], 'episodes': []}

        if ep.get('series_prem', None):
            shows[show_id]['series_prem'] = 1

        if ep.get('season_prem', None):
            shows[show_id]['season_prem'] = 1

        if ep.get('is_user_show', None):
            shows[show_id]['is_user_show'] = 1

        shows[show_id]['episodes'].append({'id': ep['episode_id'], 'name': ep['episode_name'], 'date': ep['episode_date']})

    shows_list = []
    for show_key, show_val in shows.items():
        # reorder the keys so id will be the first
        new_obj = {k: v for k, v in ([('id', show_key)] + list(show_val.items()))}
        shows_list.append(new_obj)

    return shows_list
