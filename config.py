import logging
from logging.config import dictConfig

from dotenv import load_dotenv

import sys
import os
from pathlib import Path
import rootpath
import builtins

import sqlite3

DATA_DIR_PATH = "/data"
DB_FILENAME = "airdatesTVbotdb.sqlite"
MAIN_LOG_FILENAME = "mainlog.log"
DB_SCHEMA_VERSION = 1

CACHE_DIR = "cache"

LOG_DIR = '/var/log/airdatesTVbot'
LOG_FORMAT = "%(asctime)s {app} [%(thread)d] %(levelname)-5s %(name)s - %(message)s. [file=%(filename)s:%(lineno)d]"
LOG_LEVEL = "INFO"

USER_REFRESH_DAILY_LIMIT = 5


class Config:

    def __init__(self, root_path):
        self.root_path = root_path

        if sys.platform == "darwin" or is_docker():
            env_file = f"{self.root_path}/.dev.env"
        else:
            env_file = f"{self.root_path}/.env"

        load_dotenv(dotenv_path=env_file)

        self.data_dir_path = f"{root_path}{DATA_DIR_PATH}"
        self.db_path = f"{self.data_dir_path}/{DB_FILENAME}"

        if 'SKIP_DB_CHECK' in vars(builtins):
            print('skip check db')
            pass
        else:
            curr_db_schema_version = self.get_db_schema_version()
            if curr_db_schema_version != DB_SCHEMA_VERSION:
                sys.exit('DB Schema needs to be updated')

        self.cache_path = f"{self.data_dir_path}/{CACHE_DIR}"

        self.telegram_token = os.getenv("TELEGRAM_TOKEN")

        self.script_name = os.path.basename(sys.argv[0])
        self.log_path = f"{self.data_dir_path}/{MAIN_LOG_FILENAME}"

        if sys.platform == "darwin" or is_docker():
            self.log_dir_path = f"{self.data_dir_path}/log"
        else:
            self.log_dir_path = LOG_DIR

        # logging.root.handlers = []
        # noinspection PyArgumentList
        # logging.basicConfig(level=logging.INFO,
        #                     format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
        #                     handlers=[
        #                         logging.FileHandler(self.log_path),
        #                         logging.StreamHandler(sys.stdout)
        #                     ])
        #
        self._setup_loggers(self.log_dir_path, name="airdatesTVbot")
        self.logger = logging.getLogger()
        logging.getLogger('requests').setLevel(logging.INFO)

    def get_db_schema_version(self):

        check_stmt = 'PRAGMA user_version;'

        conn = sqlite3.connect(self.db_path, isolation_level=None,
                                           detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        conn.set_trace_callback(print)
        cur = conn.cursor()
        cur.execute(check_stmt)
        res = cur.fetchall()
        return res[0][0]




    def _setup_loggers(self, log_dir_path, name, level=LOG_LEVEL, fmt=LOG_FORMAT):

        formatted = fmt.format(app=name)

        if not os.path.exists(log_dir_path):
            os.makedirs(log_dir_path)

        LOGGING_CONFIG = {
            "version": 1,
            'disable_existing_loggers': False,
            "formatters": {
                'standard': {
                    'format': formatted
                }
            },
            "handlers": {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'standard',
                    'level': level,
                    'stream': 'ext://sys.stdout'
                },
                'file_main': {
                    'class': 'logging.FileHandler',
                    'level': level,
                    'filename': f'{log_dir_path}/main.log',
                    'formatter': 'standard',
                    'mode': 'a'
                },
                'file_refresh': {
                    'class': 'logging.FileHandler',
                    'filename': f'{log_dir_path}/refresh_requests.log',
                    'formatter': 'standard',
                    'mode': 'a'
                }
            },
            "loggers": {
                "": {  # root logger
                    'handlers': ['console', 'file_main'],
                    'level': level
                },
                "ext_requests": {
                    'handlers': ['console', 'file_refresh'],
                    'level': level,
                    "propagate": False
                }
            }
        }
        dictConfig(LOGGING_CONFIG)


def is_docker():
    proc_path = '/proc/self/cgroup'
    return (
        os.path.exists('/.dockerenv') or
        os.path.isfile(proc_path) and any('docker' in line for line in open(proc_path))
    )

path = rootpath.detect()
# print(path)
if not path:
    path = os.path.dirname(os.path.abspath(__file__))

config = Config(path)
