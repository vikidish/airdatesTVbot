from datetime import datetime, timedelta
import json

import telebot
from telebot.apihelper import ApiTelegramException

from config import config
from src.TVShows import (
    TVShows, AirdatesHelper, format_show_text_header,
    format_shows_text, format_footer
)
from src.BotUser import BotUser, BotUserStorageHelper

bot = telebot.TeleBot(config.telegram_token)

tv = TVShows(AirdatesHelper(
    config.data_dir_path, config.cache_path,
    from_cache=True, local_data=False, download_if_notfound=True,
    shows_ttl=config.cache_shows_ttl,
    user_ttl=config.cache_user_ttl,
    engines_ttl=config.cache_engines_ttl
))
engines = tv.engines_data


def send_daily_shows():
    now = datetime.utcnow()
    botdbsql = BotUserStorageHelper(
        config.db_path, config.cache_path,
        refresh_ttl=config.cache_refresh_ttl
    )
    users = botdbsql.get_daily_send_by_hour(now.hour)

    config.logger.info(f'Running daily send for {len(users)} users at hour {now.hour}')

    for user in users:
        tg_user_id = user['tg_user_id']
        airdates_user = user['airdates_user']
        last_sent = user['last_sent']
        daily_types = json.loads(user['daily_types'])

        if last_sent:
            last_sent_dt = datetime.strptime(last_sent, '%Y-%m-%d %H:%M:%S.%f')
        else:
            last_sent_dt = datetime.strptime('1979-01-01 00:00:00.00', '%Y-%m-%d %H:%M:%S.%f')

        user_only = True if airdates_user else False

        # check last_sent, if sent in the current hour, do not send
        if now - last_sent_dt >= timedelta(hours=23) or now.hour - last_sent_dt.hour != 0:

            try:
                bot_user = BotUser(tg_user_id, airdates_user)

                for daily_type in daily_types:
                    shows = tv.get_shows(daily_type, bot_user, user_only)

                    header_text = format_show_text_header(daily_type, bot_user.airdates_user, shows['date'], not user_only)
                    reply_text = header_text + format_shows_text(shows['episodes'])

                    bot.send_message(tg_user_id, reply_text + format_footer(bot_user.airdates_user), parse_mode='HTML')

                config.logger.info(f'Sent daily digest to user {tg_user_id}')
                botdbsql.update_last_sent(tg_user_id, now)

            except ApiTelegramException as api_ex:
                # Handle blocked users, deactivated accounts, etc.
                config.logger.error(f'Telegram API error for user {tg_user_id}: {api_ex}')
                if api_ex.error_code == 403:
                    config.logger.warning(f'User {tg_user_id} has blocked the bot or account is deactivated')
            except Exception as ex:
                config.logger.error(f'Cannot send message to {tg_user_id}: {ex}')

    # Cleanup
    botdbsql.close()
    tv.airdates_hlp.close()


if __name__ == "__main__":
    send_daily_shows()
