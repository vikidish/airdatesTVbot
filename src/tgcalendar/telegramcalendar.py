# A library that allows to create an inline calendar keyboard.
# Most of the code used is from unmonoqueteclea @
# https://github.com/unmonoqueteclea/calendar-telegram/blob/099e2c856fc6fbfeffe35bcb666e2800e41634ee/telegramcalendar.py


from telebot import types
import calendar


def create_calendar(year, month):
    markup = types.InlineKeyboardMarkup()
    calendar.setfirstweekday(6)
    # First row - Month and Year
    row = []
    row.append(types.InlineKeyboardButton(calendar.month_name[month] + " " + str(year), callback_data="calendar-ignore"))
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
                row.append(types.InlineKeyboardButton(str(day), callback_data="calendar-day-" + str(day)))
        markup.row(*row)
    # Last row - Buttons
    row = []
    row.append(types.InlineKeyboardButton("<", callback_data="calendar-previous-month"))
    row.append(types.InlineKeyboardButton("Today", callback_data="calendar-this-month"))
    row.append(types.InlineKeyboardButton(">", callback_data="calendar-next-month"))
    markup.row(*row)
    return markup
