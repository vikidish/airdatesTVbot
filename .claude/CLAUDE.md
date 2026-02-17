# Project Memory

Instructions here apply to this project and are shared with team members.

## Context


## Post-Refactoring Architecture

### Entry Points
| File | Purpose |
|------|---------|
| `bot.py` | Main Telegram bot (long-polling, ~600 lines) |
| `dailysendtask.py` | Scheduled daily digest sender (run via cron/docker) |
| `app_setup.py` | Database setup and migration utility |
| `healthcheck.py` | Docker container health check |

### Core Modules (`src/`)

**TVShows.py** - Data fetching & formatting (~530 lines)
- `TVShows` - Main interface for show data queries
- `AirdatesHelper` - HTTP fetching and diskcache management
- Formatting functions: `format_shows_text()`, `format_footer()`, `format_date()`, etc.

**BotUser.py** - User storage (~290 lines)
- `BotUser` - User model with settings (daily_enabled, daily_types, airdates_user)
- `BotUserStorageHelper` - Thread/multiprocess-safe DB+cache operations
- Uses `@_manage_connection` decorator for SQLite lifecycle

**utils.py** - Bot command definitions (`COMMANDS_LIST`)

**tgcalendar/** - Telegram inline calendar keyboard component

### Data Layer
- **SQLite** (`data/airdatesTVbotdb.sqlite`) - User table with preferences
- **diskcache** (`data/cache/`) - Shows data, user show lists, refresh counters
- TTLs configurable via environment: `CACHE_SHOWS_TTL`, `CACHE_USER_TTL`, etc.

### Configuration (`config.py`)
- `Config` class singleton pattern (`config = Config()`)
- Environment detection: Docker (`/.dockerenv`) vs local (`.env`/`.dev.env`)
- Path management: `data_dir_path`, `cache_path`, `log_dir_path`
- Logging: dictConfig with file handlers for main.log and refresh_requests.log
- DB schema versioning via `PRAGMA user_version`

### Deployment
```
docker-compose.yml
├── bot (main service, restart: unless-stopped)
└── daily-task (profiles: [tasks], run via: docker compose run --rm daily-task)
```
- Multi-stage Dockerfile (python:3.11-slim-bookworm)
- Non-root user (`appuser`)
- Volume: `/data` for persistence
- Healthcheck: 60s interval, DB connectivity test

### Testing
- `tests/test_TVShows.py` - Unit tests for parsing/formatting
- `tests/test_BotUser.py` - User storage tests
- Test data: `tests/data/airdates.html`, `tests/data/v8i8k_airdates.txt`
- Run: `python3 -m unittest discover tests/ -v`

### Key Patterns
1. **Graceful shutdown** - Signal handlers in bot.py close cache connections
2. **Lazy cache init** - `@property` pattern for cache access
3. **Connection-per-request** - `@_manage_connection` decorator for SQLite
4. **Step handlers** - Telegram conversation state persisted to disk

---

## Development Guide

### Preferred Tools
```bash
# Package management (NOT pip directly)
uv pip install <package>
VIRTUAL_ENV=$(pwd)/venv uv pip install <package>

# Running the bot locally
venv/bin/python bot.py

# Running tests
venv/bin/python -m unittest discover tests/ -v

# Docker testing
docker compose build && docker compose up
docker compose run --rm daily-task  # Test daily sender

# Security checks
uvx safety check -r requirements.txt
```

### API Conventions

**Day parameters:** `'today'`, `'yday'`, `'tmrw'`, or `'YYYYMMDD'` string
```python
shows = tv.get_shows('today', bot_user, user_only=True)
shows = tv.get_shows('20200110', bot_user, user_only=False)
```

**Return structures:**
```python
# get_shows() returns:
{'date': '20200110', 'episodes': [...]}

# Episode dict keys:
{'show_id', 'episode_id', 'episode_name', 'episode_date',
 'is_user_show': 1,  # optional, if user follows
 'series_prem': 1,   # optional, if series premiere
 'season_prem': 1}   # optional, if season premiere
```

**BotUser initialization:**
```python
# With storage (normal usage in bot.py):
bot_user = BotUser(message.from_user.id, storage_hlp=user_storage_hlp)

# Without storage (e.g., in dailysendtask.py when you already have data):
bot_user = BotUser(tg_user_id, airdates_user='username')
```

### Gotchas & Debugging

1. **Import-time DB check** - Config validates DB schema on import. Use this hack in scripts that run before DB exists:
   ```python
   import builtins
   builtins.SKIP_DB_CHECK = 1
   from config import config
   ```

2. **Cache must be closed** - diskcache connections leak if not closed:
   ```python
   tv.airdates_hlp.close()
   user_storage_hlp.close()
   ```

3. **`@_manage_connection` injects `conn`** - First param after `self` is the connection:
   ```python
   @_manage_connection
   def some_method(self, conn, tg_user_id):  # conn is injected!
       cur = conn.cursor()
   ```

4. **daily_types is JSON** - Stored as string in SQLite, needs parsing:
   ```python
   daily_types = json.loads(user['daily_types'] or '[]')
   ```

5. **Cache TTLs are in seconds** - Not minutes! Defaults in config.py:
   - Shows: 6 hours (21600s)
   - User data: 24 hours (86400s)
   - Engines: 30 days (2592000s)

6. **Telegram exceptions** - Always catch `ApiTelegramException` separately:
   ```python
   except ApiTelegramException as api_ex:
       if api_ex.error_code == 403:  # User blocked bot
           ...
   except Exception as ex:
       ...
   ```

### Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Bot hangs on shutdown | Use signal handlers + `bot.stop_polling()` |
| "DB Schema needs update" on fresh install | Run `app_setup.py` first |
| Cache not updating | Check TTL; use `/refresh` command or clear `data/cache/` |
| Tests fail with "file not found" | Ensure `tests/data/` has test HTML files |
| Local dev uses wrong .env | macOS uses `.dev.env`, Linux uses `.env` |
| `infinity_polling()` blocks forever | That's expected; runs until signal received |

### Cache Keys Reference
```python
CACHE_KEY_AIRDATES = 'shows_data'        # All shows HTML parsed
CACHE_KEY_ENGINES = 'engines_data'       # Watch engine URLs
CACHE_KEY_PREFIX_USER = '_user_data'     # + username for user's shows
# Refresh counter: f'refresh_count_{tg_user_id}'
```

### Adding a New Bot Command
1. Add to `COMMANDS_LIST` in `src/utils.py`
2. Add handler in `bot.py`:
   ```python
   @bot.message_handler(commands=['newcmd'])
   def new_command(message):
       bot_user = BotUser(message.from_user.id, storage_hlp=user_storage_hlp)
       # ... your logic
       bot.send_message(message.chat.id, reply_text, parse_mode='HTML')
   ```
3. For callbacks: `@bot.callback_query_handler(func=lambda call: call.data.startswith('prefix-'))`

### Docker Rebuild Required
After changes to `Dockerfile`, `entrypoint.sh`, or `requirements.txt`:
```bash
docker compose build && docker compose up -d
```

