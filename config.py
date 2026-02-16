import logging
from logging.config import dictConfig

from dotenv import load_dotenv

import sys
import os
import builtins

import sqlite3

DB_FILENAME = "airdatesTVbotdb.sqlite"
MAIN_LOG_FILENAME = "mainlog.log"
DB_SCHEMA_VERSION = 1

CACHE_DIR = "cache"

LOG_DIR = '/var/log/airdatesTVbot'
LOG_FORMAT = "%(asctime)s {app} [%(thread)d] %(levelname)-5s %(name)s - %(message)s. [file=%(filename)s:%(lineno)d]"
LOG_LEVEL = "INFO"

USER_REFRESH_DAILY_LIMIT = 5


def is_docker():
    """Detect if running inside Docker container."""
    return (
        os.path.exists('/.dockerenv') or
        os.environ.get('DOCKER_CONTAINER', False)
    )


class Config:

    def __init__(self):
        # Determine root path (directory containing this file)
        self.root_path = os.path.dirname(os.path.abspath(__file__))

        # Load environment variables
        if is_docker():
            # In Docker, .env is passed via --env-file
            pass
        elif sys.platform == "darwin":
            load_dotenv(dotenv_path=f"{self.root_path}/.dev.env")
        else:
            load_dotenv(dotenv_path=f"{self.root_path}/.env")

        # Data directory: use /data in Docker, otherwise ./data relative to project
        if is_docker():
            self.data_dir_path = "/data"
        else:
            self.data_dir_path = f"{self.root_path}/data"

        self.db_path = f"{self.data_dir_path}/{DB_FILENAME}"
        self.cache_path = f"{self.data_dir_path}/{CACHE_DIR}"

        # Check DB schema version (skip during setup)
        if 'SKIP_DB_CHECK' not in vars(builtins):
            if os.path.exists(self.db_path):
                curr_db_schema_version = self.get_db_schema_version()
                if curr_db_schema_version != DB_SCHEMA_VERSION:
                    sys.exit('DB Schema needs to be updated')

        self.telegram_token = os.getenv("TELEGRAM_TOKEN")

        self.script_name = os.path.basename(sys.argv[0])
        self.log_path = f"{self.data_dir_path}/{MAIN_LOG_FILENAME}"

        # Log directory
        if is_docker() or sys.platform == "darwin":
            self.log_dir_path = f"{self.data_dir_path}/log"
        else:
            self.log_dir_path = LOG_DIR

        self._setup_loggers(self.log_dir_path, name="airdatesTVbot")
        self.logger = logging.getLogger()
        logging.getLogger('requests').setLevel(logging.INFO)

    def get_db_schema_version(self):
        check_stmt = 'PRAGMA user_version;'
        conn = sqlite3.connect(self.db_path, isolation_level=None,
                               detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cur = conn.cursor()
        cur.execute(check_stmt)
        res = cur.fetchall()
        conn.close()
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


config = Config()
