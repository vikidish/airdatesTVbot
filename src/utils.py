'''
A few useful functions/configs
'''

import rootpath
rootpath.append()

from config import *


COMMANDS_LIST = [{'command': 'start', 'desc': 'Welcome message'},
                 {'command': 'reg', 'desc': 'Start user registration'},
                 {'command': 'today', 'desc': 'Today user shows'},
                 {'command': 'today_all', 'desc': 'All today shows'},
                 {'command': 'yday', 'desc': 'Yesterday user shows'},
                 {'command': 'yday_all', 'desc': 'All yesterday shows'},
                 {'command': 'tmrw', 'desc': 'Tomorrow user shows'},
                 {'command': 'tmrw_all', 'desc': 'All tomorrow shows'},
                 {'command': 'day', 'desc': 'Shows of the specific day'},
                 {'command': 'day_all', 'desc': 'All the shows of the specific day'},
                 {'command': 'new', 'desc': 'New shows this week'},
                 {'command': 'new_next', 'desc': 'New shows last week'},
                 {'command': 'new_prev', 'desc': 'New shows next week'},
                 {'command': 'return', 'desc': 'Returning shows this week'},
                 {'command': 'return_prev', 'desc': 'Returning shows last week'},
                 {'command': 'return_next', 'desc': 'Returning shows next week'},
                 {'command': 'setairdatesuser', 'desc': 'Set/change airates.tv user'},
                 {'command': 'setdaily', 'desc': 'Send daily updates'},
                 {'command': 'settime', 'desc': 'Select when daily updates should be sent'},
                 {'command': 'setdailytype', 'desc': 'Choose types of daily updates'},
                 {'command': 'refresh', 'desc': 'Refresh the data from the airdates.tv website (limited to 5 times per day per user)'}
                 ]


COMMAND_LENGTH = 10


def print_commands():
    for cmd in COMMANDS_LIST:
        spaces_num = COMMAND_LENGTH - len(cmd['command'])

        print(cmd['command'] + ' - ' + cmd['desc'])


print_commands()
