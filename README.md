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

### Standalone Image Deployment

For production servers where you don't need the source code, deploy using just the Docker image.

#### 1. Build the image

```bash
docker build -t airdatestvbot:1 .
```

#### 2. Transfer to server

**Option A - Export/Import (rsync, scp, etc.):**
```bash
# Export to tar file
docker save airdatestvbot:1 > airdatestvbot.tar

# Copy to server
rsync airdatestvbot.tar user@server:/path/

# On server - import
docker load < airdatestvbot.tar
```

**Option B - Docker registry:**
```bash
docker tag airdatestvbot:1 registry.example.com/airdatestvbot:1
docker push registry.example.com/airdatestvbot:1
# On server: docker pull registry.example.com/airdatestvbot:1
```

#### 3. Prepare environment (on server)

Create a `.env` file with your Telegram bot token:

```bash
echo "TELEGRAM_TOKEN=your_token_here" > /path/to/your/.env
```

#### 4. Prepare data directory

```bash
mkdir -p /path/to/your/data
chown 1000:1000 /path/to/your/data
```

The container runs as UID 1000. The data directory stores the SQLite database, cache, and logs.

#### 5. Run the bot

```bash
docker run -d \
  --name airdatestvbot \
  --env-file /path/to/your/.env \
  -v /path/to/your/data:/data \
  --restart unless-stopped \
  airdatestvbot:1
```

#### 6. Daily digest (cron)

```bash
# Add to crontab - runs every hour at :05
5 * * * * docker run --rm --env-file /path/to/your/.env -v /path/to/your/data:/data airdatestvbot:1 python3 dailysendtask.py
```

**Note:** The daily task container shares the same data volume as the main bot.
