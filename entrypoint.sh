#!/bin/bash
set -e

# Run database setup/migration at container start
echo "Running database setup..."
python3 app_setup.py

# Secure cache directory (mitigate CVE-2025-69872)
if [ -d /data/cache ]; then
    chmod 700 /data/cache
    chmod 600 /data/cache/* 2>/dev/null || true
fi

# Execute the main command
exec "$@"
