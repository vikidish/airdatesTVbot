
# import logging
# logging.basicConfig(level=logging.DEBUG)

import traceback
from datetime import date, timedelta, datetime
import time
from src.tgcalendar.telegramcalendar import create_calendar

import telebot

from config import *
from src.TVShows import *
from src.BotUser import *



def main():

    # raise RuntimeError()
    current_shown_dates = {}
    current_command = {}

    bot = telebot.TeleBot(config.telegram_token)

    tv = TVShows(AirdatesHelper(config.data_dir_path, config.cache_path, True, False, True))
    engines = tv.engines_data

    # thread safe and multiprocess safe, can be a single instance
    user_storage_hlp = BotUserStorageHelper(config.db_path, config.cache_path)

    @bot.message_handler(commands=['start'])
    def send_welcome(message):

        try:

            username = message.from_user.username

            user_text = f"Greetings {username}!\n\n"
            reply_text = user_text + "Welcome to airdatesTVbot. This bot will send you your favorite shows based on information provided by airdates.tv website.\n\n" \
                         "To enjoy all the features of the bot you might want to register on airdates.tv and provide your airdates nickname to the bot. Registering on airdates.tv wll allow you to monitor your favorite shows both on the website and in the bot.\n\n" \
                         "To start the registration please use command /reg\n" \
                         "If you want to change your details provided in the registration, please use the commands:\n/setairdatesuser\n/setdaily\n/settime\n\n" \
                        "Or just click /today or /today_all to see today's TV shows.\nType the search query and press send to search for specific shows.\n\n" \
                        "New shows are marked " + EMOJIS['new_show'] + " and returning shows marked " + EMOJIS['return_show'] + \
                        " Near your shows you will see the checkmark " + EMOJIS['user_show']

            bot.send_message(message.chat.id, reply_text, parse_mode='HTML')

            bot_user = BotUser(message.from_user.id, storage_hlp=user_storage_hlp)
            bot_user.save_tg_user()

            print(message)

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()


    @bot.message_handler(commands=['reg'])
    def register(message):

        try:
            bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)

            keyboard = telebot.types.InlineKeyboardMarkup()
            key_yes = telebot.types.InlineKeyboardButton(text='Yes', callback_data='reg-airdates-user-yes')
            key_no = telebot.types.InlineKeyboardButton(text='No, Next', callback_data='reg-airdates-user-no')
            key_cancel = telebot.types.InlineKeyboardButton(text='Cancel', callback_data='reg-cancel')
            keyboard.row(key_yes, key_no, key_cancel)

            bot.send_message(message.chat.id, "The registration will allow you to subscribe to daily updates and get personalized digests. Do you want to add your airdates user? Please, note that it'll override previosly registered one", reply_markup=keyboard)

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()


    @bot.callback_query_handler(func=lambda call: call.data is not None and call.data.startswith('reg-airdates-user'))
    def get_reg_airdates_answer(call):

        try:
            if call.data == 'reg-airdates-user-yes':
                # ask for the name, next step get it
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='Please write you airdates username:')
                bot.register_next_step_handler(call.message, update_airdates_user)

            elif call.data == 'reg-airdates-user-no':
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Ok, let's proceed to the next step")
                ask_daily_send(call.message)

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()


    def update_airdates_user(message, is_step=True):
        airdates_username = message.text

        try:
            bot_user = BotUser(message.from_user.id, storage_hlp=user_storage_hlp)
            bot_user.register_airdates_user(airdates_username)
            msg = bot.send_message(message.chat.id, "The user was successfully updated!")
            if is_step:
                ask_daily_send(msg)

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()


    def ask_daily_send(message):

        try:
            keyboard = telebot.types.InlineKeyboardMarkup()
            key_yes = telebot.types.InlineKeyboardButton(text='Yes', callback_data='reg-daily-yes')
            key_no = telebot.types.InlineKeyboardButton(text='No', callback_data='reg-daily-no')
            key_cancel = telebot.types.InlineKeyboardButton(text='Cancel', callback_data='reg-cancel')

            keyboard.row(key_yes, key_no, key_cancel)

            bot.send_message(message.chat.id, "Would you like to receive daily updates? The update time is set by default to 00:00 UTC, you will be later able to change it with /settime command", reply_markup=keyboard)

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()

    @bot.callback_query_handler(func=lambda call: call.data is not None and call.data.startswith('reg-daily'))
    def get_reg_daily_answer(call):

        try:
            if call.data == 'reg-daily-yes':
                daily_enabled = True
                text = 'You will receive the daily updates!\n\nYou can change this setting later with the command /setdaily'
            else:
                daily_enabled = False
                text = 'Ok, no daily updates.\n\nYou can change this setting later with the command /setdaily'

            bot_user = BotUser(call.from_user.id, storage_hlp=user_storage_hlp)
            bot_user.update_daily_enabled(daily_enabled=daily_enabled)

            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text)
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()


    @bot.callback_query_handler(func=lambda call: call.data is not None and call.data.startswith('reg-cancel'))
    def cancel_registration(call):

        try:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='''Registration is cancelled. You can start over any time by using the /reg command.''')
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()


    @bot.message_handler(commands=['setdaily'])
    def set_daily(message):

        try:
            keyboard = telebot.types.InlineKeyboardMarkup()
            key_yes = telebot.types.InlineKeyboardButton(text='Yes', callback_data='setdaily-yes')
            key_no = telebot.types.InlineKeyboardButton(text='No', callback_data='setdaily-no')
            key_cancel = telebot.types.InlineKeyboardButton(text='Cancel', callback_data='setdaily-cancel')
            keyboard.row(key_yes, key_no, key_cancel)

            bot.send_message(message.chat.id, "Would you like to receive the daily updates of your shows that are screened today (you will receive all the shows in case you're not registered)?", reply_markup=keyboard)

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()

    @bot.callback_query_handler(func=lambda call: call.data is not None and call.data.startswith('setdaily-'))
    def set_daily_answer(call):

        try:
            if call.data == 'setdaily-yes':
                bot_user = BotUser(call.from_user.id, storage_hlp=user_storage_hlp)
                bot_user.update_daily_enabled(True)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='You will receive the daily updates!')

            elif call.data == 'setdaily-no':
                bot_user = BotUser(call.from_user.id, storage_hlp=user_storage_hlp)
                bot_user.update_daily_enabled(False)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Ok, no daily updates")

            else:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Ok, ok, no touching")

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()


    @bot.message_handler(commands=['settime'])
    def set_daily_hour(message):

        try:
            keyboard = telebot.types.InlineKeyboardMarkup()

            hour = 0
            for i in range(0, 4):
                hour_button_row = []
                for j in range(0, 6):
                    hour_button_row.append(telebot.types.InlineKeyboardButton(f'{hour}:00', callback_data=f"settime-{hour}"))
                    hour += 1
                keyboard.row(*hour_button_row)

            bot.send_message(message.chat.id, "Please, choose your preferred hour (UTC time) for daily updates", reply_markup=keyboard)

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()


    @bot.callback_query_handler(func=lambda call: call.data is not None and call.data.startswith('settime-'))
    def set_daily_hour_answer(call):

        try:
            hour = int(call.data.split('settime-')[1])
            bot_user = BotUser(call.from_user.id, storage_hlp=user_storage_hlp)
            bot_user.update_daily_hour(hour)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f'Your daily updates is set at {hour}:00 UTC time!')

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()


    def format_daily_type_keyboard(bot_user: BotUser):

        keyboard = telebot.types.InlineKeyboardMarkup()

        daily_types = ['yday', 'today', 'tmrw']
        daily_types_row = []
        for daily_type in daily_types:
            btn_emoji = '✅' if daily_type in bot_user.daily_types else '❌'
            daily_type_action = 'uncheck' if daily_type in bot_user.daily_types else 'check'
            btn_text = f'{btn_emoji} ' + get_day_text_by_type(daily_type)

            daily_types_btn = telebot.types.InlineKeyboardButton(btn_text, callback_data=f'setdailytype-{daily_type}-{daily_type_action}')
            daily_types_row.append(daily_types_btn)

        keyboard.row(*daily_types_row)
        return keyboard


    @bot.message_handler(commands=['setdailytype'])
    def set_daily_type(message):

        try:
            bot_user = BotUser(message.from_user.id, storage_hlp=user_storage_hlp)

            if not bot_user.daily_enabled:
                bot.send_message(message.chat.id, "To choose your preferred types of updates please enable your daily updates first - /setdaily")
                return

            keyboard = format_daily_type_keyboard(bot_user)
            bot.send_message(message.chat.id, "Please, choose your preferred types of updates you would like to receive every day:", reply_markup=keyboard)

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()


    @bot.callback_query_handler(func=lambda call: call.data is not None and call.data.startswith('setdailytype-'))
    def set_daily_hour_answer(call):

        try:
            daily_type = call.data.split('-')[1]
            daily_type_action = call.data.split('-')[2]

            bot_user = BotUser(call.from_user.id, storage_hlp=user_storage_hlp)

            user_daily_types = bot_user.daily_types
            if daily_type in user_daily_types:
                if daily_type_action == 'uncheck':
                    user_daily_types.remove(daily_type)
            else:
                if daily_type_action == 'check':
                    user_daily_types.append(daily_type)

            bot_user.update_daily_types(user_daily_types)

            keyboard = format_daily_type_keyboard(bot_user)

            bot.edit_message_text("Please, choose your preferred types of updates you would like to receive every day:", call.from_user.id, call.message.message_id, reply_markup=keyboard)
            bot.answer_callback_query(call.id, text="")

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()


    @bot.message_handler(commands=['setairdatesuser'])
    def set_airdates_user(message):

        try:
            bot.send_message(message.chat.id, "Please write you airdates username:")
            bot.register_next_step_handler(message, update_airdates_user, is_step=False)

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()


    @bot.message_handler(commands=['today', 'today_all', 'yday', 'yday_all', 'tmrw', 'tmrw_all'])
    def send_shows(message):

        try:
            user_only = True
            day_param = 'today'
            if '_all' in message.text:
                user_only = False
            if 'yday' in message.text:
                day_param = 'yday'
            elif 'tmrw' in message.text:
                day_param = 'tmrw'

            bot_user = BotUser(message.from_user.id, storage_hlp=user_storage_hlp)
            shows = tv.get_shows(day_param, bot_user, user_only)

            header_text = format_show_text_header(day_param, bot_user.airdates_user, shows['date'], not user_only)
            reply_text = header_text + format_shows_text(shows['episodes'])

            bot.send_message(message.chat.id, reply_text + format_footer(bot_user.airdates_user), parse_mode='HTML')

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()

    @bot.message_handler(commands=['new', 'return', 'new_prev', 'return_prev', 'new_next', 'return_next'])
    def send_new_shows(message):

        try:

            new_type = 'series'
            new_text = 'Show Premiers'
            if 'return' in message.text:
                new_type = 'season'
                new_text = 'Returning Shows'

            interval = 'week'
            if 'prev' in message.text:
                interval = 'prev'
            elif 'next' in message.text:
                interval = 'next'

            bot_user = BotUser(message.from_user.id, storage_hlp=user_storage_hlp)
            shows = tv.get_new_shows(interval, new_type, bot_user)

            header_text = f'Here are the {new_text} this week:\n\n'
            reply_text = header_text + format_shows_days_text(shows)

            bot.send_message(message.chat.id, reply_text + format_footer(), parse_mode='HTML')

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()


    @bot.message_handler(func=lambda message: message.text is not None and message.text.startswith('/details'))
    def send_episode_details(message):

        try:
            bot_user = BotUser(message.from_user.id, storage_hlp=user_storage_hlp)

            episode_id = message.text.split('_', 1)[-1]
            episode = tv.find_episode_by_episode_id(episode_id)

            if episode:
                reply_text = 'Details of episode \n' + format_episode_details(episode, engines)
            else:
                reply_text = 'Sorry, cannot find episode'

            bot.send_message(message.chat.id, reply_text + format_footer(bot_user.airdates_user), parse_mode='HTML')

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()



    @bot.message_handler(commands=['refresh'])
    def refresh_data(message):
        try:
            bot_user = BotUser(message.from_user.id, storage_hlp=user_storage_hlp)

            if bot_user.airdates_user:
                refresh_count = bot_user.get_refresh_count()
                # print(f"count={refresh_count}")
                if refresh_count < USER_REFRESH_DAILY_LIMIT:
                    tv.refresh_user_data(bot_user)
                    new_count = bot_user.update_refresh_count()
                    # print(f"new count={new_count}")

                    if USER_REFRESH_DAILY_LIMIT-new_count > 0:
                        more_text = f"you have {USER_REFRESH_DAILY_LIMIT-new_count} more refresh(es) today"
                    else:
                        more_text = f"you have no more refreshes today"

                    reply_text = f'Data refreshed, {more_text}'

                else:
                    reply_text = f'Refresh limit of {USER_REFRESH_DAILY_LIMIT} times per day reached, please try again tomorrow'
            else:
                reply_text = 'No airdates user found, nothing to refresh'

        except Exception as ex:
            config.logger.error('Something went wrong: ' + str(ex))
            traceback.print_exc()
            reply_text = 'Sorry, something went wrong'

        bot.send_message(message.chat.id, reply_text, parse_mode='HTML')


    @bot.message_handler(commands=['reset'])
    def reset_refresh_count(message):
        try:
            bot_user = BotUser(message.from_user.id, storage_hlp=user_storage_hlp)
            bot_user.reset_refresh_count()
            reply_text = 'Done'

        except Exception as ex:
            config.logger.error('Something went wrong: ' + str(ex))
            traceback.print_exc()
            reply_text = 'Sorry, something went wrong'

        bot.send_message(message.chat.id, reply_text, parse_mode='HTML')



    @bot.message_handler(commands=['day', 'day_all'])
    def get_calendar(message):

        try:
            now = datetime.now()
            chat_id = message.chat.id
            date = (now.year, now.month)
            current_shown_dates[chat_id] = date  # Saving the current date in a dict
            current_command[chat_id] = message.text
            markup = create_calendar(now.year, now.month)
            bot.send_message(message.chat.id, "Please, choose a date", reply_markup=markup)

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()



    @bot.callback_query_handler(func=lambda call: call.data == 'calendar-next-month')
    def next_month(call):

        try:
            chat_id = call.message.chat.id
            saved_date = current_shown_dates.get(chat_id, None)
            if saved_date is not None:
                year, month = saved_date
                month += 1
                if month > 12:
                    month = 1
                    year += 1
                date = (year, month)
                current_shown_dates[chat_id] = date
                markup = create_calendar(year, month)
                bot.edit_message_text("Please, choose a date", call.from_user.id, call.message.message_id, reply_markup=markup)
                bot.answer_callback_query(call.id, text="")
            else:
                # Do something to inform of the error
                pass

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()


    @bot.callback_query_handler(func=lambda call: call.data == 'calendar-previous-month')
    def previous_month(call):

        try:
            chat_id = call.message.chat.id
            saved_date = current_shown_dates.get(chat_id, None)
            if saved_date is not None:
                year, month = saved_date
                month -= 1
                if month < 1:
                    month = 12
                    year -= 1
                date = (year, month)
                current_shown_dates[chat_id] = date
                markup = create_calendar(year, month)
                bot.edit_message_text("Please, choose a date", call.from_user.id, call.message.message_id, reply_markup=markup)
                bot.answer_callback_query(call.id, text="")
            else:
                # Do something to inform of the error
                pass

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()


    @bot.callback_query_handler(func=lambda call: call.data == 'calendar-this-month')
    def this_month(call):

        try:
            chat_id = call.message.chat.id

            now = datetime.now()  # Current date
            date = (now.year, now.month)
            saved_date = current_shown_dates.get(chat_id, None)
            if saved_date is not None:
                if not date == saved_date:

                    current_shown_dates[chat_id] = date  # Saving the current date in a dict
                    markup = create_calendar(now.year, now.month)
                    bot.edit_message_text("Please, choose a date", call.from_user.id, call.message.message_id, reply_markup=markup)
                    bot.answer_callback_query(call.id, text="")

            else:
                # Do something to inform of the error
                pass

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()


    @bot.callback_query_handler(func=lambda call: call.data[0:13] == 'calendar-day-')
    def send_shows_day(call):

        chat_id = call.message.chat.id

        user_only = True
        all_text = ''
        if '_all' in current_command.get(chat_id, ''):
            user_only = False
            all_text = ' ALL'

        try:
            chat_id = call.message.chat.id
            saved_date = current_shown_dates.get(chat_id, None)
            if saved_date is not None:
                day = call.data[13:]
                selected_date = datetime(int(saved_date[0]), int(saved_date[1]), int(day), 0, 0, 0)
                day_str = selected_date.strftime("%Y%m%d")

                bot_user = BotUser(call.from_user.id, storage_hlp=user_storage_hlp)
                shows = tv.get_shows(day_str, bot_user, user_only)

                user_text = f'{bot_user.airdates_user}' if bot_user else ''
                reply_text = '{}\'s ({}){} TV Shows:\n\n'.format(user_text, format_date(shows['date']), all_text) \
                             + format_shows_text(shows['episodes'])

                # current_command[chat_id] = None
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=reply_text + format_footer(bot_user.airdates_user), parse_mode='HTML')
                # bot.send_message(chat_id, reply_text + format_footer(bot_user.airdates_user), parse_mode='HTML')
                bot.answer_callback_query(call.id, text="")

            else:
                # Do something to inform of the error
                pass

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()



    @bot.callback_query_handler(func=lambda call: call.data == 'calendar-ignore')
    def ignore_calendar(call):

        try:
            bot.answer_callback_query(call.id, text="")
        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()


    # should be the last - default, catch all input
    @bot.message_handler(func=lambda m: True)
    def search_shows(message):

        try:
            bot_user = BotUser(message.from_user.id, storage_hlp=user_storage_hlp)

            if len(message.text.strip()) < 3:
                reply_text = f"'{message.text}' is too short, please provide at least 3 letters"

            elif message.text.strip() in ['the', 'ing', 'ion', 'tion', 'ers']:
                reply_text = f"'{message.text}' is too common, please refine the search"

            else:
                episodes = tv.find_episodes_by_text(message.text)

                if episodes:
                    reply_text = f"We found the following TV Shows for '{message.text}':\n\n" \
                                 + format_shows_text(episodes, True)
                else:
                    reply_text = f"No shows with '{message.text}' in name"
                # reply_text = '&#x1F61C;'

            bot.send_message(message.chat.id, reply_text + format_footer(bot_user.airdates_user), parse_mode='HTML')

        except Exception as ex:
            config.logger.error('Cannot send message: ' + str(ex))
            traceback.print_exc()

    try:
        # Enable saving next step handlers to file "./.handlers-saves/step.save".
        # Delay=2 means that after any change in next step handlers (e.g. calling register_next_step_handler())
        # saving will happen after delay 2 seconds.
        bot.enable_save_next_step_handlers(delay=2, filename=f'{config.data_dir_path}/.handlers-saves/step.save')

        # Load next_step_handlers from save file (default "./.handlers-saves/step.save")
        # WARNING It will work only if enable_save_next_step_handlers was called!
        bot.load_next_step_handlers(filename=f'{config.data_dir_path}/.handlers-saves/step.save')

    except Exception as ex:
        config.logger.error('Cannot load next step handlers: ' + str(ex) + ' Traceback: ' + traceback.format_exc())
        traceback.print_exc()


    bot.polling(none_stop=True, interval=0)

if __name__ == "__main__":
    main()







