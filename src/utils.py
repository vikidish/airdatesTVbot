'''
A few useful functions/configs
'''

import rootpath
rootpath.append()

from config import *


COMMANDS_LIST = [{'command': 'start', 'desc': 'Welcome message'},
                 {'command': 'reg', 'desc': 'Start user registration'},
                 {'command': 'setairdatesuser', 'desc': 'Set/change airates.tv user'},
                 {'command': 'setdaily', 'desc': 'Send daily updates'},
                 {'command': 'settime', 'desc': 'Select when daily updates should be sent'},
                 {'command': 'setdailytype', 'desc': 'Choose types of daily updates'},
                 {'command': 'refresh', 'desc': 'Refresh the data from the airdates.tv website (limited to 5 times per day per user)'},
                 {'command': 'today', 'desc': 'Return today user shows'},
                 {'command': 'today_all', 'desc': 'Return all today shows'},
                 {'command': 'yday', 'desc': 'Return yesterday user shows'},
                 {'command': 'yday_all', 'desc': 'Return all yesterday shows'},
                 {'command': 'tmrw', 'desc': 'Return tomorrow user shows'},
                 {'command': 'tmrw_all', 'desc': 'Return all tomorrow shows'},
                 {'command': 'day', 'desc': 'Return the shows of the specific day'},
                 {'command': 'day_all', 'desc': 'Return all the shows of the specific day'}]


COMMAND_LENGTH = 10


def print_commands():
    for cmd in COMMANDS_LIST:
        spaces_num = COMMAND_LENGTH - len(cmd['command'])

        print(cmd['command'] + ' - ' + cmd['desc'])


print_commands()
