import sqlite3
import pathlib
import shutil
import argparse

import builtins

builtins.SKIP_DB_CHECK = 1
from config import *


parser = argparse.ArgumentParser()

parser.add_argument("-d", "--delete-db",
                    action="store_true", dest="delete_db", default=False,
                    help="delete existing user database and create a clean one")

MIGRATE_STMTS = [ 0 ]

MIGRATE_STMTS[0] = '''
BEGIN TRANSACTION;
CREATE TABLE temp_Users_534011718
(
        id                  integer not null primary key autoincrement unique,
        tg_user_id          text not null unique,
        airdates_user       text,
        daily_enabled       integer,
        daily_hour          integer default 0,   
        last_sent           timestamp,
        is_admin            integer DEFAULT 0,
        daily_types         text DEFAULT '["today"]'

);
INSERT INTO temp_Users_534011718 (id,tg_user_id,airdates_user,daily_enabled,daily_hour,last_sent,is_admin,daily_types) SELECT id,tg_user_id,airdates_user,daily_enabled,daily_hour,last_sent,0 AS is_admin,'["today"]' AS daily_types FROM Users;
DROP TABLE Users;
ALTER TABLE temp_Users_534011718 RENAME TO Users;
COMMIT TRANSACTION;
'''

def create_db(delete_exist=False):

    create_stmt = '''
    CREATE TABLE Users (
        id                  integer not null primary key autoincrement unique,
        tg_user_id          text not null unique,
        airdates_user       text,
        daily_enabled       integer,
        daily_hour          integer default 0,   
        last_sent           timestamp,
        is_admin            integer DEFAULT 0,
        daily_types         text DEFAULT ["today"]

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
    cur.executescript(create_stmt)


def migrate_db(to_version=DB_SCHEMA_VERSION):

    from_version = config.get_db_schema_version()

    if from_version > to_version:
        sys.exit('DB Rollback should be done manually')

    else:
        conn = sqlite3.connect(config.db_path, isolation_level=None,
                                           detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        conn.set_trace_callback(print)
        cur = conn.cursor()

        for migration in range(from_version, to_version, 1):
            migrate_stmt = MIGRATE_STMTS[migration]
            cur.executescript(migrate_stmt)
            cur.execute(f"PRAGMA user_version = {migration+1}")


def clear_cache():
    path = pathlib.Path(config.cache_path)
    shutil.rmtree(path)


def main():

    args = parser.parse_args()

    # create data directory
    pathlib.Path(config.data_dir_path).mkdir(parents=True, exist_ok=True)

    # create database for users
    try:
        create_db(args.delete_db)
    except sqlite3.OperationalError as sqlex:
        print('db cannot be created', sqlex)

    migrate_db()


if __name__ == '__main__':
    main()
