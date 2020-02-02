# A library that allows to create an inline calendar keyboard.
# Most of the code used is from unmonoqueteclea @
# https://github.com/unmonoqueteclea/calendar-telegram/blob/099e2c856fc6fbfeffe35bcb666e2800e41634ee/telegramcalendar.py


from telebot import types
import calendar
from datetime import datetime


def create_calendar(year, month, today_mark=True):
    markup = types.InlineKeyboardMarkup()
    calendar.setfirstweekday(6)
    now = datetime.now()

    # First row - Month and Year
    row = []
    row.append(types.InlineKeyboardButton("🗓️ " + calendar.month_name[month] + " " + str(year), callback_data="calendar-ignore"))
    markup.row(*row)
    # Second row - Week Days
    week_days = ["S", "M", "T", "W", "T", "F", "S"]
    row = []
    for day in week_days:
        row.append(types.InlineKeyboardButton(day, callback_data="calendar-ignore"))
    markup.row(*row)

    my_calendar = calendar.monthcalendar(year, month)
    calendar.setfirstweekday(6)
    for week in my_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(types.InlineKeyboardButton(" ", callback_data="calendar-ignore"))
            else:
                day_mark = False
                date_obj = datetime(year, month, day)
                if today_mark:
                    if (now.year, now.month, now.day) == (year, month, day):
                        day_mark = True

                day_str = f'🔆{str(day)}' if day_mark else str(day)

                row.append(types.InlineKeyboardButton(day_str, callback_data="calendar-day-" + date_obj.strftime('%Y%m%d')))
        markup.row(*row)
    # Last row - Buttons
    row = []

    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1

    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1

    next_date = datetime(next_year, next_month, 1)
    prev_date = datetime(prev_year, prev_month, 1)

    row.append(types.InlineKeyboardButton("<", callback_data=f"calendar-month-{prev_date.strftime('%Y%m')}"))
    row.append(types.InlineKeyboardButton("Today", callback_data=f"calendar-month-{now.strftime('%Y%m')}"))
    row.append(types.InlineKeyboardButton(">", callback_data=f"calendar-month-{next_date.strftime('%Y%m')}"))
    markup.row(*row)
    return markup
