# airdatesTVbot Refactoring Plan

## Overview

This document outlines the 5-step incremental refactoring plan for modernizing the airdatesTVbot Telegram bot.

---

## Initial Analysis

### Outdated Dependencies (Found)

| Package | Old Version | Target Version | Severity |
|---------|-------------|----------------|----------|
| `pyTelegramBotAPI` | 3.6.6 | 4.14+ | **Critical** |
| `Python` | 3.7.6 | 3.11+ | **Critical** |
| `demjson` | 2.2.4 | Removed (abandoned) | **Critical** |
| `requests` | 2.22.0 | 2.31+ | Medium |
| `diskcache` | 4.1.0 | 5.6+ | Medium |
| `beautifulsoup4` | 4.8.2 | 4.12+ | Low |
| `python-dotenv` | 0.10.5 | 1.0+ | Low |
| Base image | `buster` (EOL) | `bookworm` | **Critical** |

### Structural Issues (Found)

- Monolithic 560-line `main()` function
- Star imports (`from config import *`)
- No type hints
- Raw SQL without ORM
- Synchronous I/O throughout
- Mix of `print()` and logging
- Debug trace callbacks in production code
- Broken Dockerfile (non-existent user)

---

## Step 1: Fix Critical Breakages ✅ COMPLETE

**Goal**: Get the bot running on modern Python

### Changes Made
- [x] Updated `Dockerfile` to Python 3.11-slim-bookworm
- [x] Fixed user creation (`useradd appuser`)
- [x] Moved DB setup to runtime (entrypoint.sh)
- [x] Replaced `demjson` with stdlib `json` + regex parser
- [x] Updated `requirements.txt` with modern versions
- [x] Fixed `none_stop` → `non_stop` deprecation
- [x] Created `docker-compose.yml`
- [x] Created `.dockerignore`
- [x] Fixed `config.py` path handling for Docker

### Files Changed
- `Dockerfile`
- `requirements.txt`
- `config.py`
- `bot.py`
- `src/TVShows.py`
- `entrypoint.sh` (new)
- `docker-compose.yml` (new)
- `.dockerignore` (new)

---

## Step 2: Upgrade pyTelegramBotAPI to 4.x ✅ COMPLETE

**Goal**: Full compatibility with modern Telegram Bot API library

### Changes Made
- [x] Added `ApiTelegramException` import for proper error handling
- [x] Added graceful shutdown (SIGINT/SIGTERM handlers)
- [x] Changed `bot.polling()` → `bot.infinity_polling()` (auto-reconnect)
- [x] Added `threaded=True` to TeleBot constructor
- [x] Fixed duplicate function names
- [x] Ensured handlers directory exists before save
- [x] Replaced `print(message)` with proper logging
- [x] Fixed potential `None` username crash
- [x] Added handling for blocked users (403 errors)

### Files Changed
- `bot.py`
- `dailysendtask.py`
- `src/BotUser.py`

---

## Step 3: Code Structure & Quality ✅ COMPLETE

**Goal**: Maintainable, well-typed codebase

### Changes Made
- [x] Added type hints to all public functions
- [x] Added module-level docstrings
- [x] Added `from __future__ import annotations`
- [x] Replaced all `print()` with proper logging
- [x] Added request timeouts (30s)
- [x] Added input validation (hour range, daily_types whitelist)
- [x] Removed debug `set_trace_callback(print)`
- [x] Removed `rootpath` dependency
- [x] Removed side effects on module import
- [x] Fixed explicit imports (removed star imports)

### Files Changed
- `src/BotUser.py`
- `src/TVShows.py`
- `src/tgcalendar/telegramcalendar.py`
- `src/utils.py`
- `config.py`
- `app_setup.py`
- `dailysendtask.py`

---

## Step 4: Database & Caching Modernization ✅ COMPLETE

**Goal**: Reliable, maintainable data layer

### Changes Made
- [x] Fixed cache lifecycle - removed inefficient `_manage_cache` decorator that closed cache after every operation
- [x] Added `close()` methods to `BotUserStorageHelper` and `AirdatesHelper` for clean shutdown
- [x] Added configurable cache TTLs via environment variables:
  - `CACHE_SHOWS_TTL` (default 6 hours)
  - `CACHE_USER_TTL` (default 24 hours)
  - `CACHE_ENGINES_TTL` (default 30 days)
  - `CACHE_REFRESH_TTL` (default 24 hours)
- [x] Added `check_db_health()` function to Config class
- [x] Added graceful cache cleanup on bot shutdown
- [ ] ~~Add proper connection pooling for SQLite~~ (skipped - per-operation connections are fine for SQLite)
- [ ] ~~Consider adding Alembic for schema migrations~~ (skipped - current migration approach adequate)
- [ ] ~~Add cache statistics logging~~ (skipped - not essential)

### Files Changed
- `config.py`
- `src/BotUser.py`
- `src/TVShows.py`
- `bot.py`
- `dailysendtask.py`

---

## Step 5: Production Hardening ⏳ PENDING

**Goal**: Production-ready deployment

### Planned Changes
- [ ] Multi-stage Dockerfile (smaller image)
- [ ] Add healthcheck endpoint or script
- [ ] Proper logging to stdout (12-factor app)
- [ ] Add metrics/monitoring hooks
- [ ] Consider async rewrite for better concurrency
- [ ] Add CI/CD pipeline (tests, linting, build)
- [ ] Security scan dependencies
- [ ] Add rate limiting for API requests

### Files to Change
- `Dockerfile`
- `docker-compose.yml`
- `bot.py`
- New: `healthcheck.py`
- New: `.github/workflows/ci.yml` (optional)

---

## Testing Commands

```bash
# Build the image
docker compose build

# Run the bot
docker compose up -d bot

# Check logs
docker compose logs -f bot

# Run daily task manually
docker compose run --rm daily-task

# Stop gracefully
docker compose stop bot
```

## Cron Setup (Host)

```bash
# Run daily digest every hour at :05
5 * * * * cd /path/to/airdatesTVbot && docker compose run --rm daily-task
```

---

## Current Status

| Step | Status | Description |
|------|--------|-------------|
| 1 | ✅ Complete | Fix Critical Breakages |
| 2 | ✅ Complete | pyTelegramBotAPI 4.x |
| 3 | ✅ Complete | Code Structure & Quality |
| 4 | ✅ Complete | Database & Caching |
| 5 | ⏳ Pending | Production Hardening |
