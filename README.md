# airdates TV bot

Display your shows from airdates.tv, get daily updates, search shows by name/date

Python 3.11+, SQLite 3.24.0+ (upsert support)

On 1st run and if DB migration needed (can be run every release):

`python3 app_setup.py`

crontab to send daily digest - run every hour:

`5 * * * * python3 dailysendtask.py`

### Installing with Docker

#### 1. Clone the repository

```bash
git clone <this-repository-url>
cd /path/to/your/project
```

#### 2. Configure environment

Copy the example env file and set your Telegram bot token:

```bash
cp .example.env .env
```

Edit `.env` and set `TELEGRAM_TOKEN` to your bot token from [@BotFather](https://t.me/BotFather).

#### 3. Configure data directory

The bot stores its SQLite database, cache, and logs in a data directory that persists across container rebuilds.

By default, `docker-compose.yml` mounts `./data` (relative to the project directory) to `/data` inside the container. To use a custom location, edit `docker-compose.yml` and change the volume path in both services:

```yaml
volumes:
  - /path/to/your/data:/data
```

**Permissions:** The container runs as a non-root user with UID 1000. The data directory must be writable by this user:

```bash
mkdir -p /path/to/your/data
chown 1000:1000 /path/to/your/data
```

#### 4. Build and run

```bash
docker compose build
docker compose up -d
```

#### 5. Daily digest

Set up a cron job on the host to send daily digests:

```bash
5 * * * * cd /path/to/your/project && docker compose run --rm daily-task
```
