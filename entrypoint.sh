#!/bin/bash
set -e

# Run database setup/migration at container start
echo "Running database setup..."
python3 app_setup.py

# Execute the main command
exec "$@"
