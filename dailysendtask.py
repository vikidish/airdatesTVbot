from config import *

import telebot

from src.TVShows import *
from src.BotUser import *

bot = telebot.TeleBot(config.telegram_token)

tv = TVShows(AirdatesHelper(config.data_dir_path, config.cache_path, True, False, True))
engines = tv.get_engines()


def send_daily_shows():

    now = datetime.utcnow()
    botdbsql = BotUserStorageHelper(config.db_path, config.cache_path)
    users = botdbsql.get_daily_send_by_hour(now.hour)

    config.logger.info(f'Running daily send for {users}')
    for user in users:
        tg_user_id = user['tg_user_id']
        airdates_user = user['airdates_user']
        last_sent = user['last_sent']

        if last_sent:
            last_sent_dt = datetime.strptime(last_sent, '%Y-%m-%d %H:%M:%S.%f')
        else:
            last_sent_dt = datetime.strptime('1079-01-01 00:00:00.00', '%Y-%m-%d %H:%M:%S.%f')

        user_only = True if airdates_user else False

        # check last_sent, if sent in the current hour, do not send
        if now - last_sent_dt >= timedelta(hours=23) or now.hour - last_sent_dt.hour != 0:

            try:
                bot_user = BotUser(tg_user_id, airdates_user)
                shows = tv.get_shows('today', bot_user, user_only)

                user_text = f'{bot_user.airdates_user} ' if bot_user else ''
                reply_text = '{}Today\'s ({}) TV Shows:\n\n'.format(user_text, format_date(shows['date'])) \
                                 + format_shows_text(tv, shows['episodes'])

                bot.send_message(tg_user_id, reply_text + format_footer(bot_user.airdates_user), parse_mode='HTML')
                config.logger.info(f'sending daily for user {tg_user_id}')

                botdbsql.update_last_sent(tg_user_id, now)

            except Exception as ex:
                config.logger.error('Cannot send message: ' + str(ex))

if __name__ == "__main__":
    send_daily_shows()