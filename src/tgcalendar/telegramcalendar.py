"""Inline calendar keyboard for Telegram bots.

Based on code from unmonoqueteclea:
https://github.com/unmonoqueteclea/calendar-telegram
"""

from __future__ import annotations

import calendar
from datetime import datetime

from telebot import types


def create_calendar(
    year: int,
    month: int,
    today_mark: bool = True
) -> types.InlineKeyboardMarkup:
    """Create an inline calendar keyboard for the given month.

    Args:
        year: The year to display
        month: The month to display (1-12)
        today_mark: Whether to mark today's date

    Returns:
        InlineKeyboardMarkup with calendar layout
    """
    markup = types.InlineKeyboardMarkup()
    calendar.setfirstweekday(6)  # Start week on Sunday
    now = datetime.now()

    # First row - Month and Year header
    header = types.InlineKeyboardButton(
        f"🗓️ {calendar.month_name[month]} {year}",
        callback_data="calendar-ignore"
    )
    markup.row(header)

    # Second row - Week day headers
    week_days = ["S", "M", "T", "W", "T", "F", "S"]
    day_buttons = [
        types.InlineKeyboardButton(day, callback_data="calendar-ignore")
        for day in week_days
    ]
    markup.row(*day_buttons)

    # Calendar days
    my_calendar = calendar.monthcalendar(year, month)
    for week in my_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(types.InlineKeyboardButton(" ", callback_data="calendar-ignore"))
            else:
                # Mark today
                is_today = today_mark and (now.year, now.month, now.day) == (year, month, day)
                day_str = f'🔆{day}' if is_today else str(day)

                date_obj = datetime(year, month, day)
                callback_data = f"calendar-day-{date_obj.strftime('%Y%m%d')}"
                row.append(types.InlineKeyboardButton(day_str, callback_data=callback_data))
        markup.row(*row)

    # Navigation row
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

    prev_date = datetime(prev_year, prev_month, 1)
    next_date = datetime(next_year, next_month, 1)

    nav_row = [
        types.InlineKeyboardButton("<", callback_data=f"calendar-month-{prev_date.strftime('%Y%m')}"),
        types.InlineKeyboardButton("Today", callback_data=f"calendar-month-{now.strftime('%Y%m')}"),
        types.InlineKeyboardButton(">", callback_data=f"calendar-month-{next_date.strftime('%Y%m')}"),
    ]
    markup.row(*nav_row)

    return markup
