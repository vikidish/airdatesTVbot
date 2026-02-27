#!/bin/bash
set -e

# Run database setup/migration at container start
echo "Running database setup..."
python3 app_setup.py

# Secure cache directory (mitigate CVE-2025-69872)
if [ -d /data/cache ]; then
    find /data/cache -type d -exec chmod 700 {} \;
    find /data/cache -type f -exec chmod 600 {} \;
fi

# Execute the main command
exec "$@"
