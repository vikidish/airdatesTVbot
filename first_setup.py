import sqlite3
from config import *
import pathlib
import shutil

import argparse

parser = argparse.ArgumentParser()

parser.add_argument("-d", "--delete-db",
                    action="store_true", dest="delete_db", default=False,
                    help="delete existing user database and create a clean one")


def create_db(delete_exist=False):

    create_stmt = '''
    CREATE TABLE Users (
        id                  integer not null primary key autoincrement unique,
        tg_user_id          text not null unique,
        airdates_user       text,
        daily_enabled       integer,
        daily_hour          integer default 0,   
        last_sent           timestamp,
        is_admin            integer,
        daily_types         text
    );
    '''

    if delete_exist:
        create_stmt = '''
        DROP TABLE IF EXISTS Users;
        
        ''' + create_stmt

    conn = sqlite3.connect(config.db_path, isolation_level=None,
                                           detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.set_trace_callback(print)

    cur = conn.cursor()

    # Do some setup
    cur.executescript(create_stmt)

def clear_cache():
    path = pathlib.Path(config.cache_path)
    shutil.rmtree(path)


def main():

    args = parser.parse_args()

    # create data directory
    pathlib.Path(config.data_dir_path).mkdir(parents=True, exist_ok=True)

    # create database for users
    create_db(args.delete_db)


if __name__ == '__main__':
    main()
